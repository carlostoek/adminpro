# Codebase Structure

**Analysis Date:** 2026-01-23

## Directory Layout

```
project-root/
├── main.py                      # Entry point: initializes bot, dispatcher, lifecycle
├── config.py                    # Configuration: loads .env, validates settings, admin IDs
├── requirements.txt             # Python dependencies (aiogram, SQLAlchemy, APScheduler, etc)
├── .env.example                 # Template for environment variables
│
├── bot/                         # Bot package root
│   ├── __init__.py
│   │
│   ├── database/                # Persistence layer (SQLAlchemy)
│   │   ├── __init__.py          # Exports: init_db, close_db, get_session, get_engine
│   │   ├── base.py              # DeclarativeBase for ORM models
│   │   ├── engine.py            # Engine init, session factory, context managers
│   │   ├── models.py            # 6 models: BotConfig, User, VIPSubscriber, InvitationToken, FreeChannelRequest, SubscriptionPlan
│   │   └── enums.py             # Enum: UserRole (FREE, VIP, ADMIN), TokenStatus, RequestStatus
│   │
│   ├── services/                # Business logic layer (core functionality)
│   │   ├── __init__.py          # Exports all services
│   │   ├── container.py         # ServiceContainer: DI hub with lazy-loaded properties
│   │   ├── subscription.py      # VIP/Free subscriptions, tokens, validation, redemption
│   │   ├── channel.py           # Telegram channel operations: setup, permissions, send messages
│   │   ├── config.py            # Bot configuration singleton (channels, wait time, reactions, fees)
│   │   ├── pricing.py           # Subscription plans (create, list, activate, delete)
│   │   ├── stats.py             # Statistics: totals, VIP metrics, Free metrics, cache
│   │   └── user.py              # User management: create, get, change role, history
│   │
│   ├── handlers/                # UI/Command handlers (thin, delegate to services)
│   │   ├── __init__.py          # register_all_handlers(dispatcher)
│   │   │
│   │   ├── admin/               # Admin command handlers
│   │   │   ├── __init__.py      # Exports admin_router
│   │   │   ├── main.py          # /admin, main menu, back button, config view
│   │   │   ├── vip.py           # VIP submenú: setup channel, generate tokens
│   │   │   ├── free.py          # Free submenú: setup channel, configure wait time
│   │   │   ├── pricing.py       # Pricing: create/list/delete plans
│   │   │   ├── reactions.py     # Reaction setup: configure emoji reactions
│   │   │   ├── broadcast.py     # Broadcasting: send messages to channels (text, photo, video)
│   │   │   ├── management.py    # Management: list/manage users, subscriptions, requests
│   │   │   ├── dashboard.py     # Dashboard: health status, statistics, scheduler status
│   │   │   └── stats.py         # Detailed statistics view
│   │   │
│   │   └── user/                # User command handlers
│   │       ├── __init__.py      # Exports user_router, free_join_router
│   │       ├── start.py         # /start: detect user type, handle deep links for VIP activation
│   │       ├── vip_flow.py      # VIP flow: redeem token, create invite link, join
│   │       ├── free_flow.py     # Free flow: request access, show queue status
│   │       └── free_join_request.py  # ChatJoinRequest handler: approve free access requests
│   │
│   ├── middlewares/             # Cross-cutting concerns (injected transparently)
│   │   ├── __init__.py          # Exports DatabaseMiddleware, AdminAuthMiddleware
│   │   ├── database.py          # DatabaseMiddleware: injects AsyncSession into handlers
│   │   └── admin_auth.py        # AdminAuthMiddleware: checks Config.is_admin() before handler execution
│   │
│   ├── states/                  # FSM state definitions (workflow steps)
│   │   ├── __init__.py          # Exports all state groups
│   │   ├── admin.py             # Admin states: ChannelSetupStates, WaitTimeSetupStates, BroadcastStates, PricingSetupStates, ReactionSetupStates
│   │   └── user.py              # User states: TokenRedemptionStates, FreeAccessStates
│   │
│   ├── utils/                   # Reusable helpers (no business logic)
│   │   ├── __init__.py
│   │   ├── keyboards.py         # Keyboard factory: create_inline_keyboard, admin_main_menu_keyboard, etc
│   │   ├── formatters.py        # 19+ formatting functions: currency, dates, time delta, emojis
│   │   ├── validators.py        # Validation: email, emoji lists, prices
│   │   └── pagination.py        # Pagination helper: slice results, generate page indicators
│   │
│   └── background/              # Scheduled background tasks (async maintenance)
│       ├── __init__.py          # Exports: start_background_tasks, stop_background_tasks, get_scheduler_status
│       └── tasks.py             # APScheduler with 3 jobs: expire_and_kick_vip, process_free_queue, cleanup_old_data
│
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures: event_loop, db_setup, mock_bot
│   ├── test_e2e_flows.py        # E2E: complete VIP/Free flows, expiration, token validation
│   ├── test_integration.py      # Integration: container, services, database
│   ├── test_a3_deep_links.py    # Feature: deep link activation, plan-based tokens
│   ├── test_e2e_onda2.py        # E2E ONDA 2: stats, formatters, pagination
│   ├── test_pricing_service.py  # Unit: PricingService CRUD
│   ├── test_user_service.py     # Unit: UserService roles, history
│   └── test_sprint1_features.py # Unit: core features
│
├── docs/                        # Project documentation
│   ├── Referencia_Rápida.md     # Quick reference for development
│   ├── DESIGN.md                # System design document
│   ├── ARCHITECTURE.md          # Architecture patterns
│   └── SETUP.md                 # Setup and configuration guide
│
├── scripts/                     # Utility scripts
│   └── run_tests.sh             # Test runner (bash script)
│
├── .planning/                   # GSD planning documents
│   └── codebase/                # Codebase analysis docs (ARCHITECTURE.md, STRUCTURE.md, etc)
│
├── .git/                        # Git repository
├── .gitignore                   # Git ignore rules
├── CLAUDE.md                    # Development workflow and progress tracking
├── CHANGELOG.md                 # Release notes
├── README.md                    # Project overview and user guide
│
└── bot.db                       # SQLite database (created at runtime, SQLite WAL mode)
    ├── bot.db-wal               # Write-Ahead Log for concurrent access
    └── bot.db-shm               # Shared memory file for WAL
```

