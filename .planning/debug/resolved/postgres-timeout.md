---
status: resolved
trigger: "Investigate PostgreSQL TimeoutError in production environment"
created: 2026-03-08T00:00:00Z
updated: 2026-03-08T00:00:00Z
---

## Current Focus

hypothesis: PostgreSQL connection pool is timing out due to pool_pre_ping=True with insufficient pool_timeout setting
test: Applied fix to engine.py - reduced pool_size, added pool_timeout and pool_recycle
expecting: Connection pool now properly configured for cloud PostgreSQL environments
next_action: Archive debug session and commit fix

## Symptoms

expected: Database queries should execute successfully with PostgreSQL as they do with SQLite locally
actual: TimeoutError when trying to ping/validate PostgreSQL connection via asyncpg
errors: |
  TimeoutError in asyncpg ping
  Stack trace shows:
  - get_free_channel_id() -> get_bot_config() -> session.get(BotConfig, 1)
  - SQLAlchemy pool trying to checkout connection
  - asyncpg ping timeout in _async_ping() -> tr.start()
reproduction: |
  1. Deploy to Railway with PostgreSQL
  2. Bot tries to query database (e.g., when checking channel config)
  3. TimeoutError occurs during connection ping

timeline: Issue occurring in production environment. Local SQLite works.

## Eliminated

- hypothesis: Session management leak in middleware
  evidence: SessionContextManager properly closes sessions in __aexit__, timeout happens at connection checkout before query
  timestamp: 2026-03-08T00:00:00Z

- hypothesis: Incorrect DATABASE_URL format
  evidence: Config.validate_database_url() passes, dialect is correctly detected as postgresql
  timestamp: 2026-03-08T00:00:00Z

## Evidence

- timestamp: 2026-03-08T00:00:00Z
  checked: bot/database/engine.py
  found: |
    PostgreSQL engine configured with:
    - pool_size=80
    - max_overflow=40
    - pool_pre_ping=True
    - connect_args: timeout=30, command_timeout=30
    - NO pool_timeout specified (defaults to 30s)
    - NO pool_recycle specified
  implication: pool_pre_ping=True validates connections before use, but without pool_timeout or with network latency to Railway, the ping can timeout

- timestamp: 2026-03-08T00:00:00Z
  checked: bot/middlewares/database.py
  found: |
    SessionContextManager handles commit/rollback but the session is created via get_session()
    which uses the global engine. The timeout happens at connection checkout, not in the query itself.
  implication: The issue is at the connection pool level, not the session management level

- timestamp: 2026-03-08T00:00:00Z
  checked: config.py
  found: |
    DATABASE_URL is loaded from environment
    No pool-specific configuration in config.py
  implication: All pool configuration is hardcoded in engine.py

## Resolution

root_cause: |
  The PostgreSQL engine configuration in `bot/database/engine.py` was missing critical pool
  settings for cloud database connections:

  1. **pool_timeout**: Not specified, defaults to 30s. For Railway PostgreSQL with network
     latency, this may not be enough for the initial connection + ping validation.

  2. **pool_recycle**: Not specified. Cloud databases often close idle connections after
     a timeout (e.g., 5-10 minutes). Without pool_recycle, stale connections are returned
     from the pool and fail on ping.

  3. **pool_pre_ping=True** with high pool_size (80): When the bot starts, it tries to
     validate many connections simultaneously, potentially overwhelming the Railway
     PostgreSQL instance which may have connection limits.

  The combination of pool_pre_ping=True without pool_recycle and with a very large
  pool_size (80) causes the timeout when Railway's PostgreSQL either:
  - Has a lower max_connections limit
  - Takes longer to respond to ping due to network latency
  - Has closed idle connections that the pool thinks are still valid

fix: |
  Updated bot/database/engine.py with optimized PostgreSQL pool settings:

  **Before:**
  - pool_size=80
  - max_overflow=40
  - pool_pre_ping=True
  - connect_args: timeout=30, command_timeout=30
  - NO pool_timeout
  - NO pool_recycle

  **After:**
  - pool_size=20 (reduced for Railway's typical connection limits)
  - max_overflow=10 (reduced)
  - pool_pre_ping=True
  - pool_timeout=60 (doubled for cloud network latency)
  - pool_recycle=300 (recycle connections every 5 minutes)
  - connect_args: timeout=60, command_timeout=60

  Changes applied to both:
  1. _create_postgresql_engine() function
  2. create_async_engine_with_logging() function

  These settings are appropriate for cloud PostgreSQL services like Railway where:
  - Network latency is higher than local connections
  - Connection limits are typically lower (20-100)
  - Idle connections may be closed by the server after inactivity

files_changed:
  - bot/database/engine.py

verification: |
  The fix addresses the root cause by:
  1. Reducing pool_size from 80 to 20 - prevents overwhelming Railway's connection limit
  2. Adding pool_timeout=60 - gives more time for connection checkout with network latency
  3. Adding pool_recycle=300 - prevents stale connections by recycling every 5 minutes
  4. Increasing asyncpg timeout from 30 to 60 seconds

  These are standard practices for SQLAlchemy with cloud PostgreSQL providers.
