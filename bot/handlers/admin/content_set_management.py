"""
ContentSet Management Handler - Gestión de conjuntos de contenido.

Handlers para administración de ContentSets:
- Listar ContentSets con paginación
- Crear nuevos ContentSets (FSM flow con upload de archivos)
- Ver detalles de ContentSet
- Activar/Desactivar ContentSets
- Eliminar ContentSets

Voice: Lucien (🎩) - Formal, elegante, mayordomo
"""
import logging
from datetime import datetime
from typing import Optional, List

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.container import ServiceContainer
from bot.utils.keyboards import create_inline_keyboard
from bot.database.enums import ContentType, ContentTier
from bot.database.models import ContentSet
from bot.states.admin import ContentSetCreateState

logger = logging.getLogger(__name__)

# Create router for content set management
content_set_router = Router(name="content_set_management")

# Constants
CONTENT_SETS_PER_PAGE = 5
CONTENT_TYPE_EMOJIS = {
    ContentType.PHOTO_SET: "📸",
    ContentType.VIDEO: "🎬",
    ContentType.AUDIO: "🎵",
    ContentType.MIXED: "📁"
}
TIER_EMOJIS = {
    ContentTier.FREE: "🌸",
    ContentTier.VIP: "⭐",
    ContentTier.PREMIUM: "💎",
    ContentTier.GIFT: "🎁"
}


@content_set_router.callback_query(F.data == "admin:content_sets")
async def callback_admin_content_sets(callback: CallbackQuery, session: AsyncSession):
    """
    Handler del menú principal de gestión de ContentSets.

    Muestra opciones para crear ContentSets, listar existentes,
    y gestionar los conjuntos de contenido.

    Args:
        callback: Callback query
        session: Sesión de BD (inyectada por middleware)
    """
    logger.debug(f"📁 Usuario {callback.from_user.id} abrió menú de ContentSets")

    text = (
        "🎩 <b>Gestión de ContentSets</b>\n\n"
        "<b>Acciones disponibles:</b>\n"
        "• Crear nuevo conjunto de contenido\n"
        "• Ver/Editar conjuntos existentes\n"
        "• Activar/Desactivar conjuntos\n\n"
        "<i>Los ContentSets son colecciones de archivos que pueden "
        "venderse en la tienda o usarse como recompensas.</i>\n\n"
        "<i>Seleccione una opción...</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "➕ Crear ContentSet", "callback_data": "admin:content_sets:create:start"}],
        [{"text": "📋 Listar ContentSets", "callback_data": "admin:content_sets:list"}],
        [{"text": "🔙 Volver", "callback_data": "admin:main"}]
    ])

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error editando mensaje de ContentSets: {e}")

    await callback.answer()


