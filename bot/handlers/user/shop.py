"""
Shop Handlers - Gestión de tienda y compra de contenido.

Handlers:
- shop_catalog_handler: Muestra catálogo de productos
- shop_product_detail_handler: Muestra detalle de producto con precios VIP/Free
- shop_purchase_handler: Procesa confirmación de compra
- shop_confirm_purchase_handler: Ejecuta compra confirmada
- shop_history_handler: Muestra historial de compras
- shop_earn_besitos_handler: Redirige a opciones de ganar besitos

Voz: Lucien (🎩) - Formal, elegante, mayordomo
"""
import logging
from typing import List, Optional

from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    InputMediaPhoto, InputMediaVideo
)
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.container import ServiceContainer
from bot.database.enums import ContentTier, ContentType, TransactionType
from bot.database.models import ShopProduct, UserContentAccess
from datetime import datetime, timezone
from sqlalchemy import update as sa_update

logger = logging.getLogger(__name__)

# Router para handlers de tienda
shop_router = Router(name="shop")

# DatabaseMiddleware is applied globally in main.py - no local middleware needed


# ============================================================================
# LUCIEN'S VOICE MESSAGES
# ============================================================================

def _get_lucien_header() -> str:
    """Retorna el encabezado estándar de Lucien."""
    return "🎩 <b>Lucien:</b>"


def _get_catalog_header(balance: int) -> str:
    """
    Mensaje de encabezado del catálogo.

    Args:
        balance: Balance actual de besitos del usuario

    Returns:
        Mensaje con voz de Lucien
    """
    return f"""{_get_lucien_header()}

<i>Bienvenido a nuestra galería de curiosidades...</i>

💰 <b>Su balance:</b> {balance} besitos

<i>Aquí encontrará contenido exclusivo seleccionado por Diana.</i>"""


def _get_empty_catalog_message() -> str:
    """Mensaje cuando el catálogo está vacío."""
    return f"""{_get_lucien_header()}

<i>Oh... parece que nuestra galería está momentáneamente vacía.</i>

<i>Diana está preparando nuevo contenido. Vuelva más tarde.</i>"""


def _get_product_detail_message(
    name: str,
    description: str,
    regular_price: int,
    vip_price: int,
    user_role: str,
    file_count: int,
    content_type: str,
    is_owned: bool
) -> str:
    """
    Mensaje de detalle de producto con precios diferenciados.

    Args:
        name: Nombre del producto
        description: Descripción del producto
        regular_price: Precio regular (Free)
        vip_price: Precio VIP
        user_role: "FREE" o "VIP"
        file_count: Cantidad de archivos
        content_type: Tipo de contenido
        is_owned: Si el usuario ya posee el contenido

    Returns:
        Mensaje formateado con voz de Lucien
    """
    # Determine emoji based on content type
    type_emojis = {
        "photo_set": "📸",
        "video": "🎬",
        "audio": "🎙️",
        "mixed": "🎁"
    }
    type_emoji = type_emojis.get(content_type, "🎁")

    # Build price display based on user role
    if user_role == "VIP":
        price_display = f"""💎 <b>Precio VIP:</b> {vip_price} besitos
~~{regular_price} besitos~~

<i>Privilegio aplicado a su membresía VIP</i>"""
    else:
        price_display = f"""💰 <b>Precio:</b> {regular_price} besitos
💎 Precio VIP: {vip_price} besitos

<i>Este beneficio se aplica únicamente a membresías VIP</i>"""

    ownership_text = ""
    if is_owned:
        ownership_text = "\n✅ <i>Ya posee este contenido</i>\n"

    return f"""{_get_lucien_header()}

{type_emoji} <b>{name}</b>

<i>{description}</i>

{price_display}

📁 <b>Contenido:</b> {file_count} archivo{"s" if file_count != 1 else ""}{ownership_text}"""


def _get_insufficient_funds_message(balance: int, needed: int) -> str:
    """
    Mensaje de fondos insuficientes.

    Args:
        balance: Balance actual
        needed: Besitos necesarios

    Returns:
        Mensaje con voz de Lucien
    """
    return f"""{_get_lucien_header()}

<i>Lamentablemente, su balance es insuficiente para esta adquisición.</i>

💰 <b>Su balance:</b> {balance} besitos
💎 <b>Necesario:</b> {needed} besitos

<i>Le sugiero visitar nuestras opciones para aumentar su capital...</i>"""


