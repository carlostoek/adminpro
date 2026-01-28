"""
Keyboard Factory - Generador de teclados inline.

Funciones:
- create_inline_keyboard: Crea teclado a partir de estructura de botones
- create_menu_navigation: Crea filas de navegación estándar (Volver/Salir)
- create_content_with_navigation: Combina contenido con navegación

Centraliza la creación de keyboards para consistencia visual y navegación.
"""
from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def create_inline_keyboard(
    buttons: List[List[dict]],
    **kwargs
) -> InlineKeyboardMarkup:
    """
    Crea un inline keyboard a partir de una estructura de botones.

    Args:
        buttons: Lista de filas, cada fila es lista de botones
                 Cada botón es dict con 'text' y ('callback_data' OR 'url')

    Ejemplo:
        keyboard = create_inline_keyboard([
            [{"text": "Botón 1", "callback_data": "btn1"}],
            [
                {"text": "Botón 2", "callback_data": "btn2"},
                {"text": "Botón 3", "url": "https://example.com"}
            ]
        ])

    Returns:
        InlineKeyboardMarkup
    """
    inline_keyboard = []

    for row in buttons:
        keyboard_row = []
        for button in row:
            # Crear botón con callback_data o url
            if "callback_data" in button:
                btn = InlineKeyboardButton(
                    text=button["text"],
                    callback_data=button["callback_data"]
                )
            elif "url" in button:
                btn = InlineKeyboardButton(
                    text=button["text"],
                    url=button["url"]
                )
            else:
                raise ValueError(
                    f"Botón debe tener 'callback_data' o 'url': {button}"
                )
            keyboard_row.append(btn)
        inline_keyboard.append(keyboard_row)

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard, **kwargs)


def admin_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Keyboard del menú principal de admin.

    Opciones con Lucien voice terminology:
    - Dashboard completo
    - Círculo Exclusivo VIP
    - Vestíbulo de Acceso
    - Calibración del Reino
    - Planes de Suscripción
    - Observaciones del Reino

    Returns:
        InlineKeyboardMarkup con menú principal
    """
    return create_inline_keyboard([
        [{"text": "📊 Dashboard Completo", "callback_data": "admin:dashboard"}],
        [{"text": "👑 Círculo Exclusivo VIP", "callback_data": "admin:vip"}],
        [{"text": "📺 Vestíbulo de Acceso", "callback_data": "admin:free"}],
        [{"text": "⚙️ Calibración del Reino", "callback_data": "admin:config"}],
        [{"text": "💰 Planes de Suscripción", "callback_data": "admin:pricing"}],
        [{"text": "📈 Observaciones del Reino", "callback_data": "admin:stats"}],
    ])


def back_to_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Keyboard con solo botón "Volver al menú principal".

    Usado en submenús para regresar.

    Returns:
        InlineKeyboardMarkup con botón volver
    """
    return create_inline_keyboard([
        [{"text": "🔙 Volver al Menú Principal", "callback_data": "admin:main"}]
    ])


