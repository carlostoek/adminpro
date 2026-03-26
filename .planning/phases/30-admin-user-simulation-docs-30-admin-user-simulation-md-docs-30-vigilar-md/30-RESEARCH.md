# Phase 30: Admin User Simulation System - Research

**Researched:** 2026-03-23
**Domain:** Python/Aiogram Middleware Architecture, Runtime Context Override Patterns
**Confidence:** HIGH

## Summary

This phase implements a runtime role simulation system for admin users to test different user experiences (FREE/VIP) without modifying database records. The core challenge is creating a transparent override layer that intercepts role checks throughout the request lifecycle while maintaining safety guarantees.

The system follows a **read-time override pattern** rather than write-time mutation. This means the actual user role in the database remains unchanged; instead, a runtime context layer provides simulated role information to handlers and services.

**Primary recommendation:** Implement an in-memory Admin Override Store, a Context Resolution Layer with `resolve_user_context()` as the single source of truth, extend existing middleware to inject resolved context, and add safety guards to prevent permanent state changes during simulation.

---

## Standard Stack

### Core
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Python dict (in-memory) | 3.11+ | Admin Override Store | No external dependencies, meets non-persistence requirement |
| Aiogram BaseMiddleware | 3.4.1 | Middleware integration | Existing pattern in codebase |
| ServiceContainer | Current | DI for simulation service | Existing pattern, lazy loading |
| SQLAlchemy AsyncSession | 2.0.25 | Database access | Already used throughout codebase |

### Supporting
| Component | Purpose | When to Use |
|-----------|---------|-------------|
| datetime.utcnow() | Timestamp for simulation activation | TTL/expiration tracking |
| contextvars (optional) | Thread-local context propagation | If context needs to span async boundaries |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-memory dict | Redis/external cache | Adds external dependency (violates non-goal) |
| In-memory dict | SQLite temp table | Unnecessary complexity, persistence not required |
| Middleware injection | Handler decorators | Less consistent, harder to enforce globally |

---

## Architecture Patterns

### Recommended Project Structure

```
bot/
├── middlewares/
│   ├── __init__.py
│   ├── admin_auth.py          # Existing - validates admin permissions
│   ├── database.py            # Existing - injects session/container
│   └── simulation.py          # NEW: SimulationMiddleware (injects resolved context)
├── services/
│   ├── __init__.py
│   ├── container.py           # Existing - add simulation service
│   ├── role_detection.py      # Existing - modify to respect simulation
│   └── simulation.py          # NEW: SimulationService (override store + resolution)
├── core/
│   ├── __init__.py
│   └── simulation_context.py  # NEW: SimulationContext dataclass
└── handlers/
    └── admin/
        └── simulation.py      # NEW: Admin commands for simulation control
```

### Pattern 1: Admin Override Store (In-Memory)

**What:** Thread-safe in-memory storage mapping admin_user_id → simulation context

**When to use:** For runtime-only overrides that don't persist across restarts

**Example:**
```python
# bot/services/simulation.py
from typing import Dict, Optional, TypedDict
from datetime import datetime, timedelta

class SimulationContext(TypedDict):
    role: str  # "vip" | "free" | None
    activated_at: datetime
    expires_at: Optional[datetime]

class SimulationStore:
    """In-memory store for admin simulation contexts."""

    _store: Dict[int, SimulationContext] = {}

    @classmethod
    def set_simulation(cls, admin_id: int, role: str, ttl_minutes: int = 30) -> None:
        """Set simulation context for an admin."""
        cls._store[admin_id] = {
            "role": role,
            "activated_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=ttl_minutes)
        }

    @classmethod
    def get_simulation(cls, admin_id: int) -> Optional[SimulationContext]:
        """Get simulation context if active and not expired."""
        ctx = cls._store.get(admin_id)
        if ctx and ctx["expires_at"] and datetime.utcnow() > ctx["expires_at"]:
            cls.clear_simulation(admin_id)
            return None
        return ctx

    @classmethod
    def clear_simulation(cls, admin_id: int) -> None:
        """Clear simulation context."""
        cls._store.pop(admin_id, None)

    @classmethod
    def is_simulation_active(cls, admin_id: int) -> bool:
        """Check if admin has active simulation."""
        return cls.get_simulation(admin_id) is not None
```

