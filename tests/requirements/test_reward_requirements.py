"""
REWARD Requirements Verification Tests.

Explicitly tests all 6 REWARD requirements:
- REWARD-01: User can view available rewards with conditions
- REWARD-02: System checks reward eligibility automatically
- REWARD-03: User receives reward notification when conditions met
- REWARD-04: Rewards support streak, points, level, besitos spent conditions
- REWARD-05: Multiple conditions use AND logic
- REWARD-06: Reward value capped at maximum
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from bot.services.reward import RewardService
from bot.database.enums import (
    RewardType, RewardConditionType, RewardStatus,
    TransactionType, StreakType
)
from bot.database.models import (
    Reward, RewardCondition, UserReward,
    UserGamificationProfile, Transaction, UserContentAccess
)


@pytest.fixture
async def reward_service_with_mocks(test_session):
    """Create RewardService with mocked dependencies."""
    mock_wallet = AsyncMock()
    mock_wallet.earn_besitos = AsyncMock(return_value=(True, "earned", MagicMock()))

    mock_streak = AsyncMock()
    mock_streak.get_streak_info = AsyncMock(return_value={"current_streak": 7})

    service = RewardService(
        test_session,
        wallet_service=mock_wallet,
        streak_service=mock_streak
    )
    return service


class TestREWARD01:
    """
    REWARD-01: User can view available rewards with conditions.

    Acceptance Criteria:
    - User can see list of available rewards
    - Each reward shows its conditions
    - Each reward shows current status
    """

    async def test_reward_01_user_can_view_available_rewards(
        self, reward_service_with_mocks, test_session, test_user
    ):
        """
        Verify REWARD-01: User can view available rewards with conditions.

        Steps:
        1. Create rewards with conditions
        2. Call get_available_rewards()
        3. Assert: Returns list with reward names, descriptions, conditions
        4. Assert: Each reward shows current status
        """
        service = reward_service_with_mocks

        # Create rewards with conditions
        reward1 = Reward(
            name="Racha de 7 días",
            description="Mantén una racha de 7 días",
            reward_type=RewardType.BESITOS,
            reward_value={"amount": 50},
            is_active=True,
            sort_order=1
        )
        test_session.add(reward1)
        await test_session.flush()

        cond1 = RewardCondition(
            reward_id=reward1.id,
            condition_type=RewardConditionType.STREAK_LENGTH,
            condition_value=7,
            condition_group=0
        )
        test_session.add(cond1)

        reward2 = Reward(
            name="Primera Compra",
            description="Realiza tu primera compra",
            reward_type=RewardType.BADGE,
            reward_value={"badge_name": "Comprador", "emoji": "🛒"},
            is_active=True,
            sort_order=2
        )
        test_session.add(reward2)
        await test_session.flush()

        cond2 = RewardCondition(
            reward_id=reward2.id,
            condition_type=RewardConditionType.FIRST_PURCHASE,
            condition_group=0
        )
        test_session.add(cond2)
        await test_session.flush()

        # Call get_available_rewards
        available = await service.get_available_rewards(test_user.user_id)

        # Assert: Returns list with reward names, descriptions, conditions
        assert len(available) == 2

        reward_names = [r[0].name for r in available]
        assert "Racha de 7 días" in reward_names
        assert "Primera Compra" in reward_names

        # Assert: Each reward shows current status
        for reward, user_reward, progress_info in available:
            assert user_reward is not None
            assert hasattr(user_reward, 'status')
            assert progress_info is not None


class TestREWARD02:
    """
    REWARD-02: System checks reward eligibility automatically.

    Acceptance Criteria:
    - System evaluates conditions when relevant events occur
    - UserReward status updated to UNLOCKED when eligible
    """

    async def test_reward_02_system_checks_eligibility_on_event(
        self, reward_service_with_mocks, test_session, test_user
    ):
        """
        Verify REWARD-02: System checks eligibility automatically.

        Steps:
        1. Set up user meeting conditions
        2. Trigger event (daily_gift_claimed)
        3. Assert: System evaluates conditions automatically
        4. Assert: UserReward status updated to UNLOCKED
        """
        service = reward_service_with_mocks

        # Create reward with FIRST_DAILY_GIFT condition
        reward = Reward(
            name="Primer Regalo",
            description="Reclama tu primer regalo diario",
            reward_type=RewardType.BESITOS,
            reward_value={"amount": 25},
            is_active=True
        )
        test_session.add(reward)
        await test_session.flush()

        cond = RewardCondition(
            reward_id=reward.id,
            condition_type=RewardConditionType.FIRST_DAILY_GIFT,
            condition_group=0
        )
        test_session.add(cond)

        # Set up user meeting conditions (has EARN_DAILY transaction)
        tx = Transaction(
            user_id=test_user.user_id,
            amount=20,
            type=TransactionType.EARN_DAILY,
            reason="Daily gift"
        )
        test_session.add(tx)
        await test_session.flush()

        # Trigger event
        unlocked = await service.check_rewards_on_event(
            test_user.user_id, "daily_gift_claimed"
        )

        # Assert: System evaluated conditions automatically
        assert len(unlocked) == 1
        assert unlocked[0]["reward"].id == reward.id

        # Assert: UserReward status updated to UNLOCKED
        user_reward = await service._get_or_create_user_reward(
            test_user.user_id, reward.id
        )
        assert user_reward.status == RewardStatus.UNLOCKED


class TestREWARD03:
    """
    REWARD-03: User receives reward notification when conditions met.

    Acceptance Criteria:
    - Notification sent when reward unlocked
    - Message includes unlocked reward details
    """

    async def test_reward_03_user_receives_notification_when_conditions_met(
        self, reward_service_with_mocks, test_session, test_user
    ):
        """
        Verify REWARD-03: User receives notification when conditions met.

        Steps:
        1. Set up reward with conditions
        2. Trigger event that meets conditions
        3. Assert: build_reward_notification returns message
        4. Assert: Message includes unlocked reward details
        """
        service = reward_service_with_mocks

        # Set up reward with conditions
        reward = Reward(
            name="Notificación Test",
            description="Test de notificación",
            reward_type=RewardType.BESITOS,
            reward_value={"amount": 100},
            is_active=True
        )
        test_session.add(reward)
        await test_session.flush()

        cond = RewardCondition(
            reward_id=reward.id,
            condition_type=RewardConditionType.FIRST_DAILY_GIFT,
            condition_group=0
        )
        test_session.add(cond)

        tx = Transaction(
            user_id=test_user.user_id,
            amount=20,
            type=TransactionType.EARN_DAILY,
            reason="Daily gift"
        )
        test_session.add(tx)
        await test_session.flush()

        # Trigger event
        unlocked = await service.check_rewards_on_event(
            test_user.user_id, "daily_gift_claimed"
        )

        # Assert: build_reward_notification returns message
        notification = service.build_reward_notification(unlocked)

        assert notification["text"] != ""
        assert notification["primary_action"] == "claim"

        # Assert: Message includes unlocked reward details
        assert reward.name in notification["text"]
        assert "🎩" in notification["text"]  # Lucien's voice


class TestREWARD04:
    """
    REWARD-04: Rewards support streak, points, level, besitos spent conditions.

    Acceptance Criteria:
    - STREAK_LENGTH condition works
    - TOTAL_POINTS condition works
    - LEVEL_REACHED condition works
    - BESITOS_SPENT condition works
    """

    async def test_reward_04_streak_length_condition(
        self, reward_service_with_mocks, test_session, test_user
    ):
        """
        Verify REWARD-04: STREAK_LENGTH condition.

        Create reward with STREAK_LENGTH >= 7 condition
        User with streak = 7
        Assert: Eligible
        """
        service = reward_service_with_mocks

        # Create reward with STREAK_LENGTH >= 7 condition
        reward = Reward(
            name="Racha de 7 días",
            description="Mantén una racha de 7 días",
            reward_type=RewardType.BESITOS,
            reward_value={"amount": 50},
            is_active=True
        )
        test_session.add(reward)
        await test_session.flush()

        cond = RewardCondition(
            reward_id=reward.id,
            condition_type=RewardConditionType.STREAK_LENGTH,
            condition_value=7,
            condition_group=0
        )
        test_session.add(cond)
        await test_session.flush()

        await test_session.refresh(reward, ['conditions'])

        # Mock returns streak = 7
        service.streak_service.get_streak_info.return_value = {"current_streak": 7}

        # Evaluate
        eligible, passed, failed = await service.evaluate_reward_conditions(
            test_user.user_id, reward
        )

        # Assert: Eligible
        assert eligible is True

    async def test_reward_04_total_points_condition(
        self, reward_service_with_mocks, test_session, test_user
    ):
        """
        Verify REWARD-04: TOTAL_POINTS condition.

        Create reward with TOTAL_POINTS >= 1000 condition
        User with total_earned = 1000
        Assert: Eligible
        """
        service = reward_service_with_mocks

        # Create reward with TOTAL_POINTS >= 1000 condition
        reward = Reward(
            name="Acumulador",
            description="Acumula 1000 besitos",
            reward_type=RewardType.BADGE,
            reward_value={"badge_name": "Acumulador", "emoji": "💰"},
            is_active=True
        )
        test_session.add(reward)
        await test_session.flush()

        cond = RewardCondition(
            reward_id=reward.id,
            condition_type=RewardConditionType.TOTAL_POINTS,
            condition_value=1000,
            condition_group=0
        )
        test_session.add(cond)
        await test_session.flush()

        await test_session.refresh(reward, ['conditions'])

        # User with total_earned = 1000
        profile = UserGamificationProfile(
            user_id=test_user.user_id,
            total_earned=1000,
            level=1
        )
        test_session.add(profile)
        await test_session.flush()

        # Evaluate
        eligible, passed, failed = await service.evaluate_reward_conditions(
            test_user.user_id, reward
        )

        # Assert: Eligible
        assert eligible is True

    async def test_reward_04_level_reached_condition(
        self, reward_service_with_mocks, test_session, test_user
    ):
        """
        Verify REWARD-04: LEVEL_REACHED condition.

        Create reward with LEVEL_REACHED >= 5 condition
        User with level = 5
        Assert: Eligible
        """
        service = reward_service_with_mocks

        # Create reward with LEVEL_REACHED >= 5 condition
        reward = Reward(
            name="Nivel 5",
            description="Alcanza el nivel 5",
            reward_type=RewardType.BESITOS,
            reward_value={"amount": 200},
            is_active=True
        )
        test_session.add(reward)
        await test_session.flush()

        cond = RewardCondition(
            reward_id=reward.id,
            condition_type=RewardConditionType.LEVEL_REACHED,
            condition_value=5,
            condition_group=0
        )
        test_session.add(cond)
        await test_session.flush()

        await test_session.refresh(reward, ['conditions'])

        # User with level = 5
        profile = UserGamificationProfile(
            user_id=test_user.user_id,
            total_earned=500,
            level=5
        )
        test_session.add(profile)
        await test_session.flush()

        # Evaluate
        eligible, passed, failed = await service.evaluate_reward_conditions(
            test_user.user_id, reward
        )

        # Assert: Eligible
        assert eligible is True

    async def test_reward_04_besitos_spent_condition(
        self, reward_service_with_mocks, test_session, test_user
    ):
        """
        Verify REWARD-04: BESITOS_SPENT condition.

        Create reward with BESITOS_SPENT >= 500 condition
        User with total_spent = 500
        Assert: Eligible
        """
        service = reward_service_with_mocks

        # Create reward with BESITOS_SPENT >= 500 condition
        reward = Reward(
            name="Gastador",
            description="Gasta 500 besitos",
            reward_type=RewardType.BADGE,
            reward_value={"badge_name": "Gastador", "emoji": "💸"},
            is_active=True
        )
        test_session.add(reward)
        await test_session.flush()

        cond = RewardCondition(
            reward_id=reward.id,
            condition_type=RewardConditionType.BESITOS_SPENT,
            condition_value=500,
            condition_group=0
        )
        test_session.add(cond)
        await test_session.flush()

        await test_session.refresh(reward, ['conditions'])

        # User with total_spent = 500
        profile = UserGamificationProfile(
            user_id=test_user.user_id,
            total_spent=500,
            level=1
        )
        test_session.add(profile)
        await test_session.flush()

        # Evaluate
        eligible, passed, failed = await service.evaluate_reward_conditions(
            test_user.user_id, reward
        )

        # Assert: Eligible
        assert eligible is True


class TestREWARD05:
    """
    REWARD-05: Multiple conditions use AND logic.

    Acceptance Criteria:
    - All conditions in group 0 must pass (AND)
    - At least one condition in OR groups must pass
    """

    async def test_reward_05_multiple_conditions_and_logic(
        self, reward_service_with_mocks, test_session, test_user
    ):
        """
        Verify REWARD-05: Multiple conditions AND logic.

        Create reward with 3 conditions (all group 0)
        User meets 2 of 3
        Assert: Not eligible (AND requires all)
        User meets all 3
        Assert: Eligible
        """
        service = reward_service_with_mocks

        # Create reward with 3 conditions (all group 0)
        reward = Reward(
            name="Multi-Condición",
            description="Cumple 3 condiciones",
            reward_type=RewardType.BESITOS,
            reward_value={"amount": 500},
            is_active=True
        )
        test_session.add(reward)
        await test_session.flush()

        # All in group 0 (AND)
        cond1 = RewardCondition(
            reward_id=reward.id,
            condition_type=RewardConditionType.TOTAL_POINTS,
            condition_value=100,  # User has 200 - passes
            condition_group=0
        )
        cond2 = RewardCondition(
            reward_id=reward.id,
            condition_type=RewardConditionType.LEVEL_REACHED,
            condition_value=2,  # User is level 3 - passes
            condition_group=0
        )
        cond3 = RewardCondition(
            reward_id=reward.id,
            condition_type=RewardConditionType.BESITOS_SPENT,
            condition_value=1000,  # User spent 500 - fails
            condition_group=0
        )
        test_session.add_all([cond1, cond2, cond3])

        # User meets 2 of 3
        profile = UserGamificationProfile(
            user_id=test_user.user_id,
            total_earned=200,
            level=3,
            total_spent=500
        )
        test_session.add(profile)
        await test_session.flush()

        await test_session.refresh(reward, ['conditions'])

        # Evaluate - User meets 2 of 3
        eligible, passed, failed = await service.evaluate_reward_conditions(
            test_user.user_id, reward
        )

        # Assert: Not eligible (AND requires all)
        assert eligible is False

        # Now user meets all 3
        profile.total_spent = 1000
        await test_session.flush()

        eligible, passed, failed = await service.evaluate_reward_conditions(
            test_user.user_id, reward
        )

        # Assert: Eligible
        assert eligible is True

    async def test_reward_05_or_group_logic(
        self, reward_service_with_mocks, test_session, test_user
    ):
        """
        Verify REWARD-05: OR group logic.

        Create reward with group 0 AND, group 1 OR
        User meets group 0 but only 1 of 2 in group 1
        Assert: Eligible (OR only needs one)
        """
        service = reward_service_with_mocks

        # Create reward with group 0 AND, group 1 OR
        reward = Reward(
            name="OR Lógico",
            description="Prueba de grupos OR",
            reward_type=RewardType.BESITOS,
            reward_value={"amount": 100},
            is_active=True
        )
        test_session.add(reward)
        await test_session.flush()

        # Group 0: AND (must pass)
        cond_and = RewardCondition(
            reward_id=reward.id,
            condition_type=RewardConditionType.TOTAL_POINTS,
            condition_value=500,  # User has 1000 - passes
            condition_group=0
        )

        # Group 1: OR (at least one must pass)
        cond_or1 = RewardCondition(
            reward_id=reward.id,
            condition_type=RewardConditionType.LEVEL_REACHED,
            condition_value=10,  # User is level 5 - fails
            condition_group=1
        )
        cond_or2 = RewardCondition(
            reward_id=reward.id,
            condition_type=RewardConditionType.LEVEL_REACHED,
            condition_value=3,  # User is level 5 - passes
            condition_group=1
        )
        test_session.add_all([cond_and, cond_or1, cond_or2])

        # User meets group 0 but only 1 of 2 in group 1
        profile = UserGamificationProfile(
            user_id=test_user.user_id,
            total_earned=1000,
            level=5
        )
        test_session.add(profile)
        await test_session.flush()

        await test_session.refresh(reward, ['conditions'])

        # Evaluate
        eligible, passed, failed = await service.evaluate_reward_conditions(
            test_user.user_id, reward
        )

        # Assert: Eligible (OR only needs one)
        assert eligible is True


class TestREWARD06:
    """
    REWARD-06: Reward value capped at maximum.

    Acceptance Criteria:
    - BESITOS rewards capped at max_reward_besitos
    - VIP_EXTENSION rewards capped at max_reward_vip_days
    """

    async def test_reward_06_reward_value_capped(
        self, reward_service_with_mocks, test_session, test_user
    ):
        """
        Verify REWARD-06: Reward value capped at maximum.

        Create BESITOS reward with value 1000
        Configure max_reward_besitos = 100 in config
        Claim reward
        Assert: User receives min(value, max) besitos
        """
        service = reward_service_with_mocks

        # Create BESITOS reward with value 1000
        reward = Reward(
            name="Recompensa Grande",
            description="Muchos besitos",
            reward_type=RewardType.BESITOS,
            reward_value={"amount": 1000},  # Very high
            is_active=True
        )
        test_session.add(reward)
        await test_session.flush()

        # Create unlocked UserReward
        user_reward = UserReward(
            user_id=test_user.user_id,
            reward_id=reward.id,
            status=RewardStatus.UNLOCKED,
            unlocked_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_session.add(user_reward)
        await test_session.flush()

        # Claim reward
        success, msg, details = await service.claim_reward(
            test_user.user_id, reward.id
        )

        # Assert: Success
        assert success is True

        # Assert: Was capped
        assert details["was_capped"] is True

        # Assert: Wallet called with capped amount (default max is 100)
        call_args = service.wallet_service.earn_besitos.call_args
        assert call_args[1]["amount"] == 100  # Capped value
