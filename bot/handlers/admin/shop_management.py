"""
Shop Management Handler - Gestión de productos de tienda.

Handlers para administración de productos de la tienda:
- Listar productos con paginación
- Crear nuevos productos (FSM flow)
- Ver detalles de producto
- Activar/Desactivar productos

Voice: Lucien (🎩) - Formal, elegante, mayordomo
"""
import logging
from datetime import datetime
from typing import Optional

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.main import admin_router
from bot.services.container import ServiceContainer
from bot.utils.keyboards import create_inline_keyboard
from bot.database.enums import ContentTier
from bot.database.models import ShopProduct, ContentSet

logger = logging.getLogger(__name__)

# Constants
PRODUCTS_PER_PAGE = 5
TIER_EMOJIS = {
    ContentTier.FREE: "⚪",
    ContentTier.VIP: "🟡",
    ContentTier.PREMIUM: "🔴",
    ContentTier.GIFT: "🎁"
}


@admin_router.callback_query(F.data == "admin:shop")
async def callback_admin_shop(callback: CallbackQuery, session: AsyncSession):
    """
    Handler del menú principal de gestión de tienda.

    Muestra opciones para crear productos, listar existentes,
    y gestionar el catálogo de la tienda.

    Args:
        callback: Callback query
        session: Sesión de BD (inyectada por middleware)
    """
    logger.debug(f"🛍️ Usuario {callback.from_user.id} abrió menú de tienda")

    text = (
        "🎩 <b>Gestión de Tienda</b>\n\n"
        "<b>Acciones disponibles:</b>\n"
        "• Crear nuevo producto\n"
        "• Ver/Editar productos existentes\n"
        "• Activar/Desactivar productos\n\n"
        "<i>Seleccione una opción...</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "➕ Crear Producto", "callback_data": "admin:shop:create:start"}],
        [{"text": "📋 Listar Productos", "callback_data": "admin:shop:list"}],
        [{"text": "🔙 Volver", "callback_data": "admin:main"}]
    ])

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error editando mensaje de tienda: {e}")

    await callback.answer()


