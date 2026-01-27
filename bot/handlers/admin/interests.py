"""
Interest Management Handlers - Admin interface for managing user interests.

Handlers for listing, viewing, filtering, and marking user interests as attended.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.enums import ContentCategory
from bot.middlewares import DatabaseMiddleware
from bot.services.container import ServiceContainer

logger = logging.getLogger(__name__)

# Router for interest management handlers
interests_router = Router(name="admin_interests")

# Apply middleware (AdminAuth already on admin_router, this integrates into it)
interests_router.callback_query.middleware(DatabaseMiddleware())


# ===== MENU NAVIGATION =====

@interests_router.callback_query(F.data == "admin:interests")
async def callback_interests_menu(callback: CallbackQuery, session: AsyncSession):
    """
    Show main interests management menu.

    Args:
        callback: Callback query
        session: Sesión de BD (inyectada por middleware)
    """
    logger.debug(f"🔔 Admin {callback.from_user.id} opened interests menu")

    container = ServiceContainer(session, callback.bot)

    # Get stats for menu display
    stats = await container.interest.get_interest_stats()
    pending_count = stats.get("total_pending", 0)
    total_count = stats.get("total_pending", 0) + stats.get("total_attended", 0)

    # Get menu message
    text, keyboard = container.message.admin.interest.interests_menu(
        pending_count=pending_count,
        total_count=total_count
    )

    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.warning(f"Could not edit message: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer()


# ===== LIST INTERESTS =====

async def _show_interests_list_impl(
    callback: CallbackQuery,
    session: AsyncSession,
    filter_type: str = "all",
    page: int = 1
):
    """
    Implementation of interests list display (can be called directly).

    Args:
        callback: Callback query
        session: Database session
        filter_type: Filter to apply (all, pending, attended, vip_premium, vip_content, free_content)
        page: Page number (1-indexed)

    Filters:
    - all: All interests
    - pending: Only pending (is_attended=False)
    - attended: Only attended (is_attended=True)
    - vip_premium: Only VIP Premium packages
    - vip_content: Only VIP Content packages
    - free_content: Only Free Content packages
    """
    logger.debug(f"🔔 Admin {callback.from_user.id} viewing interests list (filter={filter_type}, page={page})")

    container = ServiceContainer(session, callback.bot)

    # Map filter to InterestService params
    is_attended = None
    package_type = None

    if filter_type == "pending":
        is_attended = False
    elif filter_type == "attended":
        is_attended = True
    elif filter_type == "vip_premium":
        package_type = ContentCategory.VIP_PREMIUM
    elif filter_type == "vip_content":
        package_type = ContentCategory.VIP_CONTENT
    elif filter_type == "free_content":
        package_type = ContentCategory.FREE_CONTENT

    # Get interests with pagination
    offset = (page - 1) * 10
    interests, total_count = await container.interest.get_interests(
        is_attended=is_attended,
        package_type=package_type,
        limit=10,
        offset=offset,
        sort_newest_first=True
    )

    # Calculate total pages
    total_pages = (total_count + 9) // 10  # Round up

    # Generate list message
    if interests:
        text, keyboard = container.message.admin.interest.interests_list(
            interests=interests,
            page=page,
            total_pages=total_pages,
            filter_type=filter_type
        )
    else:
        text, keyboard = container.message.admin.interest.interests_empty(filter_type)

    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.warning(f"Could not edit message: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer()


@interests_router.callback_query(F.data.startswith("admin:interests:list:"))
async def callback_interests_list(callback: CallbackQuery, session: AsyncSession):
    """
    Show interests list with filter.

    Callback data format: "admin:interests:list:{filter_type}"

    Filters:
    - all: All interests
    - pending: Only pending (is_attended=False)
    - attended: Only attended (is_attended=True)
    - vip_premium: Only VIP Premium packages
    - vip_content: Only VIP Content packages
    - free_content: Only Free Content packages

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    # Extract filter type from callback
    parts = callback.data.split(":")
    filter_type = parts[3] if len(parts) > 3 else "all"

    await _show_interests_list_impl(callback, session, filter_type, page=1)


# ===== PAGINATION =====