### Pattern 2: Context Resolution Layer (Single Source of Truth)

**What:** Centralized function that resolves the effective role for any user

**When to use:** All role checks throughout the application must use this function

**Example:**
```python
# bot/services/simulation.py
from bot.database.enums import UserRole

async def resolve_user_context(
    user_id: int,
    real_role: UserRole,
    is_admin: bool = False
) -> UserRole:
    """
    Resolve the effective user context.

    This is the SINGLE SOURCE OF TRUTH for user role determination.
    All role checks must flow through this function.

    Args:
        user_id: Telegram user ID
        real_role: The actual role from database
        is_admin: Whether user is an admin (can simulate)

    Returns:
        UserRole: Effective role (simulated if active, real otherwise)
    """
    # Only admins can have simulated roles
    if not is_admin:
        return real_role

    # Check for active simulation
    simulation = SimulationStore.get_simulation(user_id)
    if simulation:
        simulated_role = simulation["role"]
        if simulated_role == "vip":
            return UserRole.VIP
        elif simulated_role == "free":
            return UserRole.FREE

    return real_role


class ResolvedUserContext:
    """Container for resolved user context with simulation metadata."""

    def __init__(
        self,
        user_id: int,
        real_role: UserRole,
        effective_role: UserRole,
        is_simulation: bool = False,
        simulated_role: Optional[str] = None
    ):
        self.user_id = user_id
        self.real_role = real_role
        self.effective_role = effective_role
        self.is_simulation = is_simulation
        self.simulated_role = simulated_role

    @property
    def is_vip(self) -> bool:
        """Check if effective role is VIP."""
        return self.effective_role == UserRole.VIP

    @property
    def is_free(self) -> bool:
        """Check if effective role is FREE."""
        return self.effective_role == UserRole.FREE

    @property
    def is_admin(self) -> bool:
        """Check if real role is ADMIN (simulation doesn't remove admin status)."""
        return self.real_role == UserRole.ADMIN
```

### Pattern 3: SimulationMiddleware (Integration Point)

**What:** Middleware that injects resolved context into handler data

**When to use:** Must be applied AFTER AdminAuthMiddleware and DatabaseMiddleware

**Example:**
```python
# bot/middlewares/simulation.py
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable

from bot.services.simulation import SimulationService, ResolvedUserContext
from bot.services.role_detection import RoleDetectionService
from config import Config

class SimulationMiddleware(BaseMiddleware):
    """
    Middleware that injects resolved user context with simulation support.

    Must be applied AFTER AdminAuthMiddleware (so admin status is known)
    and AFTER DatabaseMiddleware (so session is available).

    Injects:
        - data["user_context"]: ResolvedUserContext with simulation applied
        - data["is_simulation_active"]: bool flag for visibility
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Extract user from event
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user is None:
            return await handler(event, data)

        # Get real role from role detection service
        session = data.get("session")
        bot = data.get("bot")

        if session and bot:
            role_service = RoleDetectionService(session, bot)
            real_role = await role_service.get_user_role(user.id)
        else:
            # Fallback - assume FREE if no session
            from bot.database.enums import UserRole
            real_role = UserRole.FREE

        # Check if user is admin (only admins can simulate)
        is_admin = Config.is_admin(user.id)

        # Resolve effective context
        effective_role = await SimulationService.resolve_user_context(
            user_id=user.id,
            real_role=real_role,
            is_admin=is_admin
        )

        # Create resolved context object
        simulation = SimulationService.get_simulation(user.id) if is_admin else None
        user_context = ResolvedUserContext(
            user_id=user.id,
            real_role=real_role,
            effective_role=effective_role,
            is_simulation=simulation is not None,
            simulated_role=simulation["role"] if simulation else None
        )

        # Inject into data
        data["user_context"] = user_context
        data["is_simulation_active"] = user_context.is_simulation

        return await handler(event, data)
```

