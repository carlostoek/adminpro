# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-28)

**Core value:** Consistencia absoluta en la voz de Lucien: cada mensaje del bot debe sonar elegante, misterioso y natural viniendo del mayordomo, sin importar que handler o flujo lo invoque.
**Current focus:** Phase 16 complete - Moving to Phase 17 (System Tests)

## Current Position

Phase: 18 of 18 (Admin Test Runner & Performance Profiling)
Plan: 4 of 4 in current phase
Status: Complete - Phase 18 finished
Last activity: 2026-01-30 — Completed Plan 18-04 (SQLite to PostgreSQL Migration and N+1 Query Detection)

Progress: [████████████████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 62
- Average duration: ~10.6 min
- Total execution time: ~15.5 hours

**By Phase:**

| Phase | Plans | Total Time | Avg/Plan |
|-------|-------|------------|----------|
| v1.0 (Phases 1-4) | 14 | ~2 hours | ~8.6 min |
| v1.1 (Phases 5-13) | 48 | ~10.2 hours | ~12.8 min |
| v1.2 (Phase 14) | 4 | ~25 min | ~6.3 min |
| v1.2 (Phase 15) | 5 | ~35 min | ~7.0 min |
| v1.2 (Phase 16) | 5 | ~2 hours | ~24 min |

**Recent Trend:**
- Last 5 plans: Phase 16 complete (Testing Infrastructure)
- Trend: Stable with comprehensive test infrastructure

## Accumulated Context

### Decisions

See PROJECT.md Key Decisions table for full decision log.

**v1.2 Key Decisions:**
- Phase 14: PostgreSQL migration with Alembic for production deployment
- Phase 14: Database abstraction layer for SQLite/PostgreSQL switching via DATABASE_URL
- Phase 14: Auto-inject drivers when URL lacks them (sqlite:// -> sqlite+aiosqlite://)
- Phase 14: QueuePool for PostgreSQL (pool_size=5, max_overflow=10)
- Phase 14: NullPool for SQLite (no pooling needed)
- Phase 14: PRAGMA optimizations only applied to SQLite connections
- Phase 14: Alembic configured with async engine and dialect detection (14-02a)
- Phase 14: Initial migration generated with all 9 models (14-02b)
- Phase 14: .gitignore strategy: ignore all migrations, allow initial baseline (14-02b)
- Phase 14: Helper script (scripts/migrate.py) for manual migration operations (14-02b)
- Phase 14: Timestamp-based migration naming (YYYYMMDD_HHMMSS_slug.py) for chronological ordering
- Phase 14: compare_type=True enabled for type compatibility across dialects (DBMIG-06)
- Phase 14: Auto-migration on production startup via ENV=production (14-03)
- Phase 14: Fail-fast behavior on migration failure prevents bot startup (14-03)
- Phase 14: Rollback procedures documented in docs/ROLLBACK.md (DBMIG-07)
- Phase 15: FastAPI health check endpoint for Railway monitoring
- Phase 15: Railway deployment preparation (NOT execution - deployment in v1.3+)
- Phase 15-01: uvicorn without [standard] extra due to uvloop build failure on Termux ARM
- Phase 15-02: Concurrent execution of bot and health API using asyncio tasks (15-02 complete)
- Phase 15-02: Shared event loop pattern for bot and FastAPI server (15-02 complete)
- Phase 15-02: Graceful shutdown with 5-second timeout for health API (15-02 complete)
- Phase 15-03: Railway.toml deployment configuration with health check monitoring (15-03 complete)
- Phase 15-03: Multi-stage Docker build with non-root user for security (15-03 complete)
- Phase 15-03: Health check timeout of 300s allows time for DB migrations on Railway (15-03 complete)
- Phase 15-03: .dockerignore for optimized Docker builds excluding dev artifacts (15-03 complete)
- Phase 15-04: WEBHOOK_MODE defaults to "polling" for local development (no breaking changes)
- Phase 15-04: validate_required_vars() returns (is_valid, missing_vars) tuple for detailed error reporting
- Phase 15-04: WEBHOOK_SECRET is optional but logged as warning when missing in webhook mode (15-04 complete)
- Phase 15-04: Health check API works independently of bot mode (starts in both polling and webhook)
- Phase 15-04: Environment variable validation with clear error messages for missing/invalid variables
- Phase 15-04: Webhook/polling mode switching infrastructure in place (15-04 complete)
- Phase 15-05: Graceful shutdown fix with reduced aiohttp and polling timeouts (15-05 complete)
- Phase 15-05: AiohttpSession timeout reduced from 120s to 10s for responsive Ctrl+C (15-05 complete)
- Phase 15-05: start_polling timeout reduced from 30s to 10s for responsive shutdown (15-05 complete)
- Phase 15-05: Enhanced shutdown logging with progress messages and timeout expectations (15-05 complete)
- Phase 15-05: Bot now responds to Ctrl+C within 1-2 seconds (was 150 seconds) (15-05 complete)
- Phase 15-05: No orphaned processes after shutdown; immediate restart capability (15-05 complete)
- Phase 16-01: pytest-asyncio configured with asyncio_mode=auto (no decorators needed)
- Phase 16-02: Core test fixtures created (test_db, mock_bot, container, container_with_preload)
- Phase 16-02: In-memory SQLite for isolated test databases
- Phase 16-02: ServiceContainer fixture with dependency injection for tests
- Phase 16-03: In-memory SQLite database with WAL mode and foreign keys
- Phase 16-03: BotConfig singleton auto-seeding with test defaults
- Phase 16-03: Database isolation verification tests (16 tests, 13 passing)
- Phase 16-04: Transaction rollback isolation between tests (session.rollback())
- Phase 16-04: 27 isolation verification tests (test_isolation.py, test_cleanup.py)
- Phase 16-04: BotConfig singleton modifications properly rolled back between tests
- Phase 16-05: Coverage reporting configured with pytest-cov and .coveragerc
- Phase 16-05: Branch coverage enabled for thorough measurement
- Phase 16-05: Coverage exclusions for tests, migrations, venv, scripts configured
- Phase 16-05: HTML and XML coverage reports supported
- Phase 16-05: scripts/coverage.py helper for convenient coverage runs
- Phase 17-01: System startup tests with 44 tests covering database initialization, ServiceContainer lazy loading, BotConfig singleton, background tasks, configuration validation, and health checks
- Phase 17-02: Menu system tests with 54 tests covering Admin/VIP/Free menus, role-based routing, FSM state management, callback navigation
- Phase 17-03: Role detection and user management tests with 57 tests covering role priority (Admin > VIP > Free), stateless behavior, user operations, audit logging
- Phase 17-04: VIP/Free flow tests and message provider tests with 57 tests covering token lifecycle, queue processing, all 13 message providers, Lucien voice consistency
- Phase 17: Comprehensive test coverage for all critical flows (complete)
- Phase 18-01: Admin test runner with CLI script and Telegram /run_tests command (complete)
- Phase 18-02: Test reporting with coverage, trends, and multi-format output (complete)
- Phase 18-03: Performance profiling with pyinstrument integration (complete)
- Phase 18-04: SQLite to PostgreSQL migration script with validation and N+1 query detection (complete)
- **v1.2: Redis caching DEFERRED to v1.3 (out of scope)**

**v1.1 Key Decisions:**
- Role detection is stateless (no caching) - always recalculates from fresh sources
- Priority order: Admin > VIP > Free (first match wins)
- Numeric(10,2) instead of Float for price field (currency precision)
- 5-minute debounce window for interest notifications
- Content packages sorted by price (free first, then paid ascending)
- In-memory pagination (10 items/page for content, 20 for users)
- VIP entry flow uses plain text (no HTML) for dramatic narrative
- 64-character unique tokens for VIP entry with 24h expiry
- Eager loading (selectinload) for relationships to prevent MissingGreenlet errors

### Pending Todos

None.

### Blockers/Concerns

**Research Gaps to Address (from research/SUMMARY.md):**

- **Phase 14:** Alembic auto-migration on startup patterns implemented. Best practice for running migrations in Railway deployment environment implemented with ENV=production detection.
- **Phase 16:** aiogram FSM testing patterns with pytest-asyncio for aiogram 3.4.1 needs verification. Manual mocking approaches need validation.
- **Phase 18:** pyinstrument validated for async code profiling. Statistical profiling with low overhead confirmed working.

**Resolved in v1.1:**
- Phase 5 gap: RoleDetectionMiddleware properly registered in main.py
- Enum format mismatch: Fixed to use uppercase values
- Interest notification NoneType error: Fixed with eager loading
- MissingGreenlet error: Applied eager loading with selectinload()
- Role change confirmation callback parsing: Fixed index checking

**Phase 18-01 Key Decisions:**
- Subprocess execution prevents test crashes from affecting the bot (asyncio.create_subprocess_exec)
- Lock-based concurrency prevents multiple simultaneous test runs (asyncio.Lock)
- HTML formatting for Telegram with automatic truncation at 4000 chars
- Three admin commands: /run_tests, /test_status, /smoke_test

**Phase 18-02 Key Decisions:**
- Use async file operations for history to avoid blocking bot (asyncio.create_task)
- Cache last test result in memory for failure detail retrieval
- Generate HTML reports on-demand only (not by default)
- Sanitize file paths to hide sensitive project structure
- Store lightweight TestRunRecord in history (no full stdout)

**Phase 18-03 Key Decisions:**
- Use pyinstrument for statistical profiling (low overhead ~5-10%)
- Gate profiling with PROFILE_HANDLERS env var for production safety
- Support text, HTML (flame graphs), and JSON output formats
- CLI script uses real database session for accurate profiling
- SQLAlchemy event monitoring via before_cursor_execute/after_cursor_execute
- MagicMock detection to avoid attaching events to mock sessions

**Phase 18-04 Key Decisions:**
- N+1 detection threshold: 5 similar queries (configurable via class constant)
- Slow query threshold: 100ms (configurable via SLOW_QUERY_THRESHOLD)
- Migration batch size: 100 rows per INSERT for memory efficiency
- Debug mode: Opt-in parameter (not env var) for flexibility
- Eager loading: Explicit methods (backward compatible, doesn't change defaults)
- Migration validation: Row count verification for all tables
- Query analysis: Context manager pattern for scoped monitoring

## Session Continuity

Last session: 2026-01-30 (Phase 18-04 execution)
Stopped at: Completed Plan 18-04 (SQLite to PostgreSQL Migration and N+1 Query Detection)
Resume file: None
Next: Phase 18 COMPLETE - All 4 plans finished

---

*State updated: 2026-01-30 after Plan 18-04 completion*
*Phase 18 (Admin Test Runner & Performance Profiling) is now COMPLETE*

---

*State updated: 2026-01-30 after Plan 18-03 completion*
