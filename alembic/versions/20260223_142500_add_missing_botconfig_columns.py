"""Add missing botconfig columns if they don't exist

Revision ID: 20260223_142500
Revises: 20260223_000001
Create Date: 2026-02-23 14:25:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260223_142500'
down_revision: Union[str, None] = '20260223_000001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing economy and streak columns to bot_config table."""
    conn = op.get_bind()

    # Detect database dialect
    dialect = conn.dialect.name

    # List of columns to add with their definitions
    # Format: (column_name, column_type, default_value, nullable, needs_quotes)
    columns_to_add = [
        # Economy columns (from migration 3d9f8a2e1b5c)
        ('level_formula', 'VARCHAR(255)', 'floor(sqrt(total_earned / 100)) + 1', True, True),
        ('besitos_per_reaction', 'INTEGER', 5, True, False),
        ('besitos_daily_gift', 'INTEGER', 50, True, False),
        ('besitos_daily_streak_bonus', 'INTEGER', 10, True, False),
        ('max_reactions_per_day', 'INTEGER', 20, True, False),

        # Streak columns (from migration 43b8b4e4a504)
        ('besitos_daily_base', 'INTEGER', 20, True, False),
        ('besitos_streak_bonus_per_day', 'INTEGER', 2, True, False),
        ('besitos_streak_bonus_max', 'INTEGER', 50, True, False),
        ('streak_display_format', 'VARCHAR(50)', '🔥 {days} days', True, True),
    ]

    if dialect == 'postgresql':
        # PostgreSQL: Use information_schema to check if column exists
        for column_name, column_type, default_value, nullable, needs_quotes in columns_to_add:
            # Check if column exists
            check_sql = f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'bot_config'
                AND column_name = '{column_name}'
            """
            result = conn.execute(sa.text(check_sql)).fetchone()

            if not result:
                print(f"Adding column {column_name} to bot_config table")

                # Add column (nullable first, we'll set defaults after)
                nullable_clause = '' if nullable else 'NOT NULL'
                quoted_default = f"'{default_value}'" if needs_quotes else str(default_value)
                add_sql = f"""
                    ALTER TABLE bot_config
                    ADD COLUMN {column_name} {column_type} {nullable_clause}
                """
                conn.execute(sa.text(add_sql))

                # Set default value for existing rows
                update_sql = f"""
                    UPDATE bot_config
                    SET {column_name} = {quoted_default}
                    WHERE {column_name} IS NULL
                """
                conn.execute(sa.text(update_sql))

                # Add default constraint for future rows
                # PostgreSQL doesn't allow ADD COLUMN with DEFAULT to set existing rows
                # So we set the default constraint separately
                alter_default_sql = f"""
                    ALTER TABLE bot_config
                    ALTER COLUMN {column_name} SET DEFAULT {quoted_default}
                """
                conn.execute(sa.text(alter_default_sql))

                print(f"  - Added column {column_name} with default value {default_value}")
            else:
                print(f"Column {column_name} already exists in bot_config table")

    elif dialect == 'sqlite':
        # SQLite: Check with PRAGMA table_info
        # SQLite has limited ALTER TABLE support, but we can handle it
        # Since this is primarily for production (PostgreSQL), SQLite support is secondary
        print(f"SQLite detected. Skipping column checks as columns should already exist.")

    else:
        raise ValueError(f"Unsupported dialect: {dialect}")


def downgrade() -> None:
    """Remove the columns we added (optional, for rollback)."""
    conn = op.get_bind()
    dialect = conn.dialect.name

    # Columns to remove (in reverse order of addition)
    columns_to_remove = [
        'streak_display_format',
        'besitos_streak_bonus_max',
        'besitos_streak_bonus_per_day',
        'besitos_daily_base',
        'max_reactions_per_day',
        'besitos_daily_streak_bonus',
        'besitos_daily_gift',
        'besitos_per_reaction',
        'level_formula',
    ]

    if dialect == 'postgresql':
        for column_name in columns_to_remove:
            # Check if column exists before trying to drop
            check_sql = f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'bot_config'
                AND column_name = '{column_name}'
            """
            result = conn.execute(sa.text(check_sql)).fetchone()

            if result:
                # First, drop any default constraint
                # PostgreSQL doesn't require explicit drop of default when dropping column
                # So we just drop the column
                drop_sql = f"ALTER TABLE bot_config DROP COLUMN {column_name}"
                print(f"Dropping column {column_name} from bot_config table")
                conn.execute(sa.text(drop_sql))

    elif dialect == 'sqlite':
        # SQLite has limited ALTER TABLE support (can't drop columns easily)
        print(f"SQLite detected. Skipping column removal (SQLite has limited ALTER TABLE support).")
    else:
        raise ValueError(f"Unsupported dialect: {dialect}")