"""add_kicked_tracking_to_vip_subscribers

Revision ID: da1247eed1e3
Revises: 0a20790932ed
Create Date: 2026-03-19 03:40:05.214961+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da1247eed1e3'
down_revision: Union[str, None] = '0a20790932ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agregar columna kicked_from_channel_at (compatible SQLite y PostgreSQL)
    op.add_column(
        'vip_subscribers',
        sa.Column('kicked_from_channel_at', sa.DateTime(), nullable=True)
    )
    # Agregar columna last_kick_notification_sent_at
    op.add_column(
        'vip_subscribers',
        sa.Column('last_kick_notification_sent_at', sa.DateTime(), nullable=True)
    )
    # Crear índice para búsquedas eficientes (Phase 27)
    op.create_index(
        'idx_vip_expired_not_kicked',
        'vip_subscribers',
        ['status', 'kicked_from_channel_at']
    )


def downgrade() -> None:
    # Eliminar índice
    op.drop_index('idx_vip_expired_not_kicked', table_name='vip_subscribers')
    # Eliminar columnas
    op.drop_column('vip_subscribers', 'last_kick_notification_sent_at')
    op.drop_column('vip_subscribers', 'kicked_from_channel_at')
