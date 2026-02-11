"""allow_null_package_id_for_vip_subscription_interest

Revision ID: ef144ba8b77a
Revises: 29019dace4c7
Create Date: 2026-02-10 14:22:15.553777+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef144ba8b77a'
down_revision: Union[str, None] = '29019dace4c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite requires batch mode to alter columns (recreate table)
    with op.batch_alter_table('user_interests', recreate='always') as batch_op:
        batch_op.alter_column('package_id',
                   existing_type=sa.INTEGER(),
                   nullable=True)


def downgrade() -> None:
    # SQLite requires batch mode to alter columns (recreate table)
    with op.batch_alter_table('user_interests', recreate='always') as batch_op:
        batch_op.alter_column('package_id',
                   existing_type=sa.INTEGER(),
                   nullable=False)
