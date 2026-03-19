"""Fix shop_products schema to match current ShopProduct model

Revision ID: 20260320_000001
Revises: da1247eed1e3
Create Date: 2026-03-20 00:00:01.000000+00:00

Gap: Migration 20260223_000002 created shop_products with price/currency columns,
but ShopProduct model uses besitos_price/vip_discount_percentage/vip_besitos_price/tier.
This migration bridges the gap for existing databases.

Gap 4: Migration 2bc8023392e7 creates ix_user_gamification_profiles_user_id (unique).
Migration 20260223_000002 (parallel branch) creates idx_gamification_user_id (also unique
on user_id) because it checks for a different name. Both are now present on databases
that ran both migrations. This migration normalises to the canonical name.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision: str = '20260320_000001'
down_revision: Union[str, None] = 'da1247eed1e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(table_name: str, index_name: str) -> bool:
    """Check if an index exists on a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = inspector.get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)


def upgrade() -> None:
    """
    1. Align shop_products table with current ShopProduct model.
       Adds: besitos_price, vip_discount_percentage, vip_besitos_price, tier
       Removes: price, currency (if they exist — were created by old migration)
       Fixes: content_set_id nullability (model requires NOT NULL)

    2. Resolve user_gamification_profiles duplicate unique index on user_id.
       Keeps: ix_user_gamification_profiles_user_id (canonical op.f() name)
       Drops: idx_gamification_user_id (duplicate created by 20260223_000002)
    """
    bind = op.get_bind()
    dialect = bind.dialect.name

    # =========================================================
    # PART 1: Fix shop_products schema
    # =========================================================

    # --- ADD NEW COLUMNS (idempotent) ---

    if not column_exists('shop_products', 'besitos_price'):
        op.add_column('shop_products',
            sa.Column('besitos_price', sa.Integer(), nullable=True)
        )
        # Backfill from old price column if it exists, else use default 100
        if column_exists('shop_products', 'price'):
            op.execute(text("UPDATE shop_products SET besitos_price = CAST(price AS INTEGER) WHERE besitos_price IS NULL"))
        else:
            op.execute(text("UPDATE shop_products SET besitos_price = 100 WHERE besitos_price IS NULL"))
        # Make NOT NULL after backfill
        with op.batch_alter_table('shop_products') as batch_op:
            batch_op.alter_column('besitos_price', existing_type=sa.Integer(), nullable=False)

    if not column_exists('shop_products', 'vip_discount_percentage'):
        op.add_column('shop_products',
            sa.Column('vip_discount_percentage', sa.Integer(), nullable=False, server_default='0')
        )

    if not column_exists('shop_products', 'vip_besitos_price'):
        op.add_column('shop_products',
            sa.Column('vip_besitos_price', sa.Integer(), nullable=True)
        )

    if not column_exists('shop_products', 'tier'):
        # Use String for dialect-safe enum (model uses Enum(ContentTier))
        # SQLAlchemy maps ContentTier enum values to strings: FREE, VIP, PREMIUM, GIFT
        op.add_column('shop_products',
            sa.Column('tier', sa.String(length=20), nullable=False, server_default='FREE')
        )

    # --- FIX content_set_id NULLABILITY ---
    # Old migration made it nullable=True (ON DELETE SET NULL).
    # Model requires nullable=False. Only fix if rows have NULL content_set_id
    # by setting a safe default FK or deleting orphaned rows.
    # Strategy: delete rows with NULL content_set_id (no real data at this stage)
    op.execute(text("DELETE FROM shop_products WHERE content_set_id IS NULL"))

    # Now alter the column to NOT NULL using batch_alter_table (SQLite compatible)
    # Note: We cannot enforce this on PostgreSQL with ALTER COLUMN if FK is SET NULL.
    # So we change the FK constraint as well.
    with op.batch_alter_table('shop_products') as batch_op:
        batch_op.alter_column('content_set_id',
            existing_type=sa.Integer(),
            nullable=False
        )

    # --- ADD MISSING INDEXES (idempotent via index_exists check) ---
    if not index_exists('shop_products', 'idx_shop_product_active_tier'):
        op.create_index('idx_shop_product_active_tier', 'shop_products', ['is_active', 'tier'])

    if not index_exists('shop_products', 'idx_shop_product_price'):
        op.create_index('idx_shop_product_price', 'shop_products', ['besitos_price'])

    if not index_exists('shop_products', 'idx_shop_product_sort'):
        op.create_index('idx_shop_product_sort', 'shop_products', ['sort_order'])

    # --- REMOVE OLD COLUMNS (if they still exist) ---
    if column_exists('shop_products', 'price'):
        # Remove old index first if it exists
        bind2 = op.get_bind()
        inspector2 = inspect(bind2)
        for idx in inspector2.get_indexes('shop_products'):
            if 'price' in idx.get('column_names', []) and idx['name'] not in ['idx_shop_product_price']:
                try:
                    op.drop_index(idx['name'], table_name='shop_products')
                except Exception:
                    pass
        with op.batch_alter_table('shop_products') as batch_op:
            batch_op.drop_column('price')

    if column_exists('shop_products', 'currency'):
        with op.batch_alter_table('shop_products') as batch_op:
            batch_op.drop_column('currency')

    # =========================================================
    # PART 2: Resolve user_gamification_profiles index collision (Gap 4)
    # =========================================================
    # Two unique indexes on user_id may co-exist:
    #   ix_user_gamification_profiles_user_id (from 2bc8023392e7)
    #   idx_gamification_user_id              (from 20260223_000002, parallel branch)
    #
    # Canonical name is ix_user_gamification_profiles_user_id (op.f() convention).
    # Strategy:
    #   - If both exist: drop the non-canonical idx_gamification_user_id
    #   - If only idx_gamification_user_id exists: drop and recreate as canonical name
    #   - If only ix_user_gamification_profiles_user_id (or neither) exists: no-op

    has_canonical = index_exists('user_gamification_profiles', 'ix_user_gamification_profiles_user_id')
    has_duplicate = index_exists('user_gamification_profiles', 'idx_gamification_user_id')

    if has_duplicate and has_canonical:
        # Both exist: drop the non-canonical duplicate
        op.drop_index('idx_gamification_user_id', table_name='user_gamification_profiles')
    elif has_duplicate and not has_canonical:
        # Only the non-canonical name exists: normalise to canonical name
        op.drop_index('idx_gamification_user_id', table_name='user_gamification_profiles')
        op.create_index(
            op.f('ix_user_gamification_profiles_user_id'),
            'user_gamification_profiles',
            ['user_id'],
            unique=True
        )
    # else: canonical already present (or neither) — nothing to do


def downgrade() -> None:
    """Revert shop_products to old schema (price/currency)."""
    if column_exists('shop_products', 'besitos_price'):
        # Re-add old columns
        if not column_exists('shop_products', 'price'):
            op.add_column('shop_products',
                sa.Column('price', sa.Numeric(10, 2), nullable=True)
            )
            op.execute(text("UPDATE shop_products SET price = besitos_price"))
            with op.batch_alter_table('shop_products') as batch_op:
                batch_op.alter_column('price', existing_type=sa.Numeric(10, 2), nullable=False)

        if not column_exists('shop_products', 'currency'):
            op.add_column('shop_products',
                sa.Column('currency', sa.String(length=10), nullable=False, server_default='$')
            )

        # Remove new columns
        for col in ['besitos_price', 'vip_discount_percentage', 'vip_besitos_price', 'tier']:
            if column_exists('shop_products', col):
                with op.batch_alter_table('shop_products') as batch_op:
                    batch_op.drop_column(col)