@content_set_router.callback_query(F.data == "admin:content_sets:list")
async def callback_content_set_list(callback: CallbackQuery, session: AsyncSession):
    """
    Handler para listar ContentSets con paginación.

    Muestra lista paginada de ContentSets con información
    de estado, tipo, tier y cantidad de archivos.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.debug(f"📋 Usuario {callback.from_user.id} solicitó lista de ContentSets")

    await _show_content_set_list(callback, session, page=1)


@content_set_router.callback_query(F.data.startswith("admin:content_sets:list:page:"))
async def callback_content_set_list_page(callback: CallbackQuery, session: AsyncSession):
    """
    Handler para navegación de paginación de ContentSets.

    Args:
        callback: Callback query con formato "admin:content_sets:list:page:{n}"
        session: Sesión de BD
    """
    page_str = callback.data.split(":")[-1]
    try:
        page = int(page_str)
    except ValueError:
        page = 1

    logger.debug(f"📄 Usuario {callback.from_user.id} navegó a página {page}")

    await _show_content_set_list(callback, session, page=page)


async def _show_content_set_list(callback: CallbackQuery, session: AsyncSession, page: int):
    """
    Muestra la lista paginada de ContentSets.

    Args:
        callback: Callback query
        session: Sesión de BD
        page: Número de página (1-indexed)
    """
    # Get total count
    count_result = await session.execute(select(func.count(ContentSet.id)))
    total = count_result.scalar_one_or_none() or 0

    if total == 0:
        text = (
            "🎩 <b>Gestión de ContentSets</b>\n\n"
            "<i>No hay conjuntos de contenido creados.</i>\n\n"
            "Use <b>➕ Crear ContentSet</b> para agregar el primero."
        )
        keyboard = create_inline_keyboard([
            [{"text": "➕ Crear ContentSet", "callback_data": "admin:content_sets:create:start"}],
            [{"text": "🔙 Volver", "callback_data": "admin:content_sets"}]
        ])

        try:
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                logger.error(f"❌ Error mostrando lista vacía: {e}")

        await callback.answer()
        return

    # Get content sets for current page
    offset = (page - 1) * CONTENT_SETS_PER_PAGE
    result = await session.execute(
        select(ContentSet)
        .order_by(ContentSet.created_at.desc())
        .offset(offset)
        .limit(CONTENT_SETS_PER_PAGE)
    )
    content_sets = list(result.scalars().all())

    total_pages = (total + CONTENT_SETS_PER_PAGE - 1) // CONTENT_SETS_PER_PAGE

    # Build content set list text
    lines = ["🎩 <b>ContentSets Disponibles</b>", ""]

    for cs in content_sets:
        status_emoji = "🟢" if cs.is_active else "🔴"
        type_emoji = CONTENT_TYPE_EMOJIS.get(cs.content_type, "📁")
        tier_emoji = TIER_EMOJIS.get(cs.tier, "⚪")
        lines.append(
            f"{type_emoji} {cs.name} - "
            f"{tier_emoji} {cs.file_count} archivos {status_emoji}"
        )

    lines.append("")
    lines.append(f"<i>Página {page} de {total_pages} ({total} conjuntos)</i>")

    text = "\n".join(lines)

    # Build keyboard with content set buttons
    buttons = []
    for cs in content_sets:
        # ContentSet name button -> details
        buttons.append([{
            "text": f"📁 {cs.name}",
            "callback_data": f"admin:content_set:details:{cs.id}"
        }])
        # Toggle button row
        toggle_text = "🔄 Desactivar" if cs.is_active else "✅ Activar"
        buttons.append([
            {"text": toggle_text, "callback_data": f"admin:content_set:toggle:{cs.id}"},
            {"text": "👁️ Ver", "callback_data": f"admin:content_set:details:{cs.id}"}
        ])

    # Pagination buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append({"text": "⬅️", "callback_data": f"admin:content_sets:list:page:{page-1}"})
    nav_buttons.append({"text": f"{page}/{total_pages}", "callback_data": "noop"})
    if page < total_pages:
        nav_buttons.append({"text": "➡️", "callback_data": f"admin:content_sets:list:page:{page+1}"})

    if nav_buttons:
        buttons.append(nav_buttons)

    # Back button
    buttons.append([{"text": "🔙 Volver", "callback_data": "admin:content_sets"}])

    keyboard = create_inline_keyboard(buttons)

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error mostrando lista de ContentSets: {e}")

    await callback.answer()


@content_set_router.callback_query(F.data.startswith("admin:content_set:details:"))
async def callback_content_set_details(callback: CallbackQuery, session: AsyncSession):
    """
    Handler para ver detalles de un ContentSet.

    Args:
        callback: Callback query con formato "admin:content_set:details:{id}"
        session: Sesión de BD
    """
    content_set_id_str = callback.data.split(":")[-1]
    try:
        content_set_id = int(content_set_id_str)
    except ValueError:
        logger.error(f"❌ ID de ContentSet inválido: {content_set_id_str}")
        await callback.answer("❌ Error: ID inválido", show_alert=True)
        return

    logger.debug(f"👁️ Usuario {callback.from_user.id} viendo detalles de ContentSet {content_set_id}")

    # Get content set
    result = await session.execute(
        select(ContentSet).where(ContentSet.id == content_set_id)
    )
    content_set = result.scalar_one_or_none()

    if content_set is None:
        await callback.answer("❌ ContentSet no encontrado", show_alert=True)
        return

    # Build details text
    status_text = "Activo 🟢" if content_set.is_active else "Inactivo 🔴"
    type_emoji = CONTENT_TYPE_EMOJIS.get(content_set.content_type, "📁")
    tier_emoji = TIER_EMOJIS.get(content_set.tier, "⚪")

    text = (
        f"🎩 <b>Detalles del ContentSet</b>\n\n"
        f"<b>Nombre:</b> {content_set.name}\n"
        f"<b>Descripción:</b> {content_set.description or 'Sin descripción'}\n"
        f"<b>Tipo:</b> {type_emoji} {content_set.content_type.display_name}\n"
        f"<b>Tier:</b> {tier_emoji} {content_set.tier.display_name}\n"
        f"<b>Estado:</b> {status_text}\n"
        f"<b>Archivos:</b> {content_set.file_count}\n"
        f"<b>Creado:</b> {content_set.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        f"<b>Actualizado:</b> {content_set.updated_at.strftime('%Y-%m-%d %H:%M')}"
    )

    toggle_text = "🔄 Desactivar" if content_set.is_active else "✅ Activar"
    keyboard = create_inline_keyboard([
        [{"text": toggle_text, "callback_data": f"admin:content_set:toggle:{content_set.id}"}],
        [{"text": "🗑️ Eliminar", "callback_data": f"admin:content_set:delete:{content_set.id}"}],
        [{"text": "📋 Lista", "callback_data": "admin:content_sets:list"}]
    ])

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error mostrando detalles: {e}")

    await callback.answer()


@content_set_router.callback_query(F.data.startswith("admin:content_set:toggle:"))
async def callback_content_set_toggle(callback: CallbackQuery, session: AsyncSession):
    """
    Handler para activar/desactivar un ContentSet.

    Args:
        callback: Callback query con formato "admin:content_set:toggle:{id}"
        session: Sesión de BD
    """
    content_set_id_str = callback.data.split(":")[-1]
    try:
        content_set_id = int(content_set_id_str)
    except ValueError:
        logger.error(f"❌ ID de ContentSet inválido: {content_set_id_str}")
        await callback.answer("❌ Error: ID inválido", show_alert=True)
        return

    logger.debug(f"🔄 Usuario {callback.from_user.id} cambiando estado de ContentSet {content_set_id}")

    try:
        result = await session.execute(
            select(ContentSet).where(ContentSet.id == content_set_id)
        )
        content_set = result.scalar_one_or_none()

        if content_set is None:
            await callback.answer("❌ ContentSet no encontrado", show_alert=True)
            return

        # Toggle status
        content_set.is_active = not content_set.is_active
        await session.commit()

        status_text = "activado 🟢" if content_set.is_active else "desactivado 🔴"
        logger.info(f"✅ ContentSet {content_set_id} ({content_set.name}) {status_text}")

        await callback.answer(f"✅ ContentSet {status_text}")

        # Return to content set list
        await _show_content_set_list(callback, session, page=1)

    except Exception as e:
        logger.error(f"❌ Error cambiando estado de ContentSet: {e}")
        await callback.answer("❌ Error al cambiar estado", show_alert=True)


@content_set_router.callback_query(F.data.startswith("admin:content_set:delete:"))
async def callback_content_set_delete(callback: CallbackQuery, session: AsyncSession):
    """
    Handler para mostrar confirmación de eliminación de ContentSet.

    Args:
        callback: Callback query con formato "admin:content_set:delete:{id}"
        session: Sesión de BD
    """
    content_set_id_str = callback.data.split(":")[-1]
    try:
        content_set_id = int(content_set_id_str)
    except ValueError:
        logger.error(f"❌ ID de ContentSet inválido: {content_set_id_str}")
        await callback.answer("❌ Error: ID inválido", show_alert=True)
        return

    # Get content set
    result = await session.execute(
        select(ContentSet).where(ContentSet.id == content_set_id)
    )
    content_set = result.scalar_one_or_none()

    if content_set is None:
        await callback.answer("❌ ContentSet no encontrado", show_alert=True)
        return

    text = (
        f"🎩 <b>Confirmar Eliminación</b>\n\n"
        f"¿Está seguro de que desea eliminar el ContentSet?\n\n"
        f"<b>Nombre:</b> {content_set.name}\n"
        f"<b>Archivos:</b> {content_set.file_count}\n\n"
        f"<i>Esta acción no se puede deshacer.</i>\n\n"
        f"<i>Si este ContentSet está siendo usado por productos de la tienda, "
        f"la eliminación podría causar errores.</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "✅ Confirmar Eliminación", "callback_data": f"admin:content_set:delete:confirm:{content_set.id}"}],
        [{"text": "❌ Cancelar", "callback_data": f"admin:content_set:details:{content_set.id}"}]
    ])

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error mostrando confirmación de eliminación: {e}")

    await callback.answer()


@content_set_router.callback_query(F.data.startswith("admin:content_set:delete:confirm:"))
async def callback_content_set_delete_confirm(callback: CallbackQuery, session: AsyncSession):
    """
    Handler para confirmar eliminación de ContentSet.

    Args:
        callback: Callback query con formato "admin:content_set:delete:confirm:{id}"
        session: Sesión de BD
    """
    content_set_id_str = callback.data.split(":")[-1]
    try:
        content_set_id = int(content_set_id_str)
    except ValueError:
        logger.error(f"❌ ID de ContentSet inválido: {content_set_id_str}")
        await callback.answer("❌ Error: ID inválido", show_alert=True)
        return

    logger.debug(f"🗑️ Usuario {callback.from_user.id} eliminando ContentSet {content_set_id}")

    try:
        result = await session.execute(
            select(ContentSet).where(ContentSet.id == content_set_id)
        )
        content_set = result.scalar_one_or_none()

        if content_set is None:
            await callback.answer("❌ ContentSet no encontrado", show_alert=True)
            return

        name = content_set.name

        # Delete content set
        await session.delete(content_set)
        await session.commit()

        logger.info(f"✅ ContentSet {content_set_id} ({name}) eliminado")

        await callback.answer(f"✅ ContentSet '{name}' eliminado")

        # Return to content set list
        await _show_content_set_list(callback, session, page=1)

    except Exception as e:
        logger.error(f"❌ Error eliminando ContentSet: {e}")
        await callback.answer("❌ Error al eliminar ContentSet", show_alert=True)


# ============================================================================
# FSM States for ContentSet Creation
# ============================================================================

@content_set_router.callback_query(F.data == "admin:content_sets:create:start")
async def callback_content_set_create_start(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Inicia el flujo de creación de ContentSet.

    Args:
        callback: Callback query
        state: FSM context
        session: Sesión de BD
    """
    logger.debug(f"➕ Usuario {callback.from_user.id} iniciando creación de ContentSet")

    # Initialize FSM
    await state.set_state(ContentSetCreateState.waiting_for_name)
    await state.update_data(create_data={}, file_ids=[])

    text = (
        "🎩 <b>Crear Nuevo ContentSet</b>\n\n"
        "<i>Paso 1 de 6: Nombre del conjunto</i>\n\n"
        "Por favor, envíe el nombre del ContentSet:\n"
        "<i>(máximo 200 caracteres)</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "❌ Cancelar", "callback_data": "admin:content_sets"}]
    ])

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error iniciando creación: {e}")

    await callback.answer()


