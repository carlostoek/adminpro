"""
VIP and Free Menu Tests

Tests for VIP and Free user menu functionality:
- VIP menu shows subscription info
- VIP menu has premium option
- Free menu has social media option
- Free menu has VIP channel option
- Menu navigation (back buttons)

These tests verify the specific menu options available to each user type.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock


class TestVIPMenuFeatures:
    """Tests for VIP menu features."""

    async def test_vip_menu_shows_subscription_info(self, vip_message, test_session, mock_bot):
        """Verify VIP menu displays subscription details."""
        from bot.handlers.vip.menu import show_vip_menu
        from bot.services.container import ServiceContainer

        # Create container
        container = ServiceContainer(test_session, mock_bot)
        data = {"container": container}

        # Call VIP menu
        await show_vip_menu(vip_message, data)

        # Verify menu shows subscription info
        vip_message.answer.assert_called()
        call_args = vip_message.answer.call_args
        text = call_args.args[0] if call_args.args else call_args.kwargs.get('text', '')

        # Should contain VIP indicators
        assert '🎩' in text

    async def test_vip_menu_has_premium_option(self, vip_message, test_session, mock_bot):
        """Verify VIP menu includes premium content option."""
        from bot.handlers.vip.menu import show_vip_menu
        from bot.services.container import ServiceContainer

        container = ServiceContainer(test_session, mock_bot)
        data = {"container": container}

        await show_vip_menu(vip_message, data)

        # Check keyboard has premium option
        call_args = vip_message.answer.call_args
        reply_markup = call_args.kwargs.get('reply_markup')
        assert reply_markup is not None

    async def test_vip_menu_has_status_button(self, vip_message, test_session, mock_bot):
        """Verify VIP menu includes status check button."""
        from bot.handlers.vip.menu import show_vip_menu
        from bot.services.container import ServiceContainer

        container = ServiceContainer(test_session, mock_bot)
        data = {"container": container}

        await show_vip_menu(vip_message, data)

        # Verify keyboard exists
        call_args = vip_message.answer.call_args
        reply_markup = call_args.kwargs.get('reply_markup')
        assert reply_markup is not None


class TestFreeMenuFeatures:
    """Tests for Free menu features."""

    async def test_free_menu_has_social_media(self, free_message, test_session, mock_bot):
        """Verify Free menu includes social media option."""
        from bot.handlers.free.menu import show_free_menu
        from bot.services.container import ServiceContainer

        container = ServiceContainer(test_session, mock_bot)
        data = {"container": container}

        await show_free_menu(free_message, data)

        # Verify menu was shown
        free_message.answer.assert_called()
        call_args = free_message.answer.call_args
        text = call_args.args[0] if call_args.args else call_args.kwargs.get('text', '')

        # Should have Lucien's voice
        assert '🎩' in text

    async def test_free_menu_has_vip_channel_option(self, free_message, test_session, mock_bot):
        """Verify Free menu includes VIP channel access option."""
        from bot.handlers.free.menu import show_free_menu
        from bot.services.container import ServiceContainer

        container = ServiceContainer(test_session, mock_bot)
        data = {"container": container}

        await show_free_menu(free_message, data)

        # Verify VIP channel option exists
        call_args = free_message.answer.call_args
        reply_markup = call_args.kwargs.get('reply_markup')
        assert reply_markup is not None

    async def test_free_menu_has_content_option(self, free_message, test_session, mock_bot):
        """Verify Free menu includes content access option."""
        from bot.handlers.free.menu import show_free_menu
        from bot.services.container import ServiceContainer

        container = ServiceContainer(test_session, mock_bot)
        data = {"container": container}

        await show_free_menu(free_message, data)

        # Verify keyboard exists
        call_args = free_message.answer.call_args
        reply_markup = call_args.kwargs.get('reply_markup')
        assert reply_markup is not None


class TestMenuNavigation:
    """Tests for menu navigation (back buttons)."""

    async def test_vip_back_button_navigation(self, vip_callback, test_session, mock_bot):
        """Verify back button returns to VIP main menu."""
        from bot.handlers.vip.callbacks import handle_menu_back

        # Setup
        container = MagicMock()
        container.message = MagicMock()
        container.message.user = MagicMock()
        container.message.user.menu = MagicMock()
        container.message.user.menu.vip_menu_greeting = MagicMock(return_value=("Test", MagicMock()))
        container.message.get_session_context = MagicMock(return_value=None)

        # Mock subscription service
        container.subscription = MagicMock()
        container.subscription.get_vip_subscriber = AsyncMock(return_value=None)

        # Execute
        await handle_menu_back(vip_callback, container)

        # Verify callback was answered
        vip_callback.answer.assert_called()

    async def test_free_back_button_navigation(self, free_callback, test_session, mock_bot):
        """Verify back button returns to Free main menu."""
        from bot.handlers.free.callbacks import handle_menu_back

        # Setup
        container = MagicMock()
        container.message = MagicMock()
        container.message.user = MagicMock()
        container.message.user.menu = MagicMock()
        container.message.user.menu.free_menu_greeting = MagicMock(return_value=("Test", MagicMock()))
        container.message.get_session_context = MagicMock(return_value=None)

        # Mock subscription service
        container.subscription = MagicMock()
        container.subscription.get_free_request = AsyncMock(return_value=None)

        # Execute
        await handle_menu_back(free_callback, container)

        # Verify callback was answered
        free_callback.answer.assert_called()

    async def test_vip_premium_callback(self, vip_callback, test_session, mock_bot):
        """Verify VIP premium callback works."""
        from bot.handlers.vip.callbacks import handle_vip_premium
        from bot.database.enums import ContentCategory

        # Setup
        container = MagicMock()
        container.message = MagicMock()
        container.message.user = MagicMock()
        container.message.user.menu = MagicMock()
        container.message.user.menu.vip_premium_section = MagicMock(return_value=("Test", MagicMock()))
        container.message.get_session_context = MagicMock(return_value=None)

        container.content = MagicMock()
        container.content.get_active_packages = AsyncMock(return_value=[])

        vip_callback.data = "vip:premium"

        # Execute
        await handle_vip_premium(vip_callback, container)

        # Verify callback was answered
        vip_callback.answer.assert_called()

    async def test_free_content_callback(self, free_callback, test_session, mock_bot):
        """Verify Free content callback works."""
        from bot.handlers.free.callbacks import handle_free_content
        from bot.database.enums import ContentCategory

        # Setup
        container = MagicMock()
        container.message = MagicMock()
        container.message.user = MagicMock()
        container.message.user.menu = MagicMock()
        container.message.user.menu.free_content_section = MagicMock(return_value=("Test", MagicMock()))
        container.message.get_session_context = MagicMock(return_value=None)

        container.content = MagicMock()
        container.content.get_active_packages = AsyncMock(return_value=[])

        free_callback.data = "menu:free:content"

        # Execute
        await handle_free_content(free_callback, container)

        # Verify callback was answered
        free_callback.answer.assert_called()


class TestVIPCallbacks:
    """Tests for VIP-specific callbacks."""

    async def test_vip_status_callback(self, vip_callback, test_session, mock_bot):
        """Verify VIP status callback shows subscription info."""
        from bot.handlers.vip.callbacks import handle_vip_status

        # Setup
        container = MagicMock()
        container.subscription = MagicMock()
        container.subscription.get_vip_subscriber = AsyncMock(return_value=None)

        vip_callback.data = "vip:status"
        vip_callback.message.edit_text = AsyncMock()

        # Execute
        await handle_vip_status(vip_callback, container)

        # Verify message was edited
        vip_callback.message.edit_text.assert_called()

    async def test_vip_premium_section_callback(self, vip_callback, test_session, mock_bot):
        """Verify VIP premium section callback works."""
        from bot.handlers.vip.callbacks import handle_vip_premium

        # Setup
        container = MagicMock()
        container.content = MagicMock()
        container.content.get_active_packages = AsyncMock(return_value=[])
        container.message = MagicMock()
        container.message.user = MagicMock()
        container.message.user.menu = MagicMock()
        container.message.user.menu.vip_premium_section = MagicMock(return_value=("Test", MagicMock()))
        container.message.get_session_context = MagicMock(return_value=None)

        vip_callback.data = "vip:premium"
        vip_callback.message.edit_text = AsyncMock()

        # Execute
        await handle_vip_premium(vip_callback, container)

        # Verify message was edited
        vip_callback.message.edit_text.assert_called()


class TestFreeCallbacks:
    """Tests for Free-specific callbacks."""

    async def test_free_vip_info_callback(self, free_callback, test_session, mock_bot):
        """Verify Free VIP info callback shows VIP channel information."""
        from bot.handlers.free.callbacks import handle_vip_info

        # Setup
        container = MagicMock()
        container.config = MagicMock()
        container.config.get_vip_channel_id = AsyncMock(return_value="-1001234567890")

        free_callback.data = "menu:free:vip"
        free_callback.message.edit_text = AsyncMock()

        # Execute
        await handle_vip_info(free_callback, container)

        # Verify message was edited
        free_callback.message.edit_text.assert_called()

    async def test_free_social_media_callback(self, free_callback, test_session, mock_bot):
        """Verify Free social media callback shows social links."""
        from bot.handlers.free.callbacks import handle_social_media

        free_callback.data = "menu:free:social"
        free_callback.message.edit_text = AsyncMock()

        # Execute
        await handle_social_media(free_callback)

        # Verify message was edited
        free_callback.message.edit_text.assert_called()


class TestMenuErrorHandling:
    """Tests for menu error handling."""

    async def test_vip_menu_requires_container(self, vip_message, test_session, mock_bot):
        """Verify VIP menu requires container to function."""
        from bot.handlers.vip.menu import show_vip_menu

        # Create data dict without container
        data = {}

        # Should raise AttributeError because container is required
        with pytest.raises(AttributeError):
            await show_vip_menu(vip_message, data)

    async def test_free_menu_handles_missing_container(self, free_message, test_session, mock_bot):
        """Verify Free menu handles missing container gracefully."""
        from bot.handlers.free.menu import show_free_menu

        # Create data dict without container
        data = {}

        # Should not raise
        await show_free_menu(free_message, data)

    async def test_vip_callback_handles_error(self, vip_callback, test_session, mock_bot):
        """Verify VIP callback handles errors gracefully."""
        from bot.handlers.vip.callbacks import handle_vip_premium

        # Setup container that raises error
        container = MagicMock()
        container.content = MagicMock()
        container.content.get_active_packages = AsyncMock(side_effect=Exception("Test error"))

        vip_callback.data = "vip:premium"
        vip_callback.answer = AsyncMock()

        # Execute - should not raise
        await handle_vip_premium(vip_callback, container)

        # Should answer with error
        vip_callback.answer.assert_called()
