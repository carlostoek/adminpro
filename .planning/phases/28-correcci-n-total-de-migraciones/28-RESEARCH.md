# Phase 28: Corrección total de migraciones - Research

**Researched:** 2026-03-18
**Domain:** Alembic migrations, SQLAlchemy models, dual-dialect (SQLite/PostgreSQL) schema management
**Confidence:** HIGH

## Summary

The migration chain for this project has accumulated significant drift between what `models.py` defines and what the migrations actually create. Multiple root causes compound each other: the `env.py` autogenerate import list is incomplete (missing 11 of 20 model classes), migrations were written in different styles at different points in the project's history, the `shop_products` table schema in the migration diverges from the current model, and the `20260221_000001_seed_gamification_data.py` migration uses PostgreSQL-only `DO $$ ... $$` PL/pgSQL syntax that will fail on SQLite.

The most recent two commits (`e7e7841`, `eadc117`) focused on fixing the gamification schema migration to use idiomatic Alembic `inspect()`-based guards instead of non-existent `op.create_table_if_not_exists`, and on unblocking migration file tracking from `.gitignore`. These fixes are correct but do not address the structural gaps: missing columns, schema divergence in `shop_products`, and the incomplete env.py import list.

The branch `fix/vip_expire` adds `kicked_from_channel_at` and `last_kick_notification_sent_at` columns to `vip_subscribers` (migration `20260319_034005`), but the **model only has `kicked_from_channel_at`** — `last_kick_notification_sent_at` exists in the migration but not in the model definition.

**Primary recommendation:** Audit every model class vs its migration coverage, fix all divergences with new idempotent migrations, update `env.py` imports to include all 20 model classes, and resolve the `last_kick_notification_sent_at` mismatch between model and migration.

---

## Migration Chain Analysis

### Current Chain (topological order)

```
29019dace4c7  (20260129) - initial_schema_with_all_models
     |
2bc8023392e7  (20260209) - add_gamification_tables (user_gamification_profiles + transactions)
     |
3d9f8a2e1b5c  (20260209) - add_economy_config_to_botconfig
     |
ef144ba8b77a  (20260210) - allow_null_package_id_for_vip (user_interests.package_id nullable)
     |
20260211_000001 (20260217) - fix_reaction_unique_constraint_add_emoji (user_reactions)
     |
8938058d20d3  (20260213) - merge_duplicate_heads (ef144ba8b77a + 20260211_000001)
     |
43b8b4e4a504  (20260213) - add_streak_config_columns_to_botconfig
     |
20260223_000001 (merge) - merge_heads (3d9f8a2e1b5c + 43b8b4e4a504)
     |
20260223_000002 (20260223) - create_gamification_schema (10 tables + seed data)
     |
20260223_142500 (20260223) - add_missing_botconfig_columns (PostgreSQL guard)
     |
20260227_233000 (20260227) - fix_reaction_one_per_content (unique constraint change)
     |
20260221_000001* (seed)   - seed_gamification_data [PARALLEL BRANCH - PostgreSQL-only syntax]
     |
20260317_142234 (20260317) - add_pending_request_column (free_channel_requests)
     |
0a20790932ed  (20260318) - merge_all_heads (20260221_000001 + 20260223_000002 + 20260317_142234)
     |
da1247eed1e3  (20260319) - add_kicked_tracking_to_vip_subscribers
```

The seed migration `20260221_000001` has `down_revision = '20260211_000001'` which places it on a parallel branch from `3d9f8a2e1b5c`. This is resolved by the merge at `0a20790932ed`.

---

## Critical Gaps and Divergences

### Gap 1: env.py imports only 9 of 20 model classes (CRITICAL)

**What env.py imports:**
```python
from bot.database.models import (
    BotConfig, User, SubscriptionPlan, InvitationToken,
    VIPSubscriber, FreeChannelRequest, UserInterest,
    UserRoleChangeLog, ContentPackage
)
```

**What is missing from autogenerate:**
- `UserGamificationProfile`
- `Transaction`
- `UserReaction`
- `UserStreak`
- `ContentSet`
- `ShopProduct`
- `UserContentAccess`
- `Reward`
- `RewardCondition`
- `UserReward`

**Impact:** `alembic revision --autogenerate` will not detect drift in any of the 11 missing models. Any column added to these models will never be detected automatically.

---

### Gap 2: VIPSubscriber — last_kick_notification_sent_at in migration but NOT in model (HIGH)

Migration `20260319_034005_add_kicked_tracking_to_vip_subscribers.py` adds TWO columns:
- `kicked_from_channel_at` — present in model (line 313)
- `last_kick_notification_sent_at` — **NOT in model**

