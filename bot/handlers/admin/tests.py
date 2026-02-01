"""
Admin Test Runner Handler

Handler para ejecutar tests desde Telegram via comando /run_tests.
Solo accesible para administradores.
"""

import logging
from pathlib import Path

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile
)
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.test_runner import TestRunnerService
from bot.utils.test_report import TestReportFormatter, TestReportHistory
from bot.middlewares import AdminAuthMiddleware

logger = logging.getLogger(__name__)

# Router para handlers de tests
tests_router = Router(name="admin_tests")

# Aplicar middleware de admin
tests_router.message.middleware(AdminAuthMiddleware())
tests_router.callback_query.middleware(AdminAuthMiddleware())


# Cache para ultimo resultado de tests (para ver detalles)
_last_test_result = None


@tests_router.message(Command("run_tests"))
async def cmd_run_tests(message: Message, session: AsyncSession):
    """
    Ejecuta tests y envia reporte al admin con tendencias y coverage.

    Uso:
        /run_tests - Ejecuta todos los tests
        /run_tests smoke - Ejecuta solo smoke tests
        /run_tests system - Ejecuta tests de sistema
        /run_tests coverage - Ejecuta con reporte de coverage
        /run_tests html - Genera reporte HTML
        /run_tests trend - Muestra tendencias historicas

    Args:
        message: Mensaje del comando
        session: Sesion de BD inyectada
    """
    logger.info(f"🧪 Admin {message.from_user.id} solicito ejecucion de tests")

    # Parse arguments
    args = message.text.split()[1:] if message.text else []
    coverage = "coverage" in args
    generate_html = "html" in args
    show_trend = "trend" in args
    marker = None
    test_paths = None

    if "smoke" in args:
        marker = "smoke"
    elif "system" in args:
        test_paths = ["tests/test_system/"]

    # Manejar comando trend por separado
    if show_trend:
        await _show_test_trends(message, session)
        return

    # Send "running" message
    status_msg = await message.answer(
        "🧪 <b>Ejecutando tests...</b>\n\n"
        "Esto puede tomar unos minutos."
    )

    try:
        # Create service and run tests with enhanced reporting
        runner = TestRunnerService(session)
        result, report_meta = await runner.run_tests_with_report(
            test_paths=test_paths,
            coverage=coverage,
            marker=marker,
            save_history=True,
            generate_html=generate_html
        )

        # Guardar resultado en cache para ver detalles despues
        global _last_test_result
        _last_test_result = result

        # Format report con tendencias
        formatter = TestReportFormatter()
        report = formatter.format_telegram_report(
            result,
            trend=report_meta.get("trend")
        )

        # Delete status message
        await status_msg.delete()

        # Enviar reporte (dividido si es necesario)
        await _send_report_in_parts(message, report)

        # Enviar HTML si se genero
        if generate_html and report_meta.get("html_path"):
            html_path = report_meta["html_path"]
            if html_path.exists():
                await message.answer_document(
                    FSInputFile(str(html_path)),
                    caption="📄 <b>Reporte HTML completo</b>",
                    parse_mode="HTML"
                )

        # Si hay fallos, ofrecer ver detalles
        if result.failed > 0 or result.errors > 0:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="📋 Ver detalles de fallos",
                    callback_data="tests:show_failures"
                )]
            ])
            await message.answer(
                "❌ Algunos tests fallaron. ¿Deseas ver los detalles?",
                reply_markup=keyboard
            )

    except Exception as e:
        logger.exception("Error ejecutando tests")
        await status_msg.edit_text(
            f"❌ <b>Error ejecutando tests</b>\n\n"
            f"<code>{str(e)}</code>"
        )


async def _send_report_in_parts(message: Message, report: str, max_length: int = 4000):
    """
    Envia un reporte largo dividido en multiples mensajes.

    Args:
        message: Mensaje original para responder
        report: Texto del reporte
        max_length: Longitud maxima por mensaje
    """
    if len(report) <= max_length:
        await message.answer(report, parse_mode="HTML")
        return

    # Dividir en partes manteniendo lineas completas
    parts = []
    current_part = ""

    for line in report.split("\n"):
        if len(current_part) + len(line) + 1 > max_length:
            parts.append(current_part)
            current_part = line
        else:
            current_part += "\n" + line if current_part else line

    if current_part:
        parts.append(current_part)

    # Enviar cada parte
    for i, part in enumerate(parts):
        header = f"📊 <b>Reporte de Tests (parte {i+1}/{len(parts)})</b>\n\n"
        await message.answer(header + part, parse_mode="HTML")


async def _show_test_trends(message: Message, session: AsyncSession):
    """
    Muestra tendencias historicas de tests.

    Args:
        message: Mensaje del comando
        session: Sesion de BD inyectada
    """
    logger.info(f"📈 Admin {message.from_user.id} solicito tendencias de tests")

    try:
        runner = TestRunnerService(session)
        stats = await runner.get_test_statistics()

        if not stats.get("has_data"):
            await message.answer(
                "📊 <b>Tendencias de Tests</b>\n\n"
                "ℹ️ No hay datos historicos disponibles.\n"
                "Ejecuta <code>/run_tests</code> primero para generar historial.",
                parse_mode="HTML"
            )
            return

        lines = []
        lines.append("📊 <b>Tendencias de Tests</b>")
        lines.append("")
        lines.append(f"📈 <b>Total de ejecuciones:</b> {stats['total_runs']}")
        lines.append(f"✅ <b>Exitosas:</b> {stats['successful_runs']}")
        lines.append(f"❌ <b>Fallidas:</b> {stats['failed_runs']}")
        lines.append(f"📊 <b>Tasa de exito:</b> {stats['success_rate']}%")
        lines.append("")
        lines.append(f"⏱️ <b>Duracion promedio:</b> {stats['avg_duration']}s")

        if stats.get("avg_coverage"):
            lines.append(f"📈 <b>Coverage promedio:</b> {stats['avg_coverage']}%")

        lines.append("")
        lines.append(f"🕐 <b>Ultima ejecucion:</b> {stats['last_run']}")

        await message.answer("\n".join(lines), parse_mode="HTML")

    except Exception as e:
        logger.exception("Error obteniendo tendencias")
        await message.answer(
            f"❌ <b>Error</b>\n\n"
            f"No se pudieron obtener las tendencias: <code>{str(e)}</code>",
            parse_mode="HTML"
        )


