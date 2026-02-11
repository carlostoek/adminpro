"""
System Startup Tests.

Tests for bot startup sequence:
- Database initialization
- ServiceContainer lazy loading
- BotConfig singleton seeding
- Background tasks initialization
"""
import pytest
from unittest.mock import Mock, AsyncMock


async def test_database_initialization(test_engine):
    """Verify database tables are created correctly."""
    from sqlalchemy import inspect

    async with test_engine.connect() as conn:
        def get_tables(sync_conn):
            inspector = inspect(sync_conn)
            return inspector.get_table_names()

        tables = await conn.run_sync(get_tables)

    # Verify all tables exist (at least the core ones)
    expected_tables = [
        'bot_config', 'vip_subscribers', 'invitation_tokens',
        'free_channel_requests', 'content_packages', 'user_interests',
        'users', 'user_role_change_log', 'subscription_plans'
    ]
    for table in expected_tables:
        assert table in tables, f"Table {table} not found"


async def test_service_container_lazy_loading(container):
    """Verify all services load correctly via lazy loading."""
    # Test subscription service
    subscription = container.subscription
    assert subscription is not None
    assert hasattr(subscription, 'generate_vip_token')
    assert hasattr(subscription, 'redeem_vip_token')

    # Test channel service
    channel = container.channel
    assert channel is not None
    assert hasattr(channel, 'setup_vip_channel')
    assert hasattr(channel, 'get_vip_channel_id')

    # Test config service
    config = container.config
    assert config is not None
    assert hasattr(config, 'get_config')
    assert hasattr(config, 'set_wait_time')

    # Test role detection service
    role_detection = container.role_detection
    assert role_detection is not None
    assert hasattr(role_detection, 'get_user_role')

    # Test content service
    content = container.content
    assert content is not None
    assert hasattr(content, 'create_package')

    # Test interest service
    interest = container.interest
    assert interest is not None
    assert hasattr(interest, 'register_interest')

    # Test user management service
    user_management = container.user_management
    assert user_management is not None
    assert hasattr(user_management, 'get_user_info')

    # Test VIP entry service
    vip_entry = container.vip_entry
    assert vip_entry is not None
    assert hasattr(vip_entry, 'get_current_stage')

    # Test stats service
    stats = container.stats
    assert stats is not None

    # Test pricing service
    pricing = container.pricing
    assert pricing is not None

    # Test user service
    user = container.user
    assert user is not None

    # Test message service (Lucien voice)
    message = container.message
    assert message is not None

    # Test role change service
    role_change = container.role_change
    assert role_change is not None

    # Test session history
    session_history = container.session_history
    assert session_history is not None


async def test_service_container_get_loaded_services(container):
    """Verify get_loaded_services tracks loaded services correctly."""
    # Initially no services should be loaded
    loaded_before = container.get_loaded_services()
    assert isinstance(loaded_before, list)

    # Access a service to trigger lazy loading
    _ = container.config

    # Now config should be in loaded services
    loaded_after = container.get_loaded_services()
    assert "config" in loaded_after


async def test_service_container_preload_critical_services(container):
    """Verify preload_critical_services loads expected services."""
    # Preload critical services
    await container.preload_critical_services()

    # Verify critical services are loaded
    loaded = container.get_loaded_services()
    assert "subscription" in loaded
    assert "config" in loaded


async def test_botconfig_singleton_seeding(test_session):
    """Verify BotConfig is auto-seeded with defaults."""
    from bot.database.models import BotConfig
    from bot.services.config import ConfigService

    config_service = ConfigService(test_session)

    # First access should return singleton
    config = await config_service.get_config()
    assert config is not None
    assert config.id == 1

    # Verify default values from fixture
    assert config.wait_time_minutes >= 1
    assert config.vip_reactions is not None
    assert len(config.vip_reactions) > 0
    assert config.free_reactions is not None
    assert len(config.free_reactions) > 0


