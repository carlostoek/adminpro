# Pitfalls Research: v1.2 Primer Despliegue - Migration & Deployment

**Domain:** Telegram Bot Migration to PostgreSQL + Railway Deployment + Redis Caching + Comprehensive Testing
**Researched:** 2026-01-28
**Confidence:** HIGH

## Executive Summary

Migrating a Telegram bot from SQLite to PostgreSQL, deploying to Railway, adding Redis caching, and building comprehensive test suites introduces critical risks around data corruption, deployment failures, cache invalidation bugs, and flaky tests. This research identifies pitfalls from real-world bot deployments and database migrations.

**Key Risk:** Migration failures cause data loss or corruption, deployment misconfigurations cause downtime, cache bugs cause stale data, and flaky tests hide real bugs. The complexity increases because these changes are interdependent - PostgreSQL migration affects tests, Redis affects caching logic, Railway affects environment configuration.

---

## Critical Pitfalls

### Pitfall 1: SQLite → PostgreSQL Schema Drift and Data Loss

**What goes wrong:**
SQLite's flexible typing and PostgreSQL's strict typing cause silent data corruption during migration:
```python
# SQLite: Allows this (flexible typing)
INSERT INTO vip_subscribers (user_id, expires_at) VALUES ('123', 'not-a-date')

# PostgreSQL: Rejects this (strict typing)
# ERROR: column "expires_at" is of type timestamp but expression is of type text
```

Worse - SQLite auto-creates columns that don't exist, PostgreSQL fails:
```python
# SQLite: Silently creates column if typo in name
session.query(VIPSubscriber).filter(VIPSuscriber.user_id == 123)  # Typo: Suscriber
# SQLite creates new column "vipsuscriber" with NULL values

# PostgreSQL: Fails fast
# ERROR: column "vipsuscriber" does not exist
```

**Why it happens:**
- SQLite uses **dynamic typing** (any value in any column)
- PostgreSQL uses **static typing** (strict type checking)
- SQLite has **partial ALTER TABLE support** (limited constraints)
- Development on SQLite doesn't catch type errors that production PostgreSQL will reject
- No migration testing environment before production

**How to avoid:**

1. **Enable SQLite strict mode during development:**
```python
# bot/database/engine.py
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

# Enable STRICT tables for SQLite (catch type errors early)
connect_args = {
    'check_same_thread': False,
    # Enable foreign key enforcement
    'foreign_keys': 'ON'
}

engine = create_engine(
    'sqlite:///bot.db',
    connect_args=connect_args,
    echo=False,  # Set True during migration to debug SQL
    poolclass=NullPool  # SQLite doesn't need connection pooling
)
```

2. **Use SQLAlchemy type checking in development:**
```python
# tests/test_database_types.py
import pytest
from datetime import datetime
from bot.database.models import VIPSubscriber

def test_vip_subscriber_types(session):
    """Ensure VIPSubscriber matches PostgreSQL types."""
    subscriber = VIPSubscriber(
        user_id=123,
        expires_at=datetime.utcnow(),
        subscription_type='vip'
    )
    session.add(subscriber)
    session.commit()

    # Verify types
    assert isinstance(subscriber.user_id, int)
    assert isinstance(subscriber.expires_at, datetime)
    assert isinstance(subscriber.subscription_type, str)

    # Test PostgreSQL will reject wrong types
    with pytest.raises(Exception):
        subscriber.expires_at = "not-a-date"
        session.commit()
```

3. **Create migration test suite:**
```python
# tests/test_migration.py
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from bot.database.base import Base
from bot.database.models import *

@pytest.fixture(scope="module")
def postgres_engine():
    """Test against PostgreSQL during migration."""
    engine = create_engine(
        "postgresql+asyncpg://test:test@localhost/test_db",
        echo=True
    )
    # Create all tables
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()

async def test_migration_to_postgres(postgres_engine):
    """Test that all models work with PostgreSQL."""
    # Try creating each model type
    async with AsyncSession(postgres_engine) as session:
        # Test VIPSubscriber
        subscriber = VIPSubscriber(
            user_id=123,
            expires_at=datetime.utcnow(),
            subscription_type='vip'
        )
        session.add(subscriber)
        await session.commit()

        # Test InvitationToken
        token = InvitationToken(
            token_str='test_token',
            generated_by=456,
            duration_hours=24
        )
        session.add(token)
        await session.commit()

        # Test BotConfig
        config = BotConfig(id=1, wait_time_minutes=10)
        session.add(config)
        await session.commit()
```

4. **Use pgloader with validation:**
```bash
# scripts/migrate_to_postgres.sh

#!/bin/bash
set -e  # Fail on any error

# Backup SQLite first
cp bot.db bot.db.backup.$(date +%Y%m%d_%H%M%S)

# Validate SQLite before migration
python -m scripts.validate_sqlite_schema

# Run pgloader with validation
pgloader \
  --verbose \
  --with "preload" \
  --with "create tables" \
  --with "create indexes" \
  --with "foreign keys" \
  --on-error-stop \
  sqlite:///bot.db \
  postgresql://user:pass@localhost/dbname

# Validate PostgreSQL after migration
python -m scripts.validate_postgres_schema

# Run data integrity checks
python -m scripts.validate_migration_integrity
```