@content_set_router.message(ContentSetCreateState.waiting_for_name)
async def process_content_set_name(message: Message, state: FSMContext):
    """
    Procesa el nombre del ContentSet.

    Args:
        message: Mensaje del usuario
        state: FSM context
    """
    name = message.text.strip()

    # Validate
    if not name:
        await message.answer(
            "🎩 <b>Atención</b>\n\n"
            "El nombre no puede estar vacío.\n"
            "Por favor, ingrese un nombre válido:",
            parse_mode="HTML"
        )
        return

    if len(name) > 200:
        await message.answer(
            "🎩 <b>Atención</b>\n\n"
            "El nombre es demasiado largo (máximo 200 caracteres).\n"
            "Por favor, ingrese un nombre más corto:",
            parse_mode="HTML"
        )
        return

    # Store and advance
    data = await state.get_data()
    create_data = data.get("create_data", {})
    create_data["name"] = name
    await state.update_data(create_data=create_data)

    await state.set_state(ContentSetCreateState.waiting_for_description)

    await message.answer(
        "🎩 <b>Crear Nuevo ContentSet</b>\n\n"
        f"<i>Nombre:</i> {name}\n\n"
        "<i>Paso 2 de 6: Descripción</i>\n\n"
        "Ingrese la descripción del ContentSet:\n"
        "<i>(opcional - envíe /skip para omitir)</i>",
        parse_mode="HTML"
    )