This means the column will be created in the database but SQLAlchemy cannot reference it. Any service code trying to read or write `last_kick_notification_sent_at` via the ORM will fail at runtime.

Resolution options:
1. Add `last_kick_notification_sent_at` to the `VIPSubscriber` model (if the column is actually needed)
2. Remove it from the migration (if it was added by mistake)

---

### Gap 3: shop_products schema divergence (HIGH)

**Migration `20260223_000002` creates shop_products with:**
```python
sa.Column('price', sa.Numeric(10, 2), nullable=False),
sa.Column('currency', sa.String(length=10), nullable=False, server_default='$'),
sa.Column('content_set_id', sa.Integer(), nullable=True),  # nullable
```
(No `besitos_price`, no `vip_discount_percentage`, no `vip_besitos_price`, no `tier` column)

**Current ShopProduct model has:**
```python
content_set_id = Column(Integer, ForeignKey("content_sets.id"), nullable=False)  # NOT NULL
besitos_price = Column(Integer, nullable=False)
vip_discount_percentage = Column(Integer, nullable=False, default=0)
vip_besitos_price = Column(Integer, nullable=True)
tier = Column(Enum(ContentTier), nullable=False, default=ContentTier.FREE)
```
(No `price`, no `currency`)

**Impact:** Fresh deployments get a `shop_products` table that doesn't match the ORM model. Any insert/query on `ShopProduct` via SQLAlchemy will fail because required columns (`besitos_price`, `tier`) are absent.

---

### Gap 4: user_gamification_profiles — index name collision (MEDIUM)

Migration `20260209_084314` creates index named `ix_user_gamification_profiles_user_id` (Alembic `op.f()` naming convention).

Migration `20260223_000002` creates index named `idx_gamification_user_id` on the same column, guarded by `index_exists()`.

**Impact:** On fresh databases where `20260209` runs first, `20260223_000002` will skip creating `idx_gamification_user_id` because the table already exists, but the index name differs. On databases where only `20260223_000002` ran (no `20260209`), the index is `idx_gamification_user_id`. The model has no explicit index name defined on `user_id`, but the `unique=True` on the column creates `ix_user_gamification_profiles_user_id` via SQLAlchemy convention.

---

### Gap 5: TransactionType enum mismatch (MEDIUM)

**Migration `20260209_084314` defines the enum as:**
```
'EARN_REACTION', 'EARN_DAILY', 'EARN_STREAK', 'EARN_REWARD',
'EARN_ADMIN', 'SPEND_SHOP', 'SPEND_ADMIN'
```

**Migration `20260223_000002` redefines the enum for `transactions` (IF NOT EXISTS) as:**
```
'EARN_DAILY', 'EARN_REACTION', 'EARN_REWARD', 'EARN_STREAK_BONUS',
'SPEND_SHOP', 'SPEND_REWARD', 'SPEND_CONTENT'
```

**Current `TransactionType` enum in `enums.py`:**
```
EARN_REACTION, EARN_DAILY, EARN_STREAK, EARN_REWARD,
EARN_ADMIN, EARN_SHOP_REFUND, SPEND_SHOP, SPEND_ADMIN
```

On PostgreSQL, enums are first-class types. If `20260209` ran first, the enum type `transactiontype` has values from that migration. On a fresh deployment using only `20260223_000002`, different values. Neither matches the current Python enum.

**Impact:** On PostgreSQL, inserting any transaction with types `EARN_STREAK`, `EARN_ADMIN`, `EARN_SHOP_REFUND`, `SPEND_ADMIN` will raise a PostgreSQL enum constraint violation if the DB was initialized via `20260223_000002` instead of `20260209_084314`.

---

### Gap 6: seed migration uses PostgreSQL-only PL/pgSQL syntax (MEDIUM)

`20260221_000001_seed_gamification_data.py` contains:
```sql
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint ...
    ) THEN
        ALTER TABLE rewards ADD CONSTRAINT uq_rewards_name UNIQUE (name);
    END IF;
END $$;
```

This is PostgreSQL-specific syntax. Running this migration against SQLite will raise a SQL syntax error.

---

### Gap 7: free_channel_requests partial index — SQLite partial index syntax (LOW)

The model defines:
```python
Index('uq_user_pending_request', 'user_id', unique=True,
      sqlite_where=text("pending_request = 1"))
```

The migration `20260317_142234` creates a simpler non-partial index:
```python
op.create_index('idx_pending_request', 'free_channel_requests', ['pending_request'])
```