### Pattern 4: Safety Guards (Preventing Permanent Changes)

**What:** Decorator/service methods that block state-changing operations during simulation

**When to use:** Any operation that modifies payments, balance, rewards, or subscriptions

**Example:**
```python
# bot/services/simulation.py
import functools
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

class SimulationSafetyGuard:
    """Prevents permanent state changes during simulation mode."""

    BLOCKED_OPERATIONS = {
        "payment": "Payments cannot be processed in simulation mode",
        "balance_update": "Balance updates are disabled in simulation mode",
        "reward_grant": "Reward grants are disabled in simulation mode",
        "subscription_modify": "Subscription modifications are disabled in simulation mode",
    }

    @classmethod
    def block_if_simulation(cls, operation_type: str) -> Callable:
        """
        Decorator that blocks the operation if simulation is active.

        Args:
            operation_type: Key from BLOCKED_OPERATIONS
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Check if user_context is in kwargs (injected by middleware)
                user_context = kwargs.get("user_context")

                if user_context and user_context.is_simulation:
                    message = cls.BLOCKED_OPERATIONS.get(
                        operation_type,
                        "This operation is disabled in simulation mode"
                    )
                    logger.warning(
                        f"🚫 Blocked {operation_type} for user {user_context.user_id} "
                        f"(simulating {user_context.simulated_role})"
                    )
                    return False, message, None

                return await func(*args, **kwargs)
            return wrapper
        return decorator

    @classmethod
    def check_simulation_safe(cls, user_context: "ResolvedUserContext") -> tuple[bool, str]:
        """
        Check if operation is safe to proceed.

        Returns:
            Tuple of (is_safe, error_message)
        """
        if user_context.is_simulation:
            return False, "⚠️ Simulation mode active. This operation is disabled."
        return True, ""
```

### Pattern 5: Admin UI Controls

**What:** Bot commands and callbacks for admins to control simulation

**When to use:** Admin-only handlers for switching simulation modes

**Example:**
```python
# bot/handlers/admin/simulation.py
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.middlewares import AdminAuthMiddleware
from bot.services.simulation import SimulationService, SimulationStore
from bot.services.container import ServiceContainer

simulation_router = Router(name="simulation")
simulation_router.message.middleware(AdminAuthMiddleware())
simulation_router.callback_query.middleware(AdminAuthMiddleware())

SIMULATION_MODES = {
    "real": ("🔄 Real", "Exit simulation and use your actual role"),
    "vip": ("⭐ VIP", "Simulate VIP user experience"),
    "free": ("🆓 Free", "Simulate Free user experience"),
}

@simulation_router.message(Command("simulate"))
async def cmd_simulate(message: Message):
    """Show simulation mode selector."""
    user_id = message.from_user.id

    # Check current simulation status
    current = SimulationStore.get_simulation(user_id)
    current_mode = current["role"] if current else "real"

    # Build keyboard
    builder = InlineKeyboardBuilder()
    for mode, (emoji_label, description) in SIMULATION_MODES.items():
        prefix = "✅ " if mode == current_mode else ""
        builder.button(
            text=f"{prefix}{emoji_label}",
            callback_data=f"sim:set:{mode}"
        )
    builder.adjust(1)

    # Build status message
    if current:
        status_text = f"⚠️ <b>Simulation Active</b>\nYou are simulating: <code>{current['role'].upper()}</code>"
    else:
        status_text = "ℹ️ <b>Real Mode</b>\nYou are using your actual admin role"

    await message.answer(
        f"🎭 <b>Role Simulation</b>\n\n{status_text}\n\n"
        f"Select a mode to simulate different user experiences:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@simulation_router.callback_query(F.data.startswith("sim:set:"))
async def callback_set_simulation(callback: CallbackQuery):
    """Handle simulation mode change."""
    user_id = callback.from_user.id
    mode = callback.data.split(":")[2]

    if mode == "real":
        SimulationStore.clear_simulation(user_id)
        await callback.answer("✅ Simulation ended. Back to real mode.", show_alert=True)
    else:
        SimulationStore.set_simulation(user_id, mode, ttl_minutes=30)
        await callback.answer(
            f"🎭 Simulating {mode.upper()} mode for 30 minutes",
            show_alert=True
        )

    # Refresh menu
    await cmd_simulate(callback.message)
```

