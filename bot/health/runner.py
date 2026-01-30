"""
Health API server runner for concurrent execution with aiogram bot.

Runs FastAPI health check API in a separate thread with its own event loop.
This completely isolates uvicorn from aiogram's event loop, preventing
signal handling conflicts and blocking issues.
"""
import asyncio
import logging
import socket
import threading
import time
from typing import Optional

import uvicorn

from bot.health.endpoints import create_health_app
from config import Config

logger = logging.getLogger(__name__)

# Global server state for controlled shutdown
_health_server_thread: Optional[threading.Thread] = None
_shutdown_event = threading.Event()
_started_event = threading.Event()
_startup_success = False


def is_port_available(host: str, port: int) -> bool:
    """Check if a port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result != 0  # 0 means port is in use
    except Exception:
        return False


def wait_for_port_release(host: str, port: int, timeout: int = 30) -> bool:
    """
    Wait for a port to become available.

    Args:
        host: Host to check
        port: Port to check
        timeout: Maximum time to wait in seconds

    Returns:
        True if port became available, False if timeout
    """
    logger.info(f"⏳ Esperando que el puerto {port} se libere...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_port_available(host, port):
            logger.info(f"✅ Puerto {port} liberado")
            return True
        time.sleep(0.5)
    logger.warning(f"⚠️ Timeout esperando puerto {port}")
    return False


def _run_server_in_thread(host: str, port: int, shutdown_event: threading.Event):
    """
    Run uvicorn server in a separate thread with its own event loop.

    This function runs in the background thread and blocks until shutdown.
    """
    global _startup_success

    try:
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Create FastAPI app
        app = create_health_app()

        # Configure uvicorn to run in this thread
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="warning",
            access_log=False,
            loop=loop,  # Use our thread's event loop
        )

        server = uvicorn.Server(config)

        # Signal that we're about to start
        _started_event.set()

        # Run server with graceful shutdown handling
        async def serve_with_shutdown():
            # Start server in a task
            server_task = asyncio.create_task(server.serve())

            # Wait for shutdown signal or server to complete
            while not shutdown_event.is_set() and server_task and not server_task.done():
                await asyncio.sleep(0.1)

            # Trigger graceful shutdown
            if server_task and not server_task.done():
                logger.debug("Iniciando shutdown graceful del servidor...")
                server.should_exit = True
                await asyncio.wait_for(server_task, timeout=4.0)

        loop.run_until_complete(serve_with_shutdown())

        logger.info("🔌 Health API thread finalizado")

    except Exception as e:
        logger.error(f"❌ Error en health API thread: {e}", exc_info=True)
        _startup_success = False
    finally:
        # Clean up the thread's event loop
        try:
            loop.close()
        except Exception:
            pass


async def start_health_server() -> Optional[threading.Thread]:
    """
    Start health check API server in a background thread.

    The thread runs its own event loop, completely isolated from aiogram.

    Returns:
        Thread object if started successfully, None otherwise
    """
    global _health_server_thread, _shutdown_event, _started_event, _startup_success

    logger.info("🚀 Iniciando health API server...")

    port = Config.HEALTH_PORT
    host = Config.HEALTH_HOST

    # Check port availability
    if not is_port_available(host, port):
        logger.warning(f"⚠️ Puerto {port} ocupado, esperando...")
        if not wait_for_port_release(host, port, timeout=10):
            logger.error(f"❌ Puerto {port} no disponible")
            return None

    # Reset events
    _shutdown_event.clear()
    _started_event.clear()
    _startup_success = True

    # Start server in background thread (pass shutdown_event so thread can monitor it)
    _health_server_thread = threading.Thread(
        target=_run_server_in_thread,
        args=(host, port, _shutdown_event),
        daemon=True,  # Daemon thread won't prevent process exit
        name="HealthAPIServer"
    )

    _health_server_thread.start()

    # Wait for thread to signal it has started
    _started_event.wait(timeout=5)

    if not _started_event.is_set():
        logger.error("❌ Health API thread no inició (timeout)")
        return None

    # Give server a moment to actually bind to port
    await asyncio.sleep(0.5)

    # Verify port is now in use (server is listening)
    if not is_port_available(host, port):
        logger.info(f"✅ Health API corriendo en http://{host}:{port}")
        return _health_server_thread
    else:
        logger.error("❌ Health API no está escuchando en el puerto")
        return None


async def stop_health_server():
    """
    Stop the health server by signaling the background thread.

    The thread will gracefully shutdown uvicorn and exit.
    """
    global _health_server_thread, _shutdown_event

    if _health_server_thread is None or not _health_server_thread.is_alive():
        logger.debug("Health API thread no está corriendo")
        return

    logger.info("🛑 Deteniendo health API server...")

    # Signal the thread to shutdown
    _shutdown_event.set()

    # Wait for thread to finish (with timeout)
    _health_server_thread.join(timeout=8)

    if _health_server_thread.is_alive():
        logger.warning("⚠️ Health API thread no respondió, forzando...")
        # Thread is daemon, so it will be killed when process exits
    else:
        logger.info("✅ Health API detenido correctamente")

    _health_server_thread = None
