"""
User Start Handler - Punto de entrada para usuarios.

Handler del comando /start que detecta si el usuario es admin o usuario normal.
También maneja deep links para activación automática de tokens VIP.

Deep Link Format: t.me/botname?start=TOKEN
"""
import logging
from datetime import datetime, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.enums import UserRole
from bot.middlewares import DatabaseMiddleware
from bot.services.container import ServiceContainer
from bot.utils.formatters import format_currency
from config import Config

logger = logging.getLogger(__name__)

# Router para handlers de usuario
user_router = Router(name="user")

# Aplicar middleware de database (NO AdminAuth, estos son usuarios normales)
user_router.message.middleware(DatabaseMiddleware())
user_router.callback_query.middleware(DatabaseMiddleware())


@user_router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession):
    """
    Handler del comando /start para usuarios.

    Comportamiento:
    - Si hay parámetro (deep link) → Activa token automáticamente
    - Si es admin → Redirige a /admin
    - Si es VIP activo → Muestra mensaje de bienvenida con días restantes
    - Si no es admin → Muestra menú de usuario (VIP/Free)

    Deep Link Format:
    - /start → Mensaje de bienvenida normal
    - /start TOKEN → Activa token VIP automáticamente (deep link)

    Args:
        message: Mensaje del usuario
        session: Sesión de BD (inyectada por middleware)
    """
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Usuario"

    logger.info(f"👋 Usuario {user_id} ({user_name}) ejecutó /start")

    # Crear/obtener usuario con rol FREE si no existe
    container = ServiceContainer(session, message.bot)
    user = await container.user.get_or_create_user(
        telegram_user=message.from_user,
        default_role=UserRole.FREE
    )
    logger.debug(f"👤 Usuario en sistema: {user.user_id} - Rol: {user.role.value}")

    # Verificar si es admin PRIMERO
    is_admin = Config.is_admin(user_id)

    if is_admin:
        # Redirect admin to /admin using message provider
        session_history = container.session_history
        text, _ = container.message.user.start.greeting(
            user_name=user_name,
            user_id=user_id,
            is_admin=True,
            is_vip=False,
            vip_days_remaining=0,
            session_history=session_history
        )
        await message.answer(text, parse_mode="HTML")
        return

    # Verificar si hay parámetro (deep link)
    # Formato: /start TOKEN
    args = message.text.split(maxsplit=1)

    if len(args) > 1:
        # Hay parámetro → Es un deep link con token
        token_string = args[1].strip()

        logger.info(f"🔗 Deep link detectado: Token={token_string} | User={user_id}")

        # Activar token automáticamente
        await _activate_token_from_deeplink(
            message=message,
            session=session,
            container=container,
            user=user,
            token_string=token_string
        )
    else:
        # No hay parámetro → Mensaje de bienvenida normal
        await _send_welcome_message(message, user, container, user_id)


async def _activate_token_from_deeplink(
    message: Message,
    session: AsyncSession,
    container: ServiceContainer,
    user,  # User model
    token_string: str
):
    """
    Activa un token VIP desde un deep link.

    NUEVO: Maneja la activación automática cuando el usuario hace click en el deep link.

    Args:
        message: Mensaje original
        session: Sesión de BD
        container: Service container
        user: Usuario del sistema
        token_string: String del token a activar
    """
    # Extraer nombre de usuario
    user_name = message.from_user.first_name or "Usuario"

    try:
        # Validar token
        is_valid, msg_result, token = await container.subscription.validate_token(token_string)

        if not is_valid:
            # Token invalid - delegate to provider
            error_text = container.message.user.start.deep_link_activation_error(
                error_type="invalid",
                details=""
            )
            await message.answer(error_text, parse_mode="HTML")
            return

        # Verificar si el token tiene plan asociado (acceso directo a plan_id, sin lazy loading)
        if not token.plan_id:
            # Token antiguo sin plan asociado (compatibilidad)
            error_text = container.message.user.start.deep_link_activation_error(
                error_type="no_plan",
                details=""
            )
            await message.answer(error_text, parse_mode="HTML")
            return

        # Cargar plan explícitamente (sin lazy loading)
        plan = await container.pricing.get_plan_by_id(token.plan_id)

        if not plan:
            # Plan not found - delegate to provider
            error_text = container.message.user.start.deep_link_activation_error(
                error_type="no_plan",
                details="El plan ya no existe en el sistema."
            )
            await message.answer(error_text, parse_mode="HTML")
            return

        if not plan.active:
            # Plan deactivated - delegate to provider
            error_text = container.message.user.start.deep_link_activation_error(
                error_type="no_plan",
                details="El plan fue desactivado."
            )
            await message.answer(error_text, parse_mode="HTML")
            return

        # Marcar token como usado
        token.used = True
        token.used_by = user.user_id
        token.used_at = datetime.utcnow()

        # Activar suscripción VIP (inicia flujo ritualizado)
        subscriber = await container.subscription.activate_vip_subscription(
            user_id=user.user_id,
            token_id=token.id,
            duration_hours=plan.duration_days * 24
        )

        # NO cambiar rol a VIP aún (UserRole se cambia en Stage 3)
        # user.role = UserRole.FREE  # Ya es FREE por defecto

        # Commit de la transacción
        await session.commit()
        await session.refresh(subscriber)

        logger.info(
            f"✅ Usuario {user.user_id} activó suscripción VIP vía deep link | "
            f"Plan: {plan.name} | Stage: {subscriber.vip_entry_stage}"
        )

        # Iniciar flujo ritualizado (NO enviar enlace inmediato)
        from bot.handlers.user.vip_entry import show_vip_entry_stage

        await show_vip_entry_stage(
            message=message,
            container=container,
            stage=subscriber.vip_entry_stage
        )

    except Exception as e:
        logger.error(f"❌ Error activando token desde deep link: {e}", exc_info=True)

        # Generic error - delegate to provider
        error_text = container.message.user.start.deep_link_activation_error(
            error_type="invalid",
            details="Error técnico al procesar la invitación."
        )
        await message.answer(error_text, parse_mode="HTML")


