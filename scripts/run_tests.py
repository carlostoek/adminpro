#!/usr/bin/env python3
"""
CLI Test Runner Script

Ejecuta tests de pytest desde la linea de comandos con opciones
de coverage, filtros por directorio, y reportes formateados.

Uso:
    python scripts/run_tests.py
    python scripts/run_tests.py --coverage
    python scripts/run_tests.py tests/test_system/
    python scripts/run_tests.py --marker "slow"
"""

import argparse
import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple


class TestRunner:
    """Ejecutor de tests con soporte para pytest y coverage."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.pytest_path = self._find_pytest()

    def _find_pytest(self) -> str:
        """Encuentra el ejecutable de pytest."""
        # Check virtual environment first
        venv_pytest = self.project_root / "venv" / "bin" / "pytest"
        if venv_pytest.exists():
            return str(venv_pytest)

        venv_pytest_win = self.project_root / "venv" / "Scripts" / "pytest.exe"
        if venv_pytest_win.exists():
            return str(venv_pytest_win)

        # Check PATH
        try:
            result = subprocess.run(
                ["which", "pytest"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Fallback to python -m pytest
        return "python"

    async def run_tests(
        self,
        test_paths: Optional[List[str]] = None,
        coverage: bool = False,
        marker: Optional[str] = None,
        verbose: bool = False,
        junit_xml: Optional[str] = None
    ) -> Tuple[int, str, str]:
        """
        Ejecuta tests en subprocess y retorna resultado.

        Args:
            test_paths: Lista de paths a ejecutar (None = todos)
            coverage: Si True, genera reporte de coverage
            marker: Ejecutar solo tests con este marker
            verbose: Salida verbose de pytest
            junit_xml: Path para output XML (opcional)

        Returns:
            Tuple de (returncode, stdout, stderr)
        """
        # Build pytest command
        if self.pytest_path.endswith("pytest") or self.pytest_path.endswith("pytest.exe"):
            cmd = [self.pytest_path]
        else:
            cmd = ["python", "-m", "pytest"]

        if verbose:
            cmd.append("-v")
        else:
            cmd.append("-v")

        if coverage:
            cmd.extend(["--cov=bot", "--cov-report=term", "--cov-report=term-missing"])

        if marker:
            cmd.extend(["-m", marker])

        if junit_xml:
            cmd.extend(["--junit-xml", junit_xml])

        cmd.extend(["--tb=short"])

        # Add test paths or default to tests/
        if test_paths:
            cmd.extend(test_paths)
        else:
            cmd.append("tests/")

        # Execute in subprocess
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.project_root
        )

        stdout, stderr = await proc.communicate()

        stdout_str = stdout.decode("utf-8", errors="replace")
        stderr_str = stderr.decode("utf-8", errors="replace")

        return proc.returncode or 0, stdout_str, stderr_str

    def parse_results(self, stdout: str, stderr: str) -> dict:
        """
        Parsea la salida de pytest para extraer metricas.

        Returns:
            Dict con: passed, failed, errors, skipped, total, duration
        """
        results = {
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "total": 0,
            "duration": 0.0,
            "coverage": None
        }

        # Combine stdout and stderr for parsing
        output = stdout + "\n" + stderr

        # Parse summary line like: "50 passed, 2 failed, 1 error in 12.34s"
        # or: "50 passed, 2 failed, 1 error, 3 skipped in 12.34s"
        summary_pattern = r"(\d+) passed(?:, (\d+) failed)?(?:, (\d+) error)?(?:, (\d+) skipped)? in ([\d.]+)s"
        match = re.search(summary_pattern, output)

        if match:
            results["passed"] = int(match.group(1)) if match.group(1) else 0
            results["failed"] = int(match.group(2)) if match.group(2) else 0
            results["errors"] = int(match.group(3)) if match.group(3) else 0
            results["skipped"] = int(match.group(4)) if match.group(4) else 0
            results["duration"] = float(match.group(5)) if match.group(5) else 0.0

        results["total"] = results["passed"] + results["failed"] + results["errors"] + results["skipped"]

        # Parse coverage percentage
        coverage_pattern = r"TOTAL\s+\d+\s+\d+\s+(\d+)%"
        coverage_match = re.search(coverage_pattern, output)
        if coverage_match:
            results["coverage"] = int(coverage_match.group(1))

        return results

    def format_report(self, results: dict, returncode: int) -> str:
        """Formatea resultados para display en consola."""
        lines = []
        lines.append("=" * 60)
        lines.append("📊 REPORTE DE TESTS")
        lines.append("=" * 60)
        lines.append("")

        # Status
        if returncode == 0 and results["failed"] == 0 and results["errors"] == 0:
            lines.append("✅ TODOS LOS TESTS PASARON")
        else:
            lines.append("❌ ALGUNOS TESTS FALLARON")
        lines.append("")

        # Metrics
        lines.append(f"  Total:     {results['total']}")
        lines.append(f"  ✅ Pasados:  {results['passed']}")
        lines.append(f"  ❌ Fallidos: {results['failed']}")
        lines.append(f"  ⚠️  Errores:  {results['errors']}")
        lines.append(f"  ⏭️  Saltados: {results['skipped']}")
        lines.append("")
        lines.append(f"  ⏱️  Duracion: {results['duration']:.2f}s")

        if results["coverage"] is not None:
            lines.append(f"  📈 Coverage: {results['coverage']}%")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)


async def main():
    """Punto de entrada del script CLI."""
    parser = argparse.ArgumentParser(
        description="Ejecutor de tests para el bot de Telegram"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Paths a ejecutar (default: todos los tests)"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generar reporte de coverage"
    )
    parser.add_argument(
        "--marker",
        help="Ejecutar solo tests con este marker"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Salida verbose"
    )
    parser.add_argument(
        "--junit-xml",
        help="Generar reporte JUnit XML"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output en formato JSON"
    )

    args = parser.parse_args()

    # Find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Create runner and execute
    runner = TestRunner(project_root)

    try:
        returncode, stdout, stderr = await runner.run_tests(
            test_paths=args.paths if args.paths else None,
            coverage=args.coverage,
            marker=args.marker,
            verbose=args.verbose,
            junit_xml=args.junit_xml
        )

        # Parse and format results
        results = runner.parse_results(stdout, stderr)

        if args.json:
            results["returncode"] = returncode
            print(json.dumps(results, indent=2))
        else:
            print(runner.format_report(results, returncode))

            # Show failed test names if any
            if results["failed"] > 0 or results["errors"] > 0:
                print("\n📝 Detalles de fallos:")
                print("-" * 60)
                # Extract failed test names from output
                failed_pattern = r"FAILED\s+(\S+)"
                failed_tests = re.findall(failed_pattern, stdout + stderr)
                for test in failed_tests[:10]:  # Show first 10
                    print(f"  ❌ {test}")
                if len(failed_tests) > 10:
                    print(f"  ... y {len(failed_tests) - 10} mas")

        sys.exit(returncode)

    except Exception as e:
        print(f"❌ Error ejecutando tests: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
