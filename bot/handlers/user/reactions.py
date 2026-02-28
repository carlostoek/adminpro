"""
Reaction Handlers - Gestión de reacciones a contenido de canales.

Handlers:
- handle_reaction_callback: Procesa toques en botones de reacción
"""
import logging
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from bot.services.container import ServiceContainer
from bot.database.enums import ContentCategory
from bot.utils.keyboards import get_reaction_keyboard_with_counts

logger = logging.getLogger(__name__)
router = Router()


# Callback data format: react:{channel_id}:{content_id}:{emoji}
# Fallback format: r:{content_id}:{emoji}


@router.callback_query(F.data.startswith("react:"))
async def handle_reaction_callback(
    callback: CallbackQuery,
    container: ServiceContainer,
    bot: Bot
) -> None:
    """
    Procesa un toque en botón de reacción.

    Args:
        callback: Callback query del botón presionado
        container: ServiceContainer con servicios
        bot: Instancia del bot
    """
    # Parse callback data
    # Format: react:{channel_id}:{content_id}:{emoji}
    parts = callback.data.split(":")

    if len(parts) != 4:
        logger.warning(f"Invalid callback data format: {callback.data}")
        await callback.answer("Error: formato inválido", show_alert=True)
        return

    _, channel_id, content_id_str, emoji = parts

    try:
        content_id = int(content_id_str)
    except ValueError:
        logger.warning(f"Invalid content_id in callback: {content_id_str}")
        await callback.answer("Error: contenido inválido", show_alert=True)
        return

    user_id = callback.from_user.id

    logger.info(
        f"Reaction callback: user={user_id}, content={content_id}, "
        f"channel={channel_id}, emoji={emoji}"
    )

    # Determine content category based on channel
    # This requires knowing if the channel is VIP or Free
    content_category = await _get_content_category(container, channel_id)

    # Process reaction through service
    success, code, data = await container.reaction.add_reaction(
        user_id=user_id,
        content_id=content_id,
        channel_id=channel_id,
        emoji=emoji,
        content_category=content_category
    )

    # Handle result
    if success:
        await _handle_success(callback, data, emoji)

        # Check for rewards on reaction_added event
        try:
            unlocked = await container.reward.check_rewards_on_event(
                user_id=user_id,
                event_type="reaction_added"
            )
            if unlocked:
                # Build and send reward notification
                notification = container.reward.build_reward_notification(
                    unlocked,
                    event_context="reaction_added"
                )
                if notification["text"]:
                    # callback.message puede ser None en mensajes >48h
                    if callback.message is not None:
                        await callback.message.answer(
                            notification["text"],
                            parse_mode="HTML"
                        )
                    else:
                        logger.debug(
                            f"No se pudo enviar notificación de reward a user {user_id}: "
                            "mensaje expirado (>48h)"
                        )
        except Exception as e:
            logger.error(f"Error checking rewards on reaction: {e}")
    else:
        await _handle_failure(callback, code, data)

    # Update keyboard with new counts (if message exists and we can edit)
    await _update_keyboard(callback, container, content_id, channel_id, user_id)


async def _get_content_category(
    container: ServiceContainer,
    channel_id: str
) -> Optional[ContentCategory]:
    """
    Determina la categoría del contenido basado en el canal.

    Args:
        container: ServiceContainer
        channel_id: ID del canal

    Returns:
        ContentCategory o None
    """
    config = await container.config.get_config()

    if channel_id == config.vip_channel_id:
        return ContentCategory.VIP_CONTENT
    elif channel_id == config.free_channel_id:
        return ContentCategory.FREE_CONTENT

    return None


async def _handle_success(
    callback: CallbackQuery,
    data: dict,
    emoji: str
) -> None:
    """
    Maneja reacción exitosa.

    Args:
        callback: Callback query
        data: Datos de la reacción (besitos_earned, reactions_today, daily_limit)
        emoji: Emoji reaccionado
    """
    besitos = data.get("besitos_earned", 0)
    today = data.get("reactions_today", 0)
    limit = data.get("daily_limit", 20)

    if besitos > 0:
        message = f"{emoji} ¡Reacción guardada! +{besitos} besitos ({today}/{limit})"
    else:
        message = f"{emoji} ¡Reacción guardada! ({today}/{limit})"

    await callback.answer(message, show_alert=False)


