---
status: resolved
trigger: "Fix expires_at field reference and datetime consistency issues"
created: 2026-03-17T00:00:00Z
updated: 2026-03-17T00:00:00Z
---

## Current Focus

hypothesis: Three critical bugs exist - (1) InvitationToken.expires_at doesn't exist, (2) datetime.utcnow() vs utc_now() mismatch, (3) import ordering issue in subscription.py
test: Read all relevant files to confirm bugs
expecting: Find exact lines to fix
next_action: Implement fixes

## Symptoms

expected: Code should work without runtime errors
actual: Multiple critical bugs will cause AttributeError and TypeError
errors:
  1. AttributeError: 'InvitationToken' has no attribute 'expires_at' (subscription.py:277)
  2. TypeError: can't compare offset-naive and offset-aware datetimes (multiple locations)
  3. Inconsistent datetime handling between subscription.py and vip_entry.py
reproduction:
  1. Call redeem_vip_token() - will crash with AttributeError
  2. Call process_free_queue() or cleanup_old_free_requests() - will crash with TypeError
  3. Any comparison between expiry_date and datetime.utcnow() in vip_entry.py
started: Code review of branch ftr/auditoria

## Eliminated

## Evidence

- timestamp: 2026-03-17T00:00:00Z
  checked: bot/database/models.py - InvitationToken class
  found: InvitationToken has `created_at` (DateTime) and `duration_hours` (Integer), NO `expires_at` field
  implication: Line 277 in subscription.py references non-existent field

- timestamp: 2026-03-17T00:00:00Z
  checked: bot/services/subscription.py line 277
  found: `InvitationToken.expires_at > utc_now()` - expires_at doesn't exist
  implication: Will cause AttributeError when redeem_vip_token() is called

- timestamp: 2026-03-17T00:00:00Z
  checked: bot/services/vip_entry.py
  found: Uses `datetime.utcnow()` (naive) while subscription.py uses `utc_now()` (timezone-aware)
  implication: TypeError when comparing expiry_date (naive) with utc_now() (aware)
  lines: 121, 234, 282, 333

- timestamp: 2026-03-17T00:00:00Z
  checked: bot/services/subscription.py imports
  found: `utc_now()` function defined BETWEEN import statements (lines 23-26)
  implication: Import ordering violation - function should be after imports

- timestamp: 2026-03-17T00:00:00Z
  checked: FreeChannelRequest model
  found: Uses `datetime.now(timezone.utc).replace(tzinfo=None)` (naive) for request_date
  implication: process_free_queue compares utc_now() (aware) with request_date (naive)

## Resolution

root_cause:
  1. Line 277: InvitationToken.expires_at doesn't exist - should use created_at + duration_hours calculation
  2. vip_entry.py uses datetime.utcnow() (naive) but models use naive datetimes - need consistency
  3. utc_now() function misplaced between imports in subscription.py

fix:
  1. Fixed expires_at reference in subscription.py line 277 - replaced with SQLite expression `datetime(created_at, '+' || duration_hours || ' hours') > datetime('now')`
  2. Fixed datetime consistency - updated utc_now() to return naive datetimes (matching database format) and updated vip_entry.py to use utc_now()
  3. Fixed import ordering - moved utc_now() function definition after all imports

verification:
  - Syntax check passed for both files
  - No remaining datetime.utcnow() calls in subscription.py or vip_entry.py
  - All datetime comparisons now use consistent naive datetime format

files_changed:
  - bot/services/subscription.py
  - bot/services/vip_entry.py
