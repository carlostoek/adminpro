"""
Free Join Request Handler - ChatJoinRequest del canal Free.

Flujo moderno de Telegram para acceso Free:
1. Usuario hace click en "Unirse" en el canal Free
2. Telegram envía ChatJoinRequest al bot
3. Bot valida canal correcto y verifica duplicados
4. Si nueva: Registra en BD y notifica tiempo de espera
5. Si duplicada: Notifica tiempo restante
6. Background task aprobará automáticamente después de N minutos
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

    Valida canal, verifica duplicados, registra solicitud y notifica usuario.

    Args:
        join_request: Solicitud de unión al canal (evento de Telegram)
        session: Sesión de base de datos (inyectada por middleware)
    """
    user_id = join_request.from_user.id
    user_name = join_request.from_user.first_name or "Usuario"
    from_chat_id = str(join_request.chat.id)
    channel_name = join_request.chat.title or "Canal Free"

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
    success, message, request = await container.subscription.create_free_request_from_join_request(
        user_id=user_id,
        from_chat_id=from_chat_id
    )

    if not success:
        # ===== SOLICITUD DUPLICADA =====
        logger.info(f"⚠️ Solicitud duplicada detectada: user {user_id}")

        # Declinar (usuario ya tiene solicitud pendiente)
        try:
            await join_request.decline()
        except Exception as e:
            logger.error(f"❌ Error declinando solicitud duplicada: {e}")

        # Notificar tiempo restante con barra de progreso
        if request:
            from bot.utils.formatters import format_progress_with_time

            wait_time = await container.config.get_wait_time()
            minutes_since = request.minutes_since_request()
            minutes_remaining = max(0, wait_time - minutes_since)

            # Generar barra de progreso visual
            progress_bar = format_progress_with_time(minutes_remaining, wait_time, length=15)

            try:
                await join_request.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"ℹ️ <b>Solicitud Pendiente</b>\n\n"
                        f"📺 Canal: <b>{channel_name}</b>\n\n"
                        f"Ya tienes una solicitud en proceso.\n\n"
                        f"<b>Progreso de Aprobación:</b>\n"
                        f"<code>{progress_bar}</code>\n\n"
                        f"⏰ <b>Detalles:</b>\n"
                        f"• Tiempo transcurrido: <b>{minutes_since} min</b>\n"
                        f"• Tiempo restante: <b>{minutes_remaining} min</b>\n"
                        f"• Total configurado: <b>{wait_time} min</b>\n\n"
                        f"✅ Serás aprobado automáticamente en {minutes_remaining} minutos.\n\n"
                        f"💡 No es necesario solicitar de nuevo."
                    ),
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

    # Enviar notificación automática
    try:
        await join_request.bot.send_message(
            chat_id=user_id,
            text=(
                f"👋 <b>Solicitud Registrada</b>\n\n"
                f"📺 Canal: <b>{channel_name}</b>\n\n"
                f"Tu solicitud de acceso ha sido registrada exitosamente.\n\n"
                f"⏱️ <b>Tiempo de espera:</b> {wait_time} minutos\n\n"
                f"<b>Próximos pasos:</b>\n"
                f"1️⃣ Tu solicitud está en cola de aprobación\n"
                f"2️⃣ Serás aprobado automáticamente en ~{wait_time} min\n"
                f"3️⃣ Recibirás notificación cuando seas aprobado\n"
                f"4️⃣ Podrás acceder al canal inmediatamente\n\n"
                f"💡 <i>No necesitas hacer nada más, el proceso es automático.</i>"
            ),
            parse_mode="HTML"
        )

        logger.info(f"✅ Notificación de nueva solicitud enviada a user {user_id}")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo notificar a user {user_id}: {e}")

    logger.debug(f"✅ ChatJoinRequest procesado completamente para user {user_id}")
