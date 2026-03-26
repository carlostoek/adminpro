# Architecture Research: v1.2 Primer Despliegue - Deployment, Testing, Performance

**Domain:** Telegram Bot - Production Deployment Infrastructure
**Researched:** 2026-01-28
**Confidence:** HIGH

## Executive Summary

The v1.2 milestone adds production deployment infrastructure (Railway), PostgreSQL migration, Redis caching, health monitoring, and comprehensive testing to the existing aiogram/SQLAlchemy bot. The architecture maintains the existing ServiceContainer pattern while introducing new services (CacheService, MigrationService, HealthCheckService) and a database abstraction layer for SQLite/PostgreSQL switching.

**Key Architecture Changes:**
1. **Database Abstraction Layer** - Switch between SQLite (local) and PostgreSQL (production) via `DATABASE_URL`
2. **Redis Integration** - FSM storage + CacheService for frequently accessed data
3. **Health Check Endpoint** - FastAPI alongside bot for monitoring ( Railway health checks)
4. **Migration System** - Alembic for schema versioning
5. **Test Architecture** - pytest-asyncio with fixtures mocking database/bot

**Critical Integration Points:**
- ServiceContainer adds 3 new services (cache, migration, health)
- All existing services remain unchanged (backward compatible)
- Database engine factory detects dialect from `DATABASE_URL` protocol
- FSM storage pluggable (MemoryStorage vs RedisStorage)

---

## Recommended Architecture

### System Overview with v1.2 Additions

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DEPLOYMENT LAYER                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │   Railway App    │  │  PostgreSQL DB   │  │  Redis Cache     │  │
│  │  (Python 3.11)   │  │  (Production)    │  │  (FSM + Data)    │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
└───────────┼────────────────────┼─────────────────────┼─────────────┘
            │                    │                     │
            ▼                    ▼                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    HEALTH & MONITORING LAYER                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  FastAPI Health Check Endpoint (port 8001)                   │   │
│  │  GET /health → { bot: "ok", db: "ok", redis: "ok" }         │   │
│  │  Railway pings this endpoint for service health              │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         APPLICATION LAYER                            │
│  ┌─────────────────────┐  ┌──────────────────────────────────────┐  │
│  │  aiogram Bot        │  │  Background Tasks (APScheduler)      │  │
│  │  Dispatcher         │  │  - Token expiry cleanup              │  │
│  │  FSM Storage        │  │  - Free queue processing             │  │
│  │  (Redis or Memory)  │  │  - Cache warming                     │  │
│  └──────────┬──────────┘  └──────────────────────────────────────┘  │
└─────────────┼────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     SERVICE CONTAINER (DI)                           │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐           │
│  │ Existing  │ │  NEW v1.2 │ │ Existing  │ │  NEW v1.2 │           │
│  │ Services  │ │ Services  │ │ Services  │ │ Services  │           │
│  ├───────────┤ ├───────────┤ ├───────────┤ ├───────────┤           │
│  │Subscrip.  │ │Cache      │ │Channel    │ │Migration  │           │
│  │Config     │ │Health     │ │RoleDetect │ │           │           │
│  │Content    │ │           │ │Interest   │ │           │           │
│  │UserMgmt   │ │           │ │VIPEntry   │ │           │           │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘           │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      DATABASE ABSTRACTION LAYER                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Engine Factory (dialect detection)                         │   │
│  │  - sqlite+aiosqlite:///bot.db  → SQLite + aiosqlite         │   │
│  │  - postgresql+asyncpg://...   → PostgreSQL + asyncpg        │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                    ↓                                 │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Alembic Migrations (version control)                        │   │
│  │  - versions/ directory with migration scripts                │   │
│  │  - alembic upgrade head                                       │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA STORAGE                                 │
│  ┌──────────────────────┐  ┌──────────────────────────────────────┐ │
│  │  SQLite (Local Dev)  │  │  PostgreSQL (Railway Production)     │ │
│  │  - WAL mode          │  │  - Connection pooling                 │ │
│  │  - Single instance   │  │  - Multi-instance safe               │ │
│  └──────────────────────┘  └──────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| **Railway App** | Container orchestration, environment variables, health checks | PostgreSQL, Redis, FastAPI health endpoint |
| **FastAPI Health Check** | HTTP endpoint for Railway monitoring, component health probes | Bot (status), DB (ping), Redis (ping) |
| **CacheService** | Cache get/set/delete, TTL management, cache warming | Redis (storage), existing services (cache layer) |
| **MigrationService** | Run Alembic migrations, version tracking, rollback support | Alembic CLI, database engine |
| **Engine Factory** | Create async engine based on DATABASE_URL protocol | SQLAlchemy core, database drivers (aiosqlite/asyncpg) |
| **Redis FSM Storage** | Persist FSM state across restarts, multi-instance support | aiogram Dispatcher, Redis backend |
| **pytest-asyncio Fixtures** | Mock database, bot, sessions for isolated tests | Test suites, test database |

---

## Project Structure with v1.2 Additions

### Current Structure (v1.1)

```
bot/
├── handlers/              # Command and menu handlers
├── services/              # Business logic (12 services)
├── database/              # Models, engine, session
├── middlewares/           # DI, auth, role detection
├── states/                # FSM state definitions
├── utils/                 # Helpers, keyboards, formatters
├── background/            # APScheduler tasks
└── __init__.py
```

### Proposed Structure (v1.2 - Additions Only)