## Directory Purposes

**bot/:**
- Purpose: Main bot package containing all business logic, handlers, and infrastructure
- Contains: All Python modules except main.py and config.py
- Key files: `__init__.py` is empty; organization by concern (database, services, handlers, etc)

**bot/database/:**
- Purpose: Data persistence layer; SQLAlchemy ORM configuration and models
- Contains: SQLAlchemy declarative base, models for 6 entities, async engine, session factory
- Key files: `models.py` (6 model classes), `engine.py` (initialization and session management), `enums.py` (UserRole, status enums)

**bot/services/:**
- Purpose: Business logic encapsulation; services accessed via ServiceContainer
- Contains: 6 service classes implementing domain operations
- Key files: `container.py` (DI hub), `subscription.py` (largest, 500+ lines), others 200-400 lines each

**bot/handlers/:**
- Purpose: Telegram event handlers; thin layer that delegates to services
- Contains: Message handlers, callback query handlers, organized by admin/user role
- Key files: `admin/main.py` (main menu), `user/start.py` (entry point), `admin/vip.py`, `admin/free.py` (core workflows)

**bot/handlers/admin/:**
- Purpose: Administrative command handlers for bot configuration and management
- Contains: 8 handler modules covering setup, stats, pricing, broadcasting, management
- Key files: `main.py` (menu router), `vip.py` and `free.py` (core channel setup)

**bot/handlers/user/:**
- Purpose: User-facing command handlers for subscription management
- Contains: 4 handler modules for /start, VIP redemption, Free requests, join request handling
- Key files: `start.py` (entry point and deep link handler), `vip_flow.py` and `free_flow.py` (user workflows)

**bot/middlewares/:**
- Purpose: Cross-cutting concerns; injected transparently into all handlers
- Contains: 2 middlewares for database session injection and admin auth
- Key files: `database.py` (provides AsyncSession), `admin_auth.py` (checks permissions)