@content_set_router.message(ContentSetCreateState.waiting_for_description)
async def process_content_set_description(message: Message, state: FSMContext):
    """
    Procesa la descripción del ContentSet.

    Args:
        message: Mensaje del usuario
        state: FSM context
    """
    description = message.text.strip()

    # Handle skip command
    if description == "/skip":
        description = None
    elif len(description) > 1000:
        await message.answer(
            "🎩 <b>Atención</b>\n\n"
            "La descripción es demasiado larga (máximo 1000 caracteres).\n"
            "Por favor, ingrese una descripción más corta o /skip:",
            parse_mode="HTML"
        )
        return

    # Store and advance
    data = await state.get_data()
    create_data = data.get("create_data", {})
    create_data["description"] = description
    await state.update_data(create_data=create_data)

    await state.set_state(ContentSetCreateState.waiting_for_content_type)

    await message.answer(
        "🎩 <b>Crear Nuevo ContentSet</b>\n\n"
        f"<i>Nombre:</i> {create_data['name']}\n"
        f"<i>Descripción:</i> {description or 'Sin descripción'}\n\n"
        "<i>Paso 3 de 6: Tipo de contenido</i>\n\n"
        "Seleccione el tipo de contenido:",
        parse_mode="HTML",
        reply_markup=create_inline_keyboard([
            [{"text": "📸 Set de Fotos", "callback_data": "content_type:photo_set"}],
            [{"text": "🎬 Video", "callback_data": "content_type:video"}],
            [{"text": "🎵 Audio", "callback_data": "content_type:audio"}],
            [{"text": "📁 Mixto", "callback_data": "content_type:mixed"}]
        ])
    )


