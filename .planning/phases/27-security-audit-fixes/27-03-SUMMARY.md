---
phase: 27-security-audit-fixes
plan: 03
subsystem: vip-entry
status: complete
completed_at: 2026-03-17
duration_seconds: 207
tasks_completed: 4
tasks_total: 4
files_created: 0
files_modified: 2
lines_changed: 115
key_decisions:
  - "Use atomic UPDATE with WHERE clause instead of SELECT-then-UPDATE pattern"
  - "Return Tuple[bool, str] for detailed error messages in advance_stage"
  - "Add validate_and_consume_entry_token for atomic token consumption"
  - "Preserve is_entry_token_valid for non-destructive UI checks"
deviations: []
commits:
  - bcce4ab
  - 1580c8d
  - 535a203
---

# Phase 27 Plan 03: VIP Entry Race Condition Fixes Summary

## Overview

Fixed critical race conditions C-005 and C-006 in `vip_entry.py` that allowed duplicate stage progression and token reuse during VIP entry flow.

**One-liner:** Atomic stage advancement with immediate token marking using conditional UPDATE with rowcount verification.

## Critical Issues Fixed

### C-005: TOCTOU en advance_stage VIP

**Problem:** Stage progression could happen multiple times if concurrent requests occurred.

**Root Cause:** SELECT-then-UPDATE pattern with time window for race condition.

**Solution:** Replaced with atomic UPDATE pattern:
```python
result = await self.session.execute(
    update(VIPSubscriber)
    .where(
        VIPSubscriber.user_id == user_id,
        VIPSubscriber.vip_entry_stage == from_stage,
        VIPSubscriber.expiry_date > datetime.utcnow(),
        VIPSubscriber.status == "active"
    )
    .values(vip_entry_stage=next_stage)
)

if result.rowcount == 0:
    # Another request already advanced the stage
    return (False, "Ya has avanzado a la etapa...")
```

### C-006: Race Condition validación token VIP

**Problem:** Token could be validated multiple times during the flow.

**Root Cause:** SELECT check followed by separate consumption step.

**Solution:** Added `validate_and_consume_entry_token()` with atomic consumption:
```python
async def validate_and_consume_entry_token(self, token: str) -> Tuple[bool, str, Optional[int]]:
    # Step 1: Get user_id BEFORE consuming (read-only)
    subscriber_data = await self.session.execute(...)

    # Step 2: Atomic UPDATE to consume token
    result = await self.session.execute(
        update(VIPSubscriber)
        .where(
            VIPSubscriber.vip_entry_token == token,
            VIPSubscriber.vip_entry_stage == 3
        )
        .values(vip_entry_stage=None, vip_entry_token=None)
    )

    if result.rowcount == 0:
        return (False, "El token ya fue utilizado...", None)
```

## Files Modified

| File | Lines Changed | Description |
|------|---------------|-------------|
| `bot/services/vip_entry.py` | +111, -44 | Race condition fixes for C-005 and C-006 |
| `bot/handlers/user/vip_entry.py` | +4, -3 | Updated handler for new return signature |

## Method Signatures Changed

| Method | Old Return | New Return | Purpose |
|--------|------------|------------|---------|
| `advance_stage` | `bool` | `Tuple[bool, str]` | Atomic stage advancement with detailed errors |
| `validate_and_consume_entry_token` | *new* | `Tuple[bool, str, Optional[int]]` | Atomic token consumption |
| `is_entry_token_valid` | `bool` | `bool` | Non-destructive UI check (preserved) |

## Commits

1. **bcce4ab** - fix(27-03): fix advance_stage race condition C-005 with atomic UPDATE
2. **1580c8d** - fix(27-03): fix token validation race condition C-006 with atomic consumption
3. **535a203** - fix(27-03): update handlers for new advance_stage return signature

## Verification

- [x] C-005 fixed: advance_stage uses atomic UPDATE with rowcount check
- [x] C-006 fixed: validate_and_consume_entry_token queries user_id BEFORE UPDATE
- [x] C-006 fixed: Token consumption uses UPDATE with rowcount check
- [x] is_entry_token_valid preserved for non-destructive checks
- [x] All handlers updated for new return signatures
- [x] Type checking passes (Python syntax validation)

## Race Condition Protection Summary

| Scenario | Before | After |
|----------|--------|-------|
| Concurrent stage advancement | Both succeed (duplicate) | Only first succeeds (rowcount=1) |
| Concurrent token consumption | Both grant access | Only first grants access (rowcount=1) |
| Token reuse after consumption | Allowed if within window | Blocked (token cleared atomically) |
| Stage mismatch | Checked after read | Enforced in WHERE clause |

## Security Impact

- **C-005:** Eliminated possibility of duplicate stage progression
- **C-006:** Eliminated possibility of token reuse for unauthorized access
- Both fixes use database-level atomicity guarantees (no application-level locks needed)