@admin_router.callback_query(F.data == "admin:shop:list")
async def callback_shop_list(callback: CallbackQuery, session: AsyncSession):
    """
    Handler para listar productos con paginación.

    Muestra lista paginada de productos con información
    de estado, precio y tier.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.debug(f"📋 Usuario {callback.from_user.id} solicitó lista de productos")

    await _show_product_list(callback, session, page=1)


@admin_router.callback_query(F.data.startswith("admin:shop:list:page:"))
async def callback_shop_list_page(callback: CallbackQuery, session: AsyncSession):
    """
    Handler para navegación de paginación de productos.

    Args:
        callback: Callback query con formato "admin:shop:list:page:{n}"
        session: Sesión de BD
    """
    page_str = callback.data.split(":")[-1]
    try:
        page = int(page_str)
    except ValueError:
        page = 1

    logger.debug(f"📄 Usuario {callback.from_user.id} navegó a página {page}")

    await _show_product_list(callback, session, page=page)


async def _show_product_list(callback: CallbackQuery, session: AsyncSession, page: int):
    """
    Muestra la lista paginada de productos.

    Args:
        callback: Callback query
        session: Sesión de BD
        page: Número de página (1-indexed)
    """
    # Get total count
    count_result = await session.execute(select(func.count(ShopProduct.id)))
    total = count_result.scalar_one_or_none() or 0

    if total == 0:
        text = (
            "🎩 <b>Gestión de Tienda</b>\n\n"
            "<i>No hay productos en el catálogo.</i>\n\n"
            "Use <b>➕ Crear Producto</b> para agregar el primero."
        )
        keyboard = create_inline_keyboard([
            [{"text": "➕ Crear Producto", "callback_data": "admin:shop:create:start"}],
            [{"text": "🔙 Volver", "callback_data": "admin:shop"}]
        ])

        try:
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                logger.error(f"❌ Error mostrando lista vacía: {e}")

        await callback.answer()
        return

    # Get products for current page
    offset = (page - 1) * PRODUCTS_PER_PAGE
    result = await session.execute(
        select(ShopProduct)
        .order_by(ShopProduct.created_at.desc())
        .offset(offset)
        .limit(PRODUCTS_PER_PAGE)
    )
    products = list(result.scalars().all())

    total_pages = (total + PRODUCTS_PER_PAGE - 1) // PRODUCTS_PER_PAGE

    # Build product list text
    lines = ["🎩 <b>Catálogo de Productos</b>", ""]

    for product in products:
        status_emoji = "🟢" if product.is_active else "🔴"
        tier_emoji = TIER_EMOJIS.get(product.tier, "⚪")
        lines.append(
            f"{tier_emoji} {product.name} - "
            f"{product.besitos_price}💰 ({product.tier.value}) {status_emoji}"
        )

    lines.append("")
    lines.append(f"<i>Página {page} de {total_pages} ({total} productos)</i>")

    text = "\n".join(lines)

    # Build keyboard with product buttons
    buttons = []
    for product in products:
        # Product name button -> details
        buttons.append([{
            "text": f"📦 {product.name}",
            "callback_data": f"admin:shop:details:{product.id}"
        }])
        # Toggle button row
        toggle_text = "🔄 Desactivar" if product.is_active else "✅ Activar"
        buttons.append([
            {"text": toggle_text, "callback_data": f"admin:shop:toggle:{product.id}"},
            {"text": "👁️ Ver", "callback_data": f"admin:shop:details:{product.id}"}
        ])

    # Pagination buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append({"text": "⬅️", "callback_data": f"admin:shop:list:page:{page-1}"})
    nav_buttons.append({"text": f"{page}/{total_pages}", "callback_data": "noop"})
    if page < total_pages:
        nav_buttons.append({"text": "➡️", "callback_data": f"admin:shop:list:page:{page+1}"})

    if nav_buttons:
        buttons.append(nav_buttons)

    # Back button
    buttons.append([{"text": "🔙 Volver", "callback_data": "admin:shop"}])

    keyboard = create_inline_keyboard(buttons)

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error mostrando lista de productos: {e}")

    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin:shop:details:"))
async def callback_shop_details(callback: CallbackQuery, session: AsyncSession):
    """
    Handler para ver detalles de un producto.

    Args:
        callback: Callback query con formato "admin:shop:details:{id}"
        session: Sesión de BD
    """
    product_id_str = callback.data.split(":")[-1]
    try:
        product_id = int(product_id_str)
    except ValueError:
        logger.error(f"❌ ID de producto inválido: {product_id_str}")
        await callback.answer("❌ Error: ID inválido", show_alert=True)
        return

    logger.debug(f"👁️ Usuario {callback.from_user.id} viendo detalles de producto {product_id}")

    # Get product with content_set
    result = await session.execute(
        select(ShopProduct)
        .where(ShopProduct.id == product_id)
    )
    product = result.scalar_one_or_none()

    if product is None:
        await callback.answer("❌ Producto no encontrado", show_alert=True)
        return

    # Build details text
    status_text = "Activo 🟢" if product.is_active else "Inactivo 🔴"
    tier_emoji = TIER_EMOJIS.get(product.tier, "⚪")

    content_set_name = product.content_set.name if product.content_set else "N/A"
    file_count = product.content_set.file_count if product.content_set else 0

    text = (
        f"🎩 <b>Detalles del Producto</b>\n\n"
        f"<b>Nombre:</b> {product.name}\n"
        f"<b>Descripción:</b> {product.description or 'Sin descripción'}\n"
        f"<b>Precio:</b> {product.besitos_price} besitos\n"
        f"<b>Precio VIP:</b> {product.vip_price} besitos\n"
        f"<b>Tier:</b> {tier_emoji} {product.tier.value.upper()}\n"
        f"<b>Estado:</b> {status_text}\n"
        f"<b>Compras:</b> {product.purchase_count}\n"
        f"<b>ContentSet:</b> {content_set_name} ({file_count} archivos)\n"
        f"<b>Creado:</b> {product.created_at.strftime('%Y-%m-%d %H:%M')}"
    )

    toggle_text = "🔄 Desactivar" if product.is_active else "✅ Activar"
    keyboard = create_inline_keyboard([
        [{"text": toggle_text, "callback_data": f"admin:shop:toggle:{product.id}"}],
        [{"text": "📋 Lista", "callback_data": "admin:shop:list"}]
    ])

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error mostrando detalles: {e}")

    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin:shop:toggle:"))
async def callback_shop_toggle(callback: CallbackQuery, session: AsyncSession):
    """
    Handler para activar/desactivar un producto.

    Args:
        callback: Callback query con formato "admin:shop:toggle:{id}"
        session: Sesión de BD
    """
    product_id_str = callback.data.split(":")[-1]
    try:
        product_id = int(product_id_str)
    except ValueError:
        logger.error(f"❌ ID de producto inválido: {product_id_str}")
        await callback.answer("❌ Error: ID inválido", show_alert=True)
        return

    logger.debug(f"🔄 Usuario {callback.from_user.id} cambiando estado de producto {product_id}")

    try:
        result = await session.execute(
            select(ShopProduct).where(ShopProduct.id == product_id)
        )
        product = result.scalar_one_or_none()

        if product is None:
            await callback.answer("❌ Producto no encontrado", show_alert=True)
            return

        # Toggle status
        product.is_active = not product.is_active
        await session.commit()

        status_text = "activado 🟢" if product.is_active else "desactivado 🔴"
        logger.info(f"✅ Producto {product_id} ({product.name}) {status_text}")

        await callback.answer(f"✅ Producto {status_text}")

        # Return to product list
        await _show_product_list(callback, session, page=1)

    except Exception as e:
        logger.error(f"❌ Error cambiando estado de producto: {e}")
        await callback.answer("❌ Error al cambiar estado", show_alert=True)


# ============================================================================
# FSM States for Product Creation
# ============================================================================

from bot.states.admin import ShopCreateState


@admin_router.callback_query(F.data == "admin:shop:create:start")
async def callback_shop_create_start(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Inicia el flujo de creación de producto.

    Args:
        callback: Callback query
        state: FSM context
        session: Sesión de BD
    """
    logger.debug(f"➕ Usuario {callback.from_user.id} iniciando creación de producto")

    # Check if there are ContentSets available
    result = await session.execute(
        select(func.count(ContentSet.id)).where(ContentSet.is_active == True)
    )
    content_set_count = result.scalar_one_or_none() or 0

    if content_set_count == 0:
        await callback.answer(
            "❌ No hay ContentSets disponibles. Cree uno primero.",
            show_alert=True
        )
        return

    # Initialize FSM
    await state.set_state(ShopCreateState.waiting_for_name)
    await state.update_data(create_data={})

    text = (
        "🎩 <b>Crear Nuevo Producto</b>\n\n"
        "<i>Paso 1 de 6: Nombre del producto</i>\n\n"
        "Ingrese el nombre del producto:"
    )

    keyboard = create_inline_keyboard([
        [{"text": "❌ Cancelar", "callback_data": "admin:shop"}]
    ])

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error iniciando creación: {e}")

    await callback.answer()


