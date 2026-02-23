"""merge heads

Revision ID: 20260223_000001
Revises: 3d9f8a2e1b5c, 43b8b4e4a504
Create Date: 2026-02-23 00:00:01.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260223_000001'
down_revision: Union[str, None] = ('3d9f8a2e1b5c', '43b8b4e4a504')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass