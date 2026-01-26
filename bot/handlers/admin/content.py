"""
Content Management Handlers - Admin interface for managing content packages.

Handlers for listing, viewing, creating, editing, and deactivating content packages.
"""
import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.enums import PackageType
from bot.middlewares import DatabaseMiddleware
from bot.services.container import ServiceContainer
from bot.states.admin import ContentPackageStates
from bot.utils.pagination import Paginator, create_pagination_keyboard, format_page_header, format_items_list

logger = logging.getLogger(__name__)

# Router for content management handlers
content_router = Router(name="admin_content")

# Apply middleware (AdminAuth already on admin_router, this integrates into it)
content_router.callback_query.middleware(DatabaseMiddleware())
content_router.message.middleware(DatabaseMiddleware())


# ===== MENU NAVIGATION =====

@content_router.callback_query(
    F.data == "admin:content",
    ~F.state.in_([
        ContentPackageStates.waiting_for_name,
        ContentPackageStates.waiting_for_type,
        ContentPackageStates.waiting_for_price,
        ContentPackageStates.waiting_for_description,
        ContentPackageStates.waiting_for_edit
    ])
)
async def callback_content_menu(callback: CallbackQuery, session: AsyncSession):
    """
    Show content management submenu.

    Args:
        callback: Callback query
        session: Sesión de BD (inyectada por middleware)
    """
    logger.debug(f"📦 Usuario {callback.from_user.id} abrió menú de contenido")

    container = ServiceContainer(session, callback.bot)

    # Obtener mensaje del provider
    text, keyboard = container.message.admin.content.content_menu()

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error editando mensaje de menú contenido: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer()


# ===== LIST PACKAGES =====

