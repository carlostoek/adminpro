"""Database seeders for default data initialization."""
from bot.database.seeders.rewards import seed_default_rewards
from bot.database.seeders.shop import seed_default_shop_products

__all__ = ["seed_default_rewards", "seed_default_shop_products"]
