"""Fix transactiontype enum to match current Python TransactionType enum

Revision ID: 20260320_000002
Revises: 20260320_000001
Create Date: 2026-03-20 00:00:02.000000+00:00

Gap: Migration 20260223_000002 created transactiontype with old values.
Current Python TransactionType enum has different/additional values.
On PostgreSQL, this causes errors when inserting transactions with new types.

Python TransactionType (current, in bot/database/enums.py):
  EARN_REACTION, EARN_DAILY, EARN_STREAK, EARN_REWARD,
  EARN_ADMIN, EARN_SHOP_REFUND, SPEND_SHOP, SPEND_ADMIN

PostgreSQL enum (from old migration):
  EARN_DAILY, EARN_REACTION, EARN_REWARD, EARN_STREAK_BONUS,
  SPEND_SHOP, SPEND_REWARD, SPEND_CONTENT

This migration adds all missing values and is safe to run multiple times
(uses IF NOT EXISTS syntax for each ADD VALUE).

IMPORTANT: ALTER TYPE ... ADD VALUE cannot run inside a PostgreSQL transaction.
Alembic wraps migrations in a transaction by default. We issue an explicit COMMIT
before the ADD VALUE loop to exit the transaction first.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260320_000002'
down_revision: Union[str, None] = '20260320_000001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All values required by current Python TransactionType enum
REQUIRED_ENUM_VALUES = [
    'EARN_REACTION',
    'EARN_DAILY',
    'EARN_STREAK',
    'EARN_REWARD',
    'EARN_ADMIN',
    'EARN_SHOP_REFUND',
    'SPEND_SHOP',
    'SPEND_ADMIN',
]


def upgrade() -> None:
    """Add missing values to PostgreSQL transactiontype enum.

    On SQLite, enums are stored as strings — no ALTER TYPE needed.
    On PostgreSQL, ALTER TYPE ... ADD VALUE IF NOT EXISTS is idempotent.

    PostgreSQL restriction: ALTER TYPE ADD VALUE cannot run inside a transaction.
    We issue an explicit COMMIT before the loop to exit the implicit transaction
    that Alembic opens. This is the documented pattern for this scenario.
    """
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect != 'postgresql':
        # SQLite stores enum values as plain strings, no ALTER TYPE needed
        print("SQLite dialect: skipping transactiontype enum ALTER (not needed)")
        return

    # PostgreSQL: EXIT the implicit Alembic transaction before ALTER TYPE ADD VALUE.
    # ALTER TYPE ADD VALUE cannot run inside a transaction block on PostgreSQL.
    # This COMMIT ends the current transaction; subsequent statements run auto-committed.
    op.execute(sa.text("COMMIT"))

    # Add each required value if it doesn't already exist.
    # IF NOT EXISTS makes this idempotent — safe to run multiple times.
    # PostgreSQL 9.1+ supports IF NOT EXISTS for ADD VALUE.
    for value in REQUIRED_ENUM_VALUES:
        op.execute(
            sa.text(f"ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS '{value}'")
        )

    print(f"transactiontype enum updated with {len(REQUIRED_ENUM_VALUES)} values")


def downgrade() -> None:
    """Cannot remove enum values from PostgreSQL (not supported by ALTER TYPE).

    Downgrade is a no-op. Old enum values are not used by the application
    (EARN_STREAK_BONUS, SPEND_REWARD, SPEND_CONTENT were replaced).
    Removing them would require DROP TYPE + recreate, which is destructive.
    """
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == 'postgresql':
        print(
            "WARNING: transactiontype enum values cannot be removed from PostgreSQL. "
            "Downgrade is a no-op. Old values (EARN_STREAK_BONUS, SPEND_REWARD, "
            "SPEND_CONTENT) remain in the enum but are unused."
        )
