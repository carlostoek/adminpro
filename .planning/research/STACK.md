# Technology Stack: v1.2 Primer Despliegue

**Project:** LucienVoiceService - Telegram Bot VIP/Free
**Researched:** 2026-01-28
**Mode:** Ecosystem (Railway deployment, PostgreSQL migration, Redis caching, testing)
**Overall confidence:** HIGH

## Executive Summary

For v1.2 Primer Despliegue (first production deployment), the recommended stack adds **Railway cloud platform, PostgreSQL with asyncpg driver, Redis caching layer, Alembic migrations, pytest-asyncio for testing, and FastAPI for health checks** to the existing aiogram 3.4.1 + SQLAlchemy 2.0.25 foundation. This migration from SQLite enables production-ready horizontal scaling, connection pooling, and separates concerns between persistent storage (PostgreSQL) and caching (Redis). The asyncpg driver is **5x faster than psycopg3** and is the de facto standard for async PostgreSQL in Python. Railway provides zero-config deployment with automatic PostgreSQL and Redis provisioning.

## Recommended Stack

### Cloud Platform
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Railway.app** | Current (2026) | Cloud deployment platform | Zero-config Python deployment via Nixpacks, automatic DATABASE_URL/REDIS_URL provisioning, built-in PostgreSQL/Redis services, free tier for testing. Superior to Heroku ($5/mo minimum) and Render (slower cold starts). |

### Database Migration
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **PostgreSQL** | 16.x (Railway default) | Production database | ACID compliance, concurrent writes, connection pooling, JSON support, full-text search. Migration from SQLite enables horizontal scaling and production reliability. |
| **asyncpg** | 0.29.0+ | Async PostgreSQL driver | **5x faster than psycopg3**, native asyncio support, prepared statements, connection pooling built-in. Standard for async PostgreSQL in Python. |
| **Alembic** | 1.13.0+ | Database migrations | Auto-generate migrations from SQLAlchemy models, version control schema changes, rollback support. Critical for PostgreSQL deployment. |

### Caching Layer
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Redis** | 7.x (Railway default) | In-memory cache & session store | Sub-millisecond reads, TTL-based expiration, pub/sub for future features. Caches frequently accessed data (user roles, content packages) to reduce DB load. |
| **redis-py (asyncio)** | 5.0.0+ | Async Redis client | Official Redis Python library with native asyncio support (`import redis.asyncio as redis`). aioredis was merged into redis-py in 2022. |

### Testing Infrastructure
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **pytest-asyncio** | 0.21.1+ | Async test runner | Already in use, enables `async def test_()` functions. Essential for testing aiogram handlers and SQLAlchemy async queries. |
| **aiogram-tests** | 0.3.0+ | aiogram mocking library | Dedicated testing library for aiogram bots. Provides mock Update/Message objects, handler testing utilities. Low confidence (last updated Oct 2022) - may need manual mocking. |
| **pytest-cov** | 4.1.0+ | Coverage reporting | Track test coverage, generate HTML reports, ensure critical paths are tested. |
| **pytest-mock** | 3.12.0+ | Mocking utilities | `mocker` fixture for mocking external services (Telegram API, Redis, PostgreSQL). |

### Health Check & Monitoring
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **FastAPI** | 0.109.0+ | Health check endpoint | Lightweight `/health` endpoint for Railway health checks. Runs alongside bot via uvicorn. Separate from bot to avoid crashing on bot errors. |
| **uvicorn** | 0.27.0+ | ASGI server | Run FastAPI health check server. Production-grade ASGI server with async support. |

### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **psycopg2-binary** | 2.9.9+ | Synchronous PostgreSQL access | Alembic migrations (synchronous only). NOT for runtime async queries. |
| **python-dotenv** | 1.0.0 (existing) | Environment variables | Load `.env` files for local development, Railway injects env vars automatically. |
| **httpx** | 0.26.0+ | Async HTTP client | Health check external services (Telegram API, Railway services). |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| **Cloud Platform** | Railway.app | Render | Render has slower cold starts (30-60s vs Railway's ~5s), less mature Python support. Railway's automatic DATABASE_URL/REDIS_URL provisioning is superior. |
| **Database** | PostgreSQL | MySQL | PostgreSQL has superior JSON support, better async drivers (asyncpg), and is Railway's default. MySQL's async ecosystem is weaker. |
| **PostgreSQL Driver** | asyncpg | psycopg3 | asyncpg is **5x faster** than psycopg3, has native asyncio support, and is battle-tested. psycopg3 is slower and better for drop-in psycopg2 replacements. |
| **Migration Tool** | Alembic |手动 SQL migrations | Manual migrations are error-prone and don't integrate with SQLAlchemy models. Alembic auto-generates migrations and supports rollbacks. |
| **Cache** | Redis | Memcached | Redis has richer data structures (hashes, sets, sorted sets), TTL support, and pub/sub. Memcached is simpler but less feature-rich. |
| **Testing** | pytest-asyncio + aiogram-tests | unittest | unittest doesn't support async tests natively (requires asyncio.run), and aiogram-specific mocking is better with dedicated library. |
| **Health Check** | FastAPI + uvicorn | aiogram内置 webhook | Bot webhook can't distinguish "bot crashed" from "Telegram API down". Separate health check endpoint monitors bot process independently. |

## Installation

```bash
# Core dependencies (add to requirements.txt)
# Note: Versions are minimum tested versions

# Database migration (PostgreSQL)
asyncpg==0.29.0               # Async PostgreSQL driver (5x faster than psycopg3)
psycopg2-binary==2.9.9        # Sync driver for Alembic migrations only
alembic==1.13.0               # Database migrations

# Caching
redis==5.0.0                  # Async Redis client (aioredis merged in 2022)

# Health check & monitoring
fastapi==0.109.0              # Lightweight health check endpoint
uvicorn[standard]==0.27.0     # ASGI server for FastAPI
httpx==0.26.0                 # Async HTTP client for external service checks

# Testing
pytest-cov==4.1.0             # Coverage reporting
pytest-mock==3.12.0           # Mocking utilities
aiogram-tests==0.3.0          # aiogram-specific testing utilities (LOW confidence - may need manual mocking)

# Existing dependencies (keep)
aiogram>=3.24.0               # Telegram bot framework
sqlalchemy==2.0.25            # ORM (change driver from aiosqlite to asyncpg)
APScheduler==3.10.4           # Background tasks
python-dotenv==1.0.0          # Environment variables
pytest==7.4.3                 # Test runner
pytest-asyncio==0.21.1        # Async test support
```

## Database Migration Strategy

### From SQLite to PostgreSQL

**Phase 1: Dual Database Support (Low Risk)**
```python
# config.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# Support both SQLite (local) and PostgreSQL (Railway)
if os.getenv("DATABASE_URL"):
    # Railway: PostgreSQL
    DATABASE_URL = os.getenv("DATABASE_URL")
    # Convert postgres:// to postgresql+asyncpg:// for SQLAlchemy
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
else:
    # Local: SQLite
    DATABASE_URL = "sqlite+aiosqlite:///bot.db"

engine = create_async_engine(DATABASE_URL, echo=False)
```

**Phase 2: Data Migration Script**
```python
# scripts/migrate_sqlite_to_postgres.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

async def migrate_data():
    # Connect to both databases
    sqlite_engine = create_async_engine("sqlite+aiosqlite:///bot.db")
    pg_engine = create_async_engine("postgresql+asyncpg://user:pass@host/db")

    # Read from SQLite, write to PostgreSQL
    # Migrate tables: bot_config, vip_subscribers, invitation_tokens, free_channel_requests
    # Migrate new tables: content_packages, user_interests, user_role_change_logs
```

**Phase 3: Alembic Setup**
```bash
# Initialize Alembic
alembic init alembic

# Edit alembic/env.py to use asyncpg
# sqlalchemy.url = postgresql+asyncpg://user:pass@host/db

# Generate initial migration from models
alembic revision --autogenerate -m "Initial migration"

# Run migrations
alembic upgrade head
```

**Phase 4: Switch PostgreSQL as Default**
- Remove SQLite fallback
- Deploy to Railway
- Monitor for 24 hours before deleting SQLite backup

## Integration with Existing Stack

### ServiceContainer Extension

```python
# bot/services/container.py (additions)

class ServiceContainer:
    # ... existing properties ...

    @property
    def cache(self) -> 'CacheService':
        """Lazy-loaded Redis cache service."""
        if self._cache_service is None:
            from bot.services.cache import CacheService
            self._cache_service = CacheService(self._bot)
        return self._cache_service

    @property
    def health(self) -> 'HealthService':
        """Lazy-loaded health check service."""
        if self._health_service is None:
            from bot.services.health import HealthService
            self._health_service = HealthService(self._session, self._bot)
        return self._health_service
```

### CacheService Implementation

```python
# bot/services/cache.py
import redis.asyncio as redis
from typing import Optional
import os

class CacheService:
    """Redis cache for frequently accessed data."""

    def __init__(self, bot: Bot):
        self._bot = bot
        self._redis: Optional[redis.Redis] = None

    async def get_redis(self) -> redis.Redis:
        """Get Redis connection (lazy-loaded)."""
        if self._redis is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self._redis = await redis.from_url(redis_url, decode_responses=True)
        return self._redis

    async def get_user_role(self, user_id: int) -> Optional[str]:
        """Get cached user role."""
        r = await self.get_redis()
        cached = await r.get(f"user_role:{user_id}")
        return cached

    async def set_user_role(self, user_id: int, role: str, ttl: int = 300):
        """Cache user role with 5min TTL."""
        r = await self.get_redis()
        await r.setex(f"user_role:{user_id}", ttl, role)

    async def get_content_package(self, package_id: int) -> Optional[dict]:
        """Get cached content package."""
        r = await self.get_redis()
        cached = await r.get(f"content_package:{package_id}")
        return json.loads(cached) if cached else None

    async def set_content_package(self, package_id: int, data: dict, ttl: int = 600):
        """Cache content package with 10min TTL."""
        r = await self.get_redis()
        await r.setex(f"content_package:{package_id}", ttl, json.dumps(data))
```

### Health Check Endpoint

```python
# bot/health_app.py (NEW FILE)
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine
import os
import httpx

health_app = FastAPI()

@health_app.get("/health")
async def health_check():
    """Health check endpoint for Railway monitoring."""
    checks = {
        "status": "healthy",
        "database": False,
        "redis": False,
        "telegram": False
    }

    # Check PostgreSQL
    try:
        engine = create_async_engine(os.getenv("DATABASE_URL"))
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        checks["database"] = True
    except Exception as e:
        checks["status"] = "unhealthy"
        checks["database_error"] = str(e)

    # Check Redis
    try:
        import redis.asyncio as redis
        r = await redis.from_url(os.getenv("REDIS_URL"))
        await r.ping()
        checks["redis"] = True
    except Exception as e:
        checks["status"] = "degraded" if checks["status"] == "healthy" else "unhealthy"
        checks["redis_error"] = str(e)

    # Check Telegram API
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://api.telegram.org/bot" + os.getenv("BOT_TOKEN") + "/getMe")
        checks["telegram"] = resp.status_code == 200
    except Exception as e:
        checks["status"] = "degraded" if checks["status"] == "healthy" else "unhealthy"
        checks["telegram_error"] = str(e)

    status_code = 200 if checks["status"] == "healthy" else 503
    return checks, status_code

# Run health check server alongside bot
# uvicorn bot.health_app:health_app --host 0.0.0.0 --port ${HEALTH_PORT:-8001}
```

## Railway Deployment Configuration

### railway.json (NEW FILE)
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE"
  }
}
```

### Environment Variables (Railway Dashboard)
```
# Railway automatically provides these:
DATABASE_URL=postgresql://user:pass@host/db
REDIS_URL=redis://host:port

