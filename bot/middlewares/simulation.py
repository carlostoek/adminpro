"""
Simulation Middleware - Inyecta contexto de simulación en handlers.

Se aplica después de DatabaseMiddleware para tener acceso al container.
Inyecta user_context en data para que RoleDetectionMiddleware use el rol simulado.
"""
import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

logger = logging.getLogger(__name__)


class SimulationMiddleware(BaseMiddleware):
    """
    Middleware que resuelve e inyecta el contexto de simulación del usuario.

    Uso:
        # Aplicar DESPUÉS de DatabaseMiddleware:
        dp.message.middleware(SimulationMiddleware())
        dp.callback_query.middleware(SimulationMiddleware())

    Inyecta en data dictionary:
        - data["user_context"]: ResolvedUserContext (contexto resuelto con simulación)

    Requiere:
        - DatabaseMiddleware debe ejecutarse primero (inyecta container en data)

    Pattern: Sigue RoleDetectionMiddleware structure (user extraction, data injection)
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
            handler: Handler a ejecutar después de la resolución
            event: Evento de Telegram (Message, CallbackQuery, etc)
            data: Data del handler (incluye container, session, etc)

        Returns:
            Resultado del handler con user_context disponible en data
        """
        # Extraer user del evento (siguiendo patrón RoleDetectionMiddleware)
        user = None

        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user is None:
            # Edge case: no se pudo extraer usuario
            logger.debug("⚠️ No se pudo extraer usuario del evento")
            return await handler(event, data)

        # Obtener container del data dictionary (inyectado por DatabaseMiddleware)
        container = data.get("container")

        logger.info(f"🎭 SimulationMiddleware executing for user {user.id}, has_container={container is not None}")

        if not container:
            # No hay container disponible (DatabaseMiddleware no ejecutado)
            logger.warning("⚠️ No container in data, skipping context resolution")
            return await handler(event, data)

        # Resolver contexto de simulación e inyectar en data
        try:
            context = await container.simulation.resolve_user_context(user.id)
            data["user_context"] = context
            if context.is_simulating:
                logger.info(
                    f"🎭 Simulation active for user {user.id}: "
                    f"role={context.simulated_role.value}, "
                    f"effective_role={context.effective_role().value}"
                )
            else:
                logger.debug(
                    f"🎭 No simulation active for user {user.id}"
                )
        except Exception as e:
            logger.error(f"❌ Failed to resolve user context: {e}")
            # Continuar sin inyección para no romper el handler

        # Ejecutar handler con user_context disponible en data
        return await handler(event, data)
