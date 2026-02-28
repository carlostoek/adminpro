"""Fix reaction constraint to allow only one reaction per content

Revision ID: 20260227_233000
Revises: 20260223_142500
Create Date: 2026-02-27 23:30:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260227_233000'
down_revision: Union[str, None] = '20260223_142500'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Change unique constraint from (user_id, content_id, emoji) to (user_id, content_id).

    This ensures a user can only react ONCE to each content (with any emoji).
    
    Steps:
    1. First remove duplicate reactions, keeping only the oldest one per user/content
    2. Drop the old unique index (with emoji)
    3. Create new unique index without emoji
    """
    conn = op.get_bind()
    
    # Step 1: Remove duplicates - keep only the first reaction per user/content
    # This handles the case where users reacted with multiple emojis
    op.execute("""
        DELETE FROM user_reactions
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY user_id, content_id 
                           ORDER BY created_at ASC
                       ) as row_num
                FROM user_reactions
            ) ranked
            WHERE row_num > 1
        )
    """)
    
    # Step 2: Drop the old unique index (with emoji)
    op.drop_index('idx_user_content_emoji', table_name='user_reactions')
    
    # Step 3: Create the new unique index without emoji
    op.create_index(
        'idx_user_content',
        'user_reactions',
        ['user_id', 'content_id'],
        unique=True
    )


def downgrade() -> None:
    """
    Revert to unique constraint with emoji.

    This allows users to react with multiple different emojis to the same content.
    """
    # Drop the new unique index (without emoji)
    op.drop_index('idx_user_content', table_name='user_reactions')
    
    # Recreate the old unique index with emoji
    op.create_index(
        'idx_user_content_emoji',
        'user_reactions',
        ['user_id', 'content_id', 'emoji'],
        unique=True
    )
