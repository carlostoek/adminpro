"""Seed gamification data (economy defaults, user profiles, rewards)

Revision ID: 20260221_000001
Revises: 20260211_000001
Create Date: 2026-02-21 00:00:01.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260221_000001'
down_revision: Union[str, None] = '20260211_000001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed initial gamification data."""

    # Update BotConfig with economy defaults
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

    # Backfill UserGamificationProfile for existing users
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

    # Seed default rewards (idempotent)
    op.execute("""
        INSERT OR IGNORE INTO rewards
        (name, description, reward_type, reward_value, is_repeatable, is_secret, claim_window_hours, is_active, sort_order, created_at, updated_at)
        VALUES
        ('Primeros Pasos', 'Da tu primera reacción al contenido', 'BESITOS', '{"amount": 10}', 0, 0, 168, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('Ahorrador Principiante', 'Acumula 100 besitos en tu cuenta', 'BADGE', '{"badge_name": "ahorrador", "emoji": "💰"}', 0, 0, 168, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('Racha de 7 Días', 'Mantén una racha de 7 días reclamando el regalo diario', 'BESITOS', '{"amount": 50}', 0, 0, 168, 1, 2, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """)


def downgrade() -> None:
    """Reset BotConfig economy fields (preserve user data)."""

    # Reset BotConfig economy fields to NULL
    # Do NOT delete rewards or user profiles (production safety)
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