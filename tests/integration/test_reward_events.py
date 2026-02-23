"""
Integration tests for reward event flows.

Tests complete end-to-end flows:
- Daily gift triggers streak rewards
- Purchase triggers first purchase rewards
- Level up triggers level rewards
- Multiple rewards in single notification
- Secret rewards hidden until unlocked
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from bot.services.reward import RewardService
from bot.services.wallet import WalletService
from bot.database.enums import (
    RewardType, RewardConditionType, RewardStatus,
    TransactionType
)
from bot.database.models import (
    Reward, RewardCondition, UserReward,
    UserGamificationProfile, Transaction,
    UserContentAccess, ContentSet
)


@pytest.fixture
async def integrated_reward_service(test_session):
    """Create RewardService with real WalletService."""
    wallet_service = WalletService(test_session)

    # Mock streak service (we'll control streak values)
    mock_streak = AsyncMock()
    mock_streak.get_streak_info = AsyncMock(return_value={"current_streak": 7})

    service = RewardService(
        test_session,
        wallet_service=wallet_service,
        streak_service=mock_streak
    )
    return service


class TestDailyGiftRewardFlow:
    """Test daily gift triggers rewards."""

    async def test_daily_gift_triggers_streak_reward(
        self, integrated_reward_service, test_session, test_user
    ):
        """
        User claims daily gift -> Streak reaches 7 days -> Reward unlocked.

        Steps:
        1. Create streak reward with STREAK_LENGTH >= 7
        2. Mock streak service returns 7 days
        3. Trigger daily_gift_claimed event
        4. Assert: "Racha de 7 días" reward unlocked
        5. Assert: Notification includes both gift and reward
        """
        service = integrated_reward_service
        service.streak_service.get_streak_info.return_value = {"current_streak": 7}

        # Create user profile (required for STREAK_LENGTH condition)
        profile = UserGamificationProfile(
            user_id=test_user.user_id,
            total_earned=100,
            level=1
        )
        test_session.add(profile)

        # Create streak reward
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

        # Add EARN_DAILY transaction (simulating daily gift claim)
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

        # Assert: "Racha de 7 días" reward unlocked
        assert len(unlocked) >= 1
        reward_names = [u["reward"].name for u in unlocked]
        assert "Racha de 7 días" in reward_names

        # Assert: Notification includes reward
        notification = service.build_reward_notification(
            unlocked, event_context="daily_gift"
        )
        assert "Racha de 7 días" in notification["text"]
        assert "🎩" in notification["text"]

    async def test_daily_gift_no_duplicate_notifications(
        self, integrated_reward_service, test_session, test_user
    ):
        """
        User claims daily gift -> No new rewards unlocked -> Only daily gift confirmation.

        Steps:
        1. User claims daily gift
        2. No new rewards unlocked
        3. Assert: Empty notification list
        """
        service = integrated_reward_service
        service.streak_service.get_streak_info.return_value = {"current_streak": 1}

        # Create reward requiring streak of 30 (user has 1)
        reward = Reward(
            name="Racha de 30 días",
            description="Mantén una racha de 30 días",
            reward_type=RewardType.BESITOS,
            reward_value={"amount": 200},
            is_active=True
        )
        test_session.add(reward)
        await test_session.flush()

        cond = RewardCondition(
            reward_id=reward.id,
            condition_type=RewardConditionType.STREAK_LENGTH,
            condition_value=30,
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

        # Assert: No rewards unlocked
        assert len(unlocked) == 0


class TestPurchaseRewardFlow:
    """Test purchase triggers rewards."""

    async def test_first_purchase_triggers_reward(
        self, integrated_reward_service, test_session, test_user
    ):
        """
        User makes first shop purchase -> "Primera Compra" reward unlocked.

        Steps:
        1. Create FIRST_PURCHASE reward
        2. User makes first purchase (UserContentAccess created)
        3. Trigger purchase_completed event
        4. Assert: "Primera Compra" reward unlocked
        5. Assert: Notification includes purchase + reward
        """
        service = integrated_reward_service

        # Create FIRST_PURCHASE reward
        reward = Reward(
            name="Primera Compra",
            description="Realiza tu primera compra",
            reward_type=RewardType.BADGE,
            reward_value={"badge_name": "Comprador", "emoji": "🛒"},
            is_active=True
        )
        test_session.add(reward)
        await test_session.flush()

        cond = RewardCondition(
            reward_id=reward.id,
            condition_type=RewardConditionType.FIRST_PURCHASE,
            condition_group=0
        )
        test_session.add(cond)
        await test_session.flush()

        await test_session.refresh(reward, ['conditions'])

        # Create content set first
        content_set = ContentSet(
            name="Test Content",
            file_ids=["file1"],
            is_active=True
        )
        test_session.add(content_set)
        await test_session.flush()

        # User makes first purchase
        access = UserContentAccess(
            user_id=test_user.user_id,
            content_set_id=content_set.id,
            access_type="shop_purchase",
            besitos_paid=100
        )
        test_session.add(access)
        await test_session.flush()

        # Trigger event
        unlocked = await service.check_rewards_on_event(
            test_user.user_id, "purchase_completed"
        )

        # Assert: "Primera Compra" reward unlocked
        assert len(unlocked) == 1
        assert unlocked[0]["reward"].name == "Primera Compra"

        # Assert: Notification includes purchase + reward
        notification = service.build_reward_notification(
            unlocked, event_context="purchase"
        )
        assert "Primera Compra" in notification["text"]
        assert "adquisición" in notification["text"].lower()

    async def test_besitos_spent_threshold_triggers_reward(
        self, integrated_reward_service, test_session, test_user
    ):
        """
        User spends 1000 besitos total -> "Gastador VIP" reward unlocked.

        Steps:
        1. Create BESITOS_SPENT >= 1000 reward
        2. User profile has total_spent = 1000
        3. Trigger purchase_completed event
        4. Assert: "Gastador VIP" reward unlocked
        """
        service = integrated_reward_service

        # Create BESITOS_SPENT reward
        reward = Reward(
            name="Gastador VIP",
            description="Gasta 1000 besitos en total",
            reward_type=RewardType.BADGE,
            reward_value={"badge_name": "Gastador VIP", "emoji": "💸"},
            is_active=True
        )
        test_session.add(reward)
        await test_session.flush()

        cond = RewardCondition(
            reward_id=reward.id,
            condition_type=RewardConditionType.BESITOS_SPENT,
            condition_value=1000,
            condition_group=0
        )
        test_session.add(cond)

        # User profile has total_spent = 1000
        profile = UserGamificationProfile(
            user_id=test_user.user_id,
            total_spent=1000,
            level=1
        )
        test_session.add(profile)
        await test_session.flush()

        await test_session.refresh(reward, ['conditions'])

        # Trigger event
        unlocked = await service.check_rewards_on_event(
            test_user.user_id, "purchase_completed"
        )

        # Assert: "Gastador VIP" reward unlocked
        assert len(unlocked) == 1
        assert unlocked[0]["reward"].name == "Gastador VIP"


class TestLevelUpRewardFlow:
    """Test level up triggers rewards."""

    async def test_level_up_triggers_level_reward(
        self, integrated_reward_service, test_session, test_user
    ):
        """
        User reaches level 5 -> "Nivel 5 Alcanzado" reward unlocked.

        Steps:
        1. Create LEVEL_REACHED >= 5 reward
        2. User profile has level = 5
        3. Trigger level_up event
        4. Assert: "Nivel 5 Alcanzado" reward unlocked
        5. Assert: Notification sent
        """
        service = integrated_reward_service

        # Create LEVEL_REACHED reward
        reward = Reward(
            name="Nivel 5 Alcanzado",
            description="Alcanza el nivel 5",
            reward_type=RewardType.BESITOS,
            reward_value={"amount": 100},
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

        # User profile has level = 5
        profile = UserGamificationProfile(
            user_id=test_user.user_id,
            total_earned=500,
            level=5
        )
        test_session.add(profile)
        await test_session.flush()

        await test_session.refresh(reward, ['conditions'])

        # Trigger event
        unlocked = await service.check_rewards_on_event(
            test_user.user_id, "level_up"
        )

        # Assert: "Nivel 5 Alcanzado" reward unlocked
        assert len(unlocked) == 1
        assert unlocked[0]["reward"].name == "Nivel 5 Alcanzado"

        # Assert: Notification sent
        notification = service.build_reward_notification(
            unlocked, event_context="level_up"
        )
        assert "Nivel 5 Alcanzado" in notification["text"]
        assert "progreso" in notification["text"].lower()


class TestGroupedNotifications:
    """Test multiple rewards in single notification."""

    async def test_multiple_rewards_single_notification(
        self, integrated_reward_service, test_session, test_user
    ):
        """
        Event triggers 3 rewards simultaneously -> Single message with all 3.

        Steps:
        1. Create 3 rewards with same condition
        2. User meets all conditions
        3. Trigger event
        4. Assert: Single message with all 3 rewards
        5. Assert: No duplicate/spam messages
        """
        service = integrated_reward_service

        # Create 3 rewards with same condition
        rewards = []
        for i, name in enumerate(["Reward A", "Reward B", "Reward C"]):
            reward = Reward(
                name=name,
                description=f"Description {i}",
                reward_type=RewardType.BESITOS,
                reward_value={"amount": 50 * (i + 1)},
                is_active=True
            )
            test_session.add(reward)
            await test_session.flush()
            rewards.append(reward)

            cond = RewardCondition(
                reward_id=reward.id,
                condition_type=RewardConditionType.FIRST_DAILY_GIFT,
                condition_group=0
            )
            test_session.add(cond)

        # User meets all conditions (has EARN_DAILY transaction)
        tx = Transaction(
            user_id=test_user.user_id,
            amount=20,
            type=TransactionType.EARN_DAILY,
            reason="Daily gift"
        )
        test_session.add(tx)
        await test_session.flush()

        for reward in rewards:
            await test_session.refresh(reward, ['conditions'])

        # Trigger event
        unlocked = await service.check_rewards_on_event(
            test_user.user_id, "daily_gift_claimed"
        )

        # Assert: All 3 rewards unlocked
        assert len(unlocked) == 3

        # Assert: Single message with all 3 rewards
        notification = service.build_reward_notification(unlocked)
        assert "3" in notification["text"]  # Count mentioned
        assert "Reward A" in notification["text"]
        assert "Reward B" in notification["text"]
        assert "Reward C" in notification["text"]

        # Assert: Single notification (not 3 separate)
        assert notification["primary_action"] == "claim"


class TestSecretRewards:
    """Test secret rewards hidden until unlocked."""

    async def test_secret_reward_hidden_until_unlocked(
        self, integrated_reward_service, test_session, test_user
    ):
        """
        Create secret reward -> User views reward list -> Secret reward not visible.
        User meets conditions -> Secret reward now visible.

        Steps:
        1. Create secret reward
        2. User views reward list
        3. Assert: Secret reward not visible
        4. User meets conditions
        5. Assert: Secret reward now visible
        """
        service = integrated_reward_service

        # Create secret reward
        secret_reward = Reward(
            name="Recompensa Secreta",
            description="Sorpresa especial",
            reward_type=RewardType.CONTENT,
            reward_value={"content_set_id": 1},
            is_secret=True,
            is_active=True
        )
        test_session.add(secret_reward)

        # Create regular reward
        regular_reward = Reward(
            name="Recompensa Normal",
            description="Visible para todos",
            reward_type=RewardType.BESITOS,
            reward_value={"amount": 50},
            is_secret=False,
            is_active=True
        )
        test_session.add(regular_reward)
        await test_session.flush()

        # User views reward list (default: include_secret=False)
        available = await service.get_available_rewards(test_user.user_id)

        # Assert: Secret reward not visible
        assert len(available) == 1
        assert available[0][0].name == "Recompensa Normal"

        # User meets conditions - get the existing UserReward and update it
        user_reward = await service._get_or_create_user_reward(
            test_user.user_id, secret_reward.id
        )
        user_reward.status = RewardStatus.UNLOCKED
        user_reward.unlocked_at = datetime.utcnow()
        await test_session.flush()

        # User views reward list again
        available = await service.get_available_rewards(test_user.user_id)

        # Assert: Secret reward now visible (because unlocked)
        assert len(available) == 2
        reward_names = [r[0].name for r in available]
        assert "Recompensa Secreta" in reward_names
        assert "Recompensa Normal" in reward_names


class TestRewardClaimingFlow:
    """Test complete reward claiming flow."""

    async def test_claim_reward_updates_balance(
        self, integrated_reward_service, test_session, test_user
    ):
        """
        User claims BESITOS reward -> Balance updated correctly.

        Steps:
        1. Create BESITOS reward
        2. Create unlocked UserReward
        3. Claim reward
        4. Assert: Balance increased by reward amount
        """
        service = integrated_reward_service

        # Create BESITOS reward
        reward = Reward(
            name="Besitos Reward",
            reward_type=RewardType.BESITOS,
            reward_value={"amount": 100},
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

        # Get initial balance
        initial_balance = await service.wallet_service.get_balance(test_user.user_id)

        # Claim reward
        success, msg, details = await service.claim_reward(
            test_user.user_id, reward.id
        )

        # Assert: Success
        assert success is True

        # Assert: Balance increased
        final_balance = await service.wallet_service.get_balance(test_user.user_id)
        assert final_balance == initial_balance + 100

    async def test_claim_content_reward_creates_access(
        self, integrated_reward_service, test_session, test_user
    ):
        """
        User claims CONTENT reward -> UserContentAccess created.

        Steps:
        1. Create CONTENT reward with content_set_id
        2. Create unlocked UserReward
        3. Claim reward
        4. Assert: UserContentAccess record created
        """
        service = integrated_reward_service

        # Create content set
        content_set = ContentSet(
            name="Exclusive Content",
            file_ids=["file1", "file2"],
            is_active=True
        )
        test_session.add(content_set)
        await test_session.flush()

        # Create CONTENT reward
        reward = Reward(
            name="Exclusive Content Reward",
            reward_type=RewardType.CONTENT,
            reward_value={"content_set_id": content_set.id},
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

        # Assert: UserContentAccess created
        assert details["reward_result"]["content_set_id"] == content_set.id
        assert "access_id" in details["reward_result"]


class TestRewardExpiration:
    """Test reward expiration handling."""

    async def test_expired_reward_cannot_be_claimed(
        self, integrated_reward_service, test_session, test_user
    ):
        """
        Reward expires -> User cannot claim.

        Steps:
        1. Create expired UserReward
        2. Try to claim
        3. Assert: Claim fails with expired message
        """
        service = integrated_reward_service

        # Create reward
        reward = Reward(
            name="Expired Reward",
            reward_type=RewardType.BESITOS,
            reward_value={"amount": 50},
            is_active=True
        )
        test_session.add(reward)
        await test_session.flush()

        # Create expired UserReward
        user_reward = UserReward(
            user_id=test_user.user_id,
            reward_id=reward.id,
            status=RewardStatus.EXPIRED,
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        test_session.add(user_reward)
        await test_session.flush()

        # Try to claim
        success, msg, details = await service.claim_reward(
            test_user.user_id, reward.id
        )

        # Assert: Claim fails
        assert success is False
        assert msg == "reward_expired"

    async def test_claim_updates_user_reward_status(
        self, integrated_reward_service, test_session, test_user
    ):
        """
        User claims reward -> UserReward status updated to CLAIMED.

        Steps:
        1. Create unlocked UserReward
        2. Claim reward
        3. Assert: Status is CLAIMED
        4. Assert: claim_count incremented
        5. Assert: claimed_at timestamp set
        """
        service = integrated_reward_service

        # Create reward
        reward = Reward(
            name="Claimable Reward",
            reward_type=RewardType.BESITOS,
            reward_value={"amount": 50},
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

        # Refresh user_reward
        await test_session.refresh(user_reward)

        # Assert: Status is CLAIMED
        assert user_reward.status == RewardStatus.CLAIMED

        # Assert: claim_count incremented
        assert user_reward.claim_count == 1

        # Assert: claimed_at timestamp set
        assert user_reward.claimed_at is not None
