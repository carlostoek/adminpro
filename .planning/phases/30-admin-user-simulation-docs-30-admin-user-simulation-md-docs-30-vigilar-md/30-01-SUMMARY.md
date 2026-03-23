---
phase: 30-admin-user-simulation
plan: 01
type: summary
subsystem: simulation
status: complete

key-files:
  created:
    - bot/services/simulation.py
  modified:
    - bot/database/enums.py
    - bot/services/container.py

decisions:
  - SimulationMode enum follows existing enum patterns with display_name and emoji properties
  - SimulationStore uses singleton pattern for shared state across service instances
  - TTL of 30 minutes for automatic expiration of simulation sessions
  - ResolvedUserContext provides single source of truth via effective_role() and effective_balance()
  - Non-admins cannot activate simulation (enforced via Config.is_admin check)

metrics:
  duration: "7m"
  tasks: 3
  files-created: 1
  files-modified: 2
  lines-added: ~640
---

# Phase 30 Plan 01: Admin User Simulation Summary

## Overview

Core simulation infrastructure implemented with in-memory storage, context resolution, and data models. This is the foundation layer that all other simulation features depend on.

## Deliverables

### 1. SimulationMode Enum (`bot/database/enums.py`)

Three simulation modes for admin role testing:
- `REAL` - Normal operation, no simulation
- `VIP` - Simulate VIP user experience
- `FREE` - Simulate Free user experience

Features:
- `display_name` property for UI labels
- `emoji` property for visual indicators
- `simulated_role` property mapping to UserRole

### 2. Simulation Service (`bot/services/simulation.py`)

Three core classes:

#### ResolvedUserContext (dataclass)
- Stores user_id, real_role, simulated_role
- Tracks is_simulating state
- Optional balance and subscription status overrides
- TTL tracking with activated_at and expires_at
- Methods:
  - `effective_role()` - Returns simulated or real role
  - `effective_balance(real_balance)` - Returns simulated or real balance
  - `effective_subscription_status()` - Returns simulated or real status
  - `time_remaining()` - Seconds until expiration
  - `to_dict()` - Serialization for API responses

#### SimulationStore (singleton)
- In-memory storage isolated per admin
- TTL-based automatic expiration (30 minutes)
- Methods:
  - `activate_simulation()` - Start simulation for admin
  - `deactivate_simulation()` - Stop simulation
  - `get_context()` - Retrieve admin's context
  - `is_simulating()` - Check simulation state
  - `cleanup_expired()` - Remove expired sessions
  - `get_all_active()` - List all active simulations

#### SimulationService
- Initialized with session and bot (like other services)
- Uses class-level SimulationStore singleton
- Core method: `resolve_user_context(user_id)` - THE single source of truth
- Admin control methods:
  - `start_simulation(admin_id, mode, balance, subscription_status)`
  - `stop_simulation(admin_id)`
  - `get_simulation_status(admin_id)`
- Safety: Only admins can simulate (Config.is_admin check)

### 3. ServiceContainer Integration (`bot/services/container.py`)

- Added `_simulation_service` placeholder
- Added `simulation` property with lazy loading
- Updated `get_loaded_services()` to include "simulation"

## Architecture

```
Admin Request
    ↓
ServiceContainer.simulation (lazy loaded)
    ↓
SimulationService.resolve_user_context(user_id)
    ↓
  ├─ Is admin? → Check SimulationStore for active context
  │              ├─ Simulating? → Return context with simulated_role
  │              └─ Not simulating? → Return context with real_role=ADMIN
  │
  └─ Not admin? → Detect real role from DB → Return context
    ↓
ResolvedUserContext.effective_role() → VIP/FREE/ADMIN
```

## Safety Features

1. **Admin-only**: Config.is_admin check prevents non-admins from simulating
2. **TTL expiration**: 30-minute automatic cleanup prevents stale sessions
3. **Isolated storage**: Dict key is admin_id, no cross-user leakage
4. **Real data preserved**: Simulated values don't touch database

## Verification

All success criteria met:
- ✅ SimulationMode enum exists with REAL/VIP/FREE values
- ✅ SimulationService created with resolve_user_context() as single source of truth
- ✅ SimulationStore provides in-memory isolated storage per admin
- ✅ ResolvedUserContext dataclass has effective_role() and effective_balance() methods
- ✅ ServiceContainer exposes simulation property with lazy loading
- ✅ All imports work without circular dependency errors

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 607506e | Add SimulationMode enum to database/enums.py |
| 2 | 66bdb20 | Create simulation service with core classes |
| 3 | 724309b | Add simulation service to ServiceContainer |

## Deviations from Plan

None - plan executed exactly as written.

## Next Steps

This foundation enables:
- Admin handlers for activating/deactivating simulation mode
- UI indicators showing current simulation state
- Middleware integration for automatic context resolution
- Handler updates to use resolve_user_context() instead of direct role checks

## Self-Check: PASSED

- [x] bot/services/simulation.py exists (545 lines)
- [x] SimulationMode enum in bot/database/enums.py
- [x] ServiceContainer.simulation property works
- [x] All imports verified: `python -c "from bot.services.simulation import ..."`
- [x] All commits exist in git log
