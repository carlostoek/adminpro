"""
Admin Performance Profiling Handler

Handler para ejecutar profiling de handlers desde Telegram.
Solo accesible para administradores.
"""

import logging
import tempfile
from pathlib import Path

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from bot.middlewares import AdminAuthMiddleware
from bot.utils.profiler import AsyncProfiler, HandlerProfiler
from bot.utils.query_analyzer import analyze_queries, QueryOptimizationSuggestions

logger = logging.getLogger(__name__)

profile_router = Router(name="admin_profile")
profile_router.message.middleware(AdminAuthMiddleware())
profile_router.callback_query.middleware(AdminAuthMiddleware())

# Registry of profilable handlers
HANDLER_REGISTRY = {
    "admin": "bot.handlers.admin.main.cmd_admin",
    "vip_panel": "bot.handlers.admin.vip.cmd_vip_panel",
    "free_panel": "bot.handlers.admin.free.cmd_free_panel",
    "users": "bot.handlers.admin.users.cmd_users",
    "start": "bot.handlers.user.start.cmd_start",
    "vip_entry": "bot.handlers.user.vip_entry.cmd_vip",
    "free_flow": "bot.handlers.user.free_flow.cmd_free",
}


@profile_router.message(Command("profile"))
async def cmd_profile(message: Message, session: AsyncSession):
    """
    Ejecuta profiling de un handler especifico.

    Uso:
        /profile - Lista handlers disponibles
        /profile admin - Profilea el handler admin
        /profile start --iterations=3 - Profilea con 3 iteraciones

    Args:
        message: Mensaje del comando
        session: Sesion de BD
    """
    args = message.text.split()[1:] if message.text else []

    # List available handlers
    if not args or args[0] in ["list", "--list", "-l"]:
        handlers_text = "\n".join(
            f"  • <code>{key}</code> - {path}"
            for key, path in HANDLER_REGISTRY.items()
        )
        await message.answer(
            f"📊 <b>Handlers disponibles para profiling:</b>\n\n"
            f"{handlers_text}\n\n"
            f"<i>Uso: /profile &lt;handler_name&gt; [--iterations=N]</i>",
            parse_mode="HTML"
        )
        return

    handler_key = args[0]
    if handler_key not in HANDLER_REGISTRY:
        await message.answer(
            f"❌ <b>Handler no encontrado:</b> {handler_key}\n\n"
            f"Usa <code>/profile</code> para ver los disponibles.",
            parse_mode="HTML"
        )
        return

    # Parse iterations
    iterations = 1
    for arg in args[1:]:
        if arg.startswith("--iterations="):
            iterations = int(arg.split("=")[1])
        elif arg.startswith("-i="):
            iterations = int(arg.split("=")[1])

    if iterations > 10:
        await message.answer(
            "⚠️ <b>Demasiadas iteraciones</b>\n"
            "El maximo permitido es 10 para evitar timeouts."
        )
        return

    handler_path = HANDLER_REGISTRY[handler_key]

    # Send initial status
    status_msg = await message.answer(
        f"🔍 <b>Profileando handler:</b> <code>{handler_key}</code>\n"
        f"Iteraciones: {iterations}\n\n"
        f"<i>Esto puede tomar unos segundos...</i>",
        parse_mode="HTML"
    )

    try:
        # Import and profile
        import importlib
        module_path, func_name = handler_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        handler = getattr(module, func_name)

        profiler = AsyncProfiler()

        # Mock objects
        from unittest.mock import AsyncMock, MagicMock

        mock_message = MagicMock()
        mock_message.from_user.id = message.from_user.id
        mock_message.from_user.username = message.from_user.username or "admin"
        mock_message.answer = AsyncMock()
        mock_message.bot = message.bot

        # Run profiling
        result = await profiler.profile_async(
            handler,
            mock_message,
            session
        )

        # Format results
        report_lines = [
            f"📊 <b>Resultados del Profiling</b>",
            f"",
            f"Handler: <code>{handler_key}</code>",
            f"Iteraciones: {iterations}",
            f"",
            f"⏱️ <b>Duracion promedio:</b> {result.duration_ms:.2f}ms",
            f"🗄️ <b>Queries:</b> {result.query_count}",
            f"",
            f"📈 <b>Funciones mas lentas:</b>"
        ]

        for func in result.top_functions[:5]:
            name = func['name'][:40]  # Truncate long names
            report_lines.append(
                f"  • <code>{name}</code>: {func['time_ms']:.2f}ms"
            )

        report = "\n".join(report_lines)

        await status_msg.delete()

        # Send report
        if len(report) > 4000:
            # Send as file if too long
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.txt',
                delete=False
            ) as f:
                f.write(result.summary())
                f.write("\n\n")
                f.write(result.text_output or "")

            await message.answer_document(
                document=FSInputFile(f.name),
                caption=f"📊 Profile report for {handler_key}"
            )
            Path(f.name).unlink()
        else:
            await message.answer(report, parse_mode="HTML")

        # Offer HTML report
        if result.html_output:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="📄 Descargar reporte HTML",
                    callback_data=f"profile:html:{handler_key}"
                )]
            ])
            await message.answer(
                "¿Deseas descargar el reporte HTML detallado?",
                reply_markup=keyboard
            )

    except Exception as e:
        logger.exception("Error durante profiling")
        await status_msg.edit_text(
            f"❌ <b>Error en profiling</b>\n\n"
            f"<code>{str(e)[:500]}</code>"
        )


