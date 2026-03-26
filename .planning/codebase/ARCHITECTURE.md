# Architecture

**Analysis Date:** 2026-01-23

## Pattern Overview

**Overall:** Layered Service-Oriented Architecture with Dependency Injection and FSM-based state management

**Key Characteristics:**
- **Service Container Pattern:** All business logic encapsulated in services accessed through `ServiceContainer` with lazy loading
- **Middleware Pattern:** Database sessions and admin authentication injected transparently via aiogram middlewares
- **FSM-based Workflows:** Multi-step admin operations managed via aiogram FSM (Finite State Machine) with defined states
- **Background Task Scheduler:** APScheduler for autonomous maintenance tasks (VIP expiration, Free queue processing)
- **Type-Safe Database:** SQLAlchemy Async ORM with explicit models and enums

## Layers

**Handler Layer (User Interface):**
- Purpose: Entry point for Telegram interactions; delegates business logic to services
- Location: `bot/handlers/admin/` and `bot/handlers/user/`
- Contains: Command handlers, callback query handlers, message handlers using aiogram Router
- Depends on: ServiceContainer, States, Keyboards, Formatters
- Used by: Telegram updates via Dispatcher

**Service Layer (Business Logic):**
- Purpose: Core business logic for subscriptions, channels, configuration, pricing, user management, statistics
- Location: `bot/services/`
- Contains: SubscriptionService, ChannelService, ConfigService, PricingService, StatsService, UserService
- Depends on: Database models, SQLAlchemy AsyncSession
- Used by: Handlers via ServiceContainer

**Middleware Layer (Cross-Cutting Concerns):**
- Purpose: Transparent injection of database sessions and admin authorization checks
- Location: `bot/middlewares/`
- Contains: DatabaseMiddleware (session injection), AdminAuthMiddleware (permission validation)
- Depends on: Database engine, Config for admin IDs
- Used by: Routers to process all incoming events

**Data Access Layer (Persistence):**
- Purpose: Database schema definition and async session management
- Location: `bot/database/`
- Contains: SQLAlchemy models (User, VIPSubscriber, InvitationToken, FreeChannelRequest, SubscriptionPlan, BotConfig), engine initialization, session factory
- Depends on: SQLAlchemy async, aiosqlite driver
- Used by: Services for CRUD operations

**State Management Layer (Conversation Flow):**
- Purpose: Define FSM states for multi-step workflows
- Location: `bot/states/`
- Contains: Admin states (ChannelSetupStates, WaitTimeSetupStates, BroadcastStates, PricingSetupStates, ReactionSetupStates), User states (TokenRedemptionStates, FreeAccessStates)
- Depends on: aiogram FSM framework
- Used by: Handlers to manage conversation context

**Utilities Layer (Helpers):**
- Purpose: Reusable formatting, validation, pagination, and UI component generation
- Location: `bot/utils/`
- Contains: Formatters (currency, dates, emojis), Validators (emails, emoji lists), Pagination, Keyboards factory
- Depends on: None (pure utility functions)
- Used by: Handlers and services for consistent formatting

**Background Tasks Layer (Async Maintenance):**
- Purpose: Scheduled autonomous operations outside of user interactions
- Location: `bot/background/`
- Contains: APScheduler scheduler with three recurring jobs (VIP expiration, Free queue processing, data cleanup)
- Depends on: ServiceContainer, Bot instance
- Used by: Main event loop on startup/shutdown

## Data Flow

**VIP Subscription Flow:**

1. Admin generates token via `/admin` → VIP submenú → "Generate Token with Plan"
2. Handler calls `container.subscription.generate_vip_token(plan_id=X)` → creates InvitationToken record
3. Token encoded in deep link: `https://t.me/botname?start=TOKEN`
4. User clicks link → triggers `/start TOKEN` → invokes `cmd_start` with args
5. Handler calls `container.subscription.activate_vip_subscription()` → creates VIPSubscriber record
6. User role changed from FREE to VIP via `container.user.change_role()`
7. Handler generates invite link (24h validity) → sends to user privately
8. Background task `expire_and_kick_vip_subscribers()` checks every 60 min for expired VIPs → expels from channel

**Free Access Flow:**

1. User clicks "Request Free Access" → handler creates FreeChannelRequest via `container.subscription.create_free_request()`
2. Stores with `created_at` timestamp and waits for configured minutes
3. Background task `process_free_queue()` runs every 5 min, filters by wait_time elapsed
4. For each eligible request: sends invite link (24h, single use) via `bot.send_message()`
5. User clicks link → joins channel via Telegram's join request mechanism
6. Handler `on_chat_join_request` approves request via `bot.approve_chat_join_request()`
7. Cleanup task runs daily at 3 AM UTC → deletes processed requests older than 30 days

**Admin Configuration Flow:**

1. Admin invokes `/admin` → shows main menu with config status
2. Selection of configuration option (e.g., "Setup VIP Channel") → enters FSM state
3. Each FSM state awaits specific input type (forward for channels, number for minutes, text for reactions)
4. Handler validates input and persists via service → exits state with `state.clear()`
5. Dashboard command shows real-time status of all configurations

