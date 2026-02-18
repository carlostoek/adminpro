"""fix reaction unique constraint to include emoji

Revision ID: 20260217_000001
Revises: 43b8b4e4a504
Create Date: 2026-02-17 00:00:01.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260217_000001'
down_revision: Union[str, None] = '43b8b4e4a504'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Change unique constraint from (user_id, content_id) to (user_id, content_id, emoji).

    This allows users to react with multiple different emojis to the same content,
    while preventing duplicate reactions with the same emoji.
    """
    # Drop the old unique index (without emoji)
    op.drop_index('idx_user_content', table_name='user_reactions')

    # Create the new unique index with emoji included
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
    # Drop the new unique index (with emoji)
    op.drop_index('idx_user_content_emoji', table_name='user_reactions')

    # Recreate the old unique index without emoji
    op.create_index(
        'idx_user_content',
        'user_reactions',
        ['user_id', 'content_id'],
        unique=True
    )