def _get_purchase_success_message(name: str, price: int, file_count: int) -> str:
    """
    Mensaje de compra exitosa.

    Args:
        name: Nombre del producto
        price: Precio pagado
        file_count: Cantidad de archivos

    Returns:
        Mensaje con voz de Lucien
    """
    return f"""{_get_lucien_header()}

<i>Excelente elección...</i>

✅ <b>Adquisición completada</b>

🎁 <b>{name}</b>
💰 <b>Precio:</b> {price} besitos
📁 <b>Archivos:</b> {file_count}

<i>Enviando su contenido ahora...</i>"""


def _get_purchase_error_message(reason: str) -> str:
    """
    Mensaje de error en compra.

    Args:
        reason: Razón del error

    Returns:
        Mensaje con voz de Lucien
    """
    return f"""{_get_lucien_header()}

<i>Hmm... ha ocurrido un inconveniente con su adquisición.</i>

<i>{reason}</i>

<i>Por favor, inténtelo nuevamente o contacte a Diana si el problema persiste.</i>"""


def _get_vip_only_message() -> str:
    """Mensaje para contenido exclusivo VIP."""
    return f"""{_get_lucien_header()}

<i>Este contenido es exclusivo para miembros VIP.</i>

💎 <b>Acceso restringido</b>

<i>Si desea acceder a este y otros privilegios, considere unirse a nuestra membresía VIP.</i>

<i>Diana reserva lo mejor para quienes demuestran su compromiso...</i>"""


def _get_repurchase_confirmation_message(name: str) -> str:
    """
    Mensaje de confirmación para recompra.

    Args:
        name: Nombre del producto

    Returns:
        Mensaje con voz de Lucien
    """
    return f"""{_get_lucien_header()}

<i>Veo que ya posee este contenido...</i>

🎁 <b>{name}</b>

¿Desea adquirirlo nuevamente?

<i>Nota: Se le cobrará el precio completo nuevamente.</i>"""


def _get_history_header() -> str:
    """Mensaje de encabezado del historial."""
    return f"""{_get_lucien_header()}

<i>Su historial de adquisiciones...</i>

<i>Aquí encontrará todos sus contenidos adquiridos.</i>"""


def _get_empty_history_message() -> str:
    """Mensaje cuando no hay compras."""
    return f"""{_get_lucien_header()}

<i>Aún no ha realizado ninguna adquisición...</i>

💡 <i>Visite nuestra tienda para explorar el contenido disponible.</i>"""


