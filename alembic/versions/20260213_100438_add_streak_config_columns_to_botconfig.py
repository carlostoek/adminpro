"""add streak config columns to botconfig

Revision ID: 43b8b4e4a504
Revises: 8938058d20d3
Create Date: 2026-02-13 10:04:38.588528+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43b8b4e4a504'
down_revision: Union[str, None] = '8938058d20d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add streak configuration columns to bot_config table
    op.add_column('bot_config', sa.Column('besitos_daily_base', sa.Integer(), nullable=True))
    op.add_column('bot_config', sa.Column('besitos_streak_bonus_per_day', sa.Integer(), nullable=True))
    op.add_column('bot_config', sa.Column('besitos_streak_bonus_max', sa.Integer(), nullable=True))
    op.add_column('bot_config', sa.Column('streak_display_format', sa.String(length=50), nullable=True))

    # Set default values for existing rows
    op.execute("UPDATE bot_config SET besitos_daily_base = 20 WHERE besitos_daily_base IS NULL")
    op.execute("UPDATE bot_config SET besitos_streak_bonus_per_day = 2 WHERE besitos_streak_bonus_per_day IS NULL")
    op.execute("UPDATE bot_config SET besitos_streak_bonus_max = 50 WHERE besitos_streak_bonus_max IS NULL")
    op.execute("UPDATE bot_config SET streak_display_format = '🔥 {days} days' WHERE streak_display_format IS NULL")


def downgrade() -> None:
    op.drop_column('bot_config', 'streak_display_format')
    op.drop_column('bot_config', 'besitos_streak_bonus_max')
    op.drop_column('bot_config', 'besitos_streak_bonus_per_day')
    op.drop_column('bot_config', 'besitos_daily_base')
