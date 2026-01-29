"""
Health API server runner for concurrent execution with aiogram bot.

Runs FastAPI health check API in asyncio task alongside bot polling.
Allows independent monitoring even if bot experiences issues.
"""
import asyncio
import logging
from typing import Optional

import uvicorn
from uvicorn.config import Config as UvicornConfig
from uvicorn.server import Server

from bot.health.endpoints import create_health_app
from config import Config

logger = logging.getLogger(__name__)


async def run_health_api(host: str, port: int) -> None:
    """
    Run FastAPI health check API server asynchronously.

    Creates and configures uvicorn server to run FastAPI app
    in the existing asyncio event loop. Runs forever until cancelled.

    Args:
        host: Host to bind to (e.g., "0.0.0.0" for all interfaces)
        port: Port to listen on (e.g., 8000)

    Returns:
        None (runs indefinitely until cancelled or KeyboardInterrupt)

    Note:
        - Uses "asyncio" loop mode to share event loop with bot
        - Enables access logging for monitoring
        - Handles KeyboardInterrupt gracefully
    """
    # Create FastAPI app
    app = create_health_app()

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
    logger.info(f"🏥 Health API running on http://{host}:{port}")

    try:
        # Run server (blocking until cancelled)
        await server.serve()
    except KeyboardInterrupt:
        logger.info("⌨️ Health API recibió KeyboardInterrupt")
    except asyncio.CancelledError:
        logger.info("🛑 Health API task cancelado")
    except Exception as e:
        logger.error(f"❌ Error en Health API server: {e}", exc_info=True)
    finally:
        logger.info("🔌 Health API server detenido")


async def start_health_server() -> asyncio.Task:
    """
    Start health check API server as background asyncio task.

    Gets configuration from Config.HEALTH_PORT and Config.HEALTH_HOST,
    creates asyncio task for run_health_api(), and returns task reference.

    Returns:
        asyncio.Task: Task object for tracking and graceful shutdown

    Raises:
        Exception: If task creation fails (logged, caught by caller)

    Note:
        Task runs in background and does not block bot startup.
        Store task reference for graceful shutdown in on_shutdown().
    """
    logger.info("🚀 Starting health API server...")

    # Get configuration
    port = Config.HEALTH_PORT
    host = Config.HEALTH_HOST  # Default: "0.0.0.0" for external access

    # Create asyncio task for health API
    task = asyncio.create_task(run_health_api(host, port))

    logger.info(f"✅ Health API task created (host={host}, port={port})")

    return task