@tests_router.callback_query(F.data == "tests:show_failures")
async def callback_show_failures(callback: CallbackQuery, session: AsyncSession):
    """Muestra detalles de tests fallidos."""
    await callback.answer("Obteniendo detalles...")

    global _last_test_result

    if _last_test_result is None:
        await callback.message.answer(
            "ℹ️ <b>Informacion</b>\n\n"
            "Los detalles de fallos no estan disponibles.\n"
            "Por favor, ejecuta <code>/run_tests</code> nuevamente para ver los detalles."
        )
        return

    # Mostrar detalles formateados
    formatter = TestReportFormatter()
    details = formatter.format_telegram_report(
        _last_test_result,
        max_length=3500  # Dejar margen para el header
    )

    # Enviar detalles divididos si es necesario
    if len(details) > 4000:
        parts = []
        current = ""
        for line in details.split("\n"):
            if len(current) + len(line) + 1 > 4000:
                parts.append(current)
                current = line
            else:
                current += "\n" + line if current else line
        if current:
            parts.append(current)

        for i, part in enumerate(parts):
            header = f"📋 <b>Detalles de Fallos (parte {i+1}/{len(parts)})</b>\n\n"
            await callback.message.answer(header + part, parse_mode="HTML")
    else:
        await callback.message.answer(
            f"📋 <b>Detalles de Fallos</b>\n\n{details}",
            parse_mode="HTML"
        )


@tests_router.message(Command("test_status"))
async def cmd_test_status(message: Message, session: AsyncSession):
    """
    Muestra estado del sistema de tests.

    Indica si el entorno de tests esta configurado correctamente
    y cuantos tests hay disponibles.
    """
    import subprocess
    from pathlib import Path

    logger.info(f"📊 Admin {message.from_user.id} solicito estado de tests")

    try:
        project_root = Path(__file__).parent.parent.parent.parent

        # Check pytest availability
        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=30
        )

        # Count tests
        test_count = 0
        if result.returncode == 0:
            # Count lines that look like test files
            for line in result.stdout.split("\n"):
                if "::" in line and not line.startswith("="):
                    test_count += 1

        lines = []
        lines.append("📊 <b>Estado del Sistema de Tests</b>")
        lines.append("")

        if result.returncode == 0:
            lines.append("✅ <b>pytest:</b> Disponible")
            lines.append(f"🧪 <b>Tests disponibles:</b> ~{test_count}")
        else:
            lines.append("❌ <b>pytest:</b> No disponible")
            lines.append(f"<code>{result.stderr[:200]}</code>")

        lines.append("")
        lines.append("<b>Comandos disponibles:</b>")
        lines.append("• <code>/run_tests</code> - Ejecutar todos")
        lines.append("• <code>/run_tests smoke</code> - Solo smoke tests")
        lines.append("• <code>/run_tests system</code> - Tests de sistema")
        lines.append("• <code>/run_tests coverage</code> - Con coverage")
        lines.append("• <code>/run_tests html</code> - Generar reporte HTML")
        lines.append("• <code>/run_tests trend</code> - Ver tendencias")
        lines.append("• <code>/smoke_test</code> - Verificacion rapida")

        await message.answer("\n".join(lines), parse_mode="HTML")

    except Exception as e:
        logger.exception("Error obteniendo estado de tests")
        await message.answer(
            f"❌ <b>Error</b>\n\n"
            f"No se pudo obtener el estado: <code>{str(e)}</code>",
            parse_mode="HTML"
        )


@tests_router.message(Command("smoke_test"))
async def cmd_smoke_test(message: Message, session: AsyncSession):
    """
    Ejecuta smoke tests rapidos (alias para /run_tests smoke).

    Verificacion rapida de que el sistema funciona correctamente.
    """
    logger.info(f"🚀 Admin {message.from_user.id} solicito smoke test")

    status_msg = await message.answer(
        "🚀 <b>Ejecutando smoke tests...</b>\n\n"
        "Verificacion rapida del sistema."
    )

    try:
        runner = TestRunnerService(session)
        result, report_meta = await runner.run_tests_with_report(
            marker="smoke",
            timeout=60,
            save_history=True
        )

        # Guardar resultado en cache
        global _last_test_result
        _last_test_result = result

        # Formatear con tendencias
        formatter = TestReportFormatter()
        report = formatter.format_telegram_report(
            result,
            trend=report_meta.get("trend")
        )

        await status_msg.delete()
        await message.answer(report, parse_mode="HTML")

        # Si hay fallos, ofrecer ver detalles
        if result.failed > 0 or result.errors > 0:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="📋 Ver detalles de fallos",
                    callback_data="tests:show_failures"
                )]
            ])
            await message.answer(
                "❌ Algunos tests fallaron. ¿Deseas ver los detalles?",
                reply_markup=keyboard
            )

    except Exception as e:
        logger.exception("Error en smoke test")
        await status_msg.edit_text(
            f"❌ <b>Error en smoke test</b>\n\n"
            f"<code>{str(e)}</code>"
        )
