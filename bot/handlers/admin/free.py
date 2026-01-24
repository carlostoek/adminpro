"""
Free Handlers - Gestión del canal Free.

Handlers para:
- Submenú Free
- Configuración del canal Free
- Configuración de tiempo de espera
"""
import logging
from aiogram import F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.main import admin_router
from bot.states.admin import ChannelSetupStates, WaitTimeSetupStates
from bot.services.container import ServiceContainer

logger = logging.getLogger(__name__)


@admin_router.callback_query(F.data == "admin:free")
async def callback_free_menu(callback: CallbackQuery, session: AsyncSession):
    """
    Muestra el submenú de gestión Free.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.debug(f"📺 Usuario {callback.from_user.id} abrió menú Free")

    container = ServiceContainer(session, callback.bot)

    # Verificar si canal Free está configurado
    is_configured = await container.channel.is_free_channel_configured()

    if is_configured:
        free_channel_id = await container.channel.get_free_channel_id()
        wait_time = await container.config.get_wait_time()

        # Obtener info del canal
        channel_info = await container.channel.get_channel_info(free_channel_id)
        channel_name = channel_info.title if channel_info else "Canal Free"

        # Get message from provider
        session_history = container.session_history
        text, keyboard = container.message.admin.free.free_menu(
            is_configured=True,
            channel_name=channel_name,
            wait_time_minutes=wait_time,
            user_id=callback.from_user.id,
            session_history=session_history
        )
    else:
        # Get message from provider
        session_history = container.session_history
        text, keyboard = container.message.admin.free.free_menu(
            is_configured=False,
            user_id=callback.from_user.id,
            session_history=session_history
        )

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"Error editando mensaje Free: {e}")

    await callback.answer()


@admin_router.callback_query(F.data == "free:setup")
async def callback_free_setup(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Inicia el proceso de configuración del canal Free.

    Args:
        callback: Callback query
        session: Sesión de BD
        state: FSM context
    """
    logger.info(f"⚙️ Usuario {callback.from_user.id} iniciando setup Free")

    container = ServiceContainer(session, callback.bot)

    # Entrar en estado FSM
    await state.set_state(ChannelSetupStates.waiting_for_free_channel)

    # Get message from provider
    text, keyboard = container.message.admin.free.setup_channel_prompt()

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"Error editando mensaje setup Free: {e}")

    await callback.answer()


@admin_router.message(ChannelSetupStates.waiting_for_free_channel)
async def process_free_channel_forward(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """
    Procesa el mensaje reenviado para configurar el canal Free.

    Args:
        message: Mensaje reenviado del canal
        session: Sesión de BD
        state: FSM context
    """
    # Validaciones idénticas a VIP
    if not message.forward_from_chat:
        await message.answer(
            "❌ Debes <b>reenviar</b> un mensaje del canal Free.\n\n"
            "No me envíes el ID manualmente, reenvía un mensaje.",
            parse_mode="HTML"
        )
        return

    forward_chat = message.forward_from_chat

    if forward_chat.type not in ["channel", "supergroup"]:
        await message.answer(
            "❌ El mensaje debe ser de un <b>canal</b> o <b>supergrupo</b>.\n\n"
            "Reenvía un mensaje del canal Free.",
            parse_mode="HTML"
        )
        return

    channel_id = str(forward_chat.id)
    channel_title = forward_chat.title

    logger.info(f"📺 Configurando canal Free: {channel_id} ({channel_title})")

    container = ServiceContainer(session, message.bot)

    # Intentar configurar el canal
    success, msg = await container.channel.setup_free_channel(channel_id)

    if success:
        # Get success message from provider
        text, keyboard = container.message.admin.free.channel_configured_success(
            channel_name=channel_title,
            channel_id=channel_id
        )

        await message.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        await state.clear()
    else:
        await message.answer(
            f"{msg}\n\n"
            f"Verifica permisos del bot e intenta nuevamente.",
            parse_mode="HTML"
        )


@admin_router.callback_query(F.data == "free:set_wait_time")
async def callback_set_wait_time(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Inicia configuración de tiempo de espera.

    Args:
        callback: Callback query
        session: Sesión de BD
        state: FSM context
    """
    logger.info(f"⏱️ Usuario {callback.from_user.id} configurando wait time")

    container = ServiceContainer(session, callback.bot)
    current_wait_time = await container.config.get_wait_time()

    # Entrar en estado FSM
    await state.set_state(WaitTimeSetupStates.waiting_for_minutes)

    # Get message from provider
    text, keyboard = container.message.admin.free.wait_time_setup_prompt(current_wait_time)

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"Error editando mensaje wait time: {e}")

    await callback.answer()


@admin_router.message(WaitTimeSetupStates.waiting_for_minutes)
async def process_wait_time_input(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """
    Procesa el input de tiempo de espera.

    Args:
        message: Mensaje con los minutos
        session: Sesión de BD
        state: FSM context
    """
    container = ServiceContainer(session, message.bot)

    # Intentar convertir a número
    try:
        minutes = int(message.text)
    except ValueError:
        # Get error message from provider
        text, keyboard = container.message.admin.free.invalid_wait_time_input("not_number")
        await message.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return

    # Validar rango
    if minutes < 1:
        # Get error message from provider
        text, keyboard = container.message.admin.free.invalid_wait_time_input("too_low")
        await message.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return

    try:
        # Actualizar configuración
        await container.config.set_wait_time(minutes)

        # Get success message from provider
        text, keyboard = container.message.admin.free.wait_time_updated(minutes)

        await message.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        # Limpiar estado
        await state.clear()

    except Exception as e:
        logger.error(f"Error actualizando wait time: {e}", exc_info=True)
        await message.answer(
            "❌ Error al actualizar el tiempo de espera.\n\n"
            "Intenta nuevamente.",
            parse_mode="HTML"
        )


# ===== SUBMENÚ DE CONFIGURACIÓN FREE =====

@admin_router.callback_query(F.data == "free:config")
async def callback_free_config(callback: CallbackQuery, session: AsyncSession):
    """
    Muestra el submenú de configuración Free.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.debug(f"⚙️ Usuario {callback.from_user.id} abrió configuración Free")

    container = ServiceContainer(session, callback.bot)
    wait_time = await container.config.get_wait_time()

    # Get message from provider
    text, keyboard = container.message.admin.free.config_menu(wait_time)

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"Error editando mensaje config Free: {e}")

    await callback.answer()