5. **Add type validation to models:**
```python
# bot/database/models.py
from sqlalchemy import Column, Integer, DateTime, String, Boolean, event
from sqlalchemy.orm import validates
from datetime import datetime

class VIPSubscriber(Base):
    __tablename__ = "vip_subscribers"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    subscription_type = Column(String(20), nullable=False)

    @validates('user_id')
    def validate_user_id(self, key, user_id):
        if not isinstance(user_id, int):
            raise ValueError(f"user_id must be int, got {type(user_id)}")
        if user_id <= 0:
            raise ValueError(f"user_id must be positive, got {user_id}")
        return user_id

    @validates('expires_at')
    def validate_expires_at(self, key, expires_at):
        if not isinstance(expires_at, datetime):
            raise ValueError(f"expires_at must be datetime, got {type(expires_at)}")
        return expires_at

    @validates('subscription_type')
    def validate_subscription_type(self, key, subscription_type):
        valid_types = ['vip', 'free', 'admin']
        if subscription_type not in valid_types:
            raise ValueError(f"subscription_type must be one of {valid_types}")
        return subscription_type
```

**Warning signs:**
- Tests pass on SQLite but fail on PostgreSQL
- "Column does not exist" errors in production
- "Value too long for type" errors
- Silent data corruption (wrong data in columns)
- Foreign key constraint violations in production

**Phase to address:** Phase 1 (PostgreSQL Migration)

**Impact if ignored:** CRITICAL - Data corruption, production downtime, data loss

**Rollback strategy:**
1. Keep SQLite backup for at least 7 days
2. Create read-only PostgreSQL replica before cutover
3. Use feature flags to switch databases instantly
4. Have rollback script tested and ready

---

### Pitfall 2: Railway Deployment - Webhook Configuration Failures

**What goes wrong:**
Bot deployed to Railway but webhooks fail, bot receives no updates:
```python
# bot crashes on Railway with:
# RuntimeError: Webhook setup failed: HTTP/429 Too Many Requests

# Or worse - bot starts but receives NO updates
# (webhook URL wrong, or polling still enabled)
```

**Why it happens:**
- Railway generates dynamic URLs (not known until deployment)
- Webhook must be set AFTER deployment, not hardcoded
- aiogram default is polling, not webhooks
- Railway health checks fail if bot doesn't respond to /health
- Environment variables not set correctly
- PORT not bound correctly for webhooks

**How to avoid:**

1. **Dynamic webhook setup on Railway:**
```python
# bot/main.py
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import WebhookInfo

async def setup_webhook(bot: Bot):
    """Setup webhook dynamically based on environment."""
    railway_domain = os.getenv('RAILWAY_PUBLIC_DOMAIN')
    railway_port = os.getenv('PORT', '8080')

    if railway_domain:
        # Running on Railway - use webhooks
        webhook_url = f"https://{railway_domain}/webhook"
        webhook_path = "/webhook"

        # Get current webhook info
        current = await bot.get_webhook_info()
        if current.url != webhook_url:
            logger.info(f"Setting webhook to {webhook_url}")
            await bot.set_webhook(
                url=webhook_url,
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"]
            )
            logger.info("Webhook set successfully")
    else:
        # Running locally - use polling
        logger.info("No RAILWAY_PUBLIC_DOMAIN - using polling")

async def main():
    bot = Bot(
        token=os.getenv('BOT_TOKEN'),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Setup webhook or polling based on environment
    await setup_webhook(bot)

    railway_domain = os.getenv('RAILWAY_PUBLIC_DOMAIN')
    if railway_domain:
        # Start webhook server on Railway
        from aiogram.webhook.aiohttp_server import (
            SimpleRequestHandler,
            setup_application
        )

        app = web.Application()
        webhook_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot
        )
        webhook_handler.register(app, path="/webhook")

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(
            runner,
            host="0.0.0.0",
            port=int(os.getenv('PORT', '8080'))
        )
        await site.start()
        logger.info("Webhook server started")

        # Keep running
        try:
            await asyncio.Event().wait()
        finally:
            await runner.cleanup()
    else:
        # Start polling locally
        await dp.start_polling(bot)
```

2. **Add health check endpoint:**
```python
# bot/main.py
from aiohttp import web
from aiogram.types import BotCommand

async def health_check(request: web.Request):
    """Health check for Railway."""
    bot = request.app['bot']
    try:
        # Check bot is working
        me = await bot.get_me()
        return web.json_response({
            'status': 'healthy',
            'bot_id': me.id,
            'bot_username': me.username
        })
    except Exception as e:
        return web.json_response({
            'status': 'unhealthy',
            'error': str(e)
        }, status=503)

# In main() - add health check to web app
app = web.Application()
app['bot'] = bot
app.router.add_get('/health', health_check)
```

3. **Railway.toml configuration:**
```toml
# railway.toml
[build]
builder = "NIXPACKS"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

[[services]]
name = "bot"
serviceType = "web"
internalPort = 8080

[[services.ports]]
number = 8080
protocol = "TCP"

[[services.env]]
key = "PYTHON_VERSION"
value = "3.11"

[[services.env]]
key = "PORT"
value = "8080"
```

4. **Environment variable validation:**
```python
# bot/config.py
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    BOT_TOKEN: str
    DATABASE_URL: str
    REDIS_URL: Optional[str] = None
    RAILWAY_PUBLIC_DOMAIN: Optional[str] = None
    PORT: int = 8080

    @classmethod
    def from_env(cls):
        """Load config from environment with validation."""
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token:
            raise ValueError("BOT_TOKEN environment variable is required")

        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        return cls(
            BOT_TOKEN=bot_token,
            DATABASE_URL=database_url,
            REDIS_URL=os.getenv('REDIS_URL'),
            RAILWAY_PUBLIC_DOMAIN=os.getenv('RAILWAY_PUBLIC_DOMAIN'),
            PORT=int(os.getenv('PORT', '8080'))
        )

# In main.py - validate config early
try:
    config = Config.from_env()
except ValueError as e:
    logger.error(f"Configuration error: {e}")
    sys.exit(1)
```