### Pattern 6: Visibility Indicator (Constant Awareness)

**What:** Visual indicator in all admin messages showing current simulation mode

**When to use:** Every admin UI response when simulation is active

**Example:**
```python
# bot/services/simulation.py

def get_simulation_banner(user_context: ResolvedUserContext) -> str:
    """
    Generate a visual banner showing simulation status.

    This should be prepended to all admin responses when simulation is active.
    """
    if not user_context.is_simulation:
        return ""

    return (
        f"🎭 <b>SIMULATION MODE</b> 🎭\n"
        f"├ Real role: {user_context.real_role.value}\n"
        f"├ Simulating: {user_context.simulated_role.upper()}\n"
        f"└ ⚠️ State changes are BLOCKED\n\n"
    )

# Usage in handlers:
# text = get_simulation_banner(user_context) + original_message
```

### Anti-Patterns to Avoid

- **Direct DB role queries in handlers:** Always use `user_context.is_vip` instead of querying the database directly
- **Caching resolved context:** The context must be resolved fresh for each request to prevent stale simulation states
- **Modifying real user data during simulation:** All state-changing operations must check `user_context.is_simulation` first
- **Simulation persisting across restarts:** The in-memory store naturally resets, which is the intended behavior
- **Allowing non-admins to simulate:** Always verify `Config.is_admin()` before applying simulation context

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Thread-safe in-memory storage | Custom concurrent data structures | Python dict + GIL (single-process) | Aiogram bots run single-process; dict operations are atomic |
| Context propagation | Manual passing through call chain | Middleware injection + data dict | Aiogram's middleware pattern handles this cleanly |
| Role check decorator | Custom validation logic | `user_context.is_vip` property | Centralized in ResolvedUserContext |
| Expiration logic | Custom scheduling threads | datetime comparison on access | Simpler, no thread management needed |
| Admin verification | Custom permission checks | Existing `Config.is_admin()` | Already implemented and tested |

**Key insight:** The existing Aiogram middleware architecture and ServiceContainer pattern provide all the infrastructure needed. The simulation layer is a thin wrapper that intercepts and modifies role resolution without changing the underlying systems.

---

## Common Pitfalls

### Pitfall 1: Inconsistent Role Resolution

**What goes wrong:** Some parts of the codebase use `user.is_vip` from the database model, others use `user_context.is_vip`, leading to inconsistent behavior during simulation.

**Why it happens:** The User model has `is_vip` property that queries the database role directly, bypassing the simulation layer.

**How to avoid:**
- Create a task to audit all `user.is_vip`, `user.role`, and `user.is_free` usages
- Replace with `user_context.is_vip` in handlers
- For services, pass `user_context` as a parameter or use the simulation-aware RoleDetectionService

**Warning signs:** Tests pass in isolation but fail in integration; admin sees VIP menu but gets Free channel access.

### Pitfall 2: Context Not Propagating to Services

**What goes wrong:** Handlers use simulated context, but services query the database directly and get real roles.

**Why it happens:** Services like SubscriptionService have methods that check VIP status by querying the database, not using the resolved context.

**How to avoid:**
- Modify `RoleDetectionService.get_user_role()` to check simulation store first
- Pass `user_context` to service methods that need role information
- Add `resolve_user_context()` call at the entry point of all role-dependent operations

