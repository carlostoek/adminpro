"""
Tests for database infrastructure.

Verifies in-memory database fixtures work correctly.
"""
import pytest
from sqlalchemy import text, inspect
from bot.database.models import BotConfig, VIPSubscriber, InvitationToken, FreeChannelRequest


async def test_in_memory_database(test_session):
    """Test that in-memory database is working."""
    result = await test_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


async def test_database_is_in_memory(test_engine):
    """Verify database URL is in-memory."""
    assert ":memory:" in str(test_engine.url)


async def test_tables_exist(test_session):
    """All model tables exist."""
    tables = await test_session.run_sync(
        lambda conn: inspect(conn).get_table_names()
    )
    expected = [
        'bot_config',
        'users',
        'subscription_plans',
        'invitation_tokens',
        'vip_subscribers',
        'free_channel_requests',
        'user_interests',
        'user_role_change_log',
        'content_packages'
    ]
    for table in expected:
        assert table in tables, f"Table '{table}' not found in database"


async def test_botconfig_singleton_exists(test_session):
    """Test that BotConfig singleton is pre-created."""
    config = await test_session.get(BotConfig, 1)
    assert config is not None
    assert config.id == 1
    assert config.wait_time_minutes == 5


async def test_botconfig_has_channel_ids(test_session):
    """Test that pre-created BotConfig has channel IDs."""
    config = await test_session.get(BotConfig, 1)
    assert config.vip_channel_id == "-1001234567890"
    assert config.free_channel_id == "-1000987654321"


async def test_botconfig_has_reactions(test_session):
    """Test that pre-created BotConfig has reactions configured."""
    config = await test_session.get(BotConfig, 1)
    assert config.vip_reactions == ["🔥", "❤️", "😍"]
    assert config.free_reactions == ["👍", "🙏"]


async def test_botconfig_has_subscription_fees(test_session):
    """Test that pre-created BotConfig has subscription fees."""
    config = await test_session.get(BotConfig, 1)
    assert config.subscription_fees == {"monthly": 10.0, "yearly": 100.0}


# ============================================================================
# DATABASE ISOLATION TESTS
# ============================================================================

async def test_database_isolation_write(test_session):
    """Write data in one test - should not exist in subsequent tests."""
    from datetime import datetime, timedelta

    subscriber = VIPSubscriber(
        user_id=999888777,
        username="isolation_test_user",
        expires_at=datetime.utcnow() + timedelta(days=30),
        status="active"
    )
    test_session.add(subscriber)
    await test_session.commit()

    result = await test_session.get(VIPSubscriber, 999888777)
    assert result is not None
    assert result.username == "isolation_test_user"


async def test_database_isolation_verify(test_session):
    """Verify data from previous test doesn't exist (isolation)."""
    result = await test_session.get(VIPSubscriber, 999888777)
    assert result is None


async def test_database_isolation_write_alt_id(test_session):
    """Write data with different ID to further verify isolation."""
    from datetime import datetime, timedelta

    subscriber = VIPSubscriber(
        user_id=888777666,
        username="another_isolation_test",
        expires_at=datetime.utcnow() + timedelta(days=30),
        status="active"
    )
    test_session.add(subscriber)
    await test_session.commit()

    result = await test_session.get(VIPSubscriber, 888777666)
    assert result is not None


async def test_database_isolation_verify_alt_id(test_session):
    """Verify the alt ID data also doesn't persist."""
    result1 = await test_session.get(VIPSubscriber, 999888777)
    result2 = await test_session.get(VIPSubscriber, 888777666)
    assert result1 is None
    assert result2 is None


# ============================================================================
# MODEL-SPECIFIC FIXTURE TESTS
# ============================================================================

@pytest.mark.skip(reason="test_vip_subscriber fixture not yet available")
async def test_vip_subscriber_fixture(test_vip_subscriber):
    """Test that test_vip_subscriber fixture creates a valid subscriber."""
    pass


async def test_invitation_token_fixture(test_invitation_token):
    """Test that test_invitation_token fixture creates a valid token."""
    assert test_invitation_token.token == "TEST_TOKEN_12345"
    assert test_invitation_token.generated_by == 987654321
    assert test_invitation_token.is_used is False
    assert test_invitation_token.duration_hours == 168


@pytest.mark.skip(reason="test_free_request fixture not yet available")
async def test_free_request_fixture(test_free_request):
    """Test that test_free_request fixture creates a valid request."""
    pass


# ============================================================================
# PRAGMA SETTINGS TESTS
# ============================================================================

async def test_pragma_foreign_keys_enabled(test_session):
    """Test that foreign keys are enforced."""
    result = await test_session.execute(text("PRAGMA foreign_keys"))
    value = result.scalar()
    assert value == 1, "Foreign keys should be enabled"


@pytest.mark.skip(reason="WAL mode not supported in all SQLite builds")
async def test_pragma_journal_mode(test_session):
    """Test that WAL mode is enabled."""
    result = await test_session.execute(text("PRAGMA journal_mode"))
    value = result.scalar()
    assert value.lower() == "wal", f"Journal mode should be WAL, got {value}"
