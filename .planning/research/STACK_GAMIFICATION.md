# Stack Research: Gamification Features

**Project:** Telegram Bot VIP/Free - Gamification Milestone
**Domain:** Virtual currency economy, reaction tracking, daily rewards, streaks, shop system
**Researched:** 2026-02-08
**Confidence:** HIGH

## Executive Summary

The gamification module requires **no new external dependencies**. All features can be implemented using the existing stack: aiogram 3.24+ for inline reactions, APScheduler 3.10.4 for daily/streak jobs, and SQLAlchemy 2.0.25 with atomic update patterns for the "besitos" economy. The architecture follows the established ServiceContainer DI pattern with a new `GamificationContainer` for module-specific services.

Key architectural decision: **Cascading configuration** for reward conditions will be implemented via wizard-style FSM flows that create conditions inline during reward creation, avoiding UI fragmentation.

---

## Recommended Stack

### Core Technologies (No Changes Required)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| aiogram | >=3.24.0 | Inline reaction buttons, callback queries | Already in use; `InlineKeyboardMarkup` with callback_data handles reaction tracking natively |
| SQLAlchemy | 2.0.25 | Atomic besito updates, transaction audit | Existing ORM; atomic `UPDATE SET col = col + delta` pattern prevents race conditions |
| APScheduler | 3.10.4 | Daily rewards, streak expiration jobs | Already configured in `bot/background/tasks.py`; CronTrigger for midnight UTC jobs |
| aiosqlite | 0.19.0 | Async SQLite for gamification tables | Existing driver; WAL mode supports concurrent reads during atomic updates |
| asyncpg | 0.29.0 | PostgreSQL support for production | Existing driver; handles high-volume transaction logging |

### Supporting Libraries (No New Dependencies)

| Library | Status | Purpose | Notes |
|---------|--------|---------|-------|
| python-json (stdlib) | Already available | Condition serialization for `unlock_conditions` | Using JSON in TEXT columns (established pattern from `BotConfig.subscription_fees`) |
| datetime (stdlib) | Already available | Streak tracking with UTC | Critical: All streak calculations use UTC midnight to avoid timezone issues |
| dataclasses (stdlib) | Already available | Condition validators | Type-safe JSON validation without external libs like pydantic |

### Development Tools (No Changes)

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest-asyncio | Testing concurrent besito operations | Existing; essential for testing atomic update race conditions |
| alembic | Gamification table migrations | Existing; will create migrations for 13 new models |

---

## Integration with Existing Stack

### Service Container Pattern

New gamification services integrate via `GamificationContainer` (mirrors existing `ServiceContainer`):

```python
# bot/gamification/services/container.py
class GamificationContainer:
    """DI container for gamification services (lazy loading)."""

    def __init__(self, session: AsyncSession, bot: Bot):
        self._session = session
        self._bot = bot
        self._besito_service = None
        self._reward_service = None
        # ... other services

    @property
    def besito(self) -> BesitoService:
        if self._besito_service is None:
            from bot.gamification.services.besito import BesitoService
            self._besito_service = BesitoService(self._session)
        return self._besito_service
```

### Cross-Module Integration

```python
# Handlers access both containers via middleware-injected data
async def reaction_handler(callback: CallbackQuery, data: dict):
    main_container: ServiceContainer = data['container']
    gamification_container: GamificationContainer = data['gamification_container']

    # Check user role via main container
    is_vip = await main_container.user.is_vip(callback.from_user.id)

    # Award besitos via gamification container
    balance = await gamification_container.besito.grant_besitos(
        user_id=callback.from_user.id,
        amount=5 if is_vip else 1,
        transaction_type=TransactionType.REACTION,
        description=f"Reaction to message {callback.message.message_id}"
    )
```

### Background Tasks Integration

APScheduler jobs extended in `bot/background/tasks.py`:

```python
# New job: Daily streak check
_scheduler.add_job(
    check_streak_expirations,
    trigger=CronTrigger(hour=0, minute=0, timezone="UTC"),
    args=[bot],
    id="streak_expiration",
    name="Check and reset expired streaks",
    replace_existing=True,
    max_instances=1
)

# New job: Daily reward availability
_scheduler.add_job(
    reset_daily_rewards,
    trigger=CronTrigger(hour=0, minute=0, timezone="UTC"),
    args=[bot],
    id="daily_reward_reset",
    name="Reset daily reward availability",
    replace_existing=True,
    max_instances=1
)
```

---

## Database Schema Additions

### New Models (13 total)

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `UserGamification` | User's gamification profile | `total_besitos`, `current_level_id` |
| `BesitoTransaction` | Audit log for all besito changes | `amount`, `transaction_type`, `reference_id` |
| `Reaction` | Configurable emoji reactions | `emoji`, `besitos_value`, `active` |
| `UserReaction` | Individual reaction instances | `user_id`, `message_id`, `reacted_at` |
| `UserStreak` | Daily reaction streak tracking | `current_streak`, `longest_streak`, `last_reaction_date` |
| `Level` | Level progression definitions | `min_besitos`, `order`, `benefits` |
| `Mission` | Configurable missions/tasks | `criteria` (JSON), `besitos_reward` |
| `UserMission` | User progress on missions | `progress` (JSON), `status`, `completed_at` |
| `Reward` | Shop items and unlockables | `cost_besitos`, `unlock_conditions` (JSON) |
| `UserReward` | Rewards obtained by users | `obtained_via`, `obtained_at` |
| `Badge` | Special achievement type | `icon`, `rarity` |
| `UserBadge` | Badges displayed on profile | `displayed` |
| `GamificationConfig` | Module configuration (singleton) | `max_besitos_per_day`, `streak_reset_hours` |

