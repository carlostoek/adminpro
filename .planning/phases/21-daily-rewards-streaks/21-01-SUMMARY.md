---
phase: 21
plan: 01
subsystem: database
status: completed
duration: 113s
completed: 2026-02-12
tech-stack.added: []
tech-stack.patterns:
  - SQLAlchemy declarative model
  - Enum-based type safety
  - Composite unique constraints
  - Database indexing for leaderboards
key-files.created:
  - None (modified existing)
key-files.modified:
  - bot/database/enums.py
  - bot/database/models.py
  - bot/database/__init__.py
dependencies.requires: []
dependencies.provides:
  - UserStreak model for streak tracking
  - StreakType enum for streak types
  - BotConfig streak configuration
---

# Phase 21 Plan 01: Database Model - UserStreak Summary

## One-Liner
Created UserStreak database model with StreakType enum (DAILY_GIFT, REACTION) and BotConfig streak configuration fields.

## What Was Built

### 1. StreakType Enum (`bot/database/enums.py`)
- **DAILY_GIFT**: For daily gift claim streaks
- **REACTION**: For consecutive days with reactions streaks
- Includes `display_name` and `emoji` properties for UI rendering

### 2. UserStreak Model (`bot/database/models.py`)
Database model with fields:
- `id`: Integer PK, autoincrement
- `user_id`: BigInteger FK to users.user_id
- `streak_type`: Enum(StreakType) - DAILY_GIFT or REACTION
- `current_streak`: Integer, default 0
- `longest_streak`: Integer, default 0
- `last_claim_date`: DateTime nullable (for DAILY_GIFT)
- `last_reaction_date`: DateTime nullable (for REACTION)
- `created_at`: DateTime default utcnow
- `updated_at`: DateTime default utcnow with onupdate

**Indexes:**
- `idx_user_streak_type`: Unique on (user_id, streak_type)
- `idx_streak_type_current`: Composite on (streak_type, current_streak) for leaderboards

### 3. BotConfig Streak Configuration (`bot/database/models.py`)
Added fields to BotConfig model:
- `besitos_daily_base`: Integer default 20 (base besitos for daily claim)
- `besitos_streak_bonus_per_day`: Integer default 2
- `besitos_streak_bonus_max`: Integer default 50
- `streak_display_format`: String default "🔥 {days} days"

### 4. Module Export (`bot/database/__init__.py`)
- Added UserStreak to imports and __all__ exports

## Verification Results

All verification checks passed:
- ✅ UserStreak model can be imported from bot.database
- ✅ StreakType enum has DAILY_GIFT and REACTION values
- ✅ Unique constraint on (user_id, streak_type) configured
- ✅ Model has proper __repr__ method
- ✅ Composite index for leaderboards exists
- ✅ BotConfig has all streak configuration fields

## Commits

| Commit | Message | Files |
|--------|---------|-------|
| b8d31dc | feat(21-01): add StreakType enum | bot/database/enums.py |
| 622958e | feat(21-01): create UserStreak model | bot/database/models.py |
| 1f903e7 | feat(21-01): add streak configuration to BotConfig | bot/database/models.py |
| 49aadfc | feat(21-01): export UserStreak in database module | bot/database/__init__.py |

## Deviations from Plan

None - plan executed exactly as written.

## Next Steps

This plan provides the database foundation for Phase 21. Next plans will implement:
- StreakService for streak calculation and management
- Daily gift claim flow with streak bonuses
- Reaction streak tracking integration
- Background job for streak expiration at UTC midnight
