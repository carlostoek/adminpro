"""
Economy Config Handler - Configuración de economía (besitos).

Handler para que administradores configuren valores de economía:
- Besitos por reacción
- Besitos para regalo diario
- Bonus por racha
- Máximo de reacciones por día

Todos los mensajes usan la voz de Lucien (🎩).
"""
import logging
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.container import ServiceContainer
from bot.utils.keyboards import create_inline_keyboard
from bot.states.admin import EconomyConfigState

logger = logging.getLogger(__name__)

# Router para handlers de economía
economy_config_router = Router(name="economy_config")


@economy_config_router.callback_query(F.data == "admin:economy_config")
async def callback_economy_config(callback: CallbackQuery, session: AsyncSession):
    """
    Handler para mostrar menú de configuración de economía.

    Muestra los valores actuales de configuración económica
    y permite modificarlos.

    Args:
        callback: Callback query
        session: Sesión de BD (inyectada por middleware)
    """
    logger.debug(f"💰 Usuario {callback.from_user.id} abrió menú de economía")

    # Crear container de services
    container = ServiceContainer(session, callback.bot)

    try:
        # Obtener valores actuales
        besitos_reaction = await container.config.get_besitos_per_reaction()
        besitos_daily = await container.config.get_besitos_daily_gift()
        streak_bonus = await container.config.get_besitos_daily_streak_bonus()
        max_reactions = await container.config.get_max_reactions_per_day()

        # Formatear mensaje con voz de Lucien
        text = (
            "🎩 <b>Configuración de Economía</b>\n\n"
            "<b>Valores Actuales:</b>\n"
            f"💰 Besitos por reacción: <b>{besitos_reaction}</b>\n"
            f"🎁 Besitos regalo diario: <b>{besitos_daily}</b>\n"
            f"🔥 Bonus por racha: <b>{streak_bonus}</b>\n"
            f"⚡ Máx. reacciones/día: <b>{max_reactions}</b>\n\n"
            "<i>Seleccione un valor para modificar...</i>"
        )

        # Keyboard con 4 botones (2x2 grid) + volver
        keyboard = create_inline_keyboard([
            [
                {"text": "💰 Reacción", "callback_data": "admin:economy:edit:reaction"},
                {"text": "🎁 Regalo", "callback_data": "admin:economy:edit:daily"}
            ],
            [
                {"text": "🔥 Racha", "callback_data": "admin:economy:edit:streak"},
                {"text": "⚡ Límite", "callback_data": "admin:economy:edit:limit"}
            ],
            [{"text": "🔙 Volver", "callback_data": "admin:config"}]
        ])

        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"❌ Error mostrando config de economía: {e}")
        await callback.message.edit_text(
            text="🎩 <b>Atención</b> - Ha ocurrido una perturbación en el sistema...",
            reply_markup=create_inline_keyboard([
                [{"text": "🔙 Volver", "callback_data": "admin:config"}]
            ]),
            parse_mode="HTML"
        )

    await callback.answer()


@economy_config_router.callback_query(F.data == "admin:economy:edit:reaction")
async def callback_edit_reaction(callback: CallbackQuery, state: FSMContext):
    """
    Inicia edición de besitos por reacción.

    Args:
        callback: Callback query
        state: FSM context para manejar estado
    """
    logger.debug(f"💰 Usuario {callback.from_user.id} editando besitos por reacción")

    await state.set_state(EconomyConfigState.waiting_for_reaction_value)

    await callback.message.edit_text(
        text="🎩 Ingrese la cantidad de besitos por reacción (número positivo):",
        reply_markup=create_inline_keyboard([
            [{"text": "🔙 Cancelar", "callback_data": "admin:economy_config"}]
        ]),
        parse_mode="HTML"
    )

    await callback.answer()


