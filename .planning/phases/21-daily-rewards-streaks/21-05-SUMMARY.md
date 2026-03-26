---
phase: 21
plan: 21-05
subsystem: gamification
tags: [streak, daily-gift, ui, user-menu]

requires:
  - 21-02 (StreakService Core Logic)
  - 21-04 (Daily Gift Handler)

provides:
  - Streak display in VIP user menu
  - Streak display in Free user menu
  - Daily gift button integration
  - Countdown display for next claim

affects:
  - 21-06 (Streak Background Jobs)
  - 22-01 (Shop System)

tech-stack:
  added: []
  patterns:
    - Parameter-based menu customization
    - Streak info dict passing
    - Conditional button rendering

decisions:
  - Use Diana's voice (🫦) for streak display in user menus
  - Fire emoji (🔥) with day count format: "🔥 {count} días"
  - "Sin racha" for zero streak to encourage starting
  - Daily gift button at top of menu when available
  - Countdown timer shows hours and minutes until next claim

metrics:
  duration: 15min
  completed: 2026-02-12
---

# Phase 21 Plan 05: Streak Display in User Menu - Summary

## One-Liner
Added streak display with fire emoji and daily gift button to VIP and Free user menus.

## What Was Built

### UserMenuMessages Updates (`bot/services/message/user_menu.py`)

1. **New Helper Methods:**
   - `_format_streak_display(streak_count)` - Returns "🔥 {count} días" or "🔥 Sin racha"
   - `_format_time_until_next_claim(next_claim_time)` - Returns formatted countdown (e.g., "5h 30m")

2. **Updated Menu Methods:**
   - `vip_menu_greeting()` - Added `streak_info` parameter with streak display
   - `free_menu_greeting()` - Added `streak_info` parameter with streak display

3. **Updated Keyboard Methods:**
   - `_vip_main_menu_keyboard()` - Shows "🎁 Reclamar regalo diario" button when claim available, or countdown when claimed
   - `_free_main_menu_keyboard()` - Same streak button logic for Free users

### Menu Handler Updates

1. **`bot/handlers/vip/menu.py`:**
   - Import `StreakType` enum
   - Query streak info via `container.streak.get_streak_info()`
   - Pass streak_info to `vip_menu_greeting()`

2. **`bot/handlers/free/menu.py`:**
   - Import `StreakType` enum
   - Query streak info via `container.streak.get_streak_info()`
   - Pass streak_info to `free_menu_greeting()`

## Verification Results

### Manual Testing
```python
# Test streak display formatting
assert provider._format_streak_display(0) == '🔥 Sin racha'
assert provider._format_streak_display(5) == '🔥 5 días'

# Test menu with claim available
streak_info = {'current_streak': 5, 'can_claim': True}
text, keyboard = provider.vip_menu_greeting('Test', streak_info=streak_info)
assert '🔥 5 días' in text
assert '🎁 Reclamar regalo diario' in str(keyboard)

# Test menu with countdown
streak_info = {'current_streak': 5, 'can_claim': False, 'next_claim_time': future}
text, keyboard = provider.vip_menu_greeting('Test', streak_info=streak_info)
assert '⏳ Próximo regalo en' in str(keyboard)
```

### Test Results
- All 35 StreakService tests pass
- User menu provider tests pass
- Integration tests pass

## Files Modified

| File | Changes |
|------|---------|
| `bot/services/message/user_menu.py` | Added streak helpers, updated menu methods |
| `bot/handlers/vip/menu.py` | Added streak info query and passing |
| `bot/handlers/free/menu.py` | Added streak info query and passing |

## Key Design Decisions

### Voice Consistency
- **Streak display uses Diana's voice (🫦)** - User menus already use Diana's personal voice
- Fire emoji adds visual flair consistent with gamification theme
- "Sin racha" (no streak) is encouraging rather than negative

### Button Placement
- Daily gift button appears at **top** of menu when available (high priority)
- Countdown appears at top when already claimed
- Regular menu buttons follow below

### Time Formatting
- Hours and minutes only (no seconds) for cleaner display
- "5h 30m" format is compact and clear
- "pronto" fallback when next claim time unknown

## STREAK-05 Requirement Verification

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Streak displayed in user menu | ✅ | Both VIP and Free menus show streak |
| Fire emoji with day count | ✅ | "🔥 {count} días" format |
| Button placement in main menu | ✅ | Top of menu for visibility |

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

This plan completes the user-facing streak display. Ready for:
- 21-06: Streak Background Jobs (expiration handling)
- 22-01: Shop System (users can spend earned besitos)

## Commit

```
a4008ef feat(21-05): add streak display to user menus
```
