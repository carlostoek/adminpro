"""
Story Handlers - Lectura de historias interactivas.

Handlers:
- cmd_stories: Muestra lista de historias disponibles (NARR-04)
- handle_start_story: Inicia o reanuda una historia (NARR-04, NARR-07)
- handle_make_choice: Procesa elección del usuario (NARR-06)
- handle_story_exit: Escape hatch para salir de historia (NARR-08)
- handle_back_to_list: Volver a lista de historias
- handle_restart_request: Solicitud de reinicio (UX-03)
- handle_confirm_restart: Confirma reinicio de historia

Voz: Lucien (🎩) para sistema, Diana (🫦) para contenido narrativo
"""
import logging
from typing import Optional, List, Dict

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from sqlalchemy import select

from bot.services.container import ServiceContainer
from bot.states.user import StoryReadingStates
from bot.database.enums import StoryProgressStatus, UserRole
from bot.database.models import StoryChoice
from bot.middlewares import DatabaseMiddleware
from bot.utils.keyboards import (
    get_story_choice_keyboard,
    get_story_list_keyboard,
    get_story_restart_confirmation_keyboard,
    get_story_completed_keyboard,
    get_upsell_keyboard
)

logger = logging.getLogger(__name__)

# Router para handlers de historias
story_router = Router(name="story")
story_router.message.middleware(DatabaseMiddleware())
story_router.callback_query.middleware(DatabaseMiddleware())


# ============================================================================
# LUCIEN'S VOICE MESSAGES (System)
# ============================================================================

def _get_lucien_header() -> str:
    """Retorna encabezado estándar de Lucien."""
    return "🎩 <b>Lucien:</b>"


def _get_story_list_header() -> str:
    """Mensaje de lista de historias con voz de Lucien."""
    return f"""{_get_lucien_header()}

<i>Le presento las historias disponibles...</i>

<i>Seleccione una para comenzar su viaje.</i>"""


def _get_empty_stories_message() -> str:
    """Mensaje cuando no hay historias disponibles."""
    return f"""{_get_lucien_header()}

<i>Oh... parece que no hay historias disponibles en este momento.</i>

<i>Diana está preparando nuevas narrativas. Vuelva más tarde.</i>"""


def _get_upsell_message() -> str:
    """Mensaje de upsell para contenido Premium (TIER-04)."""
    return f"""{_get_lucien_header()}

<i>Esta historia es exclusiva de nuestro círculo Premium.</i>

💎 <b>Acceso restringido</b>

<i>Si desea acceder a este contenido, considere unirse a nuestra membresía VIP.</i>"""


def _get_restart_confirmation_message(story_title: str) -> str:
    """Mensaje de confirmación para reiniciar historia (UX-03)."""
    return f"""{_get_lucien_header()}

<i>Ya ha completado esta historia anteriormente.</i>

📖 <b>{story_title}</b>

¿Desea reiniciarla desde el principio?

<i>Su progreso anterior se conservará en el historial.</i>"""


def _get_story_completed_message(story_title: str, ending: str) -> str:
    """Mensaje de historia completada (NARR-10)."""
    return f"""{_get_lucien_header()}

<i>Ha llegado al final de esta narrativa.</i>

📖 <b>{story_title}</b>
🏁 <b>Final:</b> {ending}

<i>Diana aprecia su dedicación a la historia.</i>"""


def _get_exit_message() -> str:
    """Mensaje al salir de una historia (NARR-08)."""
    return f"""{_get_lucien_header()}

<i>Ha salido de la historia.</i>

Su progreso ha sido guardado. Puede reanudarla cuando lo desee."""


def _get_error_message(context: str = "") -> str:
    """Mensaje de error con voz de Lucien."""
    error_detail = f" con {context}" if context else ""
    return f"""{_get_lucien_header()}

<i>Hmm... algo inesperado ha ocurrido{error_detail}.
Permítame consultar con Diana sobre este inconveniente.</i>"""


def _get_insufficient_funds_message(required: int, balance: int) -> str:
    """
    Mensaje de fondos insuficientes con voz de Lucien.

    Args:
        required: Cantidad de besitos requerida
        balance: Balance actual del usuario

    Returns:
        Mensaje formateado con voz de Lucien
    """
    return f"""🎩 <b>Atención</b>

Para esta decisión necesita hacer una inversión de {required} besitos, ahora cuenta con {balance} besitos.

Le sugiero que vaya a reclamar su regalo del día, tal vez con eso pueda acceder."""