@admin_router.message(ShopCreateState.waiting_for_name)
async def process_product_name(message: Message, state: FSMContext):
    """
    Procesa el nombre del producto.

    Args:
        message: Mensaje del usuario
        state: FSM context
    """
    name = message.text.strip()

    # Validate
    if not name:
        await message.answer(
            "🎩 <b>Atención</b>\n\n"
            "El nombre no puede estar vacío.\n"
            "Por favor, ingrese un nombre válido:",
            parse_mode="HTML"
        )
        return

    if len(name) > 200:
        await message.answer(
            "🎩 <b>Atención</b>\n\n"
            "El nombre es demasiado largo (máximo 200 caracteres).\n"
            "Por favor, ingrese un nombre más corto:",
            parse_mode="HTML"
        )
        return

    # Store and advance
    data = await state.get_data()
    create_data = data.get("create_data", {})
    create_data["name"] = name
    await state.update_data(create_data=create_data)

    await state.set_state(ShopCreateState.waiting_for_description)

    await message.answer(
        "🎩 <b>Crear Nuevo Producto</b>\n\n"
        f"<i>Nombre:</i> {name}\n\n"
        "<i>Paso 2 de 6: Descripción</i>\n\n"
        "Ingrese la descripción del producto:",
        parse_mode="HTML"
    )


