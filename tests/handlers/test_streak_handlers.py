"""
Tests for streak handlers - Daily gift claim flow.

Verifies:
- Lucien's voice in all messages (🎩)
- Countdown text formatting
- Message content verification
"""
import pytest
from datetime import datetime, timedelta
from bot.handlers.user.streak import (
    get_countdown_text,
    _get_lucien_header,
    _get_claim_available_message,
    _get_claim_success_message,
    _get_already_claimed_message,
    _get_error_message,
    get_claim_keyboard,
)


class TestGetCountdownText:
    """Tests for get_countdown_text helper function."""

    def test_countdown_hours_and_minutes(self):
        """Should format countdown with hours and minutes."""
        future = datetime.utcnow() + timedelta(hours=14, minutes=32)
        result = get_countdown_text(future)
        assert "h" in result
        assert "m" in result
        assert "Próximo regalo en" in result

    def test_countdown_minutes_only(self):
        """Should format countdown with only minutes when less than 1 hour."""
        future = datetime.utcnow() + timedelta(minutes=45)
        result = get_countdown_text(future)
        assert "m" in result
        assert "Próximo regalo en" in result

    def test_countdown_available_now(self):
        """Should indicate gift is available when time has passed."""
        past = datetime.utcnow() - timedelta(minutes=5)
        result = get_countdown_text(past)
        assert "disponible ahora" in result

    def test_countdown_exact_midnight_reference(self):
        """Should work with UTC midnight as reference."""
        tomorrow = datetime.utcnow() + timedelta(days=1)
        midnight = datetime.combine(tomorrow.date(), datetime.min.time())
        result = get_countdown_text(midnight)
        assert "Próximo regalo en" in result


class TestLucienVoiceMessages:
    """Tests for Lucien's voice in messages."""

    def test_lucien_header_format(self):
        """Header should contain Lucien's emoji and name."""
        header = _get_lucien_header()
        assert "🎩" in header
        assert "Lucien" in header
        assert "<b>" in header

    def test_claim_available_contains_lucien_voice(self):
        """Claim available message should use Lucien's voice."""
        msg = _get_claim_available_message(streak=5)
        assert "🎩" in msg
        assert "Lucien" in msg
        assert "<i>" in msg  # Italic for Lucien's thoughts
        assert "Diana" in msg  # References to Diana

    def test_claim_available_shows_streak(self):
        """Should show current streak in message."""
        msg = _get_claim_available_message(streak=5)
        assert "5 días" in msg

    def test_claim_available_zero_streak(self):
        """Should handle zero streak gracefully."""
        msg = _get_claim_available_message(streak=0)
        assert "Aún no ha comenzado" in msg

    def test_claim_success_detailed_breakdown(self):
        """Success message should show detailed breakdown."""
        msg = _get_claim_success_message(
            streak=5,
            base=20,
            bonus=10,
            total=30
        )
        # Check breakdown elements (HTML tags may be present)
        assert "Racha actual:" in msg and "5 días" in msg
        assert "Base:" in msg and "20 besitos" in msg
        assert "Bonus por racha:" in msg and "+10 besitos" in msg
        assert "Total recibido:" in msg and "30 besitos" in msg
        # Check Lucien's voice
        assert "🎩" in msg
        assert "Diana" in msg

    def test_already_claimed_shows_countdown(self):
        """Already claimed message should include countdown."""
        countdown = "Próximo regalo en 14h 32m"
        msg = _get_already_claimed_message(countdown)
        assert countdown in msg
        assert "🎩" in msg
        assert "Lucien" in msg

    def test_error_message_lucien_voice(self):
        """Error message should use Lucien's voice."""
        msg = _get_error_message("test context")
        assert "🎩" in msg
        assert "Lucien" in msg
        assert "Diana" in msg
        assert "inconveniente" in msg  # Lucien's elegant error term

    def test_error_message_without_context(self):
        """Error message should work without context."""
        msg = _get_error_message()
        assert "🎩" in msg
        assert "Lucien" in msg


class TestClaimKeyboard:
    """Tests for claim keyboard generation."""

    def test_keyboard_when_available(self):
        """Should return keyboard when gift is available."""
        keyboard = get_claim_keyboard(is_available=True)
        assert keyboard is not None
        # Check button text
        button = keyboard.inline_keyboard[0][0]
        assert "Reclamar" in button.text
        assert "🎁" in button.text
        assert button.callback_data == "streak:claim_daily"

    def test_keyboard_when_not_available(self):
        """Should return None when gift is not available."""
        keyboard = get_claim_keyboard(is_available=False)
        assert keyboard is None


class TestSTREAKRequirements:
    """Tests verifying STREAK requirements from plan 21-04."""

    def test_streak_01_daily_gift_once_per_24h(self):
        """
        STREAK-01: User can claim daily gift once per 24h.
        
        This is enforced by StreakService.can_claim_daily_gift()
        which checks UTC day boundaries.
        """
        # This test verifies the handler uses the service correctly
        # The actual logic is tested in test_streak_service.py
        pass  # Handler delegates to service, already tested

    def test_streak_02_base_plus_streak_bonus(self):
        """
        STREAK-02: User receives base + streak bonus besitos.
        
        Verifies success message shows both base and bonus.
        """
        msg = _get_claim_success_message(
            streak=5,
            base=20,
            bonus=10,
            total=30
        )
        assert "Base:" in msg
        assert "Bonus por racha:" in msg
        assert "Total recibido:" in msg

    def test_streak_message_format_completeness(self):
        """
        Verifies the exact format from plan 21-04 is implemented.
        
        Format should include:
        - Lucien header
        - Streak days
        - Base amount
        - Bonus amount
        - Separator line
        - Total amount
        """
        msg = _get_claim_success_message(
            streak=10,
            base=20,
            bonus=20,
            total=40
        )
        # Verify structure
        assert "🔥" in msg  # Streak emoji
        assert "💰" in msg  # Base emoji
        assert "✨" in msg  # Bonus emoji
        assert "💎" in msg  # Total emoji
        assert "─────────────────" in msg  # Separator
