# Technology Stack

**Analysis Date:** 2026-01-23

## Languages

**Primary:**
- Python 3.12.12 - Core application language, async/await support

## Runtime

**Environment:**
- Python 3.12.12

**Package Manager:**
- pip - Python package management
- Lockfile: Not present (requirements.txt used directly)

## Frameworks

**Core:**
- aiogram 3.4.1 - Telegram Bot API framework with async support

**Database:**
- SQLAlchemy 2.0.25 - Async ORM for database operations
- aiosqlite 0.19.0 - SQLite async driver

**Background Tasks:**
- APScheduler 3.10.4 - Task scheduling (IntervalTrigger and CronTrigger)

**Configuration:**
- python-dotenv 1.0.0 - Environment variable management from .env files

**Testing:**
- pytest 7.4.3 - Test framework
- pytest-asyncio 0.21.1 - Async test support

## Key Dependencies

**Critical:**
- aiogram 3.4.1 - Why it matters: Primary interface to Telegram Bot API; provides Router, FSM, middleware, exception handling
- SQLAlchemy 2.0.25 - Why it matters: ORM layer managing all database operations (users, VIP subscribers, tokens, configurations)
- APScheduler 3.10.4 - Why it matters: Executes background tasks (VIP expiration, Free queue processing, data cleanup)

**Infrastructure:**
- aiosqlite 0.19.0 - SQLite async driver compatible with SQLAlchemy async
- python-dotenv 1.0.0 - Loads configuration from .env files (BOT_TOKEN, ADMIN_USER_IDS, DATABASE_URL)

## Configuration

**Environment:**
- Loaded from `.env` file using python-dotenv
- Key configs required:
  - `BOT_TOKEN`: Telegram Bot API token (mandatory)
  - `ADMIN_USER_IDS`: Comma-separated list of admin user IDs (mandatory)
  - `DATABASE_URL`: SQLite connection string (default: `sqlite+aiosqlite:///bot.db`)
  - `VIP_CHANNEL_ID`: Telegram channel ID for VIP content (optional, configured via bot)
  - `FREE_CHANNEL_ID`: Telegram channel ID for Free content (optional, configured via bot)
  - `DEFAULT_WAIT_TIME_MINUTES`: Wait time for Free queue (default: 5)
  - `LOG_LEVEL`: Logging level - DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
  - `CLEANUP_INTERVAL_MINUTES`: Background task interval for VIP expiration (default: 60)
  - `PROCESS_FREE_QUEUE_MINUTES`: Background task interval for Free queue processing (default: 5)

**Build:**
- No build step required (pure Python application)
- Runs directly with `python main.py`

## Platform Requirements

**Development:**
- Python 3.12+
- pip package manager
- Ability to create/read .env file
- SQLite3 (usually built-in)

**Production:**
- Python 3.12+ runtime
- SQLite3 database support
- Network access to Telegram Bot API (api.telegram.org)
- Background task scheduler running continuously
- Optimized for Termux (lightweight environment)

## Database Configuration

**SQLite Optimization:**
- WAL Mode (Write-Ahead Logging) enabled in `bot/database/engine.py` - improves concurrent read/write
- PRAGMA synchronous=NORMAL - balance between performance and data safety
- Cache size: 64MB for improved query performance
- Foreign keys enabled
- Connection timeout: 30 seconds
- Pool: NullPool (SQLite doesn't use connection pooling)

## Key Integration Points

**Telegram Bot API:**
- Connection via aiogram using aiohttp sessions
- Default parse_mode: HTML
- Request timeout: 120 seconds for handlers
- Polling timeout: 30 seconds
- Session: AiohttpSession with custom timeout configuration

**Database Layer:**
- AsyncSession with context manager for transaction management
- Automatic commit/rollback handling
- Tables: `bot_config`, `users`, `vip_subscribers`, `invitation_tokens`, `free_channel_requests`, `subscription_plans`

**Background Tasks:**
- AsyncIOScheduler managing three recurring tasks:
  - VIP expiration/kick (every 60 minutes)
  - Free queue processing (every 5 minutes)
  - Data cleanup (daily at 3 AM UTC)

---

*Stack analysis: 2026-01-23*