def _get_earn_besitos_message() -> str:
    """Mensaje de opciones para ganar besitos."""
    return f"""{_get_lucien_header()}

<i>Le presento las formas de aumentar su capital...</i>

🎁 <b>Regalo Diario</b> - Reclame cada 24h
🔥 <b>Reacciones</b> - Interactúe con contenido

<i>La constancia es recompensada en esta casa.</i>"""


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_catalog_keyboard(
    products: List,
    page: int,
    total_pages: int,
    user_role: str
) -> InlineKeyboardMarkup:
    """
    Genera teclado para el catálogo.

    Args:
        products: Lista de productos
        page: Página actual
        total_pages: Total de páginas
        user_role: Rol del usuario para mostrar precios

    Returns:
        InlineKeyboardMarkup con productos y navegación
    """
    buttons = []

    # Product buttons (vertical list - one per row)
    for product in products:
        # Show appropriate price based on role
        if user_role == "VIP":
            price_text = f"💎 {product.vip_price}"
        else:
            price_text = f"💰 {product.besitos_price}"

        buttons.append([InlineKeyboardButton(
            text=f"{product.name} ({price_text})",
            callback_data=f"shop_product:{product.id}"
        )])

    # Navigation row
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(
            text="◀️ Anterior",
            callback_data=f"shop_catalog_page:{page - 1}"
        ))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(
            text="Siguiente ▶️",
            callback_data=f"shop_catalog_page:{page + 1}"
        ))
    if nav_buttons:
        buttons.append(nav_buttons)

    # History button
    buttons.append([InlineKeyboardButton(
        text="📜 Ver historial",
        callback_data="shop_history"
    )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_product_detail_keyboard(
    product_id: int,
    can_purchase: bool,
    is_owned: bool,
    is_vip_only: bool,
    user_role: str
) -> InlineKeyboardMarkup:
    """
    Genera teclado para detalle de producto.

    Args:
        product_id: ID del producto
        can_purchase: Si puede comprar (suficiente balance)
        is_owned: Si ya posee el contenido
        is_vip_only: Si es contenido VIP-only
        user_role: Rol del usuario

    Returns:
        InlineKeyboardMarkup
    """
    buttons = []

    if is_vip_only and user_role != "VIP":
        # VIP-only content for FREE user - show return only
        buttons.append([InlineKeyboardButton(
            text="🔙 Volver al catálogo",
            callback_data="shop_catalog"
        )])
    elif not can_purchase:
        # Insufficient funds
        buttons.append([InlineKeyboardButton(
            text="💰 Cómo ganar besitos",
            callback_data="shop_earn_besitos"
        )])
        buttons.append([InlineKeyboardButton(
            text="🔙 Volver al catálogo",
            callback_data="shop_catalog"
        )])
    else:
        # Can purchase
        if is_owned:
            # Already owned - show repurchase confirmation
            buttons.append([InlineKeyboardButton(
                text="🛒 Comprar nuevamente",
                callback_data=f"shop_buy:{product_id}:repurchase"
            )])
        else:
            # Normal purchase
            buttons.append([InlineKeyboardButton(
                text="🛒 Comprar ahora",
                callback_data=f"shop_buy:{product_id}"
            )])
        buttons.append([InlineKeyboardButton(
            text="🔙 Volver al catálogo",
            callback_data="shop_catalog"
        )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_purchase_confirmation_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """
    Teclado de confirmación de compra.

    Args:
        product_id: ID del producto

    Returns:
        InlineKeyboardMarkup con confirmar/cancelar
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Confirmar compra",
            callback_data=f"shop_confirm:{product_id}"
        )],
        [InlineKeyboardButton(
            text="❌ Cancelar",
            callback_data=f"shop_product:{product_id}"
        )]
    ])


def get_repurchase_confirmation_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """
    Teclado de confirmación para recompra.

    Args:
        product_id: ID del producto

    Returns:
        InlineKeyboardMarkup
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Sí, comprar nuevamente",
            callback_data=f"shop_confirm:{product_id}:repurchase"
        )],
        [InlineKeyboardButton(
            text="❌ No, volver",
            callback_data=f"shop_product:{product_id}"
        )]
    ])


def get_history_keyboard(
    page: int,
    total_pages: int,
    has_purchases: bool
) -> InlineKeyboardMarkup:
    """
    Teclado para historial de compras.

    Args:
        page: Página actual
        total_pages: Total de páginas
        has_purchases: Si hay compras para mostrar

    Returns:
        InlineKeyboardMarkup
    """
    buttons = []

    # Navigation row
    if has_purchases and total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(
                text="◀️ Anterior",
                callback_data=f"shop_history_page:{page - 1}"
            ))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(
                text="Siguiente ▶️",
                callback_data=f"shop_history_page:{page + 1}"
            ))
        if nav_buttons:
            buttons.append(nav_buttons)

    # Back to catalog
    buttons.append([InlineKeyboardButton(
        text="🛍️ Volver a la tienda",
        callback_data="shop_catalog"
    )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_earn_besitos_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado para opciones de ganar besitos.

    Returns:
        InlineKeyboardMarkup
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🎁 Reclamar regalo diario",
            callback_data="streak:claim_daily"
        )],
        [InlineKeyboardButton(
            text="🔙 Volver al catálogo",
            callback_data="shop_catalog"
        )]
    ])


# ============================================================================
# HANDLERS
# ============================================================================

