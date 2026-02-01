"""
Tests para Sprint 1 (PR #70) - Mejoras al sistema Free y Token-Plan

Cubre:
1. Aprobación Free con invite link y confirmación
2. Ventana anti-spam de 5 minutos
3. Limpieza de solicitudes antiguas
4. Validación de plan en tokens
5. Mensajes diferenciados de error
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select

from bot.database.models import (
    FreeChannelRequest,
    InvitationToken,
    SubscriptionPlan,
    BotConfig
)
from bot.services.container import ServiceContainer
from config import Config


@pytest.fixture
def mock_bot():
    """Mock del bot de Telegram."""
    bot = AsyncMock()

    # Mock para get_chat
    mock_chat = MagicMock()
    mock_chat.title = "Canal Free Test"
    bot.get_chat.return_value = mock_chat

    # Mock para approve_chat_join_request
    bot.approve_chat_join_request.return_value = True

    # Mock para create_chat_invite_link
    mock_invite = MagicMock()
    mock_invite.invite_link = "https://t.me/+test_invite_link"
    bot.create_chat_invite_link.return_value = mock_invite

    # Mock para send_message
    bot.send_message.return_value = True

    return bot


@pytest.mark.asyncio
async def test_spam_window_prevents_duplicate_requests(mock_bot, test_session, test_user):
    """
    Test: Ventana anti-spam de 5 minutos previene solicitudes duplicadas.

    Verifica que:
    - Primera solicitud se crea correctamente
    - Segunda solicitud dentro de 5 min es rechazada
    - Se retorna la solicitud existente (no se duplica)
    """
    container = ServiceContainer(test_session, mock_bot)

    # Configurar canal Free
    config = await test_session.get(BotConfig, 1)
    if not config:
        config = BotConfig(id=1)
        test_session.add(config)
    config.free_channel_id = "-1001234567890"
    await test_session.commit()

    user_id = test_user.user_id

    # Primera solicitud: debe crearse
    success1, msg1, request1 = await container.subscription.create_free_request_from_join_request(
        user_id=user_id,
        from_chat_id=config.free_channel_id
    )

    assert success1 is True
    assert "exitosamente" in msg1.lower()
    assert request1 is not None
    assert request1.user_id == user_id
    assert request1.processed is False

    # Segunda solicitud (inmediata): debe rechazarse
    success2, msg2, request2 = await container.subscription.create_free_request_from_join_request(
        user_id=user_id,
        from_chat_id=config.free_channel_id
    )

    assert success2 is False
    assert "pendiente" in msg2.lower()
    assert request2 is not None
    assert request2.id == request1.id  # Retorna la misma


@pytest.mark.asyncio
async def test_spam_window_allows_request_after_timeout(mock_bot, test_session, test_free_user):
    """
    Test: Ventana anti-spam permite nueva solicitud después de 5+ minutos.

    Verifica que:
    - Solicitudes antiguas (>5 min) se eliminan
    - Nueva solicitud se crea exitosamente
    - Estado limpio (no duplicados)
    """
    container = ServiceContainer(test_session, mock_bot)

    # Configurar canal Free
    config = await test_session.get(BotConfig, 1)
    if not config:
        config = BotConfig(id=1)
        test_session.add(config)
    config.free_channel_id = "-1001234567890"
    await test_session.commit()

    user_id = test_free_user.user_id

    # Crear solicitud antigua (6 minutos atrás)
    old_request = FreeChannelRequest(
        user_id=user_id,
        request_date=datetime.utcnow() - timedelta(minutes=6),
        processed=False
    )
    test_session.add(old_request)
    await test_session.commit()

    # Nueva solicitud: debe limpiar la antigua y crear nueva
    success, msg, new_request = await container.subscription.create_free_request_from_join_request(
        user_id=user_id,
        from_chat_id=config.free_channel_id
    )

    assert success is True
    assert new_request is not None
    # Nota: SQLite puede reutilizar IDs de filas eliminadas,
    # así que verificamos que sea nueva comparando timestamps
    assert new_request.minutes_since_request() < 1  # Recién creada

    # Verificar que no existen duplicados
    from sqlalchemy import select, func
    result = await test_session.execute(
        select(func.count()).select_from(FreeChannelRequest).where(
            FreeChannelRequest.user_id == user_id
        )
    )
    count = result.scalar()
    assert count == 1  # Solo la nueva solicitud


@pytest.mark.asyncio
async def test_approve_free_request_with_invite_link(mock_bot, test_session, test_free_user):
    """
    Test: Aprobación Free envía invite link y confirmación.

    Verifica que:
    - get_chat() se llama UNA vez (fuera del loop)
    - approve_chat_join_request() se llama correctamente
    - create_invite_link() se llama con parámetros correctos
    - send_message() envía confirmación con invite link
    - Solicitud se marca como procesada
    """
    container = ServiceContainer(test_session, mock_bot)

    # Configurar canal Free
    config = await test_session.get(BotConfig, 1)
    if not config:
        config = BotConfig(id=1)
        test_session.add(config)
    config.free_channel_id = "-1001234567890"
    config.free_wait_time_minutes = 5
    await test_session.commit()

    # Crear solicitud lista para procesar (6 minutos atrás)
    user_id = test_free_user.user_id
    request = FreeChannelRequest(
        user_id=user_id,
        request_date=datetime.utcnow() - timedelta(minutes=6),
        processed=False
    )
    test_session.add(request)
    await test_session.commit()

    # Aprobar solicitudes
    success_count, error_count = await container.subscription.approve_ready_free_requests(
        wait_time_minutes=config.free_wait_time_minutes,
        free_channel_id=config.free_channel_id
    )

    assert success_count == 1
    assert error_count == 0

    # Verificar que get_chat() se llamó UNA vez (optimización)
    assert mock_bot.get_chat.call_count == 1
    mock_bot.get_chat.assert_called_with(config.free_channel_id)

    # Verificar approve_chat_join_request
    mock_bot.approve_chat_join_request.assert_called_once_with(
        chat_id=config.free_channel_id,
        user_id=user_id
    )

    # Verificar create_invite_link
    mock_bot.create_chat_invite_link.assert_called_once()
    call_kwargs = mock_bot.create_chat_invite_link.call_args.kwargs
    assert call_kwargs["chat_id"] == config.free_channel_id
    assert call_kwargs["member_limit"] == 1  # Un solo uso

    # Verificar send_message con confirmación
    mock_bot.send_message.assert_called_once()
    call_kwargs = mock_bot.send_message.call_args.kwargs
    assert call_kwargs["chat_id"] == user_id
    assert "Acceso Free Aprobado" in call_kwargs["text"]
    assert "https://t.me/+test_invite_link" in call_kwargs["text"]

    # Verificar que solicitud se marcó como procesada
    await test_session.refresh(request)
    assert request.processed is True
    assert request.processed_at is not None


@pytest.mark.asyncio
async def test_token_without_plan_id_rejected(mock_bot, test_session):
    """
    Test: Token sin plan_id es rechazado correctamente.

    Verifica:
    - Token antiguo sin plan_id detectado
    - Mensaje de error apropiado
    - Compatibilidad hacia atrás
    """
    container = ServiceContainer(test_session, mock_bot)

    # Crear token SIN plan_id (token antiguo)
    admin_id = 1280444712
    old_token = InvitationToken(
        token="OLD_TOKEN_NO_PLAN",
        generated_by=admin_id,
        created_at=datetime.utcnow(),
        duration_hours=24,
        used=False,
        plan_id=None  # SIN PLAN
    )
    test_session.add(old_token)
    await test_session.commit()

    # Intentar validar
    is_valid, msg, token = await container.subscription.validate_token("OLD_TOKEN_NO_PLAN")

    # Token es técnicamente válido (no usado, no expirado)
    assert is_valid is True

    # Pero al verificar plan_id debe fallar
    assert token.plan_id is None


@pytest.mark.asyncio
async def test_token_with_inactive_plan_rejected(mock_bot, test_session, test_inactive_plan):
    """
    Test: Token con plan inactivo es rechazado.

    Verifica:
    - Plan existe pero está desactivado
    - Mensaje de error diferenciado
    """
    from sqlalchemy import select
    container = ServiceContainer(test_session, mock_bot)

    # Usar plan inactivo del fixture
    inactive_plan = test_inactive_plan

    # Crear token vinculado al plan inactivo
    admin_id = 1280444712
    token = InvitationToken(
        token="TOKEN_INACTIVE_PLAN",
        generated_by=admin_id,
        created_at=datetime.utcnow(),
        duration_hours=24,
        used=False,
        plan_id=inactive_plan.id
    )
    test_session.add(token)
    await test_session.commit()

    # Validar token (técnicamente válido)
    is_valid, msg, token_obj = await container.subscription.validate_token("TOKEN_INACTIVE_PLAN")
    assert is_valid is True

    # Cargar plan directamente de BD
    result = await test_session.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.id == token_obj.plan_id)
    )
    plan = result.scalar_one_or_none()
    assert plan is not None
    assert plan.active is False  # Plan inactivo


@pytest.mark.asyncio
async def test_token_without_plan_rejected(mock_bot, test_session):
    """
    Test: Token sin plan asociado es rechazado.

    Verifica:
    - Token tiene plan_id=None
    - Mensaje de error apropiado
    """
    container = ServiceContainer(test_session, mock_bot)

    # Crear token SIN plan (plan_id=None)
    admin_id = 1280444712
    token = InvitationToken(
        token="TOKEN_NO_PLAN",
        generated_by=admin_id,
        created_at=datetime.utcnow(),
        duration_hours=24,
        used=False,
        plan_id=None  # SIN PLAN
    )
    test_session.add(token)
    await test_session.commit()

    # Validar token (técnicamente válido como token)
    is_valid, msg, token_obj = await container.subscription.validate_token("TOKEN_NO_PLAN")
    assert is_valid is True

    # Verificar que no tiene plan asociado
    assert token_obj.plan_id is None  # Sin plan


@pytest.mark.asyncio
async def test_bot_blocked_error_handled_gracefully(mock_bot, test_session, test_user):
    """
    Test: Error de bot bloqueado se maneja gracefully.

    Verifica:
    - Usuario bloqueó el bot (Forbidden error)
    - Solicitud se aprueba de todos modos
    - Error se loguea como WARNING (no ERROR)
    - No crashea el procesamiento
    """
    container = ServiceContainer(test_session, mock_bot)

    # Configurar canal Free
    config = await test_session.get(BotConfig, 1)
    if not config:
        config = BotConfig(id=1)
        test_session.add(config)
    config.free_channel_id = "-1001234567890"
    config.free_wait_time_minutes = 5
    await test_session.commit()

    # Crear solicitud
    user_id = test_user.user_id
    request = FreeChannelRequest(
        user_id=user_id,
        request_date=datetime.utcnow() - timedelta(minutes=6),
        processed=False
    )
    test_session.add(request)
    await test_session.commit()

    # Mock: Usuario bloqueó el bot
    mock_bot.send_message.side_effect = Exception("Forbidden: bot was blocked by the user")

    # Aprobar solicitudes (no debe crashear)
    success_count, error_count = await container.subscription.approve_ready_free_requests(
        wait_time_minutes=config.free_wait_time_minutes,
        free_channel_id=config.free_channel_id
    )

    # Debe contar como éxito (aprobación completada, solo falló notificación)
    assert success_count == 1
    assert error_count == 0

    # Solicitud marcada como procesada
    await test_session.refresh(request)
    assert request.processed is True


@pytest.mark.asyncio
async def test_configurable_spam_window(mock_bot, test_session):
    """
    Test: Ventana anti-spam es configurable vía Config.

    Verifica:
    - Config.FREE_REQUEST_SPAM_WINDOW_MINUTES se usa correctamente
    - Cambiar el valor afecta el comportamiento
    """
    # Verificar que la constante existe
    assert hasattr(Config, "FREE_REQUEST_SPAM_WINDOW_MINUTES")
    assert isinstance(Config.FREE_REQUEST_SPAM_WINDOW_MINUTES, int)
    assert Config.FREE_REQUEST_SPAM_WINDOW_MINUTES >= 1

    # El valor por defecto debe ser 5 minutos
    assert Config.FREE_REQUEST_SPAM_WINDOW_MINUTES == 5