```
.
├── api/                           # NEW: Health check API
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entry point
│   ├── routes/
│   │   ├── __init__.py
│   │   └── health.py             # GET /health endpoint
│   └── dependencies.py           # Shared dependencies (bot, db, redis)
│
├── bot/
│   ├── services/
│   │   ├── cache.py              # NEW: CacheService
│   │   ├── health.py             # NEW: HealthCheckService
│   │   ├── migration.py          # NEW: MigrationService
│   │   └── container.py          # UPDATE: Add cache, health, migration properties
│   │
│   ├── database/
│   │   ├── engine.py             # UPDATE: Dialect detection logic
│   │   ├── factory.py            # NEW: Engine factory abstraction
│   │   └── base.py               # (unchanged)
│   │
│   └── storage/                  # NEW: FSM storage abstraction
│       ├── __init__.py
│       ├── memory.py             # MemoryStorage wrapper
│       └── redis.py              # RedisStorage wrapper
│
├── alembic/                      # NEW: Database migrations
│   ├── versions/
│   │   └── 001_initial.py        # Initial schema migration
│   ├── env.py                    # Alembic environment config
│   ├── script.py.mako            # Migration template
│   └── alembic.ini               # Alembic configuration
│
├── tests/                        # NEW: Comprehensive test suite
│   ├── __init__.py
│   ├── conftest.py               # pytest fixtures
│   ├── unit/                     # Unit tests
│   │   ├── test_services/
│   │   ├── test_middlewares/
│   │   └── test_utils/
│   ├── integration/              # Integration tests
│   │   ├── test_database/
│   │   ├── test_cache/
│   │   └── test_handlers/
│   ├── e2e/                      # End-to-end tests
│   │   ├── test_vip_flow.py
│   │   └── test_admin_flow.py
│   └── performance/              # Performance benchmarks
│       └── test_cache_hit_rate.py
│
├── railway.toml                  # NEW: Railway deployment config
├── Dockerfile                    # NEW: Container definition
├── .railway/                     # NEW: Railway-specific configs
│   └── nixpacks.toml             # Build configuration
│
├── scripts/                      # UPDATE: Add migration scripts
│   ├── migrate.sh                # NEW: Run migrations
│   └── rollback.sh               # NEW: Rollback migration
│
└── requirements/                 # NEW: Split requirements
    ├── base.txt                  # Core dependencies
    ├── dev.txt                   # Development tools
    └── prod.txt                  # Production-only (uvicorn, gunicorn)
```

### Structure Rationale

**Why `api/` directory (separate from bot):**
- **Separation of concerns:** HTTP API vs Telegram bot protocol
- **Port isolation:** Bot on polling, API on port 8001
- **Lifecycle independence:** API can run without bot (monitoring mode)

**Why `bot/storage/` abstraction:**
- **Pluggable FSM backends:** Switch between MemoryStorage (dev) and RedisStorage (prod)
- **Unified interface:** `get_storage()` function based on `REDIS_URL` presence
- **Testing support:** Mock storage for unit tests

**Why `tests/` hierarchy (unit/integration/e2e):**
- **Clear test boundaries:** Unit (no external deps), integration (real DB), e2e (full flow)
- **Parallel execution:** Unit tests run fast, can be parallelized
- **CI/CD friendly:** Different test suites for different stages

**Why split requirements:**
- **Production slim:** Only install what's needed in production (smaller image)
- **Dev tooling:** pytest, pytest-asyncio, coverage only in development
- **Clear dependencies:** base.txt is shared, dev.txt and prod.txt extend it

---

## Architectural Patterns

### Pattern 1: Database Abstraction Layer

**What:** Engine factory detects database dialect from `DATABASE_URL` protocol and creates appropriate async engine.

**When to use:** When application needs to support multiple databases (SQLite for local, PostgreSQL for production) without code changes.

**Trade-offs:**
- **Pro:** Single codebase, environment-based switching
- **Pro:** No if/else checks in service layer
- **Pro:** Easy local development (SQLite)
- **Con:** Need to test both dialects (SQLite quirks vs PostgreSQL features)
- **Con:** Migration complexity (different SQL dialects)

**Example:**
```python
# bot/database/factory.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from urllib.parse import urlparse

def create_engine(database_url: str) -> AsyncEngine:
    """
    Create async engine based on DATABASE_URL protocol.

    Protocols supported:
    - sqlite+aiosqlite:///path/to/db.db
    - postgresql+asyncpg://user:pass@host/db
    """
    parsed = urlparse(database_url)

    if parsed.scheme.startswith('sqlite'):
        # SQLite configuration
        return create_async_engine(
            database_url,
            echo=False,
            poolclass=NullPool,  # SQLite doesn't need pooling
            connect_args={
                "check_same_thread": False,
                "timeout": 30
            }
        )
    elif parsed.scheme.startswith('postgresql'):
        # PostgreSQL configuration
        return create_async_engine(
            database_url,
            echo=False,
            pool_size=10,        # Connection pool
            max_overflow=20,     # Additional connections
            pool_pre_ping=True,  # Verify connections before use
        )
    else:
        raise ValueError(f"Unsupported database protocol: {parsed.scheme}")

# Usage in main.py
from bot.database.factory import create_engine

engine = create_engine(Config.DATABASE_URL)
```

