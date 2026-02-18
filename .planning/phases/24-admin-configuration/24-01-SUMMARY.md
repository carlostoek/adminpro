---
phase: 24
plan: 01
subsystem: admin-configuration
tags: ["admin", "economy", "configuration", "handlers", "fsm"]

dependencies:
  requires:
    - phase-23-rewards-system
    - bot/services/config.py
  provides:
    - Economy configuration handlers
    - Admin UI for besitos settings
  affects:
    - phase-24-admin-configuration

tech-stack:
  added: []
  patterns:
    - FSM (Finite State Machine) for multi-step input
    - Router pattern for handler organization
    - Lucien's voice (🎩) for admin messages

key-files:
  created:
    - bot/handlers/admin/economy_config.py
  modified:
    - bot/states/admin.py
    - bot/handlers/admin/__init__.py
    - bot/utils/keyboards.py

decisions:
  - id: D1
    text: "Used FSM states for each configuration value to handle multi-step input flow"
    rationale: "Consistent with existing admin handlers (ChannelSetupStates, PricingSetupStates)"
    impact: "Clean separation of concerns, easy to extend"

metrics:
  duration: 117s
  completed: 2026-02-17
---

# Phase 24 Plan 01: Economy Configuration Handlers Summary

## One-Liner
Implemented admin handlers for configuring economy values (besitos per reaction, daily gift, streak bonus, max reactions) with FSM-based input flow and Lucien's voice.

## What Was Built

### Economy Config Handler Module
Created `bot/handlers/admin/economy_config.py` with:

**Main Handler:**
- `callback_economy_config` - Displays current economy configuration with inline keyboard
- Shows 4 values: besitos per reaction, daily gift, streak bonus, max reactions
- 2x2 grid of edit buttons + back button

**Edit Handlers (FSM-based):**
- `callback_edit_reaction` / `process_reaction_value` - Configure besitos per reaction
- `callback_edit_daily` / `process_daily_value` - Configure daily gift besitos
- `callback_edit_streak` / `process_streak_value` - Configure streak bonus
- `callback_edit_limit` / `process_limit_value` - Configure max reactions per day

**Features:**
- Input validation (positive integers only)
- Lucien's voice (🎩) for all messages
- Error handling with user-friendly messages
- Automatic menu refresh after updates

### FSM States
Added `EconomyConfigState` to `bot/states/admin.py`:
- `waiting_for_reaction_value`
- `waiting_for_daily_value`
- `waiting_for_streak_value`
- `waiting_for_limit_value`

### Menu Integration
- Registered `economy_config_router` in `bot/handlers/admin/__init__.py`
- Added "💰 Economía" button to config menu in `bot/utils/keyboards.py`

## Deviations from Plan

None - plan executed exactly as written.

## Key Implementation Details

### Voice Consistency
All messages use Lucien's formal mayordomo voice:
- "🎩 **Configuración de Economía**"
- "🎩 **Valor inválido** - Debe ser un número entero positivo."
- "🎩 **Configuración actualizada** - El valor ha sido modificado."

### Validation Pattern
```python
try:
    value = int(message.text.strip())
    if value <= 0:
        raise ValueError("Value must be positive")
except (ValueError, AttributeError):
    # Show error but keep state for retry
    return
```

### ConfigService Integration
Uses existing ConfigService methods:
- `get_besitos_per_reaction()` / `set_besitos_per_reaction()`
- `get_besitos_daily_gift()` / `set_besitos_daily_gift()`
- `get_besitos_daily_streak_bonus()` / `set_besitos_daily_streak_bonus()`
- `get_max_reactions_per_day()` / `set_max_reactions_per_day()`

## Files Changed

| File | Lines | Change |
|------|-------|--------|
| `bot/handlers/admin/economy_config.py` | +448 | New handler module |
| `bot/states/admin.py` | +8 | EconomyConfigState added |
| `bot/handlers/admin/__init__.py` | +2 | Router registration |
| `bot/utils/keyboards.py` | +1 | Menu button added |

## Commits

1. `0dbdd8a` - feat(24-01): create economy config handler module
2. `e48fe48` - feat(24-01): add economy config FSM states
3. `f15679b` - feat(24-01): register economy config router and add menu button

## Verification

- [x] Economy config handlers respond to `admin:economy_config` callback
- [x] All 4 configuration values can be viewed and modified
- [x] FSM states properly manage the input flow
- [x] Validation rejects non-positive integers
- [x] Changes persist to database via ConfigService
- [x] Menu integration works correctly
- [x] Lucien's voice (🎩) used for all messages

## Next Phase Readiness

This plan completes the foundation for admin economy configuration. The handlers are ready for:
- Phase 24 Plan 02: Reward configuration handlers
- Phase 24 Plan 03: Admin broadcast with economy stats
- Phase 24 Plan 04: Full admin dashboard integration

All economy values are now configurable via Telegram bot interface without requiring database access.
