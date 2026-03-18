---
phase: 27-security-audit-fixes
plan: 04
type: summary
subsystem: security
completed_date: 2026-03-17
duration: 15m

requires:
  - "27-01"
  - "27-02"

provides:
  - "Atomic role changes with Telegram-first pattern"
  - "Short transactions separated from API calls"

affects:
  - "bot/services/user_management.py"
  - "bot/services/subscription.py"

tech_stack:
  added: []
  patterns:
    - "Telegram-first pattern for role changes"
    - "Explicit transaction phases: SELECT → API → UPDATE/commit"
    - "SQLite-compatible atomic operations"

key_files:
  created: []
  modified:
    - bot/services/user_management.py
    - bot/services/subscription.py

decisions:
  - "Use explicit session.commit() instead of session.flush() to end transactions"
  - "Avoid re-querying after commit to prevent implicit transactions"
  - "Use UPDATE statements instead of ORM attribute assignment for clarity"

metrics:
  tasks_completed: 4
  files_modified: 2
  commits: 4
  issues_fixed:
    - "C-007: Atomicity failure in role changes"
    - "C-008: Long transactions during Telegram API calls"
---

# Phase 27 Plan 04: Atomicity and Transaction Safety Fixes

## Summary

Fixed critical atomicity issues C-007 and C-008 that caused inconsistent state between database and Telegram when API calls failed. Implemented separated transaction phases to ensure database locks are never held during slow Telegram API operations.

## Tasks Completed

### Task 1: Fix change_user_role Atomicity (C-007) ✅
**Commit:** 691803a

Restructured `change_user_role` to use Telegram-first pattern:
- All Telegram operations execute BEFORE any DB writes
- If Telegram fails, return error without touching DB (consistent state)
- Only update DB after Telegram succeeds
- Clear error messages for each failure mode

### Task 2: Fix expel_user_from_channels Atomicity ✅
**Commit:** ea7e4fd

Updated `expel_user_from_channels` with same Telegram-first pattern:
- Validation happens first (read-only)
- Telegram operations execute before any DB changes
- Simplified error handling with best-effort expulsion
- Tracks kicked_from_channel_at for VIP subscribers

### Task 3: Fix Long Transactions in approve_ready_free_requests (C-008) ✅
**Commit:** eeec528

Optimized transaction phases:
- Phase 1: SELECT candidates (read-only)
- Phase 2: UPDATE with rowcount check + explicit commit
- Phase 3: Telegram API calls (no DB locks held)
- Removed unnecessary re-query after commit
- Uses user_id_map directly instead of second SELECT

### Task 4: Fix Long Transactions in kick_expired_vip_from_channel (C-008) ✅
**Commit:** 12468da

Restructured to three explicit phases:
- **PHASE 1:** SELECT only (read-only, no transaction held)
- **PHASE 2:** Telegram API calls (no DB locks held)
- **PHASE 3:** UPDATE with explicit session.commit()
- Replaced session.flush() with session.commit()
- Uses UPDATE statement instead of ORM attribute assignment
- SQLite-compatible (no async with begin())

## Key Changes

### Transaction Pattern

Before (vulnerable to C-008):
```python
# BEGIN TRANSACTION
result = await session.execute(select(...))  # Get records
for record in result:
    await bot.ban_chat_member(...)  # Slow API call WITH lock held
    record.kicked = datetime.now()
await session.flush()  # Still in transaction
# COMMIT (finally releases locks)
```

After (fixed):
```python
# PHASE 1: Read-only
result = await session.execute(select(...))

# PHASE 2: API calls (no transaction)
for record in result:
    await bot.ban_chat_member(...)  # No locks held

# PHASE 3: Short write transaction
await session.execute(update(...))
await session.commit()  # Explicit commit
```

### Atomicity Pattern (C-007)

Before (vulnerable):
```python
user.role = new_role  # DB updated first
await session.flush()
await bot.ban_chat_member(...)  # If this fails, DB is inconsistent
```

After (fixed):
```python
await bot.ban_chat_member(...)  # Telegram first
if failed:
    return (False, "Telegram error")  # DB never touched

user.role = new_role  # Only after Telegram succeeds
await session.flush()
```

## Verification

All functions now follow the correct patterns:

| Function | C-007 Fixed | C-008 Fixed | Pattern |
|----------|-------------|-------------|---------|
| change_user_role | ✅ | N/A | Telegram-first |
| expel_user_from_channels | ✅ | N/A | Telegram-first |
| approve_ready_free_requests | N/A | ✅ | Explicit commit before API |
| kick_expired_vip_from_channel | N/A | ✅ | Three-phase separation |

## Commits

1. `691803a` - fix(27-04): fix C-007 atomicity in change_user_role
2. `ea7e4fd` - fix(27-04): fix expel_user_from_channels atomicity
3. `eeec528` - fix(27-04): optimize approve_ready_free_requests
4. `12468da` - fix(27-04): fix C-008 long transaction in kick_expired_vip_from_channel

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- [x] C-007 fixed: change_user_role does Telegram operations before DB update
- [x] C-008 fixed: approve_ready_free_requests uses explicit commit before API calls
- [x] C-008 fixed: kick_expired_vip_from_channel uses explicit commit and three-phase pattern
- [x] No long-running transactions during Telegram API calls
- [x] SQLite-compatible (no SKIP LOCKED, no async with begin())
- [x] Proper error messages for each failure mode
- [x] All modified files compile successfully (python -m py_compile)
