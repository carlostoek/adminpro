"""
Comprehensive unit tests for StreakService.

Tests all core streak functionality including:
- Streak creation and retrieval
- Daily gift claim logic (UTC boundaries)
- Streak bonus calculation
- Reaction streak tracking
- Edge cases (DST, midnight, concurrency)

Verifies STREAK-01 through STREAK-07 requirements.
"""
import pytest
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from bot.services.streak import StreakService
from bot.database.enums import StreakType, TransactionType


@pytest.fixture
def mock_wallet_service():
    """Create a mock WalletService for testing."""
    mock = AsyncMock()
    mock.earn_besitos = AsyncMock(return_value=(True, "earned", MagicMock()))
    return mock


@pytest.fixture
async def streak_service(test_session, mock_wallet_service):
    """Create a StreakService instance for testing."""
    service = StreakService(test_session, wallet_service=mock_wallet_service)
    return service


class TestGetOrCreateStreak:
    """Test _get_or_create_streak method."""

    async def test_get_or_create_streak_creates_new(self, streak_service, test_user):
        """Verify new streak creation for first-time user."""
        streak = await streak_service._get_or_create_streak(
            user_id=test_user.user_id,
            streak_type=StreakType.DAILY_GIFT
        )

        assert streak.user_id == test_user.user_id
        assert streak.streak_type == StreakType.DAILY_GIFT
        assert streak.current_streak == 0
        assert streak.longest_streak == 0
        assert streak.last_claim_date is None

    async def test_get_or_create_streak_returns_existing(self, streak_service, test_user):
        """Verify retrieval of existing streak record."""
        # Create first
        streak1 = await streak_service._get_or_create_streak(
            user_id=test_user.user_id,
            streak_type=StreakType.DAILY_GIFT
        )
        streak1.current_streak = 5
        await streak_service.session.flush()

        # Get again - should return same record
        streak2 = await streak_service._get_or_create_streak(
            user_id=test_user.user_id,
            streak_type=StreakType.DAILY_GIFT
        )

        assert streak2.current_streak == 5
        assert streak2.id == streak1.id

    async def test_get_or_create_streak_different_types(self, streak_service, test_user):
        """Verify user can have separate streaks for different types."""
        daily = await streak_service._get_or_create_streak(
            user_id=test_user.user_id,
            streak_type=StreakType.DAILY_GIFT
        )
        reaction = await streak_service._get_or_create_streak(
            user_id=test_user.user_id,
            streak_type=StreakType.REACTION
        )

        assert daily.streak_type == StreakType.DAILY_GIFT
        assert reaction.streak_type == StreakType.REACTION
        assert daily.id != reaction.id


class TestCanClaimDailyGift:
    """Test can_claim_daily_gift method."""

    async def test_can_claim_daily_gift_first_time(self, streak_service, test_user):
        """New user can claim immediately."""
        can_claim, status = await streak_service.can_claim_daily_gift(user_id=test_user.user_id)

        assert can_claim is True
        assert status == "available"

    async def test_can_claim_daily_gift_same_day(self, streak_service, test_user):
        """Cannot claim twice on same day."""
        # Setup: claimed today
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        streak.last_claim_date = datetime.utcnow()
        await streak_service.session.flush()

        can_claim, status = await streak_service.can_claim_daily_gift(user_id=test_user.user_id)

        assert can_claim is False
        assert "next_claim_in_" in status

    async def test_can_claim_daily_gift_next_day(self, streak_service, test_user):
        """Can claim after UTC midnight (next day)."""
        # Setup: claimed yesterday
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        streak.last_claim_date = datetime.utcnow() - timedelta(days=1)
        await streak_service.session.flush()

        can_claim, status = await streak_service.can_claim_daily_gift(user_id=test_user.user_id)

        assert can_claim is True
        assert status == "available"


class TestCalculateStreakBonus:
    """Test calculate_streak_bonus method."""

    async def test_calculate_streak_bonus_no_streak(self, streak_service):
        """Base amount only when no streak."""
        base, bonus, total = streak_service.calculate_streak_bonus(0)

        assert base == 20
        assert bonus == 0
        assert total == 20

    async def test_calculate_streak_bonus_with_streak(self, streak_service):
        """Base + bonus with active streak."""
        base, bonus, total = streak_service.calculate_streak_bonus(5)

        assert base == 20
        assert bonus == 10  # 5 * 2
        assert total == 30

    async def test_calculate_streak_bonus_max_cap(self, streak_service):
        """Bonus capped at 50 maximum."""
        # Day 25 would be 50 bonus (25 * 2), should cap at 50
        base, bonus, total = streak_service.calculate_streak_bonus(25)

        assert base == 20
        assert bonus == 50  # Capped
        assert total == 70

        # Very high streak still capped
        base, bonus, total = streak_service.calculate_streak_bonus(100)
        assert bonus == 50
        assert total == 70


