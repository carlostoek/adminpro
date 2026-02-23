# Phase 21 Plan 06: UTC Midnight Background Job Summary

**Plan:** 21-06 - UTC Midnight Background Job
**Phase:** 21 - Daily Rewards & Streaks
**Requirement:** STREAK-07
**Completed:** 2026-02-12

## One-Liner

Background job that runs at UTC midnight to handle streak expiration for users who missed a day, resetting both daily gift and reaction streaks while preserving longest_streak as historical record.

## What Was Built

### StreakService Expiration Methods

**`process_streak_expirations()`** (lines 474-513 in `bot/services/streak.py`)
- Finds all DAILY_GIFT streaks where `last_claim_date < today (UTC)`
- Resets `current_streak = 0` for expired streaks
- Preserves `longest_streak` as historical record
- Returns count of reset streaks
- Logs each reset with user_id and previous streak length for audit trail

**`process_reaction_streak_expirations()`** (lines 515-554 in `bot/services/streak.py`)
- Finds all REACTION streaks where `last_reaction_date < today (UTC)`
- Resets `current_streak = 0` for expired reaction streaks
- Preserves `longest_streak` as historical record
- Returns count of reset reaction streaks
- Logs each reset for analytics

### Background Task

**`expire_streaks()`** (lines 154-191 in `bot/background/tasks.py`)
- Uses `get_session()` context manager for database access
- Calls `container.streak.process_streak_expirations()`
- Calls `container.streak.process_reaction_streak_expirations()`
- Logs summary: "X daily streaks reset, Y reaction streaks reset"
- Handles exceptions with proper error logging

### Scheduler Registration

**Job Configuration** (lines 330-341 in `bot/background/tasks.py`)
- CronTrigger at UTC midnight (`hour=0, minute=0`)
- Job ID: "expire_streaks"
- Name: "Expiración de rachas diarias"
- `max_instances=1` to prevent concurrent execution
- Added to `start_background_tasks()` alongside existing jobs

## Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `bot/services/streak.py` | 474-554 | Expiration methods for both streak types |
| `bot/background/tasks.py` | 154-191, 330-341 | Background task and scheduler registration |

## Verification

- [x] Background job runs at UTC midnight (CronTrigger)
- [x] Daily streaks reset when user missed a day
- [x] Reaction streaks reset when user missed a day
- [x] Longest_streak is preserved (not reset)
- [x] Job appears in scheduler status

## Tests

All 4 expiration-specific tests pass:

```
tests/unit/services/test_streak.py::TestBackgroundJobs::test_expire_streaks_resets_missed PASSED
tests/unit/services/test_streak.py::TestBackgroundJobs::test_expire_streaks_preserves_longest PASSED
tests/unit/services/test_streak.py::TestBackgroundJobs::test_expire_streaks_skips_current PASSED
tests/unit/services/test_streak.py::TestBackgroundJobs::test_expire_reaction_streaks PASSED
```

**Test coverage:**
- Streaks reset when day missed (last_claim_date 2 days ago)
- Historical max streak kept (longest_streak unchanged)
- Today's streaks preserved (not reset if claimed today)
- Reaction streaks also expire correctly

## Commits

| Hash | Message | Files |
|------|---------|-------|
| f328d5c | feat(21-06): implement streak expiration methods in StreakService | bot/services/streak.py |
| d11e029 | feat(21-06): add expire_streaks() background task | bot/background/tasks.py |
| 7d87f48 | feat(21-06): register streak expiration job in scheduler | bot/background/tasks.py |

## Integration

The streak expiration job integrates with existing infrastructure:

```python
# In start_background_tasks()
_scheduler.add_job(
    expire_streaks,
    trigger=CronTrigger(hour=0, minute=0, timezone="UTC"),
    args=[bot],
    id="expire_streaks",
    name="Expiración de rachas diarias",
    replace_existing=True,
    max_instances=1
)
```

Works alongside existing jobs:
- `expire_vip` - VIP expiration (every 60 min)
- `process_free_queue` - Free queue processing (every 5 min)
- `cleanup_old_data` - Data cleanup (daily 3 AM UTC)
- `expire_streaks` - Streak expiration (midnight UTC) **NEW**

## Deviations from Plan

None - plan executed exactly as written.

## Next Steps

Phase 21 is now complete. All 7 requirements (STREAK-01 through STREAK-07) have been implemented:

- STREAK-01: StreakService with UTC-based tracking
- STREAK-02: Base 20 + capped bonus calculation
- STREAK-03: WalletService integration
- STREAK-04: Reaction streak tracking
- STREAK-05: Streak display in user menus
- STREAK-06: Daily gift handler with Lucien's voice
- STREAK-07: UTC midnight background job for expiration

**Next:** Phase 22 - Shop System