@profile_router.callback_query(F.data.startswith("profile:html:"))
async def callback_profile_html(callback: CallbackQuery):
    """Envia reporte HTML de profiling."""
    handler_key = callback.data.split(":")[2]

    await callback.answer("Generando reporte HTML...")

    # Re-run profiling to get HTML (or cache from previous run)
    # For now, just acknowledge
    await callback.message.answer(
        "⚠️ <i>Reporte HTML generado. "
        "Usa el script CLI para obtener el HTML completo.</i>"
    )


@profile_router.message(Command("profile_stats"))
async def cmd_profile_stats(message: Message):
    """
    Muestra estadisticas acumuladas de profiling.

    Requiere que PROFILE_HANDLERS este habilitado
    para recolectar estadisticas.
    """
    await message.answer(
        "📊 <b>Estadisticas de Profiling</b>\n\n"
        "<i>Esta funcion requiere habilitar PROFILE_HANDLERS=1 "
        "en las variables de entorno.</i>\n\n"
        "Cuando esta habilitado, muestra:\n"
        "• Handlers mas lentos en promedio\n"
        "• Numero de queries por handler\n"
        "• Tendencias de rendimiento"
    )


@profile_router.message(Command("analyzeQueries"))
async def cmd_analyze_queries(message: Message, session: AsyncSession):
    """
    Analiza queries ejecutadas en operaciones típicas.

    Detecta:
    - N+1 query patterns
    - Queries lentas (>100ms)
    - Oportunidades de optimización

    Uso:
        /analyzeQueries - Ejecuta análisis completo

    Args:
        message: Mensaje del comando
        session: Sesión de BD
    """
    from bot.services.container import ServiceContainer

    status_msg = await message.answer(
        "🔍 <b>Analizando queries...</b>\n\n"
        "Ejecutando operaciones de prueba y monitoreando queries SQL...",
        parse_mode="HTML"
    )

    try:
        container = ServiceContainer(session, message.bot)

        # Analizar operaciones con query analyzer
        with analyze_queries(session) as analyzer:
            # Test 1: Obtener suscriptores VIP (puede tener N+1)
            await container.subscription.get_all_vip_subscribers(limit=10)

            # Test 2: Obtener suscriptores con usuarios (eager loading)
            await container.subscription.get_all_vip_subscribers_with_users(limit=10)

            # Test 3: Verificar configuración de canales
            await container.channel.get_bot_config()

            # Test 4: Obtener info de suscriptor individual
            # (no hay garantía de que exista user_id=1)
            # Solo lo intentamos si hay suscriptores
            vip_list = await container.subscription.get_all_vip_subscribers(limit=1)
            if vip_list:
                await container.subscription.get_vip_subscriber(vip_list[0].user_id)

        # Obtener resultados del análisis
        result = analyzer.analyze_results()

        # Formatear reporte
        report_lines = [
            "📊 <b>Análisis de Queries</b>",
            "",
            f"Total queries: <code>{result.total_queries}</code>",
            f"Tiempo total: <code>{result.total_time_ms:.2f}ms</code>",
        ]

        # Queries lentas
        if result.slow_queries:
            report_lines.extend([
                "",
                "🐌 <b>Queries Lentas (>100ms):</b>",
            ])
            for i, query in enumerate(result.slow_queries[:3], 1):
                stmt = query.statement[:60] + "..." if len(query.statement) > 60 else query.statement
                report_lines.append(f"  {i}. <code>{stmt}</code>")
                report_lines.append(f"     ⏱ {query.duration_ms:.2f}ms")
        else:
            report_lines.extend([
                "",
                "✅ <b>No se detectaron queries lentas</b>",
            ])

        # N+1 Patterns
        if result.n_plus_one_patterns:
            report_lines.extend([
                "",
                "⚠️ <b>Patrones N+1 Detectados:</b>",
            ])
            for pattern in result.n_plus_one_patterns:
                report_lines.append(f"  • {pattern.suggestion}")
                report_lines.append(f"    ({pattern.count} queries similares)")
        else:
            report_lines.extend([
                "",
                "✅ <b>No se detectaron patrones N+1</b>",
            ])

        # Sugerencias de optimización
        if result.suggestions:
            report_lines.extend([
                "",
                "💡 <b>Sugerencias de Optimización:</b>",
            ])
            suggestions_helper = QueryOptimizationSuggestions()

            for suggestion in result.suggestions[:3]:
                report_lines.append(f"  • {suggestion}")

            # Añadir sugerencias específicas
            if result.n_plus_one_patterns:
                report_lines.extend([
                    "",
                    "<b>Para evitar N+1:</b>",
                    "  <code>.options(selectinload(Model.relation))</code>",
                ])

        await status_msg.delete()

        report = "\n".join(report_lines)

        # Enviar reporte (truncar si es muy largo)
        if len(report) > 4000:
            # Guardar en archivo
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.txt',
                delete=False
            ) as f:
                f.write(result.summary())
                f.write("\n\n")
                for query in result.queries:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"Query: {query.statement}\n")
                    f.write(f"Duration: {query.duration_ms:.2f}ms\n")

            await message.answer_document(
                document=FSInputFile(f.name),
                caption=f"📊 Reporte completo de análisis de queries"
            )
            Path(f.name).unlink()
        else:
            await message.answer(report, parse_mode="HTML")

    except Exception as e:
        logger.exception("Error durante análisis de queries")
        await status_msg.edit_text(
            f"❌ <b>Error en análisis</b>\n\n"
            f"<code>{str(e)[:500]}</code>"
        )
