"""fix reaction unique constraint to include emoji

Revision ID: 20260217_000001
Revises: 29019dace4c7
Create Date: 2026-02-17 00:00:01.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260211_000001'
down_revision: Union[str, None] = '29019dace4c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Change unique constraint from (user_id, content_id) to (user_id, content_id, emoji).

    This allows users to react with multiple different emojis to the same content,
    while preventing duplicate reactions with the same emoji.
    """
    # Check if the table exists first (for fresh deployments without user_reactions yet)
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'user_reactions' not in inspector.get_table_names():
        # Table doesn't exist yet, nothing to do
        return

    indexes = [idx['name'] for idx in inspector.get_indexes('user_reactions')]

    # Drop the old unique index (without emoji) only if it exists
    if 'idx_user_content' in indexes:
        op.drop_index('idx_user_content', table_name='user_reactions')

    # Create the new unique index with emoji included only if it doesn't exist
    if 'idx_user_content_emoji' not in indexes:
        op.create_index(
            'idx_user_content_emoji',
            'user_reactions',
            ['user_id', 'content_id', 'emoji'],
            unique=True
        )


def downgrade() -> None:
    """
    Revert to unique constraint without emoji.

    Note: If there are existing reactions with multiple emojis per user/content,
    this will fail until duplicates are removed.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'user_reactions' not in inspector.get_table_names():
        # Table doesn't exist yet, nothing to do
        return

    indexes = [idx['name'] for idx in inspector.get_indexes('user_reactions')]

    # Drop the new unique index (with emoji) only if it exists
    if 'idx_user_content_emoji' in indexes:
        op.drop_index('idx_user_content_emoji', table_name='user_reactions')

    # Recreate the old unique index without emoji only if it doesn't exist
    if 'idx_user_content' not in indexes:
        op.create_index(
            'idx_user_content',
            'user_reactions',
            ['user_id', 'content_id'],
            unique=True
        )