**Warning signs:** Admin simulates VIP but sees "Subscribe to VIP" prompts; balance updates use real role for calculations.

### Pitfall 3: Permanent State Changes During Simulation

**What goes wrong:** Admin in simulation mode accidentally triggers a payment, balance update, or reward grant that persists.

**Why it happens:** Safety guards are not applied consistently across all state-changing operations.

**How to avoid:**
- Apply `@SimulationSafetyGuard.block_if_simulation()` decorator to all mutation methods
- Add `user_context` parameter to all service methods that modify state
- Log all blocked operations for audit purposes

**Warning signs:** Database shows unexpected transactions; users report receiving rewards they didn't earn.

### Pitfall 4: Simulation Visibility Lost

**What goes wrong:** Admin forgets they are in simulation mode and makes decisions based on simulated state.

**Why it happens:** No constant visual reminder of simulation status in the UI.

**How to avoid:**
- Prepend simulation banner to ALL admin responses when active
- Use different message styling (colors, emojis) for simulated responses
- Include simulation status in admin menu header

**Warning signs:** Admin reports "bug" that is actually expected behavior for simulated role.

### Pitfall 5: Simulation Leaking to Other Users

**What goes wrong:** Non-admin users somehow get simulated roles, or one admin's simulation affects another.

**Why it happens:** User ID not properly checked in context resolution, or global state pollution.

**How to avoid:**
- Always verify `Config.is_admin(user_id)` before applying simulation
- Use user-specific keys in the simulation store
- Never store simulation state in global or class-level variables that could leak

**Warning signs:** Regular users report seeing VIP content; admins see each other's simulated states.

---

## Code Examples

### Integration with Existing Middleware Stack

```python
# main.py - Middleware registration order
from bot.middlewares import DatabaseMiddleware, AdminAuthMiddleware
from bot.middlewares.simulation import SimulationMiddleware

# Order matters:
# 1. DatabaseMiddleware - provides session
# 2. AdminAuthMiddleware - validates admin (for admin routes)
# 3. SimulationMiddleware - injects resolved context

dp.update.middleware(DatabaseMiddleware())

# For admin routes, apply auth then simulation
admin_router.message.middleware(AdminAuthMiddleware())
admin_router.message.middleware(SimulationMiddleware())

# For user routes, just simulation (no admin check)
user_router.message.middleware(SimulationMiddleware())
```

### Handler Using Resolved Context

```python
# bot/handlers/user/start.py
@user_router.message(Command("start"))
async def cmd_start(
    message: Message,
    session: AsyncSession,
    user_context: ResolvedUserContext  # Injected by SimulationMiddleware
):
    """Handler using resolved context instead of direct DB query."""

    # WRONG: Don't query DB directly for role
    # user = await container.user.get_user(message.from_user.id)
    # if user.is_vip: ...

    # CORRECT: Use resolved context
    if user_context.is_vip:
        await message.answer("Welcome VIP!")
    elif user_context.is_free:
        await message.answer("Welcome! Upgrade to VIP for more.")

    # Visibility: Check if admin is simulating
    if user_context.is_simulation:
        await message.answer(
            f"🎭 You are simulating {user_context.simulated_role.upper()}"
        )
```

### Service Method with Safety Guard

