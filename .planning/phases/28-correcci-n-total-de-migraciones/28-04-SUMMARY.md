---
phase: 28-correcci-n-total-de-migraciones
plan: "04"
subsystem: database
tags: [alembic, postgresql, enum, migration, transactiontype]

# Dependency graph
requires:
  - phase: 28-03
    provides: dialect-aware seed migration and partial unique index - establishes pattern for dialect-aware migrations
  - phase: 28-02
    provides: fix_shop_products_schema migration (20260320_000001) which is this migration's down_revision
provides:
  - PostgreSQL transactiontype enum sync migration with all 8 current TransactionType values
  - Idempotent ALTER TYPE IF NOT EXISTS for each required enum value
  - Explicit COMMIT before ADD VALUE loop to avoid PostgreSQL transaction block restriction
  - SQLite skip guard (no ALTER TYPE needed on SQLite)
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [explicit COMMIT before ALTER TYPE ADD VALUE on PostgreSQL, dialect-aware migration branching]

key-files:
  created:
    - alembic/versions/20260320_000002_fix_transactiontype_enum.py
  modified: []

key-decisions:
  - "Explicit COMMIT via op.execute(sa.text('COMMIT')) before ALTER TYPE ADD VALUE loop exits Alembic's implicit transaction to satisfy PostgreSQL's constraint that ADD VALUE cannot run inside a transaction block"
  - "IF NOT EXISTS on each ADD VALUE makes migration idempotent - safe to run multiple times even on databases that already have some or all values"
  - "Downgrade is documented no-op - PostgreSQL cannot remove enum values without DROP TYPE + recreate which would be destructive"

patterns-established:
  - "COMMIT-before-ALTER pattern: always issue COMMIT before ALTER TYPE ADD VALUE on PostgreSQL"
  - "Dialect guard pattern: check bind.dialect.name == 'postgresql' before any PostgreSQL-specific DDL"

# Metrics
duration: 4min
completed: 2026-03-19
---

# Phase 28 Plan 04: Fix TransactionType Enum Summary

**Alembic migration that syncs PostgreSQL transactiontype enum with all 8 current TransactionType values using explicit COMMIT to bypass transaction block restriction**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-19T05:25:00Z
- **Completed:** 2026-03-19T05:29:33Z
- **Tasks:** 1/1
- **Files modified:** 1

## Accomplishments

- Created migration `20260320_000002_fix_transactiontype_enum.py` that adds all 8 required TransactionType values to the PostgreSQL `transactiontype` enum
- Migration issues explicit `COMMIT` before the `ALTER TYPE ADD VALUE` loop to exit Alembic's implicit transaction - preventing the "cannot run inside a transaction block" PostgreSQL error
- Migration uses `IF NOT EXISTS` for every `ADD VALUE` call making it idempotent (safe to run multiple times)
- Migration skips entirely on SQLite (enum values stored as plain strings - no ALTER TYPE needed)
- Downgrade is a documented no-op with explanation of why values cannot be removed
- Revision chain: `20260320_000001` → `20260320_000002` (single head)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create fix_transactiontype_enum migration** - `3a745c2` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `alembic/versions/20260320_000002_fix_transactiontype_enum.py` - Migration adding all 8 TransactionType values to PostgreSQL enum with transaction-safe COMMIT pattern and SQLite skip guard

## Decisions Made

- Used `op.execute(sa.text("COMMIT"))` immediately before the ADD VALUE loop - this is the documented Alembic pattern for working around PostgreSQL's restriction on `ALTER TYPE ADD VALUE` inside transactions
- `IF NOT EXISTS` on each individual ADD VALUE call rather than checking existing values in Python - simpler, DB-side idempotency, works across PostgreSQL versions (9.1+)
- Downgrade is a no-op with detailed warning message - removing enum values requires destructive DROP TYPE + recreate; old values (EARN_STREAK_BONUS, SPEND_REWARD, SPEND_CONTENT) are harmless to leave in the enum

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - migration created successfully, syntax valid, alembic heads shows single head `20260320_000002`.

## User Setup Required

None - no external service configuration required. Migration runs automatically with `alembic upgrade head`.

## Next Phase Readiness

- Phase 28 is now fully complete (all 4 plans delivered including this correction plan)
- PostgreSQL transactiontype enum is fully synced with Python TransactionType enum
- All 8 transaction types (EARN_REACTION, EARN_DAILY, EARN_STREAK, EARN_REWARD, EARN_ADMIN, EARN_SHOP_REFUND, SPEND_SHOP, SPEND_ADMIN) can be inserted without cast errors on PostgreSQL
- Migration chain is clean: single head at 20260320_000002

## Self-Check: PASSED

- FOUND: alembic/versions/20260320_000002_fix_transactiontype_enum.py
- FOUND: .planning/phases/28-correcci-n-total-de-migraciones/28-04-SUMMARY.md
- FOUND: commit 3a745c2

---
*Phase: 28-correcci-n-total-de-migraciones*
*Completed: 2026-03-19*
