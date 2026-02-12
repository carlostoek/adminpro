---
phase: 21
plan: 21-02
subsystem: gamification
tags: [streak, daily-gift, service, besitos]
requires: [21-01]
provides: [21-03]
affects: [21-03, 21-04]
tech-stack.added: []
tech-stack.patterns: [lazy-loading, utc-boundaries, atomic-operations]
key-files.created:
  - bot/services/streak.py
key-files.modified:
  - bot/services/container.py
  - tests/fixtures/database.py
decisions:
  - Streak bonus caps at 50 besitos (25 days)
  - UTC-based day boundaries for global consistency
  - No grace period for missed days (resets immediately)
  - WalletService injected for besitos crediting
duration: 25min
completed: 2026-02-12
---

# Phase 21 Plan 02: StreakService - Core Logic Summary

## One-Liner
Created StreakService with UTC-based daily gift tracking, streak calculation with capped bonus (base 20 + max 50), and WalletService integration for automatic besitos crediting.

## What Was Built

### StreakService (`bot/services/streak.py`)
Core service for managing user streaks in the gamification system:

**Constructor:**
- Accepts `AsyncSession` and optional `WalletService` for besitos crediting
- Stores logger for operation tracking

**Key Methods:**
- `_get_or_create_streak(user_id, streak_type)` - Gets or creates UserStreak record
- `_get_utc_date(dt)` - Helper for UTC day boundary calculations
- `can_claim_daily_gift(user_id)` - Returns (bool, str) for availability check
- `calculate_streak_bonus(current_streak)` - Returns (base, bonus, total) tuple
- `claim_daily_gift(user_id)` - Processes claim with streak calculation and besitos credit
- `get_streak_info(user_id, streak_type)` - Returns current streak state dict
- `reset_streak(user_id, streak_type)` - Resets current_streak to 0 (background job)
- `update_reaction_streak(user_id)` - Updates reaction streak on new reaction

**Streak Logic:**
- Base: 20 besitos per daily gift claim
- Bonus: min(current_streak * 2, 50) besitos
- Consecutive day: streak + 1
- Missed day: reset to 1
- Same day claim: rejected with time until next claim

### ServiceContainer Integration (`bot/services/container.py`)
- Added `_streak_service` field for lazy loading
- Added `@property streak` with WalletService injection
- Added "streak" to `get_loaded_services()`

### Test Fixtures (`tests/fixtures/database.py`)
- Added `UserStreak` import to ensure table creation in tests

## Verification Results

All 35 StreakService tests pass:
- ✅ Service creation with/without wallet injection
- ✅ `_get_or_create_streak` creates and retrieves records
- ✅ UTC date boundary calculations
- ✅ `can_claim_daily_gift` correctly identifies same-day claims
- ✅ Streak increments on consecutive days
- ✅ Streak resets to 1 after missing a day
- ✅ Bonus calculation caps at 50 besitos
- ✅ `claim_daily_gift` credits besitos via WalletService
- ✅ `get_streak_info` returns complete streak state
- ✅ `reset_streak` preserves longest_streak
- ✅ `update_reaction_streak` handles reaction streaks
- ✅ ServiceContainer integration with lazy loading

All 118 service tests pass (including existing wallet, reaction tests).

## Goal-Backward Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| STREAK-01: Tracks daily gift availability per 24h period | ✅ | `can_claim_daily_gift()` uses UTC date comparison |
| STREAK-02: Streak bonus calculation (base + capped bonus) | ✅ | `calculate_streak_bonus()` caps at 50 besitos |
| STREAK-03: Streak increments for consecutive claims | ✅ | Tests verify streak +1 on consecutive day |
| STREAK-04: Streak resets when missed | ✅ | Tests verify reset to 1 after missed day |

## Deviations from Plan

None - plan executed exactly as written.

## Commits

1. `3ad01fb` - feat(21-02): create StreakService with core streak tracking logic
2. `eec7dc6` - feat(21-02): add streak service to ServiceContainer
3. `1eaf0de` - test(21-02): add comprehensive tests for StreakService

## Next Steps

Plan 21-03: Daily Gift Handler - Create user-facing handler for claiming daily gifts with StreakService integration.
