# Phase 26: Gamification Module Data Migration - Research

**Researched:** 2026-02-21
**Domain:** Database Migration for Existing Production System / SQLAlchemy Async
**Confidence:** HIGH

## Summary

**CLARIFICATION:** This is NOT an initial installation seed. The bot is ALREADY in production with an existing database containing real users, channels, and subscription data. This phase focuses on migrating the production database to add the new **gamification module** (economy, reactions, streaks, shop, rewards).

**Context:**
- Bot is in production with VIP/Free channel management
- Database exists with real users and data
- Adding gamification module: economy (besitos), reactions, streaks, shop, rewards
- Need to: (1) seed default data for new tables, (2) migrate existing users (create gamification profiles)

**Primary recommendation:** Create Alembic data migrations that:
1. Seed default data for new gamification tables (rewards, shop products, etc.)
2. Backfill existing users with gamification profiles
3. Update BotConfig with new economy configuration fields

## User Constraints (from Phase Context)

### Locked Decisions
- **Database:** SQLAlchemy 2.0.25 with async engine (aiosqlite)
- **Database Type:** SQLite with WAL mode
- **Migration Tool:** Alembic (already configured)
- **BotConfig Pattern:** Singleton (id=1) for global configuration
- **Economy Values:**
  - `besitos_per_reaction=5`
  - `besitos_daily_gift=50`
  - `max_reactions_per_day=20`
- **Level Formula:** `floor(sqrt(total_earned / 100)) + 1`
- **Shop System:** VIP discount system with percentage-based discounts

### Data Migration Tasks

**New Tables to Seed with Defaults:**
1. **BotConfig** - UPDATE existing record with new economy configuration fields
2. **Reward** - Default achievements/rewards for the gamification system
3. **RewardCondition** - Conditions to unlock each reward
4. **ContentSet** - Sample content sets for shop (empty file_ids, admin populates later)
5. **ShopProduct** - Default products for the shop

**Existing Data to Migrate:**
1. **UserGamificationProfile** - CREATE profiles for ALL existing users (backfill)
   - Set balance=0, total_earned=0, total_spent=0, level=1 for all existing users
   - One-time migration for users who existed before gamification module

**Already Exists (Do NOT Modify):**
- User table - Users already exist
- BotConfig record - Already exists, only UPDATE new fields
- SubscriptionPlan - May already exist from previous phases

### Out of Scope

- Admin user creation - Already exists in production
- Channel configuration - Already configured in production
- Actual file content (file_ids) - Admin must upload real content after deployment

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.25 | ORM with async support | Project standard, mature ecosystem |
| Alembic | 1.13.x | Database migrations | SQLAlchemy's official migration tool |
| aiosqlite | 0.19.0 | Async SQLite driver | Project standard for SQLite + async |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| alembic.op | built-in | Migration operations | For all DDL and DML in migrations |
| sqlalchemy.text | built-in | Raw SQL execution | For complex INSERTs with JSON |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Alembic data migration | Separate seed script | Alembic ensures data is seeded in proper transaction with schema; separate script requires manual orchestration |
| Raw SQL INSERTs | ORM objects in migration | Raw SQL is more explicit and doesn't require model imports that may drift |

## Architecture Patterns

### Recommended Project Structure
```
bot/
├── database/
│   ├── migrations/           # Alembic migrations (existing)
│   │   └── versions/
│   │       ├── 20260129_050441_initial_schema.py
│   │       └── 20260221_000000_seed_gamification_data.py  # NEW
│   └── seeders/              # NEW: Complex seeding logic
│       ├── __init__.py
│       ├── base.py           # Base seeder class
│       ├── economy.py        # Economy config seeder
│       ├── shop.py           # Shop products seeder
│       └── rewards.py        # Rewards seeder
```

### Pattern 1: Alembic Data Migration for Production Systems
**What:** Use `op.execute()` with raw SQL for data migration on existing production databases
**When to use:** Adding new module to existing system, backfilling data for existing users
**Key considerations for production:**
- **Idempotency:** Migration must be safe to run multiple times
- **Existing data:** Must preserve all existing user data
- **Backfilling:** Create records for existing users without profiles
- **Zero downtime:** Migration should be fast, no long locks

