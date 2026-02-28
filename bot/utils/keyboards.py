"""
Keyboard Factory - Generador de teclados inline.

Funciones:
- create_inline_keyboard: Crea teclado a partir de estructura de botones
- create_menu_navigation: Crea filas de navegación estándar (Volver/Salir)
- create_content_with_navigation: Combina contenido con navegación
- get_reaction_keyboard: Genera teclado de reacciones para contenido

Centraliza la creación de keyboards para consistencia visual y navegación.
"""
from typing import List, Optional, Dict, TYPE_CHECKING
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

if TYPE_CHECKING:
    from bot.database.models import Story, StoryChoice, UserStoryProgress


# Default reactions for content
DEFAULT_REACTIONS = ["❤️", "🔥", "💋", "😈"]


def get_reaction_keyboard(
    content_id: int,
    channel_id: str,
    reactions: Optional[List[str]] = None,
    current_counts: Optional[dict] = None
) -> InlineKeyboardMarkup:
    """
    Genera teclado inline con botones de reacción.

    Args:
        content_id: ID del mensaje/contenido
        channel_id: ID del canal
        reactions: Lista de emojis a mostrar (default: ["❤️", "🔥", "💋", "😈"])
        current_counts: Dict {emoji: count} con conteos actuales

    Returns:
        InlineKeyboardMarkup con botones de reacción

    Example:
        keyboard = get_reaction_keyboard(
            content_id=message.message_id,
            channel_id="-1001234567890",
            current_counts={"❤️": 5, "🔥": 3}
        )
    """
    if reactions is None:
        reactions = DEFAULT_REACTIONS

    if current_counts is None:
        current_counts = {}

    # Build buttons row
    buttons = []
    for emoji in reactions:
        count = current_counts.get(emoji, 0)
        # Format: "❤️ 5" or just "❤️" if no reactions
        text = f"{emoji} {count}" if count > 0 else emoji

        # Callback data format: react:{channel_id}:{content_id}:{emoji}
        # Note: channel_id may contain -100 prefix, keep as-is
        callback_data = f"react:{channel_id}:{content_id}:{emoji}"

        # Telegram callback_data limit is 64 bytes
        # If too long, use hash or shorter format
        if len(callback_data.encode('utf-8')) > 64:
            # Fallback: use shortened format
            callback_data = f"r:{content_id}:{emoji}"

        buttons.append(
            InlineKeyboardButton(text=text, callback_data=callback_data)
        )

    # Arrange in rows of 4 buttons
    keyboard = []
    for i in range(0, len(buttons), 4):
        keyboard.append(buttons[i:i+4])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_reaction_keyboard_with_counts(
    content_id: int,
    channel_id: str,
    reactions: List[str],
    user_reactions: List[str]  # Emojis the user already reacted with
) -> InlineKeyboardMarkup:
    """
    Genera teclado mostrando qué reacciones ya hizo el usuario.

    Args:
        content_id: ID del mensaje/contenido
        channel_id: ID del canal
        reactions: Lista de emojis disponibles
        user_reactions: Lista de emojis que el usuario ya usó

    Returns:
        InlineKeyboardMarkup con indicación visual de reacciones del usuario
    """
    buttons = []
    for emoji in reactions:
        # Mark user reactions with checkmark
        if emoji in user_reactions:
            text = f"✓{emoji}"
        else:
            text = emoji

        callback_data = f"react:{channel_id}:{content_id}:{emoji}"

        # Handle length limit
        if len(callback_data.encode('utf-8')) > 64:
            callback_data = f"r:{content_id}:{emoji}"

        buttons.append(
            InlineKeyboardButton(text=text, callback_data=callback_data)
        )

    keyboard = []
    for i in range(0, len(buttons), 4):
        keyboard.append(buttons[i:i+4])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


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
    - Economía (Besitos)
    - Volver al menú principal

    Returns:
        InlineKeyboardMarkup con menú de configuración
    """
    return create_inline_keyboard([
        [{"text": "📊 Estado del Reino", "callback_data": "config:status"}],
        [{"text": "👑 Reacciones del Círculo", "callback_data": "config:reactions:vip"}],
        [{"text": "📺 Reacciones del Vestíbulo", "callback_data": "config:reactions:free"}],
        [{"text": "💰 Economía", "callback_data": "admin:economy_config"}],
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


# ============================================================================
# STORY KEYBOARDS
# ============================================================================

def get_story_choice_keyboard(
    story_id: int,
    choices: List["StoryChoice"],
    show_exit: bool = True
) -> InlineKeyboardMarkup:
    """
    Genera teclado para opciones de historia.

    Layout según UX-05:
    - Opciones organizadas en filas de máximo 3 botones
    - Botón de salida siempre al final (escape hatch - NARR-08)

    Args:
        story_id: ID de la historia
        choices: Lista de StoryChoice activas para el nodo actual
        show_exit: Mostrar botón "Salir de la historia" (default: True)

    Returns:
        InlineKeyboardMarkup con botones de opciones + botón salir

    Example:
        keyboard = get_story_choice_keyboard(
            story_id=123,
            choices=node.choices,
            show_exit=True
        )
    """
    buttons = []

    # Choice buttons (max 3 per row - UX-05)
    choice_buttons = []
    for choice in choices:
        # Truncate text to 50 chars (Telegram button text limit)
        text = choice.choice_text[:50] if len(choice.choice_text) > 50 else choice.choice_text
        callback_data = f"story:choice:{story_id}:{choice.id}"

        choice_buttons.append(InlineKeyboardButton(
            text=text,
            callback_data=callback_data
        ))

    # Arrange in rows of 3
    for i in range(0, len(choice_buttons), 3):
        buttons.append(choice_buttons[i:i+3])

    # Exit button (escape hatch - NARR-08)
    if show_exit:
        buttons.append([InlineKeyboardButton(
            text="🚪 Salir de la historia",
            callback_data=f"story:exit:{story_id}"
        )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_story_list_keyboard(
    stories: List["Story"],
    user_progress: Dict[int, "UserStoryProgress"]
) -> InlineKeyboardMarkup:
    """
    Genera teclado para lista de historias disponibles.

    Muestra badge de estado según UX-02:
    - 📖 Nuevo (sin progreso)
    - 🔴 En progreso (ACTIVE)
    - ⏸️ Pausada (PAUSED)
    - ✅ Completada (COMPLETED)

    Args:
        stories: Lista de historias disponibles
        user_progress: Dict {story_id: UserStoryProgress} con progreso del usuario

    Returns:
        InlineKeyboardMarkup con botones para cada historia
    """
    from bot.database.enums import StoryProgressStatus

    buttons = []

    for story in stories:
        progress = user_progress.get(story.id)

        # Determine badge based on progress status (UX-02)
        if not progress:
            badge = "📖"
            status_text = "Nuevo"
        elif progress.status == StoryProgressStatus.ACTIVE:
            badge = "🔴"
            status_text = "En progreso"
        elif progress.status == StoryProgressStatus.PAUSED:
            badge = "⏸️"
            status_text = "Pausada"
        elif progress.status == StoryProgressStatus.COMPLETED:
            badge = "✅"
            status_text = "Completada"
        else:
            badge = "📖"
            status_text = "Nuevo"

        # Premium indicator
        premium_badge = "💎 " if story.is_premium else ""

        text = f"{badge} {premium_badge}{story.title}"
        callback_data = f"story:start:{story.id}"

        buttons.append([InlineKeyboardButton(
            text=text[:64],  # Telegram limit
            callback_data=callback_data
        )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_story_restart_confirmation_keyboard(story_id: int) -> InlineKeyboardMarkup:
    """
    Teclado de confirmación para reiniciar historia completada (UX-03).

    Args:
        story_id: ID de la historia a reiniciar

    Returns:
        InlineKeyboardMarkup con botones Sí/No
    """
    return create_inline_keyboard([
        [
            {"text": "✅ Sí, reiniciar", "callback_data": f"story:confirm_restart:{story_id}"},
            {"text": "❌ No, volver", "callback_data": "story:back_to_list"}
        ]
    ])


def get_story_completed_keyboard(story_id: int) -> InlineKeyboardMarkup:
    """
    Teclado para historia completada.

    Opciones:
    - Releer historia (pide confirmación)
    - Volver a lista de historias

    Args:
        story_id: ID de la historia completada

    Returns:
        InlineKeyboardMarkup con opciones post-completación
    """
    return create_inline_keyboard([
        [{"text": "🔄 Releer historia", "callback_data": f"story:restart:{story_id}"}],
        [{"text": "📚 Volver a historias", "callback_data": "story:back_to_list"}]
    ])


def get_upsell_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado para mensaje de upsell de contenido Premium (TIER-04).

    Returns:
        InlineKeyboardMarkup con botón para información VIP
    """
    return create_inline_keyboard([
        [{"text": "💎 Conocer membresía VIP", "callback_data": "vip:info"}],
        [{"text": "🔙 Volver", "callback_data": "story:back_to_list"}]
    ])


