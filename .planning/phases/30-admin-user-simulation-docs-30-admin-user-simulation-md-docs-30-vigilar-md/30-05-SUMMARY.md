---
phase: 30
plan: 05
subsystem: simulation
tags: [simulation, middleware, integration, gap-closure]
dependency_graph:
  requires: [30-01, 30-02, 30-04]
  provides: [simulation-middleware-registration, user-context-role-detection]
  affects: [main.py, bot/handlers/user/start.py]
tech_stack:
  added: []
  patterns:
    - Middleware chain ordering for simulation context injection
    - user_context check before Config.is_admin() in handlers
key_files:
  created: []
  modified:
    - path: main.py
      change: "Add SimulationMiddleware to imports and middleware chain"
      lines: "336-346"
    - path: bot/handlers/user/start.py
      change: "Add **data parameter and user_context check before Config.is_admin()"
      lines: "30-76"
decisions:
  - "SimulationMiddleware must be registered between DatabaseMiddleware (provides container) and UserRegistrationMiddleware (needs session)"
  - "Handler uses **data to receive middleware-injected user_context from SimulationMiddleware"
  - "When user_context.is_simulating is True, admin is treated as non-admin to show user menus"
---

# Phase 30 Plan 05: Simulation System Integration Gap Closure

**One-liner:** Fixed simulation middleware registration and handler role detection to enable admin user simulation.

## Summary

Closed critical integration gaps identified during UAT testing that prevented the admin user simulation system from working correctly.

**Gaps Closed:**
1. **SimulationMiddleware not registered in main.py** - The middleware existed but was never added to the middleware chain, so user_context was never injected.
2. **Handler used Config.is_admin() directly** - The /start handler bypassed the simulation context, always showing admin menu to admins even when simulating.

## Changes Made

### Task 1: Register SimulationMiddleware in main.py

**File:** `main.py` (lines 336-346)

Updated middleware registration to include SimulationMiddleware in the correct order:

```python
# Registrar middlewares ANTES de los handlers (orden crítico)
# 1. DatabaseMiddleware: inyecta session y container
# 2. SimulationMiddleware: inyecta user_context para simulación de roles
# 3. UserRegistrationMiddleware: registra usuario si no existe (requiere session)
# 4. RoleDetectionMiddleware: detecta rol del usuario (requiere user_context si existe)
from bot.middlewares import DatabaseMiddleware, SimulationMiddleware, RoleDetectionMiddleware, UserRegistrationMiddleware
dp.update.middleware(DatabaseMiddleware())
dp.update.middleware(SimulationMiddleware())
dp.update.middleware(UserRegistrationMiddleware())
dp.update.middleware(RoleDetectionMiddleware())
```

**Key Points:**
- SimulationMiddleware must run AFTER DatabaseMiddleware (needs container)
- SimulationMiddleware must run BEFORE RoleDetectionMiddleware (provides user_context)
- Updated comments document the execution order and dependencies

### Task 2: Update /start Handler to Use user_context

**File:** `bot/handlers/user/start.py` (lines 30-76)

Updated `cmd_start` handler to check simulation context before determining admin status:

```python
@user_router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession, **data):
    # ... docstring updated ...

    # Verificar si es admin PRIMERO (respetando simulación si está activa)
    user_context = data.get("user_context")
    if user_context and user_context.is_simulating:
        # During simulation, admin is simulating a user role, not acting as admin
        is_admin = False
        logger.debug(f"🎭 User {user_id} is simulating role: {user_context.effective_role().value}")
    else:
        is_admin = Config.is_admin(user_id)
```

**Key Points:**
- Added `**data` parameter to receive middleware-injected values
- Checks `user_context.is_simulating` before falling back to `Config.is_admin()`
- When simulating, admin is treated as non-admin to show user menus
- Logging includes simulation role for debugging

## Verification

All verification commands pass:

```bash
python -c "from main import *; print('main.py OK')"
python -c "from bot.handlers.user.start import cmd_start; print('start.py OK')"
python -c "from bot.middlewares import SimulationMiddleware; print('SimulationMiddleware OK')"
```

## Functional Behavior

After these changes:

1. **Admin activates VIP simulation** via /simulate command
2. **Admin sends /start**
3. **Admin sees VIP user menu** (not admin menu)
4. **Admin switches to FREE simulation**
5. **Admin sends /start**
6. **Admin sees FREE user menu** (not admin menu)
7. **Admin exits simulation**
8. **Admin sends /start**
9. **Admin sees normal admin menu**

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Commit | Description |
|--------|-------------|
| a096ea4 | feat(30-05): register SimulationMiddleware in main.py middleware chain |
| 0d259a8 | feat(30-05): update /start handler to respect simulation context |

## Requirements Satisfied

- SIM-01: Admin can simulate VIP user experience
- SIM-02: Admin can simulate FREE user experience

## Self-Check: PASSED

- [x] main.py modified - SimulationMiddleware registered
- [x] bot/handlers/user/start.py modified - user_context check added
- [x] All imports verify successfully
- [x] Both tasks committed with proper messages
- [x] SUMMARY.md created