**Integration with ServiceContainer:**
```python
# bot/services/container.py (UPDATED)
class ServiceContainer:
    def __init__(self, session: AsyncSession, bot: Bot):
        self._session = session
        self._bot = bot

        # NEW v1.2 services
        self._cache_service = None
        self._health_service = None
        self._migration_service = None

    @property
    def cache(self) -> 'CacheService':
        """Cache service for frequently accessed data."""
        if self._cache_service is None:
            from bot.services.cache import CacheService
            # Redis URL from config or None (in-memory fallback)
            redis_url = os.getenv("REDIS_URL")
            self._cache_service = CacheService(redis_url=redis_url)
        return self._cache_service

    @property
    def health(self) -> 'HealthCheckService':
        """Health check service for monitoring."""
        if self._health_service is None:
            from bot.services.health import HealthCheckService
            self._health_service = HealthCheckService(
                bot=self._bot,
                session=self._session,
                redis_url=os.getenv("REDIS_URL")
            )
        return self._health_service

    @property
    def migration(self) -> 'MigrationService':
        """Migration service for Alembic operations."""
        if self._migration_service is None:
            from bot.services.migration import MigrationService
            self._migration_service = MigrationService(
                database_url=Config.DATABASE_URL
            )
        return self._migration_service
```

---

### Pattern 2: Redis Integration (FSM + Caching)

**What:** Redis serves two purposes: (1) FSM state persistence across restarts, (2) Application-level caching for frequently accessed data.

**When to use:** When deploying to production with multiple bot instances or needing state persistence.

**Trade-offs:**
- **Pro:** FSM state survives bot restarts
- **Pro:** Horizontal scaling (multiple bot instances share state)
- **Pro:** Cache reduces database load
- **Con:** Additional infrastructure dependency
- **Con:** Network latency (vs in-memory)
- **Con:** Complexity (cache invalidation)

**Example:**
```python
# bot/storage/redis.py
from aiogram.fsm.storage.redis import RedisStorage
import redis.asyncio as redis

def get_redis_storage(redis_url: str) -> RedisStorage:
    """Create Redis FSM storage from URL."""
    client = redis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True
    )
    return RedisStorage(redis=client)

# bot/services/cache.py
from typing import Optional, Any
import json
import redis.asyncio as redis

class CacheService:
    """
    Cache service with TTL support.

    Use cases:
    - Cache BotConfig (rarely changes, read often)
    - Cache user role (24h TTL, reduces DB queries)
    - Cache content packages (1h TTL, improves menu render speed)
    """

    def __init__(self, redis_url: Optional[str] = None):
        if redis_url:
            self._redis = redis.from_url(redis_url)
        else:
            self._redis = None  # Fallback to no-op (dev mode)

    async def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        if not self._redis:
            return None

        value = await self._redis.get(key)
        if value:
            return json.loads(value)
        return None

    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set cached value with TTL (default 1h)."""
        if not self._redis:
            return

        await self._redis.setex(
            key,
            ttl,
            json.dumps(value)
        )

    async def delete(self, key: str):
        """Delete cached value."""
        if not self._redis:
            return
        await self._redis.delete(key)

    async def warm_cache(self):
        """Pre-populate cache with frequently accessed data."""
        # Cache BotConfig
        config = await self._get_config_from_db()
        await self.set("bot:config", config, ttl=300)  # 5 min

        # Cache active content packages
        packages = await self._get_active_packages()
        await self.set("content:active", packages, ttl=300)

# Integration in existing services:
# bot/services/subscription.py (MODIFIED)
class SubscriptionService:
    async def is_vip_active(self, user_id: int) -> bool:
        # Check cache first
        cached_role = await self.container.cache.get(f"user:role:{user_id}")
        if cached_role:
            return cached_role == "vip"

        # Query database
        subscriber = await self._session.get(VIPSubscriber, user_id)
        is_vip = subscriber and subscriber.is_active

        # Cache result
        await self.container.cache.set(
            f"user:role:{user_id}",
            "vip" if is_vip else "free",
            ttl=86400  # 24h
        )

        return is_vip
```

**Cache Invalidation Strategy:**
```python
# Invalidate on role change
async def change_user_role(self, user_id: int, new_role: str):
    # Update database
    await self._update_role_in_db(user_id, new_role)

    # Invalidate cache
    await self.container.cache.delete(f"user:role:{user_id}")

# Invalidate on config change
async def update_bot_config(self, **kwargs):
    # Update database
    config = await self._update_config(**kwargs)

    # Invalidate cache
    await self.container.cache.delete("bot:config")

    # Notify all instances (if using cache broadcasting)
    await self.container.cache.publish("cache:invalidate", "bot:config")
```

---

### Pattern 3: Health Check Endpoint (FastAPI + aiogram)

**What:** FastAPI runs alongside aiogram bot, providing HTTP health endpoint for Railway monitoring.

**When to use:** When deploying to cloud platforms that require HTTP health checks (Railway, Heroku, AWS ECS).

**Trade-offs:**
- **Pro:** Standard health check protocol (HTTP)
- **Pro:** Railway automatic restarts on failure
- **Pro:** Can expose metrics (DB latency, cache hit rate)
- **Con:** Additional process (or thread) to run
- **Con:** Port management (bot + API on different ports)
- **Con:** Dependency on FastAPI (new framework)

