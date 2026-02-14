"""
User Reward Handlers - Gestión de recompensas y logros para usuarios.

Handlers:
- rewards_list_handler: Muestra lista de recompensas disponibles (/rewards)
- reward_claim_handler: Procesa reclamo de recompensa
- reward_detail_handler: Muestra detalle de recompensa específica

Voz: Lucien (🎩) para listas y errores, Diana (🫦) para éxito de reclamo
"""
import logging
from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.services.container import ServiceContainer
from bot.database.enums import RewardStatus, RewardType
from bot.middlewares import DatabaseMiddleware

logger = logging.getLogger(__name__)

# Router para handlers de recompensas
rewards_router = Router(name="rewards")

# Apply middleware to this router (required for container injection)
rewards_router.callback_query.middleware(DatabaseMiddleware())
rewards_router.message.middleware(DatabaseMiddleware())


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _format_reward_status(status: RewardStatus) -> str:
    """
    Retorna el emoji apropiado para cada estado de recompensa.

    Args:
        status: Estado de la recompensa

    Returns:
        Emoji representando el estado
    """
    status_emojis = {
        RewardStatus.LOCKED: "🔒",
        RewardStatus.UNLOCKED: "✨",
        RewardStatus.CLAIMED: "✅",
        RewardStatus.EXPIRED: "⏰"
    }
    return status_emojis.get(status, "❓")


def _get_lucien_header() -> str:
    """Retorna el encabezado estándar de Lucien."""
    return "🎩 <b>Lucien:</b>"


def _get_diana_header() -> str:
    """Retorna el encabezado estándar de Diana."""
    return "🫦 <b>Diana:</b>"


def _get_rewards_header() -> str:
    """Mensaje de encabezado de la galería de recompensas."""
    return f"""{_get_lucien_header()}

<i>Bienvenido a su galería de logros...</i>

Aquí encontrará las recompensas disponibles y su progreso."""


def _get_empty_rewards_message() -> str:
    """Mensaje cuando no hay recompensas configuradas."""
    return f"""{_get_lucien_header()}

<i>Oh... parece que nuestra galería de logros está momentáneamente vacía.</i>

<i>Diana está preparando nuevas recompensas. Vuelva más tarde.</i>"""


def _get_reward_claimed_message(reward_name: str, reward_type: RewardType, reward_result: dict) -> str:
    """
    Mensaje de éxito al reclamar recompensa (voz de Diana).

    Args:
        reward_name: Nombre de la recompensa
        reward_type: Tipo de recompensa
        reward_result: Resultado del reclamo

    Returns:
        Mensaje con voz de Diana
    """
    base_msg = f"""{_get_diana_header()}

<i>Así me gusta... has reclamado tu recompensa.</i>

🏆 <b>{reward_name}</b>
"""

    # Add specific details based on reward type
    if reward_type == RewardType.BESITOS:
        amount = reward_result.get("amount", 0)
        base_msg += f"\n💰 <b>+{amount} besitos</b> añadidos a tu balance"
    elif reward_type == RewardType.CONTENT:
        base_msg += "\n🎁 <b>Contenido exclusivo</b> desbloqueado"
    elif reward_type == RewardType.BADGE:
        badge_emoji = reward_result.get("emoji", "🏆")
        badge_name = reward_result.get("badge_name", "Insignia")
        base_msg += f"\n{badge_emoji} <b>{badge_name}</b> añadida a tu colección"
    elif reward_type == RewardType.VIP_EXTENSION:
        days = reward_result.get("days", 0)
        base_msg += f"\n⭐ <b>+{days} días VIP</b> añadidos"

    base_msg += "\n\n<i>Sigue así... hay más por descubrir.</i>"

    return base_msg


def _get_reward_error_message(error_code: str) -> str:
    """
    Mensaje de error al reclamar recompensa (voz de Lucien).

    Args:
        error_code: Código de error

    Returns:
        Mensaje con voz de Lucien
    """
    error_messages = {
        "reward_not_found": "La recompensa solicitada no existe.",
        "reward_inactive": "Esta recompensa no está disponible actualmente.",
        "reward_expired": "El tiempo para reclamar esta recompensa ha expirado.",
        "reward_locked": "Aún no ha desbloqueado esta recompensa.",
        "already_claimed": "Ya ha reclamado esta recompensa anteriormente.",
        "wallet_service_not_available": "El servicio de economía no está disponible.",
        "wallet_error": "Hubo un problema al procesar la recompensa."
    }

    error_text = error_messages.get(error_code, "Ha ocurrido un error inesperado.")

    return f"""{_get_lucien_header()}

<i>{error_text}</i>

<i>Por favor, inténtelo nuevamente o contacte a Diana si el problema persiste.</i>"""