# ============================================================================
# STORY MANAGEMENT KEYBOARDS (Admin)
# ============================================================================

def get_story_management_keyboard() -> InlineKeyboardMarkup:
    """
    Main story management menu keyboard.

    Buttons:
    - Crear Historia
    - Listar Historias
    - Volver

    Returns:
        InlineKeyboardMarkup for story management main menu
    """
    return create_inline_keyboard([
        [{"text": "➕ Crear Historia", "callback_data": "admin:story:create:start"}],
        [{"text": "📋 Listar Historias", "callback_data": "admin:story:list"}],
        [{"text": "🔙 Volver", "callback_data": "admin:main"}],
    ])


def get_story_list_keyboard_admin(stories: List, page: int = 0) -> InlineKeyboardMarkup:
    """
    Paginated story list keyboard for admin.

    One button per story: "{title} ({status_emoji})"
    callback: "admin:story:details:{id}"

    Args:
        stories: List of Story objects
        page: Current page number (0-indexed)

    Returns:
        InlineKeyboardMarkup with story buttons and pagination
    """
    from bot.database.enums import StoryStatus

    keyboard_rows = []

    # Story buttons
    for story in stories:
        # Status emoji
        if story.status == StoryStatus.PUBLISHED:
            status_emoji = "🟢"
        elif story.status == StoryStatus.DRAFT:
            status_emoji = "🟡"
        elif story.status == StoryStatus.ARCHIVED:
            status_emoji = "⚠️"
        else:
            status_emoji = "⚪"

        # Premium badge
        premium_badge = "💎" if story.is_premium else "🆓"

        # Button text
        text = f"{status_emoji} {premium_badge} {story.title[:25]}"
        callback_data = f"admin:story:details:{story.id}"

        keyboard_rows.append([{
            "text": text,
            "callback_data": callback_data
        }])

    # Pagination row (if needed)
    pagination_row = []
    if page > 0:
        pagination_row.append({
            "text": "⬅️ Anterior",
            "callback_data": f"admin:story:list:{page - 1}"
        })
    if len(stories) >= 10:  # Assuming page size of 10
        pagination_row.append({
            "text": "➡️ Siguiente",
            "callback_data": f"admin:story:list:{page + 1}"
        })

    if pagination_row:
        keyboard_rows.append(pagination_row)

    # Bottom actions
    keyboard_rows.append([{"text": "➕ Crear Nueva", "callback_data": "admin:story:create:start"}])
    keyboard_rows.append([{"text": "🔙 Volver", "callback_data": "admin:stories"}])

    return create_inline_keyboard(keyboard_rows)