**Example:**
```python
# api/main.py
from fastapi import FastAPI
from api.dependencies import get_bot, get_session, get_redis

app = FastAPI(title="LucienVoiceService Health")

@app.get("/health")
async def health_check(
    bot = Depends(get_bot),
    session = Depends(get_session),
    redis = Depends(get_redis)
):
    """
    Health check endpoint for Railway monitoring.

    Returns:
        - bot: "ok" if bot instance exists
        - db: "ok" if database connection works
        - redis: "ok" if redis connection works (optional)

    Railway pings this endpoint every 30s.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }

    # Check bot
    try:
        # Simple check: bot instance exists
        if bot and hasattr(bot, '_session'):
            health_status["checks"]["bot"] = "ok"
        else:
            health_status["checks"]["bot"] = "error"
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["checks"]["bot"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    # Check database
    try:
        # Ping database with simple query
        await session.execute(text("SELECT 1"))
        health_status["checks"]["db"] = "ok"
    except Exception as e:
        health_status["checks"]["db"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    # Check redis (optional)
    if redis:
        try:
            await redis.ping()
            health_status["checks"]["redis"] = "ok"
        except Exception as e:
            health_status["checks"]["redis"] = f"error: {str(e)}"
            # Redis failure is warning, not failure
            health_status["status"] = "degraded"

    # Return appropriate HTTP status
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)

# Run both bot and API in main.py
# main.py (MODIFIED)
import asyncio
from hypercorn.asyncio import serve
from hypercorn.config import Config

async def run_all():
    """Run bot and API concurrently."""

    # Start FastAPI in background
    api_config = Config()
    api_config.bind = ["0.0.0.0:8001"]
    api_task = asyncio.create_task(
        serve(app, api_config)
    )

    # Start bot
    bot_task = asyncio.create_task(
        dp.start_polling(bot)
    )

    # Wait for both
    await asyncio.gather(api_task, bot_task)

if __name__ == "__main__":
    asyncio.run(run_all())
```

**Railway Configuration:**
```toml
# railway.toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "python main.py"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

[[services]]
name = "bot"
serviceType = "BOT"

[[services.ports]]
port = 8001
type = "HTTP"
healthcheck = true
```

---

### Pattern 4: Alembic Migration System

**What:** Alembic tracks database schema versions and provides migration scripts for evolving the database.

**When to use:** When application needs to evolve database schema without data loss or downtime.

**Trade-offs:**
- **Pro:** Version-controlled schema changes
- **Pro:** Rollback capability
- **Pro:** Team collaboration (migration files in git)
- **Pro:** Production-safe (upgrade/downgrade scripts)
- **Con:** Additional complexity (migration files)
- **Con:** Async driver support requires special handling
- **Con:** Migration conflicts in teams

**Example:**
```python
# alembic/versions/001_initial.py
"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-01-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Create initial tables."""

    # BotConfig table
    op.create_table(
        'bot_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vip_channel_id', sa.String(), nullable=True),
        sa.Column('free_channel_id', sa.String(), nullable=True),
        sa.Column('wait_time_minutes', sa.Integer(), nullable=False),
        sa.Column('vip_reactions', sa.JSON(), nullable=True),
        sa.Column('free_reactions', sa.JSON(), nullable=True),
        sa.Column('subscription_fees', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # VIPSubscriber table
    op.create_table(
        'vip_subscribers',
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('subscribed_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index('idx_vip_expires_at', 'vip_subscribers', ['expires_at'])

    # ... more tables

def downgrade():
    """Drop all tables."""
    op.drop_table('vip_subscribers')
    op.drop_table('bot_config')
    # ... more tables

# alembic/env.py (async engine configuration)
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

def run_migrations_online():
    """Run migrations in 'online' mode with async engine."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = os.getenv("DATABASE_URL")

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations, connection)

    await connectable.dispose()

# Run migration
# terminal
$ alembic upgrade head

# Rollback
$ alembic downgrade -1
```

**MigrationService Integration:**
```python
# bot/services/migration.py
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.environment import EnvironmentContext

class MigrationService:
    """Service for running Alembic migrations programmatically."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.alembic_cfg = Config("alembic/alembic.ini")
        self.alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    async def get_current_version(self) -> str:
        """Get current database migration version."""
        script = ScriptDirectory.from_config(self.alembic_cfg)
        # Query alembic_version table
        # Returns version number or None (initial state)
        pass

    async def run_migrations(self):
        """Run all pending migrations."""
        # Equivalent to: alembic upgrade head
        # Use Alembic API programmatically
        pass

    async def rollback(self, revision: str):
        """Rollback to specific revision."""
        # Equivalent to: alembic downgrade <revision>
        pass

# Usage in main.py (startup)
async def on_startup(bot: Bot, dispatcher: Dispatcher):
    # Run migrations on startup (production)
    if os.getenv("ENVIRONMENT") == "production":
        migration_service = MigrationService(Config.DATABASE_URL)
        await migration_service.run_migrations()
        logger.info("✅ Migrations applied")
```

---

## Data Flow Changes

### Menu Rendering with Cache

```
[User clicks "Contenido VIP" button]
    ↓
[Callback handler: content_list]
    ↓
[Check cache: key="content:active:vip"]
    ├─→ Cache Hit: Return packages (<10ms)
    └─→ Cache Miss:
        ↓
        [Query database: ContentPackage.where(type='vip', is_active=True)]
        ↓
        [Store in cache: TTL=300s (5 min)]
        ↓
        [Return packages]
    ↓
[Build pagination keyboard]
    ↓
[Send message to user]
```

### Health Check Flow

```
[Railway scheduler: every 30s]
    ↓
[HTTP GET /health]
    ↓
[FastAPI handler]
    ↓
[Check bot: instance exists]
    ↓
[Check database: SELECT 1]
    ↓
[Check redis: PING (if REDIS_URL set)]
    ↓
[Return JSON: {status: "healthy", checks: {...}}]
    ↓
[Railway evaluates response]
    ├─→ 200 OK: Service healthy
    └─→ 503 Error: Restart container
```

