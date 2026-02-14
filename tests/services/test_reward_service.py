"""
Tests for RewardService - Achievement and reward system.

Verifies:
- Condition evaluation for all types (numeric, event-based, exclusion)
- AND/OR logic for condition groups
- Event-driven reward checking
- Reward claiming flow
- User reward management
- Reward value capping (REWARD-06)
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from bot.services.reward import RewardService
from bot.database.enums import (
    RewardType, RewardConditionType, RewardStatus,
    TransactionType, StreakType, UserRole
)
from bot.database.models import Reward, RewardCondition, UserReward, UserGamificationProfile, User


@pytest.fixture
def mock_wallet_service():
    """Create a mock WalletService for testing."""
    mock = AsyncMock()
    mock.earn_besitos = AsyncMock(return_value=(True, "earned", MagicMock()))
    return mock


@pytest.fixture
def mock_streak_service():
    """Create a mock StreakService for testing."""
    mock = AsyncMock()
    mock.get_streak_info = AsyncMock(return_value={"current_streak": 5})
    return mock


@pytest.fixture
async def reward_service(test_session, mock_wallet_service, mock_streak_service):
    """Create a RewardService instance for testing."""
    service = RewardService(
        test_session,
        wallet_service=mock_wallet_service,
        streak_service=mock_streak_service
    )
    return service


@pytest.fixture
async def sample_reward(test_session):
    """Create a sample BESITOS reward with conditions."""
    reward = Reward(
        name="Test Reward",
        description="A test reward",
        reward_type=RewardType.BESITOS,
        reward_value={"amount": 100},
        is_active=True,
        sort_order=1
    )
    test_session.add(reward)
    await test_session.flush()
    return reward


@pytest.fixture
async def sample_content_reward(test_session):
    """Create a sample CONTENT reward."""
    reward = Reward(
        name="Content Reward",
        description="Exclusive content",
        reward_type=RewardType.CONTENT,
        reward_value={"content_set_id": 1},
        is_active=True,
        sort_order=2
    )
    test_session.add(reward)
    await test_session.flush()
    return reward


@pytest.fixture
async def sample_user_reward(test_session, sample_reward, test_user):
    """Create a UserReward record for testing."""
    user_reward = UserReward(
        user_id=test_user.user_id,
        reward_id=sample_reward.id,
        status=RewardStatus.LOCKED
    )
    test_session.add(user_reward)
    await test_session.flush()
    return user_reward


class TestConditionEvaluation:
    """Test condition evaluation for all types."""

    async def test_evaluate_numeric_condition_total_points(self, reward_service, test_session, test_user):
        """Verify TOTAL_POINTS >= comparison."""
        # Create profile with total_earned
        profile = UserGamificationProfile(
            user_id=test_user.user_id,
            total_earned=1000,
            level=1
        )
        test_session.add(profile)
        await test_session.flush()

        condition = MagicMock()
        condition.condition_type = RewardConditionType.TOTAL_POINTS
        condition.condition_value = 500

        result = await reward_service._evaluate_numeric_condition(
            profile, RewardConditionType.TOTAL_POINTS, 500
        )
        assert result is True

        # Test below threshold
        result = await reward_service._evaluate_numeric_condition(
            profile, RewardConditionType.TOTAL_POINTS, 1500
        )
        assert result is False

    async def test_evaluate_numeric_condition_level_reached(self, reward_service, test_session, test_user):
        """Verify LEVEL_REACHED check."""
        profile = UserGamificationProfile(
            user_id=test_user.user_id,
            total_earned=500,
            level=5
        )
        test_session.add(profile)
        await test_session.flush()

        result = await reward_service._evaluate_numeric_condition(
            profile, RewardConditionType.LEVEL_REACHED, 3
        )
        assert result is True

        result = await reward_service._evaluate_numeric_condition(
            profile, RewardConditionType.LEVEL_REACHED, 10
        )
        assert result is False

    async def test_evaluate_numeric_condition_besitos_spent(self, reward_service, test_session, test_user):
        """Verify BESITOS_SPENT check."""
        profile = UserGamificationProfile(
            user_id=test_user.user_id,
            total_spent=500,
            level=1
        )
        test_session.add(profile)
        await test_session.flush()

        result = await reward_service._evaluate_numeric_condition(
            profile, RewardConditionType.BESITOS_SPENT, 300
        )
        assert result is True

        result = await reward_service._evaluate_numeric_condition(
            profile, RewardConditionType.BESITOS_SPENT, 1000
        )
        assert result is False

    async def test_evaluate_numeric_condition_streak_length(self, reward_service, test_session, test_user):
        """Verify STREAK_LENGTH check using streak_service."""
        profile = UserGamificationProfile(
            user_id=test_user.user_id,
            level=1
        )
        test_session.add(profile)
        await test_session.flush()

        # Mock streak service returns streak of 5
        result = await reward_service._evaluate_numeric_condition(
            profile, RewardConditionType.STREAK_LENGTH, 3
        )
        assert result is True

        # Update mock to return lower streak
        reward_service.streak_service.get_streak_info.return_value = {"current_streak": 2}
        result = await reward_service._evaluate_numeric_condition(
            profile, RewardConditionType.STREAK_LENGTH, 5
        )
        assert result is False

    async def test_evaluate_event_condition_first_purchase(self, reward_service, test_session, test_user):
        """Check UserContentAccess existence for FIRST_PURCHASE."""
        from bot.database.models import UserContentAccess

        # No purchases yet
        result = await reward_service._evaluate_event_condition(
            test_user.user_id, RewardConditionType.FIRST_PURCHASE
        )
        assert result is False

        # Add a purchase
        access = UserContentAccess(
            user_id=test_user.user_id,
            content_set_id=1,
            access_type="shop_purchase",
            besitos_paid=100
        )
        test_session.add(access)
        await test_session.flush()

        result = await reward_service._evaluate_event_condition(
            test_user.user_id, RewardConditionType.FIRST_PURCHASE
        )
        assert result is True

    async def test_evaluate_event_condition_first_daily_gift(self, reward_service, test_session, test_user):
        """Check EARN_DAILY transaction for FIRST_DAILY_GIFT."""
        from bot.database.models import Transaction

        # No daily gift claimed
        result = await reward_service._evaluate_event_condition(
            test_user.user_id, RewardConditionType.FIRST_DAILY_GIFT
        )
        assert result is False

        # Add EARN_DAILY transaction
        tx = Transaction(
            user_id=test_user.user_id,
            amount=20,
            type=TransactionType.EARN_DAILY,
            reason="Daily gift"
        )
        test_session.add(tx)
        await test_session.flush()

        result = await reward_service._evaluate_event_condition(
            test_user.user_id, RewardConditionType.FIRST_DAILY_GIFT
        )
        assert result is True

    async def test_evaluate_event_condition_first_reaction(self, reward_service, test_session, test_user):
        """Check UserReaction existence for FIRST_REACTION."""
        from bot.database.models import UserReaction

        # No reactions
        result = await reward_service._evaluate_event_condition(
            test_user.user_id, RewardConditionType.FIRST_REACTION
        )
        assert result is False

        # Add a reaction
        reaction = UserReaction(
            user_id=test_user.user_id,
            content_id=123,
            channel_id="-100123",
            emoji="❤️"
        )
        test_session.add(reaction)
        await test_session.flush()

        result = await reward_service._evaluate_event_condition(
            test_user.user_id, RewardConditionType.FIRST_REACTION
        )
        assert result is True

    async def test_evaluate_exclusion_condition_not_vip(self, reward_service, test_session, test_user):
        """Verify NOT_VIP role check."""
        # User is FREE by default
        result = await reward_service._evaluate_exclusion_condition(
            test_user.user_id, RewardConditionType.NOT_VIP, 1
        )
        assert result is True

        # Change to VIP
        test_user.role = UserRole.VIP
        await test_session.flush()

        result = await reward_service._evaluate_exclusion_condition(
            test_user.user_id, RewardConditionType.NOT_VIP, 1
        )
        assert result is False

    async def test_evaluate_exclusion_condition_not_claimed_before(self, reward_service, test_session, test_user, sample_reward):
        """Verify NOT_CLAIMED_BEFORE check."""
        # No UserReward record exists yet
        result = await reward_service._evaluate_exclusion_condition(
            test_user.user_id, RewardConditionType.NOT_CLAIMED_BEFORE, sample_reward.id
        )
        assert result is True

        # Create UserReward with claim_count > 0
        user_reward = UserReward(
            user_id=test_user.user_id,
            reward_id=sample_reward.id,
            status=RewardStatus.CLAIMED,
            claim_count=1
        )
        test_session.add(user_reward)
        await test_session.flush()

        result = await reward_service._evaluate_exclusion_condition(
            test_user.user_id, RewardConditionType.NOT_CLAIMED_BEFORE, sample_reward.id
        )
        assert result is False


class TestRewardConditionsLogic:
    """Test AND/OR logic for condition groups."""

    async def test_evaluate_reward_all_conditions_and_logic(self, reward_service, test_session, test_user, sample_reward):
        """All conditions in group 0 must pass (AND logic)."""
        # Create profile
        profile = UserGamificationProfile(
            user_id=test_user.user_id,
            total_earned=1000,
            level=5,
            total_spent=500
        )
        test_session.add(profile)

        # Add 3 conditions in group 0 (all must pass)
        cond1 = RewardCondition(
            reward_id=sample_reward.id,
            condition_type=RewardConditionType.TOTAL_POINTS,
            condition_value=500,  # User has 1000 - passes
            condition_group=0
        )
        cond2 = RewardCondition(
            reward_id=sample_reward.id,
            condition_type=RewardConditionType.LEVEL_REACHED,
            condition_value=3,  # User is level 5 - passes
            condition_group=0
        )
        cond3 = RewardCondition(
            reward_id=sample_reward.id,
            condition_type=RewardConditionType.BESITOS_SPENT,
            condition_value=1000,  # User spent 500 - fails
            condition_group=0
        )
        test_session.add_all([cond1, cond2, cond3])
        await test_session.flush()

        # Refresh reward to load conditions
        await test_session.refresh(sample_reward, ['conditions'])

        eligible, passed, failed = await reward_service.evaluate_reward_conditions(
            test_user.user_id, sample_reward
        )

        assert eligible is False  # One condition failed
        assert len(passed) == 2
        assert len(failed) == 1

    async def test_evaluate_reward_or_group_logic(self, reward_service, test_session, test_user, sample_reward):
        """At least one condition in OR group must pass."""
        # Create profile
        profile = UserGamificationProfile(
            user_id=test_user.user_id,
            total_earned=100,
            level=2
        )
        test_session.add(profile)

        # Add conditions in group 1 (OR - at least one must pass)
        cond1 = RewardCondition(
            reward_id=sample_reward.id,
            condition_type=RewardConditionType.TOTAL_POINTS,
            condition_value=500,  # User has 100 - fails
            condition_group=1
        )
        cond2 = RewardCondition(
            reward_id=sample_reward.id,
            condition_type=RewardConditionType.LEVEL_REACHED,
            condition_value=5,  # User is level 2 - fails
            condition_group=1
        )
        cond3 = RewardCondition(
            reward_id=sample_reward.id,
            condition_type=RewardConditionType.LEVEL_REACHED,
            condition_value=1,  # User is level 2 - passes
            condition_group=1
        )
        test_session.add_all([cond1, cond2, cond3])
        await test_session.flush()

        await test_session.refresh(sample_reward, ['conditions'])

        eligible, passed, failed = await reward_service.evaluate_reward_conditions(
            test_user.user_id, sample_reward
        )

        assert eligible is True  # At least one in OR group passed

    async def test_evaluate_reward_mixed_and_or(self, reward_service, test_session, test_user, sample_reward):
        """Group 0 AND, Group 1 OR - mixed logic."""
        profile = UserGamificationProfile(
            user_id=test_user.user_id,
            total_earned=1000,
            level=3
        )
        test_session.add(profile)

        # Group 0: AND condition (must pass)
        cond_and = RewardCondition(
            reward_id=sample_reward.id,
            condition_type=RewardConditionType.TOTAL_POINTS,
            condition_value=500,  # User has 1000 - passes
            condition_group=0
        )

        # Group 1: OR conditions (at least one must pass)
        cond_or1 = RewardCondition(
            reward_id=sample_reward.id,
            condition_type=RewardConditionType.LEVEL_REACHED,
            condition_value=5,  # User is level 3 - fails
            condition_group=1
        )
        cond_or2 = RewardCondition(
            reward_id=sample_reward.id,
            condition_type=RewardConditionType.LEVEL_REACHED,
            condition_value=2,  # User is level 3 - passes
            condition_group=1
        )
        test_session.add_all([cond_and, cond_or1, cond_or2])
        await test_session.flush()

        await test_session.refresh(sample_reward, ['conditions'])

        eligible, passed, failed = await reward_service.evaluate_reward_conditions(
            test_user.user_id, sample_reward
        )

        assert eligible is True  # AND passed, OR group has at least one pass

    async def test_evaluate_reward_no_conditions(self, reward_service, sample_reward):
        """Empty conditions = eligible."""
        eligible, passed, failed = await reward_service.evaluate_reward_conditions(
            999999, sample_reward
        )

        assert eligible is True
        assert len(passed) == 0
        assert len(failed) == 0


class TestEventDrivenChecking:
    """Test event-driven reward checking."""

    async def test_check_rewards_on_daily_gift_event(self, reward_service, test_session, test_user, sample_reward):
        """Correct rewards triggered on daily_gift_claimed event."""
        # Add FIRST_DAILY_GIFT condition
        cond = RewardCondition(
            reward_id=sample_reward.id,
            condition_type=RewardConditionType.FIRST_DAILY_GIFT,
            condition_group=0
        )
        test_session.add(cond)

        # Add EARN_DAILY transaction
        from bot.database.models import Transaction
        tx = Transaction(
            user_id=test_user.user_id,
            amount=20,
            type=TransactionType.EARN_DAILY,
            reason="Daily gift"
        )
        test_session.add(tx)
        await test_session.flush()

        await test_session.refresh(sample_reward, ['conditions'])

        unlocked = await reward_service.check_rewards_on_event(
            test_user.user_id, "daily_gift_claimed"
        )

        assert len(unlocked) == 1
        assert unlocked[0]["reward"].id == sample_reward.id

    async def test_check_rewards_on_purchase_event(self, reward_service, test_session, test_user, sample_reward):
        """FIRST_PURCHASE triggered on purchase event."""
        from bot.database.models import UserContentAccess

        cond = RewardCondition(
            reward_id=sample_reward.id,
            condition_type=RewardConditionType.FIRST_PURCHASE,
            condition_group=0
        )
        test_session.add(cond)

        access = UserContentAccess(
            user_id=test_user.user_id,
            content_set_id=1,
            access_type="shop_purchase",
            besitos_paid=100
        )
        test_session.add(access)
        await test_session.flush()

        await test_session.refresh(sample_reward, ['conditions'])

        unlocked = await reward_service.check_rewards_on_event(
            test_user.user_id, "purchase_completed"
        )

        assert len(unlocked) == 1

    async def test_check_rewards_on_level_up(self, reward_service, test_session, test_user, sample_reward):
        """LEVEL_REACHED triggered on level_up event."""
        profile = UserGamificationProfile(
            user_id=test_user.user_id,
            total_earned=500,
            level=5
        )
        test_session.add(profile)

        cond = RewardCondition(
            reward_id=sample_reward.id,
            condition_type=RewardConditionType.LEVEL_REACHED,
            condition_value=3,
            condition_group=0
        )
        test_session.add(cond)
        await test_session.flush()

        await test_session.refresh(sample_reward, ['conditions'])

        unlocked = await reward_service.check_rewards_on_event(
            test_user.user_id, "level_up"
        )

        assert len(unlocked) == 1

    async def test_multiple_rewards_same_event(self, reward_service, test_session, test_user):
        """All applicable rewards checked on single event."""
        # Create two rewards
        reward1 = Reward(
            name="Reward 1",
            reward_type=RewardType.BESITOS,
            reward_value={"amount": 50},
            is_active=True
        )
        reward2 = Reward(
            name="Reward 2",
            reward_type=RewardType.BESITOS,
            reward_value={"amount": 100},
            is_active=True
        )
        test_session.add_all([reward1, reward2])
        await test_session.flush()

        # Both have same condition
        from bot.database.models import Transaction
        tx = Transaction(
            user_id=test_user.user_id,
            amount=20,
            type=TransactionType.EARN_DAILY,
            reason="Daily gift"
        )
        test_session.add(tx)

        cond1 = RewardCondition(
            reward_id=reward1.id,
            condition_type=RewardConditionType.FIRST_DAILY_GIFT,
            condition_group=0
        )
        cond2 = RewardCondition(
            reward_id=reward2.id,
            condition_type=RewardConditionType.FIRST_DAILY_GIFT,
            condition_group=0
        )
        test_session.add_all([cond1, cond2])
        await test_session.flush()

        await test_session.refresh(reward1, ['conditions'])
        await test_session.refresh(reward2, ['conditions'])

        unlocked = await reward_service.check_rewards_on_event(
            test_user.user_id, "daily_gift_claimed"
        )

        assert len(unlocked) == 2


class TestRewardClaiming:
    """Test reward claiming flow."""

    async def test_claim_reward_besitos_success(self, reward_service, mock_wallet_service, test_session, test_user, sample_reward):
        """Credits besitos via wallet on successful claim."""
        # Set up unlocked reward
        user_reward = UserReward(
            user_id=test_user.user_id,
            reward_id=sample_reward.id,
            status=RewardStatus.UNLOCKED,
            unlocked_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_session.add(user_reward)
        await test_session.flush()

        success, msg, details = await reward_service.claim_reward(
            test_user.user_id, sample_reward.id
        )

        assert success is True
        assert msg == "reward_claimed"
        mock_wallet_service.earn_besitos.assert_called_once()

    async def test_claim_reward_content_success(self, reward_service, test_session, test_user):
        """Creates UserContentAccess for CONTENT reward."""
        from bot.database.models import ContentSet

        # Create content set first
        content_set = ContentSet(
            name="Test Content",
            file_ids=["file1", "file2"],
            is_active=True
        )
        test_session.add(content_set)
        await test_session.flush()

        reward = Reward(
            name="Content Reward",
            reward_type=RewardType.CONTENT,
            reward_value={"content_set_id": content_set.id},
            is_active=True
        )
        test_session.add(reward)
        await test_session.flush()

        user_reward = UserReward(
            user_id=test_user.user_id,
            reward_id=reward.id,
            status=RewardStatus.UNLOCKED,
            unlocked_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_session.add(user_reward)
        await test_session.flush()

        success, msg, details = await reward_service.claim_reward(
            test_user.user_id, reward.id
        )

        assert success is True
        assert details["reward_result"]["content_set_id"] == content_set.id

    async def test_claim_reward_expired_fails(self, reward_service, test_session, test_user, sample_reward):
        """Returns error if reward expired."""
        user_reward = UserReward(
            user_id=test_user.user_id,
            reward_id=sample_reward.id,
            status=RewardStatus.EXPIRED,
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        test_session.add(user_reward)
        await test_session.flush()

        success, msg, details = await reward_service.claim_reward(
            test_user.user_id, sample_reward.id
        )

        assert success is False
        assert msg == "reward_expired"

    async def test_claim_reward_already_claimed_fails(self, reward_service, test_session, test_user, sample_reward):
        """Returns error for non-repeatable already claimed reward."""
        user_reward = UserReward(
            user_id=test_user.user_id,
            reward_id=sample_reward.id,
            status=RewardStatus.CLAIMED,
            claim_count=1
        )
        test_session.add(user_reward)
        await test_session.flush()

        success, msg, details = await reward_service.claim_reward(
            test_user.user_id, sample_reward.id
        )

        assert success is False
        assert msg == "already_claimed"

    async def test_claim_repeatable_reward_multiple_times(self, reward_service, test_session, test_user):
        """Allows multiple claims for repeatable rewards."""
        repeatable_reward = Reward(
            name="Repeatable Reward",
            reward_type=RewardType.BESITOS,
            reward_value={"amount": 10},
            is_repeatable=True,
            is_active=True
        )
        test_session.add(repeatable_reward)
        await test_session.flush()

        # First claim
        user_reward = UserReward(
            user_id=test_user.user_id,
            reward_id=repeatable_reward.id,
            status=RewardStatus.UNLOCKED,
            unlocked_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_session.add(user_reward)
        await test_session.flush()

        success1, msg1, details1 = await reward_service.claim_reward(
            test_user.user_id, repeatable_reward.id
        )
        assert success1 is True

        # Reset to unlocked for second claim (simulating re-eligibility)
        user_reward.status = RewardStatus.UNLOCKED
        user_reward.unlocked_at = datetime.utcnow()
        await test_session.flush()

        success2, msg2, details2 = await reward_service.claim_reward(
            test_user.user_id, repeatable_reward.id
        )
        assert success2 is True
        assert user_reward.claim_count == 2


class TestUserRewardManagement:
    """Test user reward management."""

    async def test_get_available_rewards_shows_non_secret(self, reward_service, test_session, test_user):
        """All non-secret rewards visible."""
        reward1 = Reward(
            name="Public Reward",
            reward_type=RewardType.BESITOS,
            reward_value={"amount": 10},
            is_secret=False,
            is_active=True
        )
        test_session.add(reward1)
        await test_session.flush()

        available = await reward_service.get_available_rewards(test_user.user_id)

        assert len(available) == 1
        assert available[0][0].name == "Public Reward"

    async def test_get_available_rewards_hides_secret_locked(self, reward_service, test_session, test_user):
        """Secret rewards hidden when locked."""
        secret_reward = Reward(
            name="Secret Reward",
            reward_type=RewardType.BESITOS,
            reward_value={"amount": 100},
            is_secret=True,
            is_active=True
        )
        test_session.add(secret_reward)
        await test_session.flush()

        # Default include_secret=False
        available = await reward_service.get_available_rewards(test_user.user_id)
        assert len(available) == 0

        # With include_secret=True
        available = await reward_service.get_available_rewards(
            test_user.user_id, include_secret=True
        )
        assert len(available) == 1

    async def test_get_available_rewards_shows_secret_unlocked(self, reward_service, test_session, test_user):
        """Secret rewards visible when unlocked."""
        secret_reward = Reward(
            name="Secret Reward",
            reward_type=RewardType.BESITOS,
            reward_value={"amount": 100},
            is_secret=True,
            is_active=True
        )
        test_session.add(secret_reward)
        await test_session.flush()

        # Create unlocked user_reward
        user_reward = UserReward(
            user_id=test_user.user_id,
            reward_id=secret_reward.id,
            status=RewardStatus.UNLOCKED
        )
        test_session.add(user_reward)
        await test_session.flush()

        available = await reward_service.get_available_rewards(test_user.user_id)
        assert len(available) == 1
        assert available[0][0].name == "Secret Reward"

    async def test_get_reward_progress_shows_current_values(self, reward_service, test_session, test_user, sample_reward):
        """Progress info shows current vs required values."""
        profile = UserGamificationProfile(
            user_id=test_user.user_id,
            total_earned=500,
            level=3,
            total_spent=200
        )
        test_session.add(profile)

        cond = RewardCondition(
            reward_id=sample_reward.id,
            condition_type=RewardConditionType.TOTAL_POINTS,
            condition_value=1000,
            condition_group=0
        )
        test_session.add(cond)
        await test_session.flush()

        await test_session.refresh(sample_reward, ['conditions'])

        progress = await reward_service.get_reward_progress(
            test_user.user_id, sample_reward.id
        )

        assert len(progress) == 1
        cond_id = list(progress.keys())[0]
        assert progress[cond_id]["current"] == 500
        assert progress[cond_id]["required"] == 1000
        assert progress[cond_id]["passed"] is False


class TestRewardValueCapping:
    """Test REWARD-06: Reward value capped at maximum."""

    async def test_reward_besitos_capped(self, reward_service, test_session, test_user):
        """BESITOS reward capped at max_reward_besitos."""
        high_value_reward = Reward(
            name="High Value Reward",
            reward_type=RewardType.BESITOS,
            reward_value={"amount": 1000},  # Very high
            is_active=True
        )
        test_session.add(high_value_reward)
        await test_session.flush()

        user_reward = UserReward(
            user_id=test_user.user_id,
            reward_id=high_value_reward.id,
            status=RewardStatus.UNLOCKED,
            unlocked_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_session.add(user_reward)
        await test_session.flush()

        success, msg, details = await reward_service.claim_reward(
            test_user.user_id, high_value_reward.id
        )

        assert success is True
        # Should be capped (default max is 100)
        assert details["was_capped"] is True

    async def test_reward_vip_extension_capped(self, reward_service, test_session, test_user):
        """VIP_EXTENSION reward capped at max_reward_vip_days."""
        vip_reward = Reward(
            name="VIP Extension",
            reward_type=RewardType.VIP_EXTENSION,
            reward_value={"days": 365},  # Very high
            is_active=True
        )
        test_session.add(vip_reward)
        await test_session.flush()

        user_reward = UserReward(
            user_id=test_user.user_id,
            reward_id=vip_reward.id,
            status=RewardStatus.UNLOCKED,
            unlocked_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_session.add(user_reward)
        await test_session.flush()

        success, msg, details = await reward_service.claim_reward(
            test_user.user_id, vip_reward.id
        )

        assert success is True
        # Should be capped (default max is 30 days)
        assert details["was_capped"] is True
        assert details["reward_result"]["days"] == 30  # Capped value
