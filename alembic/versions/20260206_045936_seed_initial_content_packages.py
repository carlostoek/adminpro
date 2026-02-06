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


def upgrade() -> None:
    """Insert the 5 initial content packages using raw SQL for PostgreSQL enum compatibility."""
    now = datetime.utcnow()

    # Use raw SQL with explicit casting for PostgreSQL enum types
    packages = [
        {
            'name': '♥ Encanto Inicial 💫',
            'description': '1 video + 10 fotos - Introducción coqueta al mundo de Diana',
            'price': 10.00,
            'category': 'VIP_CONTENT',
            'type': 'BUNDLE',
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
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
    ]

    # Get database dialect to handle different databases
    bind = op.get_bind()
    dialect = bind.dialect.name

    for pkg in packages:
        if dialect == 'postgresql':
            # PostgreSQL requires explicit casting to enum types
            op.execute(
                sa.text("""
                    INSERT INTO content_packages
                    (name, description, price, category, type, media_url, is_active, created_at, updated_at)
                    VALUES
                    (:name, :description, :price, :category::contentcategory, :type::packagetype, NULL, :is_active, :created_at, :updated_at)
                """),
                pkg
            )
        else:
            # SQLite and other databases don't have enum types
            op.execute(
                sa.text("""
                    INSERT INTO content_packages
                    (name, description, price, category, type, media_url, is_active, created_at, updated_at)
                    VALUES
                    (:name, :description, :price, :category, :type, NULL, :is_active, :created_at, :updated_at)
                """),
                pkg
            )


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
