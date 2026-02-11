---
phase: 20-reaction-system
plan: "05"
subsystem: gamification
tags: [reaction, database, constraint, deduplication]

dependency_graph:
  requires: ["20-04"]
  provides: ["reaction-single-constraint"]
  affects: []

tech-stack:
  added: []
  patterns: ["unique-constraint-enforcement"]

key-files:
  created:
    - alembic/versions/20260211_000001_fix_reaction_unique_constraint.py
  modified:
    - bot/database/models.py
    - bot/services/reaction.py
    - bot/handlers/user/reactions.py
    - tests/services/test_reaction_service.py
    - tests/services/test_reaction_integration.py

decisions:
  - id: D1
    text: "Changed unique constraint from (user_id, content_id, emoji) to (user_id, content_id) to enforce one reaction per content"
    rationale: "User reported that users could react multiple times with different emojis to the same message"
    alternatives: ["Keep old behavior", "Add config option"]

metrics:
  duration: 15m
  completed: 2026-02-11
---

# Phase 20 Plan 05: Fix Duplicate Reaction Constraint Summary

## One-Liner
Fixed duplicate reaction logic to enforce "one reaction per message" instead of "one reaction per emoji per message".

## What Was Changed

### Problem
Users could react multiple times to the same message with different emojis. The system was allowing one reaction per emoji per message, but should only allow ONE reaction per message total.

### Root Cause
- Unique constraint `idx_user_content_emoji` included the emoji column
- `_is_duplicate_reaction()` checked `user_id + content_id + emoji`
- Error message said "Ya reaccionaste con este emoji"

### Solution
1. **Updated UserReaction model** - Changed unique constraint from `(user_id, content_id, emoji)` to `(user_id, content_id)` only
2. **Created Alembic migration** - Deduplicates existing data (keeps first reaction per user/content), drops old index, creates new index
3. **Updated ReactionService** - Removed emoji parameter from `_is_duplicate_reaction()` and its WHERE clause
4. **Updated error message** - Changed to "Ya reaccionaste a este contenido"
5. **Updated tests** - Changed test expectations to match new behavior

## Files Modified

| File | Changes |
|------|---------|
| `bot/database/models.py` | Changed `idx_user_content_emoji` to `idx_user_content` (removed emoji from unique constraint) |
| `alembic/versions/20260211_000001_fix_reaction_unique_constraint.py` | New migration: deduplicates data, drops old index, creates new index |
| `bot/services/reaction.py` | Removed emoji from `_is_duplicate_reaction()` signature and query |
| `bot/handlers/user/reactions.py` | Updated error message to "Ya reaccionaste a este contenido" |
| `tests/services/test_reaction_service.py` | Updated tests for new behavior |
| `tests/services/test_reaction_integration.py` | Updated test to expect duplicate error for different emoji |

## Test Results

All 58 reaction tests pass:
- 18 reaction service tests
- 20 reaction handler tests
- 12 reaction integration tests
- 8 reaction requirements tests

## Database State

```sql
-- New unique index (user_id, content_id only)
CREATE UNIQUE INDEX idx_user_content ON user_reactions (user_id, content_id)

-- Old index removed
-- idx_user_content_emoji no longer exists
```

## Behavior Change

| Scenario | Before | After |
|----------|--------|-------|
| User reacts with ❤️ then ❤️ | Blocked (duplicate) | Blocked (duplicate) |
| User reacts with ❤️ then 🔥 | Allowed | Blocked (duplicate) |
| Error message | "Ya reaccionaste con este emoji" | "Ya reaccionaste a este contenido" |

## Deviations from Plan

None - plan executed exactly as written.

## Next Steps

- Phase 20 Reaction System is now complete with the gap fixed
- Ready to proceed to Phase 21: Daily Rewards & Streaks
