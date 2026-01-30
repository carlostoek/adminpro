"""
Role Detection Service Tests.

Comprehensive tests for the role detection system verifying:
- Priority rules: Admin > VIP > Free
- Stateless behavior (no caching)
- VIP subscription detection
- Expired subscription handling
- Edge cases
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

from bot.database.models import User, VIPSubscriber, InvitationToken
from bot.database.enums import UserRole
from bot.services.role_detection import RoleDetectionService


async def create_test_token(session, token_str="TEST_TOKEN_12345"):
    """Helper to create a test invitation token."""
    token = InvitationToken(
        token=token_str,
        generated_by=987654321,
        duration_hours=168
    )
    session.add(token)
    await session.commit()
    await session.refresh(token)
    return token


async def create_test_user(session, user_id, username="testuser", role=UserRole.FREE):
    """Helper to create a test user."""
    user = User(
        user_id=user_id,
        username=username,
        first_name="Test",
        role=role
    )
    session.add(user)
    await session.commit()
    return user


class TestRoleDetectionPriority:
    """Test role detection priority: Admin > VIP > Free."""

    async def test_admin_role_highest_priority(self, test_session, mock_bot):
        """Verify Admin role overrides VIP and Free."""
        # Create invitation token first (required for VIPSubscriber)
        token = await create_test_token(test_session)

        # Create user with active VIP subscription
        user_id = 123456789
        await create_test_user(test_session, user_id, "admin_vip_user", UserRole.VIP)

        # Create active VIP subscription
        subscriber = VIPSubscriber(
            user_id=user_id,
            join_date=datetime.utcnow() - timedelta(days=15),
            expiry_date=datetime.utcnow() + timedelta(days=15),
            token_id=token.id
        )
        test_session.add(subscriber)
        await test_session.commit()

        # User is admin - should return ADMIN
        with patch('bot.services.role_detection.Config') as MockConfig:
            MockConfig.is_admin.return_value = True
            role_service = RoleDetectionService(test_session, mock_bot)
            detected_role = await role_service.get_user_role(user_id)

        # Admin should override VIP
        assert detected_role == UserRole.ADMIN

    async def test_vip_subscription_over_free(self, test_session, mock_bot):
        """Verify active VIP subscription has priority over Free role."""
        token = await create_test_token(test_session, "TOKEN_VIP_001")
        user_id = 987654321

        # Create user without VIP subscription
        await create_test_user(test_session, user_id, "free_user", UserRole.FREE)

        # First check - should be FREE
        with patch('bot.services.role_detection.Config') as MockConfig:
            MockConfig.is_admin.return_value = False
            role_service = RoleDetectionService(test_session, mock_bot)
            detected_role = await role_service.get_user_role(user_id)

        assert detected_role == UserRole.FREE

        # Add VIP subscription
        subscriber = VIPSubscriber(
            user_id=user_id,
            join_date=datetime.utcnow() - timedelta(days=15),
            expiry_date=datetime.utcnow() + timedelta(days=15),
            token_id=token.id
        )
        test_session.add(subscriber)
        await test_session.commit()

        # Second check - should now be VIP
        with patch('bot.services.role_detection.Config') as MockConfig:
            MockConfig.is_admin.return_value = False
            role_service = RoleDetectionService(test_session, mock_bot)
            detected_role = await role_service.get_user_role(user_id)

        assert detected_role == UserRole.VIP

    async def test_admin_overrides_vip_subscription(self, test_session, mock_bot):
        """Verify Admin role takes precedence over VIP subscription."""
        token = await create_test_token(test_session, "TOKEN_VIP_002")
        user_id = 111222333

        # Create user with VIP subscription
        await create_test_user(test_session, user_id, "vip_admin", UserRole.VIP)

        subscriber = VIPSubscriber(
            user_id=user_id,
            join_date=datetime.utcnow() - timedelta(days=15),
            expiry_date=datetime.utcnow() + timedelta(days=15),
            token_id=token.id
        )
        test_session.add(subscriber)
        await test_session.commit()

        # User is admin - should return ADMIN
        with patch('bot.services.role_detection.Config') as MockConfig:
            MockConfig.is_admin.return_value = True
            role_service = RoleDetectionService(test_session, mock_bot)
            detected_role = await role_service.get_user_role(user_id)

        assert detected_role == UserRole.ADMIN


class TestVIPSubscriptionDetection:
    """Test VIP subscription detection scenarios."""

    async def test_vip_subscription_detected(self, test_session, mock_bot):
        """Verify active VIP subscription is detected correctly."""
        token = await create_test_token(test_session, "TOKEN_VIP_003")
        user_id = 111222333

        # Create user first
        await create_test_user(test_session, user_id)

        # Create active VIP subscription
        subscriber = VIPSubscriber(
            user_id=user_id,
            join_date=datetime.utcnow() - timedelta(days=15),
            expiry_date=datetime.utcnow() + timedelta(days=15),
            token_id=token.id
        )
        test_session.add(subscriber)
        await test_session.commit()

        with patch('bot.services.role_detection.Config') as MockConfig:
            MockConfig.is_admin.return_value = False
            role_service = RoleDetectionService(test_session, mock_bot)
            detected_role = await role_service.get_user_role(user_id)

        assert detected_role == UserRole.VIP

    async def test_expired_vip_returns_free(self, test_session, mock_bot):
        """Verify expired VIP subscription results in Free role."""
        token = await create_test_token(test_session, "TOKEN_VIP_004")
        user_id = 222333444

        # Create user first
        await create_test_user(test_session, user_id)

        # Create expired VIP subscription
        subscriber = VIPSubscriber(
            user_id=user_id,
            join_date=datetime.utcnow() - timedelta(days=60),
            expiry_date=datetime.utcnow() - timedelta(days=1),  # Expired yesterday
            token_id=token.id
        )
        test_session.add(subscriber)
        await test_session.commit()

        with patch('bot.services.role_detection.Config') as MockConfig:
            MockConfig.is_admin.return_value = False
            role_service = RoleDetectionService(test_session, mock_bot)
            detected_role = await role_service.get_user_role(user_id)

        assert detected_role == UserRole.FREE

    async def test_no_subscription_returns_free(self, test_session, mock_bot):
        """Verify user with no subscription is Free."""
        user_id = 333444555

        # No VIP subscription in database

        with patch('bot.services.role_detection.Config') as MockConfig:
            MockConfig.is_admin.return_value = False
            role_service = RoleDetectionService(test_session, mock_bot)
            detected_role = await role_service.get_user_role(user_id)

        assert detected_role == UserRole.FREE

    async def test_vip_subscription_expires_exactly_now(self, test_session, mock_bot):
        """Verify VIP subscription expiring exactly now is handled."""
        token = await create_test_token(test_session, "TOKEN_VIP_005")
        user_id = 444555666

        # Create user first
        await create_test_user(test_session, user_id)

        # Create subscription expiring exactly now
        subscriber = VIPSubscriber(
            user_id=user_id,
            join_date=datetime.utcnow() - timedelta(days=30),
            expiry_date=datetime.utcnow(),  # Expires now
            token_id=token.id
        )
        test_session.add(subscriber)
        await test_session.commit()

        with patch('bot.services.role_detection.Config') as MockConfig:
            MockConfig.is_admin.return_value = False
            role_service = RoleDetectionService(test_session, mock_bot)
            detected_role = await role_service.get_user_role(user_id)

        # Should be FREE since subscription expired
        assert detected_role == UserRole.FREE


class TestStatelessBehavior:
    """Test that role detection is stateless (no caching)."""

    async def test_role_detection_is_stateless(self, test_session, mock_bot):
        """Verify role detection doesn't cache results."""
        token = await create_test_token(test_session, "TOKEN_STATE_001")
        user_id = 444555666

        with patch('bot.services.role_detection.Config') as MockConfig:
            MockConfig.is_admin.return_value = False

            # First call - no subscription
            role_service = RoleDetectionService(test_session, mock_bot)
            role1 = await role_service.get_user_role(user_id)
            assert role1 == UserRole.FREE

            # Create user and add VIP subscription
            await create_test_user(test_session, user_id)
            subscriber = VIPSubscriber(
                user_id=user_id,
                join_date=datetime.utcnow(),
                expiry_date=datetime.utcnow() + timedelta(days=30),
                token_id=token.id
            )
            test_session.add(subscriber)
            await test_session.commit()

            # Second call - should detect VIP (no cache)
            role2 = await role_service.get_user_role(user_id)
            assert role2 == UserRole.VIP

            # Verify different service instance also detects VIP
            role_service2 = RoleDetectionService(test_session, mock_bot)
            role3 = await role_service2.get_user_role(user_id)
            assert role3 == UserRole.VIP

    async def test_role_changes_immediately(self, test_session, mock_bot):
        """Verify role changes are detected immediately without cache."""
        token = await create_test_token(test_session, "TOKEN_STATE_002")
        user_id = 555666777

        # Create user and start as VIP
        await create_test_user(test_session, user_id)
        subscriber = VIPSubscriber(
            user_id=user_id,
            join_date=datetime.utcnow() - timedelta(days=15),
            expiry_date=datetime.utcnow() + timedelta(days=15),
            token_id=token.id
        )
        test_session.add(subscriber)
        await test_session.commit()

        with patch('bot.services.role_detection.Config') as MockConfig:
            MockConfig.is_admin.return_value = False

            role_service = RoleDetectionService(test_session, mock_bot)

            # Check VIP status
            role1 = await role_service.get_user_role(user_id)
            assert role1 == UserRole.VIP

            # Expire subscription
            subscriber.expiry_date = datetime.utcnow() - timedelta(days=1)
            await test_session.commit()

            # Check immediately - should be FREE
            role2 = await role_service.get_user_role(user_id)
            assert role2 == UserRole.FREE


