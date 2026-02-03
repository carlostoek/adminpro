"""
Free Join Request Handler - ChatJoinRequest del canal Free.

Flujo moderno de Telegram para acceso Free:
1. Usuario hace click en "Unirse" en el canal Free
2. Telegram envía ChatJoinRequest al bot
3. Bot valida canal correcto y verifica duplicados
4. Si nueva: Registra en BD y notifica con voz de Lucien + redes sociales
5. Si duplicada: Notifica tiempo restante con voz de Lucien
6. Background task aprobará automáticamente después de N minutos con mensaje de bienvenida

ESTE ES EL FLUJO PRINCIPAL - Los usuarios llegan por link público al canal,
no por el bot. Nadie sabe del bot hasta después de solicitar acceso.
"""
import logging
from datetime import datetime, timezone
from aiogram import Router, F
from aiogram.types import ChatJoinRequest
from sqlalchemy.ext.asyncio import AsyncSession

from bot.middlewares import DatabaseMiddleware
from bot.services.container import ServiceContainer

logger = logging.getLogger(__name__)

# Router para ChatJoinRequest
free_join_router = Router(name="free_join")
free_join_router.chat_join_request.middleware(DatabaseMiddleware())


@free_join_router.chat_join_request(F.chat.type.in_({"channel", "supergroup"}))
async def handle_free_join_request(
    join_request: ChatJoinRequest,
    session: AsyncSession
):
    """
    Handler para ChatJoinRequest del canal Free.

    Valida canal, verifica duplicados, registra solicitud y notifica usuario
    con voz de Lucien y botones de redes sociales.

    Args:
        join_request: Solicitud de unión al canal (evento de Telegram)
        session: Sesión de base de datos (inyectada por middleware)
    """
    user_id = join_request.from_user.id
    from_chat_id = str(join_request.chat.id)
    channel_name = join_request.chat.title or "Los Kinkys"

    logger.info(f"📺 ChatJoinRequest recibido: User={user_id} | Chat={from_chat_id}")

    container = ServiceContainer(session, join_request.bot)

    # ===== VALIDACIÓN 1: Canal Free Configurado =====
    configured_channel_id = await container.channel.get_free_channel_id()

    if not configured_channel_id:
        logger.warning("⚠️ Canal Free no configurado, declinando solicitud")
        try:
            await join_request.decline()
        except Exception as e:
            logger.error(f"❌ Error declinando (canal no configurado): {e}")
        return

    # ===== VALIDACIÓN 2: Canal Correcto (SEGURIDAD) =====
    if configured_channel_id != from_chat_id:
        logger.warning(
            f"⚠️ Solicitud desde canal NO AUTORIZADO: {from_chat_id} "
            f"(esperado: {configured_channel_id})"
        )
        try:
            await join_request.decline()
        except Exception as e:
            logger.error(f"❌ Error declinando (canal no autorizado): {e}")
        return

    # ===== CREAR/VERIFICAR SOLICITUD =====
    # Pasar datos del usuario para crearlo si no existe
    tg_user = join_request.from_user
    success, message, request = await container.subscription.create_free_request_from_join_request(
        user_id=user_id,
        from_chat_id=from_chat_id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name
    )

    # ===== OBTENER LINKS DE REDES SOCIALES =====
    social_links = await container.config.get_social_media_links()

    if not success:
        # ===== SOLICITUD DUPLICADA =====
        logger.info(f"⚠️ Solicitud duplicada detectada: user {user_id}")

        # Declinar (usuario ya tiene solicitud pendiente)
        try:
            await join_request.decline()
        except Exception as e:
            logger.error(f"❌ Error declinando solicitud duplicada: {e}")

        # Notificar tiempo restante con voz de Lucien
        if request:
            wait_time = await container.config.get_wait_time()
            minutes_since = request.minutes_since_request()
            minutes_remaining = max(0, wait_time - minutes_since)

            # Usar UserFlowMessages para mensaje de duplicado (voz de Lucien)
            duplicate_text = container.message.user.flows.free_request_duplicate(
                time_elapsed_minutes=minutes_since,
                time_remaining_minutes=minutes_remaining
            )

            try:
                await join_request.bot.send_message(
                    chat_id=user_id,
                    text=duplicate_text,
                    parse_mode="HTML"
                )
                logger.info(f"✅ Notificación de duplicado enviada a user {user_id}")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo notificar duplicado a user {user_id}: {e}")

        return

    # ===== SOLICITUD NUEVA CREADA =====
    logger.info(f"✅ Nueva solicitud Free registrada: user {user_id}")

    # Obtener tiempo de espera
    wait_time = await container.config.get_wait_time()

    # Usar UserFlowMessages para mensaje de éxito con voz de Lucien y botones de redes sociales
    success_text, keyboard = container.message.user.flows.free_request_success(
        wait_time_minutes=wait_time,
        social_links=social_links
    )

    try:
        await join_request.bot.send_message(
            chat_id=user_id,
            text=success_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        logger.info(f"✅ Notificación de nueva solicitud enviada a user {user_id} con redes sociales")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo notificar a user {user_id}: {e}")

    logger.debug(f"✅ ChatJoinRequest procesado completamente para user {user_id}")
