# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-28)

**Core value:** Consistencia absoluta en la voz de Lucien: cada mensaje del bot debe sonar elegante, misterioso y natural viniendo del mayordomo, sin importar que handler o flujo lo invoque.
**Current focus:** Phase 15 - Health Check & Railway Preparation

## Current Position

Phase: 15 of 18 (Health Check & Railway Preparation)
Plan: 2 of 4 in current phase
Status: In progress
Last activity: 2026-01-29 — Completed Plan 15-02 (Concurrent Bot and Health API Execution)

Progress: [████████████░░░░░░░] 85%

## Performance Metrics

**Velocity:**
- Total plans completed: 54
- Average duration: ~11.1 min
- Total execution time: ~13.0 hours

**By Phase:**

| Phase | Plans | Total Time | Avg/Plan |
|-------|-------|------------|----------|
| v1.0 (Phases 1-4) | 14 | ~2 hours | ~8.6 min |
| v1.1 (Phases 5-13) | 48 | ~10.2 hours | ~12.8 min |
| v1.2 (Phase 14) | 4 | ~25 min | ~6.3 min |
| v1.2 (Phase 15) | 2 | ~15 min | ~7.5 min |

**Recent Trend:**
- Last 5 plans: Phase 15-02 completed (Concurrent Bot and Health API Execution)
- Trend: Stable

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
- Phase 16: pytest-asyncio with in-memory SQLite for test isolation
- Phase 17: Comprehensive test coverage for all critical flows
- Phase 18: Admin test runner for non-technical users
- Phase 18: Performance profiling with pyinstrument for bottleneck identification
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
- **Phase 18:** pyinstrument vs cProfile for async code needs validation. Async profiling tools are evolving.

**Resolved in v1.1:**
- Phase 5 gap: RoleDetectionMiddleware properly registered in main.py
- Enum format mismatch: Fixed to use uppercase values
- Interest notification NoneType error: Fixed with eager loading
- MissingGreenlet error: Applied eager loading with selectinload()
- Role change confirmation callback parsing: Fixed index checking

## Session Continuity

Last session: 2026-01-29 (Phase 15 execution)
Stopped at: Completed Plan 15-02 (Concurrent Bot and Health API Execution)
Resume file: None
Next: Execute Plan 15-03 (Health Check Response Enhancement)

---

*State updated: 2026-01-29 after Plan 15-02 completion*
