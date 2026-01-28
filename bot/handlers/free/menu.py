"""
Free Menu Handler - Menú específico para usuarios Free.

Responsabilidades:
- Mostrar menú principal Free con voz de Lucien
- Usar UserMenuProvider para generación de mensajes
- Manejar información de cola Free

Opciones:
- Mi Contenido (muestras del jardín)
- Canal VIP (información de suscripción)
- Redes Sociales (contenido gratuito)
"""
import logging
from typing import Dict, Any

from aiogram.types import Message

logger = logging.getLogger(__name__)


async def show_free_menu(message: Message, data: Dict[str, Any], user_id: int = None, user_first_name: str = None):
    """
    Muestra el menú Free usando UserMenuProvider.

    Este handler genera el menú principal para usuarios Free con la voz
    consistente de Lucien, proporcionando acceso a contenido gratuito,
    información del canal VIP, y redes sociales.

    Args:
        message: Mensaje de Telegram
        data: Data del handler (incluye container, session, etc.)
        user_id: ID del usuario (opcional, si no se proporciona usa message.from_user.id)
        user_first_name: Nombre del usuario (opcional, si no se proporciona usa message.from_user.first_name)

    Note:
        When called from callbacks, message.from_user may be the bot itself.
        Always pass user_id and user_first_name explicitly from callback handlers.

    Voice Characteristics (Lucien):
    - Free users = "visitantes del jardín público"
    - Usa HTML para formato (no Markdown)
    - Usa "usted", nunca "tú"
    - Emoji 🎩 siempre presente
    - Referencias a Diana para autoridad

    Examples:
        >>> container = data.get("container")
        >>> await show_free_menu(message, data)
        >>> # Sends Free menu with Lucien-voiced greeting
    """
    # Use provided user_id or fall back to message.from_user.id
    # When called from callbacks, message.from_user may be the bot itself
    target_user_id = user_id if user_id is not None else message.from_user.id

    # Use provided user_first_name or fall back to message.from_user.first_name
    target_user_first_name = user_first_name if user_first_name is not None else message.from_user.first_name

    container = data.get("container")

    # Validar que el container esté disponible
    if not container:
        logger.error(f"Container no disponible para mostrar menú Free a {target_user_id}")
        await message.answer(
            "⚠️ Error temporal: servicio de menú no disponible. "
            "Por favor, intente nuevamente en unos momentos."
        )
        return

    try:
        # Obtener información de cola Free (para contexto futuro)
        free_queue_position = None
        try:
            free_request = await container.subscription.get_free_request(target_user_id)
            if free_request:
                # TODO: Calcular posición real en la cola
                # Por ahora, solo registramos que está en cola
                free_queue_position = None  # Placeholder para futura implementación
        except Exception as e:
            logger.warning(f"No se pudo obtener información de cola Free para {target_user_id}: {e}")

        # Obtener contexto de sesión para variación de mensajes
        session_ctx = None
        try:
            session_ctx = container.message.get_session_context(container)
        except Exception as e:
            logger.warning(f"No se pudo obtener contexto de sesión para {target_user_id}: {e}")

        # Generar mensaje y teclado usando UserMenuProvider
        text, keyboard = container.message.user.menu.free_menu_greeting(
            user_name=target_user_first_name or "visitante",
            free_queue_position=free_queue_position,
            user_id=target_user_id,
            session_history=session_ctx
        )

        # Enviar mensaje con formato HTML
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

        logger.info(f"🆓 Menú Free mostrado a {target_user_id} - voz de Lucien")

    except Exception as e:
        logger.error(f"Error mostrando menú Free a {target_user_id}: {e}", exc_info=True)
        await message.answer(
            "⚠️ Error al cargar el menú. Por favor, intente nuevamente."
        )