@shop_router.callback_query(F.data == "shop_catalog")
@shop_router.message(F.text == "🛍️ Tienda")
async def shop_catalog_handler(
    event: Message | CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """
    Show shop catalog with product list (vertical layout).

    Display: Only product names with prices, minimalistic
    Navigation: Prev/Next pagination
    Ordering: By price ascending
    """
    user_id = event.from_user.id

    logger.info(f"🛍️ Usuario {user_id} viendo catálogo")

    try:
        # Get user role
        user_role_obj = await container.role_detection.get_user_role(user_id)
        user_role = user_role_obj.value

        # Get user balance
        balance = await container.wallet.get_balance(user_id)

        # Get catalog (page 1 by default)
        products, total = await container.shop.browse_catalog(
            user_role=user_role,
            page=1,
            per_page=5
        )

        # Calculate total pages
        total_pages = (total + 4) // 5 if total > 0 else 1

        if not products:
            # Empty catalog
            text = _get_empty_catalog_message()
            if isinstance(event, CallbackQuery):
                await event.message.edit_text(text=text, parse_mode="HTML")
            else:
                await event.answer(text=text, parse_mode="HTML")
            return

        # Build message
        text = _get_catalog_header(balance)

        # Build keyboard
        keyboard = get_catalog_keyboard(products, 1, total_pages, user_role)

        # Send/update message
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await event.answer(text=text, reply_markup=keyboard, parse_mode="HTML")

        logger.debug(f"✅ Catalog shown to user {user_id}: {len(products)} products")

    except Exception as e:
        logger.error(f"❌ Error mostrando catálogo a usuario {user_id}: {e}", exc_info=True)
        error_text = f"{_get_lucien_header()}\n\n<i>Ha ocurrido un inconveniente al cargar el catálogo...</i>"

        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text=error_text, parse_mode="HTML")
        else:
            await event.answer(text=error_text, parse_mode="HTML")


@shop_router.callback_query(F.data.startswith("shop_catalog_page:"))
async def shop_catalog_page_handler(
    callback: CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """Handle catalog pagination."""
    user_id = callback.from_user.id

    try:
        # Extract page number
        page = int(callback.data.split(":")[1])

        # Get user role
        user_role_obj = await container.role_detection.get_user_role(user_id)
        user_role = user_role_obj.value

        # Get user balance
        balance = await container.wallet.get_balance(user_id)

        # Get catalog for page
        products, total = await container.shop.browse_catalog(
            user_role=user_role,
            page=page,
            per_page=5
        )

        total_pages = (total + 4) // 5 if total > 0 else 1

        # Build message and keyboard
        text = _get_catalog_header(balance)
        keyboard = get_catalog_keyboard(products, page, total_pages, user_role)

        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

    except Exception as e:
        logger.error(f"❌ Error en paginación de catálogo: {e}", exc_info=True)
        await callback.answer("❌ Error al cambiar de página", show_alert=True)


@shop_router.callback_query(F.data.startswith("shop_product:"))
async def shop_product_detail_handler(
    callback: CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """
    Show product detail with VIP/Free price differentiation.

    VIP view: Strikethrough regular price, prominent VIP price with 💎
    Free view: Regular price prominent, VIP price attenuated
    """
    user_id = callback.from_user.id

    try:
        # Extract product_id
        parts = callback.data.split(":")
        product_id = int(parts[1])

        # Get user role
        user_role_obj = await container.role_detection.get_user_role(user_id)
        user_role = user_role_obj.value

        # Get user balance
        balance = await container.wallet.get_balance(user_id)

        # Get product details
        details, status = await container.shop.get_product_details(product_id, user_id)

        if status == "product_not_found" or details is None:
            await callback.answer("❌ Producto no encontrado", show_alert=True)
            return

        product = details["product"]
        content_set = details["content_set"]

        # Check if VIP-only
        is_vip_only = product.tier in [ContentTier.VIP, ContentTier.PREMIUM]

        # Calculate if user can purchase
        price_to_pay = details["vip_price"] if user_role == "VIP" else details["regular_price"]
        can_purchase = balance >= price_to_pay and (not is_vip_only or user_role == "VIP")

        # Build message
        text = _get_product_detail_message(
            name=product.name,
            description=product.description or "Sin descripción",
            regular_price=details["regular_price"],
            vip_price=details["vip_price"],
            user_role=user_role,
            file_count=details["file_count"],
            content_type=content_set.content_type.value if content_set else "mixed",
            is_owned=details["is_owned"]
        )

        # Build keyboard
        if is_vip_only and user_role != "VIP":
            # VIP-only for FREE user
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔙 Volver al catálogo",
                    callback_data="shop_catalog"
                )]
            ])
        else:
            keyboard = get_product_detail_keyboard(
                product_id=product_id,
                can_purchase=can_purchase,
                is_owned=details["is_owned"],
                is_vip_only=is_vip_only,
                user_role=user_role
            )

        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

        logger.debug(f"✅ Product detail shown: product={product_id}, user={user_id}")

    except Exception as e:
        logger.error(f"❌ Error mostrando detalle de producto: {e}", exc_info=True)
        await callback.answer("❌ Error al cargar el producto", show_alert=True)