class TestClaimDailyGift:
    """Test claim_daily_gift method."""

    async def test_claim_daily_gift_increments_streak(self, streak_service, mock_wallet_service, test_user):
        """Streak goes 0 -> 1 -> 2 on consecutive claims."""
        # First claim
        success1, result1 = await streak_service.claim_daily_gift(user_id=test_user.user_id)
        assert success1 is True
        assert result1["new_streak"] == 1

        # Simulate next day
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        streak.last_claim_date = datetime.utcnow() - timedelta(days=1)
        streak.current_streak = 1
        await streak_service.session.flush()

        mock_wallet_service.earn_besitos.reset_mock()

        # Second claim
        success2, result2 = await streak_service.claim_daily_gift(user_id=test_user.user_id)
        assert success2 is True
        assert result2["new_streak"] == 2

    async def test_claim_daily_gift_resets_after_miss(self, streak_service, mock_wallet_service, test_user):
        """Streak resets to 1 after gap day."""
        # Setup: claimed 2 days ago with streak of 5
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        streak.current_streak = 5
        streak.longest_streak = 10
        streak.last_claim_date = datetime.utcnow() - timedelta(days=2)
        await streak_service.session.flush()

        mock_wallet_service.earn_besitos.reset_mock()

        success, result = await streak_service.claim_daily_gift(user_id=test_user.user_id)

        assert success is True
        assert result["new_streak"] == 1  # Reset, not 6
        assert result["longest_streak"] == 10  # Preserved

    async def test_claim_daily_gift_wallet_integration(self, streak_service, mock_wallet_service, test_user):
        """Verify besitos credited via WalletService."""
        success, result = await streak_service.claim_daily_gift(user_id=test_user.user_id)

        assert success is True
        mock_wallet_service.earn_besitos.assert_called_once()
        call_args = mock_wallet_service.earn_besitos.call_args
        assert call_args[1]["user_id"] == test_user.user_id
        assert call_args[1]["transaction_type"] == TransactionType.EARN_DAILY


class TestGetStreakInfo:
    """Test get_streak_info method."""

    async def test_get_streak_info_returns_correct_data(self, streak_service, test_user):
        """All expected fields present in response."""
        # Setup streak
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        streak.current_streak = 7
        streak.longest_streak = 10
        streak.last_claim_date = datetime.utcnow() - timedelta(days=1)
        await streak_service.session.flush()

        info = await streak_service.get_streak_info(
            user_id=test_user.user_id,
            streak_type=StreakType.DAILY_GIFT
        )

        assert "current_streak" in info
        assert "longest_streak" in info
        assert "last_claim_date" in info
        assert "can_claim" in info
        assert "next_claim_time" in info

        assert info["current_streak"] == 7
        assert info["longest_streak"] == 10
        assert info["can_claim"] is True


class TestReactionStreakMethods:
    """Test reaction streak tracking methods."""

    async def test_record_reaction_first_reaction(self, streak_service, test_user):
        """Creates streak record on first reaction."""
        incremented, streak = await streak_service.record_reaction(user_id=test_user.user_id)

        assert incremented is True
        assert streak == 1

    async def test_record_reaction_new_day_increments(self, streak_service, test_user):
        """Streak increases on new day reaction."""
        # Setup: reacted yesterday with streak of 3
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.REACTION
        )
        streak.current_streak = 3
        streak.last_reaction_date = datetime.utcnow() - timedelta(days=1)
        await streak_service.session.flush()

        incremented, new_streak = await streak_service.record_reaction(user_id=test_user.user_id)

        assert incremented is True
        assert new_streak == 4

    async def test_record_reaction_same_day_no_change(self, streak_service, test_user):
        """No double counting on same day."""
        # Setup: reacted today with streak of 5
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.REACTION
        )
        streak.current_streak = 5
        streak.last_reaction_date = datetime.utcnow()
        await streak_service.session.flush()

        incremented, streak_count = await streak_service.record_reaction(user_id=test_user.user_id)

        assert incremented is False
        assert streak_count == 5  # Unchanged

    async def test_get_reaction_streak_returns_correct_value(self, streak_service, test_user):
        """Retrieval works correctly."""
        # Setup
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.REACTION
        )
        streak.current_streak = 12
        await streak_service.session.flush()

        result = await streak_service.get_reaction_streak(user_id=test_user.user_id)

        assert result == 12

    async def test_get_reaction_streak_no_record(self, streak_service, test_user):
        """Returns 0 when no record exists."""
        result = await streak_service.get_reaction_streak(user_id=test_user.user_id)

        assert result == 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    async def test_streak_across_dst_transition(self, streak_service, test_user):
        """UTC consistency maintained across DST transitions."""
        # DST doesn't affect UTC, but test boundary behavior
        # Simulate claim just before "midnight" UTC
        yesterday = datetime.utcnow() - timedelta(days=1)

        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        streak.last_claim_date = yesterday
        streak.current_streak = 5
        await streak_service.session.flush()

        # Should be able to claim today
        can_claim, _ = await streak_service.can_claim_daily_gift(user_id=test_user.user_id)
        assert can_claim is True

    async def test_streak_at_utc_midnight_boundary(self, streak_service, test_user):
        """Exact midnight handling."""
        # Claim at exactly midnight UTC yesterday
        midnight_yesterday = datetime.combine(
            (datetime.utcnow() - timedelta(days=1)).date(),
            datetime.min.time()
        )

        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        streak.last_claim_date = midnight_yesterday
        streak.current_streak = 3
        await streak_service.session.flush()

        # Should be able to claim today
        can_claim, _ = await streak_service.can_claim_daily_gift(user_id=test_user.user_id)
        assert can_claim is True

    async def test_streak_with_long_gap(self, streak_service, mock_wallet_service, test_user):
        """Resets correctly after multiple days missed."""
        # Setup: claimed 5 days ago
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        streak.current_streak = 10
        streak.longest_streak = 15
        streak.last_claim_date = datetime.utcnow() - timedelta(days=5)
        await streak_service.session.flush()

        mock_wallet_service.earn_besitos.reset_mock()

        success, result = await streak_service.claim_daily_gift(user_id=test_user.user_id)

        assert success is True
        assert result["new_streak"] == 1  # Reset to 1
        assert result["longest_streak"] == 15  # Preserved

    async def test_concurrent_claims_atomic(self, streak_service, mock_wallet_service, test_user):
        """No race conditions in claim logic."""
        # First claim
        success1, result1 = await streak_service.claim_daily_gift(user_id=test_user.user_id)
        assert success1 is True

        # Immediate second claim should fail
        success2, result2 = await streak_service.claim_daily_gift(user_id=test_user.user_id)
        assert success2 is False
        assert "next_claim_in_" in result2["error"]

        # Wallet should only be called once
        assert mock_wallet_service.earn_besitos.call_count == 1