**Example - Update BotConfig with new economy fields:**
```python
def upgrade() -> None:
    # Update existing BotConfig with new economy fields
    op.execute("""
        UPDATE bot_config
        SET
            level_formula = 'floor(sqrt(total_earned / 100)) + 1',
            besitos_per_reaction = 5,
            besitos_daily_gift = 50,
            besitos_daily_streak_bonus = 10,
            max_reactions_per_day = 20,
            besitos_daily_base = 20,
            besitos_streak_bonus_per_day = 2,
            besitos_streak_bonus_max = 50,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    """)
```

**Example - Backfill UserGamificationProfile for existing users:**
```python
def upgrade() -> None:
    # Create gamification profiles for all existing users that don't have one
    op.execute("""
        INSERT OR IGNORE INTO user_gamification_profiles
        (user_id, balance, total_earned, total_spent, level, created_at, updated_at)
        SELECT
            user_id,
            0 as balance,
            0 as total_earned,
            0 as total_spent,
            1 as level,
            CURRENT_TIMESTAMP as created_at,
            CURRENT_TIMESTAMP as updated_at
        FROM users
        WHERE user_id NOT IN (
            SELECT user_id FROM user_gamification_profiles
        )
    """)
```

### Pattern 2: Python Seeder Module (Complex Relational Data)
**What:** Create a Python module with async functions that use ORM models to seed related data
**When to use:** Complex relationships, data that needs validation logic, rewards with conditions
**Example:**
```python
# bot/database/seeders/rewards.py
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.models import Reward, RewardCondition
from bot.database.enums import RewardType, RewardConditionType

DEFAULT_REWARDS = [
    {
        "name": "Primeros Pasos",
        "description": "Da tu primera reacción al contenido",
        "type": RewardType.BESITOS,
        "value": {"amount": 10},
        "conditions": [{"type": RewardConditionType.FIRST_REACTION}]
    },
    {
        "name": "Ahorrador Principiante",
        "description": "Acumula 100 besitos",
        "type": RewardType.BADGE,
        "value": {"badge_name": "saver", "emoji": "💰"},
        "conditions": [{"type": RewardConditionType.TOTAL_POINTS, "value": 100}]
    },
]

async def seed_default_rewards(session: AsyncSession) -> None:
    """Seed default rewards if they don't exist."""
    for reward_data in DEFAULT_REWARDS:
        # Check if reward exists
        result = await session.execute(
            select(Reward).where(Reward.name == reward_data["name"])
        )
        if result.scalar_one_or_none():
            continue

        # Create reward
        reward = Reward(
            name=reward_data["name"],
            description=reward_data["description"],
            reward_type=reward_data["type"],
            reward_value=reward_data["value"],
            is_repeatable=False,
            is_active=True
        )
        session.add(reward)
        await session.flush()

        # Create conditions
        for cond_data in reward_data["conditions"]:
            condition = RewardCondition(
                reward_id=reward.id,
                condition_type=cond_data["type"],
                condition_value=cond_data.get("value")
            )
            session.add(condition)

    await session.commit()
```

### Pattern 3: Hybrid Approach (Recommended)
**What:** Use Alembic migration for simple data and user backfill, seeder module for complex data
**When to use:** When you have both static config and complex relational data
**Implementation:**
1. Alembic migration handles: UPDATE BotConfig, backfill UserGamificationProfile
2. Python seeder called from migration handles: Rewards with conditions, Shop products
3. Migration remains idempotent

### Anti-Patterns to Avoid
- **Dropping and recreating data:** Never drop existing data in a production migration
- **Assuming empty tables:** Always check if data exists, don't assume fresh install
- **Not handling existing users:** Must create profiles for ALL existing users
- **Long-running migrations:** Use efficient SQL, avoid ORM for large backfills
- **Non-idempotent updates:** Ensure migrations can run multiple times safely

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Migration orchestration | Custom migration runner | Alembic's built-in system | Alembic handles transaction management, versioning, rollback |
| JSON serialization for SQL | Manual string formatting | SQLAlchemy's `text()` with bind parameters | Prevents SQL injection, handles type conversion |
| Idempotency checks | Complex custom logic | `INSERT OR IGNORE` or `ON CONFLICT` | SQLite has native support |
| Async database operations | Thread pools or sync calls | `asyncio` + `async_session` | Native async support in SQLAlchemy 2.0 |
| Backfilling user data | Python loops over users | Single INSERT...SELECT statement | Much faster for large user bases |