def _format_reward_line(reward, user_reward, progress_info: dict) -> str:
    """
    Formatea una línea de recompensa para la lista.

    Args:
        reward: Objeto Reward
        user_reward: Objeto UserReward
        progress_info: Dict con información de progreso

    Returns:
        Texto formateado
    """
    status_emoji = _format_reward_status(user_reward.status)
    type_emoji = reward.reward_type.emoji

    line = f"{status_emoji} {type_emoji} <b>{reward.name}</b>\n"

    # Add description if available (truncated)
    if reward.description:
        desc = reward.description[:40] + "..." if len(reward.description) > 40 else reward.description
        line += f"   <i>{desc}</i>\n"

    # Add value info
    if reward.reward_type == RewardType.BESITOS:
        amount = reward.reward_value.get("amount", 0)
        line += f"   💰 +{amount} besitos"
    elif reward.reward_type == RewardType.VIP_EXTENSION:
        days = reward.reward_value.get("days", 0)
        line += f"   ⭐ +{days} días VIP"
    elif reward.reward_type == RewardType.CONTENT:
        line += f"   🎁 Contenido exclusivo"
    elif reward.reward_type == RewardType.BADGE:
        badge_emoji = reward.reward_value.get("emoji", "🏆")
        line += f"   {badge_emoji} Insignia especial"

    # Add progress hint for locked rewards
    if user_reward.status == RewardStatus.LOCKED and progress_info:
        # Find first incomplete condition
        for cond_id, cond_progress in progress_info.items():
            if not cond_progress.get("passed", False):
                current = cond_progress.get("current", 0)
                required = cond_progress.get("required", "?")
                if current is not None:
                    line += f"   📊 ({current}/{required})"
                break

    return line + "\n"


def get_rewards_list_keyboard(available_rewards: list) -> InlineKeyboardMarkup:
    """
    Genera teclado para la lista de recompensas.

    Args:
        available_rewards: Lista de tuplas (reward, user_reward, progress_info)

    Returns:
        InlineKeyboardMarkup con botones de reclamo
    """
    buttons = []

    # Add claim buttons for unlocked rewards
    for reward, user_reward, _ in available_rewards:
        if user_reward.status == RewardStatus.UNLOCKED:
            buttons.append([InlineKeyboardButton(
                text=f"✨ Reclamar: {reward.name}",
                callback_data=f"claim_reward:{reward.id}"
            )])

    # Add view all button
    buttons.append([InlineKeyboardButton(
        text="🔄 Ver todas las recompensas",
        callback_data="my_rewards"
    )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_reward_detail_keyboard(reward_id: int, status: RewardStatus) -> InlineKeyboardMarkup:
    """
    Genera teclado para detalle de recompensa.

    Args:
        reward_id: ID de la recompensa
        status: Estado actual de la recompensa

    Returns:
        InlineKeyboardMarkup
    """
    buttons = []

    if status == RewardStatus.UNLOCKED:
        buttons.append([InlineKeyboardButton(
            text="✨ Reclamar recompensa",
            callback_data=f"claim_reward:{reward_id}"
        )])

    buttons.append([InlineKeyboardButton(
        text="🔙 Volver a la lista",
        callback_data="my_rewards"
    )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================================================
# HANDLERS
# ============================================================================

@rewards_router.message(Command("rewards"))
@rewards_router.callback_query(F.data == "my_rewards")
async def rewards_list_handler(
    event: Message | CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """
    Handler para mostrar lista de recompensas disponibles.

    Command: /rewards
    Callback: my_rewards

    Muestra todas las recompensas con su estado (🔒 bloqueada, ✨ desbloqueada, ✅ reclamada)
    y permite reclamar las desbloqueadas.
    """
    user_id = event.from_user.id

    logger.info(f"🏆 Usuario {user_id} viendo recompensas")

    try:
        # Get available rewards
        available_rewards = await container.reward.get_available_rewards(user_id)

        if not available_rewards:
            # No rewards configured
            text = _get_empty_rewards_message()
            keyboard = None
        else:
            # Build message
            text = _get_rewards_header() + "\n\n"

            # Add each reward
            for reward, user_reward, progress_info in available_rewards:
                text += _format_reward_line(reward, user_reward, progress_info)

            # Add footer hint
            text += "\n<i>Toque 'Reclamar' para recibir una recompensa desbloqueada.</i>"

            # Build keyboard
            keyboard = get_rewards_list_keyboard(available_rewards)

        # Send/update message
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
            await event.answer()
        else:
            await event.answer(text=text, reply_markup=keyboard, parse_mode="HTML")

        logger.debug(f"✅ Rewards list shown to user {user_id}: {len(available_rewards)} rewards")

    except Exception as e:
        logger.error(f"❌ Error mostrando recompensas a usuario {user_id}: {e}", exc_info=True)
        error_text = f"{_get_lucien_header()}\n\n<i>Ha ocurrido un inconveniente al cargar sus recompensas...</i>"

        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text=error_text, parse_mode="HTML")
            await event.answer()
        else:
            await event.answer(text=error_text, parse_mode="HTML")


@rewards_router.callback_query(F.data.startswith("claim_reward:"))
async def reward_claim_handler(
    callback: CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """
    Handler para procesar el reclamo de una recompensa.

    Callback data: "claim_reward:{reward_id}"

    Procesa el reclamo y muestra mensaje de éxito (voz Diana) o error (voz Lucien).
    """
    user_id = callback.from_user.id

    try:
        # Extract reward_id
        parts = callback.data.split(":")
        reward_id = int(parts[1])

        logger.info(f"🏆 Usuario {user_id} reclamando recompensa {reward_id}")

        # Process claim
        success, message, details = await container.reward.claim_reward(user_id, reward_id)

        if success and details:
            reward = details.get("reward")
            reward_result = details.get("reward_result", {})

            # Success - show with Diana's voice
            text = _get_reward_claimed_message(
                reward_name=reward.name,
                reward_type=reward.reward_type,
                reward_result=reward_result
            )

            # Add keyboard to view more rewards
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🏆 Ver más recompensas",
                    callback_data="my_rewards"
                )]
            ])

            await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer("✅ ¡Recompensa reclamada!")

            logger.info(f"✅ User {user_id} claimed reward {reward_id}: {reward.name}")

        else:
            # Error - show with Lucien's voice
            text = _get_reward_error_message(message)

            # Add keyboard to go back
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔙 Volver a recompensas",
                    callback_data="my_rewards"
                )]
            ])

            await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer("❌ No se pudo reclamar", show_alert=True)

            logger.warning(f"⚠️ User {user_id} failed to claim reward {reward_id}: {message}")

    except Exception as e:
        logger.error(f"❌ Error reclamando recompensa para usuario {user_id}: {e}", exc_info=True)

        text = _get_reward_error_message("unknown_error")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔙 Volver a recompensas",
                callback_data="my_rewards"
            )]
        ])

        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer("❌ Error al reclamar", show_alert=True)


