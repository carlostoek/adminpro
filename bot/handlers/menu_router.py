"""
Menu Router - Enruta automáticamente a menú basado en rol detectado.

Responsabilidades:
- Detectar rol del usuario desde data["user_role"] (inyectado por RoleDetectionMiddleware)
- Redirigir a handler apropiado (admin, vip, free)
- Manejar casos edge (rol no detectado, fallback a free)
- Logging de routing decisions

Pattern: Router central que delega a handlers específicos por rol
"""
import logging
from typing import Dict, Any

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message

from bot.database.enums import UserRole
from bot.middlewares import DatabaseMiddleware, RoleDetectionMiddleware

logger = logging.getLogger(__name__)


class MenuRouter:
    """
    Router central para menús basados en rol.

    Uso:
        menu_router = MenuRouter()
        menu_router.register_routes(dp)

    Flujo:
        1. Usuario ejecuta /menu
        2. RoleDetectionMiddleware inyecta user_role en data
        3. MenuRouter detecta rol y redirige a handler apropiado
        4. Handler muestra menú específico para ese rol
    """

    def __init__(self):
        """Inicializa el router."""
        self.router = Router()

        # Aplicar middlewares al router (necesario para que funcionen con este router)
        self.router.message.middleware(DatabaseMiddleware())
        self.router.callback_query.middleware(DatabaseMiddleware())
        self.router.message.middleware(RoleDetectionMiddleware())
        self.router.callback_query.middleware(RoleDetectionMiddleware())

        self._setup_routes()
        logger.debug("✅ MenuRouter inicializado con middlewares")

    def _setup_routes(self):
        """Configura las rutas del router."""
        # /menu command - main entry point
        self.router.message.register(self._menu_wrapper, Command("menu"))

    async def _menu_wrapper(self, message: Message, data: Dict[str, Any]):
        """Wrapper que registra el handler como método de instancia."""
        logger.debug(f"📦 _menu_wrapper llamado con: message={message.text}, data_keys={list(data.keys()) if data else None}")
        return await self._route_to_menu(message, data)

    async def _route_to_menu(self, message: Message, data: Dict[str, Any]):
        """
        Handler principal que enruta a menú basado en rol.

        Args:
            message: Mensaje de Telegram
            data: Data del handler (incluye user_role y container inyectados por middlewares)

        Flujo:
            1. Obtener user_role de data (inyectado por RoleDetectionMiddleware)
            2. Redirigir a handler apropiado según rol
            3. Fallback a menú Free si rol no detectado
        """
        logger.debug(f"📨 _route_to_menu llamado con: message={message}, data_keys={list(data.keys()) if data else None}")
        user_role = data.get("user_role")

        if user_role is None:
            logger.warning(f"⚠️ No se detectó rol para user {message.from_user.id}, usando FREE por defecto")
            user_role = UserRole.FREE

        # Routing basado en rol
        if user_role == UserRole.ADMIN:
            await self._show_admin_menu(message, data)
        elif user_role == UserRole.VIP:
            await self._show_vip_menu(message, data)
        else:  # FREE o cualquier otro
            await self._show_free_menu(message, data)

    async def _show_admin_menu(self, message: Message, data: Dict[str, Any]):
        """
        Muestra menú de administrador.

        Args:
            message: Mensaje de Telegram
            data: Data del handler (incluye container, session, etc.)
        """
        try:
            from bot.handlers.admin.menu import show_admin_menu
            await show_admin_menu(message, data)
        except ImportError:
            logger.warning("Admin menu handler not available, showing placeholder")
            await message.answer(
                "👑 *Menú de Administrador*\n\n"
                "Funcionalidad de menú admin en desarrollo.\n\n"
                "⚠️ Admin menu handler no disponible aún.",
                parse_mode="Markdown"
            )

    async def _show_vip_menu(self, message: Message, data: Dict[str, Any]):
        """
        Muestra menú VIP.

        Args:
            message: Mensaje de Telegram
            data: Data del handler (incluye container, session, etc.)
        """
        try:
            from bot.handlers.vip.menu import show_vip_menu
            await show_vip_menu(message, data)
        except ImportError:
            logger.warning("VIP menu handler not available, showing placeholder")
            await message.answer(
                "⭐ *Menú VIP*\n\n"
                "Funcionalidad de menú VIP en desarrollo.\n\n"
                "⚠️ VIP menu handler no disponible aún.",
                parse_mode="Markdown"
            )

    async def _show_free_menu(self, message: Message, data: Dict[str, Any]):
        """
        Muestra menú Free.

        Args:
            message: Mensaje de Telegram
            data: Data del handler (incluye container, session, etc.)
        """
        try:
            from bot.handlers.free.menu import show_free_menu
            await show_free_menu(message, data)
        except ImportError:
            logger.warning("Free menu handler not available, showing placeholder")
            await message.answer(
                "🆓 *Menú Free*\n\n"
                "Funcionalidad de menú Free en desarrollo.\n\n"
                "⚠️ Free menu handler no disponible aún.",
                parse_mode="Markdown"
            )

    def register_routes(self, dispatcher):
        """
        Registra las rutas en el dispatcher.

        Args:
            dispatcher: Dispatcher de Aiogram
        """
        dispatcher.include_router(self.router)
        logger.info("✅ MenuRouter registrado en dispatcher")
