"""
Test Report Utility Module

Utilidades para generar reportes de tests con historial,
tendencias y formateo para diferentes salidas (Telegram,
consola, JSON, HTML).
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bot.services.test_runner import TestResult, FailedTestInfo

logger = logging.getLogger(__name__)


@dataclass
class TestRunRecord:
    """Registro de una ejecucion de tests para historial."""
    timestamp: str
    total: int
    passed: int
    failed: int
    errors: int
    skipped: int
    duration_seconds: float
    coverage_percent: Optional[float]
    success: bool
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    # No incluimos stdout/stderr ni failed_tests completos para mantenerlo ligero
    failed_count: int = 0
    warnings_count: int = 0

    @classmethod
    def from_test_result(cls, result: TestResult) -> "TestRunRecord":
        """Crea un registro desde un TestResult."""
        return cls(
            timestamp=result.timestamp or datetime.utcnow().isoformat(),
            total=result.total,
            passed=result.passed,
            failed=result.failed,
            errors=result.errors,
            skipped=result.skipped,
            duration_seconds=result.duration_seconds,
            coverage_percent=result.coverage_percent,
            success=result.success,
            git_commit=result.git_commit,
            git_branch=result.git_branch,
            failed_count=len(result.failed_tests) if result.failed_tests else 0,
            warnings_count=len(result.warnings) if result.warnings else 0
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serializacion JSON."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestRunRecord":
        """Crea un registro desde un diccionario."""
        return cls(**data)


class TestReportHistory:
    """
    Gestiona el historial de ejecuciones de tests.

    Persiste registros en JSON de forma asincrona para no bloquear
    el bot durante operaciones de I/O.
    """

    DEFAULT_HISTORY_FILE = ".test_history.json"
    MAX_HISTORY_ENTRIES = 100

    def __init__(self, history_file: Optional[Path] = None, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.history_file = history_file or (self.project_root / self.DEFAULT_HISTORY_FILE)
        self._cache: Optional[List[TestRunRecord]] = None
        self._lock = asyncio.Lock()

    async def add_record(self, result: TestResult) -> None:
        """
        Agrega un nuevo registro al historial.

        Args:
            result: Resultado de tests a registrar
        """
        record = TestRunRecord.from_test_result(result)

        async with self._lock:
            history = await self._load_history_async()
            history.append(record)

            # Mantener solo las ultimas N entradas
            if len(history) > self.MAX_HISTORY_ENTRIES:
                history = history[-self.MAX_HISTORY_ENTRIES:]

            await self._save_history_async(history)
            self._cache = history

        logger.debug(f"Registro de test agregado al historial: {record.timestamp}")

    async def get_history(self, limit: int = 10) -> List[TestRunRecord]:
        """
        Obtiene los ultimos registros del historial.

        Args:
            limit: Numero maximo de registros a retornar

        Returns:
            Lista de registros ordenados por fecha (mas reciente primero)
        """
        async with self._lock:
            history = await self._load_history_async()
            return list(reversed(history[-limit:]))

    async def get_trend_comparison(self, result: TestResult) -> Dict[str, Any]:
        """
        Compara un resultado con el historial anterior.

        Args:
            result: Resultado actual a comparar

        Returns:
            Diccionario con diferencias y tendencias
        """
        history = await self.get_history(limit=5)

        if not history or len(history) < 2:
            return {
                "has_previous": False,
                "duration_delta": 0.0,
                "duration_delta_percent": 0.0,
                "coverage_delta": 0.0,
                "failed_delta": 0,
                "trend_direction": "unknown"
            }

        # Comparar con el registro anterior (excluyendo el actual si ya esta en historial)
        previous = history[1] if history[0].timestamp == result.timestamp else history[0]

        duration_delta = result.duration_seconds - previous.duration_seconds
        duration_delta_percent = (
            (duration_delta / previous.duration_seconds * 100)
            if previous.duration_seconds > 0 else 0.0
        )

        coverage_delta = 0.0
        if result.coverage_percent is not None and previous.coverage_percent is not None:
            coverage_delta = result.coverage_percent - previous.coverage_percent

        failed_delta = result.failed - previous.failed

        # Determinar tendencia general
        trend_direction = "stable"
        if result.success and not previous.success:
            trend_direction = "improved"
        elif not result.success and previous.success:
            trend_direction = "degraded"
        elif coverage_delta > 1:
            trend_direction = "improved"
        elif coverage_delta < -1:
            trend_direction = "degraded"

        return {
            "has_previous": True,
            "previous_timestamp": previous.timestamp,
            "duration_delta": round(duration_delta, 2),
            "duration_delta_percent": round(duration_delta_percent, 1),
            "coverage_delta": round(coverage_delta, 1),
            "failed_delta": failed_delta,
            "trend_direction": trend_direction
        }

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Calcula estadisticas del historial.

        Returns:
            Diccionario con estadisticas agregadas
        """
        history = await self._load_history_async()

        if not history:
            return {"has_data": False}

        total_runs = len(history)
        successful_runs = sum(1 for r in history if r.success)
        failed_runs = total_runs - successful_runs

        avg_duration = sum(r.duration_seconds for r in history) / total_runs

        coverage_values = [r.coverage_percent for r in history if r.coverage_percent is not None]
        avg_coverage = sum(coverage_values) / len(coverage_values) if coverage_values else None

        return {
            "has_data": True,
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "success_rate": round(successful_runs / total_runs * 100, 1),
            "avg_duration": round(avg_duration, 2),
            "avg_coverage": round(avg_coverage, 1) if avg_coverage else None,
            "last_run": history[-1].timestamp if history else None
        }

    async def clear_history(self) -> None:
        """Limpia todo el historial."""
        async with self._lock:
            await self._save_history_async([])
            self._cache = []
        logger.info("Historial de tests limpiado")

    async def _load_history_async(self) -> List[TestRunRecord]:
        """Carga historial desde archivo (async)."""
        if self._cache is not None:
            return self._cache

        try:
            if not self.history_file.exists():
                return []

            # Usar run_in_executor para no bloquear
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, self._read_file_sync)
            data = json.loads(content)

            records = [TestRunRecord.from_dict(r) for r in data]
            self._cache = records
            return records

        except Exception as e:
            logger.warning(f"Error cargando historial de tests: {e}")
            return []

    def _read_file_sync(self) -> str:
        """Lee archivo de forma sincrona (para ejecutar en executor)."""
        return self.history_file.read_text(encoding="utf-8")

    async def _save_history_async(self, history: List[TestRunRecord]) -> None:
        """Guarda historial a archivo (async)."""
        try:
            data = [r.to_dict() for r in history]

            # Usar run_in_executor para no bloquear
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._write_file_sync,
                json.dumps(data, indent=2, default=str)
            )

        except Exception as e:
            logger.error(f"Error guardando historial de tests: {e}")

    def _write_file_sync(self, content: str) -> None:
        """Escribe archivo de forma sincrona (para ejecutar en executor)."""
        self.history_file.write_text(content, encoding="utf-8")