### Migration Flow (Deployment)

```
[git push to Railway]
    ↓
[Railway builds Docker image]
    ↓
[Railway deploys new container]
    ↓
[Container starts: python main.py]
    ↓
[on_startup hook]
    ↓
[MigrationService.run_migrations()]
    ↓
[Alembic checks alembic_version table]
    ├─→ No table: Create, run all migrations
    └─→ Table exists: Compare versions, run pending
    ↓
[Migrations applied: Database up-to-date]
    ↓
[Bot starts polling]
```

---

## Integration Points

### 1. ServiceContainer (Add New Services)

```python
# bot/services/container.py (UPDATED)
class ServiceContainer:
    def __init__(self, session: AsyncSession, bot: Bot):
        self._session = session
        self._bot = bot

        # Existing services (unchanged)
        self._subscription_service = None
        self._channel_service = None
        # ... 9 more existing services

        # NEW v1.2 services
        self._cache_service = None
        self._health_service = None
        self._migration_service = None

    @property
    def cache(self) -> 'CacheService':
        """Lazy-loaded cache service."""
        if self._cache_service is None:
            from bot.services.cache import CacheService
            redis_url = os.getenv("REDIS_URL")
            self._cache_service = CacheService(redis_url=redis_url)
        return self._cache_service

    @property
    def health(self) -> 'HealthCheckService':
        """Lazy-loaded health check service."""
        if self._health_service is None:
            from bot.services.health import HealthCheckService
            self._health_service = HealthCheckService(
                bot=self._bot,
                session=self._session,
                redis_url=os.getenv("REDIS_URL")
            )
        return self._health_service

    @property
    def migration(self) -> 'MigrationService':
        """Lazy-loaded migration service."""
        if self._migration_service is None:
            from bot.services.migration import MigrationService
            self._migration_service = MigrationService(
                database_url=Config.DATABASE_URL
            )
        return self._migration_service

    def get_loaded_services(self) -> list[str]:
        """Return list of loaded services (for debugging)."""
        loaded = []

        # Check existing services
        if self._subscription_service is not None:
            loaded.append("subscription")
        # ... (all existing services)

        # Check new v1.2 services
        if self._cache_service is not None:
            loaded.append("cache")
        if self._health_service is not None:
            loaded.append("health")
        if self._migration_service is not None:
            loaded.append("migration")

        return loaded
```

### 2. Database Engine Factory (Dialect Detection)

```python
# bot/database/factory.py (NEW)
from urllib.parse import urlparse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool, QueuePool

def create_engine(database_url: str) -> AsyncEngine:
    """
    Create async engine with dialect-specific configuration.

    Args:
        database_url: SQLAlchemy database URL

    Returns:
        Configured AsyncEngine

    Example URLs:
    - sqlite+aiosqlite:///bot.db
    - postgresql+asyncpg://user:pass@host:5432/dbname
    """
    parsed = urlparse(database_url)

    if parsed.scheme.startswith('sqlite'):
        # SQLite configuration (local development)
        return create_async_engine(
            database_url,
            echo=False,
            poolclass=NullPool,
            connect_args={
                "check_same_thread": False,
                "timeout": 30
            }
        )

    elif parsed.scheme.startswith('postgresql'):
        # PostgreSQL configuration (production)
        return create_async_engine(
            database_url,
            echo=False,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )

    else:
        raise ValueError(
            f"Unsupported database scheme: {parsed.scheme}. "
            f"Supported: sqlite+aiosqlite://, postgresql+asyncpg://"
        )

# bot/database/engine.py (UPDATED)
def init_db(database_url: str = None) -> None:
    """Initialize database engine with dialect detection."""
    global _engine, _session_factory

    if database_url is None:
        database_url = Config.DATABASE_URL

    # Use factory instead of direct create_async_engine
    from bot.database.factory import create_engine
    _engine = create_engine(database_url)

    # Dialect-specific setup
    parsed = urlparse(database_url)
    if parsed.scheme.startswith('sqlite'):
        # SQLite PRAGMAs
        async with _engine.begin() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA synchronous=NORMAL"))
            await conn.execute(text("PRAGMA foreign_keys=ON"))
    elif parsed.scheme.startswith('postgresql'):
        # PostgreSQL setup (if needed)
        pass

    # Create session factory
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
```

### 3. FSM Storage (Pluggable Backends)

```python
# bot/storage/__init__.py (NEW)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
import os

def get_storage():
    """
    Get FSM storage based on environment.

    Returns:
        MemoryStorage (local) or RedisStorage (production)

    Usage:
        storage = get_storage()
        dp = Dispatcher(storage=storage)
    """
    redis_url = os.getenv("REDIS_URL")

    if redis_url:
        # Production: Redis storage (persists across restarts)
        import redis.asyncio as redis
        redis_client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        storage = RedisStorage(redis=redis_client)
        logger.info("📦 Using Redis FSM storage")
    else:
        # Local: Memory storage (ephemeral)
        storage = MemoryStorage()
        logger.info("🧠 Using Memory FSM storage")

    return storage

# main.py (UPDATED)
from bot.storage import get_storage

async def main():
    bot = Bot(token=Config.BOT_TOKEN)
    storage = get_storage()  # Auto-detect from REDIS_URL
    dp = Dispatcher(storage=storage)

    # ... rest of setup
```

### 4. Testing Architecture (pytest-asyncio Fixtures)

