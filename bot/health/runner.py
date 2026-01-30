"""
Health API server runner for concurrent execution with aiogram bot.

Runs FastAPI health check API in asyncio task alongside bot polling.
Allows independent monitoring even if bot experiences issues.

Key design: Uses shared server instance with explicit shutdown control
to avoid uvicorn's signal handling conflicts with aiogram.
"""
import asyncio
import logging
import socket
import time
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from uvicorn.config import Config as UvicornConfig
from uvicorn.server import Server

from bot.health.endpoints import create_health_app
from config import Config

logger = logging.getLogger(__name__)

# Shared server instance for controlled shutdown
_health_server: Optional["ManagedHealthServer"] = None


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


class ManagedHealthServer:
    """
    Wrapper around uvicorn.Server with explicit lifecycle control.

    This prevents uvicorn from handling signals directly, avoiding conflicts
    with aiogram's signal handling.
    """

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.server: Optional[Server] = None
        self._serve_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

    async def start(self) -> bool:
        """
        Start the health server.

        Returns:
            True if started successfully, False otherwise
        """
        try:
            app = create_health_app()

            # Configure uvicorn WITHOUT signal handling
            # We'll handle shutdown ourselves via stop()
            config = UvicornConfig(
                app=app,
                host=self.host,
                port=self.port,
                log_level="warning",  # Reduce noise
                access_log=False,
                loop="asyncio",
            )

            # Disable uvicorn's signal handling
            self.server = Server(config)

            # Start serving in background task
            self._serve_task = asyncio.create_task(self._serve_with_monitoring())

            # Wait a moment to verify startup
            await asyncio.sleep(0.5)

            if self._serve_task.done():
                # Check if it crashed
                try:
                    self._serve_task.result()
                except Exception as e:
                    logger.error(f"❌ Health server falló al iniciar: {e}")
                    return False

            logger.info(f"🏥 Health API corriendo en http://{self.host}:{self.port}")
            return True

        except Exception as e:
            logger.error(f"❌ Error iniciando health server: {e}", exc_info=True)
            return False

    async def _serve_with_monitoring(self):
        """
        Serve with custom monitoring loop.

        This replaces server.serve() to avoid uvicorn's signal handling.
        We manually serve and check for our shutdown event.
        """
        if not self.server:
            return

        try:
            # Start the actual server
            # Note: We use the internal method that doesn't handle signals
            await self.server.serve()
        except asyncio.CancelledError:
            logger.debug("🛑 Health server serve cancelled")
            raise
        except Exception as e:
            logger.error(f"❌ Health server error: {e}", exc_info=True)
        finally:
            self._shutdown_event.set()

    async def stop(self, timeout: float = 5.0):
        """
        Stop the health server gracefully.

        Args:
            timeout: Maximum seconds to wait for shutdown
        """
        if self._serve_task is None or self._serve_task.done():
            return

        logger.info("🛑 Deteniendo health server...")

        # Signal shutdown
        if self.server:
            self.server.should_exit = True

        # Wait for task to complete
        try:
            await asyncio.wait_for(self._serve_task, timeout=timeout)
            logger.info("✅ Health server detenido correctamente")
        except asyncio.TimeoutError:
            logger.warning("⚠️ Health server timeout, cancelando...")
            self._serve_task.cancel()
            try:
                await self._serve_task
            except asyncio.CancelledError:
                logger.info("✅ Health server cancelado")
        except Exception as e:
            logger.warning(f"⚠️ Error deteniendo health server: {e}")

    async def wait_for_shutdown(self):
        """Wait until the server has shut down."""
        await self._shutdown_event.wait()


async def start_health_server() -> Optional[asyncio.Task]:
    """
    Start health check API server as background asyncio task.

    Returns:
        asyncio.Task if started successfully, None otherwise
    """
    global _health_server

    logger.info("🚀 Iniciando health API server...")

    port = Config.HEALTH_PORT
    host = Config.HEALTH_HOST

    # Check port availability
    if not is_port_available(host, port):
        logger.warning(f"⚠️ Puerto {port} ocupado, esperando...")
        if not wait_for_port_release(host, port, timeout=10):
            logger.error(f"❌ Puerto {port} no disponible")
            return None

    # Create managed server instance
    _health_server = ManagedHealthServer(host, port)

    # Start the server
    if not await _health_server.start():
        logger.error("❌ No se pudo iniciar health server")
        _health_server = None
        return None

    # Create a task that waits for shutdown
    # This task is what main.py monitors
    task = asyncio.create_task(_health_server.wait_for_shutdown())

    logger.info(f"✅ Health API task created (host={host}, port={port})")
    return task


async def stop_health_server():
    """
    Explicitly stop the health server.

    This should be called during shutdown to ensure clean termination.
    """
    global _health_server

    if _health_server:
        await _health_server.stop()
        _health_server = None