@shop_router.callback_query(F.data.startswith("shop_buy:"))
async def shop_purchase_handler(
    callback: CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """
    Handle purchase button click.

    Flow:
    1. Show confirmation with price summary
    2. On confirm: execute purchase
    3. Deliver content immediately
    4. Show success message with file count
    """
    user_id = callback.from_user.id

    try:
        # Extract product_id and check for repurchase flag
        parts = callback.data.split(":")
        product_id = int(parts[1])
        is_repurchase = len(parts) > 2 and parts[2] == "repurchase"

        # Get user role
        user_role_obj = await container.role_detection.get_user_role(user_id)
        user_role = user_role_obj.value

        # Get user balance
        balance = await container.wallet.get_balance(user_id)

        # Validate purchase
        can_purchase, reason, details = await container.shop.validate_purchase(
            user_id=user_id,
            product_id=product_id,
            user_role=user_role
        )

        if not can_purchase:
            if reason == "insufficient_funds":
                # Show insufficient funds message with earn options
                needed = details["price_to_pay"] if details else 0
                text = _get_insufficient_funds_message(balance, needed)
                keyboard = get_earn_besitos_keyboard()
                await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
                await callback.answer()
                return
            elif reason == "vip_only":
                # Show VIP-only message
                text = _get_vip_only_message()
                await callback.message.edit_text(text=text, parse_mode="HTML")
                await callback.answer()
                return
            elif reason == "already_owned" and not is_repurchase:
                # Show repurchase confirmation
                product = details["product"] if details else None
                if product:
                    text = _get_repurchase_confirmation_message(product.name)
                    keyboard = get_repurchase_confirmation_keyboard(product_id)
                    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
                    await callback.answer()
                    return

        # Show purchase confirmation
        product = details["product"] if details else None
        if product:
            price = details["price_to_pay"] if details else product.vip_price if user_role == "VIP" else product.besitos_price

            text = f"""{_get_lucien_header()}

<i>Confirme su adquisición...</i>

🎁 <b>{product.name}</b>
💰 <b>Precio:</b> {price} besitos
💎 <b>Su balance:</b> {balance} besitos

<i>¿Desea proceder con la compra?</i>"""

            keyboard = get_purchase_confirmation_keyboard(product_id)
            await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer()

    except Exception as e:
        logger.error(f"❌ Error en proceso de compra: {e}", exc_info=True)
        await callback.answer("❌ Error al procesar la compra", show_alert=True)


def _get_delivery_error_with_refund_message(product_name: str) -> str:
    """
    Mensaje de error en entrega con notificación de reembolso.

    Args:
        product_name: Nombre del producto

    Returns:
        Mensaje con voz de Lucien informando del reembolso
    """
    return f"""{_get_lucien_header()}

<i>Ha ocurrido un inconveniente técnico al entregar su contenido.</i>

🎁 <b>{product_name}</b>

💰 <b>Su saldo ha sido restaurado completamente.</b>

<i>Por favor, inténtelo nuevamente más tarde o contacte a Diana si el problema persiste.</i>"""


@shop_router.callback_query(F.data.startswith("shop_confirm:"))
async def shop_confirm_purchase_handler(
    callback: CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """
    Execute confirmed purchase with atomic delivery and automatic refund.

    Flow:
    1. Validate purchase (product exists, user has balance, etc.)
    2. Spend besitos (atomic operation)
    3. Create access record
    4. Deliver content
    5. If delivery fails: refund besitos automatically
    """
    user_id = callback.from_user.id

    try:
        # Extract product_id and check for repurchase flag
        parts = callback.data.split(":")
        product_id = int(parts[1])
        force_repurchase = len(parts) > 2 and parts[2] == "repurchase"

        # Get user role
        user_role_obj = await container.role_detection.get_user_role(user_id)
        user_role = user_role_obj.value

        # Step 1: Validate purchase (without spending)
        can_purchase, reason, details = await container.shop.validate_purchase(
            user_id=user_id,
            product_id=product_id,
            user_role=user_role
        )

        if not can_purchase:
            # Handle validation errors
            error_reason = "No se pudo completar la compra"
            if reason == "insufficient_funds":
                error_reason = "Fondos insuficientes"
            elif reason == "already_owned":
                error_reason = "Ya posee este contenido"
            elif reason == "vip_only":
                error_reason = "Contenido exclusivo VIP"
            elif reason == "product_not_found":
                error_reason = "Producto no encontrado"
            elif reason == "product_inactive":
                error_reason = "Producto no disponible"

            text = _get_purchase_error_message(error_reason)
            await callback.message.edit_text(text=text, parse_mode="HTML")
            await callback.answer("❌ Compra fallida", show_alert=True)
            return

        product = details["product"]
        price_to_pay = details["price_to_pay"]
        is_owned = details["is_owned"]

        # Check for duplicate purchase
        if is_owned and not force_repurchase:
            text = _get_repurchase_confirmation_message(product.name)
            keyboard = get_repurchase_confirmation_keyboard(product_id)
            await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer()
            return

        # Step 2: Spend besitos (atomic)
        spend_success, spend_msg, transaction = await container.wallet.spend_besitos(
            user_id=user_id,
            amount=price_to_pay,
            transaction_type=TransactionType.SPEND_SHOP,
            reason=f"Purchase product #{product_id}: {product.name}",
            metadata={
                "product_id": product_id,
                "content_set_id": product.content_set_id,
                "is_repurchase": is_owned
            }
        )

        if not spend_success:
            logger.warning(f"Purchase failed for user {user_id}: {spend_msg}")
            error_reason = "Error en el procesamiento de pago"
            if spend_msg == "insufficient_funds":
                error_reason = "Fondos insuficientes"
            elif spend_msg == "no_profile":
                error_reason = "Perfil no encontrado"

            text = _get_purchase_error_message(error_reason)
            await callback.message.edit_text(text=text, parse_mode="HTML")
            await callback.answer("❌ Compra fallida", show_alert=True)
            return

        # Get file_ids for delivery
        file_ids = product.content_set.file_ids if product.content_set else []
        content_type = product.content_set.content_type.value if product.content_set else "mixed"

        # Step 3: Deliver content ANTES de crear el registro de acceso en DB.
        # Si el delivery falla, solo se necesita reembolsar los besitos,
        # sin necesidad de rollback de registros de acceso que aún no existen.
        delivery_success = True
        try:
            await deliver_purchased_content(
                bot=callback.bot,
                user_id=user_id,
                file_ids=file_ids,
                content_type=content_type
            )
        except Exception as e:
            delivery_success = False
            logger.error(
                f"❌ Content delivery failed for user {user_id}, product {product_id}: {e}",
                exc_info=True
            )

        if not delivery_success:
            # Reembolsar besitos — el acceso nunca fue creado, no hay rollback de DB necesario
            try:
                refund_success, refund_msg, _ = await container.wallet.admin_credit(
                    user_id=user_id,
                    amount=price_to_pay,
                    reason="reembolso_automatico_fallo_entrega",
                    admin_id=0
                )
                if refund_success:
                    logger.error(
                        f"🔄 Automatic refund executed for user {user_id}: {price_to_pay} besitos "
                        f"(product {product_id}, reason: delivery failure)"
                    )
                else:
                    logger.critical(
                        f"🚨 REFUND FAILED for user {user_id}: {price_to_pay} besitos "
                        f"(product {product_id}, refund error: {refund_msg}). "
                        f"Manual intervention required!"
                    )
            except Exception as refund_error:
                logger.critical(
                    f"🚨 REFUND EXCEPTION for user {user_id}: {price_to_pay} besitos "
                    f"(product {product_id}, error: {refund_error}). "
                    f"Manual intervention required!"
                )

            text = _get_delivery_error_with_refund_message(product.name)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🛍️ Volver a la tienda",
                    callback_data="shop_catalog"
                )]
            ])
            await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer("❌ Error en entrega - Saldo restaurado", show_alert=True)
            return

        # Step 4: Delivery exitoso — crear registro de acceso y actualizar contador
        access_record = UserContentAccess(
            user_id=user_id,
            content_set_id=product.content_set_id,
            shop_product_id=product.id,
            access_type="shop_purchase",
            besitos_paid=price_to_pay,
            is_active=True,
            accessed_at=datetime.now(timezone.utc).replace(tzinfo=None),
            access_metadata={
                "product_name": product.name,
                "is_repurchase": is_owned
            }
        )
        container.shop.session.add(access_record)

        # Actualizar contador de compras de forma atómica
        await container.shop.session.execute(
            sa_update(ShopProduct)
            .where(ShopProduct.id == product_id)
            .values(purchase_count=ShopProduct.purchase_count + 1)
        )
        await container.shop.session.flush()

        # Delivery successful - continue with rewards and success message
        price_paid = price_to_pay

        # Check for unlocked rewards after purchase
        unlocked_rewards = await container.reward.check_rewards_on_event(
            user_id=user_id,
            event_type="purchase_completed",
            event_data={"product_id": product_id, "price_paid": price_paid}
        )

        # Build success message
        base_text = _get_purchase_success_message(
            name=product.name,
            price=price_paid,
            file_count=len(file_ids)
        )

        # Build keyboard
        keyboard_buttons = []

        # If rewards unlocked, add grouped notification
        if unlocked_rewards:
            combined_text = f"""{_get_lucien_header()}

<i>Excelente elección...</i>

✅ <b>Adquisición completada</b>

🎁 <b>{product.name}</b>
💰 <b>Precio:</b> {price_paid} besitos
📁 <b>Archivos:</b> {len(file_ids)}

✨ <b>Nuevas Recompensas Desbloqueadas:</b>
"""
            for reward_info in unlocked_rewards:
                reward = reward_info["reward"]
                combined_text += f"• {reward.name}\n"

            combined_text += "\n<i>Su adquisición abre nuevas puertas.</i>"

            # Add claim rewards button
            keyboard_buttons.append([InlineKeyboardButton(
                text="🏆 Reclamar Recompensas",
                callback_data="my_rewards"
            )])

            text = combined_text
        else:
            text = base_text

        # Add continue button
        keyboard_buttons.append([InlineKeyboardButton(
            text="🛍️ Continuar comprando",
            callback_data="shop_catalog"
        )])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")

        await callback.answer("✅ ¡Compra completada!")

        logger.info(f"✅ User {user_id} purchased product {product_id}: {product.name}")

        if unlocked_rewards:
            logger.info(
                f"✅ User {user_id} unlocked {len(unlocked_rewards)} rewards from purchase"
            )

    except Exception as e:
        logger.error(f"❌ Error confirmando compra: {e}", exc_info=True)
        await callback.answer("❌ Error al confirmar la compra", show_alert=True)


