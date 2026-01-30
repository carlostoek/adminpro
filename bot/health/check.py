"""
Health check utilities for bot and database monitoring.

Provides functions to check bot token validity and database connectivity.
Used by FastAPI health endpoints for Railway monitoring.
"""
import logging
from datetime import datetime
from enum import Enum
from typing import Dict

from config import Config
from bot.database.engine import get_engine
from sqlalchemy import text

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """
    Health status enumeration.

    Values:
        HEALTHY: Component is functioning normally
        DEGRADED: Component is working but with reduced functionality
        UNHEALTHY: Component is not functioning
    """
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


def check_bot_health() -> HealthStatus:
    """
    Check bot health by validating BOT_TOKEN.

    Verifies:
    - BOT_TOKEN is present in Config
    - BOT_TOKEN has minimum length (20+ characters)

    Returns:
        HealthStatus.HEALTHY if token is valid
        HealthStatus.UNHEALTHY if token is missing or invalid

    Note:
        Full token validation with Telegram API requires async context,
        so this performs basic validation only.
    """
    logger.info("Checking bot health...")

    # Check if BOT_TOKEN exists
    if not Config.BOT_TOKEN:
        logger.warning("BOT_TOKEN is missing or empty")
        return HealthStatus.UNHEALTHY

    # Check minimum length (Telegram tokens are typically 46+ characters)
    if len(Config.BOT_TOKEN) < 20:
        logger.warning(f"BOT_TOKEN seems invalid (length: {len(Config.BOT_TOKEN)})")
        return HealthStatus.UNHEALTHY

    logger.debug("BOT_TOKEN validation passed")
    return HealthStatus.HEALTHY


async def check_database_health() -> HealthStatus:
    """
    Check database health by testing connectivity.

    Verifies:
    - Database engine is initialized
    - Can execute a simple query (SELECT 1)

    Returns:
        HealthStatus.HEALTHY if database is responsive
        HealthStatus.UNHEALTHY if engine not initialized or query fails

    Raises:
        RuntimeError: If engine not initialized (caught and logged)
    """
    logger.info("Checking database health...")

    try:
        # Get engine (raises RuntimeError if not initialized)
        engine = get_engine()

        # Test connectivity with simple query
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            row = result.fetchone()

            if row and row[0] == 1:
                logger.debug("Database connectivity test passed")
                return HealthStatus.HEALTHY
            else:
                logger.error("Database query returned unexpected result")
                return HealthStatus.UNHEALTHY

    except RuntimeError as e:
        logger.error(f"Database engine not initialized: {e}")
        return HealthStatus.UNHEALTHY

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return HealthStatus.UNHEALTHY


async def get_health_summary() -> Dict[str, any]:
    """
    Get comprehensive health summary for all components.

    Checks:
    - Bot token validity
    - Database connectivity

    Returns:
        Dict with overall status and component statuses:
        {
            "status": "healthy" | "degraded" | "unhealthy",
            "timestamp": "2024-01-28T12:00:00Z",
            "components": {
                "bot": "healthy" | "unhealthy",
                "database": "healthy" | "unhealthy"
            }
        }

    Note:
        Overall status logic:
        - healthy: All components are healthy
        - degraded: At least one component is degraded
        - unhealthy: At least one component is unhealthy
    """
    logger.debug("Generating health summary...")

    # Check individual components
    bot_status = check_bot_health()
    db_status = await check_database_health()

    # Determine overall status
    if bot_status == HealthStatus.UNHEALTHY or db_status == HealthStatus.UNHEALTHY:
        overall_status = HealthStatus.UNHEALTHY.value
    elif bot_status == HealthStatus.DEGRADED or db_status == HealthStatus.DEGRADED:
        overall_status = HealthStatus.DEGRADED.value
    else:
        overall_status = HealthStatus.HEALTHY.value

    # Build summary
    summary = {
        "status": overall_status,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "components": {
            "bot": bot_status.value,
            "database": db_status.value
        }
    }

    logger.debug(f"Health summary: {overall_status}")
    return summary
