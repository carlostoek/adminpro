"""
Background Tasks Tests - Tests de tareas programadas.

Validan que el scheduler puede iniciarse correctamente
y manejar timezones sin errores.
"""
import pytest
from unittest.mock import AsyncMock

from bot.background.tasks import (
    start_background_tasks,
    stop_background_tasks,
    get_scheduler_status
)


@pytest.mark.asyncio
async def test_scheduler_starts_with_utc_timezone(mock_bot):
    """
    Test: El scheduler puede iniciarse con timezone UTC sin errores.

    Escenario:
    1. Iniciar scheduler
    2. Verificar que está corriendo
    3. Verificar que tiene 3 jobs programados
    4. Detener scheduler

    Expected:
    - start_background_tasks() no arroja ZoneInfoNotFoundError
    - Scheduler está running=True
    - 3 jobs activos (expire_vip, process_free_queue, cleanup_old_data)
    - stop_background_tasks() limpia correctamente
    """
    print("\n[TEST] Scheduler starts with UTC timezone")

    try:
        # Paso 1: Iniciar scheduler
        print("  1. Iniciando scheduler...")
        start_background_tasks(mock_bot)

        # Paso 2: Verificar estado
        print("  2. Verificando estado del scheduler...")
        status = get_scheduler_status()

        assert status["running"] is True, "Scheduler debe estar corriendo"
        print("     OK: Scheduler corriendo")

        # Paso 3: Verificar jobs
        print("  3. Verificando jobs programados...")
        assert status["jobs_count"] == 3, f"Deben haber 3 jobs, encontrados: {status['jobs_count']}"

        job_ids = [job["id"] for job in status["jobs"]]
        expected_jobs = ["expire_vip", "process_free_queue", "cleanup_old_data"]

        for expected_id in expected_jobs:
            assert expected_id in job_ids, f"Job '{expected_id}' no encontrado"

        print(f"     OK: 3 jobs activos: {', '.join(job_ids)}")

        # Paso 4: Verificar que todos los jobs tienen next_run_time
        print("  4. Verificando que jobs están programados...")
        for job in status["jobs"]:
            assert job["next_run_time"] is not None, f"Job '{job['id']}' no tiene next_run_time"
        print("     OK: Todos los jobs tienen next_run_time")

    finally:
        # Cleanup: Siempre detener scheduler
        print("  5. Deteniendo scheduler...")
        stop_background_tasks()

        # Verificar que se detuvo
        status = get_scheduler_status()
        assert status["running"] is False, "Scheduler debe estar detenido"
        assert status["jobs_count"] == 0, "No deben quedar jobs activos"
        print("     OK: Scheduler detenido correctamente")


@pytest.mark.asyncio
async def test_scheduler_handles_multiple_start_calls(mock_bot):
    """
    Test: start_background_tasks() es idempotente.

    Escenario:
    1. Iniciar scheduler
    2. Intentar iniciar nuevamente (debe ser ignorado)
    3. Verificar que sigue con 3 jobs (no duplicados)
    4. Detener scheduler

    Expected:
    - Segunda llamada a start_background_tasks() no crea jobs duplicados
    - Scheduler sigue con 3 jobs únicos
    """
    print("\n[TEST] Scheduler handles multiple start calls")

    try:
        # Paso 1: Iniciar scheduler
        print("  1. Primera llamada a start_background_tasks...")
        start_background_tasks(mock_bot)

        status = get_scheduler_status()
        assert status["running"] is True
        assert status["jobs_count"] == 3
        print("     OK: Scheduler iniciado con 3 jobs")

        # Paso 2: Intentar iniciar nuevamente
        print("  2. Segunda llamada a start_background_tasks (debe ser ignorada)...")
        start_background_tasks(mock_bot)

        # Paso 3: Verificar estado
        print("  3. Verificando que no se duplicaron jobs...")
        status = get_scheduler_status()
        assert status["running"] is True
        assert status["jobs_count"] == 3, f"Deben seguir 3 jobs, encontrados: {status['jobs_count']}"
        print("     OK: No se duplicaron jobs (idempotencia correcta)")

    finally:
        # Cleanup
        print("  4. Deteniendo scheduler...")
        stop_background_tasks()
        print("     OK: Scheduler detenido")


@pytest.mark.asyncio
async def test_scheduler_stop_without_start(mock_bot):
    """
    Test: stop_background_tasks() puede llamarse sin start previo.

    Escenario:
    1. Llamar stop_background_tasks() sin haber iniciado
    2. Verificar que no arroja error

    Expected:
    - No arroja excepción
    - Estado permanece running=False
    """
    print("\n[TEST] Scheduler stop without start")

    # Paso 1: Detener sin iniciar
    print("  1. Llamando stop_background_tasks sin start previo...")
    stop_background_tasks()  # No debe arrojar error

    # Paso 2: Verificar estado
    print("  2. Verificando estado...")
    status = get_scheduler_status()
    assert status["running"] is False
    assert status["jobs_count"] == 0
    print("     OK: stop_background_tasks() maneja gracefully llamadas sin start")