async def deliver_purchased_content(
    bot,
    user_id: int,
    file_ids: List[str],
    content_type: str
) -> None:
    """
    Send content files to user chat.

    Uses bot.send_photo/video/audio for each file_id.
    Groups photos into media group if multiple photos.
    """
    if not file_ids:
        logger.warning(f"No file_ids to deliver for user {user_id}")
        return

    try:
        caption = "🎩 <i>Aquí está su contenido adquirido.</i>"

        if content_type == "photo_set" and len(file_ids) > 1:
            # Send as media group
            media = []
            for i, file_id in enumerate(file_ids):
                if i == 0:
                    media.append(InputMediaPhoto(media=file_id, caption=caption, parse_mode="HTML"))
                else:
                    media.append(InputMediaPhoto(media=file_id))
            await bot.send_media_group(chat_id=user_id, media=media)

        elif content_type == "video":
            # Send video
            await bot.send_video(
                chat_id=user_id,
                video=file_ids[0],
                caption=caption,
                parse_mode="HTML"
            )

        elif content_type == "audio":
            # Send audio
            await bot.send_audio(
                chat_id=user_id,
                audio=file_ids[0],
                caption=caption,
                parse_mode="HTML"
            )

        else:
            # Mixed or single photo - send individually
            for i, file_id in enumerate(file_ids):
                file_caption = caption if i == 0 else None
                await bot.send_photo(
                    chat_id=user_id,
                    photo=file_id,
                    caption=file_caption,
                    parse_mode="HTML"
                )

        logger.info(f"✅ Content delivered to user {user_id}: {len(file_ids)} files")

    except Exception as e:
        logger.error(f"❌ Error delivering content to user {user_id}: {e}", exc_info=True)
        # Send error message to user
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"🎩 <b>Lucien:</b>\n\n<i>Hubo un problema al enviar su contenido. Por favor, contacte a Diana.</i>",
                parse_mode="HTML"
            )
        except Exception:
            pass