def get_story_detail_keyboard(story, is_valid: bool = True) -> InlineKeyboardMarkup:
    """
    Story detail actions keyboard.

    Buttons: Editar, Publicar/Despublicar, Preview, Ver Nodos, Eliminar, Volver
    Publish button disabled if not valid.

    Args:
        story: Story object
        is_valid: Whether story passes validation

    Returns:
        InlineKeyboardMarkup with story action buttons
    """
    from bot.database.enums import StoryStatus

    keyboard_rows = []

    if story.is_active:
        keyboard_rows.append([{"text": "✏️ Editar", "callback_data": f"admin:story:edit:{story.id}"}])

        if story.status == StoryStatus.DRAFT:
            keyboard_rows.append([{"text": "🔍 Validar", "callback_data": f"admin:story:validate:{story.id}"}])

            if is_valid:
                keyboard_rows.append([{"text": "🚀 Publicar", "callback_data": f"admin:story:publish:{story.id}"}])
            else:
                keyboard_rows.append([{"text": "❌ Publicar (bloqueado)", "callback_data": f"admin:story:validate:{story.id}"}])

            keyboard_rows.append([{"text": "🗑️ Eliminar", "callback_data": f"admin:story:delete:{story.id}"}])
        elif story.status == StoryStatus.PUBLISHED:
            keyboard_rows.append([{"text": "⏸️ Despublicar", "callback_data": f"admin:story:unpublish:{story.id}"}])

        keyboard_rows.append([{"text": "👁️ Preview", "callback_data": f"admin:story:preview:{story.id}"}])
        keyboard_rows.append([{"text": "📊 Estadísticas", "callback_data": f"admin:story:stats:{story.id}"}])

    keyboard_rows.append([{"text": "🔙 Lista", "callback_data": "admin:story:list"}])

    return create_inline_keyboard(keyboard_rows)