@interests_router.callback_query(F.data.startswith("admin:interests:page:"))
async def callback_interests_page(callback: CallbackQuery, session: AsyncSession):
    """
    Show specific page of interests list.

    Callback data format: "admin:interests:page:{page_num}:{filter_type}"

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    # Extract page and filter from callback
    parts = callback.data.split(":")
    try:
        page = int(parts[3]) if len(parts) > 3 else 1
    except (ValueError, IndexError):
        logger.warning(f"⚠️ Invalid page number in callback: {callback.data}")
        await callback.answer("❌ Página inválida", show_alert=True)
        return

    filter_type = parts[4] if len(parts) > 4 else "all"

    await _show_interests_list_impl(callback, session, filter_type, page)


# ===== VIEW DETAIL =====

@interests_router.callback_query(F.data.startswith("admin:interest:view:"))
async def callback_interests_view(callback: CallbackQuery, session: AsyncSession):
    """
    Show detailed view of single interest.

    Callback data format: "admin:interest:view:{interest_id}"

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    container = ServiceContainer(session, callback.bot)

    # Extract interest ID
    try:
        interest_id = int(callback.data.split(":")[-1])
    except (ValueError, IndexError):
        logger.warning(f"⚠️ Invalid interest ID in callback: {callback.data}")
        await callback.answer("❌ ID de interés inválido", show_alert=True)
        return

    # Get interest with relationships loaded
    interest = await container.interest.get_interest_by_id(interest_id)

    if not interest:
        await callback.answer("❌ Interés no encontrado", show_alert=True)
        return

    # Generate detail message
    text, keyboard = container.message.admin.interest.interest_detail(interest)

    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.warning(f"Could not edit message: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer()


# ===== FILTERS =====

@interests_router.callback_query(F.data.startswith("admin:interests:filters"))
async def callback_interests_filters(callback: CallbackQuery, session: AsyncSession):
    """
    Show filter selection screen.

    Callback data format: "admin:interests:filters" or "admin:interests:filters:{current_filter}"

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    container = ServiceContainer(session, callback.bot)

    # Extract current filter
    parts = callback.data.split(":")
    current_filter = parts[3] if len(parts) > 3 else "all"

    # Generate filter selection message
    text, keyboard = container.message.admin.interest.interests_filters(current_filter)

    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.warning(f"Could not edit message: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer()


# ===== STATS =====

@interests_router.callback_query(F.data == "admin:interests:stats")
async def callback_interests_stats(callback: CallbackQuery, session: AsyncSession):
    """
    Show interest statistics.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.debug(f"📊 Admin {callback.from_user.id} viewing interest stats")

    container = ServiceContainer(session, callback.bot)

    # Get stats from InterestService
    stats = await container.interest.get_interest_stats()

    # Generate stats message
    text, keyboard = container.message.admin.interest.interests_stats(stats)

    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.warning(f"Could not edit message: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer()


# ===== MARK ATTENDED CONFIRMATION =====

async def _show_attend_confirmation_impl(
    callback: CallbackQuery,
    session: AsyncSession,
    interest_id: int
):
    """
    Implementation of attend confirmation dialog (can be called directly).

    Args:
        callback: Callback query
        session: Database session
        interest_id: ID of the interest to confirm attendance for
    """
    container = ServiceContainer(session, callback.bot)

    # Get interest
    interest = await container.interest.get_interest_by_id(interest_id)

    if not interest:
        await callback.answer("❌ Interés no encontrado", show_alert=True)
        return

    if interest.is_attended:
        await callback.answer("✅ Este interés ya está marcado como atendido", show_alert=True)
        return

    # Generate confirmation message
    text, keyboard = container.message.admin.interest.mark_attended_confirm(interest)

    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.warning(f"Could not edit message: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer()


@interests_router.callback_query(F.data.startswith("admin:interest:attend:"))
async def callback_interest_attend_confirm(callback: CallbackQuery, session: AsyncSession):
    """
    Show confirmation dialog for marking interest as attended.

    Callback data format: "admin:interest:attend:{interest_id}"
    OR "admin:interest:confirm_attend:{interest_id}" (handled separately)

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    # Skip if this is the confirm action (handled by next handler)
    parts = callback.data.split(":")
    if len(parts) > 4 and parts[4] == "confirm_attend":
        return

    # Extract interest ID
    try:
        interest_id = int(callback.data.split(":")[-1])
    except (ValueError, IndexError):
        logger.warning(f"⚠️ Invalid interest ID in callback: {callback.data}")
        await callback.answer("❌ ID de interés inválido", show_alert=True)
        return

    await _show_attend_confirmation_impl(callback, session, interest_id)


# ===== MARK ATTENDED ACTION =====

@interests_router.callback_query(F.data.startswith("admin:interest:confirm_attend:"))
async def callback_interest_attend(callback: CallbackQuery, session: AsyncSession):
    """
    Mark interest as attended (confirmed).

    Callback data format: "admin:interest:confirm_attend:{interest_id}"

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    container = ServiceContainer(session, callback.bot)

    # Extract interest ID
    try:
        interest_id = int(callback.data.split(":")[-1])
    except (ValueError, IndexError):
        logger.warning(f"⚠️ Invalid interest ID in callback: {callback.data}")
        await callback.answer("❌ ID de interés inválido", show_alert=True)
        return

    # Mark as attended using InterestService
    success, message = await container.interest.mark_as_attended(interest_id)

    if not success:
        await callback.answer(f"❌ {message}", show_alert=True)
        return

    # Get updated interest
    interest = await container.interest.get_interest_by_id(interest_id)

    if interest:
        # Generate success message
        text, keyboard = container.message.admin.interest.mark_attended_success(interest)

        try:
            await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            if "message is not modified" not in str(e):
                logger.warning(f"Could not edit message: {e}")
            else:
                logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer("✅ Interés marcado como atendido", show_alert=True)
    logger.info(f"✅ Admin {callback.from_user.id} marked interest {interest_id} as attended")
