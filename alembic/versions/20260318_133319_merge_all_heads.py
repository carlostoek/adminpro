"""merge all heads

Revision ID: 0a20790932ed
Revises: 20260221_000001, 20260223_000002, 20260317_142234
Create Date: 2026-03-18 13:33:19.133165+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0a20790932ed'
down_revision: Union[str, None] = ('20260221_000001', '20260223_000002', '20260317_142234')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