**bot/states/:**
- Purpose: FSM state definitions for multi-step workflows
- Contains: 10+ state groups organized by domain (admin channel setup, pricing, broadcast, etc)
- Key files: `admin.py` (5 state groups, 30+ states), `user.py` (2 state groups, 3 states)

**bot/utils/:**
- Purpose: Reusable utilities with no business logic dependencies
- Contains: Formatting, validation, pagination, keyboard generation
- Key files: `keyboards.py` (15+ keyboard factories), `formatters.py` (19+ formatting functions), `validators.py`, `pagination.py`

**bot/background/:**
- Purpose: Scheduled background tasks for autonomous maintenance
- Contains: APScheduler configuration and 3 recurring jobs
- Key files: `tasks.py` (280 lines, three job definitions), `__init__.py` (exports start/stop functions)

**tests/:**
- Purpose: Test suite validating all layers
- Contains: 9+ test modules covering E2E flows, integration, and unit tests
- Key files: `conftest.py` (shared fixtures), `test_e2e_flows.py` (critical flows), `test_integration.py` (service integration)

**docs/:**
- Purpose: Project documentation
- Contains: Architecture, design, setup, and quick reference guides
- Key files: `Referencia_Rápida.md` (status and quick links), `ARCHITECTURE.md` (patterns), `DESIGN.md` (requirements)

**scripts/:**
- Purpose: Automation and helper scripts
- Contains: Test runner, deployment helpers
- Key files: `run_tests.sh` (pytest wrapper)

**.planning/codebase/:**
- Purpose: GSD (Generalist Software Developer) codebase analysis documents
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, STACK.md, etc
- Key files: Generated by GSD mapping commands; consumed by planning/execution commands

## Key File Locations

**Entry Points:**
- `main.py`: Bot entry point; initializes database, creates dispatcher, starts polling
- `bot/handlers/__init__.py`: Registers all handlers and routers with dispatcher
- `bot/background/__init__.py`: Exports start/stop functions for background tasks

**Configuration:**
- `config.py`: Environment variables, admin IDs, database URL, logging setup
- `.env.example`: Template for required environment variables
- `bot/database/engine.py`: SQLite configuration (WAL mode, cache, pragmas)

**Core Logic:**
- `bot/services/container.py`: DI hub; lazy-loads all services on first access
- `bot/services/subscription.py`: VIP/Free logic (500+ lines); token generation, validation, invite links
- `bot/services/channel.py`: Telegram channel operations; setup, permissions, message sending
- `bot/services/config.py`: Bot configuration singleton (channels, wait time, fees, reactions)

**Handler Organization:**
- `bot/handlers/admin/main.py`: Admin menu router and main commands
- `bot/handlers/admin/vip.py`: VIP channel setup and token generation
- `bot/handlers/admin/free.py`: Free channel setup and wait time configuration
- `bot/handlers/user/start.py`: User entry point; detects type and handles deep links
- `bot/handlers/user/vip_flow.py`: VIP token redemption flow
- `bot/handlers/user/free_flow.py`: Free access request flow

**Testing:**
- `tests/conftest.py`: Pytest fixtures for async testing, database setup, mocks
- `tests/test_e2e_flows.py`: End-to-end flow validation (VIP complete flow, Free complete flow, expiration)
- `tests/test_integration.py`: Cross-service integration tests

## Naming Conventions

**Files:**
- Handler files: `[feature].py` in handlers/admin/ or handlers/user/
  - Example: `vip.py` for VIP handlers, `free.py` for Free handlers
- Service files: `[domain].py` in bot/services/
  - Example: `subscription.py` for subscriptions, `channel.py` for channels
- Model files: Single `models.py` in bot/database/
- State files: `[domain].py` in bot/states/
  - Example: `admin.py` for admin states, `user.py` for user states

**Functions:**
- Handlers: `cmd_[command]` or `callback_[action]` or `process_[input_type]`
  - Examples: `cmd_admin`, `callback_vip_menu`, `process_token_input`
