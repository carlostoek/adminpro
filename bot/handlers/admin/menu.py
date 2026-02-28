"""
Admin Menu Handler - Menú específico para administradores.

Opciones:
- Gestión de usuarios VIP (listar, agregar, eliminar)
- Gestión de contenido (crear, editar paquetes)
- Configuración del bot
- Estadísticas y reportes
"""
import logging
from typing import Dict, Any

from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.utils.keyboards import create_inline_keyboard
from bot.database.enums import UserRole

logger = logging.getLogger(__name__)


async def show_admin_menu(message: Message, data: Dict[str, Any]):
    """
    Muestra el menú de administrador.

    Args:
        message: Mensaje de Telegram
        data: Data del handler (incluye container, session, etc.)
    """
    user = message.from_user
    container = data.get("container")

    # Crear teclado inline con opciones de admin
    keyboard = InlineKeyboardBuilder()

    # Sección VIP Management
    keyboard.button(text="👑 Gestión VIP", callback_data="admin:vip_management")
    keyboard.button(text="📊 Listar VIPs", callback_data="admin:list_vips")
    keyboard.button(text="🔑 Generar Token VIP", callback_data="admin:generate_vip_token")

    # Sección Content Management
    keyboard.button(text="📦 Gestión Contenido", callback_data="admin:content_management")
    keyboard.button(text="➕ Crear Paquete", callback_data="admin:create_package")
    keyboard.button(text="📋 Listar Paquetes", callback_data="admin:list_packages")

    # Sección Story Management
    keyboard.button(text="📖 Crear Historia", callback_data="admin:stories")

    # Sección Configuración
    keyboard.button(text="⚙️ Configuración", callback_data="admin:config")
    keyboard.button(text="📈 Estadísticas", callback_data="admin:stats")
    keyboard.button(text="📊 Métricas Economía", callback_data="admin:economy_stats")

    # Sección Free Queue
    keyboard.button(text="🆓 Cola Free", callback_data="admin:free_queue")
    keyboard.button(text="✅ Procesar Free", callback_data="admin:process_free")

    # Ajustar layout (3 columnas)
    keyboard.adjust(3, 3, 3, 3, 1)

    # Mensaje de bienvenida
    welcome_text = (
        f"👑 *Menú de Administrador*\n\n"
        f"Hola, {user.first_name}!\n"
        f"ID: `{user.id}`\n"
        f"Rol: {UserRole.ADMIN.value.upper()}\n\n"
        f"*Opciones disponibles:*\n"
        f"• Gestión de usuarios VIP\n"
        f"• Gestión de contenido\n"
        f"• Configuración del bot\n"
        f"• Estadísticas y reportes\n\n"
        f"Selecciona una opción:"
    )

    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )

    logger.info(f"👑 Menú admin mostrado a {user.id} (@{user.username or 'sin username'})")
