"""
Tests for StreakService - Core streak tracking functionality.

Verifies:
- Streak creation and retrieval
- Daily gift claim availability (UTC boundaries)
- Streak bonus calculation (base + capped bonus)
- Streak increment on consecutive days
- Streak reset on missed days
- WalletService integration for besitos credit
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

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


class TestStreakServiceCreation:
    """Test StreakService initialization and basic properties."""

    async def test_service_creation_with_wallet(self, test_session, mock_wallet_service):
        """Test that StreakService can be created with wallet service."""
        service = StreakService(test_session, wallet_service=mock_wallet_service)
        assert service.session is test_session
        assert service.wallet_service is mock_wallet_service

    async def test_service_creation_without_wallet(self, test_session):
        """Test that StreakService can be created without wallet service."""
        service = StreakService(test_session, wallet_service=None)
        assert service.session is test_session
        assert service.wallet_service is None

    async def test_service_constants(self, test_session):
        """Test that service has correct default constants."""
        service = StreakService(test_session)
        assert service.BASE_BESITOS == 20
        assert service.STREAK_BONUS_PER_DAY == 2
        assert service.STREAK_BONUS_MAX == 50


class TestGetOrCreateStreak:
    """Test _get_or_create_streak method."""

    async def test_create_new_streak(self, streak_service, test_user):
        """Test creating a new streak record."""
        streak = await streak_service._get_or_create_streak(
            user_id=test_user.user_id,
            streak_type=StreakType.DAILY_GIFT
        )

        assert streak.user_id == test_user.user_id
        assert streak.streak_type == StreakType.DAILY_GIFT
        assert streak.current_streak == 0
        assert streak.longest_streak == 0
        assert streak.last_claim_date is None

    async def test_get_existing_streak(self, streak_service, test_user):
        """Test retrieving an existing streak record."""
        # Create first
        streak1 = await streak_service._get_or_create_streak(
            user_id=test_user.user_id,
            streak_type=StreakType.DAILY_GIFT
        )
        streak1.current_streak = 5
        await streak_service.session.flush()

        # Get again
        streak2 = await streak_service._get_or_create_streak(
            user_id=test_user.user_id,
            streak_type=StreakType.DAILY_GIFT
        )

        assert streak2.current_streak == 5
        assert streak2.id == streak1.id

    async def test_different_types_same_user(self, streak_service, test_user):
        """Test that user can have different streak types."""
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


class TestGetUtcDate:
    """Test _get_utc_date helper method."""

    async def test_get_utc_date_now(self, streak_service):
        """Test getting UTC date for current time."""
        from datetime import date as date_cls
        date = streak_service._get_utc_date()
        assert isinstance(date, date_cls)
        # Should be today's date in UTC
        assert date == datetime.utcnow().date()

    async def test_get_utc_date_from_datetime(self, streak_service):
        """Test getting UTC date from specific datetime."""
        test_dt = datetime(2024, 1, 15, 12, 30, 45)
        date = streak_service._get_utc_date(test_dt)
        assert date.year == 2024
        assert date.month == 1
        assert date.day == 15


class TestCanClaimDailyGift:
    """Test can_claim_daily_gift method."""

    async def test_can_claim_new_user(self, streak_service, test_user):
        """Test that new user can claim immediately."""
        can_claim, status = await streak_service.can_claim_daily_gift(user_id=test_user.user_id)
        assert can_claim is True
        assert status == "available"

    async def test_can_claim_next_day(self, streak_service, test_user):
        """Test that user can claim on next day."""
        # Create streak with yesterday's claim
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        streak.last_claim_date = datetime.utcnow() - timedelta(days=1)
        await streak_service.session.flush()

        can_claim, status = await streak_service.can_claim_daily_gift(user_id=test_user.user_id)
        assert can_claim is True
        assert status == "available"

    async def test_cannot_claim_same_day(self, streak_service, test_user):
        """Test that user cannot claim twice on same day."""
        # Create streak with today's claim
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        streak.last_claim_date = datetime.utcnow()
        await streak_service.session.flush()

        can_claim, status = await streak_service.can_claim_daily_gift(user_id=test_user.user_id)
        assert can_claim is False
        assert "next_claim_in_" in status

    async def test_returns_time_until_next_claim(self, streak_service, test_user):
        """Test that status includes time until next claim."""
        # Create streak with recent claim (1 hour ago)
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        streak.last_claim_date = datetime.utcnow() - timedelta(hours=1)
        await streak_service.session.flush()

        can_claim, status = await streak_service.can_claim_daily_gift(user_id=test_user.user_id)
        assert can_claim is False
        # Should be approximately 23 hours remaining
        assert "next_claim_in_" in status
        assert "h_" in status


class TestCalculateStreakBonus:
    """Test calculate_streak_bonus method."""

    async def test_base_calculation(self, streak_service):
        """Test base amount is always 20."""
        base, bonus, total = streak_service.calculate_streak_bonus(0)
        assert base == 20
        assert total == 20 + bonus

    async def test_streak_day_1(self, streak_service):
        """Test bonus for streak day 1."""
        base, bonus, total = streak_service.calculate_streak_bonus(1)
        assert base == 20
        assert bonus == 2  # 1 * 2
        assert total == 22

    async def test_streak_day_5(self, streak_service):
        """Test bonus for streak day 5."""
        base, bonus, total = streak_service.calculate_streak_bonus(5)
        assert base == 20
        assert bonus == 10  # 5 * 2
        assert total == 30

    async def test_streak_bonus_cap(self, streak_service):
        """Test that bonus caps at 50."""
        # Day 25 would be 50 bonus (25 * 2), should cap at 50
        base, bonus, total = streak_service.calculate_streak_bonus(25)
        assert base == 20
        assert bonus == 50  # Capped, not 50
        assert total == 70

    async def test_streak_day_100(self, streak_service):
        """Test that very high streaks still cap at 50."""
        base, bonus, total = streak_service.calculate_streak_bonus(100)
        assert base == 20
        assert bonus == 50  # Still capped at 50
        assert total == 70


class TestClaimDailyGift:
    """Test claim_daily_gift method."""

    async def test_claim_first_time(self, streak_service, mock_wallet_service, test_user):
        """Test first claim creates streak of 1."""
        success, result = await streak_service.claim_daily_gift(user_id=test_user.user_id)

        assert success is True
        assert result["success"] is True
        assert result["new_streak"] == 1
        assert result["base_amount"] == 20
        assert result["total"] == 22  # 20 + 2

        # Verify wallet was called
        mock_wallet_service.earn_besitos.assert_called_once()
        call_args = mock_wallet_service.earn_besitos.call_args
        assert call_args[1]["user_id"] == test_user.user_id
        assert call_args[1]["amount"] == 22
        assert call_args[1]["transaction_type"] == TransactionType.EARN_DAILY

    async def test_claim_consecutive_day(self, streak_service, mock_wallet_service, test_user):
        """Test claim on consecutive day increments streak."""
        # Setup: claimed yesterday with streak of 3
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        streak.current_streak = 3
        streak.longest_streak = 3
        streak.last_claim_date = datetime.utcnow() - timedelta(days=1)
        await streak_service.session.flush()

        # Reset mock
        mock_wallet_service.earn_besitos.reset_mock()

        success, result = await streak_service.claim_daily_gift(user_id=test_user.user_id)

        assert success is True
        assert result["new_streak"] == 4
        assert result["longest_streak"] == 4  # Updated
        # Bonus: min(4 * 2, 50) = 8
        assert result["streak_bonus"] == 8
        assert result["total"] == 28  # 20 + 8

    async def test_claim_resets_after_missed_day(self, streak_service, mock_wallet_service, test_user):
        """Test that missed day resets streak to 1."""
        # Setup: claimed 2 days ago with streak of 5
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        streak.current_streak = 5
        streak.longest_streak = 10
        streak.last_claim_date = datetime.utcnow() - timedelta(days=2)
        await streak_service.session.flush()

        # Reset mock
        mock_wallet_service.earn_besitos.reset_mock()

        success, result = await streak_service.claim_daily_gift(user_id=test_user.user_id)

        assert success is True
        assert result["new_streak"] == 1  # Reset, not 6
        assert result["longest_streak"] == 10  # Preserved
        assert result["streak_bonus"] == 2  # min(1 * 2, 50)

    async def test_cannot_claim_twice_same_day(self, streak_service, mock_wallet_service, test_user):
        """Test that claiming twice on same day fails."""
        # Setup: claimed today
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.DAILY_GIFT
        )
        streak.current_streak = 5
        streak.last_claim_date = datetime.utcnow()
        await streak_service.session.flush()

        success, result = await streak_service.claim_daily_gift(user_id=test_user.user_id)

        assert success is False
        assert result["success"] is False
        # When already claimed today, returns "next_claim_in_Xh_Ym"
        assert "next_claim_in_" in result["error"]
        assert result["new_streak"] == 0  # Not updated (default for failed claim)

        # Wallet should not be called
        mock_wallet_service.earn_besitos.assert_not_called()

    async def test_claim_without_wallet_service(self, test_session, test_user):
        """Test claim behavior when wallet service is None."""
        service = StreakService(test_session, wallet_service=None)

        success, result = await service.claim_daily_gift(user_id=test_user.user_id)

        # Should still succeed (just skip the wallet call)
        assert success is True
        assert result["success"] is True
        assert result["new_streak"] == 1


class TestGetStreakInfo:
    """Test get_streak_info method."""

    async def test_get_info_new_user(self, streak_service, test_user):
        """Test getting info for user without streak."""
        info = await streak_service.get_streak_info(
            user_id=test_user.user_id,
            streak_type=StreakType.DAILY_GIFT
        )

        assert info["current_streak"] == 0
        assert info["longest_streak"] == 0
        assert info["last_claim_date"] is None
        assert info["can_claim"] is True
        assert info["next_claim_time"] is not None

    async def test_get_info_existing_streak(self, streak_service, test_user):
        """Test getting info for user with existing streak."""
        # Setup
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

        assert info["current_streak"] == 7
        assert info["longest_streak"] == 10
        assert info["can_claim"] is True  # Can claim today
        assert info["next_claim_time"] is not None

    async def test_get_info_reaction_type(self, streak_service, test_user):
        """Test getting info for reaction streak type."""
        info = await streak_service.get_streak_info(
            user_id=test_user.user_id,
            streak_type=StreakType.REACTION
        )

        assert info["current_streak"] == 0
        assert info["longest_streak"] == 0
        # Reaction streak doesn't use can_claim logic
        assert "can_claim" in info


class TestResetStreak:
    """Test reset_streak method."""

    async def test_reset_existing_streak(self, streak_service, test_user):
        """Test resetting an existing streak."""
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

    async def test_reset_nonexistent_streak(self, streak_service, test_user):
        """Test resetting a streak that doesn't exist."""
        # Use a non-existent user_id
        result = await streak_service.reset_streak(
            user_id=999999,
            streak_type=StreakType.DAILY_GIFT
        )

        assert result is False

    async def test_reset_reaction_streak(self, streak_service, test_user):
        """Test resetting a reaction streak."""
        # Setup
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.REACTION
        )
        streak.current_streak = 30
        streak.longest_streak = 45
        await streak_service.session.flush()

        result = await streak_service.reset_streak(
            user_id=test_user.user_id,
            streak_type=StreakType.REACTION
        )

        assert result is True

        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.REACTION
        )
        assert streak.current_streak == 0
        assert streak.longest_streak == 45  # Preserved