- Services: Async methods with domain verbs
  - Examples: `generate_vip_token`, `validate_token`, `create_invite_link`, `expire_vip_subscribers`
- Utilities: Descriptive names reflecting operation
  - Examples: `format_currency`, `validate_email`, `create_inline_keyboard`

**Variables:**
- Database models: CamelCase (Python convention for classes)
  - Examples: `VIPSubscriber`, `InvitationToken`, `FreeChannelRequest`
- Local variables: snake_case
  - Examples: `user_id`, `token_string`, `admin_id`
- Constants: UPPER_SNAKE_CASE
  - Examples: `TOKEN_LENGTH`, `DEFAULT_WAIT_TIME_MINUTES`

**FSM States:**
- StatesGroup classes: CamelCase ending in `States`
  - Examples: `ChannelSetupStates`, `TokenRedemptionStates`, `PricingSetupStates`
- State fields: snake_case
  - Examples: `waiting_for_vip_channel`, `waiting_for_token`, `waiting_for_name`

**Callback Data:**
- Format: `[namespace]:[action]` or `[namespace]:[action]:[param]`
- Examples: `admin:main`, `admin:vip`, `admin:vip:generate_token`, `user:redeem_token`

## Where to Add New Code

**New Feature (User-Facing Functionality):**
- Primary code location:
  - Service: `bot/services/[domain].py` (implement business logic)
  - Handler: `bot/handlers/[admin|user]/[feature].py` (create if needed, or add to existing)
  - Models: Extend `bot/database/models.py` if new entities needed
  - States: Add to `bot/states/[admin|user].py` if multi-step workflow
  - Keyboard: Add factory function to `bot/utils/keyboards.py`
- Tests: `tests/test_[feature].py`
- Example flow: New pricing feature → add PricingService, add handlers in handlers/admin/pricing.py, add PricingSetupStates

**New Component/Module:**
- Implementation: Create file in appropriate subdirectory under `bot/`
- Naming: Match pattern for that directory
- Exports: Add to `__init__.py` of parent package
- Example: New verification service → `bot/services/verification.py` → export from `bot/services/__init__.py`

**Utilities:**
- Shared helpers: `bot/utils/[domain].py` (create if group needed, or add to existing)
- Formatting: Add to `bot/utils/formatters.py`
- Validation: Add to `bot/utils/validators.py`
- Keyboards: Add factory to `bot/utils/keyboards.py`
- Pagination: Extend `bot/utils/pagination.py` if needed

**Database Changes:**
- Add model: `bot/database/models.py` → new class inheriting Base
- Add migration: SQLAlchemy handles via `metadata.create_all()` (no migration tool used)
- Update enums: `bot/database/enums.py` if new status types needed

**Background Tasks:**
- Add job: `bot/background/tasks.py` → new async function
- Register: Call `scheduler.add_job()` in `start_background_tasks()`
- Cleanup: Add corresponding cleanup in `stop_background_tasks()` if needed

**Documentation:**
- Architecture decisions: Update `.planning/codebase/ARCHITECTURE.md`
- Setup instructions: Update `docs/SETUP.md`
- API references: Update `docs/Referencia_Rápida.md` if public interfaces change

## Special Directories

**bot.db (and related files):**
- Purpose: SQLite database storage
- Generated: Yes (created by SQLAlchemy on first `init_db()` call)
- Committed: No (.gitignore excludes *.db, *.db-wal, *.db-shm)
- Mode: WAL (Write-Ahead Logging) for better concurrency
- Cleanup: Automatic; no manual maintenance needed

**tests/**
- Purpose: Test suite (pytest)
- Generated: No (committed source files)
- Committed: Yes (all tests are part of codebase)
- Run: `pytest tests/` or `bash scripts/run_tests.sh`

**docs/**
- Purpose: Project documentation
- Generated: No (manually maintained)
- Committed: Yes
- Update when: Architecture changes, setup changes, new features add complexity

**.planning/codebase/**
- Purpose: GSD analysis documents
- Generated: Yes (by gsd:map-codebase commands)
- Committed: Yes (checked in after generation)
- Update frequency: When significant architecture/structure changes occur

---

*Structure analysis: 2026-01-23*