**Warning signs:**
- Bot starts but doesn't respond to messages
- Railway logs show "No webhook set" or "Webhook failed"
- Health check returns 503
- Environment variables missing (crashes on startup)
- PORT not bound (connection refused)

**Phase to address:** Phase 2 (Railway Deployment)

**Impact if ignored:** CRITICAL - Bot deployed but non-functional, wasted deployment costs

**Rollback strategy:**
1. Keep bot running on old infrastructure until Railway is verified
2. Use Telegram's getWebhookInfo() to check webhook status
3. Have backup bot token ready for emergency switch
4. Railway supports instant rollback to previous deployment

---

### Pitfall 3: Redis Cache Invalidation - Stale Data Bugs

**What goes wrong:**
User's VIP status expires, but menu still shows VIP options due to cached data:
```python
# BAD: Cache never invalidated
async def get_vip_status(user_id: int) -> bool:
    # Check cache first
    cached = await redis.get(f"vip_status:{user_id}")
    if cached:
        return cached == "true"  # STALE! User expired 5 minutes ago

    # Check database
    is_vip = await subscription_service.is_vip_active(user_id)
    await redis.setex(f"vip_status:{user_id}", 3600, "true" if is_vip else "false")
    return is_vip

# User's VIP expires, but cache still says "true" for 1 hour
```

