"""
Admin Auth Middleware - Valida que el usuario tenga permisos de admin.

Se aplica a handlers que requieren permisos administrativos.
Si el usuario no es admin, responde con mensaje de error y no ejecuta el handler.

Los administradores incluyen:
- Usuarios en ADMIN_IDS (variables de entorno)
- Administradores de los canales VIP o Free configurados
"""
import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from config import Config

logger = logging.getLogger(__name__)


def _mask_user_id(user_id: int) -> str:
    """Enmascara un user ID mostrando solo primeros y últimos 2 dígitos.

    Args:
        user_id: ID de usuario de Telegram

    Returns:
        ID enmascarado (ej: "12****89")
    """
    user_str = str(user_id)
    if len(user_str) <= 4:
        return "****"
    return f"{user_str[:2]}****{user_str[-2:]}"


def is_admin(user_id: int) -> bool:
    """Verifica si un usuario es administrador (síncrono - solo variables de entorno).

    Para verificación completa incluyendo admins de canales, usar is_admin_async().

    Args:
        user_id: ID de usuario de Telegram a verificar

    Returns:
        True si el usuario es administrador (env var), False en caso contrario
    """
    return Config.is_admin(user_id)


async def is_admin_async(user_id: int, bot, session) -> bool:
    """Verifica si un usuario es administrador (async - incluye canales).

    Verifica tanto ADMIN_IDS como administradores de canales VIP/Free.

    Args:
        user_id: ID de usuario de Telegram a verificar
        bot: Instancia del bot de Aiogram
        session: Sesión de base de datos

    Returns:
        True si es admin (env o canal), False en caso contrario
    """
    # Primero verificar variables de entorno
    if Config.is_admin(user_id):
        return True

    # Verificar si es admin de algún canal
    from bot.services.channel import ChannelService
    channel_service = ChannelService(session, bot)
    return await channel_service.is_user_channel_admin(user_id)


class AdminAuthMiddleware(BaseMiddleware):
    """
    Middleware que valida permisos de administrador.

    Uso:
        # En el router de admin:
        admin_router.message.middleware(AdminAuthMiddleware())
        admin_router.callback_query.middleware(AdminAuthMiddleware())

    Si el usuario no es admin:
    - Envía mensaje de error
    - No ejecuta el handler
    - Loguea el intento
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
            handler: Handler a ejecutar si pasa validación
            event: Evento de Telegram (Message, CallbackQuery, etc)
            data: Data del handler (incluye bot, session, etc)

        Returns:
            Resultado del handler si es admin, None si no
        """
        # Extraer user del event
        user = None
        bot = data.get("bot")
        session = data.get("session")

        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user is None:
            # No se pudo extraer usuario - bloquear acceso
            logger.warning("⚠️ Acceso denegado: no se pudo extraer usuario del evento")
            # Bloquear acceso - no ejecutar handler
            return None

        # Verificar si es admin (incluyendo admins de canales)
        is_admin_user = False
        if bot and session:
            is_admin_user = await is_admin_async(user.id, bot, session)
        else:
            # Fallback a verificación sincrónica si no hay bot/session
            is_admin_user = Config.is_admin(user.id)

        if not is_admin_user:
            # Usuario no es admin
            logger.warning(
                f"🚫 Acceso denegado: user {_mask_user_id(user.id)} "
                f"intentó acceder a handler admin"
            )

            # Enviar mensaje de error
            error_message = (
                "🚫 <b>Acceso Denegado</b>\n\n"
                "Este comando es solo para administradores."
            )

            if isinstance(event, Message):
                await event.answer(error_message, parse_mode="HTML")
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "🚫 Acceso denegado: solo administradores",
                    show_alert=True
                )

            # No ejecutar handler
            return None

        # Usuario es admin: ejecutar handler normalmente
        logger.info(f"✅ Admin verificado: user {_mask_user_id(user.id)} (incluye admins de canales)")
        return await handler(event, data)