**Key insight:** The project already uses Alembic successfully. Don't introduce a new seeding mechanism when Alembic's migration system is designed exactly for this purpose - evolving the database schema AND data together in versioned, transactional steps.

## Common Pitfalls

### Pitfall 1: Non-Idempotent Migrations
**What goes wrong:** Migration fails if run twice because it tries to insert duplicate data
**Why it happens:** No check for existing data before INSERT
**How to avoid:** Use `INSERT OR IGNORE` (SQLite) or check existence first
**Warning signs:** Migration fails with "unique constraint violated" on second run

```python
# CORRECT: Idempotent insertion
op.execute("""
    INSERT OR IGNORE INTO rewards (name, description, ...)
    VALUES ('Primeros Pasos', 'Da tu primera reacción', ...)
""")
```

### Pitfail 2: Breaking Existing Data
**What goes wrong:** Migration modifies or deletes existing user data
**Why it happens:** Using UPDATE without WHERE clause, or DROP TABLE
**How to avoid:** Always use WHERE clauses, never DROP existing tables in production
**Warning signs:** Data loss after deployment

```python
# CORRECT: Only update specific record
op.execute("""
    UPDATE bot_config
    SET besitos_per_reaction = 5
    WHERE id = 1
""")
```

### Pitfall 3: Missing User Backfill
**What goes wrong:** Existing users don't have gamification profiles, causing errors
**Why it happens:** Only seeding defaults, not creating profiles for existing users
**How to avoid:** Always backfill existing data when adding new required tables
**Warning signs:** "Profile not found" errors for existing users after deployment

```python
# CORRECT: Backfill all existing users
op.execute("""
    INSERT OR IGNORE INTO user_gamification_profiles
    (user_id, balance, total_earned, total_spent, level, created_at, updated_at)
    SELECT user_id, 0, 0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    FROM users
    WHERE user_id NOT IN (SELECT user_id FROM user_gamification_profiles)
""")
```

### Pitfall 4: JSON Column Formatting
**What goes wrong:** JSON data not properly formatted for SQLite
**Why it happens:** SQLite stores JSON as text; improper quoting causes parse errors
**How to avoid:** Use single quotes around the entire JSON string, double quotes inside
**Warning signs:** "malformed JSON" errors when reading data

```python
# CORRECT: Proper JSON formatting for SQLite
op.execute("""
    INSERT INTO rewards (reward_value)
    VALUES ('{"amount": 10}')  -- Single quotes outer, double inner
""")
```

### Pitfall 5: Foreign Key Constraints in Data Migration
**What goes wrong:** Inserting child data before parent data exists
**Why it happens:** Migration order doesn't respect referential integrity
**How to avoid:** Insert parent tables first, use `await session.flush()` to get IDs
**Warning signs:** "foreign key constraint failed" errors

### Pitfall 6: Async Context Issues
**What goes wrong:** Trying to use async functions in Alembic's sync context
**Why it happens:** Alembic migrations run in sync context by default
**How to avoid:** Use `op.execute()` for simple data; for complex async seeders, use `asyncio.run()` or call from application startup
**Warning signs:** "coroutine was never awaited" or event loop errors

## Code Examples