@content_set_router.callback_query(
    F.data.startswith("content_type:"),
    ContentSetCreateState.waiting_for_content_type
)
async def process_content_set_type(
    callback: CallbackQuery,
    state: FSMContext
):
    """
    Procesa la selección de tipo de contenido.

    Args:
        callback: Callback query con formato "content_type:{value}"
        state: FSM context
    """
    type_value = callback.data.split(":")[-1]

    try:
        content_type = ContentType(type_value)
    except ValueError:
        await callback.answer("❌ Tipo inválido", show_alert=True)
        return

    # Store and advance
    data = await state.get_data()
    create_data = data.get("create_data", {})
    create_data["content_type"] = content_type
    await state.update_data(create_data=create_data)

    await state.set_state(ContentSetCreateState.waiting_for_tier)

    text = (
        "🎩 <b>Crear Nuevo ContentSet</b>\n\n"
        f"<i>Nombre:</i> {create_data['name']}\n"
        f"<i>Tipo:</i> {CONTENT_TYPE_EMOJIS.get(content_type, '📁')} {content_type.display_name}\n\n"
        "<i>Paso 4 de 6: Tier de acceso</i>\n\n"
        "Seleccione el nivel de acceso:"
    )

    keyboard = create_inline_keyboard([
        [{"text": "🌸 FREE", "callback_data": "content_tier:free"}],
        [{"text": "⭐ VIP", "callback_data": "content_tier:vip"}],
        [{"text": "💎 PREMIUM", "callback_data": "content_tier:premium"}],
        [{"text": "🎁 GIFT", "callback_data": "content_tier:gift"}]
    ])

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error mostrando selección de tier: {e}")

    await callback.answer()


