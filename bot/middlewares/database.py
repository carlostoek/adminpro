"""
Database Middleware - Inyecta sesión de base de datos y ServiceContainer en handlers.

Proporciona una sesión de SQLAlchemy y ServiceContainer a cada handler automáticamente.
"""
import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.exceptions import TelegramNetworkError, TelegramBadRequest

from bot.database import get_session
from bot.services.container import ServiceContainer

logger = logging.getLogger(__name__)


def get_db_session():
    """Obtiene una sesión de base de datos para su uso en handlers.

    Returns:
        Context manager para una sesión de base de datos
    """
    return get_session()


class DatabaseMiddleware(BaseMiddleware):
    """
    Middleware que inyecta sesión de base de datos.

    Uso:
        dispatcher.update.middleware(DatabaseMiddleware())

    El handler recibe automáticamente:
        async def handler(message: Message, session: AsyncSession):
            # session está disponible
            pass
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Ejecuta el middleware.

        Crea una sesión de base de datos, ServiceContainer, y los inyecta en data.
        El handler puede acceder a ellos como parámetros o desde data dict.

        Args:
            handler: Handler a ejecutar
            event: Evento de Telegram
            data: Data del handler

        Returns:
            Resultado del handler
        """
        # Crear sesión y ejecutar handler dentro del contexto
        async with get_session() as session:
            # Inyectar sesión en data
            data["session"] = session

            # Inyectar ServiceContainer en data (para handlers que necesitan acceso completo a servicios)
            bot = data.get("bot")
            if bot:
                data["container"] = ServiceContainer(session, bot)
                logger.debug("✅ ServiceContainer inyectado en data")

            try:
                # Ejecutar handler
                return await handler(event, data)
            except (TelegramNetworkError, TelegramBadRequest) as e:
                # Errores de red/Telegram - loguear como WARNING (no son errores del handler)
                logger.warning(
                    f"⚠️ Error de Telegram en handler: {type(e).__name__}: {e}"
                )
                raise
            except Exception as e:
                # Otros errores - loguear como ERROR y hacer rollback de la sesión
                logger.error(f"❌ Error en handler con sesión DB: {e}", exc_info=True)
                # Rollback para limpiar la transacción fallida y evitar PendingRollbackError
                try:
                    await session.rollback()
                    logger.debug("🔄 Sesión DB rollback ejecutado tras error")
                except Exception as rollback_error:
                    logger.warning(f"⚠️ Error durante rollback: {rollback_error}")
                raise
