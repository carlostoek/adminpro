"""
Handlers module - Registro de todos los handlers del bot.

Estructura:
- admin/: Handlers de administración
- user/: Handlers de usuarios
- vip/: Handlers VIP
- free/: Handlers Free
"""
import logging
from aiogram import Dispatcher

from bot.handlers.admin import admin_router
from bot.handlers.user import user_router, free_join_router

# Menu Router
from bot.handlers.menu_router import MenuRouter

# Menu Handlers
from bot.handlers.admin.menu import show_admin_menu
from bot.handlers.vip.menu import show_vip_menu
from bot.handlers.free.menu import show_free_menu

logger = logging.getLogger(__name__)


def register_all_handlers(dispatcher: Dispatcher) -> None:
    """
    Registra todos los routers y handlers en el dispatcher.

    Args:
        dispatcher: Instancia del Dispatcher
    """
    logger.info("Registrando handlers...")

    # Registrar routers
    dispatcher.include_router(admin_router)
    dispatcher.include_router(user_router)
    dispatcher.include_router(free_join_router)  # ChatJoinRequest para Free

    # Registrar menu router
    menu_router = MenuRouter()
    menu_router.register_routes(dispatcher)

    logger.info("Handlers registrados correctamente")


__all__ = [
    "register_all_handlers",
    "admin_router",
    "user_router",
    "free_join_router",
    "MenuRouter",
    "show_admin_menu",
    "show_vip_menu",
    "show_free_menu",
]
