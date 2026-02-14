"""
Streak Handlers - Gestión de rachas diarias y regalo diario.

Handlers:
- cmd_daily_gift: Comando /daily_gift para verificar y reclamar regalo
- handle_claim_daily_gift: Callback para procesar reclamo del regalo

Voz: Lucien (🎩) - Formal, elegante, mayordomo
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.services.container import ServiceContainer
from bot.states.user import StreakStates
from bot.database.enums import StreakType
from bot.middlewares import DatabaseMiddleware

logger = logging.getLogger(__name__)

# Router para handlers de rachas
streak_router = Router(name="streak")

# Apply middleware to this router (required for container injection)
streak_router.callback_query.middleware(DatabaseMiddleware())


# ============================================================================
# LUC'S VOICE MESSAGES
# ============================================================================

def _get_lucien_header() -> str:
    """Retorna el encabezado estándar de Lucien."""
    return "🎩 <b>Lucien:</b>"


def _get_claim_available_message(streak: int) -> str:
    """
    Mensaje cuando el regalo está disponible para reclamar.

    Args:
        streak: Racha actual del usuario

    Returns:
        Mensaje con voz de Lucien
    """
    if streak == 0:
        streak_text = "Aún no ha comenzado su racha..."
    else:
        streak_text = f"Su racha actual es de <b>{streak} días</b>."

    return f"""{_get_lucien_header()}

<i>Ah... veo que ha venido a reclamar su recompensa diaria.</i>

{streak_text}

<i>Diana aprecia la constancia en sus visitantes...</i>"""


def _get_claim_success_message(
    streak: int,
    base: int,
    bonus: int,
    total: int
) -> str:
    """
    Mensaje de éxito al reclamar el regalo con desglose detallado.

    Args:
        streak: Nueva racha después del reclamo
        base: Cantidad base de besitos
        bonus: Bonus por racha
        total: Total recibido

    Returns:
        Mensaje con voz de Lucien y desglose
    """
    return f"""{_get_lucien_header()}
<i>Ah... Diana ha notado su constancia.</i>

🔥 <b>Racha actual:</b> {streak} días
💰 <b>Base:</b> {base} besitos
✨ <b>Bonus por racha:</b> +{bonus} besitos
─────────────────
💎 <b>Total recibido:</b> {total} besitos

<i>Excelente elección volver hoy...</i>"""


def _get_already_claimed_message(countdown_text: str) -> str:
    """
    Mensaje cuando ya se reclamó el regalo hoy.

    Args:
        countdown_text: Texto con tiempo hasta próximo reclamo

    Returns:
        Mensaje con voz de Lucien
    """
    return f"""{_get_lucien_header()}

<i>Ya ha reclamado su regalo de hoy...</i>

⏳ <b>{countdown_text}</b>

<i>La paciencia es una virtud que Diana valora.</i>"""


def _get_error_message(context: str = "") -> str:
    """
    Mensaje de error con voz de Lucien.

    Args:
        context: Contexto opcional del error

    Returns:
        Mensaje de error elegante
    """
    error_detail = f" con {context}" if context else ""
    return f"""{_get_lucien_header()}

<i>Hmm... algo inesperado ha ocurrido{error_detail}.
Permítame consultar con Diana sobre este inconveniente.</i>

