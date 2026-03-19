"""Add pending_request column to free_channel_requests

Revision ID: 20260317_142234
Revises: 20260227_233000
Create Date: 2026-03-17 14:22:34.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision: str = '20260317_142234'
down_revision: Union[str, None] = '20260227_233000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in the given table (dialect-aware)."""
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == 'sqlite':
        result = conn.execute(text("""
            SELECT COUNT(*) FROM pragma_table_info(:table)
            WHERE name = :column
        """), {"table": table_name, "column": column_name})
    else:  # postgresql and others
        result = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_name = :table
            AND column_name = :column
        """), {"table": table_name, "column": column_name})

    return result.scalar() > 0


def upgrade() -> None:
    """
    Add pending_request column to free_channel_requests table.

    This column supports the unique constraint for one pending request per user.
    """
    # --- COLUMN: add if not present ---
    if not column_exists('free_channel_requests', 'pending_request'):
        op.add_column(
            'free_channel_requests',
            sa.Column('pending_request', sa.Boolean(), nullable=True)
        )
        # Backfill existing rows: pending_request = False
        op.execute(sa.text(
            "UPDATE free_channel_requests SET pending_request = 0 WHERE pending_request IS NULL"
        ))
        # Make NOT NULL after backfill
        with op.batch_alter_table('free_channel_requests') as batch_op:
            batch_op.alter_column('pending_request', existing_type=sa.Boolean(), nullable=False)

        print("✅ Column 'pending_request' added successfully")
    else:
        print("ℹ️ Column 'pending_request' already exists, skipping")

    # --- INDEXES: created independently of column existence ---
    # This section runs regardless of whether the column was just added or already existed.
    # Use index existence guards so the migration stays idempotent.
    bind = op.get_bind()
    inspector = inspect(op.get_bind())
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('free_channel_requests')]
    dialect = bind.dialect.name

    if 'uq_user_pending_request' not in existing_indexes:
        # Create partial unique index (only one pending request per user)
        # This enforces the C-002 race condition protection at DB level
        if dialect == 'postgresql':
            # PostgreSQL: true partial index with WHERE clause
            op.create_index(
                'uq_user_pending_request',
                'free_channel_requests',
                ['user_id'],
                unique=True,
                postgresql_where=sa.text('pending_request = true')
            )
        else:
            # SQLite: partial index with sqlite_where
            op.create_index(
                'uq_user_pending_request',
                'free_channel_requests',
                ['user_id'],
                unique=True,
                sqlite_where=sa.text('pending_request = 1')
            )

    if 'idx_pending_request' not in existing_indexes:
        # Plain index on pending_request for query performance
        op.create_index('idx_pending_request', 'free_channel_requests', ['pending_request'])


def downgrade() -> None:
    """Remove pending_request column."""
    # Drop both indexes
    try:
        op.drop_index('uq_user_pending_request', table_name='free_channel_requests')
    except Exception:
        pass
    try:
        op.drop_index('idx_pending_request', table_name='free_channel_requests')
    except Exception:
        pass

    conn = op.get_bind()

    if column_exists('free_channel_requests', 'pending_request'):
        with op.batch_alter_table('free_channel_requests') as batch_op:
            batch_op.drop_column('pending_request')

        print("✅ Column 'pending_request' removed successfully")
    else:
        print("ℹ️ Column 'pending_request' does not exist, skipping")
