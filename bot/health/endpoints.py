"""
FastAPI health check endpoints for Railway monitoring.

Provides HTTP endpoints for checking bot and database health.
Separate from aiogram dispatcher to allow independent health checks.
"""
import logging
from typing import Dict

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from bot.health.check import get_health_summary

logger = logging.getLogger(__name__)


def create_health_app() -> FastAPI:
    """
    Create and configure FastAPI application for health checks.

    The app provides:
    - GET /health: Comprehensive health check with component status
    - GET /: Basic service info for connectivity testing

    Returns:
        FastAPI: Configured application instance

    Note:
        This runs on a separate port (HEALTH_PORT, default 8000)
        and does not interfere with the bot's aiogram dispatcher.
    """
    app = FastAPI(
        title="Lucien Bot Health",
        description="Health check endpoints for Railway monitoring",
        version="1.0.0",
        docs_url=None,  # Disable Swagger UI in production
        redoc_url=None  # Disable ReDoc in production
    )

    @app.get("/")
    async def root() -> Dict[str, str]:
        """
        Root endpoint for basic connectivity testing.

        Returns:
            Dict with service name and operational status
            Always returns 200 OK for basic connectivity checks

        Example response:
            {"service": "lucien-bot-health", "status": "operational"}
        """
        return {
            "service": "lucien-bot-health",
            "status": "operational"
        }

    @app.get("/health")
    async def health() -> JSONResponse:
        """
        Comprehensive health check endpoint.

        Checks bot token validity and database connectivity.
        Returns 200 OK when healthy/degraded, 503 when unhealthy.

        Returns:
            JSONResponse with health summary and appropriate status code

        Response structure:
            {
                "status": "healthy" | "degraded" | "unhealthy",
                "timestamp": "2024-01-28T12:00:00Z",
                "components": {
                    "bot": "healthy" | "unhealthy",
                    "database": "healthy" | "unhealthy"
                }
            }

        HTTP Status Codes:
            200: System is healthy or degraded (operational)
            503: System is unhealthy (service unavailable)
        """
        logger.info("Health check requested")

        # Get health summary from check module
        summary = await get_health_summary()

        # Determine HTTP status based on overall health
        if summary["status"] == "unhealthy":
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
            logger.warning(f"Health check failed: {summary['status']}")
        else:
            http_status = status.HTTP_200_OK
            logger.debug(f"Health check passed: {summary['status']}")

        return JSONResponse(
            content=summary,
            status_code=http_status
        )

    logger.info("FastAPI health app created")
    return app