<i>Mientras tanto, ¿hay algo más en lo que pueda asistirle?</i>"""


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_countdown_text(next_claim_time: datetime) -> str:
    """
    Calcula y formatea el tiempo hasta el próximo reclamo.

    Args:
        next_claim_time: Fecha/hora del próximo reclamo disponible

    Returns:
        Texto formateado: "Próximo regalo en 14h 32m"
    """
    now = datetime.utcnow()

    if now >= next_claim_time:
        return "El regalo está disponible ahora"

    remaining = next_claim_time - now
    total_seconds = int(remaining.total_seconds())

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    if hours > 0:
        return f"Próximo regalo en {hours}h {minutes}m"
    else:
        return f"Próximo regalo en {minutes}m"


def get_claim_keyboard(is_available: bool) -> Optional[InlineKeyboardMarkup]:
    """
    Genera el teclado para el comando /daily_gift.

    Args:
        is_available: Si el regalo está disponible para reclamar

    Returns:
        InlineKeyboardMarkup o None si no disponible
    """
    if not is_available:
        return None

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🎁 Reclamar regalo diario",
            callback_data="streak:claim_daily"
        )]
    ])
    return keyboard


# ============================================================================
# COMMAND HANDLER
# ============================================================================

@streak_router.message(Command("daily_gift"))
async def cmd_daily_gift(
    message: Message,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """
    Handler del comando /daily_gift.

    Comportamiento:
    - Verifica si el usuario puede reclamar el regalo diario
    - Si disponible: Muestra botón de reclamo con preview de racha
    - Si ya reclamó: Muestra cuenta regresiva hasta próximo reclamo
    - Usa voz de Lucien (🎩) para todos los mensajes

    Args:
        message: Mensaje del comando
        state: FSMContext para gestión de estados
        container: ServiceContainer con servicios
    """
    user_id = message.from_user.id

    logger.info(f"🎁 Usuario {user_id} ejecutó /daily_gift")

    try:
        # Verificar si puede reclamar
        can_claim, status = await container.streak.can_claim_daily_gift(user_id)

        # Obtener información de racha actual
        streak_info = await container.streak.get_streak_info(
            user_id=user_id,
            streak_type=StreakType.DAILY_GIFT
        )
        current_streak = streak_info.get("current_streak", 0)

        if can_claim:
            # Regalo disponible - mostrar botón de reclamo
            text = _get_claim_available_message(current_streak)
            keyboard = get_claim_keyboard(is_available=True)

            await message.answer(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )

            # Establecer estado de confirmación
            await state.set_state(StreakStates.daily_gift_confirm)

            logger.debug(f"✅ Daily gift available for user {user_id}")

        else:
            # Ya reclamado - mostrar cuenta regresiva
            next_claim_time = streak_info.get("next_claim_time")

            if next_claim_time:
                countdown = get_countdown_text(next_claim_time)
            else:
                # Calcular manualmente si no está disponible
                tomorrow = datetime.utcnow() + timedelta(days=1)
                next_claim = datetime.combine(
                    tomorrow.date(),
                    datetime.min.time()
                )
                countdown = get_countdown_text(next_claim)

            text = _get_already_claimed_message(countdown)

            await message.answer(
                text=text,
                parse_mode="HTML"
            )

            # Establecer estado de reclamado
            await state.set_state(StreakStates.daily_gift_claimed)

            logger.debug(f"⏳ Daily gift already claimed by user {user_id}")

    except Exception as e:
        logger.error(f"❌ Error en /daily_gift para usuario {user_id}: {e}", exc_info=True)

        await message.answer(
            text=_get_error_message("al verificar su regalo diario"),
            parse_mode="HTML"
        )


# ============================================================================
# CALLBACK HANDLER
# ============================================================================

@streak_router.callback_query(lambda c: c.data == "streak:claim_daily")
async def handle_claim_daily_gift(
    callback: CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """
    Handler para procesar el reclamo del regalo diario.

    Callback data: "streak:claim_daily"

    Comportamiento:
    - Procesa el reclamo vía streak_service.claim_daily_gift
    - En éxito: Muestra desglose detallado (base + bonus = total)
    - En ya reclamado: Muestra cuenta regresiva
    - En error: Muestra mensaje de error de Lucien

    Args:
        callback: Callback query del botón
        state: FSMContext para gestión de estados
        container: ServiceContainer con servicios
    """
    user_id = callback.from_user.id

    logger.info(f"🎁 Usuario {user_id} solicitó reclamar regalo diario")

    try:
        # Procesar reclamo
        success, result = await container.streak.claim_daily_gift(user_id)

        if success and result.get("success"):
            # Check for unlocked rewards after claiming daily gift
            unlocked_rewards = await container.reward.check_rewards_on_event(
                user_id=user_id,
                event_type="daily_gift_claimed"
            )

            # Build base success message
            base_text = _get_claim_success_message(
                streak=result.get("new_streak", 1),
                base=result.get("base_amount", 20),
                bonus=result.get("streak_bonus", 0),
                total=result.get("total", 20)
            )

            # Build keyboard
            keyboard_buttons = []

            # If rewards unlocked, add grouped notification
            if unlocked_rewards:
                notification = container.reward.build_reward_notification(
                    unlocked_rewards,
                    event_context="daily_gift"
                )

                # Combine messages
                combined_text = f"""{_get_lucien_header()}
