---
phase: 30-admin-user-simulation
plan: 02
type: execute
subsystem: middleware
wave: 2

requires:
  - 30-01

provides:
  - SimulationMiddleware injection
  - RoleDetectionMiddleware integration

affects:
  - bot/middlewares/simulation.py
  - bot/middlewares/__init__.py
  - bot/middlewares/role_detection.py

tech-stack:
  added: []
  patterns:
    - Middleware chain pattern (Database → Simulation → RoleDetection)
    - Data injection via handler data dict

key-files:
  created:
    - bot/middlewares/simulation.py
  modified:
    - bot/middlewares/__init__.py
    - bot/middlewares/role_detection.py

decisions:
  - Middleware order: DatabaseMiddleware → SimulationMiddleware → RoleDetectionMiddleware
  - SimulationMiddleware gracefully handles missing container (logs warning, continues)
  - RoleDetectionMiddleware checks user_context before computing role
  - Error handling in SimulationMiddleware prevents breaking handlers on resolution errors

metrics:
  duration: 3m
  completed-date: 2026-03-23T16:52:01Z
  tasks-total: 3
  tasks-completed: 3
---

# Phase 30 Plan 02: Simulation Middleware Integration - Summary

**One-liner:** Middleware chain that injects simulation context into handler data, enabling role simulation for admins.

## What Was Built

### SimulationMiddleware (bot/middlewares/simulation.py)
New middleware that:
- Extracts user from Message/CallbackQuery events
- Gets ServiceContainer from data dict (requires DatabaseMiddleware to run first)
- Calls `container.simulation.resolve_user_context(user.id)` to get resolved context
- Injects `user_context` into handler data dict
- Logs debug message with simulation status
- Handles errors gracefully (continues without injection if resolution fails)

### Module Export (bot/middlewares/__init__.py)
- Added SimulationMiddleware import
- Added SimulationMiddleware to __all__ list

### RoleDetectionMiddleware Integration (bot/middlewares/role_detection.py)
Modified to respect simulation context:
- Checks for `user_context` in data dict before computing role
- If simulation context exists and is active, uses `effective_role()` from context
- Falls through to normal role detection for non-simulated users
- Preserves all existing functionality for regular users

## Middleware Order (Critical)

```
DatabaseMiddleware (first)
  ↓ injects session + container
SimulationMiddleware (second)
  ↓ injects user_context
RoleDetectionMiddleware (third)
  ↓ uses user_context if available, else computes role
Handler
```

## Key Links Established

| From | To | Via | Pattern |
|------|-----|-----|---------|
| SimulationMiddleware | SimulationService | `container.simulation.resolve_user_context()` | `data["container"].simulation.resolve_user_context` |
| SimulationMiddleware | handler data | `data["user_context"]` injection | `data["user_context"]` |
| RoleDetectionMiddleware | SimulationMiddleware | checks `data["user_context"]` before computing role | `if "user_context" in data` |

## Verification Results

- [x] `python -c "from bot.middlewares import SimulationMiddleware; print('Import OK')"` - PASSED
- [x] SimulationMiddleware in __all__ - VERIFIED
- [x] RoleDetectionMiddleware has user_context check - VERIFIED
- [x] Middleware order documented - DOCUMENTED

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Hash | Message |
|------|---------|
| 2dba4fe | feat(30-02): create SimulationMiddleware for context injection |
| 761b573 | feat(30-02): export SimulationMiddleware from middlewares module |
| e84d4a4 | feat(30-02): modify RoleDetectionMiddleware to respect simulation context |

## Self-Check: PASSED

- [x] bot/middlewares/simulation.py exists
- [x] bot/middlewares/__init__.py exports SimulationMiddleware
- [x] bot/middlewares/role_detection.py has user_context check
- [x] All imports work without errors
- [x] All commits recorded
