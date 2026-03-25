"""
Admin Simulation Handler - Controles de simulación para admins.

Handler del comando /simulate y gestión de modo de simulación.
Permite a los administradores ver y probar el bot como si fueran
usuarios VIP o Free.

Voice: Lucien (🎩) - Formal, mayordomo, elegante
"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.enums import SimulationMode
from bot.middlewares import AdminAuthMiddleware
from bot.services.container import ServiceContainer
from bot.utils.keyboards import get_simulation_mode_keyboard
from config import Config

logger = logging.getLogger(__name__)

# Router para handlers de simulación
router = Router(name="admin_simulation")

# Aplicar middleware de autenticación de admin
router.message.middleware(AdminAuthMiddleware())
router.callback_query.middleware(AdminAuthMiddleware())


def get_simulation_banner(context) -> str:
    """
    Genera banner visual cuando está en modo simulación.

    Args:
        context: ResolvedUserContext con estado de simulación

    Returns:
        str: Banner HTML o string vacío si no está simulando
    """
    if not context or not context.is_simulating:
        return ""

    role_display = context.simulated_role.display_name if context.simulated_role else "N/A"
    time_remaining = context.time_remaining()

    if time_remaining:
        minutes = time_remaining // 60
        seconds = time_remaining % 60
        time_str = f"{minutes}m {seconds}s"
    else:
        time_str = "Desconocido"

    return (
        f"⚠️ <b>MODO SIMULACIÓN ACTIVO</b>\n"
        f"🎭 Rol: {role_display}\n"
        f"⏱️ Tiempo restante: {time_str}\n"
        f"{'─' * 30}\n\n"
    )


def get_simulation_status_text(context, status: dict) -> str:
    """
    Genera el texto del mensaje de estado de simulación.

    Args:
        context: ResolvedUserContext con estado de simulación
        status: Dict con 'mode' y 'effective_role' del usuario

    Returns:
        str: Texto HTML del mensaje de estado
    """
    if context.is_simulating:
        banner = get_simulation_banner(context)
        return (
            f"{banner}"
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Ah… está usted viendo el reino a través de ojos diferentes.</i>\n\n"
            f"Actualmente experimentando el bot como: "
            f"<b>{status['effective_role'].upper()}</b>\n\n"
            f"Seleccione un modo para continuar su observación:"
        )
    else:
        return (
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Bienvenido al sistema de simulación, señor.</i>\n\n"
            f"Aquí puede experimentar el bot como lo verían sus usuarios, "
            f"sin modificar sus privilegios reales de administrador.\n\n"
            f"<b>Modos disponibles:</b>\n"
            f"• ⭐ VIP - Ver menús y funciones VIP\n"
            f"• 🆓 Free - Ver menús y funciones Free\n"
            f"• 👤 Real - Operar como admin normal\n\n"
            f"Seleccione un modo para comenzar:"
        )


async def get_simulation_banner_for_user(user_id: int, container) -> str:
    """
    Genera banner visual cuando el usuario está en modo simulación.

    Args:
        user_id: ID del usuario a verificar
        container: ServiceContainer con acceso a simulation service

    Returns:
        str: Banner HTML formateado o string vacío si no está simulando

    Example:
        from bot.handlers.admin.simulation import get_simulation_banner_for_user

        banner = await get_simulation_banner_for_user(user_id, container)
        await message.answer(f"{banner}🎩 Mensaje normal aquí...")
    """
    context = await container.simulation.resolve_user_context(user_id)
    return get_simulation_banner(context)


async def format_with_banner(text: str, user_id: int, container) -> str:
    """
    Prepend simulation banner to text if user is simulating.

    Args:
        text: Texto original del mensaje
        user_id: ID del usuario a verificar
        container: ServiceContainer con acceso a simulation service

    Returns:
        str: Texto con banner prepended si está simulando, o texto original

    Example:
        formatted_text = await format_with_banner("🎩 Mensaje de admin", user_id, container)
        await message.answer(formatted_text)
    """
    banner = await get_simulation_banner_for_user(user_id, container)
    if banner:
        return f"{banner}{text}"
    return text


@router.message(Command("simulate"))
async def simulation_command(message: Message, session: AsyncSession):
    """
    Handler del comando /simulate.

    Muestra el panel de control de simulación con estado actual
    y opciones para cambiar de modo.

    Args:
        message: Mensaje del usuario
        session: Sesión de BD (inyectada por middleware)
    """
    user_id = message.from_user.id
    logger.info(f"🎭 Panel de simulación abierto por admin {user_id}")

    # Verificar que sea admin (doble seguridad, ya tiene middleware)
    if not Config.is_admin(user_id):
        await message.answer(
            "🎩 <b>Acceso Denegado</b>\n\n"
            "No tiene permisos para acceder al sistema de simulación.",
            parse_mode="HTML"
        )
        return

    # Crear container de services
    container = ServiceContainer(session, message.bot)

    # Obtener estado de simulación
    context = await container.simulation.resolve_user_context(user_id)
    status = await container.simulation.get_simulation_status(user_id)

    # Construir mensaje con voz de Lucien usando helper
    text = get_simulation_status_text(context, status)

    # Obtener teclado de selección de modo
    current_mode = SimulationMode(status['mode']) if status else SimulationMode.REAL
    keyboard = get_simulation_mode_keyboard(current_mode)

    await message.answer(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "simulation:refresh")
async def simulation_refresh_callback(callback: CallbackQuery, session: AsyncSession):
    """
    Refresca el estado de simulación.

    Actualiza el mensaje con el estado actual y tiempo restante.
    """
    user_id = callback.from_user.id

    if not Config.is_admin(user_id):
        await callback.answer("No tiene permisos", show_alert=True)
        return

    container = ServiceContainer(session, callback.bot)
    context = await container.simulation.resolve_user_context(user_id)
    status = await container.simulation.get_simulation_status(user_id)

    # Construir mensaje actualizado usando helper
    text = get_simulation_status_text(context, status)

    current_mode = SimulationMode(status['mode']) if status else SimulationMode.REAL
    keyboard = get_simulation_mode_keyboard(current_mode)

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error actualizando mensaje: {e}")

    await callback.answer("Estado actualizado")


@router.callback_query(F.data == "simulation:set:vip")
async def simulation_set_vip_callback(callback: CallbackQuery, session: AsyncSession):
    """
    Activa modo de simulación VIP.
    """
    user_id = callback.from_user.id

    if not Config.is_admin(user_id):
        await callback.answer("No tiene permisos", show_alert=True)
        return

    # Responder inmediatamente al callback
    await callback.answer("Activando simulación VIP...")

    container = ServiceContainer(session, callback.bot)

    # Iniciar simulación VIP
    success, msg, context = await container.simulation.start_simulation(
        admin_id=user_id,
        mode=SimulationMode.VIP
    )

    if success and context:
        logger.info(f"🎭 Admin {user_id} activó simulación VIP")

        banner = get_simulation_banner(context)
        text = (
            f"{banner}"
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Excelente elección, señor.</i>\n\n"
            f"Ahora está viendo el bot como un <b>usuario VIP</b>. "
            f"Todos los menús y funciones se mostrarán desde esa perspectiva.\n\n"
            f"La simulación expirará automáticamente en 30 minutos, "
            f"o puede desactivarla manualmente cuando desee."
        )
    else:
        text = (
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Disculpe, ha ocurrido una perturbación...</i>\n\n"
            f"No se pudo activar la simulación: {msg}"
        )

    keyboard = get_simulation_mode_keyboard(SimulationMode.VIP)

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error actualizando mensaje: {e}")


@router.callback_query(F.data == "simulation:set:free")
async def simulation_set_free_callback(callback: CallbackQuery, session: AsyncSession):
    """
    Activa modo de simulación FREE.
    """
    user_id = callback.from_user.id

    if not Config.is_admin(user_id):
        await callback.answer("No tiene permisos", show_alert=True)
        return

    await callback.answer("Activando simulación Free...")

    container = ServiceContainer(session, callback.bot)

    success, msg, context = await container.simulation.start_simulation(
        admin_id=user_id,
        mode=SimulationMode.FREE
    )

    if success and context:
        logger.info(f"🎭 Admin {user_id} activó simulación FREE")

        banner = get_simulation_banner(context)
        text = (
            f"{banner}"
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Como desee, señor.</i>\n\n"
            f"Ahora está viendo el bot como un <b>usuario Free</b>. "
            f"Experimentará las limitaciones y opciones disponibles "
            f"para quienes esperan en el vestíbulo.\n\n"
            f"La simulación expirará automáticamente en 30 minutos."
        )
    else:
        text = (
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Disculpe, ha ocurrido una perturbación...</i>\n\n"
            f"No se pudo activar la simulación: {msg}"
        )

    keyboard = get_simulation_mode_keyboard(SimulationMode.FREE)

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error actualizando mensaje: {e}")


@router.callback_query(F.data == "simulation:set:real")
async def simulation_set_real_callback(callback: CallbackQuery, session: AsyncSession):
    """
    Desactiva la simulación (vuelve a modo REAL/admin).
    """
    user_id = callback.from_user.id

    if not Config.is_admin(user_id):
        await callback.answer("No tiene permisos", show_alert=True)
        return

    await callback.answer("Desactivando simulación...")

    container = ServiceContainer(session, callback.bot)

    success, msg = await container.simulation.stop_simulation(user_id)

    if success:
        logger.info(f"🎭 Admin {user_id} desactivó simulación")

        text = (
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Volviendo a la realidad, señor.</i>\n\n"
            f"La simulación ha sido desactivada. "
            f"Ahora opera con sus privilegios completos de administrador.\n\n"
            f"Sus observaciones como usuario han sido registradas."
        )
    else:
        text = (
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Disculpe, ha ocurrido una perturbación...</i>\n\n"
            f"{msg}"
        )

    keyboard = get_simulation_mode_keyboard(SimulationMode.REAL)

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"❌ Error actualizando mensaje: {e}")
