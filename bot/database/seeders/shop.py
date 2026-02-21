"""Default shop products seeder for the gamification system."""
import logging
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.database.models import ShopProduct, ContentSet
from bot.database.enums import ContentTier, ContentType

logger = logging.getLogger(__name__)

# Default products configuration
DEFAULT_PRODUCTS: List[Dict[str, Any]] = [
    {
        "name": "Pack de Bienvenida",
        "description": "Contenido especial para nuevos miembros del canal. Incluye fotos exclusivas de bienvenida.",
        "besitos_price": 50,
        "vip_discount_percentage": 20,
        "tier": ContentTier.FREE,
        "sort_order": 0,
        "content_set": {
            "name": "Welcome Pack",
            "description": "Fotos de bienvenida para nuevos miembros",
            "content_type": ContentType.PHOTO_SET,
            "tier": ContentTier.FREE,
            "file_ids": [],  # Empty - to be populated by admin
            "category": "welcome"
        }
    },
    {
        "name": "Pack VIP Especial",
        "description": "Contenido exclusivo para suscriptores VIP. Material premium mensual.",
        "besitos_price": 200,
        "vip_discount_percentage": 50,
        "tier": ContentTier.VIP,
        "sort_order": 1,
        "content_set": {
            "name": "VIP Special",
            "description": "Contenido premium mensual para suscriptores VIP",
            "content_type": ContentType.MIXED,
            "tier": ContentTier.VIP,
            "file_ids": [],  # Empty - to be populated by admin
            "category": "premium"
        }
    }
]


async def seed_default_shop_products(session: AsyncSession) -> None:
    """
    Seed default shop products with their content sets.

    This function is idempotent - running it multiple times will not
    create duplicate products. It checks for existing products by name.

    Note: Content sets are created with empty file_ids. The admin must
    upload actual content files after deployment and update the file_ids.

    Args:
        session: Async database session

    Returns:
        None
    """
    logger.info("Starting default shop products seeding...")
    created_count = 0
    skipped_count = 0

    for product_data in DEFAULT_PRODUCTS:
        # Check if product exists by name
        result = await session.execute(
            select(ShopProduct).where(ShopProduct.name == product_data["name"])
        )
        existing_product = result.scalar_one_or_none()

        if existing_product:
            logger.debug(f"Shop product '{product_data['name']}' already exists, skipping")
            skipped_count += 1
            continue

        # Extract content set data
        content_data = product_data["content_set"]

        # Create content set first
        content_set = ContentSet(
            name=content_data["name"],
            description=content_data["description"],
            content_type=content_data["content_type"],
            tier=content_data["tier"],
            file_ids=content_data["file_ids"],
            category=content_data.get("category"),
            is_active=True
        )
        session.add(content_set)
        await session.flush()  # Get content_set.id

        # Create product with content_set_id
        product = ShopProduct(
            name=product_data["name"],
            description=product_data["description"],
            content_set_id=content_set.id,
            besitos_price=product_data["besitos_price"],
            vip_discount_percentage=product_data["vip_discount_percentage"],
            tier=product_data["tier"],
            is_active=True,
            sort_order=product_data["sort_order"]
        )
        session.add(product)

        logger.info(
            f"Created shop product: {product_data['name']} "
            f"(ID: {product.id}, ContentSet ID: {content_set.id})"
        )
        created_count += 1

    await session.commit()
    logger.info(
        f"Shop products seeding complete. Created: {created_count}, "
        f"Skipped: {skipped_count}"
    )