@rewards_router.callback_query(F.data.startswith("reward_detail:"))
async def reward_detail_handler(
    callback: CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """
    Handler para mostrar detalle de una recompensa específica.

    Callback data: "reward_detail:{reward_id}"

    Muestra información detallada incluyendo condiciones y progreso.
    """
    user_id = callback.from_user.id

    try:
        # Extract reward_id
        parts = callback.data.split(":")
        reward_id = int(parts[1])

        # Get available rewards and find the specific one
        available_rewards = await container.reward.get_available_rewards(user_id)

        target_reward = None
        target_user_reward = None
        target_progress = None

        for reward, user_reward, progress_info in available_rewards:
            if reward.id == reward_id:
                target_reward = reward
                target_user_reward = user_reward
                target_progress = progress_info
                break

        if not target_reward:
            await callback.answer("❌ Recompensa no encontrada", show_alert=True)
            return

        # Build detailed message
        status_emoji = _format_reward_status(target_user_reward.status)
        type_emoji = target_reward.reward_type.emoji

        text = f"""{_get_lucien_header()}

{status_emoji} {type_emoji} <b>{target_reward.name}</b>

<i>{target_reward.description or 'Sin descripción'}</i>

<b>Estado:</b> {target_user_reward.status.value}
"""

        # Add conditions info
        if target_progress:
            text += "\n<b>Condiciones:</b>\n"
            for cond_id, cond_progress in target_progress.items():
                passed = cond_progress.get("passed", False)
                cond_emoji = "✅" if passed else "⏳"
                current = cond_progress.get("current", "?")
                required = cond_progress.get("required", "?")
                cond_type = cond_progress.get("condition_type", "unknown")

                text += f"{cond_emoji} {cond_type}: {current}/{required}\n"

        # Add reward value info
        text += "\n<b>Recompensa:</b>\n"
        if target_reward.reward_type == RewardType.BESITOS:
            amount = target_reward.reward_value.get("amount", 0)
            text += f"💰 +{amount} besitos"
        elif target_reward.reward_type == RewardType.VIP_EXTENSION:
            days = target_reward.reward_value.get("days", 0)
            text += f"⭐ +{days} días VIP"
        elif target_reward.reward_type == RewardType.CONTENT:
            text += f"🎁 Contenido exclusivo"
        elif target_reward.reward_type == RewardType.BADGE:
            badge_emoji = target_reward.reward_value.get("emoji", "🏆")
            badge_name = target_reward.reward_value.get("badge_name", "Insignia")
            text += f"{badge_emoji} {badge_name}"

        # Build keyboard
        keyboard = get_reward_detail_keyboard(reward_id, target_user_reward.status)

        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

        logger.debug(f"✅ Reward detail shown: reward={reward_id}, user={user_id}")

    except Exception as e:
        logger.error(f"❌ Error mostrando detalle de recompensa: {e}", exc_info=True)
        await callback.answer("❌ Error al cargar el detalle", show_alert=True)