@shop_router.callback_query(F.data == "shop_history")
@shop_router.message(F.text == "📜 Historial")
async def shop_history_handler(
    event: Message | CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """Show purchase history with pagination."""
    user_id = event.from_user.id

    try:
        # Get purchase history (page 1)
        purchases, total = await container.shop.get_purchase_history(
            user_id=user_id,
            page=1,
            per_page=5
        )

        if not purchases:
            # Empty history
            text = _get_empty_history_message()
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🛍️ Ir a la tienda",
                    callback_data="shop_catalog"
                )]
            ])
        else:
            # Build history message
            text = _get_history_header() + "\n\n"

            for purchase in purchases:
                date_str = purchase["accessed_at"].strftime("%d/%m/%Y") if purchase["accessed_at"] else "Fecha desconocida"
                status_emoji = "✅" if purchase["is_active"] else "⏳"
                text += f"{status_emoji} <b>{purchase['product_name']}</b>\n"
                text += f"   💰 {purchase['besitos_paid']} besitos | 📅 {date_str}\n\n"

            total_pages = (total + 4) // 5 if total > 0 else 1
            keyboard = get_history_keyboard(1, total_pages, True)

        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
            await event.answer()
        else:
            await event.answer(text=text, reply_markup=keyboard, parse_mode="HTML")

        logger.debug(f"✅ History shown to user {user_id}: {len(purchases)} purchases")

    except Exception as e:
        logger.error(f"❌ Error mostrando historial: {e}", exc_info=True)
        error_text = f"{_get_lucien_header()}\n\n<i>Ha ocurrido un inconveniente al cargar su historial...</i>"

        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text=error_text, parse_mode="HTML")
        else:
            await event.answer(text=error_text, parse_mode="HTML")


