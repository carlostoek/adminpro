"""
Reward Management Handlers - Admin handlers for reward and condition management.

Handlers:
- admin:rewards - Main reward management menu
- admin:reward:list - Paginated list of rewards
- admin:reward:details:{id} - Show reward details
- admin:reward:toggle:{id} - Toggle reward active status
- admin:reward:create:start - Start reward creation flow
- admin:reward:condition:add:{id} - Add condition to reward

FSM Flows:
- RewardCreateState - Multi-step reward creation
- RewardConditionState - Inline condition creation
"""
import logging
from typing import Optional

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Reward, RewardCondition, ContentSet
from bot.database.enums import RewardType, RewardConditionType, RewardStatus
from bot.handlers.admin.main import admin_router
from bot.services.container import ServiceContainer
from bot.states.admin import RewardCreateState, RewardConditionState
from bot.utils.keyboards import create_inline_keyboard

logger = logging.getLogger(__name__)

# Create reward router
reward_router = Router(name="reward_management")


# ===== HELPER FUNCTIONS =====

def format_reward_value(reward_type: RewardType, value: dict) -> str:
    """Format reward value for display."""
    if reward_type == RewardType.BESITOS:
        return f"💰 {value.get('amount', 0)} besitos"
    elif reward_type == RewardType.CONTENT:
        return f"🎁 ContentSet #{value.get('content_set_id', 'N/A')}"
    elif reward_type == RewardType.BADGE:
        emoji = value.get('emoji', '🏆')
        name = value.get('badge_name', 'Unknown')
        return f"{emoji} {name}"
    elif reward_type == RewardType.VIP_EXTENSION:
        return f"⭐ {value.get('days', 0)} días VIP"
    return "Unknown"


def get_condition_type_display(condition_type: RewardConditionType) -> str:
    """Get human-readable condition name."""
    return condition_type.display_name


def validate_condition_value(condition_type: RewardConditionType, value: int) -> tuple[bool, str]:
    """Validate condition value ranges."""
    if condition_type == RewardConditionType.STREAK_LENGTH:
        if not 1 <= value <= 365:
            return False, "Racha debe ser entre 1 y 365 días"
    elif condition_type == RewardConditionType.TOTAL_POINTS:
        if not 1 <= value <= 100000:
            return False, "Puntos totales debe ser entre 1 y 100,000"
    elif condition_type == RewardConditionType.LEVEL_REACHED:
        if not 1 <= value <= 100:
            return False, "Nivel debe ser entre 1 y 100"
    elif condition_type == RewardConditionType.BESITOS_SPENT:
        if not 1 <= value <= 100000:
            return False, "Besitos gastados debe ser entre 1 y 100,000"
    return True, ""


def get_reward_status_emoji(is_active: bool, is_secret: bool) -> str:
    """Get status emoji for reward."""
    if is_secret:
        return "🔒"
    return "🟢" if is_active else "🔴"


# ===== MAIN MENU HANDLER =====