The partial unique constraint from the model (`uq_user_pending_request`) is not in any migration. PostgreSQL partial indexes use different syntax (`postgresql_where`). The SQLite `sqlite_where` kwarg in SQLAlchemy is correct, but the migration needs to be tested to confirm both dialects receive the correct constraint.

---

## Architecture Patterns

### Pattern 1: Idempotent migration with dialect guard

Used successfully in `20260317_142234_add_pending_request_column.py`:

```python
conn = op.get_bind()
dialect = conn.dialect.name

if dialect == 'sqlite':
    result = conn.execute(text("""
        SELECT COUNT(*) FROM pragma_table_info('table_name')
        WHERE name = 'column_name'
    """))
    column_exists = result.scalar() > 0
else:  # postgresql
    result = conn.execute(text("""
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_name = 'table_name'
        AND column_name = 'column_name'
    """))
    column_exists = result.scalar() > 0

if not column_exists:
    with op.batch_alter_table('table_name') as batch_op:
        batch_op.add_column(sa.Column('column_name', sa.Boolean(), nullable=True))
```

**Why this pattern:** SQLite does not support `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`. PostgreSQL does (since 9.6 with `IF NOT EXISTS`), but for maximum compatibility this guard pattern works across all versions.

### Pattern 2: Table existence guard for create (used in 20260223_000002)

```python
from sqlalchemy import inspect

def table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()

if not table_exists('my_table'):
    op.create_table('my_table', ...)
```

This is the correct Alembic API pattern. The invalid `op.create_table_if_not_exists()` was fixed in commit `eadc117`.

### Pattern 3: batch_alter_table for SQLite column modifications

SQLite does not support `ALTER TABLE ... ALTER COLUMN` or `ALTER TABLE ... DROP COLUMN` in most operations. Always use `op.batch_alter_table()`:

```python
with op.batch_alter_table('table_name') as batch_op:
    batch_op.alter_column('column_name', ...)
    batch_op.drop_column('other_column')
```

PostgreSQL supports these operations natively, but `batch_alter_table` is safe on both dialects.

### Pattern 4: Merge migration for multiple heads

When multiple migration branches exist, create a merge migration:

```python
revision = 'merge_rev_id'
down_revision = ('head1_rev_id', 'head2_rev_id', 'head3_rev_id')

def upgrade(): pass
def downgrade(): pass
```

This is how `0a20790932ed` resolves three parallel heads. The pattern is standard Alembic.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Check if column exists | Custom introspection | `inspect(bind).get_columns(table)` | Alembic-provided, works SQLite + PG |
| Check if table exists | Raw SQL | `inspect(bind).get_table_names()` | Same, idempotent |
| Check if index exists | Custom SQL | `inspect(bind).get_indexes(table)` | Returns list of dicts with `name` key |
| Modify columns in SQLite | Direct ALTER TABLE | `op.batch_alter_table()` | SQLite ALTER TABLE is extremely limited |
| PostgreSQL conditional DDL | PL/pgSQL `DO $$ ... $$` | Python-level `if dialect == 'postgresql'` | PL/pgSQL won't work on SQLite |
| Enum migration on PostgreSQL | Skip it | Explicit `op.execute("ALTER TYPE ... ADD VALUE")` | PostgreSQL enums need DDL to add values |

**Key insight:** Never use dialect-specific SQL (`DO $$ ... $$`, `pg_constraint`) inside migrations that must run on both SQLite and PostgreSQL. Keep all conditionals at the Python level using `dialect = conn.dialect.name`.

---

## Common Pitfalls

### Pitfall 1: PostgreSQL-only SQL in dual-dialect migrations
**What goes wrong:** Migration works on Railway (PostgreSQL) but crashes on local SQLite dev environment.
**Why it happens:** Developer tests only against one dialect.
**How to avoid:** Always wrap dialect-specific SQL in `if dialect == 'postgresql': ... elif dialect == 'sqlite': ...`
**Warning signs:** Any SQL containing `DO $$`, `pg_constraint`, `information_schema.table_constraints`, `regclass`.

### Pitfall 2: Column in migration but not in model
**What goes wrong:** Column is created in DB but SQLAlchemy ORM cannot see it. Queries that filter on it from Python code fail with `AttributeError`.
**Why it happens:** Migration was written to track code that was later removed from the model, or code was removed from the model after the migration was committed.
**How to avoid:** Always audit migration vs model after making changes to either.
**Warning signs:** Column exists in `pragma_table_info()` / `information_schema.columns` but not in `model.__table__.columns`.

