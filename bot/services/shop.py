"""
Shop Service - Gestión de tienda y compras de contenido.

Responsabilidades:
- Catálogo de productos con paginación y filtros
- Validación de compras (balance, tier, ownership)
- Transacciones atómicas de compra (deducir besitos + crear acceso)
- Entrega de contenido (file_ids para Telegram)
- Historial de compras por usuario

Patrones:
- Integración con WalletService para gasto atómico
- Verificación de ownership para prevenir compras duplicadas
- Soporte para repurchase con confirmación
- Precios diferenciados FREE vs VIP
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any

from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import ContentSet, ShopProduct, UserContentAccess
from bot.database.enums import ContentTier, TransactionType

logger = logging.getLogger(__name__)


class ShopService:
    """
    Service para gestionar la tienda de contenido del sistema de gamificación.

    Flujo de compra:
    1. Usuario browse_catalog() para ver productos
    2. Usuario selecciona producto → get_product_details() para ver precio
    3. validate_purchase() verifica balance y restricciones
    4. purchase_product() ejecuta: valida, gasta besitos, crea UserContentAccess
    5. deliver_content() retorna file_ids para envío vía bot

    Precios:
    - FREE users: pagan besitos_price
    - VIP users: pagan vip_price (con descuento aplicado)

    Ownership:
    - Un usuario no puede comprar contenido que ya posee
    - Se puede forzar repurchase con force_repurchase=True
    """

    def __init__(self, session: AsyncSession, wallet_service=None):
        """
        Inicializa el ShopService.

        Args:
            session: Sesión de base de datos async
            wallet_service: WalletService opcional para operaciones de pago
        """
        self.session = session
        self.wallet_service = wallet_service
        self.logger = logging.getLogger(__name__)

    async def browse_catalog(
        self,
        user_role: str = "FREE",
        page: int = 1,
        per_page: int = 5,
        tier: Optional[ContentTier] = None
    ) -> Tuple[List[ShopProduct], int]:
        """
        Browse shop catalog with pagination, ordered by price ascending.

        Args:
            user_role: "FREE" or "VIP" for price display context
            page: Page number (1-indexed)
            per_page: Items per page
            tier: Optional filter by content tier

        Returns:
            Tuple of (products list, total count)
        """
        # Build base query for active products
        base_query = select(ShopProduct).where(ShopProduct.is_active == True)

        # Apply tier filter if provided
        if tier is not None:
            base_query = base_query.where(ShopProduct.tier == tier)

        # Get total count
        count_query = select(func.count(ShopProduct.id)).where(ShopProduct.is_active == True)
        if tier is not None:
            count_query = count_query.where(ShopProduct.tier == tier)

        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one_or_none() or 0

        # Apply ordering (by price ascending) and pagination
        offset = (page - 1) * per_page
        query = (
            base_query
            .order_by(ShopProduct.besitos_price.asc())
            .offset(offset)
            .limit(per_page)
        )

        result = await self.session.execute(query)
        products = list(result.scalars().all())

        self.logger.debug(
            f"Catalog browse: role={user_role}, page={page}, "
            f"tier={tier.value if tier else 'all'}, found={len(products)}/{total}"
        )

        return products, total

    async def get_product_details(
        self,
        product_id: int,
        user_id: int
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Get full product details with user-specific pricing.

        Args:
            product_id: ID of the product to retrieve
            user_id: ID of the user for ownership check

        Returns:
            Tuple of (product dict or None, status message)
            Product dict includes:
            - product: ShopProduct object
            - content_set: ContentSet object
            - regular_price: int
            - vip_price: int
            - user_price: int (based on user's role)
            - is_owned: bool
            - file_count: int
        """
        # Get product with content_set relationship
        result = await self.session.execute(
            select(ShopProduct)
            .where(ShopProduct.id == product_id)
            .where(ShopProduct.is_active == True)
        )
        product = result.scalar_one_or_none()

        if product is None:
            return None, "product_not_found"

        # Check ownership
        is_owned = await self.check_ownership(user_id, product.content_set_id)

        # Build response dict
        details = {
            "product": product,
            "content_set": product.content_set,
            "regular_price": product.besitos_price,
            "vip_price": product.vip_price,
            "user_price": product.vip_price,  # Default to VIP price (will be overridden)
            "is_owned": is_owned,
            "file_count": product.content_set.file_count if product.content_set else 0
        }

        return details, "ok"

    async def validate_purchase(
        self,
        user_id: int,
        product_id: int,
        user_role: str = "FREE"
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Validate if user can purchase product.

        Checks:
        1. Product exists and is active
        2. User has sufficient balance
        3. Product tier allows purchase (VIP-only check)

        Args:
            user_id: ID of the user
            product_id: ID of the product to purchase
            user_role: "FREE" or "VIP"

        Returns:
            Tuple of (can_purchase, reason_code, details_dict)
            reason_code: "ok", "product_not_found", "product_inactive",
                        "insufficient_funds", "vip_only", "already_owned"
            details_dict: includes product, price_to_pay, user_balance, is_owned
        """
        # Get product
        result = await self.session.execute(
            select(ShopProduct)
            .where(ShopProduct.id == product_id)
        )
        product = result.scalar_one_or_none()

        if product is None:
            return False, "product_not_found", None

        if not product.is_active:
            return False, "product_inactive", None

        # Verificar que el ContentSet asociado esté activo
        if product.content_set_id:
            cs_result = await self.session.execute(
                select(ContentSet.id).where(
                    ContentSet.id == product.content_set_id,
                    ContentSet.is_active == True
                )
            )
            if cs_result.scalar_one_or_none() is None:
                return False, "product_inactive", None

        # Check tier restrictions
        if product.tier == ContentTier.VIP and user_role == "FREE":
            return False, "vip_only", None

        if product.tier == ContentTier.PREMIUM and user_role == "FREE":
            return False, "vip_only", None

        # Check ownership
        is_owned = await self.check_ownership(user_id, product.content_set_id)

        # Calculate price based on user role
        price_to_pay = product.vip_price if user_role == "VIP" else product.besitos_price

        # Check balance if wallet_service available
        user_balance = 0
        if self.wallet_service is not None:
            user_balance = await self.wallet_service.get_balance(user_id)

            if user_balance < price_to_pay:
                return False, "insufficient_funds", {
                    "product": product,
                    "price_to_pay": price_to_pay,
                    "user_balance": user_balance,
                    "is_owned": is_owned
                }

        details = {
            "product": product,
            "price_to_pay": price_to_pay,
            "user_balance": user_balance,
            "is_owned": is_owned
        }

        return True, "ok", details

    async def purchase_product(
        self,
        user_id: int,
        product_id: int,
        user_role: str = "FREE",
        force_repurchase: bool = False
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Execute purchase: validate, deduct besitos, create access record.

        Args:
            user_id: User making purchase
            product_id: Product to buy
            user_role: "FREE" or "VIP"
            force_repurchase: If True, allow buying already-owned content

        Returns:
            Tuple of (success, status_code, result_dict)
            status_code: "success", "validation_failed", "payment_failed",
                        "already_owned", "vip_only"
            result_dict on success:
            - product: ShopProduct
            - content_set: ContentSet
            - price_paid: int
            - file_ids: List[str]
            - access_record: UserContentAccess
            - is_repurchase: bool
        """
        # Validate purchase
        can_purchase, reason, details = await self.validate_purchase(
            user_id, product_id, user_role
        )

        if not can_purchase:
            return False, reason, None

        product = details["product"]
        price_to_pay = details["price_to_pay"]
        is_owned = details["is_owned"]

        # Check for duplicate purchase
        if is_owned and not force_repurchase:
            return False, "already_owned", {
                "product": product,
                "content_set": product.content_set
            }

        # Spend besitos via wallet service
        if self.wallet_service is not None:
            success, msg, transaction = await self.wallet_service.spend_besitos(
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

            if not success:
                self.logger.warning(
                    f"Purchase failed for user {user_id}: {msg}"
                )
                return False, "payment_failed", {"reason": msg}

        # Create UserContentAccess record
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
        self.session.add(access_record)

        # Update purchase count — atómico con UPDATE, sin incrementar también en Python
        await self.session.execute(
            update(ShopProduct)
            .where(ShopProduct.id == product_id)
            .values(purchase_count=ShopProduct.purchase_count + 1)
        )

        await self.session.flush()

        self.logger.info(
            f"✅ User {user_id} purchased product {product_id} "
            f"({product.name}) for {price_to_pay} besitos"
        )

        return True, "success", {
            "product": product,
            "content_set": product.content_set,
            "price_paid": price_to_pay,
            "file_ids": product.content_set.file_ids if product.content_set else [],
            "access_record": access_record,
            "is_repurchase": is_owned
        }

    async def check_ownership(
        self,
        user_id: int,
        content_set_id: int
    ) -> bool:
        """
        Check if user already owns specific content.

        Args:
            user_id: ID of the user
            content_set_id: ID of the content set

        Returns:
            True if user has active access to the content
        """
        result = await self.session.execute(
            select(UserContentAccess)
            .where(UserContentAccess.user_id == user_id)
            .where(UserContentAccess.content_set_id == content_set_id)
            .where(UserContentAccess.is_active == True)
        )
        access = result.scalar_one_or_none()

        return access is not None

    async def deliver_content(
        self,
        user_id: int,
        content_set_id: int
    ) -> Tuple[bool, str, Optional[List[str]]]:
        """
        Get file_ids for content delivery to user.

        Used by handlers to send actual Telegram files to user.
        Also updates last_accessed_at timestamp.

        Args:
            user_id: User requesting content
            content_set_id: Content to deliver

        Returns:
            Tuple of (success, message, file_ids list)
            file_ids: List of Telegram file_ids to send
        """
        # Verify user has access
        result = await self.session.execute(
            select(UserContentAccess)
            .where(UserContentAccess.user_id == user_id)
            .where(UserContentAccess.content_set_id == content_set_id)
            .where(UserContentAccess.is_active == True)
        )
        access = result.scalar_one_or_none()

        if access is None:
            return False, "no_access", None

        if access.is_expired:
            return False, "access_expired", None

        # Get ContentSet
        result = await self.session.execute(
            select(ContentSet).where(ContentSet.id == content_set_id)
        )
        content_set = result.scalar_one_or_none()

        if content_set is None:
            return False, "content_not_found", None

        # Update last_accessed_at
        access.last_accessed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await self.session.flush()

        self.logger.info(
            f"Content delivered: user={user_id}, content_set={content_set_id}, "
            f"files={len(content_set.file_ids)}"
        )

        return True, "ok", content_set.file_ids

    async def get_purchase_history(
        self,
        user_id: int,
        page: int = 1,
        per_page: int = 10
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get paginated purchase history for user.

        Args:
            user_id: User to query
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            Tuple of (purchases list, total count)
            Each purchase dict includes:
            - id: access record ID
            - product_name: str
            - content_set_name: str
            - besitos_paid: int
            - accessed_at: datetime
            - is_active: bool
            - file_count: int
        """
        # Build base query for shop purchases
        base_query = (
            select(UserContentAccess)
            .where(UserContentAccess.user_id == user_id)
            .where(UserContentAccess.access_type == "shop_purchase")
        )

        # Get total count
        count_query = (
            select(func.count(UserContentAccess.id))
            .where(UserContentAccess.user_id == user_id)
            .where(UserContentAccess.access_type == "shop_purchase")
        )

        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one_or_none() or 0

        # Apply ordering and pagination — con selectinload para evitar N+1
        # al acceder a shop_product.name y content_set.name en el loop
        offset = (page - 1) * per_page
        query = (
            base_query
            .options(
                selectinload(UserContentAccess.shop_product),
                selectinload(UserContentAccess.content_set)
            )
            .order_by(UserContentAccess.accessed_at.desc())
            .offset(offset)
            .limit(per_page)
        )

        result = await self.session.execute(query)
        accesses = list(result.scalars().all())

        # Format results
        purchases = []
        for access in accesses:
            purchase = {
                "id": access.id,
                "product_name": access.shop_product.name if access.shop_product else "Unknown",
                "content_set_name": access.content_set.name if access.content_set else "Unknown",
                "besitos_paid": access.besitos_paid or 0,
                "accessed_at": access.accessed_at,
                "is_active": access.is_active,
                "file_count": access.content_set.file_count if access.content_set else 0
            }
            purchases.append(purchase)

        return purchases, total

    async def get_user_shop_stats(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Get shop-related statistics for user.

        Args:
            user_id: User to query

        Returns:
            Dict with:
            - total_purchases: int
            - total_besitos_spent: int
            - unique_content_owned: int
            - last_purchase_at: Optional[datetime]
        """
        # Get all shop purchases for user
        result = await self.session.execute(
            select(UserContentAccess)
            .where(UserContentAccess.user_id == user_id)
            .where(UserContentAccess.access_type == "shop_purchase")
            .where(UserContentAccess.is_active == True)
        )
        purchases = list(result.scalars().all())

        total_purchases = len(purchases)
        total_besitos_spent = sum(p.besitos_paid or 0 for p in purchases)
        unique_content_owned = len(set(p.content_set_id for p in purchases))

        # Get last purchase date
        last_purchase_at = None
        if purchases:
            last_purchase_at = max(p.accessed_at for p in purchases)

        return {
            "total_purchases": total_purchases,
            "total_besitos_spent": total_besitos_spent,
            "unique_content_owned": unique_content_owned,
            "last_purchase_at": last_purchase_at
        }
