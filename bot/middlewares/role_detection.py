"""
Role Detection Middleware - Detecta e inyecta el rol del usuario en handlers.

Se aplica globalmente para que todos los handlers tengan acceso a user_role.
Si el usuario no tiene sesión disponible, ejecuta el handler sin role injection.
"""
import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from bot.services.role_detection import RoleDetectionService

logger = logging.getLogger(__name__)


class RoleDetectionMiddleware(BaseMiddleware):
    """
    Middleware que detecta e inyecta el rol del usuario.

    Uso:
        # Aplicar globalmente o a routers específicos:
        dp.message.middleware(RoleDetectionMiddleware())
        dp.callback_query.middleware(RoleDetectionMiddleware())

    Inyecta en data dictionary:
        - data["user_role"]: UserRole (ADMIN, VIP, or FREE)
        - data["user_id"]: int (user ID from Telegram)

    Si no hay sesión disponible:
        - Ejecuta handler sin inyectar user_role
        - No falla, permite handlers que no necesitan BD

    Pattern: Sigue AdminAuthMiddleware structure (user extraction, data injection)
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Ejecuta el middleware.

        Args:
            handler: Handler a ejecutar después de la detección
            event: Evento de Telegram (Message, CallbackQuery, etc)
            data: Data del handler (incluye bot, session, etc)

        Returns:
            Resultado del handler con user_role inyectado en data
        """
        # Extraer user del evento (siguiendo patrón AdminAuthMiddleware)
        user = None

        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user is None:
            # Edge case: no se pudo extraer usuario
            logger.debug("⚠️ No se pudo extraer usuario del evento")
            return await handler(event, data)

        # Obtener sesión del data dictionary
        session = data.get("session")

        if session is None:
            # No hay sesión disponible (handler no requiere BD)
            logger.debug("⚠️ No hay sesión disponible, ejecutando handler sin role injection")
            return await handler(event, data)

        # Detectar rol e inyectar en data
        # Obtener bot del data dictionary (inyectado por Aiogram)
        bot = data.get("bot")
        role_service = RoleDetectionService(session, bot=bot)
        user_role = await role_service.get_user_role(user.id)

        data["user_role"] = user_role
        data["user_id"] = user.id

        logger.debug(
            f"✅ Rol inyectado: user {user.id} (@{user.username or 'sin username'}) "
            f"→ {user_role.value}"
        )

        # Log data keys para debugging
        logger.debug(f"📊 Data keys antes de handler: {list(data.keys())}")

        # Ejecutar handler con user_role disponible en data
        return await handler(event, data)