```python
# tests/conftest.py (NEW)
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from aiogram import Bot
from bot.services.container import ServiceContainer
from bot.database.base import Base

# Database fixture (in-memory SQLite)
@pytest.fixture
async def test_db():
    """Create in-memory database for tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    yield async_session

    await engine.dispose()

# Bot fixture (mocked)
@pytest.fixture
def mock_bot():
    """Mock bot instance."""
    from unittest.mock import Mock
    bot = Mock(spec=Bot)
    return bot

# Service container fixture
@pytest.fixture
async def container(test_db, mock_bot):
    """Service container with test database."""
    async with test_db() as session:
        yield ServiceContainer(session, mock_bot)

# Example test
@pytest.mark.asyncio
async def test_cache_service_set_get(container):
    """Test cache service set/get operations."""
    cache_service = container.cache

    # Set value
    await cache_service.set("test_key", {"data": "value"}, ttl=60)

    # Get value
    result = await cache_service.get("test_key")

    assert result == {"data": "value"}

# Example integration test
@pytest.mark.asyncio
async def test_vip_subscription_with_cache(container):
    """Test VIP subscription with cache layer."""
    from bot.database.models import VIPSubscriber
    from datetime import datetime, timedelta

    # Create VIP subscriber
    subscriber = VIPSubscriber(
        user_id=123,
        subscribed_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=30),
        is_active=True
    )
    await container.subscription._session.add(subscriber)
    await container.subscription._session.commit()

    # First call: query DB
    is_vip = await container.subscription.is_vip_active(123)
    assert is_vip is True

    # Check cache was set
    cached_role = await container.cache.get("user:role:123")
    assert cached_role == "vip"

    # Second call: use cache
    is_vip_cached = await container.subscription.is_vip_active(123)
    assert is_vip_cached is True
```

---

## Build Order and Dependencies

### Phase 1: Database Abstraction (No Dependencies)

**Goal:** Switch between SQLite and PostgreSQL via environment variable.

1. **Create `bot/database/factory.py`**
   - `create_engine()` with dialect detection
   - SQLite configuration (NullPool, WAL mode)
   - PostgreSQL configuration (QueuePool, connection settings)

2. **Update `bot/database/engine.py`**
   - Replace direct `create_async_engine()` with factory
   - Add dialect-specific PRAGMAs for SQLite
   - Add PostgreSQL-specific setup (if needed)

3. **Create `alembic/` directory**
   - Initialize Alembic: `alembic init alembic`
   - Configure `alembic.ini` for async operations
   - Create initial migration `001_initial.py`

**Deliverable:** Application runs with SQLite (local) and PostgreSQL (production) via `DATABASE_URL`.

**Risk:** LOW - Factory pattern isolates changes.

---

### Phase 2: Redis Integration (Depends on Phase 1)

**Goal:** Add Redis for FSM storage and caching.

1. **Create `bot/storage/` module**
   - `get_storage()` function (MemoryStorage vs RedisStorage)
   - Redis connection from `REDIS_URL`

2. **Create `bot/services/cache.py`**
   - `CacheService` class
   - Methods: get, set, delete, warm_cache
   - In-memory fallback when `REDIS_URL` not set

3. **Update `main.py`**
   - Use `get_storage()` for dispatcher
   - Initialize CacheService in container

4. **Update existing services**
   - Add cache layer to frequently accessed data
   - Implement cache invalidation on writes

**Deliverable:** FSM state persisted in Redis, cache reduces DB load.

**Risk:** MEDIUM - Redis dependency, cache invalidation complexity.

---

### Phase 3: Health Check API (Depends on Phase 1, 2)

**Goal:** HTTP endpoint for Railway health monitoring.

1. **Create `api/` directory**
   - FastAPI app in `api/main.py`
   - Health check route in `api/routes/health.py`

2. **Create `bot/services/health.py`**
   - `HealthCheckService` class
   - Methods: check_bot, check_db, check_redis

3. **Update `main.py`**
   - Run FastAPI alongside bot (concurrent tasks)
   - Expose port 8001 for API

4. **Create `railway.toml`**
   - Health check path configuration
   - Restart policy settings

**Deliverable:** Railway monitors `/health`, auto-restarts on failure.

**Risk:** MEDIUM - New framework (FastAPI), port management.

---

### Phase 4: Migration Service (Depends on Phase 1)

**Goal:** Programmatic migration management.

1. **Create `bot/services/migration.py`**
   - `MigrationService` class
   - Methods: get_current_version, run_migrations, rollback

2. **Update `on_startup` in `main.py`**
   - Run migrations on startup (production only)
   - Log migration status

3. **Create migration scripts**
   - `scripts/migrate.sh`
   - `scripts/rollback.sh`

**Deliverable:** Migrations run automatically on deployment.

**Risk:** LOW - Alembic is mature, well-documented.

---

### Phase 5: Test Suite (Depends on All Above)

**Goal:** Comprehensive test coverage.

1. **Create `tests/conftest.py`**
   - Fixtures for test_db, mock_bot, container
   - pytest-asyncio configuration

2. **Create unit tests**
   - `tests/unit/test_services/`
   - `tests/unit/test_middlewares/`
   - Mock external dependencies (Redis, Telegram API)

3. **Create integration tests**
   - `tests/integration/test_database/`
   - `tests/integration/test_cache/`
   - Real database, mocked Telegram

4. **Create e2e tests**
   - `tests/e2e/test_vip_flow.py`
   - `tests/e2e/test_admin_flow.py`
   - Full flow with test bot token

5. **Configure CI/CD**
   - GitHub Actions workflow
   - Run tests on push
   - Coverage reporting