@shop_router.callback_query(F.data.startswith("shop_history_page:"))
async def shop_history_page_handler(
    callback: CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """Handle history pagination."""
    user_id = callback.from_user.id

    try:
        # Extract page number
        page = int(callback.data.split(":")[1])

        # Get purchase history
        purchases, total = await container.shop.get_purchase_history(
            user_id=user_id,
            page=page,
            per_page=5
        )

        # Build history message
        text = _get_history_header() + "\n\n"

        for purchase in purchases:
            date_str = purchase["accessed_at"].strftime("%d/%m/%Y") if purchase["accessed_at"] else "Fecha desconocida"
            status_emoji = "✅" if purchase["is_active"] else "⏳"
            text += f"{status_emoji} <b>{purchase['product_name']}</b>\n"
            text += f"   💰 {purchase['besitos_paid']} besitos | 📅 {date_str}\n\n"

        total_pages = (total + 4) // 5 if total > 0 else 1
        keyboard = get_history_keyboard(page, total_pages, len(purchases) > 0)

        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

    except Exception as e:
        logger.error(f"❌ Error en paginación de historial: {e}", exc_info=True)
        await callback.answer("❌ Error al cambiar de página", show_alert=True)


@shop_router.callback_query(F.data == "shop_earn_besitos")
async def shop_earn_besitos_handler(
    callback: CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """Redirect to besitos earning options when balance insufficient."""
    try:
        text = _get_earn_besitos_message()
        keyboard = get_earn_besitos_keyboard()

        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

        logger.debug(f"✅ Earn besitos shown to user {callback.from_user.id}")

    except Exception as e:
        logger.error(f"❌ Error mostrando opciones de ganar besitos: {e}", exc_info=True)
        await callback.answer("❌ Error al cargar opciones", show_alert=True)
