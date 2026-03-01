"""merge heads

Revision ID: 01879f3019f5
Revises: 20260221_000001, 20260223_142500
Create Date: 2026-03-01 10:23:43.558858+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01879f3019f5'
down_revision: Union[str, None] = ('20260221_000001', '20260223_142500')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