**Why it happens:**
- Cache TTL too long (expires_at changes but cache doesn't)
- No cache invalidation on writes (database updated, cache not cleared)
- Race conditions (cache written after database update)
- No cache versioning (stale cache served after deployment)
- Distributed cache issues (multiple bot instances with different cache)

**How to avoid:**

1. **Write-through caching with invalidation:**
```python
# bot/services/cache_service.py
from typing import Optional, Any
import json
import redis.asyncio as redis
from datetime import timedelta

class CacheService:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)

    async def get(self, key: str) -> Optional[Any]:
        """Get from cache, return None if miss."""
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None

    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set in cache with TTL."""
        await self.redis.setex(key, ttl, json.dumps(value))

    async def invalidate(self, pattern: str):
        """Invalidate all keys matching pattern."""
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

    async def get_vip_status(self, user_id: int, session: AsyncSession) -> bool:
        """Get VIP status with cache."""
        cache_key = f"vip_status:{user_id}"

        # Try cache first
        cached = await self.get(cache_key)
        if cached is not None:
            return cached['is_vip']

        # Cache miss - query database
        is_vip = await subscription_service.is_vip_active(session, user_id)

        # Cache result with shorter TTL (5 minutes)
        await self.set(cache_key, {'is_vip': is_vip}, ttl=300)
        return is_vip

    async def invalidate_user_cache(self, user_id: int):
        """Invalidate all cache for user when their data changes."""
        await self.invalidate(f"vip_status:{user_id}")
        await self.invalidate(f"user_role:{user_id}")
        await self.invalidate(f"user_permissions:{user_id}")

# In SubscriptionService - invalidate cache on writes
async def expire_vip_subscriber(session: AsyncSession, user_id: int, cache: CacheService):
    # Update database
    subscriber = await session.get(VIPSubscriber, user_id)
    if subscriber:
        subscriber.is_active = False
        await session.commit()

        # Invalidate cache
        await cache.invalidate_user_cache(user_id)
```

2. **Cache versioning for deployment safety:**
```python
# bot/services/cache_service.py
class CacheService:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.cache_version = os.getenv('CACHE_VERSION', 'v1')

    def _make_key(self, key: str) -> str:
        """Add cache version to key."""
        return f"{self.cache_version}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        value = await self.redis.get(self._make_key(key))
        # ... rest of get logic

    async def set(self, key: str, value: Any, ttl: int = 3600):
        await self.redis.setex(self._make_key(key), ttl, json.dumps(value))

    async def invalidate_all(self):
        """Invalidate ALL cache (useful after deployment)."""
        pattern = f"{self.cache_version}:*"
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

# In Railway deployment - bump CACHE_VERSION
# railway.toml or environment variables:
# CACHE_VERSION=v2  # Increment after deployment
```

3. **Cache stampede prevention:**
```python
# bot/services/cache_service.py
import asyncio

class CacheService:
    async def get_or_compute(
        self,
        key: str,
        compute_fn: callable,
        ttl: int = 3600,
        lock_timeout: int = 10
    ) -> Any:
        """Get from cache or compute, preventing cache stampede."""
        cache_key = self._make_key(key)

        # Try cache first
        cached = await self.get(cache_key)
        if cached is not None:
            return cached

        # Cache miss - acquire lock to prevent stampede
        lock_key = f"lock:{cache_key}"
        lock_acquired = await self.redis.set(
            lock_key, "1", nx=True, ex=lock_timeout
        )

        if lock_acquired:
            # We got the lock - compute and cache
            try:
                value = await compute_fn()
                await self.set(cache_key, value, ttl=ttl)
                return value
            finally:
                await self.redis.delete(lock_key)
        else:
            # Someone else is computing - wait and retry
            await asyncio.sleep(0.1)
            # Retry cache get (should be ready now)
            cached = await self.get(cache_key)
            if cached is not None:
                return cached

            # If still not ready, compute anyway
            return await compute_fn()
```

4. **Monitoring cache hit/miss ratios:**
```python
# bot/services/cache_service.py
from prometheus_client import Counter, Histogram

cache_hits = Counter('cache_hits_total', 'Total cache hits')
cache_misses = Counter('cache_misses_total', 'Total cache misses')
cache_errors = Counter('cache_errors_total', 'Total cache errors')

class CacheService:
    async def get(self, key: str) -> Optional[Any]:
        try:
            value = await self.redis.get(self._make_key(key))
            if value:
                cache_hits.inc()
                return json.loads(value)
            else:
                cache_misses.inc()
                return None
        except Exception as e:
            cache_errors.inc()
            logger.error(f"Cache get error: {e}")
            return None
```

**Warning signs:**
- Users see expired VIP menu after subscription ends
- Admin changes don't appear until cache expires
- High cache miss ratio (>30%)
- Cache stampede (many simultaneous queries for same key)
- Stale data after deployment

**Phase to address:** Phase 3 (Redis Caching)

**Impact if ignored:** HIGH - Confused users, security issues (stale permissions), poor UX

**Rollback strategy:**
1. Disable cache instantly with feature flag
2. Flush entire Redis cache: `FLUSHDB`
3. Bump CACHE_VERSION to invalidate all cache
4. Graceful degradation - if Redis fails, serve from database

---

### Pitfall 4: Async Test Flakiness - Event Loop Leaks

**What goes wrong:**
Tests pass individually but fail when run together:
```bash
$ pytest tests/test_subscription.py
✓ 15 passed

$ pytest tests/
✗ FAILED - async fixture never awaited
✗ FAILED - event loop is closed
✗ FAILED - coroutine was never awaited
```

**Why it happens:**
- pytest-asyncio event loop not properly scoped
- Background tasks from previous test still running
- Database sessions not closed properly
- Mock objects not cleaned up
- Test execution order dependencies

**How to avoid:**

1. **Proper pytest-asyncio configuration:**
```python
# tests/conftest.py
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from bot.database.base import Base
from bot.database.models import *

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',')

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def db_session():
    """Create fresh database session for each test."""
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    # Cleanup
    await engine.dispose()

@pytest.fixture(scope="function")
async def cleanup_tasks():
    """Ensure all background tasks are cleaned up after test."""
    yield

    # Cancel all pending tasks
    tasks = [task for task in asyncio.all_tasks() if not task.done()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
```

2. **Proper async test writing:**
```python
# tests/test_subscription.py
import pytest
from bot.services.subscription import SubscriptionService

@pytest.mark.asyncio
async def test_generate_vip_token(db_session: AsyncSession):
    """Test token generation - properly isolated."""
    # Arrange
    service = SubscriptionService(db_session, bot=None)

    # Act
    token = await service.generate_vip_token(
        generated_by=123,
        duration_hours=24
    )

    # Assert
    assert token is not None
    assert token.generated_by == 123
    assert token.duration_hours == 24
    assert len(token.token_str) > 10  # Tokens should be long enough

    # Cleanup is automatic - db_session fixture handles it
```

3. **Mock Telegram bot properly:**
```python
# tests/conftest.py
from unittest.mock import AsyncMock, MagicMock
from aiogram import Bot

@pytest.fixture
async def mock_bot():
    """Mock bot with async methods."""
    bot = AsyncMock(spec=Bot)
    bot.id = 123456
    bot.username = "test_bot"

    # Mock common bot methods
    async def mock_send_message(*args, **kwargs):
        mock_message = MagicMock()
        mock_message.message_id = 1
        mock_message.text = kwargs.get('text', '')
        return mock_message

    bot.send_message = mock_send_message
    bot.send_photo = mock_send_message
    bot.get_me = AsyncMock(return_value=MagicMock(id=123456, username="test_bot"))

    return bot

# Use in tests
@pytest.mark.asyncio
async def test_vip_notification(db_session: AsyncSession, mock_bot: Bot):
    """Test VIP notification with mocked bot."""
    service = SubscriptionService(db_session, mock_bot)
    # ... test code
```

4. **Avoid test order dependencies:**
```python
# tests/conftest.py
@pytest.fixture(scope="function", autouse=True)
async def isolate_tests(db_session: AsyncSession):
    """Isolate each test from others."""
    # Run before each test
    yield

    # Run after each test - rollback any changes
    await db_session.rollback()

    # Clear all tables
    async with db_session.begin():
        for table in reversed(Base.metadata.sorted_tables):
            await db_session.execute(table.delete())
```

5. **Use pytest-xdist for parallel test execution:**
```bash
# pytest.ini
[pytest]
testpaths = tests
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
addopts =
    -v
    --strict-markers
    --disable-warnings
    -p no:warnings

# Run tests in parallel
$ pytest -n auto  # Use all CPUs
```

**Warning signs:**
- Tests pass individually but fail together
- "Event loop is closed" errors
- "Coroutine was never awaited" warnings
- Flaky tests (sometimes pass, sometimes fail)
- Tests depend on execution order

**Phase to address:** Phase 4 (Comprehensive Testing)

**Impact if ignored:** HIGH - Flaky tests hide real bugs, slow development, broken CI

**Rollback strategy:**
1. Run tests with `-v` to see which tests fail
2. Use `--lf` (last failed) to rerun only failed tests
3. Isolate flaky test: run it alone to debug
4. Add `@pytest.mark.skip` to temporarily skip broken tests

---

### Pitfall 5: Alembic Auto-Migration Failures - Schema Drift

**What goes wrong:**
Auto-generated migrations don't match actual database state:
```bash
$ alembic revision --autogenerate -m "add vip_expiry_column"
INFO: Generating migration...
INFO: Detected NO changes

# But column doesn't exist in production!
# Or worse - migration tries to drop existing column
```

**Why it happens:**
- Manual schema changes in production without migration
- Development database out of sync with migration history
- Alembic can't detect all changes (renames, data migrations)
- Multiple developers create conflicting migrations
- Migration order dependencies

**How to avoid:**

1. **Never modify schema manually:**
```bash
# BAD: Direct schema change
psql> ALTER TABLE vip_subscribers ADD COLUMN new_column TEXT;

# GOOD: Always use Alembic
alembic revision -m "add new_column to vip_subscribers"
# Edit generated migration file
alembic upgrade head
```

2. **Validate migrations before committing:**
```python
# scripts/validate_migration.py
import asyncio
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

async def validate_migration():
    """Validate that migration matches expected changes."""
    # 1. Check migration file was created
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    revisions = list(script.walk_revisions())

    if not revisions:
        print("❌ No migration found!")
        return False

    latest_revision = revisions[0]
    print(f"✓ Found migration: {latest_revision.doc}")

    # 2. Test migration on fresh database
    engine = create_engine("postgresql://test:test@localhost/test_db")
    inspector = inspect(engine)

    # Get schema before migration
    before_tables = set(inspector.get_table_names())

    # Run migration
    from alembic import command
    command.upgrade(config, 'head')

    # Get schema after migration
    after_tables = set(inspector.get_table_names())

    # Compare
    new_tables = after_tables - before_tables
    print(f"✓ Migration adds {len(new_tables)} tables")

    return True

if __name__ == "__main__":
    asyncio.run(validate_migration())
```

3. **Migration testing script:**
```bash
# scripts/test_migration.sh

#!/bin/bash
set -e

echo "Testing migration on fresh database..."

# Drop test database if exists
psql -c "DROP DATABASE IF EXISTS test_migration_db"

# Create fresh database
psql -c "CREATE DATABASE test_migration_db"

# Run migration
DATABASE_URL="postgresql://test:test@localhost/test_migration_db" \
  alembic upgrade head

# Validate schema
python -m scripts.validate_migration

echo "✓ Migration test passed"

# Rollback
alembic downgrade base

echo "✓ Rollback test passed"
```

4. **Data migration best practices:**
```python
# alembic/versions/001_add_subscription_type.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Step 1: Add column (nullable)
    op.add_column('vip_subscribers',
        sa.Column('subscription_type', sa.String(20), nullable=True)
    )

    # Step 2: Migrate data
    from sqlalchemy.sql import table, column
    vip_subscribers = table('vip_subscribers',
        column('id', sa.Integer),
        column('subscription_type', sa.String(20))
    )

    op.execute(
        vip_subscribers.update()
        .values(subscription_type='vip')
    )

    # Step 3: Make column non-nullable
    op.alter_column('vip_subscribers',
        'subscription_type',
        nullable=False
    )

def downgrade():
    op.drop_column('vip_subscribers', 'subscription_type')
```

5. **Migration conflict resolution:**
```bash
# When two developers create migrations with same number
# alembic/versions/
#   001_add_column.py (Developer A)
#   001_add_index.py (Developer B)  # CONFLICT!

# Solution: Rebase and rename
git checkout main
git pull

# Rename Developer B's migration to 002
mv 001_add_index.py 002_add_index.py

# Update revision dependencies in 002_add_index.py
# downgrade_revision = '001_add_column_id'
```

**Warning signs:**
- `alembic current` doesn't match production schema
- Migration files accumulate but "Detected NO changes"
- Manual schema changes in production
- Migration history has conflicts
- `alembic upgrade head` fails in production

**Phase to address:** Phase 1 (PostgreSQL Migration) + Ongoing

**Impact if ignored:** CRITICAL - Production schema drift, broken migrations, data loss

**Rollback strategy:**
1. Always test migrations on staging first
2. Keep production database backup before migration
3. Use `alembic downgrade one` to rollback last migration
4. Have rollback migration (downgrade()) tested and ready

---

### Pitfall 6: Connection Pool Exhaustion - asyncpg Pool Leaks

**What goes wrong:**
Bot deployed to Railway, but after 1 hour crashes with:
```python
sqlalchemy.exc.DBAPIError: (sqlalchemy.dialects.postgresql.asyncpg.InterfaceError)
connection pool exhausted
```

**Why it happens:**
- Database connections not properly closed
- Connection pool size too small for concurrent requests
- Long-running queries holding connections
- Connection leaks (sessions not committed/rolled back)
- asyncpg pool not configured for Railway's connection limits

**How to avoid:**

1. **Proper asyncpg pool configuration:**
```python
# bot/database/engine.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

def create_engine(database_url: str):
    """Create async engine with proper pool configuration."""
    # Parse connection string
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

    # Configure pool for Railway
    # Railway Postgres: Max 100 connections (Hobby plan)
    engine = create_async_engine(
        database_url,
        echo=False,  # Set True to debug SQL
        pool_size=10,  # Number of connections to maintain
        max_overflow=20,  # Additional connections when needed
        pool_timeout=30,  # Wait 30s for connection
        pool_recycle=3600,  # Recycle connections after 1 hour
        pool_pre_ping=True,  # Test connections before using
        connect_args={
            "server_settings": {"jit": "off"},  # Disable JIT for faster queries
            "timeout": 10  # Connection timeout
        }
    )

    return engine

# Usage
engine = create_engine(os.getenv('DATABASE_URL'))
async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

2. **Proper session lifecycle management:**
```python
# bot/middlewares/database.py
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, session_maker):
        super().__init__()
        self.session_maker = session_maker

    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: dict
    ):
        # Create session
        async with self.session_maker() as session:
            # Inject into handler data
            data['session'] = session

            try:
                # Run handler
                result = await handler(event, data)

                # Commit if handler succeeded
                await session.commit()

                return result
            except Exception as e:
                # Rollback on error
                await session.rollback()
                raise e
            finally:
                # Session automatically closed by context manager
                # No need for explicit session.close()
                pass