### Pitfall 3: env.py missing model imports breaks autogenerate
**What goes wrong:** `alembic revision --autogenerate` produces empty or partial migrations, giving false confidence that model and DB are in sync.
**Why it happens:** Alembic autogenerate only detects drift for models whose metadata is registered via import in `env.py`.
**How to avoid:** Import all model classes in `env.py`. Can use `from bot.database.models import *` or explicit list.
**Warning signs:** Running `alembic revision --autogenerate -m "test"` produces an empty upgrade/downgrade when you know columns are missing.

### Pitfall 4: enum values in PostgreSQL don't auto-update
**What goes wrong:** Adding a value to a Python `str(Enum)` works fine on SQLite (column type is TEXT) but fails on PostgreSQL because the enum type is enforced at the DB level.
**Why it happens:** PostgreSQL treats `ENUM` as a named type that must be explicitly altered.
**How to avoid:** On PostgreSQL, use `op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'NEW_VALUE'")` in a migration. On SQLite, no action needed (use `String` column type, not `Enum` type, or accept divergence).
**Warning signs:** `LookupError: 'NEW_VALUE' is not among the valid values` on PostgreSQL.

### Pitfall 5: SQLite partial index syntax vs PostgreSQL
**What goes wrong:** SQLAlchemy `Index(..., sqlite_where=...)` creates the correct partial index on SQLite, but on PostgreSQL the condition is silently dropped without `postgresql_where=`.
**How to avoid:** For dual-dialect partial indexes, specify both: `Index(..., sqlite_where=..., postgresql_where=...)`.

---

## Code Examples

### Correct idempotent column addition (dual-dialect)

```python
# Source: pattern from 20260317_142234_add_pending_request_column.py
from sqlalchemy import text, inspect

def upgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == 'sqlite':
        result = conn.execute(text(
            "SELECT COUNT(*) FROM pragma_table_info('vip_subscribers') "
            "WHERE name = 'last_kick_notification_sent_at'"
        ))
    else:
        result = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name = 'vip_subscribers' "
            "AND column_name = 'last_kick_notification_sent_at'"
        ))

    if result.scalar() == 0:
        with op.batch_alter_table('vip_subscribers') as batch_op:
            batch_op.add_column(
                sa.Column('last_kick_notification_sent_at', sa.DateTime(), nullable=True)
            )
```

### Correct env.py with all model imports

```python
# Source: pattern from alembic/env.py — currently incomplete
from bot.database.models import (
    BotConfig, User, SubscriptionPlan, InvitationToken,
    VIPSubscriber, FreeChannelRequest, UserInterest,
    UserRoleChangeLog, ContentPackage,
    # MISSING — add these:
    UserGamificationProfile, Transaction, UserReaction,
    UserStreak, ContentSet, ShopProduct, UserContentAccess,
    Reward, RewardCondition, UserReward,
)
```

### Correct partial index for dual-dialect

