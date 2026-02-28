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

from bot.database.models import Story, StoryNode
from bot.database.enums import StoryStatus
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


# Router is registered in bot/handlers/admin/__init__.py
