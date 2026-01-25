"""
Free Menu Handler - Menú específico para usuarios Free.

Opciones:
- Contenido gratuito disponible
- Solicitar acceso a cola Free
- Información sobre beneficios VIP
- Contacto y soporte
"""
import logging
from typing import Dict, Any

from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.utils.keyboards import create_inline_keyboard
from bot.database.enums import UserRole, ContentCategory

logger = logging.getLogger(__name__)


async def show_free_menu(message: Message, data: Dict[str, Any]):
    """
    Muestra el menú Free.

    Args:
        message: Mensaje de Telegram
        data: Data del handler (incluye container, session, etc.)
    """
    user = message.from_user
    container = data.get("container")

    # Obtener información de cola Free
    queue_info = ""
    if container:
        try:
            free_request = await container.subscription.get_free_request(user.id)
            if free_request:
                from datetime import datetime
                created_str = free_request.created_at.strftime("%d/%m/%Y %H:%M")
                queue_info = f"📋 *En cola desde:* {created_str}\n"
        except Exception as e:
            logger.error(f"Error obteniendo info Free para {user.id}: {e}")

    # Crear teclado inline con opciones Free
    keyboard = InlineKeyboardBuilder()

    # Sección Contenido Gratuito
    keyboard.button(text="🆓 Contenido Free", callback_data="free:content_free")
    keyboard.button(text="📚 Tutoriales", callback_data="free:tutorials")
    keyboard.button(text="🎁 Muestras VIP", callback_data="free:vip_samples")

    # Sección Upgrade
    keyboard.button(text="⭐ Convertirse en VIP", callback_data="free:become_vip")
    keyboard.button(text="💎 Ver Beneficios VIP", callback_data="free:vip_benefits")
    keyboard.button(text="🔑 Canjear Token", callback_data="free:redeem_token")

    # Sección Cola Free
    keyboard.button(text="📋 Solicitar Acceso Free", callback_data="free:request_access")
    keyboard.button(text="⏳ Estado de Cola", callback_data="free:queue_status")

    # Sección Ayuda
    keyboard.button(text="❓ Ayuda", callback_data="free:help")
    keyboard.button(text="📞 Contacto", callback_data="free:contact")

    # Ajustar layout (3 columnas)
    keyboard.adjust(3, 3, 2, 2)

    # Mensaje de bienvenida
    welcome_text = (
        f"🆓 *Menú Free*\n\n"
        f"Hola, {user.first_name}!\n"
        f"ID: `{user.id}`\n"
        f"Rol: {UserRole.FREE.value.upper()}\n\n"
        f"{queue_info}"
        f"*Opciones disponibles:*\n"
        f"• Contenido gratuito disponible\n"
        f"• Solicitar acceso a cola Free\n"
        f"• Información sobre beneficios VIP\n"
        f"• Tutoriales y muestras\n\n"
        f"Selecciona una opción:"
    )

    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )

    logger.info(f"🆓 Menú Free mostrado a {user.id} (@{user.username or 'sin username'})")
