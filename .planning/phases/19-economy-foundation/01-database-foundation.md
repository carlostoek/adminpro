---
wave: 1
depends_on: []
files_modified:
  - bot/database/enums.py
  - bot/database/models.py
  - alembic/versions/
autonomous: false
---

# Wave 1: Database Foundation

Create the database schema for the economy system: TransactionType enum, UserGamificationProfile model, and Transaction model with proper indexes.

## Tasks

<task>
<id>1</id>
<description>Add TransactionType enum to bot/database/enums.py</description>
<file>bot/database/enums.py</file>
<spec>
Add TransactionType enum with values:
- EARN_REACTION = "EARN_REACTION"
- EARN_DAILY = "EARN_DAILY"
- EARN_STREAK = "EARN_STREAK"
- EARN_REWARD = "EARN_REWARD"
- EARN_ADMIN = "EARN_ADMIN"
- SPEND_SHOP = "SPEND_SHOP"
- SPEND_ADMIN = "SPEND_ADMIN"

Include display_name property with Spanish translations.
</spec>
</task>

<task>
<id>2</id>
<description>Create UserGamificationProfile model</description>
<file>bot/database/models.py</file>
<spec>
Add UserGamificationProfile model with fields:
- id: Integer PK
- user_id: BigInteger FK to users.user_id, unique, index
- balance: Integer default=0 (current besitos)
- total_earned: Integer default=0 (lifetime earned)
- total_spent: Integer default=0 (lifetime spent)
- level: Integer default=1 (cached level)
- created_at: DateTime default=utcnow
- updated_at: DateTime default=utcnow, onupdate=utcnow

Relationships:
- user: relationship to User model (uselist=False)

Indexes:
- idx_gamification_user_id (user_id)
- idx_gamification_level (level) for leaderboard queries

Methods:
- calculate_level(formula: str) -> int: Apply formula to total_earned
</spec>
</task>

<task>
<id>3</id>
<description>Create Transaction model</description>
<file>bot/database/models.py</file>
<spec>
Add Transaction model with fields:
- id: Integer PK
- user_id: BigInteger FK to users.user_id, index
- amount: Integer (positive for earn, negative for spend)
- type: Enum(TransactionType), index
- reason: String(255) - human readable description
- metadata: JSON nullable - extra data (admin_id, shop_item_id, etc.)
- created_at: DateTime default=utcnow, index

Indexes:
- idx_transaction_user_created (user_id, created_at) for history queries
- idx_transaction_type_created (type, created_at) for analytics
- idx_transaction_user_type (user_id, type) for filtering
</spec>
</task>

<task>
<id>4</id>
<description>Create Alembic migration for gamification tables</description>
<file>alembic/versions/</file>
<spec>
Generate new migration:
- Create user_gamification_profiles table
- Create transactions table
- Add FK constraints with CASCADE on user delete
- Create all indexes
- Add comment explaining atomic transaction pattern

Test migration:
- alembic upgrade head
- alembic downgrade -1
- alembic upgrade head (verify idempotent)
</spec>
</task>

## Verification

```python
# Verify enum exists
from bot.database.enums import TransactionType
assert TransactionType.EARN_REACTION.value == "EARN_REACTION"

# Verify models can be imported
from bot.database.models import UserGamificationProfile, Transaction

# Verify migration applies cleanly
# (Run: alembic upgrade head)
```

## must_haves

1. TransactionType enum has all 7 required types
2. UserGamificationProfile has balance, total_earned, total_spent, level fields
3. Transaction model has amount, type, reason, metadata fields
4. All foreign keys have proper indexes
5. Migration runs without errors
