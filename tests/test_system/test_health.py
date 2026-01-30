"""
Health Check Endpoint Tests.

Tests for FastAPI health check endpoints:
- Health check with healthy database
- Health check with database errors
- Root endpoint connectivity
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock


async def test_health_check_root_endpoint():
    """Verify root endpoint returns service info."""
    from bot.health.endpoints import create_health_app

    app = create_health_app()

    # Use the app directly with async test client
    from httpx import AsyncClient, ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "lucien-bot-health"
    assert data["status"] == "operational"


async def test_health_check_healthy():
    """Verify health check returns 200 when all components are healthy."""
    from bot.health.endpoints import create_health_app
    from bot.health.check import HealthStatus
    from httpx import AsyncClient, ASGITransport

    app = create_health_app()

    # Mock the health check functions
    with patch("bot.health.endpoints.get_health_summary") as mock_summary:
        mock_summary.return_value = {
            "status": "healthy",
            "timestamp": "2024-01-28T12:00:00Z",
            "components": {
                "bot": "healthy",
                "database": "healthy"
            }
        }

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "components" in data
    assert data["components"]["bot"] == "healthy"
    assert data["components"]["database"] == "healthy"
    assert "timestamp" in data


async def test_health_check_degraded():
    """Verify health check returns 200 when system is degraded."""
    from bot.health.endpoints import create_health_app
    from httpx import AsyncClient, ASGITransport

    app = create_health_app()

    with patch("bot.health.endpoints.get_health_summary") as mock_summary:
        mock_summary.return_value = {
            "status": "degraded",
            "timestamp": "2024-01-28T12:00:00Z",
            "components": {
                "bot": "healthy",
                "database": "degraded"
            }
        }

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

    # Degraded still returns 200 (system is operational)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"


async def test_health_check_unhealthy():
    """Verify health check returns 503 when system is unhealthy."""
    from bot.health.endpoints import create_health_app
    from httpx import AsyncClient, ASGITransport

    app = create_health_app()

    with patch("bot.health.endpoints.get_health_summary") as mock_summary:
        mock_summary.return_value = {
            "status": "unhealthy",
            "timestamp": "2024-01-28T12:00:00Z",
            "components": {
                "bot": "healthy",
                "database": "unhealthy"
            }
        }

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

    # Unhealthy returns 503
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["components"]["database"] == "unhealthy"


async def test_health_check_bot_unhealthy():
    """Verify health check returns 503 when bot is unhealthy."""
    from bot.health.endpoints import create_health_app
    from httpx import AsyncClient, ASGITransport

    app = create_health_app()

    with patch("bot.health.endpoints.get_health_summary") as mock_summary:
        mock_summary.return_value = {
            "status": "unhealthy",
            "timestamp": "2024-01-28T12:00:00Z",
            "components": {
                "bot": "unhealthy",
                "database": "healthy"
            }
        }

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["components"]["bot"] == "unhealthy"


async def test_check_bot_health_with_valid_token():
    """Verify bot health check passes with valid token."""
    from bot.health.check import check_bot_health, HealthStatus

    with patch("bot.health.check.Config") as mock_config:
        mock_config.BOT_TOKEN = "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789"

        status = check_bot_health()

    assert status == HealthStatus.HEALTHY


async def test_check_bot_health_with_missing_token():
    """Verify bot health check fails when token is missing."""
    from bot.health.check import check_bot_health, HealthStatus

    with patch("bot.health.check.Config") as mock_config:
        mock_config.BOT_TOKEN = None

        status = check_bot_health()

    assert status == HealthStatus.UNHEALTHY


async def test_check_bot_health_with_empty_token():
    """Verify bot health check fails when token is empty."""
    from bot.health.check import check_bot_health, HealthStatus

    with patch("bot.health.check.Config") as mock_config:
        mock_config.BOT_TOKEN = ""

        status = check_bot_health()

    assert status == HealthStatus.UNHEALTHY


async def test_check_bot_health_with_short_token():
    """Verify bot health check fails when token is too short."""
    from bot.health.check import check_bot_health, HealthStatus

    with patch("bot.health.check.Config") as mock_config:
        mock_config.BOT_TOKEN = "short_token"

        status = check_bot_health()

    assert status == HealthStatus.UNHEALTHY


async def test_check_database_health_healthy():
    """Verify database health check passes when engine is healthy."""
    from bot.health.check import check_database_health, HealthStatus

    # Create a mock engine that returns 1 for SELECT 1
    mock_engine = Mock()
    mock_conn = AsyncMock()
    mock_result = Mock()
    mock_result.fetchone.return_value = (1,)
    mock_conn.execute.return_value = mock_result

    # Mock the async context manager properly
    mock_engine.connect.return_value = mock_conn
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)

    with patch("bot.health.check.get_engine", return_value=mock_engine):
        status = await check_database_health()

    assert status == HealthStatus.HEALTHY


async def test_check_database_health_uninitialized():
    """Verify database health check fails when engine not initialized."""
    from bot.health.check import check_database_health, HealthStatus

    with patch("bot.health.check.get_engine", side_effect=RuntimeError("Engine not initialized")):
        status = await check_database_health()

    assert status == HealthStatus.UNHEALTHY


async def test_check_database_health_query_error():
    """Verify database health check fails when query errors."""
    from bot.health.check import check_database_health, HealthStatus

    mock_engine = Mock()
    mock_conn = AsyncMock()
    mock_conn.execute.side_effect = Exception("Connection failed")
    mock_engine.connect.return_value = mock_conn
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)

    with patch("bot.health.check.get_engine", return_value=mock_engine):
        status = await check_database_health()

    assert status == HealthStatus.UNHEALTHY


async def test_check_database_health_wrong_result():
    """Verify database health check fails when query returns unexpected result."""
    from bot.health.check import check_database_health, HealthStatus

    mock_engine = Mock()
    mock_conn = AsyncMock()
    mock_result = Mock()
    mock_result.fetchone.return_value = (0,)  # Wrong result
    mock_conn.execute.return_value = mock_result
    mock_engine.connect.return_value = mock_conn
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)

    with patch("bot.health.check.get_engine", return_value=mock_engine):
        status = await check_database_health()

    assert status == HealthStatus.UNHEALTHY


async def test_get_health_summary_all_healthy():
    """Verify health summary when all components are healthy."""
    from bot.health.check import get_health_summary, HealthStatus

    with patch("bot.health.check.check_bot_health", return_value=HealthStatus.HEALTHY):
        with patch("bot.health.check.check_database_health", return_value=HealthStatus.HEALTHY):
            summary = await get_health_summary()

    assert summary["status"] == "healthy"
    assert summary["components"]["bot"] == "healthy"
    assert summary["components"]["database"] == "healthy"
    assert "timestamp" in summary


async def test_get_health_summary_mixed_status():
    """Verify health summary with mixed component status."""
    from bot.health.check import get_health_summary, HealthStatus

    with patch("bot.health.check.check_bot_health", return_value=HealthStatus.HEALTHY):
        with patch("bot.health.check.check_database_health", return_value=HealthStatus.DEGRADED):
            summary = await get_health_summary()

    assert summary["status"] == "degraded"
    assert summary["components"]["bot"] == "healthy"
    assert summary["components"]["database"] == "degraded"


async def test_get_health_summary_all_unhealthy():
    """Verify health summary when all components are unhealthy."""
    from bot.health.check import get_health_summary, HealthStatus

    with patch("bot.health.check.check_bot_health", return_value=HealthStatus.UNHEALTHY):
        with patch("bot.health.check.check_database_health", return_value=HealthStatus.UNHEALTHY):
            summary = await get_health_summary()

    assert summary["status"] == "unhealthy"
    assert summary["components"]["bot"] == "unhealthy"
    assert summary["components"]["database"] == "unhealthy"


async def test_health_app_has_no_docs():
    """Verify health app has docs disabled for production."""
    from bot.health.endpoints import create_health_app

    app = create_health_app()

    # Swagger UI should be disabled
    assert app.docs_url is None
    # ReDoc should be disabled
    assert app.redoc_url is None
