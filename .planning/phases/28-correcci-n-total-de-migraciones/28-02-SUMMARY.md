---
phase: 28-correcci-n-total-de-migraciones
plan: 02
subsystem: database
tags: [alembic, sqlalchemy, migrations, shop-products, gamification, index-cleanup]

# Dependency graph
requires:
  - phase: 28-01
    provides: env.py imports all 20 models; da1247eed1e3 is verified HEAD
  - phase: 22-shop-system
    provides: ShopProduct model definition with besitos_price/vip_discount_percentage/vip_besitos_price/tier
  - phase: 19-economy-foundation
    provides: user_gamification_profiles table and ix_user_gamification_profiles_user_id index
provides:
  - Migration 20260320_000001 that bridges shop_products schema gap (price/currency -> besitos_price/tier)
  - Idempotent Gap 4 resolution: normalises user_gamification_profiles user_id index to canonical name
  - Single HEAD: 20260320_000001 (parent da1247eed1e3)
affects:
  - fresh PostgreSQL/Railway deployments (shop_products now has correct columns)
  - alembic autogenerate (no more spurious diffs on shop_products or gamification index)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Use column_exists/index_exists helpers for idempotent Alembic migrations — never raw IF NOT EXISTS (SQLite unsupported)"
    - "Use batch_alter_table for column nullability changes — required for SQLite compatibility"
    - "Delete orphaned rows before enforcing NOT NULL constraint — safer than arbitrary default FK"
    - "Two-branch unique index collision: keep op.f() canonical name, drop legacy name"

key-files:
  created:
    - alembic/versions/20260320_000001_fix_shop_products_schema.py
  modified: []

key-decisions:
  - "Delete shop_products rows with NULL content_set_id rather than using a default FK — no real data exists at this stage; cleaner than patching"
  - "Use String(20) for tier column in migration (not sa.Enum) — dialect-safe; SQLAlchemy resolves ContentTier enum values to strings at the ORM layer"
  - "Drop idx_gamification_user_id when both indexes exist; recreate as ix_user_gamification_profiles_user_id when only legacy name present — normalises to op.f() convention"

patterns-established:
  - "Migration bridging pattern: detect column presence before adding/removing to handle both old and new schema states in a single idempotent migration"

# Metrics
duration: 2min
completed: 2026-03-19
---

# Phase 28 Plan 02: Fix shop_products schema Summary

**Alembic migration 20260320_000001 bridges shop_products from price/currency schema (20260223_000002) to besitos_price/vip_discount_percentage/vip_besitos_price/tier, and normalises user_gamification_profiles user_id index to canonical op.f() name**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-19T05:17:04Z
- **Completed:** 2026-03-19T05:18:54Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created migration 20260320_000001 as single HEAD child of da1247eed1e3
- upgrade() adds besitos_price (NOT NULL, backfills from price or defaults to 100), vip_discount_percentage (NOT NULL, default 0), vip_besitos_price (nullable), tier (NOT NULL String(20), default FREE)
- upgrade() removes price and currency columns if they exist, with old index cleanup
- upgrade() enforces content_set_id NOT NULL (deletes orphaned NULL rows first, then batch_alter_table)
- upgrade() adds missing indexes: idx_shop_product_active_tier, idx_shop_product_price, idx_shop_product_sort
- Gap 4 resolved: drops idx_gamification_user_id when canonical ix_user_gamification_profiles_user_id also present; renames if only legacy name exists
- All operations idempotent via column_exists/index_exists checks, SQLite+PostgreSQL compatible

## Task Commits

Each task was committed atomically:

1. **Task 1: Create fix_shop_products_schema migration** - `d2c217a` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `alembic/versions/20260320_000001_fix_shop_products_schema.py` - New migration bridging shop_products schema gap and resolving Gap 4 index collision

## Decisions Made
- Delete rows with NULL content_set_id rather than patching with a fallback FK: no real user data exists in shop_products at deployment time, and orphaned rows with no content_set cannot be used by ShopService anyway.
- Use `sa.String(length=20)` for the `tier` column in the migration rather than `sa.Enum(ContentTier)`: avoids dialect-specific enum type creation; SQLAlchemy maps the Python enum to its string value at the ORM layer, and the String column accepts those values on both SQLite and PostgreSQL.
- Keep canonical index name `ix_user_gamification_profiles_user_id` (op.f() convention) and drop legacy `idx_gamification_user_id`: the canonical name matches what a fresh `alembic revision --autogenerate` would produce, eliminating future autogenerate noise.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Migration chain has a single clean HEAD at 20260320_000001
- Fresh PostgreSQL deployments will now create shop_products with the correct columns (besitos_price, vip_discount_percentage, vip_besitos_price, tier) matching ShopProduct model
- alembic autogenerate will produce no spurious diffs on shop_products or user_gamification_profiles user_id index
- Phase 28 is now complete (2/2 plans delivered)

## Self-Check: PASSED

- alembic/versions/20260320_000001_fix_shop_products_schema.py: FOUND
- commit d2c217a: FOUND
- alembic heads shows 20260320_000001 as single head: VERIFIED
- Python syntax check: PASSED

---
*Phase: 28-correcci-n-total-de-migraciones*
*Completed: 2026-03-19*
