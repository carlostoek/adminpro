"""fix reaction unique constraint to one per user per content

Revision ID: 20260211_000001
Revises: f9c06e9cc285
Create Date: 2026-02-11 00:00:01.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260211_000001'
down_revision: Union[str, None] = 'f9c06e9cc285'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Deduplicate existing reactions - keep only the first reaction per user/content
    # (the one with the oldest created_at timestamp)

    # Get database connection
    conn = op.get_bind()

    # For SQLite, we need to use a different approach since it doesn't support
    # DELETE with subqueries that reference the same table directly

    # First, find all duplicates (user_id, content_id pairs with multiple reactions)
    # and identify which ones to keep (minimum id for each group)

    if conn.dialect.name == 'sqlite':
        # SQLite approach: Use a CTE to identify duplicates
        conn.execute(sa.text("""
            DELETE FROM user_reactions
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM user_reactions
                GROUP BY user_id, content_id
            )
        """))
    else:
        # PostgreSQL/MySQL approach
        conn.execute(sa.text("""
            DELETE FROM user_reactions
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM user_reactions
                GROUP BY user_id, content_id
            )
        """))

    # Drop the old unique index
    op.drop_index('idx_user_content_emoji', table_name='user_reactions')

    # Create the new unique index on (user_id, content_id) only
    op.create_index(
        'idx_user_content',
        'user_reactions',
        ['user_id', 'content_id'],
        unique=True
    )


def downgrade() -> None:
    # Drop the new unique index
    op.drop_index('idx_user_content', table_name='user_reactions')

    # Recreate the old unique index on (user_id, content_id, emoji)
    op.create_index(
        'idx_user_content_emoji',
        'user_reactions',
        ['user_id', 'content_id', 'emoji'],
        unique=True
    )

    # Note: Downgrade cannot restore deleted duplicate reactions
    # as we don't know which emojis were removed