```

3. **Monitor connection pool health:**
```python
# bot/services/health.py
from sqlalchemy.ext.asyncio import AsyncEngine
from prometheus_client import Gauge

db_pool_size = Gauge('db_pool_size', 'Database pool size')
db_pool_overflow = Gauge('db_pool_overflow', 'Database pool overflow')
db_pool_checkedout = Gauge('db_pool_checkedout', 'Database connections checked out')

async def check_db_health(engine: AsyncEngine) -> dict:
    """Check database connection pool health."""
    pool = engine.pool

    return {
        'pool_size': pool.size(),
        'checked_out': pool.checkedout(),
        'overflow': pool.overflow(),
        'status': 'healthy' if pool.checkedout() < pool.size() + pool.max_overflow else 'exhausted'
    }

# Log pool status every 5 minutes
@repeat_every(seconds=300)
async def log_pool_status(engine: AsyncEngine):
    status = await check_db_health(engine)
    logger.info(f"DB Pool: {status}")

    # Update metrics
    db_pool_size.set(status['pool_size'])
    db_pool_overflow.set(status['overflow'])
    db_pool_checkedout.set(status['checked_out'])

    if status['status'] == 'exhausted':
        logger.error(f"⚠️ DB Pool exhausted! {status}")
```

4. **Connection leak detection:**
```python
# tests/test_connection_leaks.py
import pytest
from sqlalchemy import text

