# External Integrations

**Analysis Date:** 2026-01-23

## APIs & External Services

**Telegram Bot API:**
- Telegram Bot API - Core messaging, channel management, user interactions
  - SDK/Client: aiogram 3.4.1
  - Auth: Environment variable `BOT_TOKEN` (format: `<bot_id>:<bot_token>`)
  - Session: AiohttpSession with 120-second request timeout
  - Features used:
    - `bot.send_message()` - Send messages to users/channels
    - `bot.get_me()` - Verify bot identity on startup
    - `bot.create_chat_invite_link()` - Generate shareable invite links
    - `bot.ban_chat_member()` - Remove expired VIP users from channel
    - `bot.forward_message()` / `bot.copy_message()` - Message forwarding
    - FSM (Finite State Machine) for multi-step conversations
    - Middlewares for authentication and dependency injection

## Data Storage

**Databases:**
- SQLite (file-based)
  - Connection: `DATABASE_URL` environment variable (default: `sqlite+aiosqlite:///bot.db`)
  - Client: SQLAlchemy 2.0.25 with aiosqlite async driver
  - Location: `bot/database/` - `models.py`, `engine.py`, `base.py`
  - Tables:
    - `bot_config` - Global bot configuration (singleton, id=1)
    - `users` - User profiles with roles (FREE/VIP/ADMIN)
    - `vip_subscribers` - VIP subscriptions with expiry dates
    - `invitation_tokens` - Single-use tokens for VIP activation
    - `free_channel_requests` - Free channel waitlist queue
    - `subscription_plans` - Configurable pricing plans

**File Storage:**
- Local filesystem only
  - Bot database: `bot.db` (SQLite file)
  - Bot logs: stdout (configurable via LOG_LEVEL)

**Caching:**
- None - All data fetched fresh from SQLite on each request
- No Redis or external caching layer

## Authentication & Identity

**Auth Provider:**
- Telegram itself (user authentication via Telegram ID)
  - Implementation: Telegram provides user_id and message signing
  - Admin verification: Config.is_admin(user_id) checks `ADMIN_USER_IDS` from .env

**User Roles:**
- FREE - Default role for all users
- VIP - Users with active subscription (from `vip_subscribers` table)
- ADMIN - Users in `ADMIN_USER_IDS` from environment

## Monitoring & Observability

**Error Tracking:**
- None - No external error tracking service (Sentry, etc.)
- Errors logged locally via Python logging module

**Logs:**
- Python logging module (stdout)
  - Configurable levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
  - Set via `LOG_LEVEL` environment variable (default: INFO)
  - Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
  - Handlers: StreamHandler to stdout

**Health Checks:**
- Startup verification: `bot.get_me()` with retry logic (max 2 retries)
- Background task status: APScheduler job tracking
- Database connectivity: Test on `init_db()` call

## CI/CD & Deployment

**Hosting:**
- Self-hosted (runs on local machine or Termux)
- No cloud platform integration

**CI Pipeline:**
- None detected - Local development only

**Deployment Method:**
- Direct Python execution: `python main.py`
- Background execution (Termux): `nohup python main.py > bot.log 2>&1 &`
- Process management: Manual (no systemd, supervisor, or PM2)

## Environment Configuration

**Required env vars:**
- `BOT_TOKEN` - Telegram Bot API token (mandatory)
- `ADMIN_USER_IDS` - Comma-separated admin user IDs (mandatory)

**Optional env vars with defaults:**
- `DATABASE_URL` - SQLite connection (default: `sqlite+aiosqlite:///bot.db`)
- `VIP_CHANNEL_ID` - VIP channel Telegram ID (default: empty, configured via bot)
- `FREE_CHANNEL_ID` - Free channel Telegram ID (default: empty, configured via bot)
- `DEFAULT_WAIT_TIME_MINUTES` - Free queue wait time (default: 5)
- `LOG_LEVEL` - Logging verbosity (default: INFO)
- `MAX_VIP_SUBSCRIBERS` - Alert threshold (default: 1000)
- `CLEANUP_INTERVAL_MINUTES` - VIP expiration check interval (default: 60)
- `PROCESS_FREE_QUEUE_MINUTES` - Free queue check interval (default: 5)
- `FREE_REQUEST_SPAM_WINDOW_MINUTES` - Anti-spam window (default: 5)

**Secrets location:**
- `.env` file (git-ignored) in project root
- Example template: `.env.example`

## Webhooks & Callbacks

**Incoming:**
- Telegram updates via Long Polling (not webhooks)
  - Polling timeout: 30 seconds
  - Drop pending updates: True (ignore past messages)
  - Update types: Filtered via `dp.resolve_used_update_types()`

**Outgoing:**
- Messages sent to users and channels via `bot.send_message()`
- Private messages for:
  - Admin notifications (startup/shutdown)
  - VIP subscription confirmations
  - Free channel invite links
  - Error/warning messages

**ChatJoinRequest Handler:**
- Handles `ChatJoinRequest` events when users request access to private channels
- Used for Free channel approval flow
- Handler location: `bot/handlers/user/free_join_request.py`

## Background Task Integrations

**APScheduler Configuration:**
- Scheduler type: AsyncIOScheduler
- Max instances: 1 (prevents concurrent execution)
- Jobs:
  1. `expire_and_kick_vip_subscribers()` - Every 60 minutes
     - Fetches expired VIP subscriptions from database
     - Calls `bot.ban_chat_member()` to remove from channel
  2. `process_free_queue()` - Every 5 minutes
     - Checks `free_channel_requests` for ready entries
     - Generates invite links via `bot.create_chat_invite_link()`
     - Sends links to users via DM
  3. `cleanup_old_free_requests()` - Daily at 3 AM UTC
     - Deletes processed requests older than 30 days
     - Housekeeping task

## Deep Links & Token Activation

**Deep Link Integration:**
- Format: `https://t.me/botname?start=TOKEN`
- Handler: `/start` command with parameters
- Location: `bot/handlers/user/start.py`
- Activation: Automatic VIP subscription when user clicks link with valid token

## Data Flow Summary

```
Telegram User
    ↓
Long Polling (Telegram API)
    ↓
aiogram Dispatcher & Routers
    ↓
Handlers (admin, user flows)
    ↓
ServiceContainer (DI pattern)
    ↓
Services (subscription, channel, config, stats)
    ↓
SQLAlchemy ORM
    ↓
SQLite Database (bot.db)

Parallel: APScheduler Background Tasks
    ↓
    Periodic jobs checking database
    ↓
    Telegram API calls (send messages, ban users)
```

---

*Integration audit: 2026-01-23*
