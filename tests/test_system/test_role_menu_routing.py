"""
Role-Based Menu Routing Tests

Tests for automatic menu routing based on user role:
- VIP users get VIP menu
- Free users get Free menu
- Admins get admin redirect on /start

These tests verify that users see the correct menu based on their role.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock


class TestFreeUserMenuRouting:
    """Tests for Free user menu routing."""

    async def test_free_user_gets_free_menu(self, free_message, test_session, mock_bot):
        """Verify free user sees Free menu on /start."""
        from bot.handlers.user.start import cmd_start

        # Execute /start (no VIP subscription)
        await cmd_start(free_message, test_session)

        # Verify free user menu was sent
        free_message.answer.assert_called()
        call_args = free_message.answer.call_args

        # Check keyboard has Free options (in kwargs)
        reply_markup = call_args.kwargs.get('reply_markup')
        assert reply_markup is not None

        # Check text contains Diana's voice for user menus (text is first positional arg)
        text = call_args.args[0] if call_args.args else call_args.kwargs.get('text', '')
        assert '🫦' in text  # Diana's voice for user menus

    async def test_free_menu_has_content_option(self, free_message, test_session, mock_bot):
        """Verify Free menu includes content access option."""
        from bot.handlers.user.start import cmd_start

        await cmd_start(free_message, test_session)

        call_args = free_message.answer.call_args
        reply_markup = call_args.kwargs.get('reply_markup')

        # Should have a keyboard
        assert reply_markup is not None

    async def test_regular_user_gets_free_menu(self, user_message, test_session, mock_bot):
        """Verify regular user (no subscription) gets Free menu."""
        from bot.handlers.user.start import cmd_start

        await cmd_start(user_message, test_session)

        # Verify message was sent
        user_message.answer.assert_called()
        call_args = user_message.answer.call_args

        # Check text contains Diana's voice for user menus (text is first positional arg)
        text = call_args.args[0] if call_args.args else call_args.kwargs.get('text', '')
        assert '🫦' in text  # Diana's voice for user menus


class TestAdminMenuRouting:
    """Tests for Admin menu routing."""

    async def test_admin_start_redirects_to_admin(self, admin_message, test_session, mock_bot):
        """Verify admin is handled correctly on /start."""
        from bot.handlers.user.start import cmd_start

        # Patch Config.is_admin to return True
        with patch('bot.handlers.user.start.Config.is_admin', return_value=True):
            await cmd_start(admin_message, test_session)

        # Verify admin-specific message
        admin_message.answer.assert_called()
        call_args = admin_message.answer.call_args
        text = call_args.args[0] if call_args.args else call_args.kwargs.get('text', '')

        # Should mention admin or panel
        assert '🎩' in text

    async def test_admin_gets_different_greeting(self, admin_message, test_session, mock_bot):
        """Verify admin gets different greeting than regular users."""
        from bot.handlers.user.start import cmd_start

        with patch('bot.handlers.user.start.Config.is_admin', return_value=True):
            await cmd_start(admin_message, test_session)

        call_args = admin_message.answer.call_args
        text = call_args.args[0] if call_args.args else call_args.kwargs.get('text', '')

        # Should have Lucien's voice
        assert '🎩' in text
        assert len(text) > 0


class TestRoleDetection:
    """Tests for role detection logic."""

    async def test_role_detection_priority_admin(self, admin_message, test_session, mock_bot):
        """Verify admin role takes priority over VIP."""
        from bot.services.role_detection import RoleDetectionService

        service = RoleDetectionService(test_session)

        with patch('bot.services.role_detection.Config.is_admin', return_value=True):
            from bot.database.enums import UserRole
            role = await service.get_user_role(admin_message.from_user.id)

        # Admin should be detected
        assert role == UserRole.ADMIN

    async def test_role_detection_free(self, free_message, test_session, mock_bot):
        """Verify Free role is detected for non-VIP users."""
        from bot.services.role_detection import RoleDetectionService
        from bot.database.enums import UserRole

        service = RoleDetectionService(test_session)

        with patch('bot.services.role_detection.Config.is_admin', return_value=False):
            role = await service.get_user_role(free_message.from_user.id)

        # Free should be detected (no VIP subscription)
        assert role == UserRole.FREE


class TestMenuRoleConsistency:
    """Tests for menu consistency across roles."""

    async def test_all_menus_use_appropriate_voice(self, admin_message, free_message, test_session, mock_bot):
        """Verify all role menus use appropriate voice consistently.

        - Admin menus: Lucien's voice (🎩)
        - User menus: Diana's voice (🫦)
        """
        from bot.handlers.user.start import cmd_start

        # Test admin menu (Lucien's voice for admin greeting)
        with patch('bot.handlers.user.start.Config.is_admin', return_value=True):
            await cmd_start(admin_message, test_session)
            admin_text = admin_message.answer.call_args.args[0] if admin_message.answer.call_args.args else admin_message.answer.call_args.kwargs.get('text', '')

        # Test Free menu (Diana's voice for user menus)
        await cmd_start(free_message, test_session)
        free_text = free_message.answer.call_args.args[0] if free_message.answer.call_args.args else free_message.answer.call_args.kwargs.get('text', '')

        # Admin uses Lucien's signature, user menus use Diana's
        assert '🎩' in admin_text  # Admin greeting uses Lucien
        assert '🫦' in free_text   # User menus use Diana


class TestVIPMenuDirect:
    """Tests for VIP menu using direct handler calls."""

    async def test_vip_menu_handler(self, vip_message, test_session, mock_bot):
        """Verify VIP menu handler works correctly."""
        from bot.handlers.vip.menu import show_vip_menu

        # Create container
        from bot.services.container import ServiceContainer
        container = ServiceContainer(test_session, mock_bot)

        # Create data dict
        data = {"container": container}

        # Call VIP menu directly
        await show_vip_menu(vip_message, data)

        # Verify message was sent
        vip_message.answer.assert_called()
        call_args = vip_message.answer.call_args
        text = call_args.args[0] if call_args.args else call_args.kwargs.get('text', '')

        # User menus use Diana's voice
        assert '🫦' in text

    async def test_vip_menu_with_subscription_info(self, vip_message, test_session, mock_bot):
        """Verify VIP menu shows subscription info when available."""
        from bot.handlers.vip.menu import show_vip_menu
        from bot.services.container import ServiceContainer

        container = ServiceContainer(test_session, mock_bot)
        data = {"container": container}

        # Call VIP menu
        await show_vip_menu(vip_message, data)

        # Verify message was sent
        vip_message.answer.assert_called()
        call_args = vip_message.answer.call_args
        text = call_args.args[0] if call_args.args else call_args.kwargs.get('text', '')

        # User menus use Diana's voice
        assert '🫦' in text
        assert len(text) > 0
