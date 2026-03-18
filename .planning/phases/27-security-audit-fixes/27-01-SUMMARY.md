---
phase: 27-security-audit-fixes
plan: 01
type: security-fix
subsystem: subscription-service
tags: [race-condition, security, sqlite, atomic-operations]
dependencies:
  requires: []
  provides: [C-001-fix, C-002-fix]
  affects: [bot/services/subscription.py, bot/database/models.py]
tech-stack:
  added: []
  patterns:
    - "Atomic UPDATE with rowcount check for SQLite"
    - "INSERT with IntegrityError handling for race condition protection"
    - "Partial unique constraint with sqlite_where"
key-files:
  created: []
  modified:
    - bot/services/subscription.py
    - bot/database/models.py
    - tests/test_system/test_free_flow.py
    - tests/test_integration.py
    - tests/test_e2e_flows.py
decisions:
  - "Use UPDATE with WHERE clause and rowcount check instead of SELECT-then-UPDATE for C-001"
  - "Use INSERT with IntegrityError handling instead of SELECT-then-INSERT for C-002 (SQLite-compatible)"
  - "Add pending_request boolean column for partial unique constraint on FreeChannelRequest"
  - "Update return signature to Tuple[bool, str, Optional[FreeChannelRequest]] for better error handling"
metrics:
  duration: "25 minutes"
  completed_date: "2026-03-17"
  tasks: 4
  files_modified: 5
  lines_changed: ~150
---

# Phase 27 Plan 01: Race Condition Fixes Summary

## Overview

Fixed critical race conditions C-001 and C-002 in subscription.py that allowed economic bypass through token reuse and spam requests. Implemented SQLite-compatible atomic database operations with proper locking and constraints.

## Critical Issues Fixed

### C-001: Race Condition in redeem_vip_token

**Problem:** Token could be redeemed multiple times by concurrent requests due to SELECT-then-UPDATE pattern creating a TOCTOU window.

**Solution:** Replaced with atomic UPDATE with WHERE clause and rowcount check:

```python
# Atomic UPDATE: mark token as redeemed ONLY if not already redeemed
result = await self.session.execute(
    update(InvitationToken)
    .where(
        InvitationToken.token == token_str,
        InvitationToken.used == False,
        InvitationToken.expires_at > datetime.utcnow()
    )
    .values(used=True, used_by=user_id, used_at=datetime.utcnow())
)

if result.rowcount == 0:
    # Token was already redeemed, expired, or doesn't exist
    return (False, "Token inválido, expirado o ya fue usado", None)
```

### C-002: Race Condition in create_free_request

**Problem:** User could spam multiple Free requests before first was processed due to SELECT-then-INSERT pattern.

**Solution:**
1. Added `pending_request` boolean column to FreeChannelRequest
2. Added partial unique constraint: `(user_id, pending_request) WHERE pending_request = True`
3. Replaced with atomic INSERT with IntegrityError handling:

```python
try:
    request = FreeChannelRequest(
        user_id=user_id,
        pending_request=True  # For unique constraint
    )
    self.session.add(request)
    await self.session.flush()
    return (True, "Solicitud creada", request)
except IntegrityError:
    await self.session.rollback()
    return (False, "Ya tienes una solicitud pendiente", existing)
```

## Changes Made

### Task 1: Database Constraint for Free Requests
- Added `UniqueConstraint` import to models.py
- Added `pending_request` boolean column to FreeChannelRequest model
- Added partial unique constraint `uq_user_pending_request` with `sqlite_where`

### Task 2: Fix redeem_vip_token Race Condition (C-001)
- Added `update` import from sqlalchemy
- Replaced SELECT-then-UPDATE with atomic UPDATE pattern
- Added rowcount check to detect race conditions
- Updated docstring to document atomic behavior

### Task 3: Fix create_free_request Race Condition (C-002)
- Added `IntegrityError` import from sqlalchemy.exc
- Replaced SELECT-then-INSERT with atomic INSERT pattern
- Added proper session rollback after IntegrityError
- Changed return type to `Tuple[bool, str, Optional[FreeChannelRequest]]`

### Task 4: Update Return Type Signatures and Callers
- Updated all places setting `processed=True` to also set `pending_request=False`
- Updated `create_free_request_from_join_request` to set `pending_request=True`
- Updated test files to handle new tuple return signature
- Verified no mypy type errors introduced

## Verification

- [x] C-001 fixed: redeem_vip_token uses atomic UPDATE with rowcount check
- [x] C-002 fixed: create_free_request uses INSERT with IntegrityError handling
- [x] No SELECT FOR UPDATE used (not reliable in SQLite)
- [x] IntegrityError properly caught and session rolled back
- [x] Python syntax validation passed
- [x] All callers updated for new return signatures

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Hash | Message |
|------|---------|
| 2dbba05 | feat(27-01): add unique constraint for pending free requests |
| ebfd230 | fix(27-01): fix race condition C-001 in redeem_vip_token |
| cbfdd4d | fix(27-01): fix race condition C-002 in create_free_request |
| dc4250b | fix(27-01): update callers and tests for new create_free_request signature |

## Self-Check: PASSED

- [x] bot/database/models.py contains pending_request column and unique constraint
- [x] bot/services/subscription.py uses atomic UPDATE in redeem_vip_token
- [x] bot/services/subscription.py uses IntegrityError handling in create_free_request
- [x] All test files updated for new return signatures
- [x] All commits exist in git history
