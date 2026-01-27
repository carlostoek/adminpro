"""
Free Flow Handler - Solicitud de acceso al canal Free.

Flujo para que usuarios soliciten acceso Free y esperen aprobación automática.
"""
import logging
from aiogram import F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.user.start import user_router
from bot.services.container import ServiceContainer

logger = logging.getLogger(__name__)


@user_router.callback_query(F.data == "user:request_free")
async def callback_request_free(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Procesa solicitud de acceso al canal Free.

    Crea la solicitud y notifica al usuario con mensaje de Lucien
    y botones de redes sociales.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    user_id = callback.from_user.id
    logger.info(f"📺 Usuario {user_id} solicitando acceso Free")

    container = ServiceContainer(session, callback.bot)

    # Verificar que canal Free está configurado
    if not await container.channel.is_free_channel_configured():
        # Use provider for error message
        error_text = container.message.user.flows.free_request_error(
            error_type="channel_not_configured"
        )
        await callback.answer(
            error_text.replace("<b>", "").replace("</b>", "").replace("🎩 ", ""),
            show_alert=True
        )
        return

    # Verificar si ya tiene solicitud pendiente
    existing_request = await container.subscription.get_free_request(user_id)

    if existing_request:
        # Calcular tiempo restante (business logic stays in handler)
        from datetime import datetime, timezone

        wait_time_minutes = await container.config.get_wait_time()
        time_since_request = (datetime.now(timezone.utc) - existing_request.request_date).total_seconds() / 60
        time_elapsed_minutes = int(time_since_request)
        time_remaining_minutes = max(0, int(wait_time_minutes - time_since_request))

        # Use provider for duplicate message
        duplicate_text = container.message.user.flows.free_request_duplicate(
            time_elapsed_minutes=time_elapsed_minutes,
            time_remaining_minutes=time_remaining_minutes
        )

        try:
            await callback.message.edit_text(
                duplicate_text,
                parse_mode="HTML"
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                logger.error(f"Error editando mensaje: {e}")

        await callback.answer()
        return

    # Crear nueva solicitud
    request = await container.subscription.create_free_request(user_id)

    # Fetch social media links from config
    social_links = await container.config.get_social_media_links()

    # Use provider for success message with social media keyboard
    success_text, keyboard = container.message.user.flows.free_request_success(
        wait_time_minutes=await container.config.get_wait_time(),
        social_links=social_links
    )

    try:
        await callback.message.edit_text(
            success_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"Error editando mensaje: {e}")

    await callback.answer("✅ Solicitud creada")

    logger.info(f"✅ Solicitud Free creada para user {user_id} con redes sociales")
