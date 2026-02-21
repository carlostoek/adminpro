"""
Integration tests for Daily Gift flow.

Tests the complete flow from claim to wallet credit, verifying:
- End-to-end daily gift claiming
- WalletService integration for besitos credit
- Streak persistence across sessions
- Double-claim prevention

Verifies STREAK-01 through STREAK-07 requirements.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import select

from bot.services.streak import StreakService
from bot.services.wallet import WalletService
from bot.database.enums import StreakType, TransactionType
from bot.database.models import UserStreak, UserGamificationProfile, Transaction


@pytest.fixture
async def streak_service_with_wallet(test_session):
    """Create a StreakService with real WalletService integration."""
    wallet_service = WalletService(test_session)
    service = StreakService(test_session, wallet_service=wallet_service)
    return service


class TestDailyGiftFullFlow:
    """Test complete daily gift flow end-to-end."""

    async def test_daily_gift_full_flow(self, streak_service_with_wallet, test_session, test_user):
        """Claim -> verify balance -> verify streak."""
        # Initial state - no streak, no balance
        initial_streak = await streak_service_with_wallet.get_streak_info(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        assert initial_streak["current_streak"] == 0
        assert initial_streak["can_claim"] is True

        # Claim daily gift
        success, result = await streak_service_with_wallet.claim_daily_gift(test_user.user_id)

        # Verify claim success
        assert success is True
        assert result["success"] is True
        assert result["base_amount"] == 20
        assert result["streak_bonus"] == 2  # First day: streak 1 * 2 = 2
        assert result["total"] == 22
        assert result["new_streak"] == 1

        # Verify streak updated
        streak_info = await streak_service_with_wallet.get_streak_info(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        assert streak_info["current_streak"] == 1
        assert streak_info["can_claim"] is False  # Already claimed today

        # Verify wallet balance updated via WalletService
        wallet_result = await test_session.execute(
            select(UserGamificationProfile).where(
                UserGamificationProfile.user_id == test_user.user_id
            )
        )
        profile = wallet_result.scalar_one_or_none()
        assert profile is not None
        assert profile.balance == 22  # 20 base + 2 bonus

        # Verify transaction recorded
        tx_result = await test_session.execute(
            select(Transaction).where(
                Transaction.user_id == test_user.user_id,
                Transaction.type == TransactionType.EARN_DAILY
            )
        )
        transaction = tx_result.scalar_one_or_none()
        assert transaction is not None
        assert transaction.amount == 22
        assert "streak_day" in (transaction.transaction_metadata or {})

    async def test_daily_gift_wallet_integration(self, streak_service_with_wallet, test_session, test_user):
        """Verify besitos credited via WalletService."""
        # Claim
        success, result = await streak_service_with_wallet.claim_daily_gift(test_user.user_id)
        assert success is True

        # Verify WalletService credited correctly
        wallet_result = await test_session.execute(
            select(UserGamificationProfile).where(
                UserGamificationProfile.user_id == test_user.user_id
            )
        )
        profile = wallet_result.scalar_one_or_none()
        assert profile is not None
        assert profile.balance == 22  # 20 base + 2 bonus
        assert profile.total_earned == 22

        # Verify transaction audit trail
        tx_result = await test_session.execute(
            select(Transaction).where(
                Transaction.user_id == test_user.user_id
            )
        )
        transactions = tx_result.scalars().all()
        assert len(transactions) == 1
        assert transactions[0].type == TransactionType.EARN_DAILY
        assert transactions[0].amount == 22

    async def test_daily_gift_cannot_claim_twice(self, streak_service_with_wallet, test_session, test_user):
        """Second claim rejected on same day."""
        # First claim
        success1, result1 = await streak_service_with_wallet.claim_daily_gift(test_user.user_id)
        assert success1 is True

        # Second claim should fail
        success2, result2 = await streak_service_with_wallet.claim_daily_gift(test_user.user_id)
        assert success2 is False
        assert result2["success"] is False
        assert "next_claim_in_" in result2["error"]

        # Verify balance only increased once
        wallet_result = await test_session.execute(
            select(UserGamificationProfile).where(
                UserGamificationProfile.user_id == test_user.user_id
            )
        )
        profile = wallet_result.scalar_one_or_none()
        assert profile.balance == 22  # Not 44

        # Verify only one transaction
        tx_result = await test_session.execute(
            select(Transaction).where(
                Transaction.user_id == test_user.user_id
            )
        )
        transactions = tx_result.scalars().all()
        assert len(transactions) == 1

    async def test_daily_gift_streak_persists(self, streak_service_with_wallet, test_session, test_user):
        """Streak survives across sessions (simulated)."""
        # Day 1: Claim
        success1, result1 = await streak_service_with_wallet.claim_daily_gift(test_user.user_id)
        assert success1 is True
        assert result1["new_streak"] == 1

        # Simulate "next day" by updating last_claim_date to yesterday
        streak_result = await test_session.execute(
            select(UserStreak).where(
                UserStreak.user_id == test_user.user_id,
                UserStreak.streak_type == StreakType.DAILY_GIFT
            )
        )
        streak = streak_result.scalar_one()
        streak.last_claim_date = datetime.utcnow() - timedelta(days=1)
        streak.current_streak = 1
        await test_session.commit()

        # Create fresh service (simulating new session)
        fresh_wallet = WalletService(test_session)
        fresh_service = StreakService(test_session, wallet_service=fresh_wallet)

        # Day 2: Claim again
        success2, result2 = await fresh_service.claim_daily_gift(test_user.user_id)
        assert success2 is True
        assert result2["new_streak"] == 2  # Streak continued
        assert result2["streak_bonus"] == 4  # 2 * 2 = 4 bonus
        assert result2["total"] == 24  # 20 + 4

        # Verify streak persisted in database
        streak_info = await fresh_service.get_streak_info(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        assert streak_info["current_streak"] == 2
        assert streak_info["longest_streak"] == 2


class TestDailyGiftStreakProgression:
    """Test streak progression over multiple days."""

    async def test_streak_progression_three_days(self, streak_service_with_wallet, test_session, test_user):
        """Streak progresses 1 -> 2 -> 3 over three days."""
        # Day 1
        success, result = await streak_service_with_wallet.claim_daily_gift(test_user.user_id)
        assert result["new_streak"] == 1
        assert result["total"] == 22  # 20 base + 2 bonus (streak 1 * 2)

        # Simulate Day 2
        streak_result = await test_session.execute(
            select(UserStreak).where(
                UserStreak.user_id == test_user.user_id,
                UserStreak.streak_type == StreakType.DAILY_GIFT
            )
        )
        streak = streak_result.scalar_one()
        streak.last_claim_date = datetime.utcnow() - timedelta(days=1)
        streak.current_streak = 1
        await test_session.commit()

        success, result = await streak_service_with_wallet.claim_daily_gift(test_user.user_id)
        assert result["new_streak"] == 2
        assert result["streak_bonus"] == 4  # 2 * 2
        assert result["total"] == 24

        # Simulate Day 3
        streak_result = await test_session.execute(
            select(UserStreak).where(
                UserStreak.user_id == test_user.user_id,
                UserStreak.streak_type == StreakType.DAILY_GIFT
            )
        )
        streak = streak_result.scalar_one()
        streak.last_claim_date = datetime.utcnow() - timedelta(days=1)
        streak.current_streak = 2
        await test_session.commit()

        success, result = await streak_service_with_wallet.claim_daily_gift(test_user.user_id)
        assert result["new_streak"] == 3
        assert result["streak_bonus"] == 6  # 3 * 2
        assert result["total"] == 26

        # Verify total balance
        wallet_result = await test_session.execute(
            select(UserGamificationProfile).where(
                UserGamificationProfile.user_id == test_user.user_id
            )
        )
        profile = wallet_result.scalar_one()
        assert profile.balance == 22 + 24 + 26  # 72 total (day 1: 22, day 2: 24, day 3: 26)

    async def test_streak_bonus_capping(self, streak_service_with_wallet, test_session, test_user):
        """Bonus caps at 50 besitos (day 25+)."""
        # Setup: Day 30 streak
        streak_result = await test_session.execute(
            select(UserStreak).where(
                UserStreak.user_id == test_user.user_id,
                UserStreak.streak_type == StreakType.DAILY_GIFT
            )
        )
        streak = streak_result.scalar_one_or_none()
        if not streak:
            streak = UserStreak(
                user_id=test_user.user_id,
                streak_type=StreakType.DAILY_GIFT,
                current_streak=30,
                longest_streak=30
            )
            test_session.add(streak)
        else:
            streak.current_streak = 30
            streak.longest_streak = 30
        streak.last_claim_date = datetime.utcnow() - timedelta(days=1)
        await test_session.commit()

        # Claim
        success, result = await streak_service_with_wallet.claim_daily_gift(test_user.user_id)
        assert success is True
        assert result["new_streak"] == 31
        assert result["streak_bonus"] == 50  # Capped, not 62
        assert result["total"] == 70  # 20 + 50


class TestDailyGiftWithMissedDays:
    """Test streak behavior when days are missed."""

    async def test_streak_resets_after_miss(self, streak_service_with_wallet, test_session, test_user):
        """Streak resets to 1 after missing a day."""
        # Setup: Had streak of 10, missed yesterday
        streak = UserStreak(
            user_id=test_user.user_id,
            streak_type=StreakType.DAILY_GIFT,
            current_streak=10,
            longest_streak=15,
            last_claim_date=datetime.utcnow() - timedelta(days=2)
        )
        test_session.add(streak)
        await test_session.commit()

        # Claim today
        success, result = await streak_service_with_wallet.claim_daily_gift(test_user.user_id)
        assert success is True
        assert result["new_streak"] == 1  # Reset, not 11
        assert result["streak_bonus"] == 2  # 1 * 2 = 2
        assert result["longest_streak"] == 15  # Preserved

    async def test_streak_resets_after_long_gap(self, streak_service_with_wallet, test_session, test_user):
        """Streak resets after multiple days missed."""
        # Setup: Had streak of 20, missed 5 days
        streak = UserStreak(
            user_id=test_user.user_id,
            streak_type=StreakType.DAILY_GIFT,
            current_streak=20,
            longest_streak=25,
            last_claim_date=datetime.utcnow() - timedelta(days=5)
        )
        test_session.add(streak)
        await test_session.commit()

        # Claim today
        success, result = await streak_service_with_wallet.claim_daily_gift(test_user.user_id)
        assert success is True
        assert result["new_streak"] == 1  # Reset
        assert result["longest_streak"] == 25  # Preserved


class TestDailyGiftEdgeCases:
    """Test edge cases in daily gift flow."""

    async def test_claim_at_exact_midnight(self, streak_service_with_wallet, test_session, test_user):
        """Claim at exactly 00:00 UTC boundary."""
        # Setup: Claimed at exactly midnight yesterday
        midnight_yesterday = datetime.combine(
            (datetime.utcnow() - timedelta(days=1)).date(),
            datetime.min.time()
        )
        streak = UserStreak(
            user_id=test_user.user_id,
            streak_type=StreakType.DAILY_GIFT,
            current_streak=5,
            longest_streak=10,
            last_claim_date=midnight_yesterday
        )
        test_session.add(streak)
        await test_session.commit()

        # Should be able to claim today
        can_claim, status = await streak_service_with_wallet.can_claim_daily_gift(test_user.user_id)
        assert can_claim is True

        # Claim
        success, result = await streak_service_with_wallet.claim_daily_gift(test_user.user_id)
        assert success is True
        assert result["new_streak"] == 6  # Continued

    async def test_concurrent_claims_prevented(self, streak_service_with_wallet, test_session, test_user):
        """Double claim on same day prevented."""
        # First claim
        success1, result1 = await streak_service_with_wallet.claim_daily_gift(test_user.user_id)
        assert success1 is True

        # Try second claim immediately
        success2, result2 = await streak_service_with_wallet.claim_daily_gift(test_user.user_id)
        assert success2 is False

        # Verify only one transaction in database
        tx_result = await test_session.execute(
            select(Transaction).where(
                Transaction.user_id == test_user.user_id
            )
        )
        transactions = tx_result.scalars().all()
        assert len(transactions) == 1

    async def test_wallet_created_if_not_exists(self, streak_service_with_wallet, test_session, test_user):
        """Wallet profile created on first claim if didn't exist."""
        # Verify no profile exists
        wallet_result = await test_session.execute(
            select(UserGamificationProfile).where(
                UserGamificationProfile.user_id == test_user.user_id
            )
        )
        profile = wallet_result.scalar_one_or_none()
        assert profile is None

        # Claim
        success, result = await streak_service_with_wallet.claim_daily_gift(test_user.user_id)
        assert success is True

        # Profile should now exist
        wallet_result = await test_session.execute(
            select(UserGamificationProfile).where(
                UserGamificationProfile.user_id == test_user.user_id
            )
        )
        profile = wallet_result.scalar_one()
        assert profile.balance == 22  # 20 base + 2 bonus