```python
# bot/services/wallet.py
from bot.services.simulation import SimulationSafetyGuard, ResolvedUserContext

class WalletService:

    @SimulationSafetyGuard.block_if_simulation("balance_update")
    async def credit_besitos(
        self,
        user_id: int,
        amount: int,
        user_context: ResolvedUserContext = None  # Optional for non-simulated
    ):
        """Credit besitos to user - blocked during simulation."""
        # Implementation...
        pass

    async def get_balance(
        self,
        user_id: int,
        user_context: ResolvedUserContext = None
    ) -> int:
        """Get balance - safe during simulation (read-only)."""
        # Read operations don't need guards
        return await self._fetch_balance(user_id)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Direct DB role queries | Resolved context via middleware | Phase 30 | Centralized role resolution enables simulation |
| `user.is_vip` property | `user_context.is_vip` | Phase 30 | Consistent simulation-aware role checks |
| No simulation capability | Runtime override layer | Phase 30 | Admins can test user experiences safely |

**Deprecated/outdated:**
- None - this is a new capability

---

## Open Questions

1. **Should simulation affect channel access?**
   - What we know: Simulation changes role context for menus and content
   - What's unclear: Whether admin should actually be added/removed from channels during simulation
   - Recommendation: NO - channel membership is a real state change. Simulation should only affect UI/context, not actual channel membership.

2. **How to handle simulation in background tasks?**
   - What we know: Background tasks run without user context
   - What's unclear: Whether simulation should affect scheduled operations
   - Recommendation: Background tasks should use real roles always - simulation is for interactive testing only.

3. **Should we extend simulation to balance/subscription status?**
   - What we know: Optional enhancement mentioned in requirements
   - What's unclear: Complexity vs value tradeoff
   - Recommendation: Start with role only. Extend if needed based on admin feedback.

---

## Sources

### Primary (HIGH confidence)
- `/data/data/com.termux/files/home/repos/adminpro/bot/middlewares/admin_auth.py` - Existing admin validation pattern
- `/data/data/com.termux/files/home/repos/adminpro/bot/middlewares/database.py` - Existing middleware injection pattern
- `/data/data/com.termux/files/home/repos/adminpro/bot/services/container.py` - ServiceContainer DI pattern
- `/data/data/com.termux/files/home/repos/adminpro/bot/services/role_detection.py` - Current role detection implementation
- `/data/data/com.termux/files/home/repos/adminpro/bot/database/enums.py` - UserRole enum definition
- `/data/data/com.termux/files/home/repos/adminpro/docs/30_Admin_User_Simulation.md` - Phase requirements
- `/data/data/com.termux/files/home/repos/adminpro/docs/30_Vigilar.md` - Watch points and critical constraints

### Secondary (MEDIUM confidence)
- Aiogram 3.4.1 documentation - Middleware patterns (verified against codebase)
- Python 3.11 typing documentation - TypedDict, dataclass patterns

### Tertiary (LOW confidence)
- None - all findings verified against existing codebase

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Uses existing codebase patterns
- Architecture: HIGH - Middleware injection proven in codebase
- Pitfalls: HIGH - Derived from requirements analysis and watch points

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (30 days - stable patterns)

---

## RESEARCH COMPLETE

**Phase:** 30 - Admin User Simulation System
**Confidence:** HIGH

### Key Findings

1. **Single Source of Truth is Critical:** The `resolve_user_context()` function must be the ONLY place where effective roles are determined. Any direct DB queries bypassing this will break simulation consistency.

2. **Middleware Integration Pattern:** The existing Aiogram middleware stack (DatabaseMiddleware → AdminAuthMiddleware → SimulationMiddleware) provides clean injection points for resolved context.

3. **In-Memory Store is Sufficient:** Python dict meets all requirements (no persistence, no external deps, per-admin isolation) with minimal complexity.

4. **Safety Requires Explicit Guards:** The `@SimulationSafetyGuard.block_if_simulation()` decorator pattern provides declarative protection for state-changing operations.

5. **Visibility Must Be Constant:** Every admin UI response must include simulation status when active - this prevents confusion and errors.

### File Created
`.planning/phases/30-admin-user-simulation-docs-30-admin-user-simulation-md-docs-30-vigilar-md/30-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | Existing codebase patterns verified |
| Architecture | HIGH | Middleware injection proven |
| Pitfalls | HIGH | Requirements analysis + watch points |

### Open Questions
- Channel access during simulation (recommend: no change)
- Background task handling (recommend: use real roles)
- Balance/subscription simulation (recommend: phase 2)

### Ready for Planning
Research complete. Planner can now create PLAN.md files.