async def handle_insufficient_funds(
    callback: CallbackQuery,
    required: int,
    balance: int,
    story_id: int
) -> None:
    """
    Muestra mensaje elegante de fondos insuficientes con opciones de recuperación.

    Args:
        callback: CallbackQuery para responder
        required: Cantidad de besitos requerida
        balance: Balance actual del usuario
        story_id: ID de la historia para poder volver
    """
    text = _get_insufficient_funds_message(required, balance)

    # Build recovery keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🎁 Ir a regalo diario",
            callback_data="menu:daily_gift"
        )],
        [InlineKeyboardButton(
            text="💰 Cómo ganar besitos",
            callback_data="menu:economy"
        )],
        [InlineKeyboardButton(
            text="🔙 Volver a la historia",
            callback_data=f"story:back:{story_id}"
        )]
    ])

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer("Fondos insuficientes", show_alert=True)


# ============================================================================
# DIANA'S VOICE MESSAGES (Content)
# ============================================================================

def _get_diana_header() -> str:
    """Retorna encabezado de Diana para contenido narrativo."""
    return "🫦"


def _format_node_content(content_text: str, progress_text: str) -> str:
    """
    Formatea contenido de nodo con voz de Diana.

    Diana es directa, íntima, empoderadora.
    Segunda persona (tú/eres/estás).
    """
    return f"""🫦

{content_text}

{progress_text}"""


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _format_progress_indicator(current_order_index: int, total_nodes: int) -> str:
    """
    Formatea indicador de progreso.

    Example: "📖 Escena 3 de 12"

    Args:
        current_order_index: Índice 0-based del nodo actual
        total_nodes: Total de nodos en la historia

    Returns:
        Texto formateado con indicador de progreso
    """
    current = current_order_index + 1  # Convert to 1-based
    return f"📖 Escena {current} de {total_nodes}"


def _get_status_badge(status: StoryProgressStatus) -> str:
    """
    Retorna badge de estado para lista de historias (UX-02).

    Returns:
        Emoji badge según estado
    """
    badges = {
        StoryProgressStatus.ACTIVE: "🔴",
        StoryProgressStatus.PAUSED: "⏸️",
        StoryProgressStatus.COMPLETED: "✅",
        StoryProgressStatus.ABANDONED: "🚪"
    }
    return badges.get(status, "📖")


async def _prepare_choice_states(
    user_id: int,
    choices: List,
    user_role: str,
    container: ServiceContainer
) -> List[Dict]:
    """
    Prepara el estado de visualización de cada elección.

    Evalúa condiciones y calcula costos para determinar el estado
    de cada elección (disponible, costosa, bloqueada por condición).

    Args:
        user_id: ID del usuario
        choices: Lista de StoryChoice
        user_role: Rol del usuario ("VIP", "FREE", etc.)
        container: ServiceContainer para acceder a servicios

    Returns:
        Lista de dicts con estado de cada elección:
        - choice_id: int
        - state: "available" | "costly" | "condition_locked"
        - cost: Optional[int]
        - vip_cost: Optional[int]
        - missing_requirements: List[str]
    """
    choice_states = []

    # Get user balance for cost evaluation
    try:
        user_balance = await container.wallet.get_balance(user_id)
    except Exception as e:
        logger.warning(f"Could not get balance for user {user_id}: {e}")
        user_balance = 0

    for choice in choices:
        # Evaluate conditions
        can_access, missing_requirements = await container.narrative.evaluate_choice_conditions(
            user_id, choice
        )

        # Calculate cost
        cost = await container.narrative.calculate_choice_cost(choice, user_role)
        vip_cost = choice.vip_cost_besitos if choice.vip_cost_besitos is not None else cost

        # Determine state
        if not can_access:
            state = "condition_locked"
        elif cost > 0:
            state = "costly"
        else:
            state = "available"

        choice_states.append({
            "choice_id": choice.id,
            "state": state,
            "cost": cost,
            "vip_cost": vip_cost,
            "missing_requirements": missing_requirements
        })

    return choice_states


