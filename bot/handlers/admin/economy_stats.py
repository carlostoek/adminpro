"""
Economy Stats Handler - Dashboard de métricas de economía.

Handler para visualización de estadísticas de economía y gamificación.
"""
import logging
from datetime import datetime

from aiogram import F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.main import admin_router
from bot.services.container import ServiceContainer
from bot.utils.keyboards import create_inline_keyboard

logger = logging.getLogger(__name__)


@admin_router.callback_query(F.data == "admin:economy_stats")
async def callback_economy_stats(callback: CallbackQuery, session: AsyncSession):
    """
    Handler del callback para mostrar métricas de economía.

    Muestra dashboard con estadísticas de besitos, usuarios activos,
    transacciones y promedios.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.debug(f"📊 Usuario {callback.from_user.id} consultando métricas de economía")

    container = ServiceContainer(session, callback.bot)

    try:
        # Get economy stats
        stats = await container.stats.get_economy_stats()

        # Format message with Lucien's voice (🎩)
        text = f"""🎩 <b>Métricas de Economía</b>

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ <b>💰 BESITOS EN CIRCULACIÓN</b>
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ Total en circulación: <b>{stats.total_besitos_circulation:,}</b>
┃ Total ganado (lifetime): {stats.total_besitos_earned_lifetime:,}
┃ Total gastado (lifetime): {stats.total_besitos_spent_lifetime:,}
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ <b>👥 USUARIOS ACTIVOS</b>
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ Con perfil: <b>{stats.total_users_with_profile:,}</b>
┃ Activos (7 días): {stats.active_users_this_week:,}
┃ Activos (30 días): {stats.active_users_this_month:,}
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ <b>📊 PROMEDIOS</b>
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ Balance promedio: {stats.avg_balance:,.2f} 💰
┃ Total ganado avg: {stats.avg_total_earned:,.2f} 💰
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ <b>📈 TRANSACCIONES</b>
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ Hoy: {stats.transactions_today:,}
┃ Esta semana: {stats.transactions_this_week:,}
┃ Este mes: {stats.transactions_this_month:,}
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━

<i>Actualizado: {stats.calculated_at.strftime('%Y-%m-%d %H:%M')} UTC</i>"""

        # Create keyboard
        keyboard = create_inline_keyboard([
            [{"text": "🏆 Top Usuarios", "callback_data": "admin:economy:top_users"},
             {"text": "📊 Distribución", "callback_data": "admin:economy:levels"}],
            [{"text": "🔄 Actualizar", "callback_data": "admin:economy_stats"},
             {"text": "🔙 Volver", "callback_data": "admin:main"}]
        ])

        # Edit message
        try:
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                logger.error(f"❌ Error editando mensaje: {e}")

    except Exception as e:
        logger.error(f"❌ Error obteniendo métricas de economía: {e}")

        text = """🎩 <b>Atención</b>

Ha ocurrido una perturbación al consultar las métricas de economía.
Por favor, intente nuevamente en unos momentos."""

        keyboard = create_inline_keyboard([
            [{"text": "🔄 Reintentar", "callback_data": "admin:economy_stats"}],
            [{"text": "🔙 Volver", "callback_data": "admin:main"}]
        ])

        try:
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception:
            pass

    await callback.answer()


@admin_router.callback_query(F.data == "admin:economy:top_users")
async def callback_economy_top_users(callback: CallbackQuery, session: AsyncSession):
    """
    Handler para mostrar top usuarios (ganadores, gastadores, balances).

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.debug(f"🏆 Usuario {callback.from_user.id} consultando top usuarios")

    container = ServiceContainer(session, callback.bot)

    try:
        # Get economy stats
        stats = await container.stats.get_economy_stats()

        # Format top earners
        earners_text = ""
        for i, user in enumerate(stats.top_earners, 1):
            earners_text += f"{i}. User {user['user_id']} - L{user['level']}: {user['total_earned']:,} besitos\n"

        # Format top spenders
        spenders_text = ""
        for i, user in enumerate(stats.top_spenders, 1):
            spenders_text += f"{i}. User {user['user_id']} - L{user['level']}: {user['total_spent']:,} besitos\n"

        # Format top balances
        balances_text = ""
        for i, user in enumerate(stats.top_balances, 1):
            balances_text += f"{i}. User {user['user_id']} - L{user['level']}: {user['balance']:,} besitos\n"

        text = f"""🎩 <b>Top Usuarios</b>

<b>💰 Top Ganadores:</b>
{earners_text or 'Sin datos'}
<b>🛍️ Top Gastadores:</b>
{spenders_text or 'Sin datos'}
<b>🏦 Mayores Balances:</b>
{balances_text or 'Sin datos'}"""

        keyboard = create_inline_keyboard([
            [{"text": "🔙 Métricas", "callback_data": "admin:economy_stats"}]
        ])

        try:
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                logger.error(f"❌ Error editando mensaje: {e}")

    except Exception as e:
        logger.error(f"❌ Error obteniendo top usuarios: {e}")

        text = """🎩 <b>Atención</b>

Ha ocurrido una perturbación al consultar los top usuarios."""

        keyboard = create_inline_keyboard([
            [{"text": "🔙 Métricas", "callback_data": "admin:economy_stats"}]
        ])

        try:
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception:
            pass

    await callback.answer()


@admin_router.callback_query(F.data == "admin:economy:levels")
async def callback_economy_levels(callback: CallbackQuery, session: AsyncSession):
    """
    Handler para mostrar distribución de usuarios por nivel.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.debug(f"📊 Usuario {callback.from_user.id} consultando distribución por nivel")

    container = ServiceContainer(session, callback.bot)

    try:
        # Get economy stats
        stats = await container.stats.get_economy_stats()

        # Format level distribution
        levels_text = ""
        if stats.level_distribution:
            for level in sorted(stats.level_distribution.keys()):
                count = stats.level_distribution[level]
                # Create simple bar chart
                bar_length = min(count, 20)
                bar = "█" * bar_length
                levels_text += f"Nivel {level}: {bar} {count} usuarios\n"
        else:
            levels_text = "Sin datos disponibles\n"

        text = f"""🎩 <b>Distribución por Nivel</b>

{levels_text}
<i>Total usuarios: {stats.total_users_with_profile:,}</i>"""

        keyboard = create_inline_keyboard([
            [{"text": "🔙 Métricas", "callback_data": "admin:economy_stats"}]
        ])

        try:
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                logger.error(f"❌ Error editando mensaje: {e}")

    except Exception as e:
        logger.error(f"❌ Error obteniendo distribución por nivel: {e}")

        text = """🎩 <b>Atención</b>

Ha ocurrido una perturbación al consultar la distribución por nivel."""

        keyboard = create_inline_keyboard([
            [{"text": "🔙 Métricas", "callback_data": "admin:economy_stats"}]
        ])

        try:
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception:
            pass

    await callback.answer()