async def _send_welcome_message(
    message: Message,
    user,  # User model
    container: ServiceContainer,
    user_id: int
):
    """
    Envía mensaje de bienvenida normal y muestra el menú correspondiente.

    Args:
        message: Mensaje original
        user: Usuario del sistema
        container: Service container
        user_id: ID del usuario
    """
    user_name = message.from_user.first_name or "Usuario"

    # Phase 13: Check if user has incomplete VIP entry flow
    subscriber = await container.subscription.get_vip_subscriber(user_id)

    if subscriber and subscriber.vip_entry_stage:
        # User has incomplete entry flow - resume from current stage
        from bot.handlers.user.vip_entry import show_vip_entry_stage

        logger.info(
            f"🔄 User {user_id} resuming VIP entry flow at stage "
            f"{subscriber.vip_entry_stage}"
        )

        await show_vip_entry_stage(
            message=message,
            container=container,
            stage=subscriber.vip_entry_stage
        )
        return

    # Original logic: Detect role and show menu
    role_service = container.role_detection
    detected_role = await role_service.get_user_role(user_id)
    is_vip = detected_role == UserRole.VIP

    # Preparar data dictionary para menu handlers (simula middleware injection)
    data = {
        "container": container,
        "session": None,  # Ya estamos dentro del contexto de sesión
        "user_role": detected_role,  # Usar rol detectado en tiempo real
    }

    # Mostrar menú apropiado según rol
    if is_vip:
        # Usuario VIP: mostrar menú VIP
        try:
            from bot.handlers.vip.menu import show_vip_menu
            await show_vip_menu(message, data)
        except ImportError:
            logger.warning("VIP menu handler no disponible")
            # Fallback a greeting normal
            await _send_greeting_fallback(message, container, user_name, user_id, is_vip)
    else:
        # Usuario Free: mostrar menú Free
        try:
            from bot.handlers.free.menu import show_free_menu
            await show_free_menu(message, data)
        except ImportError:
            logger.warning("Free menu handler no disponible")
            # Fallback a greeting normal
            await _send_greeting_fallback(message, container, user_name, user_id, is_vip)


async def _send_greeting_fallback(
    message: Message,
    container: ServiceContainer,
    user_name: str,
    user_id: int,
    is_vip: bool
):
    """
    Envía mensaje de bienvenida simple (fallback si menu handlers no disponibles).

    Args:
        message: Mensaje original
        container: Service container
        user_name: Nombre del usuario
        user_id: ID del usuario
        is_vip: Si es usuario VIP
    """
    # Calcular días restantes si es VIP
    vip_days_remaining = 0
    if is_vip:
        subscriber = await container.subscription.get_vip_subscriber(user_id)
        if subscriber and hasattr(subscriber, 'expiry_date') and subscriber.expiry_date:
            # Asegurar que expiry_date tiene timezone
            expiry = subscriber.expiry_date
            if expiry.tzinfo is None:
                # Si es naive, asumimos UTC
                expiry = expiry.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            vip_days_remaining = max(0, (expiry - now).days)

    # Use provider for greeting (handles admin/VIP/free automatically)
    session_history = container.session_history
    text, keyboard = container.message.user.start.greeting(
        user_name=user_name,
        user_id=user_id,
        is_admin=False,  # Already filtered admins above
        is_vip=is_vip,
        vip_days_remaining=vip_days_remaining,
        session_history=session_history
    )

    await message.answer(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
