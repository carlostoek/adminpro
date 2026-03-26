---
phase: 30-admin-user-simulation
plan: 04
subsystem: simulation
status: completed
tags: [simulation, safety, wallet, shop, reward, admin]
dependency_graph:
  requires: ["30-02", "30-03"]
  provides: ["simulation-safety-guards"]
  affects: ["bot/services/wallet.py", "bot/services/shop.py", "bot/services/reward.py", "bot/handlers/admin/simulation.py"]
tech_stack:
  added: []
  patterns: ["SimulationStore checks", "Service-level guards", "Lucien voice errors"]
key_files:
  created: []
  modified:
    - bot/services/wallet.py
    - bot/services/shop.py
    - bot/services/reward.py
    - bot/handlers/admin/simulation.py
decisions:
  - Added simulation checks at service level (not just UI) for defense in depth
  - Used Lucien's voice (🎩) for all error messages to maintain consistency
  - Blocked admin_credit/admin_debit even for admins during simulation
  - Added SIMULATION_BLOCKED code for shop purchases to allow specific handling
metrics:
  duration: "25 minutes"
  completed_date: "2026-03-23"
  tasks_completed: 4
  files_modified: 4
  commits: 4
---

# Phase 30 Plan 04: Simulation Safety Restrictions Summary

**One-liner:** Implemented safety guards in wallet, shop, and reward services to block permanent state changes during admin simulation mode.

## Overview

This plan implements critical safety restrictions to prevent admins from accidentally modifying real data while testing the bot in simulation mode. All state-changing operations are now blocked at the service level with clear error messages.

## Tasks Completed

### Task 1: WalletService Simulation Safety
**Commit:** `9ddf5fa`

Added simulation safety checks to `bot/services/wallet.py`:
- Imported `SimulationStore` from `bot.services.simulation`
- Added `_check_simulation_block(user_id, action)` helper method
- Blocked `earn_besitos()` during simulation with message: "🎩 Acción bloqueada: No se pueden ganar besitos durante la simulación."
- Blocked `spend_besitos()` during simulation with message: "🎩 Acción bloqueada: No se pueden gastar besitos durante la simulación."
- Blocked `admin_credit()` during simulation (even for admins)
- Blocked `admin_debit()` during simulation (even for admins)
- All blocked actions are logged with WARNING level for visibility

### Task 2: ShopService Simulation Safety
**Commit:** `698ac92`

Added simulation safety check to `bot/services/shop.py`:
- Imported `SimulationStore` from `bot.services.simulation`
- Added simulation check at start of `purchase_product()`
- Returns `(False, "SIMULATION_BLOCKED", error_message)` when simulating
- Error message: "🎩 No se pueden realizar compras durante la simulación."
- Browse catalog and view product details remain unblocked (read-only)

### Task 3: RewardService Simulation Safety
**Commit:** `3ceb160`

Added simulation safety check to `bot/services/reward.py`:
- Imported `SimulationStore` from `bot.services.simulation`
- Added simulation check at start of `claim_reward()`
- Returns `(False, "🎩 No se pueden reclamar recompensas durante la simulación.", None)` when simulating
- `get_available_rewards()` remains unblocked (read-only)

### Task 4: Simulation Banner Utilities
**Commit:** `c631908`

Added banner utilities to `bot/handlers/admin/simulation.py`:
- `get_simulation_banner(context)` - Existing function (context-based)
- `get_simulation_banner_for_user(user_id, container)` - New async function for other handlers
- `format_with_banner(text, user_id, container)` - Helper to prepend banner to any message
- Banner format includes: "⚠️ MODO SIMULACIÓN ACTIVO", simulated role, and time remaining
- Both new functions exported for use in other admin handlers
- Usage examples included in docstrings

## Safety Requirements Verification

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Wallet operations blocked during simulation | ✅ | `earn_besitos`, `spend_besitos`, `admin_credit`, `admin_debit` all blocked |
| Shop purchases blocked during simulation | ✅ | `purchase_product` returns `SIMULATION_BLOCKED` code |
| Reward claims blocked during simulation | ✅ | `claim_reward` returns error with Lucien's voice |
| Clear error messages | ✅ | All messages use Lucien's voice (🎩) and explain WHY action was blocked |
| Simulation banner in admin responses | ✅ | `get_simulation_banner_for_user` and `format_with_banner` available |

## Deviations from Plan

None - plan executed exactly as written.

## Key Design Decisions

1. **Service-Level Enforcement**: Safety checks are implemented at the service layer, not just UI layer. This provides defense in depth - even if a handler bypasses the check, the service will still block the operation.

2. **Consistent Voice**: All error messages use Lucien's voice (🎩) to maintain the established voice architecture pattern.

3. **Admin Actions Blocked**: Even `admin_credit` and `admin_debit` are blocked during simulation. This prevents admins from accidentally modifying real user balances while testing.

4. **Read-Only Operations Allowed**: Balance queries, catalog browsing, and reward availability checks remain allowed during simulation so admins can see what users see.

## Verification Results

All imports verified working:
```bash
python -c "from bot.services.wallet import WalletService; print('Wallet imports OK')"
python -c "from bot.services.shop import ShopService; print('Shop imports OK')"
python -c "from bot.services.reward import RewardService; print('Reward imports OK')"
python -c "from bot.handlers.admin.simulation import get_simulation_banner, get_simulation_banner_for_user, format_with_banner; print('Banner imports OK')"
```

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 9ddf5fa | feat(30-04) | Add simulation safety checks to WalletService |
| 698ac92 | feat(30-04) | Add simulation safety checks to ShopService |
| 3ceb160 | feat(30-04) | Add simulation safety checks to RewardService |
| c631908 | feat(30-04) | Add simulation banner utilities to admin simulation handler |

## Self-Check: PASSED

- [x] All 4 tasks completed
- [x] Each task committed individually
- [x] All imports work without circular dependency errors
- [x] SimulationStore.is_simulating called in each service
- [x] Error messages use Lucien's voice (🎩)
- [x] Banner utilities exported for other handlers