@admin_router.message(ShopCreateState.waiting_for_description)
async def process_product_description(message: Message, state: FSMContext):
    """
    Procesa la descripción del producto.

    Args:
        message: Mensaje del usuario
        state: FSM context
    """
    description = message.text.strip()

    # Validate
    if len(description) > 1000:
        await message.answer(
            "🎩 <b>Atención</b>\n\n"
            "La descripción es demasiado larga (máximo 1000 caracteres).\n"
            "Por favor, ingrese una descripción más corta:",
            parse_mode="HTML"
        )
        return

    # Store and advance
    data = await state.get_data()
    create_data = data.get("create_data", {})
    create_data["description"] = description if description else None
    await state.update_data(create_data=create_data)

    await state.set_state(ShopCreateState.waiting_for_price)

    await message.answer(
        "🎩 <b>Crear Nuevo Producto</b>\n\n"
        f"<i>Nombre:</i> {create_data['name']}\n"
        f"<i>Descripción:</i> {description or 'Sin descripción'}\n\n"
        "<i>Paso 3 de 6: Precio</i>\n\n"
        "Ingrese el precio en besitos (número positivo):",
        parse_mode="HTML"
    )


@admin_router.message(ShopCreateState.waiting_for_price)
async def process_product_price(message: Message, state: FSMContext):
    """
    Procesa el precio del producto.

    Args:
        message: Mensaje del usuario
        state: FSM context
    """
    price_text = message.text.strip()

    # Validate
    try:
        price = int(price_text)
        if price <= 0:
            raise ValueError("Price must be positive")
    except ValueError:
        await message.answer(
            "🎩 <b>Atención</b>\n\n"
            "El precio debe ser un número positivo.\n"
            "Por favor, ingrese un valor válido:",
            parse_mode="HTML"
        )
        return

    # Store and advance
    data = await state.get_data()
    create_data = data.get("create_data", {})
    create_data["price"] = price
    await state.update_data(create_data=create_data)

    await state.set_state(ShopCreateState.waiting_for_tier)

    await message.answer(
        "🎩 <b>Crear Nuevo Producto</b>\n\n"
        f"<i>Nombre:</i> {create_data['name']}\n"
        f"<i>Precio:</i> {price} besitos\n\n"
        "<i>Paso 4 de 6: Tier de acceso</i>\n\n"
        "Seleccione el nivel de acceso:",
        parse_mode="HTML",
        reply_markup=create_inline_keyboard([
            [{"text": "⚪ FREE", "callback_data": "tier:free"}],
            [{"text": "🟡 VIP", "callback_data": "tier:vip"}],
            [{"text": "🔴 PREMIUM", "callback_data": "tier:premium"}]
        ])
    )


