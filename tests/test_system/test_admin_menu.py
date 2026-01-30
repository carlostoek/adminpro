"""
Admin Menu System Tests

Tests for admin menu handlers covering:
- /admin command handler
- Admin menu callbacks
- Admin content submenu
- Non-admin access blocking

These tests verify that admins can navigate the admin menu correctly
and non-admins are properly blocked.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch


class TestAdminCommand:
    """Tests for the /admin command handler."""

    async def test_admin_command_opens_menu(self, admin_message, test_session, mock_bot):
        """Verify admin can open main menu with /admin command."""
        from bot.handlers.admin.main import cmd_admin

        # Setup mock
        admin_message.answer = AsyncMock()

        # Execute handler
        await cmd_admin(admin_message, test_session)

        # Verify response was sent
        admin_message.answer.assert_called_once()
        call_args = admin_message.answer.call_args
        assert call_args is not None

        # Check that text and keyboard were provided
        kwargs = call_args.kwargs
        assert 'text' in kwargs
        assert 'reply_markup' in kwargs
        assert 'parse_mode' in kwargs
        assert kwargs['parse_mode'] == "HTML"

        # Verify Lucien's voice is present
        text = kwargs['text']
        assert '🎩' in text

    async def test_admin_command_shows_config_status(self, admin_message, test_session, mock_bot):
        """Verify admin menu shows configuration status."""
        from bot.handlers.admin.main import cmd_admin

        admin_message.answer = AsyncMock()

        await cmd_admin(admin_message, test_session)

        call_args = admin_message.answer.call_args
        text = call_args.kwargs['text']

        # Should contain configuration indicators
        assert len(text) > 0
        assert '🎩' in text


class TestAdminMainMenuCallback:
    """Tests for admin:main callback handler."""

    async def test_admin_main_callback_updates_menu(self, admin_callback, test_session, mock_bot):
        """Verify admin:main callback updates the menu."""
        from bot.handlers.admin.main import callback_admin_main

        # Setup
        admin_callback.data = "admin:main"
        admin_callback.message.edit_text = AsyncMock()
        admin_callback.message.edit_reply_markup = AsyncMock()
        admin_callback.answer = AsyncMock()

        # Execute
        await callback_admin_main(admin_callback, test_session)

        # Verify menu was updated
        assert admin_callback.message.edit_text.called or admin_callback.message.edit_reply_markup.called
        admin_callback.answer.assert_called_once()

    async def test_admin_config_callback_shows_config_menu(self, admin_callback, test_session, mock_bot):
        """Verify admin:config callback shows configuration menu."""
        from bot.handlers.admin.main import callback_admin_config

        # Setup
        admin_callback.data = "admin:config"
        admin_callback.message.edit_text = AsyncMock()
        admin_callback.answer = AsyncMock()

        # Execute
        await callback_admin_config(admin_callback, test_session)

        # Verify config menu was shown
        admin_callback.message.edit_text.assert_called_once()
        call_args = admin_callback.message.edit_text.call_args
        kwargs = call_args.kwargs
        assert 'text' in kwargs
        assert 'reply_markup' in kwargs
        assert '🎩' in kwargs['text']

    async def test_admin_config_status_callback(self, admin_callback, test_session, mock_bot):
        """Verify config:status callback shows configuration status."""
        from bot.handlers.admin.main import callback_config_status

        # Setup
        admin_callback.data = "config:status"
        admin_callback.message.edit_text = AsyncMock()
        admin_callback.answer = AsyncMock()

        # Execute
        await callback_config_status(admin_callback, test_session)

        # Verify status was shown
        admin_callback.message.edit_text.assert_called_once()
        call_args = admin_callback.message.edit_text.call_args
        text = call_args.kwargs['text']

        # Should contain status information
        assert '🎩' in text
        assert len(text) > 0


class TestAdminContentMenu:
    """Tests for admin content management menu."""

    async def test_admin_content_management_callback(self, admin_callback, test_session, mock_bot):
        """Verify admin can access content management via callback."""
        from bot.handlers.admin.menu_callbacks import callback_content_management

        # Setup
        admin_callback.data = "admin:content_management"
        admin_callback.message.edit_text = AsyncMock()
        admin_callback.answer = AsyncMock()

        # Execute
        await callback_content_management(admin_callback, test_session)

        # Verify submenu was opened
        # Note: The callback redirects to content handler
        admin_callback.answer.assert_called()


class TestNonAdminBlocking:
    """Tests for non-admin access blocking."""

    async def test_non_admin_cannot_access_admin_menu(self, user_message, test_session, mock_bot):
        """Verify non-admin cannot access admin menu."""
        from bot.middlewares.admin_auth import AdminAuthMiddleware
        from aiogram.types import Message
        from unittest.mock import MagicMock

        # Create middleware instance
        middleware = AdminAuthMiddleware()

        # Setup mock handler that should NOT be called
        mock_handler = AsyncMock()

        # Create mock data dict
        data = {}

        # Patch Config.is_admin to return False for this user
        with patch('bot.middlewares.admin_auth.Config.is_admin', return_value=False):
            # Execute middleware
            result = await middleware(
                mock_handler,
                user_message,
                data
            )

        # Handler should not be called for non-admin
        mock_handler.assert_not_called()

    async def test_admin_passes_middleware(self, admin_message, test_session, mock_bot):
        """Verify admin passes through middleware."""
        from bot.middlewares.admin_auth import AdminAuthMiddleware
        from unittest.mock import MagicMock

        # Create middleware instance
        middleware = AdminAuthMiddleware()

        # Setup mock handler
        mock_handler = AsyncMock()

        # Create mock data dict
        data = {}

        # Patch Config.is_admin to return True for this user
        with patch('bot.middlewares.admin_auth.Config.is_admin', return_value=True):
            # Execute middleware
            await middleware(
                mock_handler,
                admin_message,
                data
            )

        # Handler should be called for admin
        mock_handler.assert_called_once()


class TestAdminMenuNavigation:
    """Tests for admin menu navigation callbacks."""

    async def test_menu_callbacks_answered(self, admin_callback, test_session, mock_bot):
        """Verify all menu callbacks answer the callback query."""
        from bot.handlers.admin.main import callback_admin_main

        # Setup
        admin_callback.data = "admin:main"
        admin_callback.message.edit_text = AsyncMock()
        admin_callback.answer = AsyncMock()

        # Execute
        await callback_admin_main(admin_callback, test_session)

        # Verify callback was answered
        admin_callback.answer.assert_called_once()

    async def test_callback_with_message_not_modified_error(self, admin_callback, test_session, mock_bot):
        """Verify handler handles 'message not modified' error gracefully."""
        from bot.handlers.admin.main import callback_admin_main

        # Setup
        admin_callback.data = "admin:main"
        admin_callback.answer = AsyncMock()

        # Mock edit_text to raise "message not modified" error
        async def raise_not_modified(*args, **kwargs):
            raise Exception("message is not modified")

        admin_callback.message.edit_text = AsyncMock(side_effect=raise_not_modified)

        # Execute - should not raise
        await callback_admin_main(admin_callback, test_session)

        # Verify callback was still answered
        admin_callback.answer.assert_called_once()
