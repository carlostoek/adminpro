"""
Database fixtures for testing.

Provides isolated in-memory database for each test.
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from bot.database.base import Base
from bot.database.models import BotConfig


@pytest_asyncio.fixture
async def test_db():
    """
    Fixture: Provides an isolated in-memory database for each test.

    Creates a new SQLite in-memory database, creates all tables,
    yields the session factory, then cleans up after the test.

    Yields:
        async_sessionmaker: Session factory bound to test database
    """
    # Create in-memory engine
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    # Create BotConfig singleton
    async with session_factory() as session:
        config = BotConfig(
            id=1,
            wait_time_minutes=5,
            vip_reactions=["🔥", "❤️"],
            free_reactions=["👍"],
            subscription_fees={"monthly": 10, "yearly": 100}
        )
        session.add(config)
        await session.commit()

    yield session_factory

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_db):
    """
    Fixture: Provides an isolated database session for a test.

    Uses nested transactions to ensure complete isolation:
    - Outer transaction is never committed
    - Inner transaction (test operations) is rolled back
    - Database is clean for each test

    Args:
        test_db: The test_db fixture (session factory)

    Yields:
        AsyncSession: Active database session with transaction isolation
    """
    async with test_db() as session:
        # Begin nested transaction (savepoint)
        # This allows us to rollback all changes made during the test
        await session.begin_nested()

        yield session

        # Rollback the nested transaction to discard all test changes
        await session.rollback()


@pytest_asyncio.fixture
async def test_engine():
    """
    Fixture: Provides an isolated database engine for each test.

    Creates a new SQLite in-memory engine with tables created.
    Useful for tests that need direct engine access.

    Yields:
        AsyncEngine: SQLAlchemy async engine bound to test database
    """
    from sqlalchemy.ext.asyncio import create_async_engine

    # Create in-memory engine
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()
