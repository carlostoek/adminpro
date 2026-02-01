"""
Test Runner Service

Servicio para ejecutar tests desde el bot, con soporte para
reportes formateados y notificaciones a administradores.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class FailedTestInfo:
    """Informacion de un test fallido."""
    name: str
    file_path: str
    line_number: Optional[int] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None

    def __str__(self) -> str:
        if self.line_number:
            return f"{self.file_path}:{self.line_number}::{self.name}"
        return f"{self.file_path}::{self.name}"


@dataclass
class TestResult:
    """Resultado de una ejecucion de tests."""
    returncode: int
    passed: int
    failed: int
    errors: int
    skipped: int
    total: int
    duration_seconds: float
    stdout: str
    stderr: str
    coverage_percent: Optional[float] = None
    coverage_by_module: Optional[dict] = None
    failed_tests: Optional[List[FailedTestInfo]] = None
    warnings: Optional[List[str]] = None
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        """Inicializa valores por defecto."""
        if self.coverage_by_module is None:
            self.coverage_by_module = {}
        if self.failed_tests is None:
            self.failed_tests = []
        if self.warnings is None:
            self.warnings = []

    @property
    def success(self) -> bool:
        """True si todos los tests pasaron."""
        return self.returncode == 0 and self.failed == 0 and self.errors == 0

    @property
    def summary(self) -> str:
        """Resumen en una linea."""
        return (
            f"Tests: {self.total} total, "
            f"{self.passed} passed, "
            f"{self.failed} failed, "
            f"{self.errors} errors, "
            f"{self.skipped} skipped"
        )


class TestRunnerService:
    """
    Servicio para ejecutar tests pytest desde el bot.

    Ejecuta tests en subprocess aislado para evitar que
    errores afecten el proceso principal del bot.
    """

    def __init__(self, session: AsyncSession, project_root: Optional[Path] = None):
        self.session = session
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self._lock = asyncio.Lock()

    async def run_tests(
        self,
        test_paths: Optional[List[str]] = None,
        coverage: bool = False,
        marker: Optional[str] = None,
        timeout: int = 300
    ) -> TestResult:
        """
        Ejecuta tests y retorna resultado estructurado.

        Args:
            test_paths: Paths especificos a testear (None = todos)
            coverage: Si True, incluye coverage
            marker: Marker de pytest para filtrar tests
            timeout: Timeout en segundos para la ejecucion

        Returns:
            TestResult con metricas y output
        """
        async with self._lock:
            # Build command
            cmd = ["python", "-m", "pytest"]

            if coverage:
                cmd.extend(["--cov=bot", "--cov-report=term"])

            if marker:
                cmd.extend(["-m", marker])

            cmd.extend(test_paths or ["tests/"])
            cmd.extend(["-v", "--tb=short"])

            # Execute in subprocess
            logger.info(f"Ejecutando tests: {' '.join(cmd)}")

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.project_root
                )

                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )

                stdout_str = stdout.decode("utf-8", errors="replace")
                stderr_str = stderr.decode("utf-8", errors="replace")

                # Parse results
                result = self._parse_results(
                    proc.returncode or 0,
                    stdout_str,
                    stderr_str
                )

                if result.total == 0:
                    logger.warning(f"No se detectaron tests en el output. Return code: {returncode}")
                    logger.debug(f"Output completo:\n{stdout_str[:3000]}")
                logger.info(f"Tests completados: {result.summary}")
                return result

            except asyncio.TimeoutError:
                logger.error(f"Tests timeout despues de {timeout}s")
                proc.kill()
                return TestResult(
                    returncode=-1,
                    passed=0, failed=0, errors=1, skipped=0, total=0,
                    duration_seconds=timeout,
                    stdout="",
                    stderr=f"Timeout despues de {timeout} segundos"
                )

    def _parse_results(
        self,
        returncode: int,
        stdout: str,
        stderr: str
    ) -> TestResult:
        """Parsea output de pytest para extraer metricas."""
        output = stdout + "\n" + stderr

        # Debug: log output para ver que formato produce pytest
        logger.debug(f"Pytest stdout:\n{stdout[:2000]}")
        logger.debug(f"Pytest stderr:\n{stderr[:500]}")

        # Initialize defaults
        passed = failed = errors = skipped = 0
        duration = 0.0
        coverage_percent = None
        coverage_by_module: Dict[str, float] = {}
        failed_tests: List[FailedTestInfo] = []
        warnings: List[str] = []

        # Parse summary line - multiples formatos soportados:
        # "50 passed, 2 failed, 1 error in 12.34s"
        # "50 passed, 2 failed, 1 error, 3 skipped in 12.34s"
        # "50 passed in 0.12s" (solo passed)
        # "12.34s" puede ser "12.34 seconds" en algunos locales
        summary_patterns = [
            # Formato completo con todo
            r"(\d+) passed(?:,\s*(\d+) failed)?(?:,\s*(\d+) error)?(?:,\s*(\d+) skipped)?\s+in\s+([\d.]+)",
            # Formato con todo en plural
            r"(\d+) passed(?:,\s*(\d+) failed)?(?:,\s*(\d+) errors)?(?:,\s*(\d+) skipped)?\s+in\s+([\d.]+)",
            # Formato con warnings al final
            r"(\d+) passed(?:,\s*(\d+) failed)?(?:,\s*(\d+) error)?(?:,\s*(\d+) skipped)?(?:,\s*\d+ warnings?)?\s+in\s+([\d.]+)",
        ]

        match = None
        for pattern in summary_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                logger.debug(f"Matched pattern: {pattern}")
                break

        if match:
            passed = int(match.group(1)) if match.group(1) else 0
            failed = int(match.group(2)) if match.group(2) else 0
            errors = int(match.group(3)) if match.group(3) else 0
            skipped = int(match.group(4)) if match.group(4) else 0
            duration = float(match.group(5)) if match.group(5) else 0.0
            logger.debug(f"Parsed: passed={passed}, failed={failed}, errors={errors}, skipped={skipped}, duration={duration}")
        else:
            logger.warning(f"No summary pattern matched. Output excerpt: {output[-500:]}")

        total = passed + failed + errors + skipped

        # Parse coverage percentage
        coverage_pattern = r"TOTAL\s+\d+\s+\d+\s+(\d+)%"
        coverage_match = re.search(coverage_pattern, output)
        if coverage_match:
            coverage_percent = float(coverage_match.group(1))

        # Parse coverage by module
        # Pattern: "module_name.py           45     10    78%"
        module_pattern = r"^(\S+\.py)\s+\d+\s+\d+\s+(\d+)%$"
        for line in output.split("\n"):
            mod_match = re.match(module_pattern, line)
            if mod_match:
                module_name = mod_match.group(1)
                module_coverage = float(mod_match.group(2))
                coverage_by_module[module_name] = module_coverage

        # Parse failed tests with details
        failed_tests = self._parse_failed_tests(output)

        # Parse warnings
        warning_pattern = r"(\d+ warnings?|Warning:.*)$"
        for line in output.split("\n"):
            warn_match = re.search(warning_pattern, line, re.IGNORECASE)
            if warn_match:
                warnings.append(warn_match.group(0))

        # Get git info
        git_commit, git_branch = self._get_git_info()

        return TestResult(
            returncode=returncode,
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            total=total,
            duration_seconds=duration,
            stdout=stdout,
            stderr=stderr,
            coverage_percent=coverage_percent,
            coverage_by_module=coverage_by_module,
            failed_tests=failed_tests,
            warnings=warnings,
            git_commit=git_commit,
            git_branch=git_branch,
            timestamp=datetime.utcnow().isoformat()
        )

    def _parse_failed_tests(self, output: str) -> List[FailedTestInfo]:
        """Parse failed tests with file:line information."""
        failed_tests: List[FailedTestInfo] = []

        # Pattern for FAILED/ERROR lines with file info
        # Example: "FAILED tests/test_example.py::test_name - Error message"
        failed_pattern = r"(FAILED|ERROR)\s+(\S+)::(\S+)(?:\s+-\s+(.+))?"

        for match in re.finditer(failed_pattern, output):
            status = match.group(1)
            file_path = match.group(2)
            test_name = match.group(3)
            error_msg = match.group(4) if match.group(4) else None

            # Try to extract line number from file path (format: path/to/file.py::test_name)
            line_number = None
            if ".py" in file_path:
                # Check if there's line info in the traceback
                line_pattern = rf"{re.escape(file_path)}:(\d+)"
                line_match = re.search(line_pattern, output)
                if line_match:
                    line_number = int(line_match.group(1))

            # Extract error type from error message
            error_type = None
            if error_msg:
                # Common error patterns: "AssertionError: ...", "ValueError: ..."
                type_match = re.match(r"^(\w+Error|Error|Exception):", error_msg)
                if type_match:
                    error_type = type_match.group(1)

            failed_tests.append(FailedTestInfo(
                name=test_name,
                file_path=file_path,
                line_number=line_number,
                error_message=error_msg,
                error_type=error_type
            ))

        return failed_tests

    def _get_git_info(self) -> tuple:
        """Get current git commit and branch."""
        try:
            import subprocess

            # Get commit hash
            commit_result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=5
            )
            commit = commit_result.stdout.strip() if commit_result.returncode == 0 else None

            # Get branch
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=5
            )
            branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None

            return commit, branch
        except Exception:
            return None, None

    async def run_tests_with_report(
        self,
        test_paths: Optional[List[str]] = None,
        coverage: bool = False,
        marker: Optional[str] = None,
        timeout: int = 300,
        save_history: bool = True,
        generate_html: bool = False,
        html_output_path: Optional[Path] = None
    ) -> Tuple[TestResult, Dict[str, Any]]:
        """
        Ejecuta tests con reporte completo incluyendo historial y tendencias.

        Args:
            test_paths: Paths especificos a testear (None = todos)
            coverage: Si True, incluye coverage
            marker: Marker de pytest para filtrar tests
            timeout: Timeout en segundos para la ejecucion
            save_history: Si True, guarda el resultado en historial
            generate_html: Si True, genera reporte HTML
            html_output_path: Ruta para el reporte HTML (opcional)

        Returns:
            Tupla de (TestResult, report_dict con tendencias y metadata)
        """
        from bot.utils.test_report import TestReportHistory, TestReportFormatter

        # Ejecutar tests
        result = await self.run_tests(
            test_paths=test_paths,
            coverage=coverage,
            marker=marker,
            timeout=timeout
        )

        # Cargar historial para comparacion
        history = TestReportHistory(project_root=self.project_root)
        trend = await history.get_trend_comparison(result)

        # Guardar en historial (no bloquear)
        if save_history:
            asyncio.create_task(history.add_record(result))

        # Generar HTML si se solicita
        html_path = None
        if generate_html:
            formatter = TestReportFormatter(project_root=self.project_root)
            html_path = formatter.generate_html_report(
                result,
                output_path=html_output_path,
                trend=trend
            )

        # Construir reporte completo
        report = {
            "result": result,
            "trend": trend,
            "html_path": html_path,
            "git": {
                "commit": result.git_commit,
                "branch": result.git_branch
            },
            "timestamp": result.timestamp
        }

        return result, report

    async def get_test_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadisticas del historial de tests.

        Returns:
            Diccionario con estadisticas agregadas
        """
        from bot.utils.test_report import TestReportHistory

        history = TestReportHistory(project_root=self.project_root)
        return await history.get_statistics()

    async def run_smoke_tests(self) -> TestResult:
        """Ejecuta solo smoke tests (verificacion rapida)."""
        return await self.run_tests(marker="smoke", timeout=60)

    async def run_system_tests(self) -> TestResult:
        """Ejecuta tests del sistema."""
        return await self.run_tests(test_paths=["tests/test_system/"])

    def format_telegram_report(self, result: TestResult, max_length: int = 4000) -> str:
        """
        Formatea resultado para enviar por Telegram.

        Args:
            result: Resultado de tests
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

        # Metrics table
        lines.append("📊 <b>Metricas:</b>")
        lines.append(f"  • Total: {result.total}")
        lines.append(f"  • ✅ Pasados: {result.passed}")
        lines.append(f"  • ❌ Fallidos: {result.failed}")
        lines.append(f"  • ⚠️ Errores: {result.errors}")
        lines.append(f"  • ⏭️ Saltados: {result.skipped}")
        lines.append("")

        # Duration
        lines.append(f"⏱️ <b>Duracion:</b> {result.duration_seconds:.2f}s")

        # Coverage if available
        if result.coverage_percent is not None:
            lines.append(f"📈 <b>Coverage:</b> {result.coverage_percent:.1f}%")

        # Failed tests details (if any)
        if result.failed > 0 or result.errors > 0:
            lines.append("")
            lines.append("📝 <b>Tests fallidos:</b>")

            # Extract failed test names
            failed_pattern = r"FAILED\s+(\S+)"
            failed_tests = re.findall(failed_pattern, result.stdout + result.stderr)

            for test in failed_tests[:5]:  # Show first 5
                # Escape HTML special characters
                test_escaped = test.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                lines.append(f"  ❌ <code>{test_escaped}</code>")

            if len(failed_tests) > 5:
                lines.append(f"  ... y {len(failed_tests) - 5} mas")

        report = "\n".join(lines)

        # Truncate if exceeds max_length
        if len(report) > max_length:
            truncated = report[:max_length - 100]
            truncated += "\n\n<i>(Mensaje truncado por limite de longitud)</i>"
            return truncated

        return report

    def get_failed_test_details(self, result: TestResult, max_tests: int = 3) -> str:
        """
        Extrae detalles de tests fallidos para mostrar.

        Args:
            result: Resultado de tests
            max_tests: Maximo numero de tests a mostrar

        Returns:
            Texto formateado con detalles de fallos
        """
        if result.failed == 0 and result.errors == 0:
            return "✅ No hay tests fallidos."

        lines = []
        lines.append("📋 <b>Detalles de fallos:</b>")
        lines.append("")

        # Split output by test sections
        output = result.stdout + "\n" + result.stderr

        # Find failed test sections
        failed_pattern = r"(FAILED|ERROR)\s+(\S+)\s*\n.*?\n(?=FAILED|ERROR|PASSED|=+|$)"
        matches = re.findall(failed_pattern, output, re.DOTALL)

        for i, (status, test_name) in enumerate(matches[:max_tests]):
            if i > 0:
                lines.append("")

            # Escape HTML
            test_escaped = test_name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            lines.append(f"<b>{status}:</b> <code>{test_escaped}</code>")

            # Extract traceback
            section_match = re.search(
                rf"{re.escape(status)}\s+{re.escape(test_name)}.*?\n(.*?)(?=FAILED|ERROR|PASSED|=+|$)",
                output,
                re.DOTALL
            )
            if section_match:
                traceback = section_match.group(1).strip()
                # Limit traceback length
                if len(traceback) > 500:
                    traceback = traceback[:500] + "\n..."
                # Escape HTML
                traceback_escaped = traceback.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                lines.append(f"<pre>{traceback_escaped}</pre>")

        if len(matches) > max_tests:
            lines.append(f"\n<i>... y {len(matches) - max_tests} fallos mas</i>")

        return "\n".join(lines)