@admin_router.callback_query(
    F.data.startswith("tier:"),
    ShopCreateState.waiting_for_tier
)
async def process_product_tier(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Procesa la selección de tier.

    Args:
        callback: Callback query con formato "tier:{value}"
        state: FSM context
        session: Sesión de BD
    """
    tier_value = callback.data.split(":")[-1]

    try:
        tier = ContentTier(tier_value)
    except ValueError:
        await callback.answer("❌ Tier inválido", show_alert=True)
        return

    # Store and advance
    data = await state.get_data()
    create_data = data.get("create_data", {})
    create_data["tier"] = tier
    await state.update_data(create_data=create_data)

    await state.set_state(ShopCreateState.waiting_for_content_set)

    # Get available ContentSets
    result = await session.execute(
        select(ContentSet)
        .where(ContentSet.is_active == True)
        .order_by(ContentSet.name)
    )
    content_sets = list(result.scalars().all())

    if not content_sets:
        await callback.answer(
            "❌ No hay ContentSets disponibles.",
            show_alert=True
        )
        await state.clear()
        return

    # Build ContentSet selection keyboard
    buttons = []
    for cs in content_sets:
        buttons.append([{
            "text": f"{cs.name} ({cs.file_count} archivos)",
            "callback_data": f"content_set:{cs.id}"
        }])

    buttons.append([{"text": "❌ Cancelar", "callback_data": "admin:shop"}])

    text = (
        "🎩 <b>Crear Nuevo Producto</b>\n\n"
        f"<i>Nombre:</i> {create_data['name']}\n"
        f"<i>Precio:</i> {create_data['price']} besitos\n"
        f"<i>Tier:</i> {TIER_EMOJIS.get(tier, '⚪')} {tier.value.upper()}\n\n"
        "<i>Paso 5 de 6: ContentSet</i>\n\n"
        "Seleccione el conjunto de contenido:"
    )

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=create_inline_keyboard(buttons),
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error mostrando ContentSets: {e}")

    await callback.answer()


@admin_router.callback_query(
    F.data.startswith("content_set:"),
    ShopCreateState.waiting_for_content_set
)
async def process_product_content_set(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Procesa la selección de ContentSet y muestra confirmación.

    Args:
        callback: Callback query con formato "content_set:{id}"
        state: FSM context
        session: Sesión de BD
    """
    content_set_id_str = callback.data.split(":")[-1]
    try:
        content_set_id = int(content_set_id_str)
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    # Verify ContentSet exists
    result = await session.execute(
        select(ContentSet).where(ContentSet.id == content_set_id)
    )
    content_set = result.scalar_one_or_none()

    if content_set is None:
        await callback.answer("❌ ContentSet no encontrado", show_alert=True)
        return

    # Store and advance
    data = await state.get_data()
    create_data = data.get("create_data", {})
    create_data["content_set_id"] = content_set_id
    create_data["content_set_name"] = content_set.name
    await state.update_data(create_data=create_data)

    await state.set_state(ShopCreateState.waiting_for_confirmation)

    tier = create_data["tier"]
    vip_price = int(create_data["price"] * 0.8)  # 20% discount default

    text = (
        "🎩 <b>Confirmar Creación</b>\n\n"
        f"<b>Nombre:</b> {create_data['name']}\n"
        f"<b>Descripción:</b> {create_data.get('description') or 'Sin descripción'}\n"
        f"<b>Precio:</b> {create_data['price']} besitos\n"
        f"<b>Precio VIP:</b> {vip_price} besitos\n"
        f"<b>Tier:</b> {TIER_EMOJIS.get(tier, '⚪')} {tier.value.upper()}\n"
        f"<b>ContentSet:</b> {content_set.name}\n\n"
        "<i>¿Crear este producto?</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "✅ Confirmar", "callback_data": "shop:create:confirm"}],
        [{"text": "❌ Cancelar", "callback_data": "admin:shop"}]
    ])

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error mostrando confirmación: {e}")

    await callback.answer()


@admin_router.callback_query(
    F.data == "shop:create:confirm",
    ShopCreateState.waiting_for_confirmation
)
async def process_product_creation(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Crea el producto final.

    Args:
        callback: Callback query
        state: FSM context
        session: Sesión de BD
    """
    data = await state.get_data()
    create_data = data.get("create_data", {})

    if not create_data:
        await callback.answer("❌ Error: Datos no encontrados", show_alert=True)
        await state.clear()
        return

    try:
        # Calculate VIP price (20% discount)
        price = create_data["price"]
        vip_price = int(price * 0.8)

        # Create product
        product = ShopProduct(
            name=create_data["name"],
            description=create_data.get("description"),
            content_set_id=create_data["content_set_id"],
            besitos_price=price,
            vip_discount_percentage=20,  # Default 20% discount
            vip_besitos_price=vip_price,
            tier=create_data["tier"],
            is_active=True,
            purchase_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        session.add(product)
        await session.commit()

        logger.info(
            f"✅ Producto creado: {product.name} (ID: {product.id}) "
            f"por usuario {callback.from_user.id}"
        )

        await callback.answer("✅ Producto creado exitosamente")

        # Clear state
        await state.clear()

        # Show success message and return to shop menu
        text = (
            "🎩 <b>Producto Creado</b>\n\n"
            f"<b>{product.name}</b> ha sido agregado al catálogo.\n\n"
            f"Precio: {product.besitos_price} besitos\n"
            f"Precio VIP: {product.vip_price} besitos\n"
            f"Estado: Activo 🟢"
        )

        keyboard = create_inline_keyboard([
            [{"text": "📋 Ver Productos", "callback_data": "admin:shop:list"}],
            [{"text": "➕ Crear Otro", "callback_data": "admin:shop:create:start"}],
            [{"text": "🔙 Menú Tienda", "callback_data": "admin:shop"}]
        ])

        try:
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                logger.error(f"❌ Error mostrando éxito: {e}")

    except Exception as e:
        logger.error(f"❌ Error creando producto: {e}")
        await callback.answer("❌ Error al crear producto", show_alert=True)
        await state.clear()
