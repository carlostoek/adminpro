"""create gamification schema - rewards, shop, content_sets

Revision ID: 20260223_000002
Revises: 20260211_000001
Create Date: 2026-02-23 02:00:00.000000+00:00

Note: This migration creates gamification tables and seeds initial data.
The original seed migration (20260221_000001) has been disabled due to
migration cycle issues on Railway deployment.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '20260223_000002'
down_revision: Union[str, None] = '20260211_000001'  # Direct child of 20260211_000001 (fix from 20260217)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the current database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def index_exists(table_name: str, index_name: str) -> bool:
    """Check if an index exists on a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = inspector.get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)


def upgrade() -> None:
    """
    Create gamification schema tables that were missing from previous migrations.

    Uses IF NOT EXISTS for idempotency - safe to run multiple times.

    This includes:
    - user_gamification_profiles: User balances, levels, stats
    - transactions: Audit trail for all besito movements
    - user_reactions: User reactions to content
    - user_streaks: Daily streak tracking
    - rewards: Reward/achievement definitions
    - reward_conditions: Conditions for unlocking rewards
    - user_rewards: User progress on rewards
    - content_sets: Content bundles for shop
    - shop_products: Shop items
    - user_content_access: User access to purchased content
    """

    # 1. user_gamification_profiles
    if not table_exists('user_gamification_profiles'):
        op.create_table('user_gamification_profiles',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('balance', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('total_earned', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('total_spent', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('level', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
    if not index_exists('user_gamification_profiles', 'idx_gamification_user_id'):
        op.create_index('idx_gamification_user_id', 'user_gamification_profiles', ['user_id'], unique=True)
    if not index_exists('user_gamification_profiles', 'idx_gamification_level_balance'):
        op.create_index('idx_gamification_level_balance', 'user_gamification_profiles', ['level', 'balance'])

    # 2. transactions
    if not table_exists('transactions'):
        op.create_table('transactions',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('amount', sa.Integer(), nullable=False),
            sa.Column('type', sa.Enum('EARN_DAILY', 'EARN_REACTION', 'EARN_REWARD', 'EARN_STREAK_BONUS', 'SPEND_SHOP', 'SPEND_REWARD', 'SPEND_CONTENT', name='transactiontype'), nullable=False),
            sa.Column('reason', sa.String(length=255), nullable=False),
            sa.Column('transaction_metadata', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
    if not index_exists('transactions', 'idx_transaction_user_created'):
        op.create_index('idx_transaction_user_created', 'transactions', ['user_id', 'created_at'])
    if not index_exists('transactions', 'idx_transaction_type_created'):
        op.create_index('idx_transaction_type_created', 'transactions', ['type', 'created_at'])
    if not index_exists('transactions', 'idx_transaction_user_type'):
        op.create_index('idx_transaction_user_type', 'transactions', ['user_id', 'type'])

    # 3. user_reactions
    if not table_exists('user_reactions'):
        op.create_table('user_reactions',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('content_id', sa.BigInteger(), nullable=False),
            sa.Column('channel_id', sa.String(length=50), nullable=False),
            sa.Column('emoji', sa.String(length=10), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
    if not index_exists('user_reactions', 'idx_user_content_emoji'):
        op.create_index('idx_user_content_emoji', 'user_reactions', ['user_id', 'content_id', 'emoji'], unique=True)
    if not index_exists('user_reactions', 'idx_user_reactions_recent'):
        op.create_index('idx_user_reactions_recent', 'user_reactions', ['user_id', 'created_at'])
    if not index_exists('user_reactions', 'idx_content_reactions'):
        op.create_index('idx_content_reactions', 'user_reactions', ['channel_id', 'content_id', 'emoji'])

    # 4. user_streaks
    if not table_exists('user_streaks'):
        op.create_table('user_streaks',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('streak_type', sa.Enum('DAILY_GIFT', 'REACTION', name='streaktype'), nullable=False),
            sa.Column('current_streak', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('longest_streak', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('last_claim_date', sa.DateTime(), nullable=True),
            sa.Column('last_reaction_date', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
    if not index_exists('user_streaks', 'idx_user_streak_type'):
        op.create_index('idx_user_streak_type', 'user_streaks', ['user_id', 'streak_type'], unique=True)
    if not index_exists('user_streaks', 'idx_streak_type_current'):
        op.create_index('idx_streak_type_current', 'user_streaks', ['streak_type', 'current_streak'])

    # 5. rewards
    if not table_exists('rewards'):
        op.create_table('rewards',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('description', sa.String(length=500), nullable=True),
            sa.Column('reward_type', sa.Enum('BESITOS', 'BADGE', 'CONTENT', 'VIP_EXTENSION', name='rewardtype'), nullable=False),
            sa.Column('reward_value', sa.JSON(), nullable=False),
            sa.Column('is_repeatable', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('is_secret', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('claim_window_hours', sa.Integer(), nullable=False, server_default='168'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
    if not index_exists('rewards', 'idx_rewards_active'):
        op.create_index('idx_rewards_active', 'rewards', ['is_active'])
    if not index_exists('rewards', 'idx_rewards_type'):
        op.create_index('idx_rewards_type', 'rewards', ['reward_type'])

    # 6. reward_conditions
    if not table_exists('reward_conditions'):
        op.create_table('reward_conditions',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('reward_id', sa.Integer(), nullable=False),
            sa.Column('condition_type', sa.Enum('STREAK_LENGTH', 'TOTAL_POINTS', 'LEVEL_REACHED', 'BESITOS_SPENT', 'FIRST_PURCHASE', 'FIRST_DAILY_GIFT', 'FIRST_REACTION', 'NOT_VIP', 'NOT_CLAIMED_BEFORE', name='rewardconditiontype'), nullable=False),
            sa.Column('condition_value', sa.Integer(), nullable=True),
            sa.Column('condition_group', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['reward_id'], ['rewards.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
    if not index_exists('reward_conditions', 'idx_reward_conditions_reward'):
        op.create_index('idx_reward_conditions_reward', 'reward_conditions', ['reward_id'])

    # 7. user_rewards
    if not table_exists('user_rewards'):
        op.create_table('user_rewards',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('reward_id', sa.Integer(), nullable=False),
            sa.Column('status', sa.Enum('LOCKED', 'UNLOCKED', 'CLAIMED', 'EXPIRED', name='rewardstatus'), nullable=False, server_default='LOCKED'),
            sa.Column('unlocked_at', sa.DateTime(), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
            sa.Column('claimed_at', sa.DateTime(), nullable=True),
            sa.Column('claim_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('last_claimed_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['reward_id'], ['rewards.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
    if not index_exists('user_rewards', 'idx_user_rewards_user'):
        op.create_index('idx_user_rewards_user', 'user_rewards', ['user_id'])
    if not index_exists('user_rewards', 'idx_user_rewards_reward'):
        op.create_index('idx_user_rewards_reward', 'user_rewards', ['reward_id'])
    if not index_exists('user_rewards', 'idx_user_rewards_status'):
        op.create_index('idx_user_rewards_status', 'user_rewards', ['status'])
    if not index_exists('user_rewards', 'idx_user_rewards_user_status'):
        op.create_index('idx_user_rewards_user_status', 'user_rewards', ['user_id', 'status'])

    # 8. content_sets
    if not table_exists('content_sets'):
        op.create_table('content_sets',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('description', sa.String(length=1000), nullable=True),
            sa.Column('file_ids', sa.JSON(), nullable=False),
            sa.Column('content_type', sa.Enum('PHOTO_SET', 'VIDEO', 'AUDIO', 'MIXED', name='contenttype'), nullable=False),
            sa.Column('tier', sa.Enum('FREE', 'VIP', 'PREMIUM', 'GIFT', name='contenttier'), nullable=False),
            sa.Column('category', sa.String(length=50), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
    if not index_exists('content_sets', 'idx_content_sets_active'):
        op.create_index('idx_content_sets_active', 'content_sets', ['is_active'])
    if not index_exists('content_sets', 'idx_content_sets_tier'):
        op.create_index('idx_content_sets_tier', 'content_sets', ['tier'])

    # 9. shop_products
    if not table_exists('shop_products'):
        op.create_table('shop_products',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('description', sa.String(length=1000), nullable=True),
            sa.Column('price', sa.Numeric(10, 2), nullable=False),
            sa.Column('currency', sa.String(length=10), nullable=False, server_default='$'),
            sa.Column('content_set_id', sa.Integer(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('purchase_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['content_set_id'], ['content_sets.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
    if not index_exists('shop_products', 'idx_shop_products_active'):
        op.create_index('idx_shop_products_active', 'shop_products', ['is_active'])
    if not index_exists('shop_products', 'idx_shop_products_content_set'):
        op.create_index('idx_shop_products_content_set', 'shop_products', ['content_set_id'])

    # 10. user_content_access
    if not table_exists('user_content_access'):
        op.create_table('user_content_access',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('content_set_id', sa.Integer(), nullable=True),
            sa.Column('shop_product_id', sa.Integer(), nullable=True),
            sa.Column('access_type', sa.String(length=50), nullable=False),
            sa.Column('besitos_paid', sa.Integer(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('accessed_at', sa.DateTime(), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
            sa.Column('access_metadata', sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['content_set_id'], ['content_sets.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['shop_product_id'], ['shop_products.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
    if not index_exists('user_content_access', 'idx_user_content_access_user'):
        op.create_index('idx_user_content_access_user', 'user_content_access', ['user_id'])
    if not index_exists('user_content_access', 'idx_user_content_access_content_set'):
        op.create_index('idx_user_content_access_content_set', 'user_content_access', ['content_set_id'])
    if not index_exists('user_content_access', 'idx_user_content_access_shop_product'):
        op.create_index('idx_user_content_access_shop_product', 'user_content_access', ['shop_product_id'])

    # ===== SEED DATA (after tables are created) =====
    # This was originally in 20260221_000001 but moved here to avoid cycle

    # 1. Update BotConfig with default economy values
    op.execute("""
        UPDATE bot_config
        SET
            level_formula = 'floor(sqrt(total_earned / 100)) + 1',
            besitos_per_reaction = 5,
            besitos_daily_gift = 50,
            besitos_daily_streak_bonus = 10,
            max_reactions_per_day = 20,
            besitos_daily_base = 20,
            besitos_streak_bonus_per_day = 2,
            besitos_streak_bonus_max = 50,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    """)

    # 2. Backfill UserGamificationProfile for all existing users
    op.execute("""
        INSERT INTO user_gamification_profiles
        (user_id, balance, total_earned, total_spent, level, created_at, updated_at)
        SELECT
            user_id,
            0 as balance,
            0 as total_earned,
            0 as total_spent,
            1 as level,
            CURRENT_TIMESTAMP as created_at,
            CURRENT_TIMESTAMP as updated_at
        FROM users
        WHERE user_id NOT IN (
            SELECT user_id FROM user_gamification_profiles
        )
        ON CONFLICT (user_id) DO NOTHING
    """)

    # 3. Seed default rewards
    op.execute("""
        INSERT INTO rewards
        (name, description, reward_type, reward_value, is_repeatable, is_secret, claim_window_hours, is_active, sort_order, created_at, updated_at)
        VALUES
        ('Primeros Pasos', 'Da tu primera reacción al contenido', 'BESITOS', '{"amount": 10}', 0, 0, 168, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('Ahorrador Principiante', 'Acumula 100 besitos en tu cuenta', 'BADGE', '{"badge_name": "ahorrador", "emoji": "💰"}', 0, 0, 168, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('Racha de 7 Días', 'Mantén una racha de 7 días reclamando el regalo diario', 'BESITOS', '{"amount": 50}', 0, 0, 168, 1, 2, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    """
    Drop gamification schema tables.

    Note: This will delete all user gamification data!
    """
    op.drop_table('user_content_access')
    op.drop_table('shop_products')
    op.drop_table('content_sets')
    op.drop_table('user_rewards')
    op.drop_table('reward_conditions')
    op.drop_table('rewards')
    op.drop_table('user_streaks')
    op.drop_table('user_reactions')
    op.drop_table('transactions')
    op.drop_table('user_gamification_profiles')
