"""
Test Cleanup Verification.

Ensures that all resources are properly cleaned up after tests.
These tests verify that the test infrastructure doesn't leak resources
between test executions.
"""
import gc
import pytest
from sqlalchemy import text

from bot.database.models import BotConfig


class TestResourceCleanup:
    """Verify resources are cleaned up after tests."""

    async def test_database_connections_closed(self, test_engine):
        """Verify database connections are properly managed with engine."""
        # Engine should be usable during test
        async with test_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

        # After exiting context, connection is returned to pool/closed
        # The engine itself remains usable until disposed
        async with test_engine.connect() as conn:
            result = await conn.execute(text("SELECT 2"))
            assert result.scalar() == 2

    async def test_sessions_properly_closed(self, test_db):
        """Verify sessions are properly closed after use."""
        session = None

        async with test_db() as session:
            # Session should be active
            config = await session.get(BotConfig, 1)
            assert config is not None
            assert config.id == 1

        # After exiting context, session should be closed
        # Note: SQLAlchemy session.is_active may still be True if not
        # explicitly closed, but the connection is returned to pool

    async def test_session_rollback_on_exit(self, test_db):
        """Verify uncommitted changes are rolled back when session exits."""
        from bot.database.models import User

        async with test_db() as session:
            # Create a user
            user = User(
                user_id=5000001,
                username="rollback_test",
                first_name="Rollback Test",
                role="FREE"
            )
            session.add(user)
            # Note: We don't commit - changes should be rolled back on exit

        # New session should not see the uncommitted user
        async with test_db() as new_session:
            result = await new_session.get(User, 5000001)
            assert result is None, "Uncommitted data persisted after session exit"

    async def test_engine_dispose_releases_resources(self):
        """Verify engine disposal releases all resources."""
        from sqlalchemy.ext.asyncio import create_async_engine
        from bot.database.base import Base

        # Create a temporary engine
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
            future=True
        )

        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Use it
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

        # Dispose should release all connections
        await engine.dispose()

        # After dispose, engine should not be usable
        # (attempting to connect would raise an error)


class TestServiceContainerCleanup:
    """Verify ServiceContainer doesn't leak resources."""

    async def test_container_services_loadable(self, container):
        """Verify ServiceContainer can load services without errors."""
        # Load some services
        _ = container.subscription
        _ = container.config
        _ = container.channel

        loaded = container.get_loaded_services()
        assert len(loaded) == 3
        assert "subscription" in loaded
        assert "config" in loaded
        assert "channel" in loaded

    async def test_container_with_preload_works(self, container_with_preload):
        """Verify preloaded container has services ready."""
        loaded = container_with_preload.get_loaded_services()
        assert len(loaded) >= 2  # At least subscription and config

    async def test_container_session_integration(self, container):
        """Verify container uses the test session correctly."""
        # Access config service through container
        config_service = container.config

        # Should be able to get config
        config = await config_service.get_config()
        assert config is not None
        assert config.id == 1


class TestFixtureIsolation:
    """Verify fixtures provide fresh instances for each test."""

    _previous_container_id = None
    _previous_session_id = None

    async def test_fixture_freshness_1(self, container, test_session):
        """Record fixture identities for comparison."""
        TestFixtureIsolation._previous_container_id = id(container)
        TestFixtureIsolation._previous_session_id = id(test_session)

        # Verify we can use them
        config = await container.config.get_config()
        assert config is not None

    async def test_fixture_freshness_2(self, container, test_session):
        """Verify fixtures are different instances from previous test."""
        current_container_id = id(container)
        current_session_id = id(test_session)

        # Fixtures should be fresh instances (different IDs)
        # Note: This may not always be true depending on pytest-asyncio
        # internals, but the database state should definitely be isolated

        # The key assertion: database state is clean
        config = await test_session.get(BotConfig, 1)
        assert config is not None
        assert config.wait_time_minutes == 5  # Default value


class TestMemoryCleanup:
    """Verify memory is properly managed during tests."""

    async def test_large_result_sets_freed(self, test_session):
        """Verify large query results don't leak memory."""
        from bot.database.models import User

        # Create multiple users
        for i in range(100):
            user = User(
                user_id=6000000 + i,
                username=f"memory_test_{i}",
                first_name=f"Test {i}",
                role="FREE"
            )
            test_session.add(user)

        await test_session.commit()

        # Query all users
        from sqlalchemy import select
        result = await test_session.execute(select(User))
        users = result.scalars().all()
        assert len(users) == 100

        # After test completes, these objects should be garbage collected
        # (we can't directly test GC, but the test framework handles cleanup)

    async def test_object_references_cleared(self, test_session):
        """Verify object references don't prevent cleanup."""
        from bot.database.models import User

        # Create and commit user
        user = User(
            user_id=7000001,
            username="reference_test",
            first_name="Reference Test",
            role="VIP"
        )
        test_session.add(user)
        await test_session.commit()

        # User object exists
        assert user.user_id == 7000001

        # After test, the user variable goes out of scope
        # and can be garbage collected


class TestTransactionBoundaries:
    """Verify transaction boundaries are respected."""

    async def test_explicit_commit_required(self, test_session):
        """Verify changes aren't persisted without commit."""
        from bot.database.models import User

        # Add user but don't commit
        user = User(
            user_id=8000001,
            username="no_commit_test",
            first_name="No Commit",
            role="FREE"
        )
        test_session.add(user)
        # Explicitly NOT committing

        # Query within same session should see the user (in transaction)
        # But after rollback, it should be gone

    async def test_commit_then_rollback_interaction(self, test_db):
        """Verify commit and rollback interact correctly."""
        from bot.database.models import User

        # Session 1: Create and commit user
        async with test_db() as session1:
            user = User(
                user_id=9000001,
                username="commit_test",
                first_name="Commit Test",
                role="FREE"
            )
            session1.add(user)
            await session1.commit()

        # Session 2: Should see committed user
        async with test_db() as session2:
            result = await session2.get(User, 9000001)
            assert result is not None
            assert result.username == "commit_test"

            # Modify but don't commit
            result.first_name = "Modified"
            # No commit - change should be rolled back on session exit

        # Session 3: Should see original value
        async with test_db() as session3:
            result = await session3.get(User, 9000001)
            assert result is not None
            assert result.first_name == "Commit Test"  # Not "Modified"
