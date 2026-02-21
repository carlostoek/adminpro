"""
User Gamification Profile Handler - Admin user lookup and profile viewing.

Handlers for administrators to view any user's complete gamification profile
including balance, streaks, transaction history, rewards, and purchases.

All messages use Lucien's voice (🎩) for consistency.
"""
import logging
from datetime import datetime
from typing import Optional

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.main import admin_router
from bot.services.container import ServiceContainer
from bot.database.models import User
from bot.database.enums import StreakType, TransactionType, RewardStatus
from bot.states.admin import UserLookupState
from bot.utils.keyboards import create_inline_keyboard

logger = logging.getLogger(__name__)

# Create router for user gamification handlers
user_gamification_router = Router(name="user_gamification")


# ===== HELPER FUNCTIONS =====

def format_transaction_type(tx_type: TransactionType) -> str:
    """Format transaction type to human-readable string."""
    type_names = {
        TransactionType.EARN_REACTION: "Reacción",
        TransactionType.EARN_DAILY: "Regalo diario",
        TransactionType.EARN_SHOP_REFUND: "Reembolso tienda",
        TransactionType.EARN_ADMIN: "Crédito admin",
        TransactionType.EARN_REWARD: "Recompensa",
        TransactionType.SPEND_SHOP: "Compra tienda",
        TransactionType.SPEND_ADMIN: "Débito admin",
    }
    return type_names.get(tx_type, tx_type.value)


def format_datetime(dt: Optional[datetime]) -> str:
    """Format datetime for display."""
    if dt is None:
        return "N/A"
    return dt.strftime("%d/%m/%Y %H:%M")


def get_transaction_emoji(amount: int) -> str:
    """Get emoji for transaction based on amount."""
    return "➕" if amount > 0 else "➖"


async def get_user_by_id_or_username(
    session: AsyncSession,
    input_text: str
) -> Optional[User]:
    """
    Get user by ID or username.

    Args:
        session: Database session
        input_text: User ID (numeric) or username (with or without @)

    Returns:
        User object if found, None otherwise
    """
    if input_text.isdigit():
        result = await session.execute(
            select(User).where(User.user_id == int(input_text))
        )
    else:
        username = input_text.lstrip('@')
        result = await session.execute(
            select(User).where(User.username == username)
        )
    return result.scalar_one_or_none()


# ===== USER LOOKUP HANDLER =====