@pytest.mark.asyncio
async def test_no_connection_leaks(db_session, engine):
    """Ensure no connections are leaked."""
    # Get initial pool status
    pool = engine.pool
    initial_checkedout = pool.checkedout()

    # Run some database operations
    for i in range(100):
        subscriber = VIPSubscriber(
            user_id=i,
            expires_at=datetime.utcnow(),
            subscription_type='vip'
        )
        db_session.add(subscriber)
        await db_session.commit()

    # Check pool status - should be same as initial
    final_checkedout = pool.checkedout()
    assert final_checkedout == initial_checkedout, \
        f"Connection leak! Initial: {initial_checkedout}, Final: {final_checkedout}"
```

**Warning signs:**
- "connection pool exhausted" errors
- Database response time increases over time
- Railway Postgres metrics show max connections
- Bot crashes after running for hours
- Slow queries (>1s) holding connections

**Phase to address:** Phase 1 (PostgreSQL Migration) + Phase 2 (Railway Deployment)

**Impact if ignored:** CRITICAL - Bot crashes, database unavailable, poor performance

**Rollback strategy:**
1. Restart bot to clear connection pool
2. Increase pool_size temporarily
3. Kill long-running queries in PostgreSQL
4. Fallback to SQLite if PostgreSQL unavailable (feature flag)

---

## Moderate Pitfalls

### Pitfall 7: Railway Environment Variables Not Set

**What goes wrong:**
Bot deployed to Railway but crashes on startup:
```python
ValueError: BOT_TOKEN environment variable is required
```

**Why it happens:**
- Environment variables not added to Railway project
- Variables added to wrong environment (staging vs production)
- Variable names mismatched (BOT_TOKEN vs TELEGRAM_BOT_TOKEN)
- Secrets not committed (correct) but not added to Railway (incorrect)

**How to avoid:**

1. **Environment variable validation at startup:**
```python
# bot/config.py
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    BOT_TOKEN: str
    DATABASE_URL: str
    REDIS_URL: Optional[str] = None
    RAILWAY_PUBLIC_DOMAIN: Optional[str] = None

    @classmethod
    def from_env(cls) -> 'Config':
        """Load and validate environment variables."""
        required_vars = {
            'BOT_TOKEN': os.getenv('BOT_TOKEN'),
            'DATABASE_URL': os.getenv('DATABASE_URL')
        }

        missing = [k for k, v in required_vars.items() if not v]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Please set them in Railway dashboard or .env file"
            )

        return cls(
            BOT_TOKEN=required_vars['BOT_TOKEN'],
            DATABASE_URL=required_vars['DATABASE_URL'],
            REDIS_URL=os.getenv('REDIS_URL'),
            RAILWAY_PUBLIC_DOMAIN=os.getenv('RAILWAY_PUBLIC_DOMAIN')
        )

# In main.py - validate config early
try:
    config = Config.from_env()
    logger.info("✓ Configuration loaded successfully")
except ValueError as e:
    logger.error(f"❌ Configuration error: {e}")
    sys.exit(1)
```

2. **Railway environment variable template:**
```bash
# .env.railway.template - Add to Railway dashboard
BOT_TOKEN=your_bot_token_here
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
RAILWAY_PUBLIC_DOMAIN=${{RAILWAY_PUBLIC_DOMAIN}}
CACHE_VERSION=v1

# Copy this to Railway dashboard and replace values
```

3. **Pre-startup validation script:**
```python
# scripts/validate_env.py
import os
import sys