@content_router.callback_query(F.data == "admin:content:list")
async def callback_content_list(callback: CallbackQuery, session: AsyncSession):
    """
    Show first page of content packages.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.debug(f"📦 Usuario {callback.from_user.id} listando paquetes (página 1)")

    container = ServiceContainer(session, callback.bot)

    # Get all packages (in-memory pagination per RESEARCH.md recommendation)
    all_packages = await container.content.list_packages(is_active=None)

    # Check if empty
    if not all_packages:
        text, keyboard = container.message.admin.content.content_list_empty()
        try:
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                logger.error(f"❌ Error editando mensaje lista vacía: {e}")

        await callback.answer()
        return

    # Paginate
    paginator = Paginator(items=all_packages, page_size=10)
    page = paginator.get_first_page()

    # Format display using AdminContentMessages
    text, keyboard = container.message.admin.content.content_list_header()

    # Add package summaries to text
    packages_text = format_items_list(
        page.items,
        lambda pkg, idx: container.message.admin.content.package_summary(pkg),
        separator="\n\n"
    )

    # Combine header with packages
    full_text = f"{text}\n\n{packages_text}"

    # Create pagination keyboard
    keyboard = create_pagination_keyboard(
        page=page,
        callback_pattern="admin:content:page:{page}",
        back_callback="admin:content"
    )

    try:
        await callback.message.edit_text(
            text=full_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error editando mensaje lista: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer()


@content_router.callback_query(F.data.startswith("admin:content:page:"))
async def callback_content_page(callback: CallbackQuery, session: AsyncSession):
    """
    Show specific page of content packages.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    # Extract page number from callback
    try:
        page_num = int(callback.data.split(":")[-1])
    except (ValueError, IndexError):
        logger.warning(f"⚠️ Callback data inválido: {callback.data}")
        await callback.answer("❌ Página inválida", show_alert=True)
        return

    logger.debug(f"📦 Usuario {callback.from_user.id} viendo página {page_num}")

    container = ServiceContainer(session, callback.bot)

    # Get all packages (in-memory pagination per RESEARCH.md recommendation)
    all_packages = await container.content.list_packages(is_active=None)
    paginator = Paginator(items=all_packages, page_size=10)

    # Validate page number
    if page_num < 1 or page_num > paginator.total_pages:
        logger.warning(f"⚠️ Número de página fuera de rango: {page_num}")
        await callback.answer("❌ Página fuera de rango", show_alert=True)
        return

    page = paginator.get_page(page_num)

    # Format display using AdminContentMessages
    text, keyboard = container.message.admin.content.content_list_header()

    # Add package summaries to text
    packages_text = format_items_list(
        page.items,
        lambda pkg, idx: container.message.admin.content.package_summary(pkg),
        separator="\n\n"
    )

    # Combine header with packages
    full_text = f"{text}\n\n{packages_text}"

    # Create pagination keyboard
    keyboard = create_pagination_keyboard(
        page=page,
        callback_pattern="admin:content:page:{page}",
        back_callback="admin:content"
    )

    try:
        await callback.message.edit_text(
            text=full_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error editando mensaje página: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer()


# ===== PACKAGE DETAIL VIEW =====

@content_router.callback_query(F.data.startswith("admin:content:view:"))
async def callback_content_view(callback: CallbackQuery, session: AsyncSession):
    """
    Show package details with action buttons.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    # Extract package_id from callback
    try:
        package_id = int(callback.data.split(":")[-1])
    except (ValueError, IndexError):
        logger.warning(f"⚠️ Callback data inválido: {callback.data}")
        await callback.answer("❌ ID de paquete inválido", show_alert=True)
        return

    logger.debug(f"📦 Usuario {callback.from_user.id} viendo paquete {package_id}")

    container = ServiceContainer(session, callback.bot)

    package = await container.content.get_package(package_id)
    if not package:
        await callback.answer("❌ Paquete no encontrado", show_alert=True)
        return

    # Get package detail with action buttons
    text, keyboard = container.message.admin.content.package_detail(package)

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error editando mensaje detalle: {e}")
        else:
            logger.debug("ℹ️ Mensaje sin cambios, ignorando")

    await callback.answer()


# ===== CREATE PACKAGE WIZARD (FSM) =====

@content_router.callback_query(F.data == "admin:content:create:start")
async def callback_content_create_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Inicia flujo de creación de paquete.

    Args:
        callback: Callback query
        state: FSM context
        session: Sesión de BD
    """
    logger.info(f"➕ Usuario {callback.from_user.id} iniciando creación de paquete")

    await state.set_state(ContentPackageStates.waiting_for_name)

    container = ServiceContainer(session, callback.bot)
    text, keyboard = container.message.admin.content.create_step_name()
    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error editando mensaje de creación: {e}")

    await callback.answer()


@content_router.message(ContentPackageStates.waiting_for_name)
async def process_content_name(message: Message, state: FSMContext, session: AsyncSession):
    """
    Procesa nombre del paquete.

    Args:
        message: Mensaje con el nombre
        state: FSM context
        session: Sesión de BD
    """
    name = message.text.strip()

    # Validación: no vacío, max 200 chars
    if not name or len(name) > 200:
        await message.answer("❌ Nombre inválido. Debe tener 1-200 caracteres.")
        return  # Keep state active for retry

    await state.update_data(name=name)
    await state.set_state(ContentPackageStates.waiting_for_type)

    container = ServiceContainer(session, message.bot)
    text, keyboard = container.message.admin.content.create_step_type()
    await message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")


@content_router.callback_query(F.data.startswith("admin:content:create:type:"), ContentPackageStates.waiting_for_type)
async def process_content_type(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Procesa tipo seleccionado via botones.

    Args:
        callback: Callback query con el tipo seleccionado
        state: FSM context
        session: Sesión de BD
    """
    # Extract type from callback: "admin:content:create:type:VIP_PREMIUM"
    type_str = callback.data.split(":")[-1]

    # Extract category from callback string
    if "free_content" in type_str:
        from bot.database.enums import ContentCategory
        category = ContentCategory.FREE_CONTENT
    elif "vip_content" in type_str:
        from bot.database.enums import ContentCategory
        category = ContentCategory.VIP_CONTENT
    elif "vip_premium" in type_str:
        from bot.database.enums import ContentCategory
        category = ContentCategory.VIP_PREMIUM
    else:
        logger.warning(f"⚠️ Tipo de paquete inválido: {type_str}")
        await callback.answer("❌ Tipo inválido", show_alert=True)
        return

    await state.update_data(category=category)
    await state.set_state(ContentPackageStates.waiting_for_price)

    container = ServiceContainer(session, callback.bot)
    text, keyboard = container.message.admin.content.create_step_price()
    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error editando mensaje paso precio: {e}")

    await callback.answer()


@content_router.callback_query(F.data == "admin:content:create:skip:price", ContentPackageStates.waiting_for_price)
async def skip_content_price(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Salta el paso de precio (opcional).

    Args:
        callback: Callback query
        state: FSM context
        session: Sesión de BD
    """
    await state.update_data(price=None)
    await state.set_state(ContentPackageStates.waiting_for_description)

    container = ServiceContainer(session, callback.bot)
    text, keyboard = container.message.admin.content.create_step_description()
    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error editando mensaje paso descripción: {e}")

    await callback.answer()


@content_router.message(ContentPackageStates.waiting_for_price)
async def process_content_price(message: Message, state: FSMContext, session: AsyncSession):
    """
    Procesa precio (opcional).

    Args:
        message: Mensaje con el precio
        state: FSM context
        session: Sesión de BD
    """
    text = message.text.strip()

    # Validate: must be numeric, non-negative
    try:
        price = float(text)
        if price < 0:
            raise ValueError("Price cannot be negative")
    except ValueError:
        await message.answer("❌ Precio inválido. Envía un número positivo o /skip para omitir.")
        return  # Keep state active

    await state.update_data(price=price)
    await state.set_state(ContentPackageStates.waiting_for_description)

    container = ServiceContainer(session, message.bot)
    text_msg, keyboard = container.message.admin.content.create_step_description()
    await message.answer(text=text_msg, reply_markup=keyboard, parse_mode="HTML")


@content_router.callback_query(F.data == "admin:content:create:skip:description", ContentPackageStates.waiting_for_description)
async def skip_content_description(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Salta el paso de descripción y crea el paquete.

    Args:
        callback: Callback query
        state: FSM context
        session: Sesión de BD
    """
    await state.update_data(description=None)

    # Get all collected data
    data = await state.get_data()

    # Create package using ContentService
    container = ServiceContainer(session, callback.bot)
    package = await container.content.create_package(
        name=data["name"],
        category=data["category"],
        description=None,
        price=data.get("price")
    )

    # Clear FSM state (CRITICAL - per RESEARCH.md Pitfall 1)
    await state.clear()

    # Show success message with action buttons
    text, keyboard = container.message.admin.content.create_success(package)
    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error editando mensaje éxito: {e}")

    await callback.answer()
    logger.info(f"✅ Paquete creado: {package.name} (ID: {package.id}) por {callback.from_user.id}")


@content_router.message(ContentPackageStates.waiting_for_description)
async def process_content_description(message: Message, state: FSMContext, session: AsyncSession):
    """
    Procesa descripción y crea paquete.

    Args:
        message: Mensaje con la descripción
        state: FSM context
        session: Sesión de BD
    """
    description = message.text.strip()

    # Allow /skip to omit
    if description == "/skip":
        description = None

    # Get all collected data
    data = await state.get_data()

    # Create package using ContentService
    container = ServiceContainer(session, message.bot)
    package = await container.content.create_package(
        name=data["name"],
        category=data["category"],
        description=description,
        price=data.get("price")
    )

    # Clear FSM state (CRITICAL - per RESEARCH.md Pitfall 1)
    await state.clear()

    # Show success message with action buttons
    text, keyboard = container.message.admin.content.create_success(package)
    await message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")
    logger.info(f"✅ Paquete creado: {package.name} (ID: {package.id}) por {message.from_user.id}")


# ===== EDIT PACKAGE HANDLERS =====

@content_router.callback_query(F.data.startswith("admin:content:edit:"))
async def callback_content_edit_field(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Prompt for field value edit.

    Args:
        callback: Callback query
        state: FSM context
        session: Sesión de BD
    """
    # Extract package_id and field from callback: "admin:content:edit:123:name"
    parts = callback.data.split(":")

    # Validate format
    if len(parts) < 5:
        logger.warning(f"⚠️ Callback data inválido: {callback.data}")
        await callback.answer("❌ Formato inválido", show_alert=True)
        return

    try:
        package_id = int(parts[3])
    except (ValueError, IndexError):
        logger.warning(f"⚠️ ID de paquete inválido en callback: {callback.data}")
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    field = parts[4]  # name, price, or description

    # Validate field
    valid_fields = ["name", "price", "description"]
    if field not in valid_fields:
        logger.warning(f"⚠️ Campo inválido: {field}")
        await callback.answer("❌ Campo inválido", show_alert=True)
        return

    await state.set_state(ContentPackageStates.waiting_for_edit)
    await state.update_data(package_id=package_id, field=field)

    container = ServiceContainer(session, callback.bot)
    package = await container.content.get_package(package_id)

    if not package:
        await callback.answer("❌ Paquete no encontrado", show_alert=True)
        await state.clear()
        return

    # Get current value for display
    current_value = getattr(package, field, "N/A")

    # Field name for display
    field_names = {
        "name": "Nombre",
        "price": "Precio",
        "description": "Descripción"
    }

    text, keyboard = container.message.admin.content.edit_prompt(field_names[field], current_value)
    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error editando mensaje edición: {e}")

    await callback.answer()


@content_router.callback_query(F.data == "admin:content:cancel_edit", ContentPackageStates.waiting_for_edit)
async def callback_content_edit_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Cancela edición de campo.

    Args:
        callback: Callback query
        state: FSM context
        session: Sesión de BD
    """
    data = await state.get_data()
    package_id = data.get("package_id")

    await state.clear()

    if package_id:
        # Return to detail view
        container = ServiceContainer(session, callback.bot)
        package = await container.content.get_package(package_id)
        if package:
            text, keyboard = container.message.admin.content.package_detail(package)
            try:
                await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
            except Exception as e:
                if "message is not modified" not in str(e):
                    logger.error(f"❌ Error volviendo a detalle: {e}")

    await callback.answer()


@content_router.message(ContentPackageStates.waiting_for_edit)
async def process_content_edit(message: Message, state: FSMContext, session: AsyncSession):
    """
    Process field edit and update package.

    Args:
        message: Mensaje con el nuevo valor
        state: FSM context
        session: Sesión de BD
    """
    data = await state.get_data()
    package_id = data["package_id"]
    field = data["field"]

    # Allow /skip to keep current value
    if message.text.strip() == "/skip":
        await state.clear()
        container = ServiceContainer(session, message.bot)
        package = await container.content.get_package(package_id)
        if package:
            text, keyboard = container.message.admin.content.package_detail(package)
            await message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")
        return

    container = ServiceContainer(session, message.bot)

    # Validate based on field
    if field == "price":
        try:
            new_value = float(message.text.strip())
            if new_value < 0:
                raise ValueError("Price cannot be negative")
        except ValueError:
            await message.answer("❌ Precio inválido. Debe ser un número positivo.")
            return  # Keep state active
    elif field == "name":
        new_value = message.text.strip()
        # Name validation
        if not new_value or len(new_value) > 200:
            await message.answer("❌ Nombre inválido. Debe tener 1-200 caracteres.")
            return
    else:  # description
        new_value = message.text.strip()

    # Update using ContentService
    await container.content.update_package(package_id, **{field: new_value})

    await state.clear()

    # Show updated detail view
    package = await container.content.get_package(package_id)
    if package:
        text, keyboard = container.message.admin.content.package_detail(package)
        await message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")
        logger.info(f"✅ Paquete {package_id} actualizado: {field}={new_value} por {message.from_user.id}")


# ===== TOGGLE (ACTIVATE/DEACTIVATE) HANDLERS =====

@content_router.callback_query(F.data.startswith("admin:content:deactivate:"))
async def callback_content_deactivate_confirm(callback: CallbackQuery, session: AsyncSession):
    """
    Show deactivation confirmation dialog.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    # Check if this is the confirm action (has extra "confirm" segment)
    parts = callback.data.split(":")
    if len(parts) > 4 and parts[4] == "confirm":
        # This is handled by callback_content_deactivate
        return

    # Extract package_id from callback
    try:
        package_id = int(parts[-1])
    except (ValueError, IndexError):
        logger.warning(f"⚠️ Callback data inválido: {callback.data}")
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    container = ServiceContainer(session, callback.bot)
    package = await container.content.get_package(package_id)

    if not package:
        await callback.answer("❌ Paquete no encontrado", show_alert=True)
        return

    text, keyboard = container.message.admin.content.deactivate_confirm(package)
    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error editando mensaje desactivación: {e}")

    await callback.answer()


@content_router.callback_query(F.data.startswith("admin:content:deactivate:confirm:"))
async def callback_content_deactivate(callback: CallbackQuery, session: AsyncSession):
    """
    Deactivate package (soft delete).

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    # Extract package_id from callback
    try:
        package_id = int(callback.data.split(":")[-1])
    except (ValueError, IndexError):
        logger.warning(f"⚠️ Callback data inválido: {callback.data}")
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    container = ServiceContainer(session, callback.bot)
    result = await container.content.deactivate_package(package_id)

    if result:
        await callback.answer("✅ Paquete desactivado", show_alert=True)
        # Return to detail view
        package = await container.content.get_package(package_id)
        if package:
            text, keyboard = container.message.admin.content.package_detail(package)
            try:
                await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
            except Exception as e:
                if "message is not modified" not in str(e):
                    logger.error(f"❌ Error editando mensaje después de desactivar: {e}")
        logger.info(f"✅ Paquete {package_id} desactivado por {callback.from_user.id}")
    else:
        await callback.answer("❌ Error al desactivar", show_alert=True)


@content_router.callback_query(F.data.startswith("admin:content:reactivate:"))
async def callback_content_reactivate_confirm(callback: CallbackQuery, session: AsyncSession):
    """
    Show reactivation confirmation dialog.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    # Check if this is the confirm action (has extra "confirm" segment)
    parts = callback.data.split(":")
    if len(parts) > 4 and parts[4] == "confirm":
        # This is handled by callback_content_reactivate
        return

    # Extract package_id from callback
    try:
        package_id = int(parts[-1])
    except (ValueError, IndexError):
        logger.warning(f"⚠️ Callback data inválido: {callback.data}")
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    container = ServiceContainer(session, callback.bot)
    package = await container.content.get_package(package_id)

    if not package:
        await callback.answer("❌ Paquete no encontrado", show_alert=True)
        return

    text, keyboard = container.message.admin.content.reactivate_confirm(package)
    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error editando mensaje reactivación: {e}")

    await callback.answer()


@content_router.callback_query(F.data.startswith("admin:content:reactivate:confirm:"))
async def callback_content_reactivate(callback: CallbackQuery, session: AsyncSession):
    """
    Reactivate package.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    # Extract package_id from callback
    try:
        package_id = int(callback.data.split(":")[-1])
    except (ValueError, IndexError):
        logger.warning(f"⚠️ Callback data inválido: {callback.data}")
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    container = ServiceContainer(session, callback.bot)
    result = await container.content.activate_package(package_id)

    if result:
        await callback.answer("✅ Paquete reactivado", show_alert=True)
        # Return to detail view
        package = await container.content.get_package(package_id)
        if package:
            text, keyboard = container.message.admin.content.package_detail(package)
            try:
                await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
            except Exception as e:
                if "message is not modified" not in str(e):
                    logger.error(f"❌ Error editando mensaje después de reactivar: {e}")
        logger.info(f"✅ Paquete {package_id} reactivado por {callback.from_user.id}")
    else:
        await callback.answer("❌ Error al reactivar", show_alert=True)


# ===== CANCEL CREATION WIZARD =====

@content_router.callback_query(
    F.data == "admin:content",
    F.state.in_([
        ContentPackageStates.waiting_for_name,
        ContentPackageStates.waiting_for_type,
        ContentPackageStates.waiting_for_price,
        ContentPackageStates.waiting_for_description,
        ContentPackageStates.waiting_for_edit
    ])
)
async def callback_content_create_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Cancela creación o edición de paquete (desde cualquier paso del wizard).

    Args:
        callback: Callback query
        state: FSM context
        session: Sesión de BD
    """
    await state.clear()  # CRITICAL: Always clear FSM state

    container = ServiceContainer(session, callback.bot)
    text, keyboard = container.message.admin.content.content_menu()
    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error volviendo al menú contenido: {e}")

    await callback.answer()
