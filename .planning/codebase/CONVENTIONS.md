# Coding Conventions

**Analysis Date:** 2026-01-23

## Naming Patterns

**Files:**
- Snake case for module files: `subscription.py`, `admin_auth.py`, `formatters.py`
- Descriptive names indicating purpose: `bot/services/subscription.py`, `bot/handlers/admin/vip.py`
- Package directories use lowercase: `bot/`, `services/`, `handlers/`, `middlewares/`, `states/`, `utils/`, `background/`
- Test files follow pattern: `tests/test_e2e_flows.py`, `test_pricing_service.py`, `test_formatters.py`

**Functions:**
- Async functions use `async def` with descriptive action verbs: `async def generate_vip_token()`, `async def process_free_queue()`
- Non-async utilities use `def`: `def create_inline_keyboard()`, `def format_datetime()`
- Private methods prefix with underscore: `_is_cache_fresh()`, `_get_from_cache()`, `_set_cache()`, `_count_vip_by_status()`
- Boolean getters use `is_` or `has_` prefix: `is_vip_active()`, `is_fully_configured()`, `has_vip_subscription()`
- Callback handlers use `callback_` prefix: `callback_admin_main()`, `callback_vip_menu()`, `callback_generate_token_with_plan()`
- Command handlers use `cmd_` prefix: `cmd_admin()`, `cmd_start()`
- Message/event processors use `process_` prefix: `process_vip_channel_forward()`, `process_free_channel_forward()`, `process_wait_time_input()`

**Variables:**
- Camel case for local variables: `user_id`, `admin_id`, `wait_time_minutes`, `vip_channel_id`, `token_str`
- Boolean flags describe what they represent: `is_configured`, `used`, `active`, `processed`, `has_permission`
- Loop counters: `attempt`, `days`, `count`, `limit`, `offset`
- Collections use plural: `plans`, `users`, `tokens`, `subscribers`, `reactions`
- Constants uppercase: `CLEANUP_INTERVAL_MINUTES`, `PROCESS_FREE_QUEUE_MINUTES`

**Classes:**
- PascalCase for all classes: `SubscriptionService`, `ServiceContainer`, `AdminAuthMiddleware`, `BotConfig`, `VIPSubscriber`
- Abstract base classes inherit from framework types: `class AdminAuthMiddleware(BaseMiddleware):`
- Service classes suffixed with `Service`: `SubscriptionService`, `ChannelService`, `ConfigService`, `StatsService`, `PricingService`, `UserService`
- Model classes use singular nouns: `BotConfig`, `User`, `VIPSubscriber`, `InvitationToken`, `SubscriptionPlan`
- State groups use PascalCase with `States` suffix: `ChannelSetupStates`, `WaitTimeSetupStates`, `TokenRedemptionStates`

**Types:**
- Enum values use snake_case: `status='active'`, `status='expired'`, `role=UserRole.VIP`, `processed=False`
- Type hints use `Optional`, `List`, `Dict`, `Tuple` from `typing` module
- Import style: `from typing import Optional, List, Tuple, Dict`

## Code Style

**Formatting:**
- No linting config file detected (no .flake8, .pylintrc, pyproject.toml)
- 4-space indentation (Python default)
- Line length appears consistent but not enforced via config
- UTF-8 encoding with inline comments explaining logic

**Linting:**
- Not explicitly configured but code follows PEP 8 conventions
- No strict formatting tool detected (no Prettier, Black, Ruff configs)
- Code quality maintained through manual review

**Docstrings:**
- Google Style docstrings for all public functions and classes
- Always includes Args, Returns, Raises sections
- Examples provided in docstring for complex utility functions
- Module docstrings at top of each file explaining purpose
- Format:
  ```python
  def function_name(param1: str) -> str:
      """
      One-line summary.

      Longer description if needed.

      Args:
          param1: Description of param1

      Returns:
          Description of return value

      Raises:
          ValueError: When validation fails
          RuntimeError: When specific condition occurs

      Examples:
          >>> function_name("example")
          "result"
      """
  ```

## Import Organization

**Order:**
1. Standard library imports: `import logging`, `import secrets`, `from datetime import datetime, timedelta`
2. Third-party framework imports: `from aiogram import Bot, Router, F`, `from sqlalchemy import select`
3. Internal app imports: `from bot.services.container import ServiceContainer`, `from config import Config`

**Path Aliases:**
- No path aliases detected in codebase
- Direct imports from module structure: `from bot.database.models import VIPSubscriber`
- Relative imports used within packages: `from bot.middlewares import AdminAuthMiddleware`

**Import Style:**
- Prefer specific imports: `from typing import Optional, List, Dict`
- Framework imports on separate lines from same package: `from aiogram import Router, F` (multiple on one line if short)
- Database imports grouped: `from sqlalchemy import select, delete` and `from sqlalchemy.ext.asyncio import AsyncSession`

## Error Handling