```python
# For a partial index that works on both SQLite and PostgreSQL
from sqlalchemy import text

Index(
    'uq_user_pending_request',
    'user_id',
    unique=True,
    sqlite_where=text("pending_request = 1"),
    postgresql_where=text("pending_request = TRUE")
)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `op.create_table_if_not_exists()` (invalid) | `if not table_exists():` guard | Commit eadc117 | Migrations are now valid Alembic API |
| `.gitignore` suppressing migration files | Migrations tracked in git | Commit e7e7841 | Migration history now auditable |
| Single-dialect migrations | Dialect detection + guards | ~Phase 14 onwards | Supports both SQLite dev and PostgreSQL prod |
| Naive datetime (with timezone info) | `.replace(tzinfo=None)` naive UTC | Phase 27 / commit bc4d6c8 | Compatible with PostgreSQL's `timestamp without time zone` |
| `op.get_bind()` in async context | Synchronous ops still work in Alembic | Stable | Alembic runs migrations synchronously even with async app |

**Deprecated/outdated:**
- `DO $$ ... $$` PL/pgSQL blocks in migration `20260221_000001`: PostgreSQL-only, will crash SQLite. Replaced by Python-level dialect guard in `20260223_000002` pattern.
- `INSERT OR IGNORE` (SQLite-only SQL): replaced by `ON CONFLICT DO NOTHING` (ANSI SQL, works on PostgreSQL too).

---

## Open Questions

1. **Should `last_kick_notification_sent_at` exist?**
   - What we know: Column is added in migration `20260319_034005`, not present in model.
   - What's unclear: Is this column needed for kick retry logic in Phase 27 services? Was it accidentally omitted from the model, or accidentally added to the migration?
   - Recommendation: Search service code for `last_kick_notification_sent_at` references to determine intent. If used, add to model. If not used, remove from migration.

2. **Should `shop_products` be rebuilt from scratch or migrated column-by-column?**
   - What we know: Current model has `besitos_price`, `tier`, `vip_discount_percentage`, `vip_besitos_price`. Migration has `price`, `currency`, `content_set_id nullable`.
   - What's unclear: Does any production data exist in `shop_products`? Does Railway PostgreSQL have rows in this table?
   - Recommendation: Check Railway DB state before deciding between `DROP/CREATE` (clean) vs column migration (safe for existing data).

3. **PostgreSQL enum `transactiontype` — which values are actually in prod?**
   - What we know: Three different migrations define different values for this enum.
   - What's unclear: What values exist in Railway PostgreSQL's `transactiontype` enum type right now?
   - Recommendation: Run `SELECT enum_range(NULL::transactiontype)` on prod before writing the corrective migration.

4. **Should `20260221_000001_seed_gamification_data.py` be disabled or fixed?**
   - What we know: It uses `DO $$ ... $$` which fails on SQLite. It's on a parallel branch resolved by `0a20790932ed`.
   - What's unclear: Does it run on fresh local SQLite installs? Does it need to for dev workflow?
   - Recommendation: Add a `if dialect == 'postgresql':` guard around the `DO $$` block, or replace with Python-level alternative.

---

## Sources

### Primary (HIGH confidence)
- Direct inspection of `alembic/versions/*.py` — all 14 migration files read in full
- Direct inspection of `bot/database/models.py` — all 20 model classes checked
- Direct inspection of `alembic/env.py` — import list verified
- `bot/database/enums.py` — all enum definitions verified
- `git log --oneline -20` — recent commit history
- `git show eadc117 --stat` and `git show e7e7841 --stat` — confirmed what each fix commit changed

### Secondary (MEDIUM confidence)
- Alembic documentation on `op.batch_alter_table` for SQLite compatibility (standard well-known behavior)
- PostgreSQL documentation on enum type management (standard behavior)

---

## Full Model vs Migration Coverage Matrix

| Model Class | Table | In Migration | Missing Columns in Migrations |
|-------------|-------|-------------|-------------------------------|
| BotConfig | bot_config | Yes (initial + additive) | None apparent |
| User | users | Yes (initial) | None apparent |
| SubscriptionPlan | subscription_plans | Yes (initial) | None apparent |
| InvitationToken | invitation_tokens | Yes (initial) | None apparent |
| VIPSubscriber | vip_subscribers | Yes (initial + 20260319) | `last_kick_notification_sent_at` in migration but NOT in model |
| FreeChannelRequest | free_channel_requests | Yes (initial + 20260317) | Partial index `uq_user_pending_request` not in migration |
| UserInterest | user_interests | Yes (initial + 20260210) | None apparent |
| UserRoleChangeLog | user_role_change_log | Yes (initial) | None apparent |
| ContentPackage | content_packages | Yes (initial) | None apparent |
| UserGamificationProfile | user_gamification_profiles | Yes (20260209) | env.py missing import |
| Transaction | transactions | Yes (20260209, enum mismatch) | env.py missing import; enum values differ |
| UserReaction | user_reactions | Yes (via 20260211 + 20260223) | env.py missing import |
| UserStreak | user_streaks | Yes (20260223_000002) | env.py missing import |
| ContentSet | content_sets | Yes (20260223_000002) | env.py missing import |
| ShopProduct | shop_products | PARTIAL - wrong schema | Missing: besitos_price, vip_discount_percentage, vip_besitos_price, tier; extra: price, currency |
| UserContentAccess | user_content_access | Yes (20260223_000002) | env.py missing import |
| Reward | rewards | Yes (20260223_000002) | env.py missing import |
| RewardCondition | reward_conditions | Yes (20260223_000002) | env.py missing import |
| UserReward | user_rewards | Yes (20260223_000002) | env.py missing import |

---

## Metadata

**Confidence breakdown:**
- Migration chain topology: HIGH — read every file directly
- Model-vs-migration gap analysis: HIGH — compared models.py columns against each migration file
- shop_products schema divergence: HIGH — column-level comparison done
- TransactionType enum drift: HIGH — enums.py, migration 20260209, and migration 20260223 all checked
- env.py autogenerate gap: HIGH — import list read directly from file
- Production state (Railway DB): LOW — cannot inspect Railway PostgreSQL directly

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (stable domain — valid until model or migrations change significantly)
