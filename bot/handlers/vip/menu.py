"""
VIP Menu Handler - Menú específico para usuarios VIP.

Opciones:
- Acceso a contenido VIP
- Gestión de suscripción
- Historial de contenido
- Invitar amigos (referral)
"""
import logging
from typing import Dict, Any

from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.utils.keyboards import create_inline_keyboard
from bot.database.enums import UserRole, ContentCategory

logger = logging.getLogger(__name__)


async def show_vip_menu(message: Message, data: Dict[str, Any]):
    """
    Muestra el menú VIP.

    Args:
        message: Mensaje de Telegram
        data: Data del handler (incluye container, session, etc.)
    """
    user = message.from_user
    container = data.get("container")

    # Obtener información de suscripción VIP
    vip_info = ""
    if container:
        try:
            subscriber = await container.subscription.get_vip_subscriber(user.id)
            if subscriber:
                from datetime import datetime
                expires_str = subscriber.expires_at.strftime("%d/%m/%Y %H:%M") if subscriber.expires_at else "No expira"
                vip_info = f"📅 *Expira:* {expires_str}\n"
        except Exception as e:
            logger.error(f"Error obteniendo info VIP para {user.id}: {e}")

    # Crear teclado inline con opciones VIP
    keyboard = InlineKeyboardBuilder()

    # Sección Contenido VIP
    keyboard.button(text="⭐ Contenido VIP", callback_data="vip:content_vip")
    keyboard.button(text="💎 VIP Premium", callback_data="vip:content_premium")
    keyboard.button(text="📚 Biblioteca", callback_data="vip:library")

    # Sección Suscripción
    keyboard.button(text="📅 Mi Suscripción", callback_data="vip:subscription")
    keyboard.button(text="🔄 Extender VIP", callback_data="vip:extend")
    keyboard.button(text="👥 Invitar Amigos", callback_data="vip:invite")

    # Sección Intereses
    keyboard.button(text="❤️ Mis Intereses", callback_data="vip:interests")
    keyboard.button(text="🔔 Notificaciones", callback_data="vip:notifications")

    # Ajustar layout (3 columnas)
    keyboard.adjust(3, 3, 2)

    # Mensaje de bienvenida
    welcome_text = (
        f"⭐ *Menú VIP*\n\n"
        f"Hola, {user.first_name}!\n"
        f"ID: `{user.id}`\n"
        f"Rol: {UserRole.VIP.value.upper()}\n\n"
        f"{vip_info}"
        f"*Opciones disponibles:*\n"
        f"• Acceso a contenido VIP exclusivo\n"
        f"• Gestión de tu suscripción\n"
        f"• Invitar amigos y ganar beneficios\n"
        f"• Biblioteca de contenido descargado\n\n"
        f"Selecciona una opción:"
    )

    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )

    logger.info(f"⭐ Menú VIP mostrado a {user.id} (@{user.username or 'sin username'})")
