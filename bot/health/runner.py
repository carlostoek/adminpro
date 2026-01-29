"""
Health API server runner for concurrent execution with aiogram bot.

Runs FastAPI health check API in asyncio task alongside bot polling.
Allows independent monitoring even if bot experiences issues.
"""
import asyncio
import logging
import socket
import time
from typing import Optional

import uvicorn
from uvicorn.config import Config as UvicornConfig
from uvicorn.server import Server

from bot.health.endpoints import create_health_app
from config import Config

logger = logging.getLogger(__name__)


def create_socket_with_reuse(host: str, port: int) -> Optional[socket.socket]:
    """
    Create a socket with SO_REUSEADDR to allow port reuse.

    This handles the case where the port is in TIME_WAIT state from
    a previous session, which is common during rapid restarts.

    Args:
        host: Host to bind to
        port: Port to bind to

    Returns:
        Socket if successful, None if port is truly in use
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Try to bind - this will fail if port is truly in use
        sock.bind((host, port))
        return sock
    except OSError as e:
        if e.errno == 98:  # Address already in use
            logger.warning(f"⚠️ Puerto {port} está ocupado (no TIME_WAIT)")
        else:
            logger.error(f"❌ Error creando socket: {e}")
        try:
            sock.close()
        except:
            pass
        return None


async def run_health_api(host: str, port: int) -> bool:
    """
    Run FastAPI health check API server asynchronously.

    Creates and configures uvicorn server to run FastAPI app
    in the existing asyncio event loop. Runs forever until cancelled.

    Args:
        host: Host to bind to (e.g., "0.0.0.0" for all interfaces)
        port: Port to listen on (e.g., 8000)

    Returns:
        bool: True if server started and ran successfully, False if bind failed

    Note:
        - Uses "asyncio" loop mode to share event loop with bot
        - Enables access logging for monitoring
        - Handles KeyboardInterrupt gracefully
        - Uses SO_REUSEADDR to handle TIME_WAIT state
        - Captures SystemExit to prevent uvicorn from killing the bot
    """
    # Create FastAPI app
    app = create_health_app()

    # Create socket with SO_REUSEADDR to handle TIME_WAIT
    sock = create_socket_with_reuse(host, port)
    if sock is None:
        logger.error(f"❌ No se pudo crear socket en {host}:{port}")
        logger.error("   Puerto está ocupado por otro proceso")
        return False

    # Configure uvicorn
    uvicorn_config = UvicornConfig(
        app=app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
        loop="asyncio"  # Use existing event loop
    )

    # Create server
    server = Server(uvicorn_config)

    # Log startup
    logger.info(f"🏥 Health API starting on http://{host}:{port}")

    try:
        # Run server with pre-created socket (prevents bind errors)
        # We need to pass the socket to uvicorn's startup
        await server.startup(sockets=[sock])
        await server.main_loop()
    except KeyboardInterrupt:
        logger.info("⌨️ Health API recibió KeyboardInterrupt")
    except asyncio.CancelledError:
        logger.info("🛑 Health API task cancelado - iniciando shutdown...")
        # CancelledError indica que debemos cerrar limpiamente
        raise  # Re-raise para que el caller sepa que fue cancelado
    except SystemExit as e:
        # Uvicorn calls sys.exit() on some errors - don't let it kill the bot
        logger.error(f"❌ Health API SystemExit({e.code}) - capturado, no se propaga")
        return False
    except OSError as e:
        if e.errno == 98:  # Address already in use
            logger.error(f"❌ Puerto {port} ocupado: {e}")
        else:
            logger.error(f"❌ Error en Health API server: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"❌ Error inesperado en Health API: {e}", exc_info=True)
        return False
    finally:
        # Asegurar que el servidor se cierre y libere el puerto
        try:
            if server.started:
                logger.info("🔌 Cerrando servidor Health API...")
                await server.shutdown(sockets=[sock] if sock else None)
        except Exception as e:
            logger.warning(f"⚠️ Error durante shutdown: {e}")
        finally:
            # Cerrar el socket si todavía está abierto
            try:
                if sock:
                    sock.close()
            except:
                pass
        logger.info("🔌 Health API server detenido")

    return True


async def start_health_server() -> Optional[asyncio.Task]:
    """
    Start health check API server as background asyncio task.

    Gets configuration from Config.HEALTH_PORT and Config.HEALTH_HOST,
    creates asyncio task for run_health_api(), and returns task reference.

    If the port is unavailable, logs a warning and returns None instead
    of failing, allowing the bot to continue running without health checks.

    Returns:
        asyncio.Task: Task object for tracking and graceful shutdown, or None if failed to start

    Note:
        Task runs in background and does not block bot startup.
        Store task reference for graceful shutdown in on_shutdown().
        If health API fails to start, bot continues running (health is optional).
    """
    logger.info("🚀 Starting health API server...")

    # Get configuration
    port = Config.HEALTH_PORT
    host = Config.HEALTH_HOST  # Default: "0.0.0.0" for external access

    # Quick check if port is available with SO_REUSEADDR test
    sock = create_socket_with_reuse(host, port)
    if sock is None:
        logger.error(f"❌ Puerto {port} no disponible - Health API no iniciará")
        logger.error("   Bot continuará funcionando sin health checks")
        logger.error(f"   Para liberar: kill $(lsof -t -i:{port}) 2>/dev/null")
        return None

    # Close the test socket - we'll create a new one in run_health_api
    try:
        sock.close()
    except:
        pass

    # Wait a moment for the port to be fully released
    await asyncio.sleep(0.5)

    # Create asyncio task for health API
    task = asyncio.create_task(run_health_api(host, port))

    logger.info(f"✅ Health API task created (host={host}, port={port})")

    return task