@economy_config_router.message(EconomyConfigState.waiting_for_reaction_value)
async def process_reaction_value(message: Message, state: FSMContext, session: AsyncSession):
    """
    Procesa el valor ingresado para besitos por reacción.

    Args:
        message: Mensaje del usuario
        state: FSM context
        session: Sesión de BD
    """
    logger.debug(f"💰 Procesando valor de reacción: {message.text}")

    # Validar que sea un número entero positivo
    try:
        value = int(message.text.strip())
        if value <= 0:
            raise ValueError("Value must be positive")
    except (ValueError, AttributeError):
        await message.answer(
            text="🎩 <b>Valor inválido</b> - Debe ser un número entero positivo.",
            parse_mode="HTML"
        )
        return  # Mantener estado para reintentar

    # Guardar valor
    container = ServiceContainer(session, message.bot)

    try:
        success, msg = await container.config.set_besitos_per_reaction(value)

        if success:
            await message.answer(
                text="🎩 <b>Configuración actualizada</b> - El valor ha sido modificado.",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                text=f"🎩 <b>Error</b> - No se pudo actualizar: {msg}",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"❌ Error actualizando besitos por reacción: {e}")
        await message.answer(
            text="🎩 <b>Atención</b> - Ha ocurrido una perturbación en el sistema...",
            parse_mode="HTML"
        )

    # Limpiar estado y volver al menú
    await state.clear()

    # Mostrar menú actualizado
    await show_economy_config_menu(message, session)


@economy_config_router.callback_query(F.data == "admin:economy:edit:daily")
async def callback_edit_daily(callback: CallbackQuery, state: FSMContext):
    """
    Inicia edición de besitos para regalo diario.

    Args:
        callback: Callback query
        state: FSM context
    """
    logger.debug(f"💰 Usuario {callback.from_user.id} editando besitos diarios")

    await state.set_state(EconomyConfigState.waiting_for_daily_value)

    await callback.message.edit_text(
        text="🎩 Ingrese los besitos para regalo diario base (número positivo):",
        reply_markup=create_inline_keyboard([
            [{"text": "🔙 Cancelar", "callback_data": "admin:economy_config"}]
        ]),
        parse_mode="HTML"
    )

    await callback.answer()


@economy_config_router.message(EconomyConfigState.waiting_for_daily_value)
async def process_daily_value(message: Message, state: FSMContext, session: AsyncSession):
    """
    Procesa el valor ingresado para besitos diarios.

    Args:
        message: Mensaje del usuario
        state: FSM context
        session: Sesión de BD
    """
    logger.debug(f"💰 Procesando valor diario: {message.text}")

    try:
        value = int(message.text.strip())
        if value <= 0:
            raise ValueError("Value must be positive")
    except (ValueError, AttributeError):
        await message.answer(
            text="🎩 <b>Valor inválido</b> - Debe ser un número entero positivo.",
            parse_mode="HTML"
        )
        return

    container = ServiceContainer(session, message.bot)

    try:
        success, msg = await container.config.set_besitos_daily_gift(value)

        if success:
            await message.answer(
                text="🎩 <b>Configuración actualizada</b> - El valor ha sido modificado.",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                text=f"🎩 <b>Error</b> - No se pudo actualizar: {msg}",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"❌ Error actualizando besitos diarios: {e}")
        await message.answer(
            text="🎩 <b>Atención</b> - Ha ocurrido una perturbación en el sistema...",
            parse_mode="HTML"
        )

    await state.clear()
    await show_economy_config_menu(message, session)


@economy_config_router.callback_query(F.data == "admin:economy:edit:streak")
async def callback_edit_streak(callback: CallbackQuery, state: FSMContext):
    """
    Inicia edición de bonus por racha.

    Args:
        callback: Callback query
        state: FSM context
    """
    logger.debug(f"💰 Usuario {callback.from_user.id} editando bonus de racha")

    await state.set_state(EconomyConfigState.waiting_for_streak_value)

    await callback.message.edit_text(
        text="🎩 Ingrese el bonus por día de racha (número positivo):",
        reply_markup=create_inline_keyboard([
            [{"text": "🔙 Cancelar", "callback_data": "admin:economy_config"}]
        ]),
        parse_mode="HTML"
    )

    await callback.answer()


@economy_config_router.message(EconomyConfigState.waiting_for_streak_value)
async def process_streak_value(message: Message, state: FSMContext, session: AsyncSession):
    """
    Procesa el valor ingresado para bonus de racha.

    Args:
        message: Mensaje del usuario
        state: FSM context
        session: Sesión de BD
    """
    logger.debug(f"💰 Procesando valor de racha: {message.text}")

    try:
        value = int(message.text.strip())
        if value <= 0:
            raise ValueError("Value must be positive")
    except (ValueError, AttributeError):
        await message.answer(
            text="🎩 <b>Valor inválido</b> - Debe ser un número entero positivo.",
            parse_mode="HTML"
        )
        return

    container = ServiceContainer(session, message.bot)

    try:
        success, msg = await container.config.set_besitos_daily_streak_bonus(value)

        if success:
            await message.answer(
                text="🎩 <b>Configuración actualizada</b> - El valor ha sido modificado.",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                text=f"🎩 <b>Error</b> - No se pudo actualizar: {msg}",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"❌ Error actualizando bonus de racha: {e}")
        await message.answer(
            text="🎩 <b>Atención</b> - Ha ocurrido una perturbación en el sistema...",
            parse_mode="HTML"
        )

    await state.clear()
    await show_economy_config_menu(message, session)