def validate_env():
    """Validate all required environment variables."""
    required = {
        'BOT_TOKEN': 'Telegram bot token from @BotFather',
        'DATABASE_URL': 'PostgreSQL connection string',
    }

    optional = {
        'REDIS_URL': 'Redis connection string (optional)',
        'RAILWAY_PUBLIC_DOMAIN': 'Railway public domain (auto-set by Railway)',
    }

    print("Checking required environment variables...")
    missing = []
    for var, description in required.items():
        value = os.getenv(var)
        if value:
            print(f"✓ {var} is set")
        else:
            print(f"❌ {var} is missing ({description})")
            missing.append(var)

    print("\nChecking optional environment variables...")
    for var, description in optional.items():
        value = os.getenv(var)
        if value:
            print(f"✓ {var} is set")
        else:
            print(f"⚠️  {var} is not set ({description}) - optional")

    if missing:
        print(f"\n❌ Missing required variables: {', '.join(missing)}")
        return False

    print("\n✓ All required environment variables are set")
    return True

if __name__ == "__main__":
    if not validate_env():
        sys.exit(1)
```

**Phase to address:** Phase 2 (Railway Deployment)

**Impact if ignored:** HIGH - Bot won't start, deployment failure

---

### Pitfall 8: Redis Connection Failures - No Graceful Degradation

**What goes wrong:**
Redis goes down, bot crashes:
```python
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Why it happens:**
- No error handling for Redis connection failures
- Cache service blocks entire bot if Redis is down
- No fallback to database when cache unavailable
- Railway Redis service restarts (maintenance)

**How to avoid:**

1. **Graceful degradation in cache service:**
```python
# bot/services/cache_service.py
import logging
from typing import Optional, Any
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis = None
        self._enabled = True

    async def connect(self):
        """Connect to Redis with error handling."""
        try:
            self.redis = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.redis.ping()
            logger.info("✓ Redis connected successfully")
            self._enabled = True
        except Exception as e:
            logger.warning(f"⚠️  Redis connection failed: {e}")
            logger.warning("Cache disabled - using database only")
            self._enabled = False
            self.redis = None

    async def get(self, key: str) -> Optional[Any]:
        """Get from cache, return None if Redis unavailable."""
        if not self._enabled or not self.redis:
            return None

        try:
            value = await self.redis.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set in cache, ignore errors."""
        if not self._enabled or not self.redis:
            return

        try:
            await self.redis.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            # Don't crash - just log and continue
            pass

    async def invalidate_user_cache(self, user_id: int):
        """Invalidate cache, ignore errors."""
        if not self._enabled or not self.redis:
            return

        try:
            await self.redis.delete(f"vip_status:{user_id}")
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
```

2. **Circuit breaker for Redis:**
```python
# bot/services/cache_service.py
from datetime import datetime, timedelta

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout_seconds=60):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = datetime.utcnow()

        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failures} failures")

    def record_success(self):
        self.failures = 0
        self.state = "closed"

    def allow_request(self) -> bool:
        if self.state == "closed":
            return True

        if self.state == "open":
            if (datetime.utcnow() - self.last_failure_time).total_seconds() > self.timeout_seconds:
                self.state = "half-open"
                logger.info("Circuit breaker half-open - testing connection")
                return True
            return False

        return True

class CacheService:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.circuit_breaker = CircuitBreaker()

    async def get(self, key: str) -> Optional[Any]:
        if not self.circuit_breaker.allow_request():
            return None

        try:
            value = await self.redis.get(key)
            self.circuit_breaker.record_success()
            return json.loads(value) if value else None
        except Exception as e:
            self.circuit_breaker.record_failure()
            return None
```

**Phase to address:** Phase 3 (Redis Caching)

**Impact if ignored:** MEDIUM - Bot crashes when Redis unavailable, poor reliability

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| **Phase 1: PostgreSQL Migration** | Schema drift, data type incompatibilities | Validate types on SQLite, test migration on staging, use pgloader with validation |
| **Phase 2: Railway Deployment** | Webhook misconfiguration, missing env vars | Dynamic webhook setup, env validation, health check endpoint |
| **Phase 3: Redis Caching** | Stale cache, cache stampede, Redis failures | Write-through caching, invalidation on writes, graceful degradation |
| **Phase 4: Comprehensive Testing** | Flaky async tests, event loop leaks | Proper pytest-asyncio config, cleanup fixtures, proper session management |
| **Phase 5: Auto-Migration** | Auto-generated migrations wrong | Never manual schema changes, validate migrations, test on fresh DB |
| **Phase 6: Performance Optimization** | N+1 queries, connection pool exhaustion | Use selectinload, monitor pool health, configure pool correctly |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **SQLite → PostgreSQL** | Assume same SQL dialect works | Test all queries on PostgreSQL, check type compatibility |
| **aiogram + Railway** | Use polling instead of webhooks | Use webhooks on Railway, dynamic webhook setup |
| **Redis + SQLAlchemy** | Cache never invalidated | Invalidate cache on writes, use shorter TTLs |
| **pytest-asyncio + aiogram** | Event loop not scoped | Use event_loop fixture, cleanup tasks after tests |
| **Alembic + Railway** | Migration fails in production | Test migrations on staging, keep backups ready |
| **asyncpg + Railway Postgres** | Connection pool exhausted | Configure pool_size, monitor pool health, recycle connections |

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| **Data corruption during migration** | CRITICAL | 1. Stop all writes<br>2. Restore from SQLite backup<br>3. Fix migration script<br>4. Test on staging<br>5. Retry migration |
| **Railway deployment fails** | MEDIUM | 1. Check Railway logs<br>2. Validate env vars<br>3. Test webhook URL<br>4. Rollback to previous deployment<br>5. Fix and redeploy |
| **Redis cache stale data** | LOW | 1. Flush Redis cache: `FLUSHDB`<br>2. Bump CACHE_VERSION<br>3. Restart bot<br>4. Monitor cache hit ratios |
| **Flaky tests blocking CI** | MEDIUM | 1. Isolate flaky test: `pytest tests/test_failing.py::test_func -v`<br>2. Run test alone to debug<br>3. Add proper cleanup<br>4. Skip test temporarily: `@pytest.mark.skip` |
| **Migration fails in production** | CRITICAL | 1. Stop bot to prevent writes<br>2. Run `alembic downgrade one`<br>3. Fix migration script<br>4. Test on staging<br>5. Retry upgrade |
| **Connection pool exhausted** | HIGH | 1. Restart bot to clear pool<br>2. Kill long-running queries<br>3. Increase pool_size<br>4. Add connection leak detection |