**State Management:**

- Admin workflows use FSM: Handler sets state → receives next message → validates → updates DB → clears state
- User interactions mostly stateless except VIP token redemption (one FSM state)
- MemoryStorage used for FSM (lightweight for Termux)

## Key Abstractions

**ServiceContainer:**
- Purpose: Central dependency injection hub; lazy-loads services on first access
- Examples: `bot/services/container.py`
- Pattern: Lazy property initialization with memoization; reduces startup memory footprint
- Usage: Every handler instantiates `container = ServiceContainer(session, bot)` then accesses services as properties

**DatabaseMiddleware:**
- Purpose: Transparently provide AsyncSession to handlers without boilerplate
- Examples: `bot/middlewares/database.py`
- Pattern: BaseMiddleware with context manager; auto-commit/rollback; error handling
- Usage: `async def handler(message: Message, session: AsyncSession)` — session injected automatically

**AdminAuthMiddleware:**
- Purpose: Enforce permission checks before handler execution
- Examples: `bot/middlewares/admin_auth.py`
- Pattern: Checks Config.is_admin() before calling handler; blocks non-admins early
- Usage: Applied to admin router; non-admins receive error message, handler never runs

**FSM States Groups:**
- Purpose: Organize conversation state machines; document multi-step flows
- Examples: `bot/states/admin.py`, `bot/states/user.py`
- Pattern: Inherit from StatesGroup; each State() defines a step in workflow
- Usage: Handlers use `await state.set_state(ChannelSetupStates.waiting_for_vip_channel)` to enter states

**Service Pattern:**
- Purpose: Encapsulate domain logic; keep handlers thin and testable
- Examples: SubscriptionService, ChannelService, ConfigService
- Pattern: Async methods with type hints; validate input; log operations; return status tuples
- Usage: `success, msg, result = await service.method(...)`

## Entry Points

**Main Script:**
- Location: `main.py`
- Triggers: Executed as `python main.py` (or via nohup in Termux)
- Responsibilities: Initialize bot, create dispatcher, register handlers, manage lifecycle (on_startup, on_shutdown), start polling

**Admin Command:**
- Location: `bot/handlers/admin/main.py` → `cmd_admin` handler
- Triggers: User sends `/admin` command
- Responsibilities: Check auth, display menu, route to submenus

**User Start Command:**
- Location: `bot/handlers/user/start.py` → `cmd_start` handler
- Triggers: User sends `/start` or clicks deep link with token parameter
- Responsibilities: Detect user type (admin/VIP/free), auto-activate deep links, show welcome message

**Background Task Scheduler:**
- Location: `bot/background/tasks.py` → `start_background_tasks()` called in on_startup
- Triggers: Bot startup (automatic) and shutdown (cleanup)
- Responsibilities: Initialize APScheduler with three recurring jobs; handle errors gracefully

## Error Handling

**Strategy:** Layered error handling with early returns; explicit error messages to users; comprehensive logging

**Patterns:**

1. **Input Validation:** Handlers validate before calling services; return error messages to user immediately
   - Example: `if not token.isalnum(): await message.answer("Invalid token format")`

2. **Service Error Handling:** Services return tuples `(success: bool, message: str, result: Optional[T])`
   - Example: `success, msg, token = await service.generate_token(...)`
   - Handlers check success before proceeding

3. **Database Errors:** SessionContextManager catches and logs exceptions; rolls back transaction
   - Example: Malformed query → logs error → user receives generic "error occurred" message

4. **Telegram API Errors:** Caught in middlewares as TelegramNetworkError or TelegramBadRequest
   - Example: User blocks bot → handler logs warning → gracefully continues

5. **Background Task Errors:** Tasks wrapped in try/except; errors logged as WARNING/ERROR; scheduler continues
   - Example: Failed message send → logs error → continues with next user

## Cross-Cutting Concerns

**Logging:**
- Framework: Python `logging` module configured in each module
- Patterns: DEBUG for flow traces, INFO for state changes, WARNING for recoverable issues, ERROR/CRITICAL for failures
- Example: `logger.info(f"✅ VIP {user_id} subscription created, expires in {days} days")`

**Validation:**
- Approach: Explicit validation in handlers before state entry; validator utilities in `bot/utils/validators.py`
- Examples: Token format (alphanumeric), emoji lists (1-10 emojis), prices (positive floats)
- Errors reported to user with clear messages

**Authentication:**
- Approach: Admin check via `Config.is_admin(user_id)` against hardcoded list in .env
- User roles tracked in database (FREE, VIP, ADMIN enum in User model)
- AdminAuthMiddleware blocks non-admin access at middleware level (early prevention)

**Data Consistency:**
- Approach: SQLAlchemy transactions; foreign keys enabled in SQLite; services enforce business rules
- Example: Deleting a subscription plan cascades to InvitationToken records

**Performance Optimization:**
- Lazy loading in ServiceContainer (only load services used)
- Database indexes on frequently queried columns (user_id, status, created_at)
- SQLite WAL mode for concurrent reads during writes
- Pagination for large result sets (managed in handlers via PaginationHelper)

---

*Architecture analysis: 2026-01-23*
