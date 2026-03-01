"""add is_active to stories table

Revision ID: 28ff60290baa
Revises: 01879f3019f5
Create Date: 2026-03-01 10:26:02.259457+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28ff60290baa'
down_revision: Union[str, None] = '01879f3019f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_active column to stories table
    op.add_column('stories', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'))


def downgrade() -> None:
    # Remove is_active column from stories table
    op.drop_column('stories', 'is_active')