class TestChannelMembership:
    """Test VIP channel membership detection."""

    async def test_vip_channel_member_without_subscription_is_free(self, test_session, mock_bot):
        """Verify user in VIP channel without subscription is treated as Free."""
        token = await create_test_token(test_session, "TOKEN_CHAN_001")
        user_id = 666777888

        # Create user first
        await create_test_user(test_session, user_id)

        # Create expired VIP subscription (user was VIP but expired)
        expired_sub = VIPSubscriber(
            user_id=user_id,
            join_date=datetime.utcnow() - timedelta(days=60),
            expiry_date=datetime.utcnow() - timedelta(days=30),  # Expired
            token_id=token.id
        )
        test_session.add(expired_sub)
        await test_session.commit()

        # Mock bot.get_chat_member to return "member" (in channel)
        mock_member = Mock()
        mock_member.status = "member"
        mock_bot.get_chat_member = AsyncMock(return_value=mock_member)

        with patch('bot.services.role_detection.Config') as MockConfig:
            MockConfig.is_admin.return_value = False
            role_service = RoleDetectionService(test_session, mock_bot)
            detected_role = await role_service.get_user_role(user_id)

        # Should be FREE (subscription expired, no active subscription)
        assert detected_role == UserRole.FREE

    async def test_vip_channel_admin_without_subscription_is_free(self, test_session, mock_bot):
        """Verify channel admin without VIP subscription is Free."""
        user_id = 777888999

        # No VIP subscription

        # Mock bot.get_chat_member to return "administrator"
        mock_member = Mock()
        mock_member.status = "administrator"
        mock_bot.get_chat_member = AsyncMock(return_value=mock_member)

        with patch('bot.services.role_detection.Config') as MockConfig:
            MockConfig.is_admin.return_value = False
            role_service = RoleDetectionService(test_session, mock_bot)
            detected_role = await role_service.get_user_role(user_id)

        # Should be FREE (no active VIP subscription)
        assert detected_role == UserRole.FREE

    async def test_bot_not_in_channel_handled_gracefully(self, test_session, mock_bot):
        """Verify error when bot can't check channel membership is handled."""
        user_id = 888999000

        # No VIP subscription

        # Mock bot.get_chat_member to raise exception
        mock_bot.get_chat_member = AsyncMock(side_effect=Exception("Bot is not a member"))

        with patch('bot.services.role_detection.Config') as MockConfig:
            MockConfig.is_admin.return_value = False
            role_service = RoleDetectionService(test_session, mock_bot)
            detected_role = await role_service.get_user_role(user_id)

        # Should default to FREE
        assert detected_role == UserRole.FREE


class TestEdgeCases:
    """Test edge cases and error handling."""

    async def test_negative_user_id(self, test_session, mock_bot):
        """Verify negative user IDs are handled correctly."""
        user_id = -123456

        with patch('bot.services.role_detection.Config') as MockConfig:
            MockConfig.is_admin.return_value = False
            role_service = RoleDetectionService(test_session, mock_bot)
            detected_role = await role_service.get_user_role(user_id)

        assert detected_role == UserRole.FREE

    async def test_zero_user_id(self, test_session, mock_bot):
        """Verify zero user ID is handled correctly."""
        user_id = 0

        with patch('bot.services.role_detection.Config') as MockConfig:
            MockConfig.is_admin.return_value = False
            role_service = RoleDetectionService(test_session, mock_bot)
            detected_role = await role_service.get_user_role(user_id)

        assert detected_role == UserRole.FREE

    async def test_very_large_user_id(self, test_session, mock_bot):
        """Verify very large user IDs are handled correctly."""
        token = await create_test_token(test_session, "TOKEN_LARGE_001")
        user_id = 999999999999

        # Create user first
        await create_test_user(test_session, user_id)

        subscriber = VIPSubscriber(
            user_id=user_id,
            join_date=datetime.utcnow() - timedelta(days=15),
            expiry_date=datetime.utcnow() + timedelta(days=15),
            token_id=token.id
        )
        test_session.add(subscriber)
        await test_session.commit()

        with patch('bot.services.role_detection.Config') as MockConfig:
            MockConfig.is_admin.return_value = False
            role_service = RoleDetectionService(test_session, mock_bot)
            detected_role = await role_service.get_user_role(user_id)

        assert detected_role == UserRole.VIP

    async def test_refresh_user_role_alias(self, test_session, mock_bot):
        """Verify refresh_user_role is an alias for get_user_role."""
        token = await create_test_token(test_session, "TOKEN_ALIAS_001")
        user_id = 999000111

        # Create user first
        await create_test_user(test_session, user_id)

        subscriber = VIPSubscriber(
            user_id=user_id,
            join_date=datetime.utcnow() - timedelta(days=15),
            expiry_date=datetime.utcnow() + timedelta(days=15),
            token_id=token.id
        )
        test_session.add(subscriber)
        await test_session.commit()

        with patch('bot.services.role_detection.Config') as MockConfig:
            MockConfig.is_admin.return_value = False
            role_service = RoleDetectionService(test_session, mock_bot)

            role1 = await role_service.get_user_role(user_id)
            role2 = await role_service.refresh_user_role(user_id)

            assert role1 == role2
            assert role1 == UserRole.VIP

    async def test_is_admin_helper_method(self, test_session, mock_bot):
        """Verify is_admin helper method works correctly."""
        with patch('bot.services.role_detection.Config') as MockConfig:
            MockConfig.is_admin.return_value = True
            role_service = RoleDetectionService(test_session, mock_bot)

            assert role_service.is_admin(123456) is True
            MockConfig.is_admin.assert_called_once_with(123456)

    async def test_vip_subscription_with_different_tokens(self, test_session, mock_bot):
        """Verify VIP subscription with different tokens works correctly."""
        token = await create_test_token(test_session, "TOKEN_MULTI_001")
        user_id = 111000222

        # Create user first
        await create_test_user(test_session, user_id)

        # Create active subscription
        subscriber = VIPSubscriber(
            user_id=user_id,
            join_date=datetime.utcnow() - timedelta(days=5),
            expiry_date=datetime.utcnow() + timedelta(days=25),
            token_id=token.id
        )
        test_session.add(subscriber)
        await test_session.commit()

        with patch('bot.services.role_detection.Config') as MockConfig:
            MockConfig.is_admin.return_value = False
            role_service = RoleDetectionService(test_session, mock_bot)
            detected_role = await role_service.get_user_role(user_id)

        # Should be VIP
        assert detected_role == UserRole.VIP
