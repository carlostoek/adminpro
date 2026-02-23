"""merge duplicate heads

Revision ID: 8938058d20d3
Revises: ef144ba8b77a, 20260211_000001
Create Date: 2026-02-13 10:04:31.583311+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8938058d20d3'
down_revision: Union[str, None] = ('ef144ba8b77a', '20260211_000001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
