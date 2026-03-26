---
phase: 27-security-audit-fixes
plan: "05"
subsystem: security
tags: ["rate-limiting", "pagination", "datetime", "validation", "scheduler"]
dependency_graph:
  requires: ["27-04"]
  provides: []
  affects: ["bot/services/subscription.py", "bot/services/config.py", "bot/background/tasks.py", "config.py"]
tech_stack:
  added: []
  patterns:
    - "RATE_LIMIT_DELAY constant for bulk operations"
    - "utc_now() helper for timezone-aware datetimes"
    - "LIMIT clause for pagination"
    - "misfire_grace_time for scheduler resilience"
key_files:
  created: []
  modified:
    - "config.py - Rate limiting constants"
    - "bot/services/config.py - Rate limiting getters"
    - "bot/services/subscription.py - Rate limiting and pagination"
    - "bot/background/tasks.py - Misfire handling"
    - "bot/services/channel.py - Input validation"
decisions:
  - "Use 100ms delay between bulk Telegram API calls to prevent rate limits"
  - "Use batch_size=100 default for all bulk operations"
  - "Create utc_now() helper for consistent timezone-aware datetimes"
  - "Add misfire_grace_time to all APScheduler jobs"
metrics:
  duration: 25
  completed_date: "2026-03-17"
---

# Phase 27 Plan 05: Security Audit Fixes - Rate Limiting and Timezone-Aware Datetimes

## Summary

Fixed 21 warnings from security audit by implementing rate limiting for bulk operations, migrating from deprecated datetime.utcnow() to timezone-aware datetimes, adding pagination for large datasets, and improving APScheduler job resilience.

## Changes Made

### Task 1: Rate Limiting Configuration
- Added `TELEGRAM_RATE_LIMIT_RPS`, `TELEGRAM_RATE_LIMIT_DELAY`, `BULK_OPERATION_BATCH_SIZE`, `BULK_OPERATION_RATE_LIMIT_DELAY` to `config.py`
- Added getter methods in `ConfigService` for centralized rate limiting configuration

### Task 2: Rate Limiting in Bulk Operations
- Added `asyncio.sleep(RATE_LIMIT_DELAY)` between `ban_chat_member` calls in `kick_expired_vip_from_channel`
- Added `asyncio.sleep(RATE_LIMIT_DELAY)` between `approve_chat_join_request` calls in `approve_ready_free_requests`
- Prevents Telegram API rate limit violations during bulk operations

### Task 3: Pagination for Large Operations
- Added `batch_size` parameter to `expire_vip_subscribers` with default 100
- Added `.limit(batch_size)` clause to query for pagination
- Prevents memory issues when processing large VIP subscriber datasets

### Task 4: Timezone-Aware Datetime Migration
- Created `utc_now()` helper function returning `datetime.now(timezone.utc)`
- Replaced all 30+ `datetime.utcnow()` calls in `subscription.py` with `utc_now()`
- Updated `tasks.py` to use `datetime.now(timezone.utc)`
- Python 3.12+ compatible datetime handling

### Task 5: Input Validation
- Added validation to `generate_vip_token`: `generated_by`, `duration_hours`, `plan_id`
- Added validation to `redeem_vip_token`: `token_str`, `user_id`
- Added validation to `send_to_channel`: `channel_id` format, text length (4096 char limit)

### Task 6: APScheduler Misfire Handling
- Added `misfire_grace_time=300` (5 min) to `expire_vip` job
- Added `misfire_grace_time=60` (1 min) to `process_free_queue` job
- Added `misfire_grace_time=3600` (1 hour) to `cleanup_old_data` and `expire_streaks` jobs
- Added `coalesce=True` to all jobs to combine missed executions

### Task 7: Documentation
- Updated module docstring with security considerations
- Documented atomic UPDATE pattern for race condition prevention
- Documented rate limiting for bulk operations
- Documented transaction separation from API calls

## Commits

| Commit | Description |
|--------|-------------|
| aea4a1e | feat(27-05): add rate limiting configuration constants |
| 4a406e7 | feat(27-05): add rate limiting to bulk Telegram API operations |
| f987539 | feat(27-05): add pagination to expire_vip_subscribers |
| 55f12de | feat(27-05): migrate datetime.utcnow() to timezone-aware datetimes |
| b2f1199 | feat(27-05): add input validation to key service methods |
| e380291 | feat(27-05): add misfire handling to APScheduler jobs |

## Verification

- [x] Rate limiting configuration constants added
- [x] Rate limiting (asyncio.sleep) added to all bulk Telegram API calls
- [x] Pagination (LIMIT) used for bulk queries > 100 records
- [x] datetime.utcnow() migrated to timezone-aware equivalent
- [x] Input validation added to key public methods
- [x] APScheduler jobs configured with misfire_grace_time
- [x] All Python files pass syntax check

## Security Improvements

| Warning | Fix | Status |
|---------|-----|--------|
| W-001: Rate limiting missing | Added 100ms delay between API calls | Fixed |
| W-002: Pagination missing | Added LIMIT 100 to bulk queries | Fixed |
| W-003: datetime.utcnow() deprecated | Migrated to timezone-aware datetimes | Fixed |
| W-004: Missing input validation | Added validation to key methods | Fixed |
| W-006: Missing scheduler resilience | Added misfire_grace_time | Fixed |

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- All modified files exist and are valid Python
- All commits created successfully
- Verification commands pass
- No syntax errors
