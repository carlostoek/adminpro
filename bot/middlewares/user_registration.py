"""
User Registration Middleware - Registra usuarios automáticamente en cualquier interacción.

Asegura que todo usuario que interactúe con el bot exista en la base de datos,
independientemente del punto de entrada (deep link, comando directo, callback, etc.)

Se ejecuta después de DatabaseMiddleware para tener acceso a la sesión.
"""
import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from bot.database.enums import UserRole

logger = logging.getLogger(__name__)


class UserRegistrationMiddleware(BaseMiddleware):
    """
    Middleware que registra usuarios automáticamente en cualquier interacción.

    Uso:
        # Aplicar globalmente después de DatabaseMiddleware:
        dp.update.middleware(DatabaseMiddleware())  # Primero (inyecta session)
        dp.update.middleware(UserRegistrationMiddleware())  # Segundo (usa session)

    Comportamiento:
        - Extrae usuario del evento (Message o CallbackQuery)
        - Verifica si existe en BD usando UserService
        - Si no existe: crea usuario con rol FREE y hace commit inmediato
        - Si existe: no hace nada (permite que el handler actualice datos si es necesario)

    Este middleware evita errores como:
        - "Cannot create streak for non-existent user"
        - Foreign key violations en tablas relacionadas
        - Usuarios perdidos en flujos con errores de token

    Nota:
        Requiere que DatabaseMiddleware se ejecute primero para inyectar 'session'.
        Si no hay sesión disponible, el middleware continúa sin error (graceful degradation).
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
            handler: Handler a ejecutar después del registro
            event: Evento de Telegram (Message, CallbackQuery, etc)
            data: Data del handler (incluye session, container, etc)

        Returns:
            Resultado del handler
        """
        # Extraer usuario del evento
        telegram_user = None

        if isinstance(event, Message):
            telegram_user = event.from_user
        elif isinstance(event, CallbackQuery):
            telegram_user = event.from_user

        if telegram_user is None:
            # Edge case: no se pudo extraer usuario (ej: edición de mensaje del bot)
            logger.debug("⚠️ No se pudo extraer usuario del evento para registro")
            return await handler(event, data)

        # Obtener sesión del data dictionary (inyectada por DatabaseMiddleware)
        session = data.get("session")

        if session is None:
            # No hay sesión disponible - no podemos registrar usuario
            logger.debug("⚠️ No hay sesión disponible, saltando registro de usuario")
            return await handler(event, data)

        try:
            # Importar UserService aquí para evitar circular imports
            from bot.services.user import UserService

            user_service = UserService(session)

            # Verificar si el usuario existe usando get_or_create_user
            # Esto crea el usuario si no existe, o actualiza sus datos si existe
            user = await user_service.get_or_create_user(
                telegram_user=telegram_user,
                default_role=UserRole.FREE
            )

            # Commit inmediato para asegurar persistencia
            # Esto evita que el usuario se pierda si hay errores posteriores
            # Importante: hacemos commit incluso si hay otros middlewares que crean nuevas sesiones
            await session.commit()

            # NO inyectamos el objeto user en data para evitar problemas de "detached instance"
            # cuando hay múltiples sesiones (middleware global + middlewares locales de routers).
            # Los handlers deben obtener el usuario de la sesión actual usando UserService.
            logger.debug(
                f"✅ Usuario registrado/verificado: {user.user_id} (@{user.username or 'sin_username'})"
            )

        except Exception as e:
            # Loguear error pero NO fallar - el handler puede funcionar sin usuario
            logger.error(
                f"❌ Error registrando usuario {telegram_user.id}: {e}",
                exc_info=True
            )
            # Rollback para limpiar estado de la sesión
            try:
                await session.rollback()
            except Exception:
                pass

        # Ejecutar handler independientemente del resultado del registro
        return await handler(event, data)
