"""
User Management Handlers - Admin interface for managing users.

Handlers for listing, viewing, searching, and changing user roles.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.enums import UserRole
from bot.middlewares import DatabaseMiddleware, AdminAuthMiddleware
from bot.services.container import ServiceContainer
from bot.states.admin import UserManagementStates
from bot.utils import CallbackParser, CallbackData

logger = logging.getLogger(__name__)

# Pagination constants
USER_LIST_PAGE_SIZE = 20

# Router for user management handlers
users_router = Router(name="admin_users")

# Apply middleware (AdminAuth already on admin_router, this integrates into it)
users_router.callback_query.middleware(DatabaseMiddleware())
users_router.message.middleware(DatabaseMiddleware())
users_router.callback_query.middleware(AdminAuthMiddleware())
users_router.message.middleware(AdminAuthMiddleware())


# ===== MENU NAVIGATION =====

@users_router.callback_query(F.data == "admin:users")
async def callback_users_menu(callback: CallbackQuery, session: AsyncSession):
    """
    Show main user management menu.

    Args:
        callback: Callback query
        session: Sesión de BD (inyectada por middleware)
    """
    logger.debug(f"👥 Admin {callback.from_user.id} opened user management menu")

    container = ServiceContainer(session, callback.bot)

    # Get user counts by role
    _, total_count = await container.user_management.get_user_list(limit=1)
    _, vip_count = await container.user_management.get_user_list(role=UserRole.VIP, limit=1)
    _, free_count = await container.user_management.get_user_list(role=UserRole.FREE, limit=1)
    _, admin_count = await container.user_management.get_user_list(role=UserRole.ADMIN, limit=1)

    # Get menu message
    text, keyboard = container.message.admin.user.users_menu(
        total_users=total_count,
        vip_count=vip_count,
        free_count=free_count,
        admin_count=admin_count,
        user_id=callback.from_user.id,
        session_history=container.session_history
    )

    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.warning(f"Could not edit message: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer()


# ===== LIST USERS =====

@users_router.callback_query(F.data.startswith("admin:users:list:"))
async def callback_users_list(callback: CallbackQuery, session: AsyncSession):
    """
    Show users list with filter.

    Callback data format: "admin:users:list:{filter_type}"

    Filters:
    - all: All users
    - vip: Only VIP users
    - free: Only Free users

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.debug(f"👥 Admin {callback.from_user.id} viewing users list")

    container = ServiceContainer(session, callback.bot)

    # Parse callback data using CallbackParser
    cb_data = CallbackParser.parse_or_none(callback.data)
    if not cb_data:
        logger.warning(f"⚠️ Invalid callback data: {callback.data}")
        await callback.answer("❌ Datos inválidos", show_alert=True)
        return

    filter_type = cb_data.get_str("filter", "all")

    # Map filter to UserRole
    role_filter = None
    if filter_type == "vip":
        role_filter = UserRole.VIP
    elif filter_type == "free":
        role_filter = UserRole.FREE

    # Get users with pagination (first page)
    users, total_count = await container.user_management.get_user_list(
        role=role_filter,
        limit=USER_LIST_PAGE_SIZE,
        offset=0,
        sort_newest_first=True
    )

    # Calculate total pages
    total_pages = (total_count + USER_LIST_PAGE_SIZE - 1) // USER_LIST_PAGE_SIZE  # Round up

    # Generate list message
    if users:
        text, keyboard = container.message.admin.user.users_list(
            users=users,
            page=1,
            total_pages=total_pages,
            filter_type=filter_type,
            total_count=total_count
        )
    else:
        # Empty list message
        text = f"👥 <b>Usuarios: {filter_type.title()}</b>\n\n<i>No hay usuarios para mostrar.</i>"
        from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(text="🔙 Volver", callback_data="admin:users:menu")
        )
        keyboard = keyboard.as_markup()

    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.warning(f"Could not edit message: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer()


# ===== PAGINATION =====

@users_router.callback_query(F.data.startswith("admin:users:page:"))
async def callback_users_page(callback: CallbackQuery, session: AsyncSession):
    """
    Show specific page of users list.

    Callback data format: "admin:users:page:{page_num}:{filter_type}"

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    container = ServiceContainer(session, callback.bot)

    # Parse callback data using CallbackParser
    cb_data = CallbackParser.parse_or_none(callback.data)
    if not cb_data:
        logger.warning(f"⚠️ Invalid callback data: {callback.data}")
        await callback.answer("❌ Datos inválidos", show_alert=True)
        return

    page = cb_data.get_int("page", 1)
    if not page or page < 1:
        logger.warning(f"⚠️ Invalid page number: {page}")
        await callback.answer("❌ Página inválida", show_alert=True)
        return

    filter_type = cb_data.get_str("filter", "all")

    # Map filter to UserRole
    role_filter = None
    if filter_type == "vip":
        role_filter = UserRole.VIP
    elif filter_type == "free":
        role_filter = UserRole.FREE

    # Get users with pagination
    offset = (page - 1) * USER_LIST_PAGE_SIZE
    users, total_count = await container.user_management.get_user_list(
        role=role_filter,
        limit=USER_LIST_PAGE_SIZE,
        offset=offset,
        sort_newest_first=True
    )

    # Calculate total pages
    total_pages = (total_count + USER_LIST_PAGE_SIZE - 1) // USER_LIST_PAGE_SIZE

    # Generate list message
    if users:
        text, keyboard = container.message.admin.user.users_list(
            users=users,
            page=page,
            total_pages=total_pages,
            filter_type=filter_type,
            total_count=total_count
        )
    else:
        # Empty list
        text = f"👥 <b>Usuarios: {filter_type.title()}</b>\n\n<i>No hay usuarios para mostrar.</i>"
        from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(text="🔙 Volver", callback_data="admin:users:menu")
        )
        keyboard = keyboard.as_markup()

    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.warning(f"Could not edit message: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer()


# ===== SEARCH USERS =====

@users_router.callback_query(F.data == "admin:users:search")
async def callback_users_search(callback: CallbackQuery, state, session: AsyncSession):
    """
    Prompt user to enter search query.

    Args:
        callback: Callback query
        state: FSM state
        session: Sesión de BD
    """
    logger.debug(f"🔍 Admin {callback.from_user.id} initiating user search")

    # Set FSM state
    await state.set_state(UserManagementStates.searching_user)

    # Get search prompt message
    container = ServiceContainer(session, callback.bot)
    text, keyboard = container.message.admin.user.user_search_prompt()

    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.warning(f"Could not edit message: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer()


@users_router.message(UserManagementStates.searching_user)
async def callback_users_search_results(message: Message, state, session: AsyncSession):
    """
    Process user search query and display results.

    Args:
        message: Message with search query
        state: FSM state
        session: Sesión de BD
    """
    logger.debug(f"🔍 Admin {message.from_user.id} searching for user: {message.text}")

    container = ServiceContainer(session, message.bot)

    # Search for users
    query = message.text.strip()
    users = await container.user_management.search_users(query=query, limit=10)

    # Clear FSM state
    await state.clear()

    # Generate results message
    text, keyboard = container.message.admin.user.user_search_results(users=users, query=query)

    await message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")


# ===== USER DETAIL VIEW =====

@users_router.callback_query(F.data.startswith("admin:user:view:"))
async def callback_user_view(callback: CallbackQuery, session: AsyncSession):
    """
    Show detailed user profile with tabs.

    Callback data format: "admin:user:view:{user_id}:{tab}"

    Tabs: overview, subscription, activity, interests

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    container = ServiceContainer(session, callback.bot)

    # Parse callback data using CallbackParser
    cb_data = CallbackParser.parse_or_none(callback.data, pattern=["user_id", "tab"])
    if not cb_data:
        logger.warning(f"⚠️ Invalid callback data: {callback.data}")
        await callback.answer("❌ Datos inválidos", show_alert=True)
        return

    user_id = cb_data.get_int("user_id")
    if not user_id:
        await callback.answer("❌ ID de usuario inválido", show_alert=True)
        return

    tab = cb_data.get_str("tab", "overview")

    # Get user info
    user_info = await container.user_management.get_user_info(user_id=user_id)

    if not user_info:
        await callback.answer("❌ Usuario no encontrado", show_alert=True)
        return

    # Generate appropriate tab message
    if tab == "overview":
        text, keyboard = container.message.admin.user.user_detail_overview(user_info)
    elif tab == "subscription":
        text, keyboard = container.message.admin.user.user_detail_subscription(user_info)
    elif tab == "activity":
        text, keyboard = container.message.admin.user.user_detail_activity(user_info)
    elif tab == "interests":
        # Get user interests
        interests, _ = await container.interest.get_interests(user_id=user_id, limit=10)
        text, keyboard = container.message.admin.user.user_detail_interests(user_info, interests)
    else:
        text, keyboard = container.message.admin.user.user_detail_overview(user_info)

    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.warning(f"Could not edit message: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer()


# ===== ROLE CHANGE =====

@users_router.callback_query(F.data.startswith("admin:user:role:"))
async def callback_user_role(callback: CallbackQuery, session: AsyncSession):
    """
    Show role change confirmation dialog.

    Callback data format: "admin:user:role:{user_id}"
    OR "admin:user:role:confirm:{user_id}:{new_role}"

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    container = ServiceContainer(session, callback.bot)

    # Parse callback data using CallbackParser
    cb_data = CallbackParser.parse_or_none(callback.data)
    if not cb_data:
        logger.warning(f"⚠️ Invalid callback data: {callback.data}")
        await callback.answer("❌ Datos inválidos", show_alert=True)
        return

    # Check if this is the confirm action
    if cb_data.has("confirm"):
        # Handle actual role change in separate handler
        await callback_user_role_confirm(callback, session)
        return

    user_id = cb_data.get_int("role")
    if not user_id:
        await callback.answer("❌ ID de usuario inválido", show_alert=True)
        return

    # Get user info
    user_info = await container.user_management.get_user_info(user_id=user_id)

    if not user_info:
        await callback.answer("❌ Usuario no encontrado", show_alert=True)
        return

    # Show role selection dialog with all available roles
    from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

    user_name = user_info.get("first_name", "Usuario")
    current_role = user_info["role"]

    text = (
        f"🔄 <b>Cambiar Rol de Usuario</b>\n\n"
        f"👤 <b>Usuario:</b> {user_name}\n"
        f"🆔 <b>ID:</b> {user_id}\n"
        f"📍 <b>Rol actual:</b> {current_role.value}\n\n"
        f"<i>Seleccione el nuevo rol:</i>"
    )

    keyboard = InlineKeyboardBuilder()

    # Add role options (excluding current role)
    if current_role != UserRole.VIP:
        keyboard.row(
            InlineKeyboardButton(text="💎 VIP", callback_data=f"admin:user:role:confirm:{user_id}:vip")
        )
    if current_role != UserRole.FREE:
        keyboard.row(
            InlineKeyboardButton(text="👤 Free", callback_data=f"admin:user:role:confirm:{user_id}:free")
        )
    if current_role != UserRole.ADMIN:
        keyboard.row(
            InlineKeyboardButton(text="👑 Admin", callback_data=f"admin:user:role:confirm:{user_id}:admin")
        )

    keyboard.row(
        InlineKeyboardButton(text="❌ Cancelar", callback_data=f"admin:user:view:{user_id}:overview")
    )

    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.warning(f"Could not edit message: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer()


async def callback_user_role_confirm(callback: CallbackQuery, session: AsyncSession):
    """
    Execute role change (confirmed).

    Callback data format: "admin:user:role:confirm:{user_id}:{new_role}"

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    container = ServiceContainer(session, callback.bot)

    # Parse callback data using CallbackParser
    cb_data = CallbackParser.parse_or_none(callback.data)
    if not cb_data:
        logger.warning(f"⚠️ Invalid callback data: {callback.data}")
        await callback.answer("❌ Datos inválidos", show_alert=True)
        return

    user_id = cb_data.get_int("confirm")
    new_role_str = cb_data.get_str("role")

    if not user_id or not new_role_str:
        await callback.answer("❌ Parámetros inválidos", show_alert=True)
        return

    # Map role string to UserRole enum
    role_map = {
        "vip": UserRole.VIP,
        "free": UserRole.FREE,
        "admin": UserRole.ADMIN
    }
    new_role = role_map.get(new_role_str.lower())

    if not new_role:
        await callback.answer("❌ Rol inválido", show_alert=True)
        return

    # Get current user info
    user_info = await container.user_management.get_user_info(user_id=user_id)

    if not user_info:
        await callback.answer("❌ Usuario no encontrado", show_alert=True)
        return

    old_role = user_info["role"]
    admin_id = callback.from_user.id

    # Perform role change
    success, message = await container.user_management.change_user_role(
        user_id=user_id,
        new_role=new_role,
        changed_by=admin_id
    )

    if not success:
        # Show error message
        await callback.answer(f"❌ {message}", show_alert=True)
        text, keyboard = container.message.admin.user.action_error(message)
        try:
            await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            if "message is not modified" not in str(e):
                logger.warning(f"Could not edit message: {e}")
        return

    # Show success message
    text, keyboard = container.message.admin.user.role_change_success(
        user_info=user_info,
        old_role=old_role,
        new_role=new_role
    )

    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.warning(f"Could not edit message: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer("✅ Rol cambiado exitosamente", show_alert=True)
    logger.info(f"✅ Admin {admin_id} changed user {user_id} role from {old_role.value} to {new_role.value}")


# ===== EXPEL USER =====

@users_router.callback_query(F.data.startswith("admin:user:expel:"))
async def callback_user_expel(callback: CallbackQuery, session: AsyncSession):
    """
    Show expel confirmation dialog or execute expel action.

    Callback data format:
    - "admin:user:expel:{user_id}" - Show confirmation
    - "admin:user:expel:confirm:{user_id}" - Execute expel

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    container = ServiceContainer(session, callback.bot)

    # Parse callback data using CallbackParser
    cb_data = CallbackParser.parse_or_none(callback.data)
    if not cb_data:
        logger.warning(f"⚠️ Invalid callback data: {callback.data}")
        await callback.answer("❌ Datos inválidos", show_alert=True)
        return

    # Check if this is a confirm callback
    if cb_data.has("confirm"):
        await callback_user_expel_confirm(callback, session)
        return

    user_id = cb_data.get_int("expel")
    if not user_id:
        await callback.answer("❌ ID de usuario inválido", show_alert=True)
        return

    # Get user info
    user_info = await container.user_management.get_user_info(user_id=user_id)

    if not user_info:
        await callback.answer("❌ Usuario no encontrado", show_alert=True)
        return

    # Check permissions first
    can_modify, error_msg = await container.user_management._can_modify_user(
        target_user_id=user_id,
        admin_user_id=callback.from_user.id
    )

    if not can_modify:
        await callback.answer(f"❌ {error_msg}", show_alert=True)
        return

    # Show confirmation dialog
    text, keyboard = container.message.admin.user.expel_confirm(user_info)

    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.warning(f"Could not edit message: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer()


async def callback_user_expel_confirm(callback: CallbackQuery, session: AsyncSession):
    """
    Execute user expulsion from channels (confirmed).

    Callback data format: "admin:user:expel:confirm:{user_id}"

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    container = ServiceContainer(session, callback.bot)

    # Extract user_id from callback using CallbackParser
    cb_data = CallbackParser.parse_or_none(callback.data)
    if not cb_data or not cb_data.has("confirm"):
        logger.warning(f"⚠️ Invalid callback data: {callback.data}")
        await callback.answer("❌ Datos inválidos", show_alert=True)
        return

    user_id = cb_data.get_int("confirm")

    if not user_id:
        await callback.answer("❌ ID de usuario inválido", show_alert=True)
        return

    # Get user info before expulsion
    user_info = await container.user_management.get_user_info(user_id=user_id)

    if not user_info:
        await callback.answer("❌ Usuario no encontrado", show_alert=True)
        return

    admin_id = callback.from_user.id

    # Perform expulsion (returns tuple of 3: success, message, expelled_from list)
    success, message, expelled_from = await container.user_management.expel_user_from_channels(
        user_id=user_id,
        expelled_by=admin_id
    )

    if not success:
        # Show error message
        await callback.answer(f"❌ {message}", show_alert=True)
        text, keyboard = container.message.admin.user.action_error(message)
        try:
            await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            if "message is not modified" not in str(e):
                logger.warning(f"Could not edit message: {e}")
        return

    # Show success message
    text, keyboard = container.message.admin.user.expel_success(
        user_info=user_info,
        expelled_from=expelled_from
    )

    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.warning(f"Could not edit message: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer("✅ Usuario expulsado", show_alert=True)
    logger.info(f"✅ Admin {admin_id} expelled user {user_id} from channels: {', '.join(expelled_from)}")


# ===== DELETE USER =====

@users_router.callback_query(F.data.startswith("admin:user:delete:"))
async def callback_user_delete(callback: CallbackQuery, state, session: AsyncSession):
    """
    Show delete confirmation dialog.

    Callback data format:
    - "admin:user:delete:{user_id}" - Show confirmation
    - "admin:user:delete:confirm:{user_id}" - Execute delete (handled by callback_user_delete_confirm)

    Args:
        callback: Callback query
        state: FSM state
        session: Sesión de BD
    """
    container = ServiceContainer(session, callback.bot)

    # Parse callback data using CallbackParser
    cb_data = CallbackParser.parse_or_none(callback.data)
    if not cb_data:
        logger.warning(f"⚠️ Invalid callback data: {callback.data}")
        await callback.answer("❌ Datos inválidos", show_alert=True)
        return

    # Check if this is a confirm callback
    if cb_data.has("confirm"):
        await callback_user_delete_confirm(callback, state, session)
        return

    user_id = cb_data.get_int("user_id")
    if not user_id:
        await callback.answer("❌ ID de usuario inválido", show_alert=True)
        return

    # Get user info
    user_info = await container.user_management.get_user_info(user_id=user_id)

    if not user_info:
        await callback.answer("❌ Usuario no encontrado", show_alert=True)
        return

    # Check permissions first
    can_modify, error_msg = await container.user_management._can_modify_user(
        target_user_id=user_id,
        admin_user_id=callback.from_user.id
    )

    if not can_modify:
        await callback.answer(f"❌ {error_msg}", show_alert=True)
        return

    # Set FSM state for confirmation flow
    await state.set_state(UserManagementStates.deleting_user)

    # Show confirmation dialog
    text, keyboard = container.message.admin.user.delete_confirm(user_info)

    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.warning(f"Could not edit message: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer()


async def callback_user_delete_confirm(callback: CallbackQuery, state, session: AsyncSession):
    """
    Execute user deletion (confirmed).

    Callback data format: "admin:user:delete:confirm:{user_id}"

    Args:
        callback: Callback query
        state: FSM state
        session: Sesión de BD
    """
    container = ServiceContainer(session, callback.bot)

    # Extract user_id from callback using CallbackParser
    cb_data = CallbackParser.parse_or_none(callback.data)
    if not cb_data or not cb_data.has("confirm"):
        logger.warning(f"⚠️ Invalid callback data: {callback.data}")
        await callback.answer("❌ Datos inválidos", show_alert=True)
        return

    user_id = cb_data.get_int("confirm")

    if not user_id:
        await callback.answer("❌ ID de usuario inválido", show_alert=True)
        return

    # Get user info before deletion
    user_info = await container.user_management.get_user_info(user_id=user_id)

    if not user_info:
        await callback.answer("❌ Usuario no encontrado", show_alert=True)
        await state.clear()
        return

    admin_id = callback.from_user.id

    # Perform deletion
    success, message, deleted_user = await container.subscription.delete_user_completely(
        user_id=user_id,
        deleted_by=admin_id
    )

    # Clear FSM state
    await state.clear()

    if not success:
        # Show error message
        await callback.answer(f"❌ {message}", show_alert=True)
        text, keyboard = container.message.admin.user.action_error(message)
        try:
            await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            if "message is not modified" not in str(e):
                logger.warning(f"Could not edit message: {e}")
        return

    # Show success message
    text, keyboard = container.message.admin.user.delete_success(user_info=user_info)

    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.warning(f"Could not edit message: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer("✅ Usuario eliminado", show_alert=True)
    logger.info(f"✅ Admin {admin_id} deleted user {user_id} completely")


# ===== BLOCK USER (Placeholder) =====

@users_router.callback_query(F.data.startswith("admin:user:block:"))
async def callback_user_block(callback: CallbackQuery, session: AsyncSession):
    """
    Handle block user action (placeholder for future implementation).

    Callback data format: "admin:user:block:{user_id}"

    Note: Full implementation requires adding User.is_blocked field to database.
    This handler shows a placeholder message explaining the feature is planned.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

    container = ServiceContainer(session, callback.bot)

    # Parse callback data using CallbackParser
    cb_data = CallbackParser.parse_or_none(callback.data, pattern=["user_id"])
    if not cb_data:
        logger.warning(f"⚠️ Invalid callback data: {callback.data}")
        await callback.answer("❌ Datos inválidos", show_alert=True)
        return

    user_id = cb_data.get_int("user_id")
    if not user_id:
        await callback.answer("❌ ID de usuario inválido", show_alert=True)
        return

    # Check permissions first
    can_modify, error_msg = await container.user_management._can_modify_user(
        target_user_id=user_id,
        admin_user_id=callback.from_user.id
    )

    if not can_modify:
        await callback.answer(f"❌ {error_msg}", show_alert=True)
        return

    # Show placeholder message
    placeholder_text = (
        f"🚫 <b>Bloquear Usuario</b>\n\n"
        f"<i>Esta función estará disponible en una próxima versión.</i>\n\n"
        f"<b>Estado:</b> Planificado\n"
        f"<b>Requisito:</b> Migración de base de datos para agregar campo de bloqueo\n\n"
        f"<i>El bloqueo impedirá que el usuario use el bot, pero no lo expulsará de los canales. "
        f"Use la opción 'Expulsar' para remover al usuario de los canales.</i>"
    )

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="🔙 Volver al Perfil", callback_data=f"admin:user:view:{user_id}:overview")
    )

    try:
        await callback.message.edit_text(text=placeholder_text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.warning(f"Could not edit message: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer("⚠️ Función planificada para próxima versión", show_alert=True)
    logger.info(f"ℹ️ Admin {callback.from_user.id} attempted to block user {user_id} (feature not yet implemented)")


# ===== FILTERS =====

@users_router.callback_query(F.data.startswith("admin:users:filters"))
async def callback_users_filters(callback: CallbackQuery, session: AsyncSession):
    """
    Show filter selection screen.

    Callback data format: "admin:users:filters" or "admin:users:filters:{current_filter}"

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

    # Parse callback data using CallbackParser
    cb_data = CallbackParser.parse_or_none(callback.data)
    current_filter = "all"
    if cb_data:
        current_filter = cb_data.get_str("filters", "all")

    filter_names = {
        "all": "Todos los Usuarios",
        "vip": "Solo VIP",
        "free": "Solo Free"
    }

    text = (
        f"🔍 <b>Filtros de Usuarios</b>\n\n"
        f"<i>Filtro actual: {filter_names.get(current_filter, 'Todos')}</i>\n\n"
        f"<i>Seleccione un nuevo filtro:</i>"
    )

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="👥 Todos", callback_data="admin:users:list:all")
    )
    keyboard.row(
        InlineKeyboardButton(text="💎 Solo VIP", callback_data="admin:users:list:vip"),
        InlineKeyboardButton(text="👤 Solo Free", callback_data="admin:users:list:free")
    )
    keyboard.row(
        InlineKeyboardButton(text="🔙 Volver", callback_data="admin:users:menu")
    )

    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.warning(f"Could not edit message: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer()


# ===== NAVIGATION HELPERS =====

@users_router.callback_query(F.data == "admin:users:menu")
async def callback_users_menu_back(callback: CallbackQuery, session: AsyncSession):
    """
    Return to user management menu.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    await callback_users_menu(callback, session)


@users_router.callback_query(F.data == "admin:users:noop")
async def callback_users_noop(callback: CallbackQuery):
    """
    No-op handler for pagination page number button.

    Args:
        callback: Callback query
    """
    await callback.answer()
