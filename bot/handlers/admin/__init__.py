"""Admin handlers module."""
from bot.handlers.admin.main import admin_router
from bot.handlers.admin.menu import show_admin_menu
from bot.handlers.admin.profile import profile_router
from bot.handlers.admin.tests import tests_router
from bot.handlers.admin.economy_config import economy_config_router
from bot.handlers.admin.shop_management import shop_router

# Include routers
admin_router.include_router(tests_router)
admin_router.include_router(profile_router)
admin_router.include_router(economy_config_router)
admin_router.include_router(shop_router)

__all__ = ["admin_router", "show_admin_menu"]