### Critical Pattern: Atomic Updates

```python
# CORRECT: Atomic update (prevents race conditions)
from sqlalchemy import update

stmt = (
    update(UserGamification)
    .where(UserGamification.user_id == user_id)
    .values(
        total_besitos=UserGamification.total_besitos + delta,
        besitos_earned=UserGamification.besitos_earned + (delta if delta > 0 else 0),
        besitos_spent=UserGamification.besitos_spent + (abs(delta) if delta < 0 else 0),
        updated_at=datetime.now(UTC)
    )
)
await session.execute(stmt)
await session.commit()

# INCORRECT: Read-modify-write (race condition risk)
user = await session.get(UserGamification, user_id)
user.total_besitos += delta  # Race condition if another transaction modifies concurrently
await session.commit()
```

---

## Architecture Patterns

### Cascading Configuration Flow

The "cascading" requirement (create conditions inline from reward creation) is implemented via FSM wizards:

```
Admin starts reward creation
    |
Enter basic info (name, description, type)
    |
Configure unlock conditions? -> Yes
    |
Select condition type (mission/level/besitos/multiple)
    |
If mission: Select from existing missions OR create new mission (inline)
    |
If create new mission: Launch MissionWizard inline, then return to RewardWizard
    |
Complete reward creation with embedded condition reference
```

This avoids UI fragmentation by embedding the mission creation flow within the reward creation flow, then returning context to complete the reward.

### Reaction Tracking Architecture

```
Channel message posted (via ChannelService)
    |
Add inline keyboard with reaction emojis
    |
User clicks reaction -> callback_query handler
    |
Verify not already reacted (UserReaction deduplication)
    |
Record reaction + award besitos (atomic transaction)
    |
Update streak (UserStreak.current_streak += 1 if daily continuity)
    |
Update reaction button to show count (optional visual feedback)
```

### Streak Calculation Logic

```python
# Daily streak logic (UTC-based)
last_date = user_streak.last_reaction_date.date() if user_streak.last_reaction_date else None
today = datetime.now(UTC).date()
yesterday = today - timedelta(days=1)

if last_date == today:
    # Already reacted today - no streak change
    pass
elif last_date == yesterday:
    # Consecutive day - increment streak
    user_streak.current_streak += 1
    user_streak.longest_streak = max(user_streak.longest_streak, user_streak.current_streak)
else:
    # Streak broken - reset to 1 (today's reaction)
    user_streak.current_streak = 1

user_streak.last_reaction_date = datetime.now(UTC)
```

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Redis/cache layer** | Overkill for single-bot deployment; adds infrastructure complexity | SQLite WAL mode + atomic updates (sufficient for expected load) |
| **External payment processors** for virtual currency | Scope creep; besitos are earned, not purchased directly | Existing real-money flow for VIP/content packages |
| **pydantic** for validation | Adds dependency; dataclasses sufficient for condition validation | `dataclasses` + `__post_init__` validation |
| **Separate message queue** (Celery/RQ) | APScheduler already handles background jobs | APScheduler CronTrigger for daily tasks |
| **Web dashboard** for gamification admin | Scope creep; Telegram bot admin menus sufficient | Inline admin handlers with wizard FSM |
| **Real-time WebSocket updates** | Not supported by Telegram Bot API; polling sufficient | Callback query updates for immediate feedback |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| aiogram 3.24+ | APScheduler 3.10.4 | Both use asyncio - no conflicts |
| SQLAlchemy 2.0.25 | aiosqlite 0.19.0, asyncpg 0.29.0 | Tested combination |
| APScheduler 3.10.4 | pytz (via tzdata) | Timezone database for CronTrigger |

---

## Installation (No New Dependencies)

```bash
# All dependencies already in requirements.txt
# No pip install needed for gamification module

# Verify existing versions
pip show aiogram sqlalchemy apscheduler
```

---

## Sources

- `/data/data/com.termux/files/home/repos/adminpro/requirements.txt` - Existing dependency versions
- `/data/data/com.termux/files/home/repos/adminpro/bot/services/container.py` - DI pattern reference
- `/data/data/com.termux/files/home/repos/adminpro/bot/background/tasks.py` - APScheduler integration pattern
- `/data/data/com.termux/files/home/repos/adminpro/docs/dev/PROMPT_G1.2_Modelos_BD.md` - Gamification data model specifications
- `/data/data/com.termux/files/home/repos/adminpro/docs/dev/PROMPT_G2.2_BesitoService.md` - Atomic update patterns
- `/data/data/com.termux/files/home/repos/adminpro/bot/database/models.py` - Existing model patterns (JSON fields, indexes)

---

*Stack research for: Gamification milestone (virtual currency, reactions, streaks, shop)*
*Researched: 2026-02-08*
