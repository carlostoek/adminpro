---
phase: 26-initial-data-migration
plan: "02"
subsystem: database
tags: [seeder, rewards, gamification, data-migration]
dependency_graph:
  requires: ["26-01"]
  provides: ["seed_default_rewards function"]
  affects: ["bot/database/seeders/"]
tech_stack:
  added: []
  patterns: [async seeder, idempotent data insertion, ORM relationships]
key_files:
  created:
    - bot/database/seeders/__init__.py
    - bot/database/seeders/base.py
    - bot/database/seeders/rewards.py
  modified: []
decisions: []
metrics:
  duration_minutes: 2
  completed_date: "2026-02-21"
---

# Phase 26 Plan 02: Python Seeders for Complex Relational Data

## Summary

Created Python seeder modules for complex relational data (rewards with conditions) that can be called from Alembic migrations or application startup. The seeder handles ORM relationships and validation logic that is difficult to implement in raw SQL.

## One-Liner

Async Python seeder module with idempotent reward creation and condition relationship handling.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create seeders module structure | 52481d8 | `bot/database/seeders/__init__.py`, `bot/database/seeders/base.py` |
| 2 | Create rewards seeder | 6a4746d | `bot/database/seeders/rewards.py` |

## Implementation Details

### Module Structure

```
bot/database/seeders/
├── __init__.py       # Exports seed_default_rewards
├── base.py           # BaseSeeder abstract class
└── rewards.py        # Reward seeding logic
```

### BaseSeeder Class

Provides common functionality for all seeders:
- `__init__(session)`: Initialize with AsyncSession
- `check_exists(model_class, **filters)`: Idempotency check helper
- Abstract `seed()` method for implementation

### Rewards Seeder

**DEFAULT_REWARDS** configuration includes 3 default rewards:

1. **Primeros Pasos**
   - Type: BESITOS (10)
   - Condition: FIRST_REACTION
   - Sort order: 0

2. **Ahorrador Principiante**
   - Type: BADGE (💰 ahorrador)
   - Condition: TOTAL_POINTS >= 100
   - Sort order: 1

3. **Racha de 7 Días**
   - Type: BESITOS (50)
   - Condition: STREAK_LENGTH >= 7
   - Sort order: 2

### Key Features

- **Idempotent**: Checks for existing rewards by name before creating
- **Relationship handling**: Uses `session.flush()` to get reward ID before creating conditions
- **Proper enums**: Uses RewardType and RewardConditionType enums
- **Logging**: Reports created and skipped counts
- **Async**: Fully async with AsyncSession support

## Usage

```python
from bot.database.seeders import seed_default_rewards
from bot.database.engine import get_session

async def initialize_data():
    async with get_session() as session:
        await seed_default_rewards(session)
```

## Verification

```bash
# Verify imports work
python3 -c "from bot.database.seeders import seed_default_rewards; print('OK')"

# Verify DEFAULT_REWARDS
python3 -c "from bot.database.seeders.rewards import DEFAULT_REWARDS; print(len(DEFAULT_REWARDS))"
# Output: 3
```

## Deviations from Plan

None - plan executed exactly as written.

## Auth Gates

None encountered.

## Self-Check: PASSED

- [x] `bot/database/seeders/__init__.py` exists and exports `seed_default_rewards`
- [x] `bot/database/seeders/base.py` contains `BaseSeeder` class
- [x] `bot/database/seeders/rewards.py` exists with seeding logic
- [x] `seed_default_rewards` is importable
- [x] Function accepts AsyncSession parameter
- [x] Function creates rewards with their conditions
- [x] Function is idempotent (checks existence before creating)
- [x] Commits 52481d8 and 6a4746d exist in git history