@content_set_router.callback_query(
    F.data.startswith("content_tier:"),
    ContentSetCreateState.waiting_for_tier
)
async def process_content_set_tier(
    callback: CallbackQuery,
    state: FSMContext
):
    """
    Procesa la selección de tier.

    Args:
        callback: Callback query con formato "content_tier:{value}"
        state: FSM context
    """
    tier_value = callback.data.split(":")[-1]

    try:
        tier = ContentTier(tier_value)
    except ValueError:
        await callback.answer("❌ Tier inválido", show_alert=True)
        return

    # Store and advance
    data = await state.get_data()
    create_data = data.get("create_data", {})
    create_data["tier"] = tier
    await state.update_data(create_data=create_data)

    await state.set_state(ContentSetCreateState.waiting_for_files)

    text = (
        "🎩 <b>Crear Nuevo ContentSet</b>\n\n"
        f"<i>Nombre:</i> {create_data['name']}\n"
        f"<i>Tipo:</i> {CONTENT_TYPE_EMOJIS.get(create_data['content_type'], '📁')} {create_data['content_type'].display_name}\n"
        f"<i>Tier:</i> {TIER_EMOJIS.get(tier, '⚪')} {tier.display_name}\n\n"
        "<i>Paso 5 de 6: Archivos</i>\n\n"
        "<b>Ahora reenvíe los mensajes con el contenido</b> que desea incluir.\n\n"
        "Puede enviar:\n"
        "• Fotos\n"
        "• Videos\n"
        "• Audios\n"
        "• Notas de voz\n\n"
        "<i>Cuando termine, envíe el comando /done</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "❌ Cancelar", "callback_data": "admin:content_sets"}]
    ])

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error iniciando carga de archivos: {e}")

    await callback.answer()


@content_set_router.message(
    ContentSetCreateState.waiting_for_files,
    F.content_type.in_(["photo", "video", "audio", "voice"])
)
async def process_content_set_file(message: Message, state: FSMContext):
    """
    Procesa archivos enviados al ContentSet.

    Args:
        message: Mensaje con archivo
        state: FSM context
    """
    # Extract file_id based on content type
    file_id = None

    if message.photo:
        # Get the largest photo (last in array)
        file_id = message.photo[-1].file_id
    elif message.video:
        file_id = message.video.file_id
    elif message.audio:
        file_id = message.audio.file_id
    elif message.voice:
        file_id = message.voice.file_id

    if not file_id:
        await message.answer(
            "🎩 <b>Atención</b>\n\n"
            "No se pudo procesar el archivo.\n"
            "Por favor, envíe fotos, videos, audios o notas de voz.",
            parse_mode="HTML"
        )
        return

    # Get current file_ids and add new one
    data = await state.get_data()
    file_ids = data.get("file_ids", [])
    file_ids.append(file_id)
    await state.update_data(file_ids=file_ids)

    # Acknowledge receipt
    await message.answer(
        f"🎩 <b>Archivo recibido</b>\n\n"
        f"Archivos recolectados: <b>{len(file_ids)}</b>\n\n"
        f"<i>Continue enviando más archivos o use /done para finalizar.</i>",
        parse_mode="HTML"
    )


