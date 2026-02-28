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
    """Handler for paginated story list."""
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

    # Build list text
    text = "🎩 <b>Lista de Historias</b>\n\n"

    for story in stories:
        node_count = len(story.nodes) if story.nodes else 0
        badge = get_story_status_badge(story.status, story.is_active)
        premium_badge = "💎" if story.is_premium else "🆓"

        text += f"{badge} <b>{story.title}</b>\n"
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

    # Build action buttons based on status
    keyboard_rows = []

    if story.is_active:
        keyboard_rows.append([{"text": "✏️ Editar", "callback_data": f"admin:story:edit:{story.id}"}])

        if story.status == StoryStatus.DRAFT:
            keyboard_rows.append([{"text": "🚀 Publicar", "callback_data": f"admin:story:publish:{story.id}"}])
            keyboard_rows.append([{"text": "🗑️ Eliminar", "callback_data": f"admin:story:delete:{story.id}"}])
        elif story.status == StoryStatus.PUBLISHED:
            keyboard_rows.append([{"text": "⏸️ Despublicar", "callback_data": f"admin:story:unpublish:{story.id}"}])

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
            [{"text": "🔙 Volver", "callback_data": f"admin:story:details:{story_id}"}],
        ])

        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        return

    # Publish story
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