<i>Ah... Diana ha notado su constancia.</i>

🔥 <b>Racha actual:</b> {result.get('new_streak', 1)} días
💰 <b>Base:</b> {result.get('base_amount', 20)} besitos
✨ <b>Bonus por racha:</b> +{result.get('streak_bonus', 0)} besitos
─────────────────
💎 <b>Total recibido:</b> {result.get('total', 20)} besitos

✨ <b>Nuevas Recompensas Desbloqueadas:</b>
"""
                for reward_info in unlocked_rewards:
                    reward = reward_info["reward"]
                    combined_text += f"• {reward.name}\n"

                combined_text += "\n<i>Su constancia tiene su recompensa.</i>"

                # Add claim rewards button
                keyboard_buttons.append([InlineKeyboardButton(
                    text="🏆 Reclamar Recompensas",
                    callback_data="my_rewards"
                )])

                text = combined_text
            else:
                text = base_text

            # Add view all rewards button
            keyboard_buttons.append([InlineKeyboardButton(
                text="📜 Ver Todas las Recompensas",
                callback_data="my_rewards"
            )])

            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons) if keyboard_buttons else None

            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )

            # Establecer estado de reclamado
            await state.set_state(StreakStates.daily_gift_claimed)

            # Responder al callback
            await callback.answer(
                f"✅ ¡+{result.get('total', 20)} besitos recibidos!",
                show_alert=False
            )

            logger.info(
                f"✅ User {user_id} claimed daily gift: "
                f"{result.get('total')} besitos "
                f"(base={result.get('base_amount')}, "
                f"bonus={result.get('streak_bonus')}, "
                f"streak={result.get('new_streak')})"
            )

            if unlocked_rewards:
                logger.info(
                    f"✅ User {user_id} unlocked {len(unlocked_rewards)} rewards from daily gift"
                )

        elif result.get("error") == "already_claimed":
            # Ya reclamado - mostrar cuenta regresiva
            streak_info = await container.streak.get_streak_info(
                user_id=user_id,
                streak_type=StreakType.DAILY_GIFT
            )
            next_claim_time = streak_info.get("next_claim_time")

            if next_claim_time:
                countdown = get_countdown_text(next_claim_time)
            else:
                tomorrow = datetime.utcnow() + timedelta(days=1)
                next_claim = datetime.combine(
                    tomorrow.date(),
                    datetime.min.time()
                )
                countdown = get_countdown_text(next_claim)

            text = _get_already_claimed_message(countdown)

            await callback.message.edit_text(
                text=text,
                parse_mode="HTML"
            )

            await state.set_state(StreakStates.daily_gift_claimed)

            await callback.answer(
                "⏳ Ya reclamaste hoy",
                show_alert=True
            )

            logger.debug(f"⏳ User {user_id} tried to claim already claimed gift")

        else:
            # Error en el reclamo
            error_msg = result.get("error", "unknown_error")
            logger.error(f"❌ Claim failed for user {user_id}: {error_msg}")

            await callback.message.edit_text(
                text=_get_error_message("al procesar su reclamo"),
                parse_mode="HTML"
            )

            await callback.answer(
                "❌ Error al reclamar",
                show_alert=True
            )

    except Exception as e:
        logger.error(f"❌ Error en claim_daily_gift para usuario {user_id}: {e}", exc_info=True)

        await callback.message.edit_text(
            text=_get_error_message("al procesar su reclamo"),
            parse_mode="HTML"
        )

        await callback.answer(
            "❌ Error al reclamar",
            show_alert=True
        )
