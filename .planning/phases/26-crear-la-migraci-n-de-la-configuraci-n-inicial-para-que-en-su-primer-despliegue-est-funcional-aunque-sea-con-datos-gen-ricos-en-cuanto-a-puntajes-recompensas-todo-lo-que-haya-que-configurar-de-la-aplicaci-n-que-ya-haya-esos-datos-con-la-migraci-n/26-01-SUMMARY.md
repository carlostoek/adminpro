---
phase: 26-initial-data-migration
plan: 01
type: execute
subsystem: database
tags: [migration, gamification, seed-data, alembic]
dependency_graph:
  requires: []
  provides: [gamification-defaults]
  affects: [bot_config, user_gamification_profiles, rewards]
tech_stack:
  added: []
  patterns: [data-migration, idempotent-sql]
key_files:
  created:
    - alembic/versions/20260221_000001_seed_gamification_data.py
  modified:
    - .gitignore
decisions:
  - idempotent-design-pattern
  - preserve-user-data-on-downgrade
  - data-migration-in-git
metrics:
  duration: 5m
  completed_date: 2026-02-21
---

# Phase 26 Plan 01: Initial Data Migration Summary

## Overview

Created the Alembic data migration that seeds default gamification configuration and backfills existing users with gamification profiles. This ensures the production database has all necessary default data for the gamification module to function immediately after deployment, without requiring manual configuration.

## What Was Built

### Migration File: `alembic/versions/20260221_000001_seed_gamification_data.py`

A comprehensive data migration with three main operations:

#### 1. BotConfig Economy Defaults
Updates the singleton BotConfig record (id=1) with default economy values:
- `level_formula`: `floor(sqrt(total_earned / 100)) + 1`
- `besitos_per_reaction`: 5
- `besitos_daily_gift`: 50
- `besitos_daily_streak_bonus`: 10
- `max_reactions_per_day`: 20
- `besitos_daily_base`: 20
- `besitos_streak_bonus_per_day`: 2
- `besitos_streak_bonus_max`: 50

#### 2. User Profile Backfill
Creates UserGamificationProfile records for all existing users who don't have one:
- Default balance: 0
- Default total_earned: 0
- Default total_spent: 0
- Default level: 1
- Uses `INSERT OR IGNORE` for idempotency

#### 3. Default Rewards Seeding
Seeds three initial achievements:
1. **Primeros Pasos** - First reaction reward (10 besitos)
2. **Ahorrador Principiante** - Save 100 besitos badge (emoji: 💰)
3. **Racha de 7 Dias** - 7-day streak reward (50 besitos)

### Key Design Decisions

#### Idempotent Design
- Uses `UPDATE...WHERE id=1` for BotConfig (safe to run multiple times)
- Uses `INSERT OR IGNORE` for SQLite to prevent duplicate errors
- Uses `INSERT...SELECT...WHERE NOT EXISTS` pattern for user backfill
- Migration can be safely re-run without creating duplicates

#### Safety-First Downgrade
- Downgrade ONLY resets BotConfig economy fields to NULL
- User gamification profiles are PRESERVED (production safety)
- Rewards are NOT deleted (to avoid losing user achievement history)
- User data integrity is prioritized over clean downgrade

#### Git Integration
- Updated `.gitignore` to include exception for data migrations
- Data migrations (unlike auto-generated schema migrations) are committed to version control
- Ensures consistent seed data across all environments

## Verification

All verification checks passed:
- ✅ Valid Python syntax
- ✅ revision variable defined
- ✅ down_revision points to 20260217_000001
- ✅ upgrade() function with three op.execute() calls
- ✅ downgrade() function that resets BotConfig
- ✅ Uses INSERT OR IGNORE for idempotency
- ✅ Proper JSON formatting for reward_value

## Revision Chain

```
20260217_000001_fix_reaction_unique_constraint_add_emoji
                    ↓
    20260221_000001_seed_gamification_data (this migration)
```

## Files Changed

| File | Change |
|------|--------|
| `alembic/versions/20260221_000001_seed_gamification_data.py` | Created - Data migration file |
| `.gitignore` | Modified - Added exception for data migration |

## Commits

- `f9335d6`: feat(26-01): create alembic data migration for gamification seed data

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- [x] Migration file exists at `alembic/versions/20260221_000001_seed_gamification_data.py`
- [x] Contains `revision = '20260221_000001'`
- [x] Contains `down_revision = '20260217_000001'`
- [x] Contains `def upgrade()` with three op.execute() calls
- [x] Contains `def downgrade()` that resets BotConfig
- [x] Uses `INSERT OR IGNORE` for idempotency
- [x] Uses proper JSON formatting for reward_value
- [x] Commit hash f9335d6 exists in git log

## Next Steps

This migration is ready to be applied to production databases. When deployed:
1. Run `alembic upgrade head` to apply the migration
2. All existing users will get gamification profiles
3. Default rewards will be available in the system
4. Economy configuration will be active with sensible defaults
