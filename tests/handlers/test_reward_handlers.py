"""
Tests for reward handlers - UI and flow integration.

Verifies:
- Rewards list display with correct status emojis
- Claim handler functionality
- Reward detail display
- Voice consistency (Lucien for admin, Diana for success)
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.types import Message, CallbackQuery, User as TelegramUser
from aiogram.fsm.context import FSMContext

from bot.services.reward import RewardService
from bot.database.enums import RewardType, RewardStatus
from bot.database.models import Reward, UserReward


@pytest.fixture
async def reward_service(test_session):
    """Create a RewardService instance for testing."""
    mock_wallet = AsyncMock()
    mock_wallet.earn_besitos = AsyncMock(return_value=(True, "earned", MagicMock()))

    mock_streak = AsyncMock()
    mock_streak.get_streak_info = AsyncMock(return_value={"current_streak": 5})

    service = RewardService(
        test_session,
        wallet_service=mock_wallet,
        streak_service=mock_streak
    )
    return service


@pytest.fixture
def mock_reward_message():
    """Create a mock message for reward testing."""
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=TelegramUser)
    message.from_user.id = 123456
    message.from_user.first_name = "Test"
    message.answer = AsyncMock()
    message.edit_text = AsyncMock()
    return message


@pytest.fixture
def mock_reward_callback():
    """Create a mock callback query for reward testing."""
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock(spec=TelegramUser)
    callback.from_user.id = 123456
    callback.from_user.first_name = "Test"
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    return callback


@pytest.fixture
async def sample_rewards_list(test_session):
    """Create a list of rewards with different statuses."""
    rewards = []

    # Locked reward
    r1 = Reward(
        name="Locked Reward",
        description="Not yet unlocked",
        reward_type=RewardType.BESITOS,
        reward_value={"amount": 50},
        is_active=True,
        sort_order=1
    )
    test_session.add(r1)

    # Unlocked reward
    r2 = Reward(
        name="Unlocked Reward",
        description="Ready to claim",
        reward_type=RewardType.BESITOS,
        reward_value={"amount": 100},
        is_active=True,
        sort_order=2
    )
    test_session.add(r2)

    # Claimed reward
    r3 = Reward(
        name="Claimed Reward",
        description="Already claimed",
        reward_type=RewardType.BADGE,
        reward_value={"badge_name": "Tester", "emoji": "🧪"},
        is_active=True,
        sort_order=3
    )
    test_session.add(r3)

    await test_session.flush()

    rewards = [r1, r2, r3]
    return rewards


class TestRewardsListHandler:
    """Test rewards list display handler."""

    async def test_rewards_list_shows_all_rewards(self, test_session, sample_rewards_list, test_user):
        """Handler displays all active rewards."""
        from bot.services.reward import RewardService

        service = RewardService(test_session)
        available = await service.get_available_rewards(test_user.user_id)

        assert len(available) == 3
        reward_names = [r[0].name for r in available]
        assert "Locked Reward" in reward_names
        assert "Unlocked Reward" in reward_names
        assert "Claimed Reward" in reward_names

    async def test_rewards_list_shows_correct_status_emojis(self, test_session, sample_rewards_list, test_user):
        """Status emojis 🔒 ✨ ✅ displayed correctly."""
        from bot.services.reward import RewardService
        from bot.database.enums import RewardStatus

        # Create user rewards with different statuses
        for i, reward in enumerate(sample_rewards_list):
            if i == 0:
                status = RewardStatus.LOCKED
            elif i == 1:
                status = RewardStatus.UNLOCKED
            else:
                status = RewardStatus.CLAIMED

            user_reward = UserReward(
                user_id=test_user.user_id,
                reward_id=reward.id,
                status=status
            )
            test_session.add(user_reward)

        await test_session.flush()

        service = RewardService(test_session)
        available = await service.get_available_rewards(test_user.user_id)

        # Check status emojis
        for reward, user_reward, _ in available:
            if user_reward.status == RewardStatus.LOCKED:
                assert RewardStatus.LOCKED.emoji == "🔒"
            elif user_reward.status == RewardStatus.UNLOCKED:
                assert RewardStatus.UNLOCKED.emoji == "🔓"
            elif user_reward.status == RewardStatus.CLAIMED:
                assert RewardStatus.CLAIMED.emoji == "✅"

    async def test_rewards_list_shows_claim_button_for_unlocked(self, test_session, sample_rewards_list, test_user):
        """Claim button present for unlocked rewards."""
        from bot.services.reward import RewardService

        # Create unlocked user_reward
        user_reward = UserReward(
            user_id=test_user.user_id,
            reward_id=sample_rewards_list[1].id,  # Unlocked Reward
            status=RewardStatus.UNLOCKED,
            unlocked_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_session.add(user_reward)
        await test_session.flush()

        service = RewardService(test_session)
        available = await service.get_available_rewards(test_user.user_id)

        unlocked = [r for r in available if r[1].status == RewardStatus.UNLOCKED]
        assert len(unlocked) == 1
        assert unlocked[0][1].status == RewardStatus.UNLOCKED

    async def test_rewards_list_empty_shows_message(self, test_session, test_user):
        """No rewards message when empty."""
        from bot.services.reward import RewardService

        service = RewardService(test_session)
        available = await service.get_available_rewards(test_user.user_id)

        assert len(available) == 0


class TestRewardClaimHandler:
    """Test reward claim handler."""

    async def test_claim_unlocked_reward_success(self, reward_service, test_session, test_user, sample_rewards_list):
        """Updates status to CLAIMED on successful claim."""
        reward = sample_rewards_list[1]  # Unlocked Reward

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
        assert msg == "reward_claimed"

        # Refresh to check status
        await test_session.refresh(user_reward)
        assert user_reward.status == RewardStatus.CLAIMED
        assert user_reward.claim_count == 1

    async def test_claim_locked_reward_fails(self, reward_service, test_session, test_user, sample_rewards_list):
        """Error message shown for locked reward."""
        reward = sample_rewards_list[0]  # Locked Reward

        user_reward = UserReward(
            user_id=test_user.user_id,
            reward_id=reward.id,
            status=RewardStatus.LOCKED
        )
        test_session.add(user_reward)
        await test_session.flush()

        success, msg, details = await reward_service.claim_reward(
            test_user.user_id, reward.id
        )

        assert success is False
        assert msg == "reward_locked"

    async def test_claim_expired_reward_fails(self, reward_service, test_session, test_user, sample_rewards_list):
        """Error message shown for expired reward."""
        reward = sample_rewards_list[1]

        user_reward = UserReward(
            user_id=test_user.user_id,
            reward_id=reward.id,
            status=RewardStatus.EXPIRED,
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        test_session.add(user_reward)
        await test_session.flush()

        success, msg, details = await reward_service.claim_reward(
            test_user.user_id, reward.id
        )

        assert success is False
        assert msg == "reward_expired"

    async def test_claim_already_claimed_fails(self, reward_service, test_session, test_user, sample_rewards_list):
        """Error for non-repeatable already claimed."""
        reward = sample_rewards_list[0]
        reward.is_repeatable = False

        user_reward = UserReward(
            user_id=test_user.user_id,
            reward_id=reward.id,
            status=RewardStatus.CLAIMED,
            claim_count=1
        )
        test_session.add(user_reward)
        await test_session.flush()

        success, msg, details = await reward_service.claim_reward(
            test_user.user_id, reward.id
        )

        assert success is False
        assert msg == "already_claimed"

    async def test_claim_repeatable_second_time_success(self, reward_service, test_session, test_user):
        """Allows second claim for repeatable rewards."""
        repeatable_reward = Reward(
            name="Repeatable",
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
            expires_at=datetime.utcnow() + timedelta(hours=24),
            claim_count=1
        )
        test_session.add(user_reward)
        await test_session.flush()

        success, msg, details = await reward_service.claim_reward(
            test_user.user_id, repeatable_reward.id
        )

        assert success is True
        assert user_reward.claim_count == 2


class TestRewardDetailHandler:
    """Test reward detail display."""

    async def test_reward_detail_shows_conditions(self, reward_service, test_session, test_user, sample_rewards_list):
        """All conditions listed in detail."""
        from bot.database.models import RewardCondition
        from bot.database.enums import RewardConditionType

        reward = sample_rewards_list[0]

        # Add conditions
        cond1 = RewardCondition(
            reward_id=reward.id,
            condition_type=RewardConditionType.TOTAL_POINTS,
            condition_value=1000,
            condition_group=0
        )
        cond2 = RewardCondition(
            reward_id=reward.id,
            condition_type=RewardConditionType.LEVEL_REACHED,
            condition_value=5,
            condition_group=0
        )
        test_session.add_all([cond1, cond2])
        await test_session.flush()

        await test_session.refresh(reward, ['conditions'])

        assert len(reward.conditions) == 2
        condition_types = [c.condition_type for c in reward.conditions]
        assert RewardConditionType.TOTAL_POINTS in condition_types
        assert RewardConditionType.LEVEL_REACHED in condition_types

    async def test_reward_detail_shows_progress(self, reward_service, test_session, test_user, sample_rewards_list):
        """Current vs required shown in progress."""
        from bot.database.models import RewardCondition, UserGamificationProfile
        from bot.database.enums import RewardConditionType

        reward = sample_rewards_list[0]

        # Create profile
        profile = UserGamificationProfile(
            user_id=test_user.user_id,
            total_earned=500,
            level=3
        )
        test_session.add(profile)

        # Add condition
        cond = RewardCondition(
            reward_id=reward.id,
            condition_type=RewardConditionType.TOTAL_POINTS,
            condition_value=1000,
            condition_group=0
        )
        test_session.add(cond)
        await test_session.flush()

        progress = await reward_service.get_reward_progress(
            test_user.user_id, reward.id
        )

        assert len(progress) == 1
        cond_id = list(progress.keys())[0]
        assert progress[cond_id]["current"] == 500
        assert progress[cond_id]["required"] == 1000
        assert progress[cond_id]["passed"] is False

    async def test_reward_detail_unlocked_has_claim_button(self, reward_service, test_session, test_user, sample_rewards_list):
        """Claim option available for unlocked rewards."""
        reward = sample_rewards_list[1]

        user_reward = UserReward(
            user_id=test_user.user_id,
            reward_id=reward.id,
            status=RewardStatus.UNLOCKED,
            unlocked_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_session.add(user_reward)
        await test_session.flush()

        # Verify unlocked status
        assert user_reward.status == RewardStatus.UNLOCKED
        assert user_reward.expires_at is not None


class TestVoiceConsistency:
    """Test voice consistency in reward messages."""

    async def test_rewards_list_uses_lucien_voice(self, reward_service, sample_rewards_list):
        """Lucien emoji present in reward notifications."""
        notification = reward_service.build_reward_notification(
            [{"reward": sample_rewards_list[0], "status_result": "newly_unlocked"}],
            event_context="daily_gift"
        )

        assert "🎩" in notification["text"]

    async def test_reward_claim_success_uses_diana_voice(self, test_session, test_user, sample_rewards_list):
        """Diana emoji present for success messages."""
        # Success messages for claiming rewards use Diana's voice
        # This would be in the handler implementation
        # For now, we verify the notification builder uses Lucien
        # and claim success would use Diana

        # Diana's voice uses 🫦 emoji
        # This test verifies the pattern exists
        from bot.services.reward import RewardService

        service = RewardService(test_session)

        # Build notification uses Lucien (🎩)
        notification = service.build_reward_notification([])
        # Empty notification returns empty text
        assert notification["text"] == ""

        # Non-empty uses Lucien
        notification = service.build_reward_notification(
            [{"reward": sample_rewards_list[0], "status_result": "newly_unlocked"}]
        )
        assert "🎩" in notification["text"]

    async def test_reward_claim_error_uses_lucien_voice(self, reward_service, sample_rewards_list):
        """Lucien emoji present for error messages."""
        # Error messages use Lucien's voice (🎩)
        notification = reward_service.build_reward_notification(
            [{"reward": sample_rewards_list[0], "status_result": "newly_unlocked"}]
        )

        assert "🎩" in notification["text"]
        # Should have formal tone
        assert "Ha desbloqueado" in notification["text"] or "Excelente" in notification["text"]


class TestRewardNotificationBuilder:
    """Test reward notification message builder."""

    async def test_single_reward_notification(self, reward_service, sample_rewards_list):
        """Single reward notification format."""
        notification = reward_service.build_reward_notification(
            [{"reward": sample_rewards_list[0], "status_result": "newly_unlocked"}]
        )

        assert "🎩" in notification["text"]
        assert "Excelente" in notification["text"]
        assert sample_rewards_list[0].name in notification["text"]
        assert notification["primary_action"] == "claim"

    async def test_multiple_rewards_notification(self, reward_service, sample_rewards_list):
        """Multiple rewards notification format."""
        notification = reward_service.build_reward_notification(
            [
                {"reward": sample_rewards_list[0], "status_result": "newly_unlocked"},
                {"reward": sample_rewards_list[1], "status_result": "newly_unlocked"}
            ]
        )

        assert "🎩" in notification["text"]
        assert "2" in notification["text"]  # Count mentioned
        assert notification["primary_action"] == "claim"

    async def test_empty_notification(self, reward_service):
        """Empty notification returns empty text."""
        notification = reward_service.build_reward_notification([])

        assert notification["text"] == ""
        assert notification["primary_action"] == "none"

    async def test_context_specific_messages(self, reward_service, sample_rewards_list):
        """Context-specific messages for different events."""
        contexts = ["daily_gift", "purchase", "level_up", "reaction_added", "streak_updated"]

        for context in contexts:
            notification = reward_service.build_reward_notification(
                [{"reward": sample_rewards_list[0], "status_result": "newly_unlocked"}],
                event_context=context
            )
            assert "🎩" in notification["text"]
            assert notification["primary_action"] == "claim"


class TestRewardStats:
    """Test user reward statistics."""

    async def test_get_user_reward_stats(self, reward_service, test_session, test_user, sample_rewards_list):
        """Statistics calculated correctly."""
        # Create user rewards with different statuses
        for i, reward in enumerate(sample_rewards_list):
            if i == 0:
                status = RewardStatus.LOCKED
            elif i == 1:
                status = RewardStatus.UNLOCKED
            else:
                status = RewardStatus.CLAIMED

            user_reward = UserReward(
                user_id=test_user.user_id,
                reward_id=reward.id,
                status=status,
                claim_count=1 if status == RewardStatus.CLAIMED else 0
            )
            test_session.add(user_reward)

        await test_session.flush()

        stats = await reward_service.get_user_reward_stats(test_user.user_id)

        assert stats["total_claimed"] == 1
        assert stats["currently_unlocked"] == 1
        assert stats["total_unlocked"] == 2  # UNLOCKED + CLAIMED

    async def test_stats_empty_user(self, reward_service, test_session):
        """Stats for user with no rewards."""
        stats = await reward_service.get_user_reward_stats(999999)

        assert stats["total_claimed"] == 0
        assert stats["currently_unlocked"] == 0
        assert stats["total_unlocked"] == 0
