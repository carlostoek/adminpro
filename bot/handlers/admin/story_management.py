"""
Story Management Handlers - Admin handlers for story CRUD operations.

Handlers:
- admin:stories - Main story management menu
- admin:story:list - Paginated list of stories
- admin:story:details:{id} - Show story details
- admin:story:create:start - Start story creation flow
- admin:story:edit:{id} - Edit story
- admin:story:publish:{id} - Publish/unpublish story
- admin:story:delete:{id} - Delete story
- admin:story:stats:{id} - Show story statistics

FSM Flows:
- StoryEditorStates - Multi-step story creation and editing
"""
import logging
from typing import Optional

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Story, StoryNode, StoryChoice
from bot.database.enums import StoryStatus, NodeType
from bot.handlers.admin.main import admin_router
from bot.services.container import ServiceContainer
from bot.states.admin import StoryEditorStates
from bot.utils.keyboards import create_inline_keyboard

logger = logging.getLogger(__name__)

# Create story router
story_router = Router(name="story_management")


# ===== HELPER FUNCTIONS =====

def format_validation_status(is_valid: bool, errors: list, info: dict) -> tuple:
    """
    Format validation status for display.

    Returns:
        Tuple of (status_emoji, status_text, detail_text)
        - ✅ Jugable (no errors)
        - ⚠️ Revisar (warnings only)
        - ❌ Bloqueado (errors exist)
    """
    if not is_valid and errors:
        error_count = len(errors)
        status_emoji = "❌"
        status_text = f"Bloqueado ({error_count} errores)"
        detail_text = "\n".join([f"❌ {err}" for err in errors[:5]])
        if len(errors) > 5:
            detail_text += f"\n<i>...y {len(errors) - 5} errores más</i>"
        return status_emoji, status_text, detail_text

    # Check for warnings (unreachable nodes)
    unreachable = info.get("unreachable_nodes", [])
    if unreachable:
        status_emoji = "⚠️"
        status_text = f"Revisar ({len(unreachable)} nodos inalcanzables)"
        detail_text = f"<b>Nodos inalcanzables:</b> {', '.join(map(str, unreachable))}"
        return status_emoji, status_text, detail_text

    # Valid story
    node_count = info.get("node_count", 0)
    ending_count = len(info.get("ending_node_ids", []))
    status_emoji = "✅"
    status_text = "Jugable"
    detail_text = f"<b>Resumen:</b> {node_count} nodos, {ending_count} finales"
    return status_emoji, status_text, detail_text


def get_story_status_badge(status: StoryStatus, is_active: bool) -> str:
    """Get status badge emoji for story."""
    if not is_active:
        return "🗑️"
    if status == StoryStatus.PUBLISHED:
        return "🟢"
    elif status == StoryStatus.DRAFT:
        return "🟡"
    elif status == StoryStatus.ARCHIVED:
        return "⚠️"
    return "⚪"


def get_story_status_text(status: StoryStatus, is_active: bool) -> str:
    """Get human-readable status text."""
    if not is_active:
        return "Eliminada"
    if status == StoryStatus.PUBLISHED:
        return "Publicada"
    elif status == StoryStatus.DRAFT:
        return "Borrador"
    elif status == StoryStatus.ARCHIVED:
        return "Archivada"
    return "Desconocido"


def format_story_info(story: Story, node_count: int) -> str:
    """Format story information for display."""
    badge = get_story_status_badge(story.status, story.is_active)
    status_text = get_story_status_text(story.status, story.is_active)
    premium_badge = "💎" if story.is_premium else "🆓"

    text = (
        f"{badge} <b>{story.title}</b>\n"
        f"   {premium_badge} {status_text} • {node_count} nodos\n"
    )
    return text


# ===== MAIN MENU HANDLER =====