---

## Pre-Deployment Checklist

### Before PostgreSQL Migration

- [ ] All tests pass on PostgreSQL (not just SQLite)
- [ ] Migration tested on staging database
- [ ] SQLite backup created and verified
- [ ] Rollback plan documented and tested
- [ ] Data integrity checks written and passing
- [ ] Type validation added to all models
- [ ] Foreign key constraints tested

### Before Railway Deployment

- [ ] All environment variables documented
- [ ] Health check endpoint working (`/health`)
- [ ] Webhook setup tested locally
- [ ] Logging configured and tested
- [ ] Database connection pool configured
- [ ] Redis connection with graceful degradation
- [ ] Deployment tested on staging

### Before Enabling Redis Cache

- [ ] Cache invalidation tested (write-through)
- [ ] Graceful degradation working (Redis down = bot still works)
- [ ] Cache hit/miss monitoring configured
- [ ] CACHE_VERSION bump mechanism tested
- [ ] Cache stampede prevention tested
- [ ] TTL values reviewed (not too long)

### Before Expanding Test Suite

- [ ] pytest-asyncio properly configured
- [ ] Event loop cleanup working
- [ ] Database session cleanup tested
- [ ] Mock bot properly implemented
- [ ] Tests can run in parallel (`pytest -n auto`)
- [ ] No test order dependencies

---

## Sources

- [How to migrate from SQLite to PostgreSQL](https://render.com/articles/how-to-migrate-from-sqlite-to-postgresql) — Migration pitfalls (HIGH confidence)
- [Django + Redis Caching: Patterns, Pitfalls, and Real-World Lessons](https://dev.to/topunix/django-redis-caching-patterns-pitfalls-and-real-world-lessons-m7o) — Cache invalidation strategies (MEDIUM confidence)
- [Railway Webhooks Documentation](https://docs.railway.com/guides/webhooks) — Webhook setup on Railway (HIGH confidence)
- [7 Hidden SQLAlchemy Performance Traps](https://python.plainenglish.io/7-hidden-sqlalchemy-performance-traps-secretly-destroying-your-production-database-performance-729e5cab6a68) — N+1 queries and connection leaks (HIGH confidence)
- [pytest-asyncio Issue #1114 - Flaky async fixture tests](https://github.com/pytest-dev/pytest-asyncio/issues/1114) — Event loop management (HIGH confidence)
- [Best Practices for Alembic Schema Migration](https://www.pingcap.com/article/best-practices-alembic-schema-migration/) — Alembic pitfalls (HIGH confidence)
- [What is a Cache Stampede? How to Prevent It Using Redis](https://slaknoah.com/blog/what-is-a-cache-stampede-how-to-prevent-it-using-redis) — Cache stampede prevention (MEDIUM confidence)
- [Boost Your App Performance With Asyncpg and PostgreSQL](https://www.tigerdata.com/blog/how-to-build-applications-with-asyncpg-and-postgresql) — Connection pooling (MEDIUM confidence)
- [Asynchronous SQLAlchemy 2: A simple step-by-step guide](https://dev.to/amverum/asynchronous-sqlalchemy-2-a-simple-step-by-step-guide-to-configuration-models-relationships-and-3ob3) — Async configuration (HIGH confidence)
- [python-telegram-bot Test Suite Maintenance](https://github.com/python-telegram-bot/python-telegram-bot/issues/4324) — Test flakiness patterns (MEDIUM confidence)

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| PostgreSQL Migration | HIGH | Verified with official docs and migration guides |
| Railway Deployment | HIGH | Official Railway docs + deployment guides |
| Redis Caching | MEDIUM | Community patterns, need production validation |
| Async Testing | HIGH | pytest-asyncio issues documented, patterns clear |
| Alembic Migrations | HIGH | Official docs + best practice guides |
| Connection Pooling | MEDIUM | asyncpg docs, but pool configuration varies by workload |

---

## Gaps to Address

- **Redis caching patterns**: Need production data on optimal TTL values
- **Railway performance**: No benchmarks for aiogram on Railway (test during deployment)
- **Migration testing tools**: Need to evaluate pgloader vs custom scripts
- **Test coverage targets**: Industry standard for async bot tests unclear (aim for 80%+)
- **Cache monitoring**: Need production metrics on cache hit ratios

---

*Pitfalls research for: v1.2 Primer Despliegue (Migration & Deployment)*
*Researched: 2026-01-28*
*Confidence: HIGH (based on official docs + community patterns)*
