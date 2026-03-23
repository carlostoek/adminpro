---
phase: 30
plan: 03
subsystem: admin
phase_name: Admin User Simulation
tags: [simulation, admin, ui, handlers]
requires: ["30-01"]
provides: ["admin-simulation-ui"]
affects: ["bot/handlers/admin/simulation.py", "bot/utils/keyboards.py", "bot/handlers/admin/__init__.py"]
tech-stack:
  added: []
  patterns: ["Lucien voice", "Router registration", "Inline keyboard"]
key-files:
  created:
    - bot/handlers/admin/simulation.py
  modified:
    - bot/utils/keyboards.py
    - bot/handlers/admin/__init__.py
decisions:
  - "Used checkmark (✅) and circle (⚪) emojis for mode selection visual indicator"
  - "Banner function returns empty string when not simulating for easy concatenation"
  - "Double admin check (middleware + explicit Config.is_admin) for defense in depth"
  - "Immediate callback.answer() to avoid 'loading...' state in Telegram"
metrics:
  duration: "8 minutes"
  completed-date: "2026-03-23"
  tasks-completed: 3
  files-created: 1
  files-modified: 2
  lines-added: ~400
---

# Phase 30 Plan 03: Admin Simulation UI Controls Summary

**One-liner:** Admin /simulate command with mode selector keyboard and visual banner for simulation state.

## What Was Built

Admin UI controls for the simulation system, allowing administrators to:
- Activate simulation mode via `/simulate` command
- Switch between REAL, VIP, and FREE modes via inline keyboard
- See visual banner with time remaining when simulating
- Refresh status display to check remaining time

### Components Created

1. **bot/handlers/admin/simulation.py** (340 lines)
   - `/simulate` command handler with Lucien's voice (🎩)
   - `get_simulation_banner()` - Visual indicator when simulating
   - `simulation_command` - Main panel with current status
   - `simulation_refresh_callback` - Refresh status display
   - `simulation_set_vip_callback` - Activate VIP simulation
   - `simulation_set_free_callback` - Activate FREE simulation
   - `simulation_set_real_callback` - Deactivate simulation
   - Admin-only access with Config.is_admin checks

2. **bot/utils/keyboards.py** - `get_simulation_mode_keyboard()`
   - Three mode buttons in one row: VIP | FREE | REAL
   - Current mode marked with ✅, others with ⚪
   - Refresh button (🔄) for status updates
   - Returns InlineKeyboardMarkup

3. **bot/handlers/admin/__init__.py**
   - Registered simulation_router in admin handlers

## Verification Results

```bash
✅ python -c "from bot.handlers.admin.simulation import router; print('Router import OK')"
✅ python -c "from bot.utils.keyboards import get_simulation_mode_keyboard; print('Keyboard import OK')"
✅ grep "simulation_router" bot/handlers/admin/__init__.py  # Found import and include
```

## Deviations from Plan

None - plan executed exactly as written.

## Architecture Decisions

1. **Visual Mode Indicator**: Used ✅ for current mode and ⚪ for others instead of just text. More intuitive at a glance.

2. **Banner Function Design**: `get_simulation_banner()` returns empty string when not simulating, allowing simple string concatenation without conditional checks in message building.

3. **Double Admin Verification**: While AdminAuthMiddleware handles the primary check, handlers also verify `Config.is_admin()` for defense in depth and clearer error messages.

4. **Immediate Callback Response**: All callback handlers call `callback.answer()` immediately to prevent Telegram from showing "loading..." state while processing.

## Integration Points

- **SimulationService** (from 30-01): Uses `start_simulation()`, `stop_simulation()`, `get_simulation_status()`, `resolve_user_context()`
- **ServiceContainer**: Standard DI pattern for accessing simulation service
- **SimulationMode enum**: VIP/FREE/REAL modes with display names and emojis
- **AdminAuthMiddleware**: Applied to all simulation handlers

## Commits

| Hash | Message |
|------|---------|
| 388e299 | feat(30-03): create simulation control handlers |
| 51f0ddd | feat(30-03): add simulation mode selector keyboard |
| 0206f2c | feat(30-03): register simulation router in admin handlers |

## Self-Check: PASSED

- [x] /simulate command handler exists and responds to admin users
- [x] Mode selector keyboard with VIP/FREE/REAL options
- [x] Current mode visually indicated with checkmark
- [x] Simulation status shows time remaining when active
- [x] Visual banner function for simulating state
- [x] Only admins can access simulation controls
- [x] Router registered in admin handlers module
- [x] All messages use Lucien's voice (🎩)
