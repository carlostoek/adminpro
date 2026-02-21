"""Default rewards seeder for the gamification system."""
import logging
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.database.models import Reward, RewardCondition
from bot.database.enums import RewardType, RewardConditionType

logger = logging.getLogger(__name__)

# Default rewards configuration
DEFAULT_REWARDS: List[Dict[str, Any]] = [
    {
        "name": "Primeros Pasos",
        "description": "Da tu primera reacción al contenido",
        "reward_type": RewardType.BESITOS,
        "reward_value": {"amount": 10},
        "is_repeatable": False,
        "is_secret": False,
        "claim_window_hours": 168,  # 7 days
        "sort_order": 0,
        "conditions": [
            {"condition_type": RewardConditionType.FIRST_REACTION}
        ]
    },
    {
        "name": "Ahorrador Principiante",
        "description": "Acumula 100 besitos en tu cuenta",
        "reward_type": RewardType.BADGE,
        "reward_value": {"badge_name": "ahorrador", "emoji": "💰"},
        "is_repeatable": False,
        "is_secret": False,
        "claim_window_hours": 168,
        "sort_order": 1,
        "conditions": [
            {"condition_type": RewardConditionType.TOTAL_POINTS, "condition_value": 100}
        ]
    },
    {
        "name": "Racha de 7 Días",
        "description": "Mantén una racha de 7 días reclamando el regalo diario",
        "reward_type": RewardType.BESITOS,
        "reward_value": {"amount": 50},
        "is_repeatable": False,
        "is_secret": False,
        "claim_window_hours": 168,
        "sort_order": 2,
        "conditions": [
            {"condition_type": RewardConditionType.STREAK_LENGTH, "condition_value": 7}
        ]
    }
]


async def seed_default_rewards(session: AsyncSession) -> None:
    """
    Seed default rewards if they don't exist.

    This function is idempotent - running it multiple times will not
    create duplicate rewards. It checks for existing rewards by name.

    Args:
        session: Async database session

    Returns:
        None
    """
    logger.info("Starting default rewards seeding...")
    created_count = 0
    skipped_count = 0

    for reward_data in DEFAULT_REWARDS:
        # Check if reward exists by name
        result = await session.execute(
            select(Reward).where(Reward.name == reward_data["name"])
        )
        existing_reward = result.scalar_one_or_none()

        if existing_reward:
            logger.debug(f"Reward '{reward_data['name']}' already exists, skipping")
            skipped_count += 1
            continue

        # Extract conditions before creating reward
        conditions_data = reward_data.pop("conditions", [])

        # Create reward
        reward = Reward(
            name=reward_data["name"],
            description=reward_data["description"],
            reward_type=reward_data["reward_type"],
            reward_value=reward_data["reward_value"],
            is_repeatable=reward_data["is_repeatable"],
            is_secret=reward_data["is_secret"],
            claim_window_hours=reward_data["claim_window_hours"],
            is_active=True,
            sort_order=reward_data["sort_order"]
        )
        session.add(reward)
        await session.flush()  # Get reward.id

        # Create conditions for this reward
        for cond_data in conditions_data:
            condition = RewardCondition(
                reward_id=reward.id,
                condition_type=cond_data["condition_type"],
                condition_value=cond_data.get("condition_value"),
                condition_group=cond_data.get("condition_group", 0),
                sort_order=cond_data.get("sort_order", 0)
            )
            session.add(condition)

        logger.info(f"Created reward: {reward_data['name']} (ID: {reward.id})")
        created_count += 1

    await session.commit()
    logger.info(
        f"Rewards seeding complete. Created: {created_count}, "
        f"Skipped: {skipped_count}"
    )