async def _handle_failure(
    callback: CallbackQuery,
    code: str,
    data: Optional[dict]
) -> None:
    """
    Maneja fallo en reacción.

    Args:
        callback: Callback query
        code: Código de error
        data: Datos adicionales del error (puede ser None)
    """
    # Ensure data is a dict for safe access
    data = data or {}

    messages = {
        "duplicate": "🎩 Lucien:\n\nSé que le encantan las publicaciones de Diana pero solo puede reaccionar una vez a cada publicación.",
        "rate_limited": f"Espera {data.get('seconds_remaining', 30)}s entre reacciones ⏱",
        "daily_limit_reached": f"Límite diario alcanzado ({data.get('used', 20)}/{data.get('limit', 20)}) 📊",
        "no_access": data.get("error", "No tienes acceso a este contenido 🔒"),
        "error": "Error al guardar reacción ❌"
    }

    message = messages.get(code, "Error desconocido")
    await callback.answer(message, show_alert=True)


async def _update_keyboard(
    callback: CallbackQuery,
    container: ServiceContainer,
    content_id: int,
    channel_id: str,
    user_id: int
) -> None:
    """
    Actualiza el teclado con conteos actualizados.

    Args:
        callback: Callback query
        container: ServiceContainer
        content_id: ID del contenido
        channel_id: ID del canal
        user_id: ID del usuario (para marcar sus reacciones)
    """
    try:
        # Get updated reaction counts
        counts = await container.reaction.get_content_reactions(content_id, channel_id)

        # Get user's reactions to mark them
        user_reactions = await container.reaction.get_user_reactions_for_content(
            user_id=user_id,
            content_id=content_id,
            channel_id=channel_id
        )

        # Build new keyboard with user reactions marked and counts displayed
        from bot.utils.keyboards import DEFAULT_REACTIONS
        keyboard = get_reaction_keyboard_with_counts(
            content_id=content_id,
            channel_id=channel_id,
            reactions=DEFAULT_REACTIONS,
            user_reactions=user_reactions,
            counts=counts
        )

        # Try to update the message
        # Note: callback.message puede ser None en mensajes >48h
        if callback.message is None:
            logger.debug(f"No se puede actualizar keyboard: mensaje expirado (>48h)")
            return
        await callback.message.edit_reply_markup(reply_markup=keyboard)

    except TelegramBadRequest as e:
        # Message might be unchanged or too old
        if "message is not modified" in str(e).lower():
            pass  # OK, no change needed
        else:
            logger.debug(f"Could not update keyboard: {e}")
    except Exception as e:
        logger.error(f"Error updating reaction keyboard: {e}")


@router.callback_query(F.data.startswith("r:"))
async def handle_short_reaction_callback(
    callback: CallbackQuery,
    container: ServiceContainer,
    bot: Bot
) -> None:
    """
    Procesa callback en formato corto.

    Format: r:{content_id}:{emoji}
    Channel must be determined from message context.
    """
    parts = callback.data.split(":")

    if len(parts) != 3:
        await callback.answer("Error: formato inválido", show_alert=True)
        return

    _, content_id_str, emoji = parts

    try:
        content_id = int(content_id_str)
    except ValueError:
        await callback.answer("Error: contenido inválido", show_alert=True)
        return

    # Get channel from message
    if callback.message and callback.message.chat:
        channel_id = str(callback.message.chat.id)
    else:
        await callback.answer("Error: no se pudo determinar el canal", show_alert=True)
        return

    # Delegate to main handler logic
    user_id = callback.from_user.id
    content_category = await _get_content_category(container, channel_id)

    success, code, data = await container.reaction.add_reaction(
        user_id=user_id,
        content_id=content_id,
        channel_id=channel_id,
        emoji=emoji,
        content_category=content_category
    )

    if success:
        await _handle_success(callback, data, emoji)

        # Check for rewards on reaction_added event
        try:
            unlocked = await container.reward.check_rewards_on_event(
                user_id=user_id,
                event_type="reaction_added"
            )
            if unlocked:
                # Build and send reward notification
                notification = container.reward.build_reward_notification(
                    unlocked,
                    event_context="reaction_added"
                )
                if notification["text"]:
                    # callback.message puede ser None en mensajes >48h
                    if callback.message is not None:
                        await callback.message.answer(
                            notification["text"],
                            parse_mode="HTML"
                        )
                    else:
                        logger.debug(
                            f"No se pudo enviar notificación de reward a user {user_id}: "
                            "mensaje expirado (>48h)"
                        )
        except Exception as e:
            logger.error(f"Error checking rewards on reaction: {e}")
    else:
        await _handle_failure(callback, code, data)

    await _update_keyboard(callback, container, content_id, channel_id, user_id)


def register_reaction_handlers(dp) -> None:
    """
    Registra los handlers de reacciones en el dispatcher.

    Args:
        dp: Dispatcher de aiogram
    """
    dp.include_router(router)
    logger.info("✅ Reaction handlers registered")
