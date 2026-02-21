"""seed gamification data for initial deployment

Revision ID: 20260221_000001
Revises: 20260217_000001
Create Date: 2026-02-21 00:00:01.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260221_000001'
down_revision: Union[str, None] = '20260217_000001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Seed default gamification data for initial deployment.

    This is a DATA migration (not schema) that populates the database with:
    1. Default economy configuration in BotConfig (singleton id=1)
    2. UserGamificationProfile records for all existing users
    3. Default rewards (achievements) for the gamification system

    Idempotent Design:
    - Uses UPDATE...WHERE id=1 for BotConfig (safe to run multiple times)
    - Uses INSERT OR IGNORE for SQLite to prevent duplicate errors
    - Uses INSERT...SELECT...WHERE NOT EXISTS for user backfill
    - Can be safely re-run without creating duplicates

    Default Economy Values:
    - level_formula: floor(sqrt(total_earned / 100)) + 1
    - besitos_per_reaction: 5
    - besitos_daily_gift: 50 (base 20 + streak bonus logic)
    - besitos_daily_streak_bonus: 10
    - max_reactions_per_day: 20
    - besitos_daily_base: 20
    - besitos_streak_bonus_per_day: 2
    - besitos_streak_bonus_max: 50

    Default Rewards:
    1. Primeros Pasos - First reaction reward (10 besitos)
    2. Ahorrador Principiante - Save 100 besitos badge
    3. Racha de 7 Dias - 7-day streak reward (50 besitos)
    """

    # 1. Update BotConfig with default economy values
    # Using UPDATE instead of INSERT because BotConfig is a singleton (id=1)
    # and should already exist from initial schema migration
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
    # Creates a profile with default values (balance=0, level=1) for any user
    # that doesn't already have a gamification profile
    # INSERT OR IGNORE prevents errors if profiles already exist
    op.execute("""
        INSERT OR IGNORE INTO user_gamification_profiles
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
    """)

    # 3. Seed default rewards (idempotent with INSERT OR IGNORE)
    # These are the initial achievements available in the system
    # reward_value is stored as JSON with type-specific structure:
    # - BESITOS: {"amount": N}
    # - BADGE: {"badge_name": "...", "emoji": "..."}
    # - CONTENT: {"content_set_id": N}
    # - VIP_EXTENSION: {"days": N}
    op.execute("""
        INSERT OR IGNORE INTO rewards
        (name, description, reward_type, reward_value, is_repeatable, is_secret, claim_window_hours, is_active, sort_order, created_at, updated_at)
        VALUES
        ('Primeros Pasos', 'Da tu primera reacción al contenido', 'BESITOS', '{"amount": 10}', 0, 0, 168, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('Ahorrador Principiante', 'Acumula 100 besitos en tu cuenta', 'BADGE', '{"badge_name": "ahorrador", "emoji": "💰"}', 0, 0, 168, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('Racha de 7 Días', 'Mantén una racha de 7 días reclamando el regalo diario', 'BESITOS', '{"amount": 50}', 0, 0, 168, 1, 2, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """)


def downgrade() -> None:
    """
    Revert gamification configuration to null state.

    Safety Note:
    - This ONLY resets BotConfig economy fields to NULL
    - User gamification profiles are PRESERVED (production safety)
    - Rewards are NOT deleted (to avoid losing user achievement history)
    - User data integrity is prioritized over clean downgrade

    Downgrade Behavior:
    - Sets all economy configuration fields to NULL in BotConfig
    - Preserves user balances, levels, and transaction history
    - Preserves reward definitions and user achievements
    """

    # Reset BotConfig economy fields to NULL
    # This effectively disables the gamification economy until
    # the migration is re-applied or values are set manually
    op.execute("""
        UPDATE bot_config
        SET
            level_formula = NULL,
            besitos_per_reaction = NULL,
            besitos_daily_gift = NULL,
            besitos_daily_streak_bonus = NULL,
            max_reactions_per_day = NULL,
            besitos_daily_base = NULL,
            besitos_streak_bonus_per_day = NULL,
            besitos_streak_bonus_max = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    """)

    # Note: We intentionally do NOT delete from user_gamification_profiles
    # or rewards tables to preserve user data and achievement history
