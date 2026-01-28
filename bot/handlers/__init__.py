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
from bot.handlers.user import user_router, free_join_router, vip_entry_router
from bot.handlers.vip import vip_callbacks_router
from bot.handlers.free import free_callbacks_router

# Menu Handlers (for direct use in role-based handlers)
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
    dispatcher.include_router(vip_entry_router)  # VIP entry flow (Phase 13)
    dispatcher.include_router(vip_callbacks_router)  # VIP menu callbacks
    dispatcher.include_router(free_callbacks_router)  # Free menu callbacks

    logger.info("Handlers registrados correctamente")


__all__ = [
    "register_all_handlers",
    "admin_router",
    "user_router",
    "free_join_router",
    "vip_entry_router",
    "vip_callbacks_router",
    "free_callbacks_router",
    "show_admin_menu",
    "show_vip_menu",
    "show_free_menu",
]