@content_set_router.message(
    ContentSetCreateState.waiting_for_files,
    F.text == "/done"
)
async def process_content_set_done(message: Message, state: FSMContext):
    """
    Procesa el comando /done para finalizar la carga de archivos.

    Args:
        message: Mensaje con comando /done
        state: FSM context
    """
    data = await state.get_data()
    file_ids = data.get("file_ids", [])

    if not file_ids:
        await message.answer(
            "🎩 <b>Atención</b>\n\n"
            "Debe enviar al menos un archivo antes de continuar.\n\n"
            "Por favor, reenvíe mensajes con fotos, videos o audios.",
            parse_mode="HTML"
        )
        return

    create_data = data.get("create_data", {})

    await state.set_state(ContentSetCreateState.waiting_for_confirmation)

    text = (
        "🎩 <b>Confirmar Creación de ContentSet</b>\n\n"
        f"<b>Nombre:</b> {create_data['name']}\n"
        f"<b>Descripción:</b> {create_data.get('description') or 'Sin descripción'}\n"
        f"<b>Tipo:</b> {CONTENT_TYPE_EMOJIS.get(create_data['content_type'], '📁')} {create_data['content_type'].display_name}\n"
        f"<b>Tier:</b> {TIER_EMOJIS.get(create_data['tier'], '⚪')} {create_data['tier'].display_name}\n"
        f"<b>Archivos:</b> {len(file_ids)}\n\n"
        "<i>¿Crear este ContentSet?</i>"
    )

    await message.answer(
        text=text,
        parse_mode="HTML",
        reply_markup=create_inline_keyboard([
            [{"text": "✅ Confirmar", "callback_data": "content_set:create:confirm"}],
            [{"text": "❌ Cancelar", "callback_data": "admin:content_sets"}]
        ])
    )


@content_set_router.callback_query(
    F.data == "content_set:create:confirm",
    ContentSetCreateState.waiting_for_confirmation
)
async def process_content_set_creation(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Crea el ContentSet final.

    Args:
        callback: Callback query
        state: FSM context
        session: Sesión de BD
    """
    data = await state.get_data()
    create_data = data.get("create_data", {})
    file_ids = data.get("file_ids", [])

    if not create_data or not file_ids:
        await callback.answer("❌ Error: Datos no encontrados", show_alert=True)
        await state.clear()
        return

    try:
        # Create content set
        content_set = ContentSet(
            name=create_data["name"],
            description=create_data.get("description"),
            file_ids=file_ids,
            content_type=create_data["content_type"],
            tier=create_data["tier"],
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        session.add(content_set)
        await session.commit()

        logger.info(
            f"✅ ContentSet creado: {content_set.name} (ID: {content_set.id}) "
            f"con {len(file_ids)} archivos por usuario {callback.from_user.id}"
        )

        await callback.answer("✅ ContentSet creado exitosamente")

        # Clear state
        await state.clear()

        # Show success message and return to menu
        text = (
            "🎩 <b>ContentSet Creado</b>\n\n"
            f"<b>{content_set.name}</b> ha sido creado.\n\n"
            f"Tipo: {CONTENT_TYPE_EMOJIS.get(content_set.content_type, '📁')} {content_set.content_type.display_name}\n"
            f"Tier: {TIER_EMOJIS.get(content_set.tier, '⚪')} {content_set.tier.display_name}\n"
            f"Archivos: {content_set.file_count}\n"
            f"Estado: Activo 🟢\n\n"
            "<i>Ahora puede usar este ContentSet para crear productos en la tienda.</i>"
        )

        keyboard = create_inline_keyboard([
            [{"text": "📋 Ver ContentSets", "callback_data": "admin:content_sets:list"}],
            [{"text": "➕ Crear Otro", "callback_data": "admin:content_sets:create:start"}],
            [{"text": "🔙 Menú ContentSets", "callback_data": "admin:content_sets"}]
        ])

        try:
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                logger.error(f"❌ Error mostrando éxito: {e}")

    except Exception as e:
        logger.error(f"❌ Error creando ContentSet: {e}")
        await callback.answer("❌ Error al crear ContentSet", show_alert=True)
        await state.clear()