class TestReportFormatter:
    """
    Formatea reportes de tests para diferentes salidas.

    Soporta: Telegram (HTML), consola, JSON, y HTML completo.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent

    def format_telegram(
        self,
        result: TestResult,
        trend: Optional[Dict[str, Any]] = None,
        max_length: int = 4000
    ) -> str:
        """
        Formatea resultado para enviar por Telegram (HTML).

        Args:
            result: Resultado de tests
            trend: Informacion de tendencia (opcional)
            max_length: Longitud maxima del mensaje

        Returns:
            Texto formateado en HTML
        """
        lines = []

        # Header with status
        if result.success:
            lines.append("✅ <b>TODOS LOS TESTS PASARON</b>")
        else:
            lines.append("❌ <b>ALGUNOS TESTS FALLARON</b>")
        lines.append("")

        # Git info if available
        if result.git_branch:
            commit_info = f"@{result.git_commit}" if result.git_commit else ""
            lines.append(f"🌿 <b>Branch:</b> <code>{result.git_branch}{commit_info}</code>")
            lines.append("")

        # Metrics table
        lines.append("📊 <b>Metricas:</b>")
        lines.append(f"  • Total: {result.total}")
        lines.append(f"  • ✅ Pasados: {result.passed}")
        lines.append(f"  • ❌ Fallidos: {result.failed}")
        lines.append(f"  • ⚠️ Errores: {result.errors}")
        lines.append(f"  • ⏭️ Saltados: {result.skipped}")
        lines.append("")

        # Duration with trend
        duration_str = f"⏱️ <b>Duracion:</b> {result.duration_seconds:.2f}s"
        if trend and trend.get("has_previous"):
            delta = trend["duration_delta"]
            if delta > 0:
                duration_str += f" (<code>+{delta:.1f}s</code> ⬆️)"
            elif delta < 0:
                duration_str += f" (<code>{delta:.1f}s</code> ⬇️)"
        lines.append(duration_str)

        # Coverage with trend
        if result.coverage_percent is not None:
            coverage_str = f"📈 <b>Coverage:</b> {result.coverage_percent:.1f}%"
            if trend and trend.get("has_previous"):
                delta = trend["coverage_delta"]
                if delta > 0:
                    coverage_str += f" (<code>+{delta:.1f}%</code> 🟢)"
                elif delta < 0:
                    coverage_str += f" (<code>{delta:.1f}%</code> 🔴)")
            lines.append(coverage_str)

        # Trend indicator
        if trend:
            direction = trend.get("trend_direction", "unknown")
            if direction == "improved":
                lines.append("📊 <b>Tendencia:</b> 🟢 Mejorando")
            elif direction == "degraded":
                lines.append("📊 <b>Tendencia:</b> 🔴 Degradando")
            elif direction == "stable":
                lines.append("📊 <b>Tendencia:</b> ⚪ Estable")

        # Failed tests details (if any)
        if result.failed_tests:
            lines.append("")
            lines.append("📝 <b>Tests fallidos:</b>")

            for i, test in enumerate(result.failed_tests[:5]):
                # Sanitize file path (remove project root)
                file_display = self._sanitize_path(test.file_path)
                line_info = f":{test.line_number}" if test.line_number else ""

                # Escape HTML special characters
                file_escaped = file_display.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                name_escaped = test.name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

                lines.append(f"  ❌ <code>{file_escaped}{line_info}::{name_escaped}</code>")

                # Show error type if available
                if test.error_type:
                    lines.append(f"     <i>{test.error_type}</i>")

            if len(result.failed_tests) > 5:
                lines.append(f"  ... y {len(result.failed_tests) - 5} mas")

        # Warnings
        if result.warnings:
            lines.append("")
            lines.append(f"⚠️ <b>Advertencias:</b> {len(result.warnings)}")

        report = "\n".join(lines)

        # Truncate if exceeds max_length
        if len(report) > max_length:
            truncated = report[:max_length - 100]
            truncated += "\n\n<i>(Mensaje truncado por limite de longitud)</i>"
            return truncated

        return report

    def format_console(self, result: TestResult, trend: Optional[Dict[str, Any]] = None) -> str:
        """
        Formatea resultado para mostrar en consola.

        Args:
            result: Resultado de tests
            trend: Informacion de tendencia (opcional)

        Returns:
            Texto formateado para consola
        """
        lines = []

        # Header
        if result.success:
            lines.append("=" * 50)
            lines.append("✅ TODOS LOS TESTS PASARON")
            lines.append("=" * 50)
        else:
            lines.append("=" * 50)
            lines.append("❌ ALGUNOS TESTS FALLARON")
            lines.append("=" * 50)

        # Git info
        if result.git_branch:
            commit_info = f"@{result.git_commit}" if result.git_commit else ""
            lines.append(f"Branch: {result.git_branch}{commit_info}")

        lines.append("")
        lines.append("Metricas:")
        lines.append(f"  Total:      {result.total}")
        lines.append(f"  Pasados:    {result.passed}")
        lines.append(f"  Fallidos:   {result.failed}")
        lines.append(f"  Errores:    {result.errors}")
        lines.append(f"  Saltados:   {result.skipped}")
        lines.append("")
        lines.append(f"Duracion: {result.duration_seconds:.2f}s")

        if result.coverage_percent is not None:
            lines.append(f"Coverage: {result.coverage_percent:.1f}%")

        if trend and trend.get("has_previous"):
            lines.append("")
            lines.append("Tendencia vs ejecucion anterior:")
            lines.append(f"  Duracion: {trend['duration_delta']:+.1f}s ({trend['duration_delta_percent']:+.1f}%)")
            if trend.get("coverage_delta"):
                lines.append(f"  Coverage: {trend['coverage_delta']:+.1f}%")

        # Failed tests
        if result.failed_tests:
            lines.append("")
            lines.append("Tests fallidos:")
            for test in result.failed_tests[:10]:
                file_display = self._sanitize_path(test.file_path)
                line_info = f":{test.line_number}" if test.line_number else ""
                lines.append(f"  ❌ {file_display}{line_info}::{test.name}")
                if test.error_type:
                    lines.append(f"     {test.error_type}")

        return "\n".join(lines)

    def format_json(self, result: TestResult, trend: Optional[Dict[str, Any]] = None) -> str:
        """
        Formatea resultado como JSON.

        Args:
            result: Resultado de tests
            trend: Informacion de tendencia (opcional)

        Returns:
            String JSON formateado
        """
        data = {
            "timestamp": result.timestamp,
            "success": result.success,
            "metrics": {
                "total": result.total,
                "passed": result.passed,
                "failed": result.failed,
                "errors": result.errors,
                "skipped": result.skipped,
                "duration_seconds": result.duration_seconds,
                "coverage_percent": result.coverage_percent
            },
            "git": {
                "commit": result.git_commit,
                "branch": result.git_branch
            },
            "failed_tests": [
                {
                    "name": t.name,
                    "file": t.file_path,
                    "line": t.line_number,
                    "error_type": t.error_type,
                    "error_message": t.error_message
                }
                for t in (result.failed_tests or [])
            ],
            "coverage_by_module": result.coverage_by_module,
            "trend": trend
        }

        return json.dumps(data, indent=2, default=str)

    def generate_html_report(
        self,
        result: TestResult,
        output_path: Optional[Path] = None,
        trend: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Genera un reporte HTML completo.

        Args:
            result: Resultado de tests
            output_path: Ruta de salida (opcional)
            trend: Informacion de tendencia (opcional)

        Returns:
            Ruta al archivo HTML generado
        """
        if output_path is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_path = self.project_root / f"test_report_{timestamp}.html"

        # Color based on success
        status_color = "#28a745" if result.success else "#dc3545"
        status_text = "PASSED" if result.success else "FAILED"

        # Coverage color
        coverage_color = "#28a745"
        if result.coverage_percent is not None:
            if result.coverage_percent < 50:
                coverage_color = "#dc3545"
            elif result.coverage_percent < 80:
                coverage_color = "#ffc107"

        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Report - {result.timestamp or datetime.utcnow().isoformat()}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: {status_color};
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header .timestamp {{ opacity: 0.9; }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .metric {{
            text-align: center;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .metric .value {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        .metric .label {{ color: #666; font-size: 0.9em; margin-top: 5px; }}
        .coverage {{
            padding: 30px;
            border-bottom: 1px solid #eee;
        }}
        .coverage-bar {{
            height: 30px;
            background: #e9ecef;
            border-radius: 15px;
            overflow: hidden;
            margin-top: 10px;
        }}
        .coverage-fill {{
            height: 100%;
            background: {coverage_color};
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            transition: width 0.3s ease;
        }}
        .failed-tests {{
            padding: 30px;
        }}
        .failed-tests h2 {{ margin-bottom: 20px; color: #333; }}
        .test-item {{
            background: #f8f9fa;
            border-left: 4px solid #dc3545;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 4px;
        }}
        .test-item .name {{
            font-family: monospace;
            font-size: 0.95em;
            color: #333;
        }}
        .test-item .location {{
            color: #666;
            font-size: 0.85em;
            margin-top: 5px;
        }}
        .test-item .error {{
            color: #dc3545;
            font-size: 0.9em;
            margin-top: 10px;
            padding: 10px;
            background: #fff;
            border-radius: 4px;
            font-family: monospace;
            white-space: pre-wrap;
        }}
        .git-info {{
            padding: 20px 30px;
            background: #e9ecef;
            font-family: monospace;
            font-size: 0.9em;
        }}
        .footer {{
            padding: 20px 30px;
            text-align: center;
            color: #666;
            font-size: 0.85em;
            border-top: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{status_text}</h1>
            <div class="timestamp">{result.timestamp or datetime.utcnow().isoformat()}</div>
        </div>

        <div class="metrics">
            <div class="metric">
                <div class="value">{result.total}</div>
                <div class="label">Total</div>
            </div>
            <div class="metric">
                <div class="value" style="color: #28a745;">{result.passed}</div>
                <div class="label">Passed</div>
            </div>
            <div class="metric">
                <div class="value" style="color: #dc3545;">{result.failed}</div>
                <div class="label">Failed</div>
            </div>
            <div class="metric">
                <div class="value" style="color: #ffc107;">{result.errors}</div>
                <div class="label">Errors</div>
            </div>
            <div class="metric">
                <div class="value" style="color: #6c757d;">{result.skipped}</div>
                <div class="label">Skipped</div>
            </div>
            <div class="metric">
                <div class="value">{result.duration_seconds:.2f}s</div>
                <div class="label">Duration</div>
            </div>
        </div>
"""

        # Add coverage section if available
        if result.coverage_percent is not None:
            html_content += f"""
        <div class="coverage">
            <h2>Coverage</h2>
            <div class="coverage-bar">
                <div class="coverage-fill" style="width: {result.coverage_percent}%;">
                    {result.coverage_percent:.1f}%
                </div>
            </div>
        </div>
"""

        # Add failed tests section
        if result.failed_tests:
            html_content += """
        <div class="failed-tests">
            <h2>Failed Tests</h2>
"""
            for test in result.failed_tests:
                file_display = self._sanitize_path(test.file_path)
                line_info = f":{test.line_number}" if test.line_number else ""
                html_content += f"""
            <div class="test-item">
                <div class="name">{test.name}</div>
                <div class="location">{file_display}{line_info}</div>
                {f'<div class="error">{test.error_type}: {test.error_message or ""}</div>' if test.error_type else ""}
            </div>
"""
            html_content += """
        </div>
"""

        # Add git info
        if result.git_branch:
            commit_info = f"@{result.git_commit}" if result.git_commit else ""
            html_content += f"""
        <div class="git-info">
            <strong>Git:</strong> {result.git_branch}{commit_info}
        </div>
"""

        html_content += f"""
        <div class="footer">
            Generated by Telegram Bot Test Runner
        </div>
    </div>
</body>
</html>
"""

        output_path.write_text(html_content, encoding="utf-8")
        logger.info(f"Reporte HTML generado: {output_path}")
        return output_path

    def _sanitize_path(self, file_path: str) -> str:
        """
        Sanitiza una ruta de archivo removiendo el project root.

        Args:
            file_path: Ruta original

        Returns:
            Ruta relativa o nombre de archivo
        """
        try:
            path = Path(file_path)
            # Intentar hacerla relativa al project root
            try:
                relative = path.relative_to(self.project_root)
                return str(relative)
            except ValueError:
                # Ya es relativa o esta fuera del project
                return file_path
        except Exception:
            return file_path