@economy_config_router.callback_query(F.data == "admin:economy:edit:limit")
async def callback_edit_limit(callback: CallbackQuery, state: FSMContext):
    """
    Inicia edición de máximo de reacciones por día.

    Args:
        callback: Callback query
        state: FSM context
    """
    logger.debug(f"💰 Usuario {callback.from_user.id} editando límite de reacciones")

    await state.set_state(EconomyConfigState.waiting_for_limit_value)

    await callback.message.edit_text(
        text="🎩 Ingrese el máximo de reacciones por día (número positivo):",
        reply_markup=create_inline_keyboard([
            [{"text": "🔙 Cancelar", "callback_data": "admin:economy_config"}]
        ]),
        parse_mode="HTML"
    )

    await callback.answer()


@economy_config_router.message(EconomyConfigState.waiting_for_limit_value)
async def process_limit_value(message: Message, state: FSMContext, session: AsyncSession):
    """
    Procesa el valor ingresado para límite de reacciones.

    Args:
        message: Mensaje del usuario
        state: FSM context
        session: Sesión de BD
    """
    logger.debug(f"💰 Procesando valor de límite: {message.text}")

    try:
        value = int(message.text.strip())
        if value <= 0:
            raise ValueError("Value must be positive")
    except (ValueError, AttributeError):
        await message.answer(
            text="🎩 <b>Valor inválido</b> - Debe ser un número entero positivo.",
            parse_mode="HTML"
        )
        return

    container = ServiceContainer(session, message.bot)

    try:
        success, msg = await container.config.set_max_reactions_per_day(value)

        if success:
            await message.answer(
                text="🎩 <b>Configuración actualizada</b> - El valor ha sido modificado.",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                text=f"🎩 <b>Error</b> - No se pudo actualizar: {msg}",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"❌ Error actualizando límite de reacciones: {e}")
        await message.answer(
            text="🎩 <b>Atención</b> - Ha ocurrido una perturbación en el sistema...",
            parse_mode="HTML"
        )

    await state.clear()
    await show_economy_config_menu(message, session)


async def show_economy_config_menu(message: Message, session: AsyncSession):
    """
    Muestra el menú de configuración de economía (helper).

    Args:
        message: Mensaje para editar/actualizar
        session: Sesión de BD
    """
    container = ServiceContainer(session, message.bot)

    try:
        besitos_reaction = await container.config.get_besitos_per_reaction()
        besitos_daily = await container.config.get_besitos_daily_gift()
        streak_bonus = await container.config.get_besitos_daily_streak_bonus()
        max_reactions = await container.config.get_max_reactions_per_day()

        text = (
            "🎩 <b>Configuración de Economía</b>\n\n"
            "<b>Valores Actuales:</b>\n"
            f"💰 Besitos por reacción: <b>{besitos_reaction}</b>\n"
            f"🎁 Besitos regalo diario: <b>{besitos_daily}</b>\n"
            f"🔥 Bonus por racha: <b>{streak_bonus}</b>\n"
            f"⚡ Máx. reacciones/día: <b>{max_reactions}</b>\n\n"
            "<i>Seleccione un valor para modificar...</i>"
        )

        keyboard = create_inline_keyboard([
            [
                {"text": "💰 Reacción", "callback_data": "admin:economy:edit:reaction"},
                {"text": "🎁 Regalo", "callback_data": "admin:economy:edit:daily"}
            ],
            [
                {"text": "🔥 Racha", "callback_data": "admin:economy:edit:streak"},
                {"text": "⚡ Límite", "callback_data": "admin:economy:edit:limit"}
            ],
            [{"text": "🔙 Volver", "callback_data": "admin:config"}]
        ])

        await message.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"❌ Error mostrando menú de economía: {e}")
        await message.answer(
            text="🎩 <b>Atención</b> - Ha ocurrido una perturbación...",
            reply_markup=create_inline_keyboard([
                [{"text": "🔙 Volver", "callback_data": "admin:config"}]
            ]),
            parse_mode="HTML"
        )
