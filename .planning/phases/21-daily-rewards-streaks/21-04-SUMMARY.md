---
phase: 21
plan: "21-04"
subsystem: "handlers"
tags: ["streak", "daily-gift", "handler", "lucien-voice", "gamification"]

dependency_graph:
  requires: ["21-02"]
  provides: ["daily-gift-handler", "streak-commands"]
  affects: ["21-05", "22-01"]

tech-stack:
  added: []
  patterns: ["FSM-states", "handler-router", "lucien-voice-messages"]

key-files:
  created:
    - bot/handlers/user/streak.py
    - tests/handlers/test_streak_handlers.py
  modified:
    - bot/states/user.py
    - bot/handlers/user/__init__.py

decisions:
  - "Use FSM states for daily gift flow (daily_gift_confirm, daily_gift_claimed)"
  - "Lucien's voice (🎩) for all messages - formal, elegant, references Diana"
  - "Detailed breakdown format: base + bonus = total with visual separator"
  - "UTC-based countdown calculation for next claim time"
  - "Inline keyboard with single claim button when available"

metrics:
  duration: "~15 min"
  completed: "2026-02-12"
  tests: 17
  coverage: "Handler logic and Lucien voice verification"
---

# Phase 21 Plan 04: Daily Gift Handler Summary

## One-Liner
Daily gift handler with Lucien's voice, detailed breakdown display, and FSM state management for claim flow.

## What Was Built

### Handler Module (`bot/handlers/user/streak.py`)
- **`/daily_gift` command handler**: Checks claim availability via `streak_service.can_claim_daily_gift()`
- **Claim callback handler**: Processes claim via `streak_service.claim_daily_gift()` with detailed breakdown
- **`get_countdown_text()` helper**: Calculates hours/minutes until next UTC midnight claim
- **Lucien voice messages**: All messages use 🎩 emoji, formal tone, references to Diana

### FSM States (`bot/states/user.py`)
- **`daily_gift_confirm`**: Waiting for user to confirm claim
- **`daily_gift_claimed`**: Just claimed, showing countdown to next claim

### Message Format (Success)
```
🎩 <b>Lucien:</b>
<i>Ah... Diana ha notado su constancia.</i>

🔥 <b>Racha actual:</b> {streak} días
💰 <b>Base:</b> {base} besitos
✨ <b>Bonus por racha:</b> +{bonus} besitos
─────────────────
💎 <b>Total recibido:</b> {total} besitos

<i>Excelente elección volver hoy...</i>
```

## Verification Results

### Requirements Verified
| Requirement | Status | Evidence |
|-------------|--------|----------|
| STREAK-01: Claim once per 24h | ✅ | Handler uses `can_claim_daily_gift()` service method |
| STREAK-02: Base + streak bonus | ✅ | Success message shows base (20) + bonus (streak*2, max 50) = total |
| Detailed breakdown display | ✅ | Visual format with emojis and separator line |
| Lucien's voice consistency | ✅ | All 17 tests verify 🎩, Diana references, formal tone |

### Test Results
```
tests/handlers/test_streak_handlers.py: 17 passed
- TestGetCountdownText: 4 tests
- TestLucienVoiceMessages: 8 tests
- TestClaimKeyboard: 2 tests
- TestSTREAKRequirements: 3 tests
```

### Total Streak Tests
```
tests/services/test_streak_service.py: 35 passed
tests/handlers/test_streak_handlers.py: 17 passed
Total: 52 streak-related tests passing
```

## Deviations from Plan

None - plan executed exactly as written.

## Key Implementation Details

### Lucien's Voice Patterns
- **Header**: `🎩 <b>Lucien:</b>` with HTML bold
- **Thoughts**: Wrapped in `<i>...</i>` (italic)
- **Diana references**: "Diana ha notado...", "Diana aprecia..."
- **Elegant terms**: "constancia", "inconveniente", "Excelente elección"

### Countdown Format
- Hours + minutes: "Próximo regalo en 14h 32m"
- Minutes only: "Próximo regalo en 45m"
- Available now: "El regalo está disponible ahora"

### Error Handling
- Service errors caught and logged
- User sees elegant Lucien error message
- Callback answers provide feedback without alerts for success

## Integration Points

### ServiceContainer
```python
# Handler receives container via dependency injection
can_claim, status = await container.streak.can_claim_daily_gift(user_id)
success, result = await container.streak.claim_daily_gift(user_id)
```

### Router Registration
```python
# In bot/handlers/user/__init__.py
from bot.handlers.user.streak import streak_router
user_router.include_router(streak_router)
```

## Next Phase Readiness

This plan completes the user-facing daily gift flow. Ready for:
- **Plan 21-05**: Background jobs for streak expiration
- **Phase 22**: Shop system (users will have besitos to spend)

## Files Created/Modified

| File | Lines | Purpose |
|------|-------|---------|
| `bot/handlers/user/streak.py` | 399 | Main handler module |
| `tests/handlers/test_streak_handlers.py` | 194 | Handler tests |
| `bot/states/user.py` | +23 | StreakStates FSM |
| `bot/handlers/user/__init__.py` | +5 | Router registration |

## Commits

1. `561545f` - feat(21-04): add StreakStates for daily gift flow
2. `89401ba` - feat(21-04): create daily gift handler with Lucien's voice
3. `815a898` - feat(21-04): register streak handlers in user module
4. `7d5d33a` - test(21-04): add tests for daily gift handler