@story_router.callback_query(F.data == "admin:stories")
async def callback_stories_menu(callback: CallbackQuery):
    """Handler for story management main menu."""
    text = (
        "🎩 <b>Gestión de Historias</b>\n\n"
        "<b>Acciones disponibles:</b>\n"
        "• Crear nueva historia\n"
        "• Listar historias existentes\n"
        "• Editar, publicar o eliminar\n\n"
        "<i>Seleccione una opción...</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "➕ Crear Historia", "callback_data": "admin:story:create:start"}],
        [{"text": "📋 Listar Historias", "callback_data": "admin:story:list"}],
        [{"text": "🔙 Volver", "callback_data": "admin:main"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# ===== LIST STORIES HANDLER =====

@story_router.callback_query(F.data == "admin:story:list")
async def callback_story_list(callback: CallbackQuery, session: AsyncSession):
    """Handler for paginated story list with validation badges."""
    # Get all stories with node count
    result = await session.execute(
        select(Story).order_by(Story.status, Story.title)
    )
    stories = list(result.scalars().all())

    if not stories:
        text = (
            "🎩 <b>Gestión de Historias</b>\n\n"
            "<i>No hay historias configuradas.</i>\n\n"
            "Use 'Crear Historia' para agregar una."
        )
        keyboard = create_inline_keyboard([
            [{"text": "➕ Crear Historia", "callback_data": "admin:story:create:start"}],
            [{"text": "🔙 Volver", "callback_data": "admin:stories"}],
        ])
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        return

    # Build list text with validation status
    text = "🎩 <b>Lista de Historias</b>\n\n"
    container = ServiceContainer(session, callback.bot)

    for story in stories:
        node_count = len(story.nodes) if story.nodes else 0
        badge = get_story_status_badge(story.status, story.is_active)
        premium_badge = "💎" if story.is_premium else "🆓"

        # Get validation status for draft stories
        validation_badge = ""
        if story.status == StoryStatus.DRAFT and node_count > 0:
            try:
                is_valid, errors, info = await container.story_editor.validate_story(story.id)
                val_emoji, val_text, _ = format_validation_status(is_valid, errors, info)
                validation_badge = f" {val_emoji}"
            except Exception:
                validation_badge = " ⚠️"

        text += f"{badge} <b>{story.title}</b>{validation_badge}\n"
        text += f"   {premium_badge} {node_count} nodos • {get_story_status_text(story.status, story.is_active)}\n\n"

    # Build keyboard with story buttons
    keyboard_rows = []
    for story in stories:
        badge = get_story_status_badge(story.status, story.is_active)
        premium_badge = "💎" if story.is_premium else "🆓"

        keyboard_rows.append([
            {
                "text": f"{badge} {premium_badge} {story.title[:25]}",
                "callback_data": f"admin:story:details:{story.id}"
            }
        ])

    keyboard_rows.append([{"text": "➕ Crear Nueva", "callback_data": "admin:story:create:start"}])
    keyboard_rows.append([{"text": "🔙 Volver", "callback_data": "admin:stories"}])

    keyboard = create_inline_keyboard(keyboard_rows)

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# ===== STORY DETAILS HANDLER =====

@story_router.callback_query(F.data.startswith("admin:story:details:"))
async def callback_story_details(callback: CallbackQuery, session: AsyncSession):
    """Handler for story details view."""
    try:
        story_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    story = await session.get(Story, story_id)
    if not story:
        await callback.answer("❌ Historia no encontrada", show_alert=True)
        return

    # Get node count
    result = await session.execute(
        select(func.count(StoryNode.id)).where(StoryNode.story_id == story_id)
    )
    node_count = result.scalar_one()

    # Format story details
    badge = get_story_status_badge(story.status, story.is_active)
    status_text = get_story_status_text(story.status, story.is_active)
    premium_text = "Premium" if story.is_premium else "Free"

    text = (
        f"🎩 <b>Detalles de Historia</b>\n\n"
        f"{badge} <b>{story.title}</b>\n\n"
        f"<b>Descripción:</b>\n{story.description or '<i>Sin descripción</i>'}\n\n"
        f"<b>Estado:</b> {status_text}\n"
        f"<b>Tipo:</b> {premium_text}\n"
        f"<b>Nodos:</b> {node_count}\n"
        f"<b>ID:</b> {story.id}\n"
    )

    # Get validation status for draft stories
    validation_info = None
    if story.status == StoryStatus.DRAFT:
        container = ServiceContainer(session, callback.bot)
        try:
            is_valid, errors, info = await container.story_editor.validate_story(story_id)
            val_emoji, val_text, _ = format_validation_status(is_valid, errors, info)
            validation_info = (is_valid, val_emoji, val_text)
            text += f"\n<b>Validación:</b> {val_emoji} {val_text}\n"
        except Exception:
            pass

    # Build action buttons based on status
    keyboard_rows = []

    if story.is_active:
        keyboard_rows.append([{"text": "✏️ Editar", "callback_data": f"admin:story:edit:{story.id}"}])

        if story.status == StoryStatus.DRAFT:
            # Show validation button
            keyboard_rows.append([{"text": "🔍 Validar", "callback_data": f"admin:story:validate:{story.id}"}])

            # Publish button - disabled if not valid
            if validation_info and validation_info[0]:
                keyboard_rows.append([{"text": "🚀 Publicar", "callback_data": f"admin:story:publish:{story.id}"}])
            elif validation_info:
                keyboard_rows.append([{"text": "❌ Publicar (bloqueado)", "callback_data": f"admin:story:validate:{story.id}"}])
            else:
                keyboard_rows.append([{"text": "🚀 Publicar", "callback_data": f"admin:story:publish:{story.id}"}])

            keyboard_rows.append([{"text": "🗑️ Eliminar", "callback_data": f"admin:story:delete:{story.id}"}])
        elif story.status == StoryStatus.PUBLISHED:
            keyboard_rows.append([{"text": "⏸️ Despublicar", "callback_data": f"admin:story:unpublish:{story.id}"}])

        keyboard_rows.append([{"text": "👁️ Preview", "callback_data": f"admin:story:preview:{story.id}"}])
        keyboard_rows.append([{"text": "📊 Estadísticas", "callback_data": f"admin:story:stats:{story.id}"}])

    keyboard_rows.append([{"text": "🔙 Lista", "callback_data": "admin:story:list"}])

    keyboard = create_inline_keyboard(keyboard_rows)

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# ===== CREATE STORY FLOW =====

@story_router.callback_query(F.data == "admin:story:create:start")
async def callback_story_create_start(callback: CallbackQuery, state: FSMContext):
    """Start story creation flow."""
    await state.set_state(StoryEditorStates.waiting_for_title)

    text = (
        "🎩 <b>Crear Nueva Historia</b>\n\n"
        "<b>Paso 1/3:</b> Título de la historia\n\n"
        "Ingrese el título de la historia:\n"
        "<i>(Máximo 200 caracteres)</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "❌ Cancelar", "callback_data": "admin:stories"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@story_router.message(StoryEditorStates.waiting_for_title)
async def process_story_title(message: Message, state: FSMContext):
    """Process story title input."""
    title = message.text.strip()

    if not title:
        await message.answer("🎩 <b>Error:</b> El título no puede estar vacío.\n\nIntente nuevamente:")
        return

    if len(title) > 200:
        await message.answer("🎩 <b>Error:</b> El título es demasiado largo (máx. 200 caracteres).\n\nIntente nuevamente:")
        return

    await state.update_data(title=title)
    await state.set_state(StoryEditorStates.waiting_for_description)

    text = (
        f"🎩 <b>Crear Nueva Historia</b>\n\n"
        f"<b>Título:</b> {title}\n\n"
        f"<b>Paso 2/3:</b> Descripción\n\n"
        f"Ingrese la descripción de la historia:\n"
        f"<i>(Máximo 1000 caracteres, o envíe /skip para omitir)</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "⏭️ Saltar", "callback_data": "story:create:skip_description"}],
        [{"text": "❌ Cancelar", "callback_data": "admin:stories"}],
    ])

    await message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")


@story_router.callback_query(F.data == "story:create:skip_description")
async def callback_skip_description(callback: CallbackQuery, state: FSMContext):
    """Skip description step."""
    await state.update_data(description=None)
    await state.set_state(StoryEditorStates.waiting_for_premium)

    data = await state.get_data()
    title = data.get("title")

    text = (
        f"🎩 <b>Crear Nueva Historia</b>\n\n"
        f"<b>Título:</b> {title}\n"
        f"<b>Descripción:</b> <i>(sin descripción)</i>\n\n"
        f"<b>Paso 3/3:</b> Tipo de acceso\n\n"
        f"¿Esta historia es Premium?"
    )

    keyboard = create_inline_keyboard([
        [{"text": "💎 Sí, Premium", "callback_data": "story:premium:true"},
         {"text": "🆓 No, Free", "callback_data": "story:premium:false"}],
        [{"text": "❌ Cancelar", "callback_data": "admin:stories"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@story_router.message(StoryEditorStates.waiting_for_description)
async def process_story_description(message: Message, state: FSMContext):
    """Process story description input."""
    description = message.text.strip()

    if description.lower() == "/skip":
        await state.update_data(description=None)
    elif len(description) > 1000:
        await message.answer("🎩 <b>Error:</b> La descripción es demasiado larga (máx. 1000 caracteres).\n\nIntente nuevamente:")
        return
    else:
        await state.update_data(description=description)

    await state.set_state(StoryEditorStates.waiting_for_premium)

    data = await state.get_data()
    title = data.get("title")
    desc = data.get("description")

    text = (
        f"🎩 <b>Crear Nueva Historia</b>\n\n"
        f"<b>Título:</b> {title}\n"
        f"<b>Descripción:</b> {desc[:50]}{'...' if desc and len(desc) > 50 else '<i>(sin descripción)</i>'}\n\n"
        f"<b>Paso 3/3:</b> Tipo de acceso\n\n"
        f"¿Esta historia es Premium?"
    )

    keyboard = create_inline_keyboard([
        [{"text": "💎 Sí, Premium", "callback_data": "story:premium:true"},
         {"text": "🆓 No, Free", "callback_data": "story:premium:false"}],
        [{"text": "❌ Cancelar", "callback_data": "admin:stories"}],
    ])

    await message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")


@story_router.callback_query(F.data.startswith("story:premium:"))
async def callback_story_premium_selected(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """Handle premium selection and create story."""
    try:
        is_premium = callback.data.split(":")[-1] == "true"
    except ValueError:
        await callback.answer("❌ Valor inválido", show_alert=True)
        return

    data = await state.get_data()
    title = data.get("title")
    description = data.get("description")

    # Create story using StoryEditorService
    container = ServiceContainer(session, callback.bot)
    success, msg, story = await container.story_editor.create_story(
        title=title,
        description=description,
        is_premium=is_premium
    )

    if not success:
        await callback.answer(f"❌ Error: {msg}", show_alert=True)
        return

    await session.commit()
    await session.refresh(story)

    # Clear state
    await state.clear()

    premium_text = "Premium" if is_premium else "Free"

    text = (
        f"🎩 <b>Historia Creada</b>\n\n"
        f"La historia <b>{story.title}</b> ha sido creada exitosamente.\n"
        f"<b>ID:</b> {story.id}\n"
        f"<b>Tipo:</b> {premium_text}\n\n"
        f"<i>Ahora puede agregar nodos y opciones para construir la historia.</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "➕ Agregar Nodo", "callback_data": f"admin:story:node:create:{story.id}"}],
        [{"text": "📋 Ver Historia", "callback_data": f"admin:story:details:{story.id}"}],
        [{"text": "✅ Finalizar", "callback_data": "admin:story:list"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer("✅ Historia creada")


# ===== EDIT STORY HANDLERS =====

@story_router.callback_query(F.data.startswith("admin:story:edit:"))
async def callback_story_edit(callback: CallbackQuery, session: AsyncSession):
    """Show edit menu for story."""
    try:
        story_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    story = await session.get(Story, story_id)
    if not story:
        await callback.answer("❌ Historia no encontrada", show_alert=True)
        return

    text = (
        f"🎩 <b>Editar Historia</b>\n\n"
        f"<b>Título actual:</b> {story.title}\n"
        f"<b>Descripción actual:</b>\n{story.description or '<i>Sin descripción</i>'}\n\n"
        f"<b>Premium:</b> {'Sí' if story.is_premium else 'No'}\n\n"
        f"<i>Seleccione el campo a editar:</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "✏️ Editar Título", "callback_data": f"admin:story:edit:title:{story.id}"}],
        [{"text": "📝 Editar Descripción", "callback_data": f"admin:story:edit:desc:{story.id}"}],
        [{"text": "💎 Cambiar Premium", "callback_data": f"admin:story:edit:premium:{story.id}"}],
        [{"text": "🔙 Volver", "callback_data": f"admin:story:details:{story.id}"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@story_router.callback_query(F.data.startswith("admin:story:edit:title:"))
async def callback_story_edit_title(callback: CallbackQuery, state: FSMContext):
    """Start editing story title."""
    try:
        story_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    await state.set_state(StoryEditorStates.waiting_for_edit_value)
    await state.update_data(edit_field="title", story_id=story_id)

    text = (
        "🎩 <b>Editar Título</b>\n\n"
        "Ingrese el nuevo título de la historia:\n"
        "<i>(Máximo 200 caracteres)</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "❌ Cancelar", "callback_data": f"admin:story:details:{story_id}"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@story_router.callback_query(F.data.startswith("admin:story:edit:desc:"))
async def callback_story_edit_description(callback: CallbackQuery, state: FSMContext):
    """Start editing story description."""
    try:
        story_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    await state.set_state(StoryEditorStates.waiting_for_edit_value)
    await state.update_data(edit_field="description", story_id=story_id)

    text = (
        "🎩 <b>Editar Descripción</b>\n\n"
        "Ingrese la nueva descripción de la historia:\n"
        "<i>(Máximo 1000 caracteres, o /clear para eliminar)</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "❌ Cancelar", "callback_data": f"admin:story:details:{story_id}"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@story_router.callback_query(F.data.startswith("admin:story:edit:premium:"))
async def callback_story_edit_premium(callback: CallbackQuery, session: AsyncSession):
    """Toggle premium status."""
    try:
        story_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    story = await session.get(Story, story_id)
    if not story:
        await callback.answer("❌ Historia no encontrada", show_alert=True)
        return

    # Toggle premium
    story.is_premium = not story.is_premium
    await session.commit()

    status_text = "Premium" if story.is_premium else "Free"
    await callback.answer(f"✅ Ahora es {status_text}")

    # Refresh details view
    await callback_story_details(callback, session)


@story_router.message(StoryEditorStates.waiting_for_edit_value)
async def process_story_edit_value(message: Message, state: FSMContext, session: AsyncSession):
    """Handle new value input for story edit."""
    data = await state.get_data()
    edit_field = data.get("edit_field")
    story_id = data.get("story_id")

    story = await session.get(Story, story_id)
    if not story:
        await message.answer("🎩 <b>Error:</b> Historia no encontrada.")
        await state.clear()
        return

    new_value = message.text.strip()

    if edit_field == "title":
        if not new_value:
            await message.answer("🎩 <b>Error:</b> El título no puede estar vacío.\n\nIntente nuevamente:")
            return
        if len(new_value) > 200:
            await message.answer("🎩 <b>Error:</b> El título es demasiado largo (máx. 200 caracteres).\n\nIntente nuevamente:")
            return
        story.title = new_value
        await session.commit()
        await message.answer(f"🎩 <b>Título actualizado:</b> {new_value}")

    elif edit_field == "description":
        if new_value.lower() == "/clear":
            story.description = None
            await session.commit()
            await message.answer("🎩 <b>Descripción eliminada.</b>")
        elif len(new_value) > 1000:
            await message.answer("🎩 <b>Error:</b> La descripción es demasiado larga (máx. 1000 caracteres).\n\nIntente nuevamente:")
            return
        else:
            story.description = new_value
            await session.commit()
            await message.answer(f"🎩 <b>Descripción actualizada.</b>")

    # Clear state
    await state.clear()

    # Show updated details
    # Create a mock callback to reuse the details handler
    class MockCallback:
        def __init__(self, message, data):
            self.message = message
            self.data = data
            self.bot = message.bot

        async def answer(self, **kwargs):
            pass

    mock_callback = MockCallback(message, f"admin:story:details:{story_id}")
    await callback_story_details(mock_callback, session)


# ===== PUBLISH/UNPUBLISH HANDLERS =====

@story_router.callback_query(F.data.startswith("admin:story:publish:"))
async def callback_story_publish(callback: CallbackQuery, session: AsyncSession):
    """Publish a story."""
    try:
        story_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    story = await session.get(Story, story_id)
    if not story:
        await callback.answer("❌ Historia no encontrada", show_alert=True)
        return

    if story.status == StoryStatus.PUBLISHED:
        await callback.answer("ℹ️ La historia ya está publicada", show_alert=True)
        return

    # Validate story before publishing
    container = ServiceContainer(session, callback.bot)
    is_valid, errors, info = await container.story_editor.validate_story(story_id)

    if not is_valid:
        error_text = "\n".join([f"• {err}" for err in errors[:5]])
        text = (
            f"🎩 <b>No se puede publicar</b>\n\n"
            f"La historia <b>{story.title}</b> tiene errores de validación:\n\n"
            f"{error_text}\n\n"
            f"<i>Corrija estos errores antes de publicar.</i>"
        )

        keyboard = create_inline_keyboard([
            [{"text": "🔍 Ver Validación", "callback_data": f"admin:story:validate:{story_id}"}],
            [{"text": "🔙 Volver", "callback_data": f"admin:story:details:{story_id}"}],
        ])

        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        return

    # Check for warnings (unreachable nodes)
    unreachable = info.get("unreachable_nodes", [])
    if unreachable:
        warning_text = (
            f"🎩 <b>Advertencia antes de publicar</b>\n\n"
            f"La historia <b>{story.title}</b> es válida pero tiene advertencias:\n\n"
            f"⚠️ Nodos inalcanzables: {', '.join(map(str, unreachable))}\n\n"
            f"<i>¿Desea publicar de todos modos?</i>"
        )

        keyboard = create_inline_keyboard([
            [{"text": "✅ Sí, publicar", "callback_data": f"admin:story:publish:confirm:{story_id}"}],
            [{"text": "🔍 Ver Validación", "callback_data": f"admin:story:validate:{story_id}"}],
            [{"text": "🔙 No, volver", "callback_data": f"admin:story:details:{story_id}"}],
        ])

        await callback.message.edit_text(text=warning_text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        return

    # Publish story (no warnings)
    success, msg = await container.story_editor.publish_story(story_id)

    if success:
        await session.commit()
        await callback.answer("✅ Historia publicada")
    else:
        await callback.answer(f"❌ Error: {msg}", show_alert=True)
        return

    # Refresh details
    await callback_story_details(callback, session)


@story_router.callback_query(F.data.startswith("admin:story:unpublish:"))
async def callback_story_unpublish(callback: CallbackQuery, session: AsyncSession):
    """Unpublish a story (set back to draft)."""
    try:
        story_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    story = await session.get(Story, story_id)
    if not story:
        await callback.answer("❌ Historia no encontrada", show_alert=True)
        return

    if story.status != StoryStatus.PUBLISHED:
        await callback.answer("ℹ️ La historia no está publicada", show_alert=True)
        return

    # Set back to draft
    story.status = StoryStatus.DRAFT
    await session.commit()

    await callback.answer("✅ Historia despublicada")
    await callback_story_details(callback, session)


@story_router.callback_query(F.data.startswith("admin:story:publish:confirm:"))
async def callback_story_publish_confirm(callback: CallbackQuery, session: AsyncSession):
    """Confirm publish story after warnings."""
    try:
        story_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    story = await session.get(Story, story_id)
    if not story:
        await callback.answer("❌ Historia no encontrada", show_alert=True)
        return

    if story.status == StoryStatus.PUBLISHED:
        await callback.answer("ℹ️ La historia ya está publicada", show_alert=True)
        return

    # Publish with force=True (user confirmed after warnings)
    container = ServiceContainer(session, callback.bot)
    success, msg = await container.story_editor.publish_story(story_id, force=True)

    if success:
        await session.commit()
        await callback.answer("✅ Historia publicada")
    else:
        await callback.answer(f"❌ Error: {msg}", show_alert=True)
        return

    # Refresh details
    await callback_story_details(callback, session)


# ===== PREVIEW MODE HANDLERS =====

@story_router.callback_query(F.data.startswith("admin:story:preview:"))
async def callback_story_preview(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Start preview mode for testing a story."""
    try:
        story_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    story = await session.get(Story, story_id)
    if not story:
        await callback.answer("❌ Historia no encontrada", show_alert=True)
        return

    # Initialize preview state
    await state.set_state(StoryEditorStates.preview_mode)
    await state.update_data(
        preview_story_id=story_id,
        preview_current_node_id=None,
        preview_is_preview=True
    )

    # Use NarrativeService to simulate user experience
    container = ServiceContainer(session, callback.bot)

    # Create a mock progress for preview (not saved to DB)
    from bot.database.models import StoryNode
    from bot.database.enums import NodeType

    # Find start node
    result = await session.execute(
        select(StoryNode).where(
            StoryNode.story_id == story_id,
            StoryNode.node_type == NodeType.START,
            StoryNode.is_active == True
        )
    )
    start_node = result.scalar_one_or_none()

    if not start_node:
        await callback.answer("❌ La historia no tiene nodo inicial", show_alert=True)
        await state.clear()
        return

    # Update current node in preview state
    await state.update_data(preview_current_node_id=start_node.id)

    # Display node content (using Diana's voice for content as users see)
    text = (
        f"🎩 <b>Modo Preview</b> - Viendo como usuario\n"
        f"<i>Historia: {story.title}</i>\n\n"
        f"🫦 <b>{story.title}</b>\n\n"
        f"{start_node.content_text or '<i>Sin contenido</i>'}"
    )

    # Get active choices for this node
    active_choices = [c for c in start_node.choices if c.is_active]

    keyboard_rows = []

    # Add choice buttons (max 3 per row)
    choice_buttons = []
    for choice in active_choices:
        choice_text = choice.choice_text[:50] if len(choice.choice_text) > 50 else choice.choice_text
        choice_buttons.append({
            "text": choice_text,
            "callback_data": f"admin:preview:choice:{choice.id}"
        })

    # Arrange in rows of 3
    for i in range(0, len(choice_buttons), 3):
        keyboard_rows.append(choice_buttons[i:i+3])

    # Add exit button
    keyboard_rows.append([{"text": "🚪 Salir del Preview", "callback_data": "admin:preview:exit"}])

    keyboard = create_inline_keyboard(keyboard_rows)

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer("👁️ Modo preview activado")


@story_router.callback_query(F.data.startswith("admin:preview:choice:"))
async def callback_preview_choice(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle choice selection in preview mode."""
    try:
        choice_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    # Get preview state
    data = await state.get_data()
    story_id = data.get("preview_story_id")
    preview_is_preview = data.get("preview_is_preview")

    if not preview_is_preview:
        await callback.answer("❌ No está en modo preview", show_alert=True)
        return

    # Get the choice and target node
    from bot.database.models import StoryNode, StoryChoice
    from bot.database.enums import NodeType

    choice = await session.get(StoryChoice, choice_id)
    if not choice or not choice.is_active:
        await callback.answer("❌ Opción no válida", show_alert=True)
        return

    target_node = await session.get(StoryNode, choice.target_node_id)
    if not target_node:
        await callback.answer("❌ Nodo destino no encontrado", show_alert=True)
        return

    # Update preview state with new node
    await state.update_data(preview_current_node_id=target_node.id)

    # Get story for title
    story = await session.get(Story, story_id)

    # Check if this is an ending
    is_ending = target_node.node_type == NodeType.ENDING

    # Display node content (Diana's voice for content)
    if is_ending:
        text = (
            f"🎩 <b>Modo Preview</b> - Viendo como usuario\n"
            f"<i>Historia: {story.title}</i>\n\n"
            f"🫦 <b>{story.title}</b> - <i>Final</i>\n\n"
            f"{target_node.content_text or '<i>Sin contenido</i>'}\n\n"
            f"✨ <i>Historia completada</i>"
        )
    else:
        text = (
            f"🎩 <b>Modo Preview</b> - Viendo como usuario\n"
            f"<i>Historia: {story.title}</i>\n\n"
            f"🫦 <b>{story.title}</b>\n\n"
            f"{target_node.content_text or '<i>Sin contenido</i>'}"
        )

    # Get active choices for this node
    active_choices = [c for c in target_node.choices if c.is_active]

    keyboard_rows = []

    if is_ending or not active_choices:
        # End of story - show restart option
        keyboard_rows.append([{"text": "🔄 Reiniciar Preview", "callback_data": f"admin:story:preview:{story_id}"}])
    else:
        # Add choice buttons (max 3 per row)
        choice_buttons = []
        for ch in active_choices:
            choice_text = ch.choice_text[:50] if len(ch.choice_text) > 50 else ch.choice_text
            choice_buttons.append({
                "text": choice_text,
                "callback_data": f"admin:preview:choice:{ch.id}"
            })

        # Arrange in rows of 3
        for i in range(0, len(choice_buttons), 3):
            keyboard_rows.append(choice_buttons[i:i+3])

    # Add exit button
    keyboard_rows.append([{"text": "🚪 Salir del Preview", "callback_data": "admin:preview:exit"}])

    keyboard = create_inline_keyboard(keyboard_rows)

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@story_router.callback_query(F.data == "admin:preview:exit")
async def callback_preview_exit(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Exit preview mode and return to story details."""
    # Get story ID from state before clearing
    data = await state.get_data()
    story_id = data.get("preview_story_id")

    # Clear preview state
    await state.clear()

    # Return to story details
    if story_id:
        # Create mock callback for story details
        class MockCallback:
            def __init__(self, message, data):
                self.message = message
                self.data = data
                self.bot = message.bot

            async def answer(self, **kwargs):
                pass

        mock_callback = MockCallback(callback.message, f"admin:story:details:{story_id}")
        await callback_story_details(mock_callback, session)
    else:
        await callback.message.edit_text(
            "🎩 <b>Preview finalizado</b>\n\n<i>Volviendo al menú de historias...</i>",
            reply_markup=create_inline_keyboard([[{"text": "🔙 Volver", "callback_data": "admin:story:list"}]]),
            parse_mode="HTML"
        )

    await callback.answer("👁️ Preview finalizado")


# ===== DELETE HANDLER =====

@story_router.callback_query(F.data.startswith("admin:story:delete:"))
async def callback_story_delete(callback: CallbackQuery, session: AsyncSession):
    """Show delete confirmation for story."""
    try:
        story_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    story = await session.get(Story, story_id)
    if not story:
        await callback.answer("❌ Historia no encontrada", show_alert=True)
        return

    # Only allow deleting draft stories
    if story.status != StoryStatus.DRAFT:
        await callback.answer("❌ Solo se pueden eliminar historias en borrador", show_alert=True)
        return

    text = (
        f"🎩 <b>Confirmar Eliminación</b>\n\n"
        f"¿Está seguro de eliminar la historia <b>{story.title}</b>?\n\n"
        f"<i>Esta acción no se puede deshacer. Los nodos y opciones asociados también se eliminarán.</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "✅ Sí, eliminar", "callback_data": f"admin:story:delete:confirm:{story.id}"}],
        [{"text": "❌ No, cancelar", "callback_data": f"admin:story:details:{story.id}"}],
    ])

    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise
    await callback.answer()


@story_router.callback_query(F.data.startswith("admin:story:delete:confirm:"))
async def callback_story_delete_confirm(callback: CallbackQuery, session: AsyncSession):
    """Confirm story deletion (soft delete)."""
    try:
        story_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    story = await session.get(Story, story_id)
    if not story:
        await callback.answer("❌ Historia no encontrada", show_alert=True)
        return

    title = story.title

    # Soft delete - set is_active to False
    story.is_active = False
    await session.commit()

    await callback.answer(f"✅ Historia '{title}' eliminada")

    # Return to list
    await callback_story_list(callback, session)


# ===== VALIDATION DETAIL HANDLER =====

@story_router.callback_query(F.data.startswith("admin:story:validate:"))
async def callback_story_validation_detail(callback: CallbackQuery, session: AsyncSession):
    """Show full validation report for a story."""
    try:
        story_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    story = await session.get(Story, story_id)
    if not story:
        await callback.answer("❌ Historia no encontrada", show_alert=True)
        return

    # Run validation
    container = ServiceContainer(session, callback.bot)
    is_valid, errors, info = await container.story_editor.validate_story(story_id)

    # Format validation report
    val_emoji, val_text, detail_text = format_validation_status(is_valid, errors, info)

    text = (
        f"🎩 <b>Validación de Historia</b>\n\n"
        f"<b>{story.title}</b>\n"
        f"Estado: {val_emoji} {val_text}\n\n"
    )

    if errors:
        text += "<b>Errores:</b>\n" + "\n".join([f"❌ {err}" for err in errors]) + "\n\n"

    # Add info section
    text += f"<b>Información:</b>\n"
    text += f"• Nodos totales: {info.get('node_count', 0)}\n"
    text += f"• Finales: {len(info.get('ending_node_ids', []))}\n"
    text += f"• Elecciones: {info.get('choice_count', 0)}\n"

    if info.get('start_node_id'):
        text += f"• Nodo inicial: #{info['start_node_id']}\n"

    if info.get('unreachable_nodes'):
        text += f"• Nodos inalcanzables: {', '.join(map(str, info['unreachable_nodes']))}\n"

    # Build keyboard
    keyboard_rows = []

    # If there are errors, show button to edit nodes
    if errors:
        keyboard_rows.append([{"text": "🔧 Ver Nodos", "callback_data": f"admin:story:nodes:{story_id}"}])

    keyboard_rows.append([{"text": "🔙 Volver", "callback_data": f"admin:story:details:{story_id}"}])

    keyboard = create_inline_keyboard(keyboard_rows)

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# ===== STATS HANDLER =====

@story_router.callback_query(F.data.startswith("admin:story:stats:"))
async def callback_story_stats(callback: CallbackQuery, session: AsyncSession):
    """Show story statistics."""
    try:
        story_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    story = await session.get(Story, story_id)
    if not story:
        await callback.answer("❌ Historia no encontrada", show_alert=True)
        return

    # Get stats from StoryEditorService
    container = ServiceContainer(session, callback.bot)
    success, msg, stats = await container.story_editor.get_story_stats(story_id)

    if not success:
        await callback.answer(f"❌ Error: {msg}", show_alert=True)
        return

    text = (
        f"🎩 <b>Estadísticas de Historia</b>\n\n"
        f"<b>{story.title}</b>\n\n"
        f"📊 <b>Participación:</b>\n"
        f"• Inicios totales: {stats['total_starts']}\n"
        f"• Activos: {stats['active']}\n"
        f"• Completados: {stats['completed']}\n"
        f"• Abandonados: {stats['abandoned']}\n\n"
        f"📈 <b>Métricas:</b>\n"
        f"• Tasa de finalización: {stats['completion_rate'] * 100:.1f}%\n"
        f"• Decisiones promedio: {stats['avg_decisions']}\n"
    )

    if stats['most_common_ending']:
        text += f"• Final más común: Nodo #{stats['most_common_ending']}\n"

    keyboard = create_inline_keyboard([
        [{"text": "🔙 Volver", "callback_data": f"admin:story:details:{story_id}"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# =============================================================================
# NODE CREATION WIZARD
# =============================================================================

@story_router.callback_query(F.data.startswith("admin:story:node:create:"))
async def callback_node_create_start(callback: CallbackQuery, state: FSMContext):
    """Start node creation wizard."""
    try:
        story_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    await state.set_state(StoryEditorStates.waiting_for_content)
    await state.update_data(
        story_id=story_id,
        node_content_text=None,
        node_media_file_ids=[],
        node_media_type=None
    )

    text = (
        "🎩 <b>Crear Nodo de Historia</b>\n\n"
        "<b>Paso 1:</b> Contenido del nodo\n\n"
        "Envíe el contenido del nodo:\n"
        "• Texto (mensaje de texto)\n"
        "• Foto (con caption opcional)\n"
        "• Video (con caption opcional)\n\n"
        "<i>El contenido será mostrado al usuario cuando llegue a este nodo.</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "❌ Cancelar", "callback_data": f"admin:story:details:{story_id}"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@story_router.message(StoryEditorStates.waiting_for_content)
async def process_node_content(message: Message, state: FSMContext):
    """Handle node content input (text, photo, video)."""
    content_text = None
    media_file_ids = []
    media_type = None

    # Handle photo
    if message.photo:
        media_file_ids = [message.photo[-1].file_id]  # Highest resolution
        media_type = "photo"
        content_text = message.caption
    # Handle video
    elif message.video:
        media_file_ids = [message.video.file_id]
        media_type = "video"
        content_text = message.caption
    # Handle text
    elif message.text:
        content_text = message.text.strip()
        if content_text.lower() == "/skip":
            content_text = None
    else:
        await message.answer(
            "🎩 <b>Error:</b> Tipo de contenido no soportado.\n"
            "Envíe texto, foto o video:"
        )
        return

    # Validate: at least text OR media must exist
    if not content_text and not media_file_ids:
        await message.answer(
            "🎩 <b>Error:</b> El nodo debe tener contenido (texto o multimedia).\n"
            "Intente nuevamente:"
        )
        return

    # Store in FSM
    await state.update_data(
        node_content_text=content_text,
        node_media_file_ids=media_file_ids,
        node_media_type=media_type
    )

    # Advance to type selection
    await state.set_state(StoryEditorStates.waiting_for_node_type)

    # Show preview
    data = await state.get_data()
    preview = ""
    if content_text:
        preview += f"<b>Texto:</b> {content_text[:100]}{'...' if len(content_text) > 100 else ''}\n"
    if media_file_ids:
        preview += f"<b>Media:</b> {media_type.capitalize()} ({len(media_file_ids)} archivo(s))\n"

    text = (
        f"🎩 <b>Crear Nodo de Historia</b>\n\n"
        f"<b>Contenido recibido:</b>\n{preview}\n"
        f"<b>Paso 2:</b> Tipo de nodo\n\n"
        f"¿Qué tipo de nodo es?"
    )

    keyboard = create_inline_keyboard([
        [{"text": "🚀 Inicio", "callback_data": "node_type:START"}],
        [{"text": "📖 Historia", "callback_data": "node_type:STORY"}],
        [{"text": "🎯 Decisión", "callback_data": "node_type:CHOICE"}],
        [{"text": "🏁 Final", "callback_data": "node_type:ENDING"}],
        [{"text": "❌ Cancelar", "callback_data": f"admin:story:details:{data['story_id']}"}],
    ])

    await message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")


@story_router.callback_query(F.data.startswith("node_type:"))
async def callback_node_type_selected(callback: CallbackQuery, state: FSMContext):
    """Handle node type selection."""
    try:
        node_type_str = callback.data.split(":")[-1]
        node_type = NodeType(node_type_str)
    except ValueError:
        await callback.answer("❌ Tipo inválido", show_alert=True)
        return

    # Store type in FSM
    await state.update_data(node_type=node_type_str)

    # If ENDING type, skip conditions and go to final confirmation
    if node_type == NodeType.ENDING:
        await state.set_state(StoryEditorStates.waiting_for_final_decision)

        data = await state.get_data()

        text = (
            f"🎩 <b>Crear Nodo de Historia</b>\n\n"
            f"<b>Tipo:</b> {node_type.display_name}\n\n"
            f"<b>Confirmación:</b>\n"
            f"Este nodo será marcado como <b>FINAL</b>.\n"
            f"Los usuarios terminarán la historia al llegar aquí.\n\n"
            f"¿Desea crear este nodo?"
        )

        keyboard = create_inline_keyboard([
            [{"text": "✅ Crear Nodo", "callback_data": "node:create:confirm"}],
            [{"text": "❌ Cancelar", "callback_data": f"admin:story:details:{data['story_id']}"}],
        ])

        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        return

    # For other types, ask about conditions
    await state.set_state(StoryEditorStates.waiting_for_conditions)

    data = await state.get_data()

    text = (
        f"🎩 <b>Crear Nodo de Historia</b>\n\n"
        f"<b>Tipo:</b> {node_type.display_name}\n\n"
        f"<b>Paso 3:</b> Condiciones de acceso\n\n"
        f"¿Este nodo tiene condiciones de acceso?\n\n"
        f"<i>Las condiciones permiten restringir el acceso basado en\n"
        f"nivel, racha, tier, etc.</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "✅ Sí, configurar", "callback_data": "node:conditions:yes"}],
        [{"text": "⏭️ No, continuar", "callback_data": "node:conditions:no"}],
        [{"text": "❌ Cancelar", "callback_data": f"admin:story:details:{data['story_id']}"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# =============================================================================
# CONDITION CONFIGURATION FLOW
# =============================================================================

@story_router.callback_query(F.data == "node:conditions:yes")
async def callback_node_conditions_start(callback: CallbackQuery, state: FSMContext):
    """Start condition configuration."""
    from bot.states.admin import RewardConditionState

    # Store return info for checkpoint/resume pattern
    await state.update_data(
        return_to="node_wizard",
        checkpoint_state="waiting_for_conditions"
    )

    await state.set_state(RewardConditionState.waiting_for_type)

    text = (
        "🎩 <b>Configurar Condición</b>\n\n"
        "<b>Tipo de Condición</b>\n\n"
        "Seleccione el tipo de condición:\n"
        "• Nivel requerido\n"
        "• Tier requerido\n"
        "• Racha de días\n"
        "• Puntos totales\n"
        "• Producto en inventario"
    )

    keyboard = create_inline_keyboard([
        [{"text": "📊 Nivel requerido", "callback_data": "cond_type:LEVEL_REACHED"}],
        [{"text": "⭐ Tier requerido", "callback_data": "cond_type:TIER_REQUIRED"}],
        [{"text": "📅 Racha de días", "callback_data": "cond_type:STREAK_LENGTH"}],
        [{"text": "💯 Puntos totales", "callback_data": "cond_type:TOTAL_POINTS"}],
        [{"text": "🛒 Producto en inventario", "callback_data": "cond_type:PRODUCT_OWNED"}],
        [{"text": "🔙 Volver", "callback_data": "node:conditions:skip"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@story_router.callback_query(F.data == "node:conditions:no")
async def callback_node_conditions_skip(callback: CallbackQuery, state: FSMContext):
    """Skip conditions and go to rewards."""
    await state.set_state(StoryEditorStates.waiting_for_rewards)

    data = await state.get_data()

    text = (
        "🎩 <b>Crear Nodo de Historia</b>\n\n"
        "<b>Paso 4:</b> Recompensas\n\n"
        "¿Desea asignar recompensas a este nodo?\n\n"
        "<i>Las recompensas se otorgan cuando el usuario\n"
        f"llega a este nodo.</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "✅ Sí, configurar", "callback_data": "node:rewards:configure"}],
        [{"text": "⏭️ No, continuar", "callback_data": "node:rewards:skip"}],
        [{"text": "❌ Cancelar", "callback_data": f"admin:story:details:{data['story_id']}"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@story_router.callback_query(F.data == "node:conditions:skip")
async def callback_node_conditions_done(callback: CallbackQuery, state: FSMContext):
    """Finish conditions and go to rewards."""
    await callback_node_conditions_skip(callback, state)


# =============================================================================
# REWARD CONFIGURATION WITH INLINE CREATION
# =============================================================================

@story_router.callback_query(F.data == "node:rewards:configure")
async def callback_node_rewards_question(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Show reward selection interface."""
    data = await state.get_data()
    selected_rewards = data.get("selected_rewards", [])

    # Get all available rewards
    from bot.database.models import Reward
    result = await session.execute(
        select(Reward).where(Reward.is_active == True).order_by(Reward.sort_order, Reward.id)
    )
    rewards = list(result.scalars().all())

    text = (
        "🎩 <b>Crear Nodo de Historia</b>\n\n"
        "<b>Paso 4:</b> Recompensas\n\n"
    )

    if selected_rewards:
        text += f"<b>Seleccionadas ({len(selected_rewards)}):</b>\n"
        for reward_id in selected_rewards:
            reward = await session.get(Reward, reward_id)
            if reward:
                text += f"✅ {reward.name}\n"
        text += "\n"

    text += "Seleccione recompensas para este nodo:"

    # Build keyboard with checkboxes
    keyboard_rows = []
    for reward in rewards[:10]:  # Limit to 10
        is_selected = reward.id in selected_rewards
        checkbox = "☑️" if is_selected else "⬜️"
        keyboard_rows.append([{
            "text": f"{checkbox} {reward.name[:25]}",
            "callback_data": f"node:reward:toggle:{reward.id}"
        }])

    keyboard_rows.append([{"text": "➕ Crear nueva recompensa", "callback_data": "node:reward:create:inline"}])
    keyboard_rows.append([
        {"text": "✅ Continuar", "callback_data": "node:rewards:done"},
        {"text": "❌ Cancelar", "callback_data": f"admin:story:details:{data['story_id']}"}
    ])

    keyboard = create_inline_keyboard(keyboard_rows)

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@story_router.callback_query(F.data.startswith("node:reward:toggle:"))
async def callback_node_reward_toggle(callback: CallbackQuery, state: FSMContext):
    """Toggle reward selection."""
    try:
        reward_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    data = await state.get_data()
    selected_rewards = data.get("selected_rewards", [])

    # Toggle
    if reward_id in selected_rewards:
        selected_rewards.remove(reward_id)
    else:
        selected_rewards.append(reward_id)

    await state.update_data(selected_rewards=selected_rewards)

    # Refresh display
    await callback_node_rewards_question(callback, state)


@story_router.callback_query(F.data == "node:reward:create:inline")
async def callback_node_reward_create_inline(callback: CallbackQuery, state: FSMContext):
    """Start inline reward creation with checkpoint pattern."""
    # Save current state for resume
    data = await state.get_data()
    await state.update_data(
        checkpoint_state="waiting_for_rewards",
        checkpoint_data={
            "story_id": data.get("story_id"),
            "node_content_text": data.get("node_content_text"),
            "node_media_file_ids": data.get("node_media_file_ids"),
            "node_media_type": data.get("node_media_type"),
            "node_type": data.get("node_type"),
            "selected_rewards": data.get("selected_rewards", []),
            "conditions": data.get("conditions", [])
        },
        return_to="story_editor",
        return_callback="node:reward:created"
    )

    # Switch to reward creation flow
    from bot.states.admin import RewardCreateState
    await state.set_state(RewardCreateState.waiting_for_name)

    text = (
        "🎩 <b>Crear Nueva Recompensa</b>\n\n"
        "<i>(Creación rápida desde editor de nodos)</i>\n\n"
        "Ingrese el nombre de la recompensa:\n"
        "<i>(Máximo 200 caracteres)</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "❌ Cancelar", "callback_data": "node:reward:create:cancel"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@story_router.callback_query(F.data == "node:reward:create:cancel")
async def callback_node_reward_create_cancel(callback: CallbackQuery, state: FSMContext):
    """Cancel inline reward creation and return to rewards selection."""
    await state.set_state(StoryEditorStates.waiting_for_rewards)
    await callback_node_rewards_question(callback, state)


@story_router.callback_query(F.data == "node:reward:created")
async def callback_node_reward_created(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Resume after reward creation - auto-select the new reward."""
    data = await state.get_data()

    # Get created reward ID
    created_reward_id = data.get("created_reward_id")

    # Restore checkpoint data
    checkpoint_data = data.get("checkpoint_data", {})
    await state.update_data(**checkpoint_data)

    # Auto-select the new reward
    selected_rewards = checkpoint_data.get("selected_rewards", [])
    if created_reward_id and created_reward_id not in selected_rewards:
        selected_rewards.append(created_reward_id)

    await state.update_data(
        selected_rewards=selected_rewards,
        checkpoint_data=None,
        checkpoint_state=None,
        return_to=None,
        return_callback=None,
        created_reward_id=None
    )

    await state.set_state(StoryEditorStates.waiting_for_rewards)

    # Show reward list again
    await callback_node_rewards_question(callback, state)

    if created_reward_id:
        await callback.answer("✅ Recompensa creada y seleccionada")
    else:
        await callback.answer()


@story_router.callback_query(F.data == "node:rewards:skip")
async def callback_node_rewards_skip(callback: CallbackQuery, state: FSMContext):
    """Skip rewards and go to final decision."""
    await state.set_state(StoryEditorStates.waiting_for_final_decision)

    data = await state.get_data()
    node_type_str = data.get("node_type")

    # If ENDING type, show completion
    if node_type_str == NodeType.ENDING.value:
        await callback_node_create_confirm(callback, state)
        return

    # Otherwise ask about choices
    text = (
        "🎩 <b>Crear Nodo de Historia</b>\n\n"
        "<b>Paso 5:</b> Elecciones\n\n"
        "¿Este nodo tiene elecciones que llevan a otros nodos?\n\n"
        "<i>Si es final, el usuario terminará la historia aquí.</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "✅ Sí, crear elecciones", "callback_data": "node:choices:create"}],
        [{"text": "🏁 No, es final", "callback_data": "node:choices:final"}],
        [{"text": "❌ Cancelar", "callback_data": f"admin:story:details:{data['story_id']}"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@story_router.callback_query(F.data == "node:rewards:done")
async def callback_node_rewards_done(callback: CallbackQuery, state: FSMContext):
    """Finish rewards and go to final decision."""
    await callback_node_rewards_skip(callback, state)


# =============================================================================
# FINAL NODE DECISION AND CHOICE CREATION
# =============================================================================

@story_router.callback_query(F.data == "node:choices:final")
async def callback_node_final_choice(callback: CallbackQuery, state: FSMContext):
    """Mark node as final (no choices)."""
    await state.update_data(is_ending=True, create_choices=False)
    await callback_node_create_confirm(callback, state)


@story_router.callback_query(F.data == "node:choices:create")
async def callback_node_create_choices(callback: CallbackQuery, state: FSMContext):
    """Start choice creation flow."""
    await state.update_data(is_ending=False, create_choices=True)
    await state.set_state(StoryEditorStates.waiting_for_choice_text)

    text = (
        "🎩 <b>Crear Elección</b>\n\n"
        "<b>Paso 1:</b> Texto de la elección\n\n"
        "Ingrese el texto que verá el usuario:\n"
        "<i>(1-500 caracteres)</i>\n\n"
        "<i>Ejemplo: 'Entrar por la puerta izquierda'</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "❌ Cancelar", "callback_data": "node:choices:cancel"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@story_router.callback_query(F.data == "node:choices:cancel")
async def callback_node_choices_cancel(callback: CallbackQuery, state: FSMContext):
    """Cancel choice creation and go back to final decision."""
    await state.set_state(StoryEditorStates.waiting_for_final_decision)
    await callback_node_rewards_skip(callback, state)


@story_router.message(StoryEditorStates.waiting_for_choice_text)
async def process_choice_text(message: Message, state: FSMContext, session: AsyncSession):
    """Handle choice text input."""
    choice_text = message.text.strip()

    if not choice_text:
        await message.answer("🎩 <b>Error:</b> El texto no puede estar vacío.\nIntente nuevamente:")
        return

    if len(choice_text) > 500:
        await message.answer("🎩 <b>Error:</b> El texto es demasiado largo (máx. 500 caracteres).\nIntente nuevamente:")
        return

    # Store choice text
    await state.update_data(current_choice_text=choice_text)
    await state.set_state(StoryEditorStates.waiting_for_target_node)

    # Get existing nodes in story
    data = await state.get_data()
    story_id = data.get("story_id")

    result = await session.execute(
        select(StoryNode).where(
            and_(
                StoryNode.story_id == story_id,
                StoryNode.is_active == True
            )
        ).order_by(StoryNode.id)
    )
    nodes = list(result.scalars().all())

    text = (
        f"🎩 <b>Crear Elección</b>\n\n"
        f"<b>Texto:</b> {choice_text[:50]}{'...' if len(choice_text) > 50 else ''}\n\n"
        f"<b>Paso 2:</b> Nodo destino\n\n"
        f"Seleccione el nodo al que lleva esta elección:"
    )

    keyboard_rows = []
    for node in nodes[:8]:  # Limit to 8 existing nodes
        preview = node.content_text[:20] if node.content_text else f"Nodo #{node.id}"
        keyboard_rows.append([{
            "text": f"📍 {preview}...",
            "callback_data": f"choice:target:{node.id}"
        }])

    keyboard_rows.append([{"text": "➕ Crear nuevo nodo", "callback_data": "choice:target:new"}])
    keyboard_rows.append([{"text": "🔙 Volver", "callback_data": "node:choices:create"}])

    keyboard = create_inline_keyboard(keyboard_rows)

    await message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")


@story_router.callback_query(F.data.startswith("choice:target:"))
async def callback_choice_target_selected(callback: CallbackQuery, state: FSMContext):
    """Handle target node selection."""
    target = callback.data.split(":")[-1]

    if target == "new":
        # Will create new node after this choice
        await state.update_data(target_node_id=None, create_target_node=True)
    else:
        try:
            target_node_id = int(target)
            await state.update_data(target_node_id=target_node_id, create_target_node=False)
        except ValueError:
            await callback.answer("❌ ID inválido", show_alert=True)
            return

    await state.set_state(StoryEditorStates.waiting_for_cost_besitos)

    text = (
        "🎩 <b>Crear Elección</b>\n\n"
        "<b>Paso 3:</b> Costo\n\n"
        "¿Cuántos besitos cuesta esta elección?\n"
        "<i>(0 = gratis)</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "0 (Gratis)", "callback_data": "choice:cost:0"}],
        [{"text": "5 besitos", "callback_data": "choice:cost:5"}],
        [{"text": "10 besitos", "callback_data": "choice:cost:10"}],
        [{"text": "20 besitos", "callback_data": "choice:cost:20"}],
        [{"text": "🔙 Volver", "callback_data": "node:choices:create"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@story_router.callback_query(F.data.startswith("choice:cost:"))
async def callback_choice_cost_selected(callback: CallbackQuery, state: FSMContext):
    """Handle choice cost selection."""
    try:
        cost = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ Costo inválido", show_alert=True)
        return

    await state.update_data(choice_cost=cost)

    # Show confirmation for creating another choice
    text = (
        "🎩 <b>Crear Elección</b>\n\n"
        f"<b>Costo:</b> {cost} besitos\n\n"
        "¿Crear otra elección para este nodo?"
    )

    keyboard = create_inline_keyboard([
        [{"text": "✅ Sí, crear otra", "callback_data": "choice:create:another"}],
        [{"text": "🏁 No, terminar nodo", "callback_data": "node:create:confirm"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@story_router.callback_query(F.data == "choice:create:another")
async def callback_choice_create_another(callback: CallbackQuery, state: FSMContext):
    """Store current choice and start another."""
    data = await state.get_data()

    # Get current choice data
    choice_data = {
        "text": data.get("current_choice_text"),
        "target_node_id": data.get("target_node_id"),
        "create_target_node": data.get("create_target_node", False),
        "cost": data.get("choice_cost", 0)
    }

    # Add to choices list
    choices = data.get("pending_choices", [])
    choices.append(choice_data)
    await state.update_data(pending_choices=choices)

    # Reset for next choice
    await state.update_data(
        current_choice_text=None,
        target_node_id=None,
        create_target_node=False,
        choice_cost=0
    )

    # Go back to choice text input
    await state.set_state(StoryEditorStates.waiting_for_choice_text)

    text = (
        "🎩 <b>Crear Otra Elección</b>\n\n"
        f"<b>Elecciones pendientes:</b> {len(choices)}\n\n"
        "Ingrese el texto para la siguiente elección:\n"
        "<i>(1-500 caracteres)</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "❌ Cancelar", "callback_data": "node:choices:cancel"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# =============================================================================
# NODE CREATION CONFIRMATION
# =============================================================================

@story_router.callback_query(F.data == "node:create:confirm")
async def callback_node_create_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Create the node with all configured data."""
    data = await state.get_data()

    story_id = data.get("story_id")
    node_type_str = data.get("node_type")
    content_text = data.get("node_content_text")
    media_file_ids = data.get("node_media_file_ids", [])
    is_ending = data.get("is_ending", False)
    selected_rewards = data.get("selected_rewards", [])
    pending_choices = data.get("pending_choices", [])
    current_choice = None

    # If there's a current choice being edited, add it to pending
    if data.get("current_choice_text"):
        current_choice = {
            "text": data.get("current_choice_text"),
            "target_node_id": data.get("target_node_id"),
            "create_target_node": data.get("create_target_node", False),
            "cost": data.get("choice_cost", 0)
        }

    # Create node using StoryEditorService
    container = ServiceContainer(session, callback.bot)

    node_type = NodeType(node_type_str) if node_type_str else NodeType.STORY

    success, msg, node = await container.story_editor.create_node(
        story_id=story_id,
        node_type=node_type,
        content_text=content_text,
        media_file_ids=media_file_ids if media_file_ids else None,
        is_ending=is_ending
    )

    if not success:
        await callback.answer(f"❌ Error: {msg}", show_alert=True)
        return

    # Attach rewards
    for reward_id in selected_rewards:
        await container.story_editor.attach_reward_to_node(node.id, reward_id)

    # Create choices
    created_choices = []
    if current_choice:
        pending_choices.append(current_choice)

    for choice_data in pending_choices:
        # If needs new target node, create it first
        target_node_id = choice_data.get("target_node_id")

        if choice_data.get("create_target_node") and not target_node_id:
            # Create placeholder target node
            success, msg, target_node = await container.story_editor.create_node(
                story_id=story_id,
                node_type=NodeType.STORY,
                content_text=f"<Continuación desde elección: {choice_data['text'][:30]}...>",
                order_index=0
            )
            if success:
                target_node_id = target_node.id

        if target_node_id:
            success, msg, choice = await container.story_editor.create_choice(
                source_node_id=node.id,
                target_node_id=target_node_id,
                choice_text=choice_data["text"],
                cost_besitos=choice_data.get("cost", 0)
            )
            if success:
                created_choices.append(choice)

    await session.commit()

    # Clear state
    await state.clear()

    # Show completion summary
    text = (
        f"🎩 <b>Nodo Creado</b>\n\n"
        f"<b>ID:</b> {node.id}\n"
        f"<b>Tipo:</b> {node_type.display_name}\n"
        f"<b>Recompensas:</b> {len(selected_rewards)}\n"
        f"<b>Elecciones:</b> {len(created_choices)}\n\n"
        f"<i>El nodo ha sido creado exitosamente.</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "➕ Crear siguiente nodo", "callback_data": f"admin:story:node:create:{story_id}"}],
        [{"text": "📋 Ver nodos", "callback_data": f"admin:story:nodes:{story_id}"}],
        [{"text": "🔙 Panel de historia", "callback_data": f"admin:story:details:{story_id}"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer("✅ Nodo creado")


# =============================================================================
# NODE LIST AND EDIT HANDLERS
# =============================================================================

@story_router.callback_query(F.data.startswith("admin:story:nodes:"))
async def callback_node_list(callback: CallbackQuery, session: AsyncSession):
    """Show nodes for a story."""
    try:
        story_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    story = await session.get(Story, story_id)
    if not story:
        await callback.answer("❌ Historia no encontrada", show_alert=True)
        return

    # Get all nodes
    result = await session.execute(
        select(StoryNode).where(
            and_(
                StoryNode.story_id == story_id,
                StoryNode.is_active == True
            )
        ).order_by(StoryNode.order_index, StoryNode.id)
    )
    nodes = list(result.scalars().all())

    if not nodes:
        text = (
            f"🎩 <b>Nodos de Historia</b>\n\n"
            f"<b>{story.title}</b>\n\n"
            f"<i>No hay nodos configurados.</i>\n\n"
            f"Use 'Crear Nodo' para agregar uno."
        )
        keyboard = create_inline_keyboard([
            [{"text": "➕ Crear Nodo", "callback_data": f"admin:story:node:create:{story_id}"}],
            [{"text": "🔙 Volver", "callback_data": f"admin:story:details:{story_id}"}],
        ])
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        return

    text = (
        f"🎩 <b>Nodos de Historia</b>\n\n"
        f"<b>{story.title}</b>\n\n"
    )

    for node in nodes:
        type_emoji = {
            "START": "🚀",
            "STORY": "📖",
            "CHOICE": "🎯",
            "ENDING": "🏁"
        }.get(node.node_type.value, "📍")

        preview = node.content_text[:30] if node.content_text else "(sin texto)"
        choice_count = len([c for c in node.choices if c.is_active])

        text += f"{type_emoji} <b>#{node.id}</b> {preview}... ({choice_count} elec.)\n"

    keyboard_rows = []
    for node in nodes:
        preview = node.content_text[:20] if node.content_text else f"Nodo #{node.id}"
        keyboard_rows.append([{
            "text": f"✏️ {preview}...",
            "callback_data": f"admin:node:edit:{node.id}"
        }])

    keyboard_rows.append([{"text": "➕ Crear Nodo", "callback_data": f"admin:story:node:create:{story_id}"}])
    keyboard_rows.append([{"text": "🔙 Volver", "callback_data": f"admin:story:details:{story_id}"}])

    keyboard = create_inline_keyboard(keyboard_rows)

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@story_router.callback_query(F.data.startswith("admin:node:edit:"))
async def callback_node_edit(callback: CallbackQuery, session: AsyncSession):
    """Show node edit menu."""
    try:
        node_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    node = await session.get(StoryNode, node_id)
    if not node:
        await callback.answer("❌ Nodo no encontrado", show_alert=True)
        return

    # Get counts
    condition_count = len(node.conditions) if node.conditions else 0
    reward_count = len(node.attached_rewards) if node.attached_rewards else 0
    choice_count = len([c for c in node.choices if c.is_active])

    type_emoji = {
        "START": "🚀",
        "STORY": "📖",
        "CHOICE": "🎯",
        "ENDING": "🏁"
    }.get(node.node_type.value, "📍")

    preview = node.content_text[:200] if node.content_text else "<i>(sin texto)</i>"

    text = (
        f"🎩 <b>Editar Nodo</b>\n\n"
        f"{type_emoji} <b>Nodo #{node.id}</b> ({node.node_type.display_name})\n\n"
        f"<b>Contenido:</b>\n{preview}\n\n"
        f"<b>Condiciones:</b> {condition_count}\n"
        f"<b>Recompensas:</b> {reward_count}\n"
        f"<b>Elecciones:</b> {choice_count}\n"
    )

    keyboard = create_inline_keyboard([
        [{"text": "📝 Editar Contenido", "callback_data": f"admin:node:edit:content:{node_id}"}],
        [{"text": f"🔒 Condiciones ({condition_count})", "callback_data": f"admin:node:conditions:{node_id}"}],
        [{"text": f"🎁 Recompensas ({reward_count})", "callback_data": f"admin:node:rewards:{node_id}"}],
        [{"text": f"🔗 Elecciones ({choice_count})", "callback_data": f"admin:node:choices:{node_id}"}],
        [{"text": "🗑️ Eliminar", "callback_data": f"admin:node:delete:{node_id}"}],
        [{"text": "🔙 Volver", "callback_data": f"admin:story:nodes:{node.story_id}"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@story_router.callback_query(F.data.startswith("admin:node:delete:"))
async def callback_node_delete(callback: CallbackQuery, session: AsyncSession):
    """Show node delete confirmation."""
    try:
        node_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    node = await session.get(StoryNode, node_id)
    if not node:
        await callback.answer("❌ Nodo no encontrado", show_alert=True)
        return

    choice_count = len([c for c in node.choices if c.is_active])

    text = (
        f"🎩 <b>Confirmar Eliminación</b>\n\n"
        f"¿Eliminar el nodo <b>#{node.id}</b>?\n\n"
        f"<i>⚠️ Esto también eliminará {choice_count} elecciones asociadas.</i>\n\n"
        f"<b>Esta acción no se puede deshacer.</b>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "✅ Sí, eliminar", "callback_data": f"admin:node:delete:confirm:{node_id}"}],
        [{"text": "❌ No, cancelar", "callback_data": f"admin:node:edit:{node_id}"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@story_router.callback_query(F.data.startswith("admin:node:delete:confirm:"))
async def callback_node_delete_confirm(callback: CallbackQuery, session: AsyncSession):
    """Confirm node deletion."""
    try:
        node_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    node = await session.get(StoryNode, node_id)
    if not node:
        await callback.answer("❌ Nodo no encontrado", show_alert=True)
        return

    story_id = node.story_id

    # Delete via service
    container = ServiceContainer(session, callback.bot)
    success, msg = await container.story_editor.delete_node(node_id)

    if success:
        await session.commit()
        await callback.answer(f"✅ Nodo eliminado")
    else:
        await callback.answer(f"❌ Error: {msg}", show_alert=True)
        return

    # Return to node list
    await callback_node_list(callback, session)


# =============================================================================
# CHOICE LIST AND EDIT HANDLERS
# =============================================================================

@story_router.callback_query(F.data.startswith("admin:node:choices:"))
async def callback_choice_list(callback: CallbackQuery, session: AsyncSession):
    """Show choices for a node."""
    try:
        node_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    node = await session.get(StoryNode, node_id)
    if not node:
        await callback.answer("❌ Nodo no encontrado", show_alert=True)
        return

    # Get active choices
    choices = [c for c in node.choices if c.is_active]

    text = (
        f"🎩 <b>Elecciones del Nodo</b>\n\n"
        f"<b>Nodo #{node.id}</b>\n\n"
    )

    if not choices:
        text += "<i>No hay elecciones configuradas.</i>\n"
    else:
        for choice in choices:
            cost_text = f" ({choice.cost_besitos}💋)" if choice.cost_besitos > 0 else ""
            text += f"• {choice.choice_text[:40]}{'...' if len(choice.choice_text) > 40 else ''}{cost_text}\n"
            text += f"  → Nodo #{choice.target_node_id}\n\n"

    keyboard_rows = []
    for choice in choices:
        keyboard_rows.append([
            {"text": f"✏️ {choice.choice_text[:20]}...", "callback_data": f"admin:choice:edit:{choice.id}"},
            {"text": "🗑️", "callback_data": f"admin:choice:delete:{choice.id}"}
        ])

    keyboard_rows.append([{"text": "➕ Agregar Elección", "callback_data": f"admin:choice:create:{node_id}"}])
    keyboard_rows.append([{"text": "🔙 Volver", "callback_data": f"admin:node:edit:{node_id}"}])

    keyboard = create_inline_keyboard(keyboard_rows)

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@story_router.callback_query(F.data.startswith("admin:choice:delete:"))
async def callback_choice_delete(callback: CallbackQuery, session: AsyncSession):
    """Confirm and delete choice."""
    try:
        choice_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    choice = await session.get(StoryChoice, choice_id)
    if not choice:
        await callback.answer("❌ Elección no encontrada", show_alert=True)
        return

    node_id = choice.source_node_id

    # Delete via service
    container = ServiceContainer(session, callback.bot)
    success, msg = await container.story_editor.delete_choice(choice_id)

    if success:
        await session.commit()
        await callback.answer("✅ Elección eliminada")
    else:
        await callback.answer(f"❌ Error: {msg}", show_alert=True)
        return

    # Refresh choice list
    class MockCallback:
        def __init__(self, message, data, bot):
            self.message = message
            self.data = data
            self.bot = bot
        async def answer(self, **kwargs):
            pass

    mock = MockCallback(callback.message, f"admin:node:choices:{node_id}", callback.bot)
    await callback_choice_list(mock, session)


# Router is registered in bot/handlers/admin/__init__.py