**Patterns:**
- Explicit try-except blocks with specific exception types:
  ```python
  try:
      # Operation
  except TelegramBadRequest:
      logger.error("Bad request")
  except TelegramForbiddenError:
      logger.error("Forbidden")
  except Exception as e:
      logger.error(f"Unexpected error: {e}", exc_info=True)
  ```

- Validation with ValueError and RuntimeError:
  ```python
  if duration_hours < 1:
      raise ValueError("duration_hours debe ser al menos 1")

  if not token_str:
      raise RuntimeError("No se puede generar token único después de 10 intentos")
  ```

- Return tuples for operations with status: `(bool, str, Optional[Model])`
  ```python
  success, msg, subscriber = await container.subscription.redeem_vip_token(...)
  ```

- Guard clauses for early returns:
  ```python
  if not vip_channel_id:
      logger.warning("Canal VIP no configurado")
      return
  ```

## Logging

**Framework:** Python's `logging` module

**Initialization:**
- All modules create logger at top: `logger = logging.getLogger(__name__)`
- Imported once per module

**Patterns:**
- INFO for major operations: `logger.info(f"📋 Admin panel abierto por user {message.from_user.id}")`
- WARNING for non-critical issues: `logger.warning("⚠️ Canal VIP no configurado, saltando expulsión")`
- ERROR for exceptions: `logger.error(f"❌ Error en tarea: {e}", exc_info=True)`
- DEBUG for detailed flow: `logger.debug(f"✅ SubscriptionService inicializado")`

**Style:**
- Use emoji prefixes for visual scanning: ✅, ⚠️, ❌, 📋, 🔄, 👍, 👤, 🚫
- Include context: user IDs, operation names, counts
- Use f-strings for formatting
- exc_info=True for exceptions to include traceback

## Comments

**When to Comment:**
- Complex business logic: when token generation or subscription flows are non-obvious
- Integration points: explaining why specific framework APIs are used
- Edge cases: like "max_instances=1 prevents race conditions" in APScheduler setup
- Not used for obvious code (e.g., no comments explaining simple assignments)

**Style:**
- Inline comments use `# ` (space after hash)
- Comments on separate lines for blocks
- English language (codebase uses Spanish in docstrings/logs, but comments in English)

## Function Design

**Size:**
- Service methods average 20-40 lines
- Handlers average 30-60 lines
- Utility functions 10-20 lines
- Larger functions broken into sections with comments: `# ===== TOKENS VIP =====`

**Parameters:**
- Type hints required for all parameters: `async def generate_vip_token(self, generated_by: int, duration_hours: int = 24) -> InvitationToken:`
- Session and bot passed as constructor arguments to services, injected via middlewares in handlers
- Keyword arguments used for optional parameters with defaults

**Return Values:**
- Services return models directly: `-> InvitationToken`, `-> Optional[VIPSubscriber]`
- Handlers return None (async operations with side effects)
- Utility functions return specific types: `-> str`, `-> Dict`, `-> bool`, `-> List[Dict]`
- Complex results use tuples: `-> Tuple[bool, str, Optional[VIPSubscriber]]`

## Module Design

**Exports:**
- `bot/services/__init__.py` exports all services via: `from bot.services.container import ServiceContainer`
- `bot/handlers/admin/__init__.py` exports main router: `from bot.handlers.admin.main import admin_router`
- `bot/states/__init__.py` exports all state groups
- `bot/middlewares/__init__.py` exports middleware classes

**Barrel Files:**
- Used for organizing multi-file modules
- Example: `bot/handlers/admin/__init__.py` imports from vip.py, free.py, stats.py, etc.
- Makes imports cleaner: `from bot.handlers.admin import admin_router`

**Service Container Pattern:**
- Central dependency injection through `ServiceContainer` class
- Lazy loading with property decorators: `@property def subscription(self):`
- All services initialized with `session` and `bot` in constructor
- Container prevents duplicate service instances per request

## Async/Await Patterns

**Async Functions:**
- All database operations marked `async`: `async def get_vip_subscriber(self, user_id: int) -> Optional[VIPSubscriber]:`
- All bot API calls marked `async`: `async def send_to_channel(self, channel_id: str, text: str) -> (bool, str)`
- Async context managers for database sessions: `async with get_session() as session:`

**Async Context Managers:**
- Used for resource management: `async with get_session() as session:` opens and closes DB session
- Used in fixtures: `async with get_session_factory()() as session:`

## Type Hints

**Coverage:** 100% for new code
- All function parameters have type hints
- All function returns have type hints
- Class attributes documented with types in docstrings
- Optional types explicitly marked: `Optional[str]`, `Optional[InvitationToken]`

**Style:**
- Use `from typing import Optional, List, Dict, Tuple, Union`
- Prefer `Optional[Type]` over `Union[Type, None]`
- Use generics for collections: `List[Dict]`, `Dict[str, float]`
- Async return types: `async def func() -> Type:` not `-> Awaitable[Type]`

---

*Convention analysis: 2026-01-23*
