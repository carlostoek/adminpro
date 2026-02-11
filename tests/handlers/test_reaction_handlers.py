"""
Integration tests for reaction handlers.

Tests the full flow from callback query to reaction recording.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from bot.handlers.user.reactions import (
    handle_reaction_callback,
    _get_content_category,
    _handle_success,
    _handle_failure
)
from bot.database.enums import ContentCategory


@pytest.fixture
def mock_callback():
    """Create a mock callback query."""
    callback = MagicMock()
    callback.data = "react:-1001234567890:100:❤️"
    callback.from_user.id = 12345
    callback.answer = AsyncMock()
    callback.message = MagicMock()
    callback.message.edit_reply_markup = AsyncMock()
    callback.message.chat = MagicMock()
    callback.message.chat.id = -1001234567890
    return callback


@pytest.fixture
def mock_container():
    """Create a mock service container."""
    container = MagicMock()
    container.reaction.add_reaction = AsyncMock()
    container.reaction.get_content_reactions = AsyncMock(return_value={"❤️": 5})
    container.reaction.get_user_reactions_for_content = AsyncMock(return_value=["❤️"])
    container.config.get_config = AsyncMock()
    return container


class TestHandleReactionCallback:
    """Test reaction callback handler."""

    async def test_successful_reaction(self, mock_callback, mock_container):
        """Handler should process successful reaction."""
        mock_container.reaction.add_reaction.return_value = (
            True, "success", {"besitos_earned": 5, "reactions_today": 3, "daily_limit": 20}
        )

        await handle_reaction_callback(mock_callback, mock_container, MagicMock())

        mock_container.reaction.add_reaction.assert_called_once()
        mock_callback.answer.assert_called_once()
        # Should contain besitos info
        call_args = mock_callback.answer.call_args
        assert "+5 besitos" in call_args[0][0] or "5 besitos" in call_args[0][0]

    async def test_duplicate_reaction(self, mock_callback, mock_container):
        """Handler should show duplicate message."""
        mock_container.reaction.add_reaction.return_value = (
            False, "duplicate", None
        )

        await handle_reaction_callback(mock_callback, mock_container, MagicMock())

        mock_callback.answer.assert_called_once()
        call_args = mock_callback.answer.call_args
        assert "Lucien" in call_args[0][0]
        assert call_args[1].get("show_alert") is True

    async def test_rate_limited(self, mock_callback, mock_container):
        """Handler should show rate limit message."""
        mock_container.reaction.add_reaction.return_value = (
            False, "rate_limited", {"seconds_remaining": 15}
        )

        await handle_reaction_callback(mock_callback, mock_container, MagicMock())

        mock_callback.answer.assert_called_once()
        call_args = mock_callback.answer.call_args
        assert "15s" in call_args[0][0] or "Espera" in call_args[0][0]

    async def test_daily_limit_reached(self, mock_callback, mock_container):
        """Handler should show daily limit message."""
        mock_container.reaction.add_reaction.return_value = (
            False, "daily_limit_reached", {"used": 20, "limit": 20}
        )

        await handle_reaction_callback(mock_callback, mock_container, MagicMock())

        mock_callback.answer.assert_called_once()
        call_args = mock_callback.answer.call_args
        assert "Límite" in call_args[0][0] or "20/20" in call_args[0][0]

    async def test_invalid_callback_format(self, mock_callback, mock_container):
        """Handler should handle invalid callback data."""
        mock_callback.data = "react:invalid"

        await handle_reaction_callback(mock_callback, mock_container, MagicMock())

        mock_callback.answer.assert_called_once()
        call_args = mock_callback.answer.call_args
        assert "formato inválido" in call_args[0][0].lower()

    async def test_invalid_content_id(self, mock_callback, mock_container):
        """Handler should handle invalid content_id."""
        mock_callback.data = "react:-1001234567890:abc:❤️"

        await handle_reaction_callback(mock_callback, mock_container, MagicMock())

        mock_callback.answer.assert_called_once()
        call_args = mock_callback.answer.call_args
        assert "contenido inválido" in call_args[0][0].lower()

    async def test_no_access_vip_content(self, mock_callback, mock_container):
        """Handler should show no access message for VIP content."""
        mock_container.reaction.add_reaction.return_value = (
            False, "no_access", {"error": "Este contenido es exclusivo para suscriptores VIP."}
        )

        await handle_reaction_callback(mock_callback, mock_container, MagicMock())

        mock_callback.answer.assert_called_once()
        call_args = mock_callback.answer.call_args
        assert "VIP" in call_args[0][0] or "acceso" in call_args[0][0].lower()


class TestGetContentCategory:
    """Test content category detection."""

    async def test_vip_channel(self):
        """Should return VIP_CONTENT for VIP channel."""
        container = MagicMock()
        config = MagicMock()
        config.vip_channel_id = "-100123"
        config.free_channel_id = "-100456"
        container.config.get_config = AsyncMock(return_value=config)

        result = await _get_content_category(container, "-100123")

        assert result == ContentCategory.VIP_CONTENT

    async def test_free_channel(self):
        """Should return FREE_CONTENT for Free channel."""
        container = MagicMock()
        config = MagicMock()
        config.vip_channel_id = "-100123"
        config.free_channel_id = "-100456"
        container.config.get_config = AsyncMock(return_value=config)

        result = await _get_content_category(container, "-100456")

        assert result == ContentCategory.FREE_CONTENT

    async def test_unknown_channel(self):
        """Should return None for unknown channel."""
        container = MagicMock()
        config = MagicMock()
        config.vip_channel_id = "-100123"
        config.free_channel_id = "-100456"
        container.config.get_config = AsyncMock(return_value=config)

        result = await _get_content_category(container, "-100999")

        assert result is None


class TestHandleSuccess:
    """Test success feedback handler."""

    async def test_success_with_besitos(self):
        """Should show message with besitos earned."""
        callback = MagicMock()
        callback.answer = AsyncMock()
        data = {"besitos_earned": 5, "reactions_today": 3, "daily_limit": 20}

        await _handle_success(callback, data, "❤️")

        callback.answer.assert_called_once()
        call_args = callback.answer.call_args
        assert "+5 besitos" in call_args[0][0]
        assert "3/20" in call_args[0][0]
        assert call_args[1].get("show_alert") is False

    async def test_success_without_besitos(self):
        """Should show message without besitos info."""
        callback = MagicMock()
        callback.answer = AsyncMock()
        data = {"besitos_earned": 0, "reactions_today": 5, "daily_limit": 20}

        await _handle_success(callback, data, "🔥")

        callback.answer.assert_called_once()
        call_args = callback.answer.call_args
        assert "🔥" in call_args[0][0]
        assert "5/20" in call_args[0][0]


class TestHandleFailure:
    """Test failure feedback handler."""

    async def test_duplicate_error(self):
        """Should show duplicate reaction message."""
        callback = MagicMock()
        callback.answer = AsyncMock()

        await _handle_failure(callback, "duplicate", None)

        callback.answer.assert_called_once()
        call_args = callback.answer.call_args
        assert "Lucien" in call_args[0][0]
        assert call_args[1].get("show_alert") is True

    async def test_rate_limited_error(self):
        """Should show rate limit message with seconds."""
        callback = MagicMock()
        callback.answer = AsyncMock()

        await _handle_failure(callback, "rate_limited", {"seconds_remaining": 25})

        callback.answer.assert_called_once()
        call_args = callback.answer.call_args
        assert "25s" in call_args[0][0]
        assert call_args[1].get("show_alert") is True

    async def test_daily_limit_error(self):
        """Should show daily limit message."""
        callback = MagicMock()
        callback.answer = AsyncMock()

        await _handle_failure(callback, "daily_limit_reached", {"used": 20, "limit": 20})

        callback.answer.assert_called_once()
        call_args = callback.answer.call_args
        assert "20/20" in call_args[0][0]
        assert call_args[1].get("show_alert") is True

    async def test_no_access_error(self):
        """Should show no access message."""
        callback = MagicMock()
        callback.answer = AsyncMock()

        await _handle_failure(callback, "no_access", {"error": "VIP only content"})

        callback.answer.assert_called_once()
        call_args = callback.answer.call_args
        assert "VIP only content" in call_args[0][0]
        assert call_args[1].get("show_alert") is True

    async def test_unknown_error(self):
        """Should show generic error for unknown code."""
        callback = MagicMock()
        callback.answer = AsyncMock()

        await _handle_failure(callback, "unknown_code", {})

        callback.answer.assert_called_once()
        call_args = callback.answer.call_args
        assert "Error desconocido" in call_args[0][0]
        assert call_args[1].get("show_alert") is True

    async def test_handles_none_data(self):
        """Should handle None data gracefully."""
        callback = MagicMock()
        callback.answer = AsyncMock()

        # Should not raise when data is None
        await _handle_failure(callback, "duplicate", None)
        await _handle_failure(callback, "rate_limited", None)
        await _handle_failure(callback, "daily_limit_reached", None)
        await _handle_failure(callback, "no_access", None)

        assert callback.answer.call_count == 4


class TestKeyboardUpdate:
    """Test keyboard update functionality."""

    async def test_keyboard_updated_after_reaction(self, mock_callback, mock_container):
        """Should update keyboard with new counts."""
        mock_container.reaction.add_reaction.return_value = (
            True, "success", {"besitos_earned": 5, "reactions_today": 1, "daily_limit": 20}
        )
        mock_container.reaction.get_content_reactions.return_value = {"❤️": 6, "🔥": 3}

        await handle_reaction_callback(mock_callback, mock_container, MagicMock())

        # Should get updated counts
        mock_container.reaction.get_content_reactions.assert_called_once_with(100, "-1001234567890")
        # Should edit reply markup
        mock_callback.message.edit_reply_markup.assert_called_once()

    async def test_keyboard_update_handles_not_modified(self, mock_callback, mock_container):
        """Should handle message not modified error gracefully."""
        from aiogram.exceptions import TelegramBadRequest

        mock_container.reaction.add_reaction.return_value = (
            True, "success", {"besitos_earned": 5, "reactions_today": 1, "daily_limit": 20}
        )
        # Create proper exception with required arguments
        mock_callback.message.edit_reply_markup.side_effect = TelegramBadRequest(
            message="message is not modified",
            method="editMessageReplyMarkup"
        )

        # Should not raise exception
        await handle_reaction_callback(mock_callback, mock_container, MagicMock())

        mock_callback.answer.assert_called_once()