def get_node_list_keyboard(nodes: List, story_id: int) -> InlineKeyboardMarkup:
    """
    Node list keyboard for story editing.

    One button per node: "{type_emoji} {preview}"
    callback: "admin:node:edit:{id}"

    Args:
        nodes: List of StoryNode objects
        story_id: ID of the parent story

    Returns:
        InlineKeyboardMarkup with node buttons
    """
    from bot.database.enums import NodeType

    keyboard_rows = []

    for node in nodes:
        # Type emoji
        if node.node_type == NodeType.START:
            type_emoji = "🚀"
        elif node.node_type == NodeType.STORY:
            type_emoji = "📖"
        elif node.node_type == NodeType.CHOICE:
            type_emoji = "🔄"
        elif node.node_type == NodeType.ENDING:
            type_emoji = "🏁"
        else:
            type_emoji = "📄"

        # Preview text (first 20 chars of content)
        preview = node.content_text[:20] if node.content_text else "Sin contenido"
        text = f"{type_emoji} {preview}"

        keyboard_rows.append([{
            "text": text,
            "callback_data": f"admin:node:edit:{node.id}"
        }])

    # Add node button
    keyboard_rows.append([{"text": "➕ Agregar Nodo", "callback_data": f"admin:story:node:create:{story_id}"}])
    keyboard_rows.append([{"text": "🔙 Volver", "callback_data": f"admin:story:details:{story_id}"}])

    return create_inline_keyboard(keyboard_rows)


def get_node_edit_keyboard(node) -> InlineKeyboardMarkup:
    """
    Node edit actions keyboard.

    Buttons: Editar Contenido, Condiciones, Recompensas, Ver Elecciones, Eliminar, Volver

    Args:
        node: StoryNode object

    Returns:
        InlineKeyboardMarkup with node edit buttons
    """
    keyboard_rows = [
        [{"text": "📝 Editar Contenido", "callback_data": f"admin:node:edit:content:{node.id}"}],
        [{"text": "🔒 Condiciones", "callback_data": f"admin:node:conditions:{node.id}"}],
        [{"text": "🎁 Recompensas", "callback_data": f"admin:node:rewards:{node.id}"}],
        [{"text": "🔀 Ver Elecciones", "callback_data": f"admin:node:choices:{node.id}"}],
        [{"text": "🗑️ Eliminar", "callback_data": f"admin:node:delete:{node.id}"}],
        [{"text": "🔙 Volver", "callback_data": f"admin:story:nodes:{node.story_id}"}],
    ]

    return create_inline_keyboard(keyboard_rows)


def get_choice_list_keyboard(choices: List, node_id: int) -> InlineKeyboardMarkup:
    """
    Choice list keyboard for node editing.

    One button per choice: "{text} → {target}"
    callback: "admin:choice:edit:{id}"

    Args:
        choices: List of StoryChoice objects
        node_id: ID of the parent node

    Returns:
        InlineKeyboardMarkup with choice buttons
    """
    keyboard_rows = []

    for choice in choices:
        # Get target node preview
        target_preview = choice.target_node.content_text[:15] if choice.target_node and choice.target_node.content_text else "Nodo"
        text = f"{choice.choice_text[:20]} → {target_preview}"

        keyboard_rows.append([{
            "text": text,
            "callback_data": f"admin:choice:edit:{choice.id}"
        }])

    # Add choice button
    keyboard_rows.append([{"text": "➕ Agregar Elección", "callback_data": f"admin:choice:create:{node_id}"}])
    keyboard_rows.append([{"text": "🔙 Volver", "callback_data": f"admin:node:choices:{node_id}"}])

    return create_inline_keyboard(keyboard_rows)
