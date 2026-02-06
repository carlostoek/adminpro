"""seed_initial_content_packages

Revision ID: 1f340519f489
Revises: 29019dace4c7
Create Date: 2026-02-06 04:59:36.916919+00:00

"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f340519f489'
down_revision: Union[str, None] = '29019dace4c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Define the table structure for bulk_insert
content_packages_table = sa.table(
    'content_packages',
    sa.column('id', sa.Integer),
    sa.column('name', sa.String(200)),
    sa.column('description', sa.String(500)),
    sa.column('price', sa.Numeric(10, 2)),
    sa.column('category', sa.String(20)),
    sa.column('type', sa.String(20)),
    sa.column('media_url', sa.String(500)),
    sa.column('is_active', sa.Boolean),
    sa.column('created_at', sa.DateTime),
    sa.column('updated_at', sa.DateTime),
)


def upgrade() -> None:
    """Insert the 5 initial content packages."""
    now = datetime.utcnow()

    packages = [
        {
            'name': '♥ Encanto Inicial 💫',
            'description': '1 video + 10 fotos - Introducción coqueta al mundo de Diana',
            'price': 10.00,
            'category': 'VIP_CONTENT',
            'type': 'BUNDLE',
            'media_url': None,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        {
            'name': '🔴 Sensualidad Revelada 🔥',
            'description': '2 videos + 10 fotos - El lado más atrevido de Diana',
            'price': 14.00,
            'category': 'VIP_CONTENT',
            'type': 'BUNDLE',
            'media_url': None,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        {
            'name': '❤‍🔥 Pasión Desbordante 💋',
            'description': '3 videos + 15 fotos - Una experiencia íntima única',
            'price': 17.00,
            'category': 'VIP_CONTENT',
            'type': 'BUNDLE',
            'media_url': None,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        {
            'name': '❤️ Intimidad Explosiva 🔞',
            'description': '5 videos + 15 fotos - Contenido explícito sin censura',
            'price': 20.00,
            'category': 'VIP_PREMIUM',
            'type': 'BUNDLE',
            'media_url': None,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        {
            'name': '💎 El Diván de Diana 💎',
            'description': 'Canal VIP - Más de 3,000 archivos, contenido sin censura, acceso preferente a Premium, descuento VIP en personalizado, historias privadas',
            'price': 23.00,
            'category': 'VIP_PREMIUM',
            'type': 'COLLECTION',
            'media_url': None,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
    ]

    op.bulk_insert(content_packages_table, packages)


def downgrade() -> None:
    """Remove the 5 initial content packages by name."""
    package_names = [
        '♥ Encanto Inicial 💫',
        '🔴 Sensualidad Revelada 🔥',
        '❤‍🔥 Pasión Desbordante 💋',
        '❤️ Intimidad Explosiva 🔞',
        '💎 El Diván de Diana 💎',
    ]

    for name in package_names:
        op.execute(
            sa.text("DELETE FROM content_packages WHERE name = :name"),
            {'name': name}
        )