class TestUpdateReactionStreak:
    """Test update_reaction_streak method."""

    async def test_first_reaction(self, streak_service, test_user):
        """Test first reaction sets streak to 1."""
        incremented, streak = await streak_service.update_reaction_streak(user_id=test_user.user_id)

        assert incremented is True
        assert streak == 1

    async def test_reaction_same_day(self, streak_service, test_user):
        """Test reaction on same day doesn't increment."""
        # Setup: reacted today
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.REACTION
        )
        streak.current_streak = 5
        streak.last_reaction_date = datetime.utcnow()
        await streak_service.session.flush()

        incremented, streak_count = await streak_service.update_reaction_streak(user_id=test_user.user_id)

        assert incremented is False
        assert streak_count == 5  # Unchanged

    async def test_reaction_consecutive_day(self, streak_service, test_user):
        """Test reaction on consecutive day increments streak."""
        # Setup: reacted yesterday
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.REACTION
        )
        streak.current_streak = 10
        streak.longest_streak = 10
        streak.last_reaction_date = datetime.utcnow() - timedelta(days=1)
        await streak_service.session.flush()

        incremented, streak_count = await streak_service.update_reaction_streak(user_id=test_user.user_id)

        assert incremented is True
        assert streak_count == 11

        # Verify longest was updated
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.REACTION
        )
        assert streak.longest_streak == 11

    async def test_reaction_after_missed_day(self, streak_service, test_user):
        """Test reaction after missed day resets to 1."""
        # Setup: reacted 2 days ago
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.REACTION
        )
        streak.current_streak = 20
        streak.longest_streak = 25
        streak.last_reaction_date = datetime.utcnow() - timedelta(days=2)
        await streak_service.session.flush()

        incremented, streak_count = await streak_service.update_reaction_streak(user_id=test_user.user_id)

        assert incremented is True  # Still increments from 0 to 1
        assert streak_count == 1  # Reset

        # Verify longest was preserved
        streak = await streak_service._get_or_create_streak(
            test_user.user_id, StreakType.REACTION
        )
        assert streak.longest_streak == 25


class TestServiceContainerIntegration:
    """Test integration with ServiceContainer."""

    async def test_container_has_streak_property(self, test_session, mock_bot):
        """Test that ServiceContainer exposes streak property."""
        from bot.services.container import ServiceContainer

        container = ServiceContainer(test_session, mock_bot)

        # Access streak property (should lazy load)
        streak_service = container.streak

        assert streak_service is not None
        assert isinstance(streak_service, StreakService)

    async def test_container_streak_in_loaded_services(self, test_session, mock_bot):
        """Test that streak appears in get_loaded_services after access."""
        from bot.services.container import ServiceContainer

        container = ServiceContainer(test_session, mock_bot)

        # Initially not loaded
        loaded = container.get_loaded_services()
        assert "streak" not in loaded

        # Access to trigger lazy load
        _ = container.streak

        # Now should be loaded
        loaded = container.get_loaded_services()
        assert "streak" in loaded

    async def test_container_injects_wallet_service(self, test_session, mock_bot):
        """Test that container injects wallet service into streak service."""
        from bot.services.container import ServiceContainer

        container = ServiceContainer(test_session, mock_bot)

        # Access both to trigger lazy loading with injection
        wallet = container.wallet
        streak = container.streak

        assert streak.wallet_service is wallet