**Deliverable:** Test suite validates all functionality.

**Risk:** LOW - Tests don't break existing code.

---

### Phase 6: Railway Deployment (Depends on All Above)

**Goal:** Deploy to Railway with all infrastructure.

1. **Create `railway.toml`**
   - Build configuration (NIXPACKS)
   - Environment variables
   - Health check settings

2. **Create `Dockerfile`**
   - Python base image
   - Install dependencies
   - Run command

3. **Create `.railway/nixpacks.toml`**
   - Build-specific configuration
   - Start command

4. **Configure Railway services**
   - Bot service
   - PostgreSQL plugin
   - Redis plugin

5. **Deploy**
   - Link GitHub repo
   - Set environment variables
   - Deploy and monitor

**Deliverable:** Bot running on Railway with health checks.

**Risk:** MEDIUM - New platform, environment variable management.

---

### Dependency Graph

```
Phase 1 (Database Abstraction)
    ↓
    ├─→ Phase 2 (Redis Integration)
    │       ↓
    │       ├─→ Phase 3 (Health Check API)
    │       └─→ Phase 4 (Migration Service)
    │               ↓
    │           Phase 5 (Test Suite)
    │               ↓
    │           Phase 6 (Railway Deployment)
    │
    └─→ (can run in parallel with Phase 2)
```

**Critical path:** Phase 1 must complete before all other phases.

**Parallel work:** Phase 3 (Health Check) and Phase 4 (Migration) can be developed simultaneously after Phase 2.

---

## Anti-Patterns

### Anti-Pattern 1: Hardcoding Database URLs

**What people do:** Hardcode `postgresql://` URLs in service code.

```python
# BAD: Hardcoded PostgreSQL URL
class SubscriptionService:
    def __init__(self):
        self.engine = create_async_engine(
            "postgresql+asyncpg://user:pass@localhost/db"
        )
```

**Why it's wrong:**
- Cannot switch between environments (dev/staging/prod)
- Database credentials in source code (security risk)
- Cannot use SQLite for local development

**Do this instead:**
```python
# GOOD: Use environment variable + factory
from bot.database.factory import create_engine

engine = create_engine(Config.DATABASE_URL)
```

---

### Anti-Pattern 2: Cache-Aside Without Invalidation

**What people do:** Cache data but never invalidate on updates.

```python
# BAD: Cache never invalidated
async def get_user_role(user_id: int) -> str:
    cached = await cache.get(f"user:role:{user_id}")
    if cached:
        return cached

    role = await db.query_user_role(user_id)
    await cache.set(f"user:role:{user_id}", role)
    return role

async def change_user_role(user_id: int, new_role: str):
    await db.update_user_role(user_id, new_role)
    # ❌ Forgot to invalidate cache!
```

**Why it's wrong:**
- Stale data served from cache
- User sees old role for 24h (cache TTL)
- Inconsistent state between cache and database

**Do this instead:**
```python
# GOOD: Invalidate cache on update
async def change_user_role(user_id: int, new_role: str):
    await db.update_user_role(user_id, new_role)
    await cache.delete(f"user:role:{user_id}")  # ✅ Invalidate
```

---

### Anti-Pattern 3: Synchronous Migrations in Async Codebase

**What people do:** Use synchronous Alembic driver with async SQLAlchemy.

```python
# BAD: Sync driver with async engine
# alembic/env.py
engine = create_engine(
    "postgresql://user:pass@host/db",  # ❌ Synchronous
)
```

**Why it's wrong:**
- Mixed sync/async code causes blocking
- Cannot use asyncpg benefits
- Performance degradation

**Do this instead:**
```python
# GOOD: Async driver with async engine
# alembic/env.py
from sqlalchemy.ext.asyncio import async_engine_from_config

connectable = async_engine_from_config(
    configuration,
    prefix="sqlalchemy.",
)
```

---

### Anti-Pattern 4: Health Check that Doesn't Check Anything

**What people do:** Health check always returns "ok" without verifying dependencies.

```python
# BAD: Health check doesn't check anything
@app.get("/health")
async def health():
    return {"status": "ok"}  # ❌ Always ok, even if DB is down
```

**Why it's wrong:**
- Railway thinks service is healthy when it's not
- Users experience failures but service isn't restarted
- No visibility into actual system state

**Do this instead:**
```python
# GOOD: Verify all dependencies
@app.get("/health")
async def health(bot, db, redis):
    checks = {}

    # Check bot
    try:
        assert bot is not None
        checks["bot"] = "ok"
    except Exception as e:
        checks["bot"] = f"error: {e}"

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {e}"

    # Check redis
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    status_code = 200 if all(v == "ok" for v in checks.values()) else 503
    return JSONResponse(content={"status": "healthy", "checks": checks}, status_code=status_code)
```

---

### Anti-Pattern 5: Tests that Require External Services

**What people do:** Unit tests connect to real Redis, PostgreSQL, Telegram API.

```python
# BAD: Unit test connects to real services
@pytest.mark.asyncio
async def test_subscription_service():
    # ❌ Requires real PostgreSQL and Redis running
    service = SubscriptionService(real_db, real_redis)
    result = await service.is_vip_active(123)
```

**Why it's wrong:**
- Tests fail if services aren't running
- Slow test execution (network latency)
- Cannot run tests in CI without complex setup
- Tests are integration tests, not unit tests

