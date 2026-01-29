"""
Database fixtures for testing with in-memory SQLite.

Provides isolated, fast in-memory database for each test.
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from bot.database.base import Base
from bot.database.models import BotConfig, VIPSubscriber, InvitationToken, FreeChannelRequest


@pytest_asyncio.fixture
async def test_db():
    """
    Fixture: Provides an isolated in-memory database for each test.

    Creates a new SQLite in-memory database with:
    - All tables created from Base.metadata
    - BotConfig singleton pre-populated (id=1)
    - WAL mode enabled for better concurrency
    - Foreign keys enforced

    Yields:
        async_sessionmaker: Session factory bound to test database

    Example:
        async def test_example(test_db):
            async with test_db() as session:
                # Use session for database operations
                pass
    """
    # Create in-memory engine with aiosqlite
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
        connect_args={
            "check_same_thread": False,  # Required for async
        }
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Enable WAL mode for better concurrency
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA synchronous=NORMAL"))
        await conn.execute(text("PRAGMA foreign_keys=ON"))

    # Create session factory
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )

    # Create BotConfig singleton with test defaults
    async with session_factory() as session:
        config = BotConfig(
            id=1,
            vip_channel_id="-1001234567890",
            free_channel_id="-1000987654321",
            wait_time_minutes=5,
            vip_reactions=["🔥", "❤️", "😍"],
            free_reactions=["👍", "🙏"],
            subscription_fees={"monthly": 10.0, "yearly": 100.0}
        )
        session.add(config)
        await session.commit()

    yield session_factory

    # Cleanup: Drop all tables and dispose engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_db):
    """
    Fixture: Provides an active database session for a test.

    The session is automatically rolled back after the test to ensure
    test isolation - no data persists between tests.

    Args:
        test_db: The test_db fixture (session factory)

    Yields:
        AsyncSession: Active database session with active transaction

    Example:
        async def test_with_session(test_session):
            config = await test_session.get(BotConfig, 1)
            assert config.wait_time_minutes == 5
    """
    async with test_db() as session:
        yield session
        # Rollback ensures no data persists after test
        await session.rollback()


@pytest_asyncio.fixture
async def test_engine():
    """
    Fixture: Provides a raw database engine for tests that need it.

    Useful for tests that need to execute raw SQL or manage their own
    sessions.

    Yields:
        AsyncEngine: SQLAlchemy async engine

    Example:
        async def test_raw_sql(test_engine):
            async with test_engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
    """
    from sqlalchemy.ext.asyncio import AsyncEngine

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


# ============================================================================
# MODEL-SPECIFIC FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def test_vip_subscriber(test_session):
    """
    Fixture: Creates a test VIP subscriber.

    Returns:
        VIPSubscriber: Created subscriber instance
    """
    from datetime import datetime, timedelta

    subscriber = VIPSubscriber(
        user_id=123456789,
        username="test_vip_user",
        expires_at=datetime.utcnow() + timedelta(days=30),
        status="active"
    )
    test_session.add(subscriber)
    await test_session.commit()
    await test_session.refresh(subscriber)
    return subscriber


@pytest_asyncio.fixture
async def test_invitation_token(test_session):
    """
    Fixture: Creates a test invitation token.

    Returns:
        InvitationToken: Created token instance
    """
    from datetime import datetime, timedelta

    token = InvitationToken(
        token="TEST_TOKEN_12345",
        generated_by=987654321,
        expires_at=datetime.utcnow() + timedelta(hours=24),
        is_used=False,
        duration_hours=168  # 7 days
    )
    test_session.add(token)
    await test_session.commit()
    await test_session.refresh(token)
    return token


@pytest_asyncio.fixture
async def test_free_request(test_session):
    """
    Fixture: Creates a test free channel request.

    Returns:
        FreeChannelRequest: Created request instance
    """
    from datetime import datetime

    request = FreeChannelRequest(
        user_id=111222333,
        username="test_free_user",
        requested_at=datetime.utcnow(),
        status="pending"
    )
    test_session.add(request)
    await test_session.commit()
    await test_session.refresh(request)
    return request
