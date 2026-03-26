---
phase: 28-correcci-n-total-de-migraciones
plan: 03
subsystem: database
tags: [alembic, migrations, sqlite, postgresql, dialect-compatibility, partial-index]

# Dependency graph
requires:
  - phase: 28-01
    provides: env.py model coverage and VIPSubscriber alignment
  - phase: 27-01
    provides: pending_request column and C-002 race condition fix
provides:
  - Dialect-aware seed migration (no PL/pgSQL DO blocks)
  - Partial unique index uq_user_pending_request enforced on ALL deployments
affects:
  - alembic migrations
  - free_channel_requests race condition protection (C-002)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dialect-aware migration pattern: bind.dialect.name branch in upgrade/downgrade"
    - "Separate index creation from column creation in migrations for unconditional enforcement"
    - "SQLite batch_alter_table for unique constraint operations"
    - "PostgreSQL pg_constraint existence guard before op.create_unique_constraint"

key-files:
  created: []
  modified:
    - alembic/versions/20260221_000001_seed_gamification_data.py
    - alembic/versions/20260317_142234_add_pending_request_column.py

key-decisions:
  - "Replace PL/pgSQL DO $$ blocks with Python dialect branches using op.get_bind().dialect.name"
  - "Move index creation OUTSIDE column existence guard so uq_user_pending_request is created on all deployments"
  - "PostgreSQL partial index uses postgresql_where='pending_request = true'; SQLite uses sqlite_where='pending_request = 1'"
  - "SQLite unique constraint uses batch_alter_table; PostgreSQL queries pg_constraint before op.create_unique_constraint"

patterns-established:
  - "Always separate structural additions (column) from constraint/index creation in migrations"
  - "Use dialect.name check not try/except for dialect-specific SQL"

# Metrics
duration: 2min
completed: 2026-03-19
---

# Phase 28 Plan 03: Fix Dialect Compatibility in Seed and Pending-Request Migrations Summary

**Removed two PL/pgSQL-only DO $$ blocks from seed migration and moved partial unique index uq_user_pending_request outside the column-existence guard so C-002 protection is enforced on all existing PostgreSQL deployments**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-19T05:22:17Z
- **Completed:** 2026-03-19T05:24:11Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Seed migration `20260221_000001` now runs on SQLite without crashing — DO $$ PL/pgSQL blocks replaced with dialect-aware Python using `bind.dialect.name`
- Pending-request migration `20260317_142234` now creates `uq_user_pending_request` as a proper partial unique index (`postgresql_where` / `sqlite_where`) matching the model definition
- Index creation moved outside `if not column_exists:` block so it runs on all databases including those where `pending_request` already existed before this migration

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix seed migration — replace PL/pgSQL DO blocks with dialect-aware Python** - `e1fc372` (fix)
2. **Task 2: Fix pending_request index — add PostgreSQL partial index support, outside column existence guard** - `67c367f` (fix)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `alembic/versions/20260221_000001_seed_gamification_data.py` - Replaced two DO $$ blocks with dialect branches using sa_inspect + batch_alter_table (SQLite) and pg_constraint query (PostgreSQL)
- `alembic/versions/20260317_142234_add_pending_request_column.py` - Restructured to separate column block from index block; added uq_user_pending_request partial unique index with correct WHERE syntax per dialect; added `from sqlalchemy import inspect`

## Decisions Made

- Used `bind.dialect.name == 'postgresql'` branch instead of try/except for cleaner dialect detection
- SQLite unique constraint requires `batch_alter_table` (SQLite limitation); PostgreSQL uses `op.create_unique_constraint` directly
- Index section in pending-request migration is unconditional (guarded only by index existence, not column existence) to enforce C-002 on all existing deployments

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 28 complete: all 3 migration correction plans delivered
- Both migrations are now SQLite and PostgreSQL compatible
- C-002 race condition protection (partial unique index on free_channel_requests) enforced on ALL deployments
- No blockers for deployment

## Self-Check: PASSED

- alembic/versions/20260221_000001_seed_gamification_data.py — FOUND
- alembic/versions/20260317_142234_add_pending_request_column.py — FOUND
- .planning/phases/28-correcci-n-total-de-migraciones/28-03-SUMMARY.md — FOUND
- Commit e1fc372 — FOUND
- Commit 67c367f — FOUND

---
*Phase: 28-correcci-n-total-de-migraciones*
*Completed: 2026-03-19*