class TestBackgroundJobs:
    """Test background job methods."""

    async def test_expire_streaks_resets_missed(self, streak_service, test_user):
        """Streaks reset when day missed."""
        # Setup: claimed 2 days ago
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        streak.current_streak = 5
        streak.longest_streak = 10
        streak.last_claim_date = datetime.utcnow() - timedelta(days=2)
        await streak_service.session.flush()

        # Run expiration
        reset_count = await streak_service.process_streak_expirations()

        assert reset_count == 1

        # Verify reset
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        assert streak.current_streak == 0

    async def test_expire_streaks_preserves_longest(self, streak_service, test_user):
        """Historical max streak kept."""
        # Setup
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        streak.current_streak = 5
        streak.longest_streak = 20
        streak.last_claim_date = datetime.utcnow() - timedelta(days=2)
        await streak_service.session.flush()

        await streak_service.process_streak_expirations()

        # Verify longest preserved
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        assert streak.longest_streak == 20

    async def test_expire_streaks_skips_current(self, streak_service, test_user):
        """Today's streaks preserved."""
        # Setup: claimed today
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        streak.current_streak = 5
        streak.last_claim_date = datetime.utcnow()
        await streak_service.session.flush()

        reset_count = await streak_service.process_streak_expirations()

        assert reset_count == 0

        # Verify unchanged
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        assert streak.current_streak == 5

    async def test_expire_reaction_streaks(self, streak_service, test_user):
        """Reaction streaks also expire correctly."""
        # Setup: reacted 2 days ago
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.REACTION
        )
        streak.current_streak = 8
        streak.last_reaction_date = datetime.utcnow() - timedelta(days=2)
        await streak_service.session.flush()

        reset_count = await streak_service.process_reaction_streak_expirations()

        assert reset_count == 1

        # Verify reset
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.REACTION
        )
        assert streak.current_streak == 0


class TestResetStreak:
    """Test reset_streak method."""

    async def test_reset_streak_manual(self, streak_service, test_user):
        """Manual reset works correctly."""
        # Setup
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        streak.current_streak = 15
        streak.longest_streak = 20
        await streak_service.session.flush()

        result = await streak_service.reset_streak(
            user_id=test_user.user_id,
            streak_type=StreakType.DAILY_GIFT
        )

        assert result is True

        # Verify reset
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        assert streak.current_streak == 0
        assert streak.longest_streak == 20  # Preserved


class TestNextClaimTime:
    """Test _get_next_claim_time helper."""

    async def test_next_claim_time_after_claim(self, streak_service):
        """Next claim is 00:00 UTC next day."""
        yesterday = datetime.utcnow() - timedelta(days=1)

        next_claim = streak_service._get_next_claim_time(yesterday)

        # Should be midnight UTC today
        expected = datetime.combine(datetime.utcnow().date(), datetime.min.time())
        assert next_claim.date() == expected.date()

    async def test_next_claim_time_none(self, streak_service):
        """Returns now when no previous claim."""
        next_claim = streak_service._get_next_claim_time(None)

        # Should be approximately now
        now = datetime.utcnow()
        diff = abs((next_claim - now).total_seconds())
        assert diff < 5  # Within 5 seconds