### Example 1: Complete Gamification Migration
```python
"""Add gamification module default data

Revision ID: seed_gamification_data
Revises: previous_migration
Create Date: 2026-02-21

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'seed_gamification'
down_revision: Union[str, None] = 'previous_migration_id'

def upgrade() -> None:
    # 1. Update BotConfig with economy defaults
    op.execute("""
        UPDATE bot_config
        SET
            level_formula = 'floor(sqrt(total_earned / 100)) + 1',
            besitos_per_reaction = 5,
            besitos_daily_gift = 50,
            besitos_daily_streak_bonus = 10,
            max_reactions_per_day = 20,
            besitos_daily_base = 20,
            besitos_streak_bonus_per_day = 2,
            besitos_streak_bonus_max = 50,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    """)

    # 2. Backfill gamification profiles for existing users
    op.execute("""
        INSERT OR IGNORE INTO user_gamification_profiles
        (user_id, balance, total_earned, total_spent, level, created_at, updated_at)
        SELECT
            user_id,
            0 as balance,
            0 as total_earned,
            0 as total_spent,
            1 as level,
            CURRENT_TIMESTAMP as created_at,
            CURRENT_TIMESTAMP as updated_at
        FROM users
        WHERE user_id NOT IN (
            SELECT user_id FROM user_gamification_profiles
        )
    """)

    # 3. Seed default rewards (idempotent)
    op.execute("""
        INSERT OR IGNORE INTO rewards
        (name, description, reward_type, reward_value, is_repeatable, is_secret, claim_window_hours, is_active, sort_order, created_at, updated_at)
        VALUES
        ('Primeros Pasos', 'Da tu primera reacción al contenido', 'BESITOS', '{"amount": 10}', 0, 0, 168, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('Ahorrador Principiante', 'Acumula 100 besitos', 'BADGE', '{"badge_name": "saver", "emoji": "💰"}', 0, 0, 168, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('Racha de 7 Días', 'Mantén una racha de 7 días reclamando el regalo diario', 'BESITOS', '{"amount": 50}', 0, 0, 168, 1, 2, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """)

def downgrade() -> None:
    # Reset economy config
    op.execute("""
        UPDATE bot_config
        SET
            level_formula = NULL,
            besitos_per_reaction = NULL,
            besitos_daily_gift = NULL,
            besitos_daily_streak_bonus = NULL,
            max_reactions_per_day = NULL,
            besitos_daily_base = NULL,
            besitos_streak_bonus_per_day = NULL,
            besitos_streak_bonus_max = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    """)

    # Note: We intentionally do NOT delete gamification profiles or rewards
    # on downgrade to preserve user data. This is a production system.
```

### Example 2: Python Seeder for Complex Rewards
```python
# bot/database/seeders/rewards.py
"""Default rewards seeder for the gamification system."""
import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.database.models import Reward, RewardCondition
from bot.database.enums import RewardType, RewardConditionType

logger = logging.getLogger(__name__)

DEFAULT_REWARDS = [
    {
        "name": "Primeros Pasos",
        "description": "Da tu primera reacción al contenido",
        "type": RewardType.BESITOS,
        "value": {"amount": 10},
        "conditions": [{"type": RewardConditionType.FIRST_REACTION}]
    },
    {
        "name": "Ahorrador Principiante",
        "description": "Acumula 100 besitos",
        "type": RewardType.BADGE,
        "value": {"badge_name": "saver", "emoji": "💰"},
        "conditions": [{"type": RewardConditionType.TOTAL_POINTS, "value": 100}]
    },
    {
        "name": "Racha de 7 Días",
        "description": "Mantén una racha de 7 días",
        "type": RewardType.BESITOS,
        "value": {"amount": 50},
        "conditions": [{"type": RewardConditionType.STREAK_LENGTH, "value": 7}]
    }
]

async def seed_default_rewards(session: AsyncSession) -> None:
    """
    Seed default rewards if they don't exist.

    Args:
        session: Async database session
    """
    for reward_data in DEFAULT_REWARDS:
        # Check if reward exists
        result = await session.execute(
            select(Reward).where(Reward.name == reward_data["name"])
        )
        if result.scalar_one_or_none():
            logger.debug(f"Reward '{reward_data['name']}' already exists, skipping")
            continue

        # Create reward
        reward = Reward(
            name=reward_data["name"],
            description=reward_data["description"],
            reward_type=reward_data["type"],
            reward_value=reward_data["value"],
            is_repeatable=False,
            is_active=True
        )
        session.add(reward)
        await session.flush()  # Get reward.id

        # Create conditions
        for cond_data in reward_data["conditions"]:
            condition = RewardCondition(
                reward_id=reward.id,
                condition_type=cond_data["type"],
                condition_value=cond_data.get("value")
            )
            session.add(condition)

        logger.info(f"Created reward: {reward_data['name']}")

    await session.commit()
```

