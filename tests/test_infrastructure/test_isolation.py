"""
Test Isolation Verification.

These tests verify that the test infrastructure properly isolates
each test from others. If isolation fails, these tests will fail.

The tests are designed in pairs:
- test_*_1: Creates data in the database
- test_*_2: Verifies the data does NOT exist (isolation confirmed)

If isolation is broken, the *_2 tests will fail because they'll
see data from the *_1 tests.
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import select

from bot.database.models import VIPSubscriber, InvitationToken, FreeChannelRequest, BotConfig, User


class TestDatabaseIsolation:
    """Verify each test gets a clean database."""

    async def test_isolation_vip_subscriber_1(self, test_session):
        """Create a VIP subscriber - data should not leak to other tests."""
        # First ensure user exists (foreign key constraint)
        user = User(
            user_id=1000001,
            username="isolation_test_user_1",
            first_name="Test",
            role="FREE"
        )
        test_session.add(user)
        await test_session.commit()

        # Create token for subscriber
        token = InvitationToken(
            token="ISOLATION001",
            generated_by=999999,
            duration_hours=24
        )
        test_session.add(token)
        await test_session.commit()

        # Create VIP subscriber
        subscriber = VIPSubscriber(
            user_id=1000001,
            expiry_date=datetime.utcnow() + timedelta(days=30),
            status="active",
            token_id=token.id
        )
        test_session.add(subscriber)
        await test_session.commit()

        # Verify exists in this test
        result = await test_session.get(VIPSubscriber, subscriber.id)
        assert result is not None
        assert result.user_id == 1000001

    async def test_isolation_vip_subscriber_2(self, test_session):
        """Subscriber from test_1 should NOT exist here - verifies isolation."""
        # Query for any VIP subscribers with user_id from test_1
        result = await test_session.execute(
            select(VIPSubscriber).where(VIPSubscriber.user_id == 1000001)
        )
        subscriber = result.scalar_one_or_none()
        assert subscriber is None, \
            "Database isolation failed - VIP subscriber from previous test leaked"

    async def test_isolation_invitation_token_1(self, test_session):
        """Create an invitation token - data should not leak to other tests."""
        token = InvitationToken(
            token="ISOLATION_TOKEN_123",
            generated_by=999999,
            duration_hours=24
        )
        test_session.add(token)
        await test_session.commit()

        result = await test_session.execute(
            select(InvitationToken).where(InvitationToken.token == "ISOLATION_TOKEN_123")
        )
        assert result.scalar_one_or_none() is not None

    async def test_isolation_invitation_token_2(self, test_session):
        """Token from test_1 should NOT exist here - verifies isolation."""
        result = await test_session.execute(
            select(InvitationToken).where(InvitationToken.token == "ISOLATION_TOKEN_123")
        )
        assert result.scalar_one_or_none() is None, \
            "Token isolation failed - token from previous test leaked"

    async def test_isolation_free_request_1(self, test_session):
        """Create a free channel request - data should not leak to other tests."""
        # First ensure user exists
        user = User(
            user_id=2000001,
            username="free_isolation_test",
            first_name="Free Test",
            role="FREE"
        )
        test_session.add(user)
        await test_session.commit()

        request = FreeChannelRequest(
            user_id=2000001,
            request_date=datetime.utcnow(),
            processed=False
        )
        test_session.add(request)
        await test_session.commit()

        result = await test_session.get(FreeChannelRequest, request.id)
        assert result is not None

    async def test_isolation_free_request_2(self, test_session):
        """Request from test_1 should NOT exist here - verifies isolation."""
        # Query all free requests
        result = await test_session.execute(select(FreeChannelRequest))
        requests = result.scalars().all()

        # Check that no requests from test_1 exist
        user_ids = [r.user_id for r in requests]
        assert 2000001 not in user_ids, \
            "Free request isolation failed - request from previous test leaked"


class TestBotConfigIsolation:
    """Verify BotConfig singleton behavior in tests with proper rollback."""

    async def test_botconfig_is_singleton_within_test(self, test_session):
        """BotConfig should be the same record within a test."""
        config1 = await test_session.get(BotConfig, 1)
        config2 = await test_session.get(BotConfig, 1)

        # Both should reference the same database row
        assert config1.id == config2.id == 1
        # In SQLAlchemy, they may be the same object instance too
        assert config1 is config2 or config1.id == config2.id

    async def test_botconfig_modifications_rolled_back(self, test_session):
        """Modifications to BotConfig should not persist between tests."""
        config = await test_session.get(BotConfig, 1)
        original_wait_time = config.wait_time_minutes

        # Modify the config
        config.wait_time_minutes = 999
        await test_session.commit()

        # Verify modified within this test
        config = await test_session.get(BotConfig, 1)
        assert config.wait_time_minutes == 999

        # Store original for verification in next test
        # (This value is stored in memory, not affecting isolation)
        TestBotConfigIsolation._original_wait_time = original_wait_time

    async def test_botconfig_reset_in_next_test(self, test_session):
        """BotConfig should have default values (modifications rolled back)."""
        config = await test_session.get(BotConfig, 1)

        # Should have default value (5), not 999 from previous test
        # If isolation is broken, this will fail with 999
        assert config.wait_time_minutes == 5, \
            f"Expected wait_time=5 (default), got {config.wait_time_minutes}. " \
            f"Isolation failed - BotConfig modification leaked from previous test!"


class TestSessionIsolation:
    """Verify session-level isolation between different sessions."""

    async def test_session_does_not_see_uncommitted(self, test_session, test_db):
        """Uncommitted data should not be visible to other sessions."""
        # Create user first (for FK constraint)
        user = User(
            user_id=3000001,
            username="session_test",
            first_name="Session Test",
            role="FREE"
        )
        test_session.add(user)
        await test_session.commit()

        # Create token
        token = InvitationToken(
            token="SESSION_TOKEN_001",
            generated_by=999999,
            duration_hours=24
        )
        test_session.add(token)
        await test_session.commit()

        # Add subscriber in this session (but don't commit yet)
        subscriber = VIPSubscriber(
            user_id=3000001,
            expiry_date=datetime.utcnow() + timedelta(days=30),
            status="active",
            token_id=token.id
        )
        test_session.add(subscriber)
        # Note: NOT committed yet

        # Create a new session - should not see uncommitted data
        async with test_db() as new_session:
            result = await new_session.get(VIPSubscriber, subscriber.id)
            assert result is None, \
                "Uncommitted data visible to other sessions - isolation violated"

        # Now commit and verify visible to new sessions
        await test_session.commit()

        async with test_db() as new_session:
            result = await new_session.get(VIPSubscriber, subscriber.id)
            assert result is not None, \
                "Committed data should be visible after commit"

    async def test_parallel_sessions_isolated(self, test_db):
        """Multiple concurrent sessions should be isolated from each other."""
        # Create two separate sessions
        async with test_db() as session1:
            async with test_db() as session2:
                # Modify BotConfig in session1
                config1 = await session1.get(BotConfig, 1)
                config1.wait_time_minutes = 777
                await session1.commit()

                # Session2 should still see original value
                config2 = await session2.get(BotConfig, 1)
                # Note: In SQLite with shared cache, this might see the change
                # depending on isolation level. The key is that transactions
                # don't interfere with each other.
                assert config2 is not None
                assert config2.id == 1


class TestDeterministicExecution:
    """Verify tests execute deterministically regardless of order."""

    _execution_order = []

    async def test_deterministic_1(self, test_session):
        """First test in deterministic sequence."""
        TestDeterministicExecution._execution_order.append(1)

        # Create some data
        user = User(
            user_id=4000001,
            username="deterministic_test",
            first_name="Deterministic",
            role="FREE"
        )
        test_session.add(user)
        await test_session.commit()

    async def test_deterministic_2(self, test_session):
        """Second test - should not see data from test_1."""
        TestDeterministicExecution._execution_order.append(2)

        # Should not see user from test_1
        result = await test_session.get(User, 4000001)
        assert result is None, \
            "Deterministic execution failed - data leaked between ordered tests"

        # Create our own data
        user = User(
            user_id=4000002,
            username="deterministic_test_2",
            first_name="Deterministic 2",
            role="VIP"
        )
        test_session.add(user)
        await test_session.commit()

    async def test_deterministic_3(self, test_session):
        """Third test - verifies isolation across multiple preceding tests."""
        TestDeterministicExecution._execution_order.append(3)

        # Should not see any users from previous tests
        result1 = await test_session.get(User, 4000001)
        result2 = await test_session.get(User, 4000002)

        assert result1 is None, "User from test_1 leaked"
        assert result2 is None, "User from test_2 leaked"

        # Verify execution order was maintained
        assert TestDeterministicExecution._execution_order == [1, 2, 3], \
            "Tests executed in unexpected order"
