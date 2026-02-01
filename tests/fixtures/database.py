"""
Database fixtures for testing with in-memory SQLite.

Provides isolated, fast in-memory database for each test.
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from bot.database.base import Base
from bot.database.models import BotConfig, InvitationToken, User, SubscriptionPlan
from bot.database.enums import UserRole


@pytest_asyncio.fixture
async def test_db():
    """
    Fixture: Provides an isolated in-memory database for each test.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
        connect_args={"check_same_thread": False}
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA synchronous=NORMAL"))
        await conn.execute(text("PRAGMA foreign_keys=ON"))

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )

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

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_db):
    """
    Fixture: Provides an active database session for a test.
    """
    async with test_db() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_engine():
    """
    Fixture: Provides a raw database engine for tests.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def test_invitation_token(test_session):
    """
    Fixture: Creates a test invitation token.
    """
    token = InvitationToken(
        token="TEST_TOKEN_12345",
        generated_by=987654321,
        duration_hours=168
    )
    test_session.add(token)
    await test_session.commit()
    await test_session.refresh(token)
    return token


@pytest_asyncio.fixture
async def test_user(test_session):
    """
    Fixture: Creates a test user in the database.

    Creates a basic user with FREE role that can be used
    for tests requiring user_id foreign key.
    """
    user = User(
        user_id=12345,
        username="testuser",
        first_name="Test",
        last_name="User",
        role=UserRole.FREE
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_vip_user(test_session):
    """
    Fixture: Creates a test VIP user in the database.
    """
    user = User(
        user_id=12346,
        username="vipuser",
        first_name="VIP",
        last_name="User",
        role=UserRole.VIP
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_free_user(test_session):
    """
    Fixture: Creates a test Free user in the database.
    """
    user = User(
        user_id=12347,
        username="freeuser",
        first_name="Free",
        last_name="User",
        role=UserRole.FREE
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin_user(test_session):
    """
    Fixture: Creates a test admin user in the database.
    """
    user = User(
        user_id=1280444712,
        username="adminuser",
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_subscription_plan(test_session, test_admin_user):
    """
    Fixture: Creates an active subscription plan.

    Creates a standard monthly plan that can be used
    for tests requiring plan_id foreign key.
    """
    plan = SubscriptionPlan(
        name="Plan Mensual Test",
        duration_days=30,
        price=9.99,
        currency="USD",
        active=True,
        created_by=test_admin_user.user_id
    )
    test_session.add(plan)
    await test_session.commit()
    await test_session.refresh(plan)
    return plan


@pytest_asyncio.fixture
async def test_inactive_plan(test_session, test_admin_user):
    """
    Fixture: Creates an inactive subscription plan.

    Used for testing validation of inactive plans.
    """
    import random
    plan = SubscriptionPlan(
        name=f"Plan Inactivo Test {random.randint(1000, 9999)}",
        duration_days=30,
        price=9.99,
        currency="USD",
        active=False,
        created_by=test_admin_user.user_id
    )
    test_session.add(plan)
    await test_session.commit()
    await test_session.refresh(plan)
    return plan