### Example 3: Shop Products Seeder
```python
# bot/database/seeders/shop.py
"""Default shop products seeder."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from bot.database.models import ShopProduct, ContentSet
from bot.database.enums import ContentTier, ContentType

logger = logging.getLogger(__name__)

DEFAULT_PRODUCTS = [
    {
        "name": "Pack de Bienvenida",
        "description": "Contenido especial para nuevos miembros",
        "besitos_price": 50,
        "vip_discount": 20,
        "tier": ContentTier.FREE,
        "content_set": {
            "name": "Welcome Pack",
            "description": "Fotos de bienvenida",
            "content_type": ContentType.PHOTO_SET,
            "tier": ContentTier.FREE,
            "file_ids": []  # Empty - to be populated later
        }
    },
    {
        "name": "Pack VIP Especial",
        "description": "Contenido exclusivo para suscriptores VIP",
        "besitos_price": 200,
        "vip_discount": 50,
        "tier": ContentTier.VIP,
        "content_set": {
            "name": "VIP Special",
            "description": "Contenido premium mensual",
            "content_type": ContentType.MIXED,
            "tier": ContentTier.VIP,
            "file_ids": []
        }
    }
]

async def seed_default_shop_products(session: AsyncSession) -> None:
    """Seed default shop products with their content sets."""
    for product_data in DEFAULT_PRODUCTS:
        # Check if product exists
        result = await session.execute(
            select(ShopProduct).where(ShopProduct.name == product_data["name"])
        )
        if result.scalar_one_or_none():
            continue

        # Create content set first
        content_data = product_data["content_set"]
        content_set = ContentSet(
            name=content_data["name"],
            description=content_data["description"],
            content_type=content_data["content_type"],
            tier=content_data["tier"],
            file_ids=content_data["file_ids"],
            is_active=True
        )
        session.add(content_set)
        await session.flush()

        # Create product
        product = ShopProduct(
            name=product_data["name"],
            description=product_data["description"],
            content_set_id=content_set.id,
            besitos_price=product_data["besitos_price"],
            vip_discount_percentage=product_data["vip_discount"],
            tier=product_data["tier"],
            is_active=True,
            sort_order=0
        )
        session.add(product)
        logger.info(f"Created shop product: {product_data['name']}")

    await session.commit()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw SQLAlchemy 1.x Core | SQLAlchemy 2.0 with async | SQLAlchemy 2.0 (2023) | Native async support, improved type hints |
| Sync database operations | Async throughout | Project start | Better performance, non-blocking I/O |
| Manual migration scripts | Alembic with autogenerate | Project phase 14 | Versioned, reversible migrations |
| Synchronous SQLite | SQLite with WAL mode | Project phase 1 | Better concurrency for async operations |

**Deprecated/outdated:**
- Synchronous database drivers in async contexts: Use aiosqlite for SQLite
- Manual schema management: Use Alembic for all schema changes
- JSON as TEXT without validation: Use SQLAlchemy's JSON type with proper dialect handling

## Open Questions (Production Context)

1. **Reward Conditions for Existing Users**
   - What we know: Rewards track progress via UserReward table
   - What's unclear: Should existing users get retroactive credit for achievements?
   - Recommendation: Start fresh - existing users begin gamification from zero

2. **Content File IDs for Shop**
   - What we know: ContentSet.file_ids stores Telegram file_ids
   - What's unclear: Seed with empty file_ids and document admin upload process?
   - Recommendation: Create sample products with empty file_ids, admin uploads content post-deployment

3. **Downgrade Strategy**
   - What we know: Production systems should preserve user data
   - What's unclear: Should downgrade remove gamification data or just disable features?
   - Recommendation: Downgrade should NOT delete user data; only reset config to NULL

4. **Migration Timing with Deployment**
   - What we know: Alembic runs before bot starts
   - What's unclear: Should migration be run manually before deployment or auto-run?
   - Recommendation: Auto-run as part of deployment, but have rollback plan ready

## Sources

### Primary (HIGH confidence)
- `/data/data/com.termux/files/home/repos/adminpro/alembic/versions/20260129_050441_initial_schema_with_all_models.py` - Existing seed pattern (lines 159-163)
- `/data/data/com.termux/files/home/repos/adminpro/bot/database/models.py` - All model definitions
- `/data/data/com.termux/files/home/repos/adminpro/bot/database/enums.py` - Enum definitions for seeding
- `/data/data/com.termux/files/home/repos/adminpro/alembic/env.py` - Alembic configuration
- SQLAlchemy 2.0 Documentation - Async patterns and migration best practices

### Secondary (MEDIUM confidence)
- Alembic official documentation - Data migration patterns
- SQLite documentation - JSON and UPSERT support

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Project already uses these tools successfully
- Architecture: HIGH - Pattern already established in initial migration
- Pitfalls: MEDIUM-HIGH - Based on common SQLAlchemy/Alembic issues and production migration experience

**Research date:** 2026-02-21
**Valid until:** 2026-03-21 (30 days - SQLAlchemy/Alembic are stable)