def stats_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Keyboard del menú de estadísticas.

    Opciones con Lucien voice terminology:
    - Observaciones del Círculo (VIP)
    - Observaciones del Vestíbulo (Free)
    - Registro de Invitaciones (tokens)
    - Actualizar Observaciones
    - Volver al Menú Principal

    Returns:
        InlineKeyboardMarkup con menú de stats
    """
    return create_inline_keyboard([
        [{"text": "📊 Observaciones del Círculo", "callback_data": "admin:stats:vip"}],
        [{"text": "📊 Observaciones del Vestíbulo", "callback_data": "admin:stats:free"}],
        [{"text": "🎟️ Registro de Invitaciones", "callback_data": "admin:stats:tokens"}],
        [{"text": "🔄 Actualizar Observaciones", "callback_data": "admin:stats:refresh"}],
        [{"text": "🔙 Volver al Menú Principal", "callback_data": "admin:main"}],
    ])


def yes_no_keyboard(
    yes_callback: str,
    no_callback: str
) -> InlineKeyboardMarkup:
    """
    Keyboard de confirmación Sí/No.

    Args:
        yes_callback: Callback data para "Sí"
        no_callback: Callback data para "No"

    Returns:
        InlineKeyboardMarkup con botones Sí/No
    """
    return create_inline_keyboard([
        [
            {"text": "✅ Sí", "callback_data": yes_callback},
            {"text": "❌ No", "callback_data": no_callback}
        ]
    ])


def config_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Keyboard del menú de configuración.

    Opciones con Lucien voice terminology:
    - Estado del Reino
    - Reacciones del Círculo (VIP)
    - Reacciones del Vestíbulo (Free)
    - Volver al menú principal

    Returns:
        InlineKeyboardMarkup con menú de configuración
    """
    return create_inline_keyboard([
        [{"text": "📊 Estado del Reino", "callback_data": "config:status"}],
        [{"text": "👑 Reacciones del Círculo", "callback_data": "config:reactions:vip"}],
        [{"text": "📺 Reacciones del Vestíbulo", "callback_data": "config:reactions:free"}],
        [{"text": "🔙 Volver al Menú Principal", "callback_data": "admin:main"}],
    ])


def create_menu_navigation(
    include_back: bool = True,
    include_exit: bool = False,
    back_text: str = "⬅️ Volver",
    exit_text: str = "🚪 Salir",
    back_callback: str = "menu:back",
    exit_callback: str = "menu:exit"
) -> List[List[dict]]:
    """
    Crea filas de navegación estándar para menús.

    Args:
        include_back: Incluir botón "Volver"
        include_exit: Incluir botón "Salir" (default: False)
        back_text: Texto del botón "Volver"
        exit_text: Texto del botón "Salir"
        back_callback: Callback data para "Volver"
        exit_callback: Callback data para "Salir"

    Returns:
        Lista de filas de navegación para usar con create_inline_keyboard

    Ejemplo:
        # Crear teclado con contenido + navegación
        content_buttons = [[{"text": "Opción 1", "callback_data": "opt1"}]]
        nav_rows = create_menu_navigation()
        all_buttons = content_buttons + nav_rows
        keyboard = create_inline_keyboard(all_buttons)
    """
    navigation_rows = []

    if include_back and include_exit:
        # Ambos botones en misma fila
        navigation_rows.append([
            {"text": back_text, "callback_data": back_callback},
            {"text": exit_text, "callback_data": exit_callback}
        ])
    elif include_back:
        # Solo botón "Volver"
        navigation_rows.append([
            {"text": back_text, "callback_data": back_callback}
        ])
    elif include_exit:
        # Solo botón "Salir"
        navigation_rows.append([
            {"text": exit_text, "callback_data": exit_callback}
        ])

    return navigation_rows


def create_content_with_navigation(
    content_buttons: List[List[dict]],
    include_back: bool = True,
    include_exit: bool = False,
    **nav_kwargs
) -> InlineKeyboardMarkup:
    """
    Crea teclado con botones de contenido + navegación estándar.

    Convenience wrapper que combina create_inline_keyboard y create_menu_navigation.

    Args:
        content_buttons: Botones de contenido (mismo formato que create_inline_keyboard)
        include_back: Incluir botón "Volver"
        include_exit: Incluir botón "Salir" (default: False)
        **nav_kwargs: Argumentos adicionales para create_menu_navigation

    Returns:
        InlineKeyboardMarkup con contenido y navegación

    Ejemplo:
        content = [[{"text": "Paquete 1", "callback_data": "pkg:1"}]]
        keyboard = create_content_with_navigation(content)
    """
    nav_rows = create_menu_navigation(
        include_back=include_back,
        include_exit=include_exit,
        **nav_kwargs
    )
    all_buttons = content_buttons + nav_rows
    return create_inline_keyboard(all_buttons)