@admin_router.callback_query(F.data == "admin:user:lookup")
async def callback_user_lookup(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Handler for user lookup - prompts admin to enter user ID or username.

    Args:
        callback: Callback query
        state: FSM context for state management
        session: Database session
    """
    logger.debug(f"User lookup initiated by admin {callback.from_user.id}")

    # Set state to wait for user input
    await state.set_state(UserLookupState.waiting_for_user)

    text = (
        "🎩 <b>Lucien:</b>\n\n"
        "<i>¿A qué huésped desea consultar?</i>\n\n"
        "Por favor, ingrese el <b>ID de usuario</b> o el <b>@username</b>:"
    )

    keyboard = create_inline_keyboard([
        [{"text": "🔙 Cancelar", "callback_data": "admin:main"}]
    ])

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@admin_router.message(UserLookupState.waiting_for_user)
async def process_user_lookup(
    message: Message,
    state: FSMContext,
    session: AsyncSession
):
    """
    Process user lookup input and redirect to profile view.

    Args:
        message: Message with user input
        state: FSM context
        session: Database session
    """
    input_text = message.text.strip()
    logger.debug(f"Admin {message.from_user.id} looking up user: {input_text}")

    # Find user
    user = await get_user_by_id_or_username(session, input_text)

    if user is None:
        # User not found - stay in state and show error
        text = (
            "🎩 <b>Lucien:</b>\n\n"
            "<i>Lo siento, no he encontrado ningún huésped con ese identificador.</i>\n\n"
            "Por favor, verifique e intente nuevamente:\n"
            "• ID numérico (ej: <code>123456789</code>)\n"
            "• Username (ej: <code>@usuario</code> o <code>usuario</code>)"
        )

        keyboard = create_inline_keyboard([
            [{"text": "🔙 Cancelar", "callback_data": "admin:main"}]
        ])

        await message.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return

    # Clear state and show profile
    await state.clear()

    # Redirect to profile view
    await show_user_profile(message, session, user.user_id, is_new_message=True)


# ===== USER PROFILE HANDLER =====

async def show_user_profile(
    message_or_callback,
    session: AsyncSession,
    user_id: int,
    is_new_message: bool = False
):
    """
    Show complete gamification profile for a user.

    Args:
        message_or_callback: Message or CallbackQuery object
        session: Database session
        user_id: Target user ID
        is_new_message: Whether to send a new message or edit existing
    """
    container = ServiceContainer(session, message_or_callback.bot)

    # Get user info
    result = await session.execute(
        select(User).where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        text = (
            "🎩 <b>Lucien:</b>\n\n"
            "<i>El huésped ya no existe en nuestros registros.</i>"
        )
        keyboard = create_inline_keyboard([
            [{"text": "🔙 Volver", "callback_data": "admin:main"}]
        ])

        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await message_or_callback.answer()
        else:
            await message_or_callback.answer(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        return

    # Gather all user data
    profile = await container.wallet.get_profile(user_id)

    # Streaks
    daily_streak = await container.streak.get_streak_info(user_id, StreakType.DAILY_GIFT)
    reaction_streak = await container.streak.get_streak_info(user_id, StreakType.REACTION)

    # Stats
    reward_stats = await container.reward.get_user_reward_stats(user_id)
    shop_stats = await container.shop.get_user_shop_stats(user_id)

    # Format profile data
    balance = profile.balance if profile else 0
    total_earned = profile.total_earned if profile else 0
    total_spent = profile.total_spent if profile else 0
    level = profile.level if profile else 1

    text = (
        f"🎩 <b>Perfil de Gamificación</b>\n\n"
        f"<b>👤 Usuario:</b> {user.full_name}\n"
        f"<b>ID:</b> <code>{user.user_id}</code>\n"
        f"<b>Username:</b> @{user.username or 'N/A'}\n"
        f"<b>Rol:</b> {user.role.value if user.role else 'N/A'}\n\n"
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"┃ <b>💰 ECONOMÍA</b>\n"
        f"┣━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"┃ Balance: <b>{balance}</b> 💰\n"
        f"┃ Total ganado: {total_earned} 💰\n"
        f"┃ Total gastado: {total_spent} 💰\n"
        f"┃ Nivel: <b>{level}</b> ⭐\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"┃ <b>🔥 RACHAS</b>\n"
        f"┣━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"┃ Regalo diario: <b>{daily_streak['current_streak']}</b> días\n"
        f"┃   (Récord: {daily_streak['longest_streak']})\n"
        f"┃ Reacciones: <b>{reaction_streak['current_streak']}</b> días\n"
        f"┃   (Récord: {reaction_streak['longest_streak']})\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"┃ <b>🏆 RECOMPENSAS</b>\n"
        f"┣━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"┃ Desbloqueadas: {reward_stats['total_unlocked']}\n"
        f"┃ Reclamadas: {reward_stats['total_claimed']}\n"
        f"┃ Disponibles: {reward_stats['currently_unlocked']}\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"┃ <b>🛍️ TIENDA</b>\n"
        f"┣━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"┃ Compras: {shop_stats['total_purchases']}\n"
        f"┃ Gastado: {shop_stats['total_besitos_spent']} 💰\n"
        f"┃ Contenido: {shop_stats['unique_content_owned']} items\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    keyboard = create_inline_keyboard([
        [{"text": "📜 Transacciones", "callback_data": f"admin:user:transactions:{user_id}:1"}],
        [{"text": "🏆 Recompensas", "callback_data": f"admin:user:rewards:{user_id}"}],
        [{"text": "🛍️ Compras", "callback_data": f"admin:user:purchases:{user_id}:1"}],
        [{"text": "🔍 Otro Usuario", "callback_data": "admin:user:lookup"}],
        [{"text": "🔙 Volver", "callback_data": "admin:main"}],
    ])

    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await message_or_callback.answer()
    else:
        await message_or_callback.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )


@admin_router.callback_query(F.data.startswith("admin:user:profile:"))
async def callback_user_profile(callback: CallbackQuery, session: AsyncSession):
    """
    Handler to show user profile from callback.

    Args:
        callback: Callback query with user_id in data
        session: Database session
    """
    # Extract user_id from callback data
    parts = callback.data.split(":")
    if len(parts) < 4:
        await callback.answer("❌ Datos inválidos", show_alert=True)
        return

    try:
        user_id = int(parts[3])
    except ValueError:
        await callback.answer("❌ ID de usuario inválido", show_alert=True)
        return

    await show_user_profile(callback, session, user_id)


# ===== TRANSACTIONS HANDLER =====

@admin_router.callback_query(F.data.startswith("admin:user:transactions:"))
async def callback_user_transactions(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Handler to show paginated transaction history for a user.

    Args:
        callback: Callback query with user_id and page in data
        session: Database session
    """
    # Extract user_id and page from callback data
    parts = callback.data.split(":")
    if len(parts) < 5:
        await callback.answer("❌ Datos inválidos", show_alert=True)
        return

    try:
        user_id = int(parts[3])
        page = int(parts[4]) if len(parts) > 4 else 1
    except ValueError:
        await callback.answer("❌ Datos inválidos", show_alert=True)
        return

    container = ServiceContainer(session, callback.bot)

    # Get paginated transactions
    transactions, total = await container.wallet.get_transaction_history(
        user_id=user_id, page=page, per_page=10
    )

    total_pages = max(1, (total + 9) // 10)

    # Build transaction list
    tx_lines = []
    for tx in transactions:
        emoji = get_transaction_emoji(tx.amount)
        tx_type = format_transaction_type(tx.type)
        date_str = format_datetime(tx.created_at)
        tx_lines.append(
            f"{emoji} <b>{abs(tx.amount)}</b> 💰 - {tx_type}\n"
            f"<i>{tx.reason or 'Sin descripción'}</i>\n"
            f"<code>{date_str}</code>\n"
            f"---"
        )

    tx_text = "\n".join(tx_lines) if tx_lines else "<i>No hay transacciones registradas.</i>"

    text = (
        f"🎩 <b>Historial de Transacciones</b>\n"
        f"Usuario: <code>{user_id}</code> | Página {page}/{total_pages}\n\n"
        f"{tx_text}"
    )

    # Build pagination keyboard
    keyboard_buttons = []

    # Pagination row
    pagination_row = []
    if page > 1:
        pagination_row.append({
            "text": "⬅️",
            "callback_data": f"admin:user:transactions:{user_id}:{page - 1}"
        })
    if page < total_pages:
        pagination_row.append({
            "text": "➡️",
            "callback_data": f"admin:user:transactions:{user_id}:{page + 1}"
        })
    if pagination_row:
        keyboard_buttons.append(pagination_row)

    keyboard_buttons.append([
        {"text": "🔙 Perfil", "callback_data": f"admin:user:profile:{user_id}"}
    ])

    keyboard = create_inline_keyboard(keyboard_buttons)

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


# ===== REWARDS HANDLER =====

@admin_router.callback_query(F.data.startswith("admin:user:rewards:"))
async def callback_user_rewards(callback: CallbackQuery, session: AsyncSession):
    """
    Handler to show user's rewards status.

    Args:
        callback: Callback query with user_id in data
        session: Database session
    """
    # Extract user_id from callback data
    parts = callback.data.split(":")
    if len(parts) < 4:
        await callback.answer("❌ Datos inválidos", show_alert=True)
        return

    try:
        user_id = int(parts[3])
    except ValueError:
        await callback.answer("❌ ID de usuario inválido", show_alert=True)
        return

    container = ServiceContainer(session, callback.bot)

    # Get available rewards (including secret ones for admin view)
    rewards_data = await container.reward.get_available_rewards(user_id, include_secret=True)

    # Categorize rewards
    unlocked = []
    locked = []
    claimed = []

    for reward, user_reward, progress in rewards_data:
        if user_reward.status == RewardStatus.CLAIMED:
            claimed.append((reward, user_reward, progress))
        elif user_reward.status == RewardStatus.UNLOCKED:
            unlocked.append((reward, user_reward, progress))
        else:
            locked.append((reward, user_reward, progress))

    # Build sections
    sections = []

    # Unlocked section
    if unlocked:
        lines = ["<b>Disponibles para reclamar:</b>"]
        for reward, user_reward, progress in unlocked:
            lines.append(f"🔓 {reward.name}")
        sections.append("\n".join(lines))

    # Locked section
    if locked:
        lines = ["<b>Bloqueadas:</b>"]
        for reward, user_reward, progress in locked:
            lines.append(f"🔒 {reward.name}")
        sections.append("\n".join(lines))

    # Claimed section
    if claimed:
        lines = ["<b>Reclamadas:</b>"]
        for reward, user_reward, progress in claimed:
            lines.append(f"✅ {reward.name}")
        sections.append("\n".join(lines))

    content = "\n\n".join(sections) if sections else "<i>No hay recompensas registradas.</i>"

    text = (
        f"🎩 <b>Recompensas del Usuario</b>\n"
        f"Usuario: <code>{user_id}</code>\n\n"
        f"{content}"
    )

    keyboard = create_inline_keyboard([
        [{"text": "🔙 Perfil", "callback_data": f"admin:user:profile:{user_id}"}]
    ])

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


# ===== PURCHASES HANDLER =====

@admin_router.callback_query(F.data.startswith("admin:user:purchases:"))
async def callback_user_purchases(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Handler to show paginated purchase history for a user.

    Args:
        callback: Callback query with user_id and page in data
        session: Database session
    """
    # Extract user_id and page from callback data
    parts = callback.data.split(":")
    if len(parts) < 5:
        await callback.answer("❌ Datos inválidos", show_alert=True)
        return

    try:
        user_id = int(parts[3])
        page = int(parts[4]) if len(parts) > 4 else 1
    except ValueError:
        await callback.answer("❌ Datos inválidos", show_alert=True)
        return

    container = ServiceContainer(session, callback.bot)

    # Get paginated purchases
    purchases, total = await container.shop.get_purchase_history(
        user_id=user_id, page=page, per_page=10
    )

    total_pages = max(1, (total + 9) // 10)

    # Build purchase list
    purchase_lines = []
    for purchase in purchases:
        date_str = format_datetime(purchase['accessed_at'])
        purchase_lines.append(
            f"🛍️ <b>{purchase['product_name']}</b>\n"
            f"💰 {purchase['besitos_paid']} besitos\n"
            f"📅 {date_str}\n"
            f"---"
        )

    purchases_text = "\n".join(purchase_lines) if purchase_lines else "<i>No hay compras registradas.</i>"

    text = (
        f"🎩 <b>Historial de Compras</b>\n"
        f"Usuario: <code>{user_id}</code> | Página {page}/{total_pages}\n\n"
        f"{purchases_text}"
    )

    # Build pagination keyboard
    keyboard_buttons = []

    # Pagination row
    pagination_row = []
    if page > 1:
        pagination_row.append({
            "text": "⬅️",
            "callback_data": f"admin:user:purchases:{user_id}:{page - 1}"
        })
    if page < total_pages:
        pagination_row.append({
            "text": "➡️",
            "callback_data": f"admin:user:purchases:{user_id}:{page + 1}"
        })
    if pagination_row:
        keyboard_buttons.append(pagination_row)

    keyboard_buttons.append([
        {"text": "🔙 Perfil", "callback_data": f"admin:user:profile:{user_id}"}
    ])

    keyboard = create_inline_keyboard(keyboard_buttons)

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()