@reward_router.callback_query(F.data == "admin:rewards")
async def callback_rewards_menu(callback: CallbackQuery):
    """Handler for reward management main menu."""
    text = (
        "🎩 <b>Gestión de Recompensas</b>\n\n"
        "<b>Acciones disponibles:</b>\n"
        "• Crear nueva recompensa\n"
        "• Ver/Editar recompensas\n"
        "• Gestionar condiciones\n\n"
        "<i>Seleccione una opción...</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "➕ Crear Recompensa", "callback_data": "admin:reward:create:start"}],
        [{"text": "📋 Listar Recompensas", "callback_data": "admin:reward:list"}],
        [{"text": "🔙 Volver", "callback_data": "admin:main"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# ===== LIST REWARDS HANDLER =====

@reward_router.callback_query(F.data == "admin:reward:list")
async def callback_reward_list(callback: CallbackQuery, session: AsyncSession):
    """Handler for paginated reward list."""
    # Get all rewards with condition count
    result = await session.execute(
        select(Reward).order_by(Reward.sort_order, Reward.id)
    )
    rewards = list(result.scalars().all())

    if not rewards:
        text = (
            "🎩 <b>Gestión de Recompensas</b>\n\n"
            "<i>No hay recompensas configuradas.</i>\n\n"
            "Use 'Crear Recompensa' para agregar una."
        )
        keyboard = create_inline_keyboard([
            [{"text": "➕ Crear Recompensa", "callback_data": "admin:reward:create:start"}],
            [{"text": "🔙 Volver", "callback_data": "admin:rewards"}],
        ])
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        return

    # Build list text
    text = "🎩 <b>Lista de Recompensas</b>\n\n"

    for reward in rewards:
        type_emoji = reward.reward_type.emoji
        status_emoji = get_reward_status_emoji(reward.is_active, reward.is_secret)
        condition_count = len(reward.conditions)

        text += f"{type_emoji} <b>{reward.name}</b> {status_emoji}\n"
        text += f"   ({condition_count} cond.)\n\n"

    # Build keyboard with reward buttons
    keyboard_rows = []
    for reward in rewards:
        type_emoji = reward.reward_type.emoji
        status_emoji = "🟢" if reward.is_active else "🔴"

        keyboard_rows.append([
            {
                "text": f"{type_emoji} {reward.name[:20]}",
                "callback_data": f"admin:reward:details:{reward.id}"
            },
            {
                "text": status_emoji,
                "callback_data": f"admin:reward:toggle:{reward.id}"
            }
        ])

    keyboard_rows.append([{"text": "🔙 Volver", "callback_data": "admin:rewards"}])

    keyboard = create_inline_keyboard(keyboard_rows)

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# ===== REWARD DETAILS HANDLER =====

@reward_router.callback_query(F.data.startswith("admin:reward:details:"))
async def callback_reward_details(callback: CallbackQuery, session: AsyncSession):
    """Handler for reward details view."""
    try:
        reward_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    reward = await session.get(Reward, reward_id)
    if not reward:
        await callback.answer("❌ Recompensa no encontrada", show_alert=True)
        return

    # Format reward details
    type_emoji = reward.reward_type.emoji
    status_text = "Activa" if reward.is_active else "Inactiva"
    repeatable_text = "Sí" if reward.is_repeatable else "No"
    secret_text = "Sí" if reward.is_secret else "No"
    value_text = format_reward_value(reward.reward_type, reward.reward_value)

    text = (
        f"🎩 <b>Detalles de Recompensa</b>\n\n"
        f"<b>Nombre:</b> {reward.name}\n"
        f"<b>Descripción:</b> {reward.description or 'N/A'}\n"
        f"<b>Tipo:</b> {type_emoji} {reward.reward_type.display_name}\n"
        f"<b>Valor:</b> {value_text}\n"
        f"<b>Repetible:</b> {repeatable_text}\n"
        f"<b>Secreta:</b> {secret_text}\n"
        f"<b>Ventana:</b> {reward.claim_window_hours} horas\n"
        f"<b>Estado:</b> {status_text}\n"
        f"<b>Orden:</b> {reward.sort_order}\n\n"
        f"<b>Condiciones ({len(reward.conditions)}):</b>\n"
    )

    for condition in reward.conditions:
        cond_name = get_condition_type_display(condition.condition_type)
        if condition.condition_value is not None:
            text += f"• {cond_name}: {condition.condition_value}\n"
        else:
            text += f"• {cond_name}\n"

    toggle_text = "Desactivar" if reward.is_active else "Activar"

    keyboard = create_inline_keyboard([
        [{"text": "➕ Agregar Condición", "callback_data": f"admin:reward:condition:add:{reward.id}"}],
        [{"text": f"🔄 {toggle_text}", "callback_data": f"admin:reward:toggle:{reward.id}"}],
        [{"text": "🗑️ Eliminar", "callback_data": f"admin:reward:delete:{reward.id}"}],
        [{"text": "🔙 Lista", "callback_data": "admin:reward:list"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# ===== TOGGLE REWARD HANDLER =====

@reward_router.callback_query(F.data.startswith("admin:reward:toggle:"))
async def callback_reward_toggle(callback: CallbackQuery, session: AsyncSession):
    """Handler for toggling reward active status."""
    try:
        reward_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    reward = await session.get(Reward, reward_id)
    if not reward:
        await callback.answer("❌ Recompensa no encontrada", show_alert=True)
        return

    # Toggle status
    reward.is_active = not reward.is_active
    await session.commit()

    status_text = "activada" if reward.is_active else "desactivada"
    await callback.answer(f"✅ Recompensa {status_text}")

    # Refresh details view
    await callback_reward_details(callback, session)


# ===== CREATE REWARD FLOW =====

@reward_router.callback_query(F.data == "admin:reward:create:start")
async def callback_reward_create_start(callback: CallbackQuery, state: FSMContext):
    """Start reward creation flow."""
    await state.set_state(RewardCreateState.waiting_for_name)

    text = (
        "🎩 <b>Crear Nueva Recompensa</b>\n\n"
        "<b>Paso 1/8:</b> Nombre de la recompensa\n\n"
        "Ingrese el nombre de la recompensa:\n"
        "<i>(Máximo 200 caracteres)</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "❌ Cancelar", "callback_data": "admin:rewards"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@reward_router.message(RewardCreateState.waiting_for_name)
async def process_reward_name(message: Message, state: FSMContext):
    """Process reward name input."""
    name = message.text.strip()

    if not name:
        await message.answer("🎩 <b>Error:</b> El nombre no puede estar vacío.\n\nIntente nuevamente:")
        return

    if len(name) > 200:
        await message.answer("🎩 <b>Error:</b> El nombre es demasiado largo (máx. 200 caracteres).\n\nIntente nuevamente:")
        return

    await state.update_data(name=name)
    await state.set_state(RewardCreateState.waiting_for_description)

    text = (
        f"🎩 <b>Crear Nueva Recompensa</b>\n\n"
        f"<b>Nombre:</b> {name}\n\n"
        f"<b>Paso 2/8:</b> Descripción\n\n"
        f"Ingrese la descripción de la recompensa:\n"
        f"<i>(Máximo 1000 caracteres, o envíe /skip para omitir)</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "⏭️ Saltar", "callback_data": "reward:create:skip_description"}],
        [{"text": "❌ Cancelar", "callback_data": "admin:rewards"}],
    ])

    await message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")


@reward_router.callback_query(F.data == "reward:create:skip_description")
async def callback_skip_description(callback: CallbackQuery, state: FSMContext):
    """Skip description step."""
    await state.update_data(description=None)
    await state.set_state(RewardCreateState.waiting_for_type)

    data = await state.get_data()
    name = data.get("name")

    text = (
        f"🎩 <b>Crear Nueva Recompensa</b>\n\n"
        f"<b>Nombre:</b> {name}\n"
        f"<b>Descripción:</b> <i>(sin descripción)</i>\n\n"
        f"<b>Paso 3/8:</b> Tipo de recompensa\n\n"
        f"Seleccione el tipo de recompensa:"
    )

    keyboard = create_inline_keyboard([
        [{"text": "💰 Besitos", "callback_data": "reward_type:BESITOS"}],
        [{"text": "🎁 Contenido", "callback_data": "reward_type:CONTENT"}],
        [{"text": "🏆 Insignia", "callback_data": "reward_type:BADGE"}],
        [{"text": "⭐ Extensión VIP", "callback_data": "reward_type:VIP_EXTENSION"}],
        [{"text": "❌ Cancelar", "callback_data": "admin:rewards"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@reward_router.message(RewardCreateState.waiting_for_description)
async def process_reward_description(message: Message, state: FSMContext):
    """Process reward description input."""
    description = message.text.strip()

    if len(description) > 1000:
        await message.answer("🎩 <b>Error:</b> La descripción es demasiado larga (máx. 1000 caracteres).\n\nIntente nuevamente:")
        return

    await state.update_data(description=description)
    await state.set_state(RewardCreateState.waiting_for_type)

    data = await state.get_data()
    name = data.get("name")

    text = (
        f"🎩 <b>Crear Nueva Recompensa</b>\n\n"
        f"<b>Nombre:</b> {name}\n"
        f"<b>Descripción:</b> {description[:50]}{'...' if len(description) > 50 else ''}\n\n"
        f"<b>Paso 3/8:</b> Tipo de recompensa\n\n"
        f"Seleccione el tipo de recompensa:"
    )

    keyboard = create_inline_keyboard([
        [{"text": "💰 Besitos", "callback_data": "reward_type:BESITOS"}],
        [{"text": "🎁 Contenido", "callback_data": "reward_type:CONTENT"}],
        [{"text": "🏆 Insignia", "callback_data": "reward_type:BADGE"}],
        [{"text": "⭐ Extensión VIP", "callback_data": "reward_type:VIP_EXTENSION"}],
        [{"text": "❌ Cancelar", "callback_data": "admin:rewards"}],
    ])

    await message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")


@reward_router.callback_query(F.data.startswith("reward_type:"))
async def callback_reward_type_selected(callback: CallbackQuery, state: FSMContext):
    """Handle reward type selection."""
    reward_type_str = callback.data.split(":")[-1]
    reward_type = RewardType(reward_type_str)

    await state.update_data(reward_type=reward_type_str)

    data = await state.get_data()
    name = data.get("name")

    type_names = {
        RewardType.BESITOS: "💰 Besitos",
        RewardType.CONTENT: "🎁 Contenido",
        RewardType.BADGE: "🏆 Insignia",
        RewardType.VIP_EXTENSION: "⭐ Extensión VIP",
    }

    if reward_type == RewardType.BESITOS:
        await state.set_state(RewardCreateState.waiting_for_besitos_amount)
        text = (
            f"🎩 <b>Crear Nueva Recompensa</b>\n\n"
            f"<b>Nombre:</b> {name}\n"
            f"<b>Tipo:</b> {type_names[reward_type]}\n\n"
            f"<b>Paso 4/8:</b> Cantidad de besitos\n\n"
            f"Ingrese la cantidad de besitos (10-1000):"
        )
    elif reward_type == RewardType.CONTENT:
        await state.set_state(RewardCreateState.waiting_for_content_set)
        # Get available content sets
        session = callback.bot.get("session")
        result = await session.execute(
            select(ContentSet).where(ContentSet.is_active == True).order_by(ContentSet.name)
        )
        content_sets = list(result.scalars().all())

        if not content_sets:
            await callback.answer("❌ No hay ContentSets disponibles", show_alert=True)
            return

        text = (
            f"🎩 <b>Crear Nueva Recompensa</b>\n\n"
            f"<b>Nombre:</b> {name}\n"
            f"<b>Tipo:</b> {type_names[reward_type]}\n\n"
            f"<b>Paso 4/8:</b> Seleccione ContentSet:\n\n"
        )

        keyboard_rows = []
        for cs in content_sets[:10]:  # Limit to 10
            keyboard_rows.append([
                {"text": cs.name, "callback_data": f"reward_content_set:{cs.id}"}
            ])
        keyboard_rows.append([{"text": "❌ Cancelar", "callback_data": "admin:rewards"}])

        keyboard = create_inline_keyboard(keyboard_rows)
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        return
    elif reward_type == RewardType.BADGE:
        await state.set_state(RewardCreateState.waiting_for_badge_name)
        text = (
            f"🎩 <b>Crear Nueva Recompensa</b>\n\n"
            f"<b>Nombre:</b> {name}\n"
            f"<b>Tipo:</b> {type_names[reward_type]}\n\n"
            f"<b>Paso 4/8:</b> Nombre de la insignia\n\n"
            f"Ingrese el nombre de la insignia:"
        )
    elif reward_type == RewardType.VIP_EXTENSION:
        await state.set_state(RewardCreateState.waiting_for_vip_days)
        text = (
            f"🎩 <b>Crear Nueva Recompensa</b>\n\n"
            f"<b>Nombre:</b> {name}\n"
            f"<b>Tipo:</b> {type_names[reward_type]}\n\n"
            f"<b>Paso 4/8:</b> Días de extensión VIP\n\n"
            f"Ingrese los días de extensión VIP (1-30):"
        )

    keyboard = create_inline_keyboard([
        [{"text": "❌ Cancelar", "callback_data": "admin:rewards"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@reward_router.message(RewardCreateState.waiting_for_besitos_amount)
async def process_besitos_amount(message: Message, state: FSMContext):
    """Process besitos amount input."""
    try:
        amount = int(message.text.strip())
        if not 10 <= amount <= 1000:
            raise ValueError("Out of range")
    except ValueError:
        await message.answer("🎩 <b>Error:</b> Ingrese un número válido entre 10 y 1000:")
        return

    await state.update_data(reward_value={"amount": amount})
    await show_behavior_config(message, state)


@reward_router.callback_query(F.data.startswith("reward_content_set:"))
async def callback_content_set_selected(callback: CallbackQuery, state: FSMContext):
    """Handle content set selection."""
    try:
        content_set_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    await state.update_data(reward_value={"content_set_id": content_set_id})
    await show_behavior_config(callback.message, state, edit=True)
    await callback.answer()


@reward_router.message(RewardCreateState.waiting_for_badge_name)
async def process_badge_name(message: Message, state: FSMContext):
    """Process badge name input."""
    badge_name = message.text.strip()

    if not badge_name:
        await message.answer("🎩 <b>Error:</b> El nombre no puede estar vacío.\n\nIntente nuevamente:")
        return

    await state.update_data(badge_name=badge_name)
    await state.set_state(RewardCreateState.waiting_for_badge_emoji)

    data = await state.get_data()
    name = data.get("name")

    text = (
        f"🎩 <b>Crear Nueva Recompensa</b>\n\n"
        f"<b>Nombre:</b> {name}\n"
        f"<b>Tipo:</b> 🏆 Insignia\n"
        f"<b>Nombre de insignia:</b> {badge_name}\n\n"
        f"<b>Paso 5/8:</b> Emoji de la insignia\n\n"
        f"Ingrese el emoji de la insignia (ej: 🔥):"
    )

    keyboard = create_inline_keyboard([
        [{"text": "❌ Cancelar", "callback_data": "admin:rewards"}],
    ])

    await message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")


@reward_router.message(RewardCreateState.waiting_for_badge_emoji)
async def process_badge_emoji(message: Message, state: FSMContext):
    """Process badge emoji input."""
    emoji = message.text.strip()

    if not emoji:
        await message.answer("🎩 <b>Error:</b> El emoji no puede estar vacío.\n\nIntente nuevamente:")
        return

    data = await state.get_data()
    badge_name = data.get("badge_name")

    await state.update_data(reward_value={"badge_name": badge_name, "emoji": emoji})
    await show_behavior_config(message, state)


@reward_router.message(RewardCreateState.waiting_for_vip_days)
async def process_vip_days(message: Message, state: FSMContext):
    """Process VIP extension days input."""
    try:
        days = int(message.text.strip())
        if not 1 <= days <= 30:
            raise ValueError("Out of range")
    except ValueError:
        await message.answer("🎩 <b>Error:</b> Ingrese un número válido entre 1 y 30:")
        return

    await state.update_data(reward_value={"days": days})
    await show_behavior_config(message, state)


async def show_behavior_config(message_or_callback, state: FSMContext, edit: bool = False):
    """Show behavior configuration options."""
    await state.set_state(RewardCreateState.waiting_for_behavior)

    data = await state.get_data()
    name = data.get("name")
    reward_type_str = data.get("reward_type")
    reward_type = RewardType(reward_type_str)
    reward_value = data.get("reward_value", {})

    value_text = format_reward_value(reward_type, reward_value)

    text = (
        f"🎩 <b>Crear Nueva Recompensa</b>\n\n"
        f"<b>Nombre:</b> {name}\n"
        f"<b>Tipo:</b> {reward_type.emoji} {reward_type.display_name}\n"
        f"<b>Valor:</b> {value_text}\n\n"
        f"<b>Paso 6/8:</b> Configuración de comportamiento\n\n"
        f"¿Es repetible?"
    )

    keyboard = create_inline_keyboard([
        [{"text": "✅ Sí", "callback_data": "reward:repeatable:yes"},
         {"text": "❌ No", "callback_data": "reward:repeatable:no"}],
        [{"text": "❌ Cancelar", "callback_data": "admin:rewards"}],
    ])

    if edit and hasattr(message_or_callback, 'edit_text'):
        await message_or_callback.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message_or_callback.answer(text=text, reply_markup=keyboard, parse_mode="HTML")


@reward_router.callback_query(F.data.startswith("reward:repeatable:"))
async def callback_repeatable_selected(callback: CallbackQuery, state: FSMContext):
    """Handle repeatable selection."""
    is_repeatable = callback.data.split(":")[-1] == "yes"
    await state.update_data(is_repeatable=is_repeatable)
    await state.set_state(RewardCreateState.waiting_for_secret)

    data = await state.get_data()
    name = data.get("name")

    text = (
        f"🎩 <b>Crear Nueva Recompensa</b>\n\n"
        f"<b>Nombre:</b> {name}\n"
        f"<b>Repetible:</b> {'Sí' if is_repeatable else 'No'}\n\n"
        f"<b>Paso 7/8:</b> Configuración de comportamiento\n\n"
        f"¿Es secreta (oculta hasta desbloquear)?"
    )

    keyboard = create_inline_keyboard([
        [{"text": "✅ Sí", "callback_data": "reward:secret:yes"},
         {"text": "❌ No", "callback_data": "reward:secret:no"}],
        [{"text": "❌ Cancelar", "callback_data": "admin:rewards"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@reward_router.callback_query(F.data.startswith("reward:secret:"))
async def callback_secret_selected(callback: CallbackQuery, state: FSMContext):
    """Handle secret selection."""
    is_secret = callback.data.split(":")[-1] == "yes"
    await state.update_data(is_secret=is_secret)
    await state.set_state(RewardCreateState.waiting_for_claim_window)

    data = await state.get_data()
    name = data.get("name")

    text = (
        f"🎩 <b>Crear Nueva Recompensa</b>\n\n"
        f"<b>Nombre:</b> {name}\n"
        f"<b>Secreta:</b> {'Sí' if is_secret else 'No'}\n\n"
        f"<b>Paso 8/8:</b> Ventana de reclamo\n\n"
        f"Seleccione las horas disponibles para reclamar tras desbloqueo:"
    )

    keyboard = create_inline_keyboard([
        [{"text": "24h", "callback_data": "reward:window:24"},
         {"text": "72h", "callback_data": "reward:window:72"},
         {"text": "168h (7d)", "callback_data": "reward:window:168"}],
        [{"text": "❌ Cancelar", "callback_data": "admin:rewards"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@reward_router.callback_query(F.data.startswith("reward:window:"))
async def callback_window_selected(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle claim window selection and create reward."""
    try:
        window_hours = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ Valor inválido", show_alert=True)
        return

    await state.update_data(claim_window_hours=window_hours)

    data = await state.get_data()

    # Create the reward
    reward = Reward(
        name=data.get("name"),
        description=data.get("description"),
        reward_type=RewardType(data.get("reward_type")),
        reward_value=data.get("reward_value", {}),
        is_repeatable=data.get("is_repeatable", False),
        is_secret=data.get("is_secret", False),
        claim_window_hours=window_hours,
        is_active=True,
        sort_order=0
    )

    session.add(reward)
    await session.commit()
    await session.refresh(reward)

    # Clear state
    await state.clear()

    text = (
        f"🎩 <b>Recompensa Creada</b>\n\n"
        f"La recompensa <b>{reward.name}</b> ha sido creada exitosamente.\n"
        f"<b>ID:</b> {reward.id}\n\n"
        f"¿Desea agregar condiciones ahora?"
    )

    keyboard = create_inline_keyboard([
        [{"text": "➕ Agregar Condición", "callback_data": f"admin:reward:condition:add:{reward.id}"}],
        [{"text": "✅ Finalizar", "callback_data": "admin:reward:list"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer("✅ Recompensa creada")


# ===== DELETE REWARD HANDLER =====

@reward_router.callback_query(F.data.startswith("admin:reward:delete:"))
async def callback_reward_delete(callback: CallbackQuery, session: AsyncSession):
    """Handler for deleting reward with confirmation."""
    try:
        reward_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    reward = await session.get(Reward, reward_id)
    if not reward:
        await callback.answer("❌ Recompensa no encontrada", show_alert=True)
        return

    text = (
        f"🎩 <b>Confirmar Eliminación</b>\n\n"
        f"¿Está seguro de eliminar la recompensa <b>{reward.name}</b>?\n\n"
        f"<i>Esta acción no se puede deshacer.</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "✅ Sí, eliminar", "callback_data": f"admin:reward:delete:confirm:{reward.id}"}],
        [{"text": "❌ No, cancelar", "callback_data": f"admin:reward:details:{reward.id}"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@reward_router.callback_query(F.data.startswith("admin:reward:delete:confirm:"))
async def callback_reward_delete_confirm(callback: CallbackQuery, session: AsyncSession):
    """Confirm reward deletion."""
    try:
        reward_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    reward = await session.get(Reward, reward_id)
    if not reward:
        await callback.answer("❌ Recompensa no encontrada", show_alert=True)
        return

    name = reward.name
    await session.delete(reward)
    await session.commit()

    await callback.answer(f"✅ Recompensa '{name}' eliminada")

    # Return to list
    await callback_reward_list(callback, session)


# ===== CONDITION CREATION FLOW =====

@reward_router.callback_query(F.data.startswith("admin:reward:condition:add:"))
async def callback_condition_add(callback: CallbackQuery, state: FSMContext):
    """Start condition creation flow."""
    try:
        reward_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    await state.set_state(RewardConditionState.waiting_for_type)
    await state.update_data(reward_id=reward_id)

    text = (
        f"🎩 <b>Agregar Condición</b>\n\n"
        f"<b>Tipo de Condición</b>\n\n"
        f"<b>Numéricas:</b>\n"
        f"• Racha de días\n"
        f"• Puntos totales\n"
        f"• Nivel alcanzado\n"
        f"• Besitos gastados\n\n"
        f"<b>Eventos:</b>\n"
        f"• Primera compra\n"
        f"• Primer regalo diario\n"
        f"• Primera reacción\n\n"
        f"<b>Exclusión:</b>\n"
        f"• No VIP\n"
        f"• No reclamado antes"
    )

    keyboard = create_inline_keyboard([
        [{"text": "📅 Racha de días", "callback_data": "cond_type:STREAK_LENGTH"}],
        [{"text": "💯 Puntos totales", "callback_data": "cond_type:TOTAL_POINTS"}],
        [{"text": "📊 Nivel alcanzado", "callback_data": "cond_type:LEVEL_REACHED"}],
        [{"text": "💸 Besitos gastados", "callback_data": "cond_type:BESITOS_SPENT"}],
        [{"text": "🛒 Primera compra", "callback_data": "cond_type:FIRST_PURCHASE"}],
        [{"text": "🎁 Primer regalo diario", "callback_data": "cond_type:FIRST_DAILY_GIFT"}],
        [{"text": "👍 Primera reacción", "callback_data": "cond_type:FIRST_REACTION"}],
        [{"text": "🚫 No VIP", "callback_data": "cond_type:NOT_VIP"}],
        [{"text": "🔒 No reclamado antes", "callback_data": "cond_type:NOT_CLAIMED_BEFORE"}],
        [{"text": "🔙 Volver", "callback_data": f"admin:reward:details:{reward_id}"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@reward_router.callback_query(F.data.startswith("cond_type:"))
async def callback_condition_type_selected(callback: CallbackQuery, state: FSMContext):
    """Handle condition type selection."""
    condition_type_str = callback.data.split(":")[-1]
    condition_type = RewardConditionType(condition_type_str)

    await state.update_data(condition_type=condition_type_str)

    data = await state.get_data()
    reward_id = data.get("reward_id")

    if condition_type.requires_value:
        await state.set_state(RewardConditionState.waiting_for_value)

        value_prompts = {
            RewardConditionType.STREAK_LENGTH: "Ingrese valor de racha (1-365 días):",
            RewardConditionType.TOTAL_POINTS: "Ingrese puntos totales requeridos (1-100000):",
            RewardConditionType.LEVEL_REACHED: "Ingrese nivel requerido (1-100):",
            RewardConditionType.BESITOS_SPENT: "Ingrese besitos gastados requeridos (1-100000):",
        }

        text = (
            f"🎩 <b>Agregar Condición</b>\n\n"
            f"<b>Tipo:</b> {condition_type.display_name}\n\n"
            f"{value_prompts[condition_type]}"
        )

        keyboard = create_inline_keyboard([
            [{"text": "🔙 Volver", "callback_data": f"admin:reward:condition:add:{reward_id}"}],
        ])

        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    else:
        # Skip to group selection for event/exclusion types
        await state.set_state(RewardConditionState.waiting_for_group)
        await show_group_selection(callback, state)

    await callback.answer()


@reward_router.message(RewardConditionState.waiting_for_value)
async def process_condition_value(message: Message, state: FSMContext):
    """Process condition value input."""
    try:
        value = int(message.text.strip())
    except ValueError:
        await message.answer("🎩 <b>Error:</b> Ingrese un número válido:")
        return

    data = await state.get_data()
    condition_type = RewardConditionType(data.get("condition_type"))

    valid, error_msg = validate_condition_value(condition_type, value)
    if not valid:
        await message.answer(f"🎩 <b>Error:</b> {error_msg}\n\nIntente nuevamente:")
        return

    await state.update_data(condition_value=value)
    await show_group_selection(message, state)


async def show_group_selection(message_or_callback, state: FSMContext):
    """Show condition group selection."""
    await state.set_state(RewardConditionState.waiting_for_group)

    data = await state.get_data()
    condition_type_str = data.get("condition_type")
    condition_type = RewardConditionType(condition_type_str)
    condition_value = data.get("condition_value")

    text = (
        f"🎩 <b>Agregar Condición</b>\n\n"
        f"<b>Tipo:</b> {condition_type.display_name}\n"
    )

    if condition_value is not None:
        text += f"<b>Valor:</b> {condition_value}\n"

    text += (
        f"\n<b>Grupo lógico:</b>\n"
        f"Grupo 0 = AND (todas deben cumplirse)\n"
        f"Grupo 1+ = OR (al menos una del grupo)\n\n"
        f"Seleccione el grupo:"
    )

    keyboard = create_inline_keyboard([
        [
            {"text": "0 (AND)", "callback_data": "cond_group:0"},
            {"text": "1 (OR)", "callback_data": "cond_group:1"},
            {"text": "2 (OR)", "callback_data": "cond_group:2"},
        ],
        [{"text": "🔙 Volver", "callback_data": "admin:reward:list"}],
    ])

    await message_or_callback.answer(text=text, reply_markup=keyboard, parse_mode="HTML")


@reward_router.callback_query(F.data.startswith("cond_group:"))
async def callback_group_selected(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle group selection and create condition."""
    try:
        group = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ Grupo inválido", show_alert=True)
        return

    data = await state.get_data()
    reward_id = data.get("reward_id")
    condition_type = RewardConditionType(data.get("condition_type"))
    condition_value = data.get("condition_value")

    # Create condition
    condition = RewardCondition(
        reward_id=reward_id,
        condition_type=condition_type,
        condition_value=condition_value,
        condition_group=group,
        sort_order=0
    )

    session.add(condition)
    await session.commit()

    # Clear state
    await state.clear()

    text = (
        f"🎩 <b>Condición Agregada</b>\n\n"
        f"Se ha agregado la condición <b>{condition_type.display_name}</b>.\n\n"
        f"¿Agregar otra condición?"
    )

    keyboard = create_inline_keyboard([
        [{"text": "➕ Sí, agregar otra", "callback_data": f"admin:reward:condition:add:{reward_id}"}],
        [{"text": "✅ No, finalizar", "callback_data": f"admin:reward:details:{reward_id}"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer("✅ Condición agregada")


# Register router with admin router
admin_router.include_router(reward_router)