async def test_botconfig_singleton_persistence(test_session):
    """Verify BotConfig singleton persists across service calls."""
    from bot.services.config import ConfigService

    config_service = ConfigService(test_session)

    # Get config twice
    config1 = await config_service.get_config()
    config2 = await config_service.get_config()

    # Should be the same object (singleton)
    assert config1.id == config2.id
    assert config1.id == 1


async def test_background_tasks_scheduler_initialization():
    """Verify background tasks scheduler initializes and stops correctly."""
    from bot.background.tasks import (
        start_background_tasks,
        stop_background_tasks,
        get_scheduler_status
    )

    # Create a mock bot
    mock_bot = Mock()
    mock_bot.id = 123456789

    try:
        # Start background tasks
        await start_background_tasks(mock_bot)

        # Verify scheduler is running
        status = get_scheduler_status()
        assert status["running"] is True
        assert status["jobs_count"] == 3  # Three scheduled jobs
    finally:
        # Stop background tasks to ensure cleanup
        stop_background_tasks()

    # Verify scheduler stopped after cleanup
    status = get_scheduler_status()
    assert status["running"] is False


async def test_background_tasks_scheduler_no_duplicate_start():
    """Verify starting scheduler twice doesn't create duplicate jobs."""
    from bot.background.tasks import (
        start_background_tasks,
        stop_background_tasks,
        get_scheduler_status
    )

    mock_bot = Mock()
    mock_bot.id = 123456789

    try:
        # Start twice
        await start_background_tasks(mock_bot)
        await start_background_tasks(mock_bot)  # Should warn but not duplicate

        # Should still have only 3 jobs
        status = get_scheduler_status()
        assert status["jobs_count"] == 3
    finally:
        # Cleanup
        stop_background_tasks()



async def test_background_tasks_job_details():
    """Verify background tasks have correct job configuration."""
    from bot.background.tasks import (
        start_background_tasks,
        stop_background_tasks,
        get_scheduler_status
    )

    mock_bot = Mock()
    mock_bot.id = 123456789

    try:
        await start_background_tasks(mock_bot)

        status = get_scheduler_status()
        jobs = status["jobs"]

        # Verify job IDs
        job_ids = [job["id"] for job in jobs]
        assert "expire_vip" in job_ids
        assert "process_free_queue" in job_ids
        assert "cleanup_old_data" in job_ids

        # Verify job names are present
        job_names = [job["name"] for job in jobs]
        assert any("VIP" in name or "vip" in name for name in job_names)
        assert any("Free" in name or "free" in name for name in job_names)
    finally:
        # Cleanup
        stop_background_tasks()



async def test_service_container_dependency_injection(container):
    """Verify ServiceContainer properly injects dependencies."""
    # Verify session is accessible
    assert container._session is not None

    # Verify bot is accessible
    assert container._bot is not None

    # Verify services can access dependencies
    subscription = container.subscription
    assert subscription.session is container._session
    assert subscription.bot is container._bot


async def test_all_services_accessible_after_preload(container):
    """Verify all 14 services are accessible after container initialization."""
    services_to_test = [
        ("subscription", ["generate_vip_token", "redeem_vip_token"]),
        ("channel", ["setup_vip_channel", "get_vip_channel_id"]),
        ("config", ["get_config", "set_wait_time"]),
        ("stats", ["get_overall_stats"]),
        ("pricing", ["get_all_plans"]),
        ("user", ["get_or_create_user"]),
        ("message", []),  # Lucien voice service
        ("session_history", ["get_recent_variants"]),
        ("role_detection", ["get_user_role"]),
        ("content", ["create_package"]),
        ("role_change", ["log_role_change"]),
        ("interest", ["register_interest"]),
        ("user_management", ["get_user_info"]),
        ("vip_entry", ["get_current_stage"]),
    ]

    for service_name, expected_methods in services_to_test:
        service = getattr(container, service_name)
        assert service is not None, f"Service {service_name} is None"

        for method in expected_methods:
            assert hasattr(service, method), f"Service {service_name} missing method {method}"