**Do this instead:**
```python
# GOOD: Mock external dependencies in unit tests
from unittest.mock import AsyncMock, Mock

@pytest.mark.asyncio
async def test_subscription_service():
    # ✅ Mock dependencies
    mock_db = AsyncMock()
    mock_cache = AsyncMock()
    mock_cache.get.return_value = None  # Cache miss

    service = SubscriptionService(mock_db, mock_cache)
    result = await service.is_vip_active(123)

    assert result is True
    mock_cache.set.assert_called_once()  # Verify cache set
```

---

## Scalability Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **Current (<1k users, SQLite)** | Single bot instance, SQLite WAL mode, no caching needed. |
| **Medium (1k-10k users, PostgreSQL)** | Add Redis for FSM storage, cache frequently accessed data, index on (user_id, expires_at). |
| **Large (10k-100k users)** | Multiple bot instances with shared Redis FSM, read replica for queries, connection pooling (pool_size=20). |
| **Very Large (100k+ users)** | Horizontal scaling (5-10 bot instances), Redis Cluster, database sharding, CDN for media, message queue for notifications. |

### Scaling Priorities for v1.2

1. **First bottleneck:** Database connection pool (SQLite locks, PostgreSQL pool exhaustion). Solution: PostgreSQL with pool_size=10.
2. **Second bottleneck:** FSM state memory (MemoryStorage grows unbounded). Solution: RedisStorage with TTL.
3. **Third bottleneck:** Cache hit rate (frequent DB queries for same data). Solution: Cache BotConfig, user roles, active content.

### Performance Targets

| Operation | Current (SQLite) | With PostgreSQL + Redis | Target |
|-----------|-----------------|-------------------------|--------|
| Bot startup | 2-3s | 3-5s (migration check) | <5s |
| Menu render | 50-100ms | 20-30ms (cached) | <50ms |
| Role check | 30-50ms | 5-10ms (cached) | <20ms |
| Token generation | 100-150ms | 80-120ms | <150ms |
| Health check | N/A | 10-20ms | <100ms |

---

## Sources

### Railway Deployment
- [Deploy Telegram Gatekeeper Bot on Railway](https://railway.com/deploy/telegram-gatekeeper-bot) — Railway bot template (HIGH confidence)
- [The Simplest Way to Deploy a Telegram Bot in 2026](https://kuberns.com/blogs/post/deploy-telegram-bot/) — Deployment guide (MEDIUM confidence)
- [Railway CLI - GitHub](https://github.com/railwayapp/cli) — Official CLI documentation (HIGH confidence)

### PostgreSQL + SQLAlchemy Async
- [Connect to PostgreSQL with SQLAlchemy and asyncio](https://makimo.com/blog/connect-to-postgresql-with-sqlalchemy-and-asyncio) — PostgreSQL async setup (HIGH confidence)
- [Asynchronous SQLAlchemy 2: A simple step-by-step guide](https://dev.to/amverum/asynchronous-sqlalchemy-2-a-simple-step-by-step-guide-to-configuration-models-relationships-and-3ob3) — Async patterns (HIGH confidence)
- [PostgreSQL — SQLAlchemy 2.1 Documentation](http://docs.sqlalchemy.org/en/latest/dialects/postgresql.html) — Official PostgreSQL dialect docs (HIGH confidence)

### Alembic Migrations
- [Setup FastAPI Project with Async SQLAlchemy 2, Alembic, PostgreSQL](https://berkkaraal.com/blog/2024/09/19/setup-fastapi-project-with-async-sqlalchemy-2-alembic-postgresql-and-docker/) — Async Alembic setup (HIGH confidence)
- [FastAPI with Async SQLAlchemy, SQLModel, and Alembic](https://testdriven.io/blog/fastapi-sqlmodel/) — Alembic integration (MEDIUM confidence)
- [Tutorial — Alembic 1.18.1 documentation](https://alembic.sqlalchemy.org/en/latest/tutorial.html) — Official Alembic docs (HIGH confidence)

### Redis Integration
- [aiogram_bot_template - GitHub](https://github.com/wakaree/aiogram_bot_template) — Redis FSM storage example (MEDIUM confidence)
- [aiogram 3.24.0 Changelog](https://docs.aiogram.dev/en/latest/changelog.html) — FSM storage features (HIGH confidence)

### Testing with pytest-asyncio
- [A Practical Guide To Async Testing With Pytest-Asyncio](https://dag7.it/appunti/dev/Pytest/A-Practical-Guide-To-Async-Testing-With-Pytest-Asyncio) — Async testing patterns (HIGH confidence)
- [Best Practices for Testing Async Python Apps](https://www.linkedin.com/advice/0/what-best-practices-testing-async-python-applications-ybe4e) — Testing best practices (MEDIUM confidence)
- [aiogram pytest-asyncio compatibility fixes](https://docs.aiogram.dev/en/v3.16.0/changelog.html) — aiogram testing (HIGH confidence)

### Health Check & Monitoring
- [FastAPI Health Monitor - GitHub](https://github.com/adamkirchberger/fastapi-health-monitor) — Health check patterns (HIGH confidence)
- [How to Build a Web Monitoring Workflow with Python and Telegram Alerts](https://dev.to/jesulayomi/how-to-build-a-web-monitoring-workflow-with-python-n8n-docker-using-telegram-alerts-22la) — Monitoring setup (MEDIUM confidence)

---

*Architecture research for: v1.2 Primer Despliegue*
*Researched: 2026-01-28*
*Python 3.11+ | aiogram 3.4.1 | SQLAlchemy 2.0.25 | PostgreSQL 15+ | Redis 7+*
