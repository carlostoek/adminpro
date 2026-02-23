"""Admin handlers module."""
from bot.handlers.admin.main import admin_router
from bot.handlers.admin.menu import show_admin_menu
from bot.handlers.admin.profile import profile_router
from bot.handlers.admin.tests import tests_router
from bot.handlers.admin.economy_config import economy_config_router
from bot.handlers.admin.shop_management import shop_router
from bot.handlers.admin.content_set_management import content_set_router
from bot.handlers.admin.user_gamification import user_gamification_router
from bot.handlers.admin.economy_stats import economy_stats_router
from bot.handlers.admin.reward_management import reward_router

# Include routers
admin_router.include_router(tests_router)
admin_router.include_router(profile_router)
admin_router.include_router(economy_config_router)
admin_router.include_router(shop_router)
admin_router.include_router(content_set_router)
admin_router.include_router(user_gamification_router)
admin_router.include_router(economy_stats_router)
admin_router.include_router(reward_router)

__all__ = ["admin_router", "show_admin_menu"]