async def _display_node_media(
    message_or_callback,
    node,
    caption: str,
    keyboard: InlineKeyboardMarkup
) -> None:
    """
    Muestra media asociada a un nodo.

    Supports (UX-06):
    - Single photo: send_photo
    - Multiple photos: send_media_group
    - Video: send_video

    Args:
        message_or_callback: Message o CallbackQuery para responder
        node: StoryNode con media_file_ids
        caption: Texto a mostrar (contenido del nodo)
        keyboard: Teclado inline con opciones
    """
    if not node.media_file_ids:
        # No media - just send text with keyboard
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.edit_text(
                text=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await message_or_callback.answer(
                text=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        return

    file_ids = node.media_file_ids

    if len(file_ids) == 1:
        # Single media item - can use edit or send
        if isinstance(message_or_callback, CallbackQuery):
            # Try edit first, if fails (different media type), delete and send
            try:
                await message_or_callback.message.edit_text(
                    text=caption,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                # If original had media, we need to send new message
                # This is handled by checking message type before calling
            except Exception:
                await message_or_callback.message.delete()
                await message_or_callback.message.answer_photo(
                    photo=file_ids[0],
                    caption=caption,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
        else:
            await message_or_callback.answer_photo(
                photo=file_ids[0],
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    else:
        # Multiple photos - send as media group
        # Media group cannot have reply_markup, so send separately
        media = []
        for i, file_id in enumerate(file_ids):
            media.append(InputMediaPhoto(
                media=file_id,
                caption=caption if i == 0 else None,
                parse_mode="HTML"
            ))

        if isinstance(message_or_callback, CallbackQuery):
            # Delete old message, send media group, then send keyboard
            await message_or_callback.message.delete()
            await message_or_callback.message.answer_media_group(media=media)
            # Send keyboard in separate message
            await message_or_callback.message.answer(
                text="🫦 <i>Continúa cuando estés lista...</i>",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await message_or_callback.answer_media_group(media=media)
            await message_or_callback.answer(
                text="🫦 <i>Continúa cuando estés lista...</i>",
                reply_markup=keyboard,
                parse_mode="HTML"
            )


# ============================================================================
# COMMAND HANDLER
# ============================================================================

@story_router.message(Command("stories"))
async def cmd_stories(
    message: Message,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """
    Handler del comando /stories.

    Muestra lista de historias disponibles filtradas por tier (TIER-02, TIER-03).
    - Free users: solo historias Free
    - VIP users: historias Free + Premium

    NARR-04: User can start an available story from the story list
    UX-02: User sees story list with completion status
    """
    user_id = message.from_user.id

    logger.info(f"📖 Usuario {user_id} ejecutó /stories")

    try:
        # Get user info for tier filtering
        user = await container.wallet.get_or_create_user(user_id)
        is_premium = user.role == UserRole.VIP

        # Get available stories
        stories, total = await container.narrative.get_available_stories(
            is_premium_user=is_premium
        )

        if not stories:
            await message.answer(
                text=_get_empty_stories_message(),
                parse_mode="HTML"
            )
            return

        # Get user progress for all stories
        user_progress: Dict[int, any] = {}
        for story in stories:
            progress = await container.narrative.get_story_progress(user_id, story.id)
            if progress:
                user_progress[story.id] = progress

        # Build keyboard with stories
        keyboard = get_story_list_keyboard(stories, user_progress)

        await message.answer(
            text=_get_story_list_header(),
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        # Set browsing state
        await state.set_state(StoryReadingStates.browsing_stories)

        logger.debug(f"📖 Mostradas {len(stories)} historias a usuario {user_id}")

    except Exception as e:
        logger.error(f"❌ Error en /stories para usuario {user_id}: {e}", exc_info=True)
        await message.answer(
            text=_get_error_message("al cargar historias"),
            parse_mode="HTML"
        )


# ============================================================================
# CALLBACK HANDLERS
# ============================================================================

@story_router.callback_query(lambda c: c.data.startswith("story:start:"))
async def handle_start_story(
    callback: CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """
    Inicia o reanuda una historia.

    NARR-04: User can start an available story
    NARR-07: User can resume a story from where they left off
    UX-03: User can restart a completed story (with confirmation)
    TIER-04: Free users attempting Premium story see upsell
    """
    user_id = callback.from_user.id
    story_id = int(callback.data.split(":")[2])

    logger.info(f"📖 Usuario {user_id} iniciando historia {story_id}")

    try:
        # Check if user has existing progress
        existing = await container.narrative.get_story_progress(user_id, story_id)

        if existing and existing.status == StoryProgressStatus.COMPLETED:
            # UX-03: Ask for restart confirmation
            await state.set_state(StoryReadingStates.confirm_restart)

            # Get story title
            stories, _ = await container.narrative.get_available_stories()
            story_title = next((s.title for s in stories if s.id == story_id), "Historia")

            text = _get_restart_confirmation_message(story_title)
            keyboard = get_story_restart_confirmation_keyboard(story_id)

            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await callback.answer()
            return

        # Start or resume story
        success, msg, progress = await container.narrative.start_story(user_id, story_id)

        if not success:
            # Check if it's a premium story and user is not VIP
            if "premium" in msg.lower() or "not available" in msg.lower():
                # TIER-04: Show upsell
                await callback.message.edit_text(
                    text=_get_upsell_message(),
                    reply_markup=get_upsell_keyboard(),
                    parse_mode="HTML"
                )
                await callback.answer("Contenido Premium", show_alert=True)
                return

            await callback.answer(f"Error: {msg}", show_alert=True)
            return

        # Get current node
        success, msg, node, choices = await container.narrative.get_current_node(progress)

        if not success:
            await callback.answer(f"Error: {msg}", show_alert=True)
            return

        # Display node
        await state.set_state(StoryReadingStates.reading_node)

        # Store story_id in state for later use
        await state.update_data(current_story_id=story_id)

        # Format content with Diana's voice
        progress_text = _format_progress_indicator(node.order_index, 12)  # Total will come from story
        caption = _format_node_content(node.content_text, progress_text)
        keyboard = get_story_choice_keyboard(story_id, choices, show_exit=True)

        await _display_node_media(callback, node, caption, keyboard)
        await callback.answer()

        logger.info(f"📖 Usuario {user_id} en nodo {node.id} de historia {story_id}")

    except Exception as e:
        logger.error(f"❌ Error iniciando historia {story_id} para {user_id}: {e}", exc_info=True)
        await callback.answer("Error al iniciar historia", show_alert=True)


@story_router.callback_query(lambda c: c.data.startswith("story:choice:"))
async def handle_make_choice(
    callback: CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """
    Procesa elección del usuario con manejo de race conditions.

    NARR-06: User choice transitions to next node and saves progress
    NARR-10: System handles story completion (end nodes)
    """
    user_id = callback.from_user.id
    parts = callback.data.split(":")
    story_id = int(parts[2])
    choice_id = int(parts[3])

    logger.info(f"📖 Usuario {user_id} eligió opción {choice_id} en historia {story_id}")

    try:
        # Set intermediate state to prevent double-clicks (race condition protection)
        current_state = await state.get_state()
        if current_state == "StoryReadingStates:processing_choice":
            await callback.answer("Procesando...", show_alert=False)
            return

        await state.set_state(StoryReadingStates.processing_choice)

        # Get progress
        progress = await container.narrative.get_story_progress(user_id, story_id)
        if not progress:
            await state.set_state(StoryReadingStates.browsing_stories)
            await callback.answer("Progreso no encontrado", show_alert=True)
            return

        # Verify progress is active
        if progress.status != StoryProgressStatus.ACTIVE:
            await state.set_state(StoryReadingStates.browsing_stories)
            await callback.answer("Historia no está activa", show_alert=True)
            return

        # Make choice
        success, msg, node, progress = await container.narrative.make_choice(
            user_id, progress, choice_id
        )

        if not success:
            await state.set_state(StoryReadingStates.reading_node)
            await callback.answer(f"Error: {msg}", show_alert=True)
            return

        # Check if completed
        if progress.status == StoryProgressStatus.COMPLETED:
            await state.set_state(StoryReadingStates.story_completed)

            # Get story title
            stories, _ = await container.narrative.get_available_stories()
            story_title = next((s.title for s in stories if s.id == story_id), "Historia")

            ending = progress.ending_reached or "Final"
            text = _get_story_completed_message(story_title, ending)
            keyboard = get_story_completed_keyboard(story_id)

            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await callback.answer("¡Historia completada!", show_alert=False)

            logger.info(f"📖 Usuario {user_id} completó historia {story_id}, final: {ending}")
        else:
            # Get choices for new node
            success, msg, node, choices = await container.narrative.get_current_node(progress)

            if not success:
                await state.set_state(StoryReadingStates.reading_node)
                await callback.answer(f"Error: {msg}", show_alert=True)
                return

            # Check if node has no choices (error condition)
            if not choices and node.node_type != "ending":
                logger.error(f"Nodo {node.id} sin opciones y no es final")
                # Still show content but with exit button only
                choices = []

            # Display new node
            progress_text = _format_progress_indicator(node.order_index, 12)
            caption = _format_node_content(node.content_text, progress_text)
            keyboard = get_story_choice_keyboard(story_id, choices, show_exit=True)

            await _display_node_media(callback, node, caption, keyboard)
            await state.set_state(StoryReadingStates.reading_node)
            await callback.answer()

            logger.debug(f"📖 Usuario {user_id} avanzó a nodo {node.id}")

    except Exception as e:
        logger.error(f"❌ Error procesando elección para {user_id}: {e}", exc_info=True)
        await state.set_state(StoryReadingStates.reading_node)
        await callback.answer("Error al procesar elección", show_alert=True)


@story_router.callback_query(lambda c: c.data.startswith("story:exit:"))
async def handle_story_exit(
    callback: CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """
    Handler para escape hatch - salir de historia.

    NARR-08: User has escape hatch button to exit story at any time
    """
    user_id = callback.from_user.id
    story_id = int(callback.data.split(":")[2])

    logger.info(f"🚪 Usuario {user_id} saliendo de historia {story_id}")

    try:
        # Get progress and abandon
        progress = await container.narrative.get_story_progress(user_id, story_id)
        if progress:
            await container.narrative.abandon_story(user_id, progress)

        # Clear FSM state
        await state.clear()

        # Show exit message with back to menu
        from bot.utils.keyboards import back_to_main_menu_keyboard
        await callback.message.edit_text(
            text=_get_exit_message(),
            reply_markup=back_to_main_menu_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer("Has salido de la historia")

    except Exception as e:
        logger.error(f"❌ Error saliendo de historia para {user_id}: {e}", exc_info=True)
        await callback.answer("Error al salir", show_alert=True)


@story_router.callback_query(lambda c: c.data == "story:back_to_list")
async def handle_back_to_list(
    callback: CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """Volver a la lista de historias."""
    # Reuse cmd_stories logic
    await cmd_stories(callback.message, state, container)
    await callback.answer()


@story_router.callback_query(lambda c: c.data.startswith("story:restart:"))
async def handle_restart_request(
    callback: CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """Solicitud de reinicio - muestra confirmación."""
    user_id = callback.from_user.id
    story_id = int(callback.data.split(":")[2])

    # Get story title
    stories, _ = await container.narrative.get_available_stories()
    story_title = next((s.title for s in stories if s.id == story_id), "Historia")

    await state.set_state(StoryReadingStates.confirm_restart)

    text = _get_restart_confirmation_message(story_title)
    keyboard = get_story_restart_confirmation_keyboard(story_id)

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@story_router.callback_query(lambda c: c.data.startswith("story:confirm_restart:"))
async def handle_confirm_restart(
    callback: CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """Confirma reinicio de historia completada."""
    user_id = callback.from_user.id
    story_id = int(callback.data.split(":")[2])

    logger.info(f"🔄 Usuario {user_id} reiniciando historia {story_id}")

    try:
        # Delete old progress
        progress = await container.narrative.get_story_progress(user_id, story_id)
        if progress:
            # Mark as abandoned first
            await container.narrative.abandon_story(user_id, progress)

        # Start fresh
        await handle_start_story(callback, state, container)

    except Exception as e:
        logger.error(f"❌ Error reiniciando historia para {user_id}: {e}", exc_info=True)
        await callback.answer("Error al reiniciar", show_alert=True)


@story_router.callback_query(lambda c: c.data.startswith("story:confirm:"))
async def handle_confirm_choice(
    callback: CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """
    Procesa la confirmación de una elección costosa.

    Este handler se ejecuta cuando el usuario confirma una elección
    que tiene costo en besitos. Realiza el cargo y avanza la historia.
    """
    user_id = callback.from_user.id
    parts = callback.data.split(":")
    story_id = int(parts[2])
    choice_id = int(parts[3])

    logger.info(f"📖 Usuario {user_id} confirmando elección {choice_id} en historia {story_id}")

    try:
        # Get user info for role and cost calculation
        user = await container.wallet.get_or_create_user(user_id)
        user_role = "VIP" if user.role == UserRole.VIP else "FREE"

        # Get progress
        progress = await container.narrative.get_story_progress(user_id, story_id)
        if not progress:
            await callback.answer("Progreso no encontrado", show_alert=True)
            return

        # Verify progress is active
        if progress.status != StoryProgressStatus.ACTIVE:
            await state.set_state(StoryReadingStates.browsing_stories)
            await callback.answer("Historia no está activa", show_alert=True)
            return

        # Get choice details for cost verification
        result = await container.narrative.session.execute(
            select(StoryChoice).where(StoryChoice.id == choice_id)
        )
        choice = result.scalar_one_or_none()

        if not choice:
            await callback.answer("Elección no encontrada", show_alert=True)
            return

        # Calculate cost
        cost = await container.narrative.calculate_choice_cost(choice, user_role)

        # Check balance before processing
        balance = await container.wallet.get_balance(user_id)
        if balance < cost:
            await handle_insufficient_funds(callback, cost, balance, story_id)
            return

        # Process the choice
        success, msg, node, progress = await container.narrative.make_choice(
            user_id, progress, choice_id
        )

        if not success:
            await callback.answer(f"Error: {msg}", show_alert=True)
            return

        # Deduct cost if applicable
        if cost > 0:
            try:
                await container.wallet.spend_besitos(
                    user_id=user_id,
                    amount=cost,
                    reason=f"Elección en historia {story_id}"
                )
            except Exception as e:
                logger.error(f"Error charging for choice {choice_id}: {e}")
                # Continue anyway - the choice was made

        # Check if completed
        if progress.status == StoryProgressStatus.COMPLETED:
            await state.set_state(StoryReadingStates.story_completed)

            # Get story title
            stories, _ = await container.narrative.get_available_stories()
            story_title = next((s.title for s in stories if s.id == story_id), "Historia")

            ending = progress.ending_reached or "Final"
            text = _get_story_completed_message(story_title, ending)
            keyboard = get_story_completed_keyboard(story_id)

            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await callback.answer("¡Historia completada!", show_alert=False)

            logger.info(f"📖 Usuario {user_id} completó historia {story_id}, final: {ending}")
        else:
            # Get choices for new node
            success, msg, node, choices = await container.narrative.get_current_node(progress)

            if not success:
                await state.set_state(StoryReadingStates.reading_node)
                await callback.answer(f"Error: {msg}", show_alert=True)
                return

            # Prepare choice states for display
            choice_states = await _prepare_choice_states(user_id, choices, user_role, container)

            # Display new node
            progress_text = _format_progress_indicator(node.order_index, 12)
            caption = _format_node_content(node.content_text, progress_text)
            keyboard = get_story_choice_keyboard(story_id, choices, show_exit=True, choice_states=choice_states)

            await _display_node_media(callback, node, caption, keyboard)
            await state.set_state(StoryReadingStates.reading_node)
            await callback.answer()

            logger.debug(f"📖 Usuario {user_id} avanzó a nodo {node.id}")

    except Exception as e:
        logger.error(f"❌ Error confirmando elección para {user_id}: {e}", exc_info=True)
        await state.set_state(StoryReadingStates.reading_node)
        await callback.answer("Error al procesar elección", show_alert=True)


@story_router.callback_query(lambda c: c.data == "stories:menu")
async def handle_stories_menu(
    callback: CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """
    Handler para acceder a historias desde el menú principal.

    NARR-04: User can start an available story from the story list
    """
    # Reuse cmd_stories logic
    await cmd_stories(callback.message, state, container)
    await callback.answer()