# Manual configuration:
BOT_TOKEN=your_bot_token
ADMIN_IDS=123456789,987654321
HEALTH_PORT=8001
```

### Procfile (NEW FILE - optional, overrides default)
```
web: python -m uvicorn bot.health_app:health_app --host 0.0.0.0 --port $PORT & python main.py
```

**Note:** Railway's Nixpacks automatically detects Python projects and installs from `requirements.txt`. No Dockerfile needed unless custom build steps are required.

## Testing Strategy

### pytest-asyncio Configuration

```python
# tests/conftest.py (NEW FILE)
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from bot.database.base import Base

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def session():
    """Create test database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

@pytest.fixture
def mock_bot():
    """Mock aiogram Bot instance."""
    from unittest.mock import AsyncMock
    from aiogram import Bot

    bot = AsyncMock(spec=Bot)
    bot.get_me.return_value = AsyncMock(id=123, username="test_bot")
    return bot
```

### aiogram Handler Testing

```python
# tests/test_handlers/test_menu.py
import pytest
from aiogram import types
from aiogram.filters import StateFilter
from bot.handlers.menu.vip import vip_main_menu

@pytest.mark.asyncio
async def test_vip_main_menu_rendering(session, mock_bot):
    """Test VIP main menu renders correctly."""
    # Create mock callback query
    callback = types.CallbackQuery(
        id="test_callback",
        from_user=types.User(id=123, is_bot=False, first_name="Test"),
        data="menu:vip",
        message=types.Message(message_id=1, date=None, chat=None, from_user=None)
    )

    # Create mock state
    from aiogram.fsm.state import StateContext
    state = AsyncMock(spec=StateContext)

    # Call handler
    await vip_main_menu(callback, state)

    # Assert menu was sent
    callback.message.edit_text.assert_called_once()
    args = callback.message.edit_text.call_args
    assert "Contenido VIP" in args[0][0]
```

### Service Testing with Mocks

```python
# tests/test_services/test_cache.py
import pytest
from unittest.mock import AsyncMock, patch
from bot.services.cache import CacheService

@pytest.mark.asyncio
async def test_cache_user_role():
    """Test caching and retrieving user role."""
    bot = AsyncMock()
    service = CacheService(bot)

    # Mock Redis
    with patch.object(service, 'get_redis') as mock_redis:
        mock_conn = AsyncMock()
        mock_redis.return_value = mock_conn

        # Set role
        await service.set_user_role(123, "vip", ttl=60)
        mock_conn.setex.assert_called_once_with("user_role:123", 60, "vip")

        # Get role
        mock_conn.get.return_value = "vip"
        role = await service.get_user_role(123)
        assert role == "vip"
```

## Performance Considerations

### Connection Pooling (asyncpg)
```python
# bot/database/engine.py (updated)
from sqlalchemy.ext.asyncio import create_async_engine
import os

def get_engine():
    """Create async engine with connection pooling."""
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///bot.db")

    # PostgreSQL: Use connection pool
    if "postgresql" in database_url:
        engine = create_async_engine(
            database_url,
            pool_size=10,           # Min connections in pool
            max_overflow=20,        # Max additional connections
            pool_pre_ping=True,     # Verify connections before use
            pool_recycle=3600,      # Recycle connections after 1h
            echo=False
        )
    else:
        # SQLite: No pooling needed
        engine = create_async_engine(database_url)

    return engine
```

### Cache Strategy
| Data Type | Cache TTL | Invalidation Strategy |
|-----------|-----------|----------------------|
| User role | 5 minutes (300s) | Invalidate on role change |
| Content package | 10 minutes (600s) | Invalidate on update |
| Menu keyboard | 1 hour (3600s) | Manual cache clear on menu changes |
| Channel info | 30 minutes (1800s) | Automatic expiration |

### Expected Performance (Railway)
| Operation | SQLite (Local) | PostgreSQL (Railway) | Redis Cache |
|-----------|----------------|----------------------|-------------|
| User role lookup | ~10ms | ~20ms (network) | ~2ms (cached) |
| Content package fetch | ~15ms | ~30ms | ~3ms |
| Menu render (5 packages) | ~50ms | ~80ms | ~20ms |
| Health check | N/A | ~100ms | ~50ms |

**Bottlenecks to watch:**
- Network latency to Railway PostgreSQL (US East region)
- Redis cache misses (cold starts after TTL expiry)
- Telegram API rate limits (30 msg/sec for bots)

## Migration Checklist

### Pre-Migration (Local)
- [ ] Update `requirements.txt` with new dependencies
- [ ] Create `bot/services/cache.py` (CacheService)
- [ ] Create `bot/health_app.py` (FastAPI health check)
- [ ] Update `bot/database/engine.py` for PostgreSQL support
- [ ] Create `alembic/` directory with migrations
- [ ] Write data migration script (`scripts/migrate_sqlite_to_postgres.py`)
- [ ] Add railway.json and Procfile
- [ ] Test locally with PostgreSQL (Docker or Railway instance)

### Migration (Railway)
- [ ] Create Railway project
- [ ] Add PostgreSQL service
- [ ] Add Redis service
- [ ] Deploy bot service (connect to existing repo)
- [ ] Set environment variables (BOT_TOKEN, ADMIN_IDS)
- [ ] Run Alembic migrations via Railway console
- [ ] Run data migration script
- [ ] Verify health check endpoint: `https://your-app.up.railway.app/health`
- [ ] Test bot commands in Telegram

### Post-Migration
- [ ] Monitor Railway metrics (CPU, memory, DB connections)
- [ ] Check Redis memory usage
- [ ] Verify all user flows (VIP/Free menus, content browsing)
- [ ] Load test with 100 concurrent users
- [ ] Set up Railway alerts (restart on crash, high memory)
- [ ] Delete SQLite backup after 7 days

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Celery** | Overkill for simple background tasks, adds Redis infrastructure complexity | APScheduler (already in use) |
| **Django ORM** | Heavier than SQLAlchemy, not async-first | SQLAlchemy 2.0 + asyncpg |
| **Memcached** | Less feature-rich than Redis (no pub/sub, limited data structures) | Redis 7.x |
| **aioredis** | Deprecated library (merged into redis-py in 2022) | `import redis.asyncio as redis` |
| **psycopg3** | Slower than asyncpg (5x), less mature async support | asyncpg |
| **Manual SQL migrations** | Error-prone, don't integrate with SQLAlchemy models | Alembic with auto-generation |
| **Hardcoded health check in bot** | Can't distinguish "bot crashed" from "Telegram API down" | Separate FastAPI health check endpoint |
| **SQLite in production** | No concurrent writes, single-file corruption risk, no connection pooling | PostgreSQL on Railway |
| **Heroku** | Expensive ($5/mo minimum), slower deploys | Railway.app (free tier, faster) |
| **Jinja2 for templates** | Overhead (50ms+), 5MB+ dependency | f-strings (already in use, <5ms) |

## Open Questions for Validation

- **Railway region selection:** Should bot deploy to US East (default) or closer to target users (e.g., EU South America for Spanish content)?
- **PostgreSQL version:** Railway defaults to PostgreSQL 16.x. Any compatibility concerns with SQLAlchemy 2.0.25? (LOW confidence - verify)
- **Redis max memory:** Default Railway Redis has 100MB limit. Is this sufficient for caching ~10k users and ~100 content packages?
- **Health check frequency:** Railway checks `/health` every 30s by default. Is this too frequent (adds load)? Can increase to 60s+.
- **Migration downtime:** Data migration from SQLite to PostgreSQL requires ~1-2 minutes of bot downtime. Is this acceptable? (Plan for low-traffic window)

## Sources

**Railway Deployment:**
- [Manually Optimize Deployments on Railway](https://blog.railway.com/p/comparing-deployment-methods-in-railway) (Dec 2024) — HIGH confidence, official Railway blog on deployment optimization
- [Railway.app - DevOps Friendly Deployment Tool](https://dev.to/kaustubhyerkade/railwayapp-devops-friendly-deployment-tool-5aab) (Dec 2025) — MEDIUM confidence, community guide
- [Debugging Railway Deployment: PORT Variables and Configuration Conflicts](https://medium.com/@tomhag_17/debugging-a-railway-deployment-my-journey-through-port-variables-and-configuration-conflicts-eb49cfb19cb8) — MEDIUM confidence, common port variable pitfalls
- [Public Networking | Railway Docs](https://docs.railway.com/guides/public-networking) — HIGH confidence, official Railway documentation

**PostgreSQL & asyncpg:**
- [Connect to PostgreSQL with SQLAlchemy and asyncio - Makimo](https://makimo.com/blog/connect-to-postgresql-with-sqlalchemy-and-asyncio) — HIGH confidence, specific to SQLAlchemy async setup
- [Asynchronous Python Postgres Drivers: A Deep Dive](https://leapcell.io/blog/asynchronous-python-postgres-drivers-a-deep-dive-into-performance-features-and-usability) (Oct 2025) — HIGH confidence, performance comparison
- [Psycopg 3 vs Asyncpg - Fernando Arteaga](https://fernandoarteaga.dev/blog/psycopg-vs-asyncpg/) (Feb 2024) — HIGH confidence, benchmarks showing asyncpg 5x faster
- [Boost Your App Performance With Asyncpg and PostgreSQL](https://www.tigerdata.com/blog/how-to-build-applications-with-asyncpg-and-postgresql) (July 2024) — MEDIUM confidence, connection pool configuration
- [asyncpg PyPI page](https://pypi.org/project/asyncpg/) — HIGH confidence, official library docs

**Redis Caching:**
- [redis-py Examples - Asyncio Examples](https://redis-py.readthedocs.io/en/stable/examples.html) — HIGH confidence, official redis-py documentation with async examples

**Alembic Migrations:**
- [FastAPI with Async SQLAlchemy, SQLModel, and Alembic](https://testdriven.io/blog/fastapi-sqlmodel/) — HIGH confidence, tutorial covering Alembic with async SQLAlchemy
- [Asynchronous SQLAlchemy 2: A simple step-by-step guide](https://dev.to/amverum/asynchronous-sqlalchemy-2-a-simple-step-by-step-guide-to-configuration-models-relationships-and-3ob3) (June 2025) — MEDIUM confidence, Alembic setup guide

**Testing:**
- [Mastering Pytest Fixtures and Async Testing](https://www.ctrix.pro/blog/pytest-fixtures-async-testing-guide) (Dec 2025) — HIGH confidence, pytest-asyncio best practices
- [Examples how to test your bot · Issue #378](https://github.com/aiogram/aiogram/issues/378) — MEDIUM confidence, aiogram community discussion on testing approaches
- [aiogram-tests GitHub](https://github.com/OCCASS/aiogram_tests) — LOW confidence, dedicated aiogram testing library (last updated Oct 2022)

**Health Checks:**
- [Building a Health-Check Microservice with FastAPI](https://dev.to/lisan_al_gaib/building-a-health-check-microservice-with-fastapi-26jo) (June 2025) — HIGH confidence, comprehensive health check patterns

**PostgreSQL Connection Strings:**
- [PostgreSQL | Railway Docs](https://docs.railway.com/guides/postgresql) — HIGH confidence, official Railway PostgreSQL setup guide
- [How to Handle Database Connection Pooling](https://blog.railway.com/p/database-connection-pooling) (Dec 2024) — HIGH confidence, Railway official blog on connection pooling

---

*Stack research for: v1.2 Primer Despliegue (Railway deployment, PostgreSQL migration, Redis caching, testing)*
*Researched: 2026-01-28*
*Python 3.12.12 | aiogram 3.4.1 | SQLAlchemy 2.0.25 | asyncpg 0.29.0+ | Railway.app (2026)*
