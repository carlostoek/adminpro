"""Add pending_request column to free_channel_requests

Revision ID: 20260317_142234
Revises: 20260227_233000
Create Date: 2026-03-17 14:22:34.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '20260317_142234'
down_revision: Union[str, None] = '20260227_233000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add pending_request column to free_channel_requests table.

    This column supports the unique constraint for one pending request per user.
    """
    conn = op.get_bind()
    dialect = conn.dialect.name

    # Check if column already exists (database-specific)
    if dialect == 'sqlite':
        result = conn.execute(text("""
            SELECT COUNT(*) FROM pragma_table_info('free_channel_requests')
            WHERE name = 'pending_request'
        """))
        column_exists = result.scalar() > 0
    else:  # postgresql and others
        result = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_name = 'free_channel_requests'
            AND column_name = 'pending_request'
        """))
        column_exists = result.scalar() > 0

    if not column_exists:
        # Add column using batch_alter_table (SQLite compatible)
        with op.batch_alter_table('free_channel_requests') as batch_op:
            batch_op.add_column(
                sa.Column('pending_request', sa.Boolean(), nullable=True, default=True)
            )

        # Update existing rows (SQLite uses 1/0, PostgreSQL uses true/false)
        if dialect == 'sqlite':
            op.execute(text("""
                UPDATE free_channel_requests
                SET pending_request = CASE
                    WHEN processed = 1 THEN 0
                    ELSE 1
                END
            """))
        else:
            op.execute(text("""
                UPDATE free_channel_requests
                SET pending_request = CASE
                    WHEN processed = true THEN false
                    ELSE true
                END
            """))

        # Set NOT NULL with default
        with op.batch_alter_table('free_channel_requests') as batch_op:
            batch_op.alter_column(
                'pending_request',
                existing_type=sa.Boolean(),
                nullable=False,
                server_default='1' if dialect == 'sqlite' else 'true'
            )

        # Create index for constraint support
        op.create_index('idx_pending_request', 'free_channel_requests', ['pending_request'])

        print("✅ Column 'pending_request' added successfully")
    else:
        print("ℹ️ Column 'pending_request' already exists, skipping")


def downgrade() -> None:
    """Remove pending_request column."""
    conn = op.get_bind()
    dialect = conn.dialect.name

    # Check if column exists before dropping (database-specific)
    if dialect == 'sqlite':
        result = conn.execute(text("""
            SELECT COUNT(*) FROM pragma_table_info('free_channel_requests')
            WHERE name = 'pending_request'
        """))
        column_exists = result.scalar() > 0
    else:  # postgresql and others
        result = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_name = 'free_channel_requests'
            AND column_name = 'pending_request'
        """))
        column_exists = result.scalar() > 0

    if column_exists:
        op.drop_index('idx_pending_request', table_name='free_channel_requests')

        with op.batch_alter_table('free_channel_requests') as batch_op:
            batch_op.drop_column('pending_request')

        print("✅ Column 'pending_request' removed successfully")
    else:
        print("ℹ️ Column 'pending_request' does not exist, skipping")
