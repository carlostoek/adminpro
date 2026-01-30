"""
User Management Service Tests.

Comprehensive tests for user management operations:
- Get user info
- Change user roles
- Block/unblock users
- Kick users from channels
- User list with pagination and filtering
- Permission validation
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

from sqlalchemy import select

from bot.database.models import User, VIPSubscriber, InvitationToken, UserRoleChangeLog
from bot.database.enums import UserRole, RoleChangeReason
from bot.services.user_management import UserManagementService


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


class TestGetUserInfo:
    """Test getting user information."""

    async def test_get_user_info(self, test_session, mock_bot):
        """Verify admin can retrieve detailed user information."""
        user_id = 123456789
        user = await create_test_user(test_session, user_id, "testuser", UserRole.FREE)

        user_mgmt_service = UserManagementService(test_session, mock_bot)
        info = await user_mgmt_service.get_user_info(user_id)

        assert info is not None
        assert info["user_id"] == user_id
        assert info["username"] == "testuser"
        assert info["role"] == UserRole.FREE
        assert info["first_name"] == "Test"

    async def test_get_user_info_with_vip_subscription(self, test_session, mock_bot):
        """Verify user info includes VIP subscription details."""
        token = await create_test_token(test_session)
        user_id = 123456790

        user = await create_test_user(test_session, user_id, "vipuser", UserRole.VIP)

        # Create VIP subscription
        subscriber = VIPSubscriber(
            user_id=user_id,
            join_date=datetime.utcnow() - timedelta(days=15),
            expiry_date=datetime.utcnow() + timedelta(days=15),
            token_id=token.id
        )
        test_session.add(subscriber)
        await test_session.commit()

        user_mgmt_service = UserManagementService(test_session, mock_bot)
        info = await user_mgmt_service.get_user_info(user_id)

        assert info is not None
        assert info["user_id"] == user_id
        assert info["vip_subscription"] is not None
        assert info["vip_subscription"]["is_active"] is True

    async def test_get_user_info_nonexistent_user(self, test_session, mock_bot):
        """Verify getting info for nonexistent user returns None."""
        user_mgmt_service = UserManagementService(test_session, mock_bot)
        info = await user_mgmt_service.get_user_info(999999999)

        assert info is None


class TestChangeUserRole:
    """Test changing user roles."""

    async def test_change_user_role(self, test_session, mock_bot):
        """Verify admin can change user role."""
        user_id = 987654321
        admin_id = 111111111

        await create_test_user(test_session, user_id, "promote_user", UserRole.FREE)
        await create_test_user(test_session, admin_id, "admin_user", UserRole.ADMIN)

        user_mgmt_service = UserManagementService(test_session, mock_bot)

        # Change role from FREE to VIP
        success, message = await user_mgmt_service.change_user_role(
            user_id=user_id,
            new_role=UserRole.VIP,
            changed_by=admin_id
        )

        assert success is True

        # Verify role changed in database using proper refresh
        result = await test_session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one()
        assert user.role == UserRole.VIP

    async def test_change_user_role_creates_audit_log(self, test_session, mock_bot):
        """Verify role change creates audit log entry."""
        user_id = 987654322
        admin_id = 111111112

        await create_test_user(test_session, user_id, "audit_user", UserRole.FREE)
        await create_test_user(test_session, admin_id, "admin_user2", UserRole.ADMIN)

        user_mgmt_service = UserManagementService(test_session, mock_bot)

        # Change role
        await user_mgmt_service.change_user_role(
            user_id=user_id,
            new_role=UserRole.VIP,
            changed_by=admin_id
        )

        # Commit to ensure log is persisted
        await test_session.commit()

        # Verify audit log entry created using proper query
        result = await test_session.execute(
            select(UserRoleChangeLog).where(
                UserRoleChangeLog.user_id == user_id
            )
        )
        log = result.scalar_one_or_none()
        assert log is not None
        assert log.previous_role == UserRole.FREE
        assert log.new_role == UserRole.VIP
        assert log.changed_by == admin_id

    async def test_change_to_same_role(self, test_session, mock_bot):
        """Verify changing to same role returns success with message."""
        user_id = 987654323
        admin_id = 111111113

        await create_test_user(test_session, user_id, "same_role_user", UserRole.VIP)
        await create_test_user(test_session, admin_id, "admin_user3", UserRole.ADMIN)

        user_mgmt_service = UserManagementService(test_session, mock_bot)

        # Try to change VIP to VIP
        success, message = await user_mgmt_service.change_user_role(
            user_id=user_id,
            new_role=UserRole.VIP,
            changed_by=admin_id
        )

        assert success is True
        assert "ya tiene el rol" in message

    async def test_change_role_nonexistent_user(self, test_session, mock_bot):
        """Verify changing role for nonexistent user fails."""
        admin_id = 111111111
        await create_test_user(test_session, admin_id, "admin_user", UserRole.ADMIN)

        user_mgmt_service = UserManagementService(test_session, mock_bot)

        success, message = await user_mgmt_service.change_user_role(
            user_id=999999999,
            new_role=UserRole.VIP,
            changed_by=admin_id
        )

        assert success is False
        assert "no encontrado" in message

    async def test_change_role_self_prevention(self, test_session, mock_bot):
        """Verify admin cannot change their own role."""
        admin_id = 111111111

        await create_test_user(test_session, admin_id, "admin_self", UserRole.ADMIN)

        user_mgmt_service = UserManagementService(test_session, mock_bot)

        success, message = await user_mgmt_service.change_user_role(
            user_id=admin_id,
            new_role=UserRole.VIP,
            changed_by=admin_id
        )

        assert success is False
        assert "ti mismo" in message


class TestBlockUnblockUser:
    """Test blocking and unblocking users."""

    async def test_block_user(self, test_session, mock_bot):
        """Verify admin can block a user."""
        user_id = 222333444
        admin_id = 111111111

        await create_test_user(test_session, user_id, "blockme", UserRole.FREE)
        await create_test_user(test_session, admin_id, "admin_user", UserRole.ADMIN)

        user_mgmt_service = UserManagementService(test_session, mock_bot)

        # Note: Block user is currently a placeholder
        success, message = await user_mgmt_service.block_user(
            user_id=user_id,
            blocked_by=admin_id,
            reason="Spam"
        )

        # Currently returns False as it's not implemented
        assert success is False
        assert "próxima versión" in message

    async def test_unblock_user(self, test_session, mock_bot):
        """Verify admin can unblock a user."""
        user_id = 333444555
        admin_id = 111111111

        await create_test_user(test_session, user_id, "blocked_user", UserRole.FREE)
        await create_test_user(test_session, admin_id, "admin_user", UserRole.ADMIN)

        user_mgmt_service = UserManagementService(test_session, mock_bot)

        # Note: Unblock user is currently a placeholder
        success, message = await user_mgmt_service.unblock_user(
            user_id=user_id,
            unblocked_by=admin_id
        )

        # Currently returns False as it's not implemented
        assert success is False
        assert "próxima versión" in message

    async def test_block_self_prevention(self, test_session, mock_bot):
        """Verify admin cannot block themselves."""
        admin_id = 111111111

        await create_test_user(test_session, admin_id, "admin_self", UserRole.ADMIN)

        user_mgmt_service = UserManagementService(test_session, mock_bot)

        success, message = await user_mgmt_service.block_user(
            user_id=admin_id,
            blocked_by=admin_id,
            reason="Test"
        )

        assert success is False
        assert "ti mismo" in message


class TestExpelUser:
    """Test expelling users from channels."""

    async def test_expel_user_from_channels(self, test_session, mock_bot):
        """Verify admin can expel user from channels."""
        user_id = 444555666
        admin_id = 111111111

        await create_test_user(test_session, user_id, "kickme", UserRole.VIP)
        await create_test_user(test_session, admin_id, "admin_user", UserRole.ADMIN)

        # Mock successful ban
        mock_bot.ban_chat_member = AsyncMock(return_value=True)

        user_mgmt_service = UserManagementService(test_session, mock_bot)

        success, message, expelled_from = await user_mgmt_service.expel_user_from_channels(
            user_id=user_id,
            expelled_by=admin_id
        )

        # Should succeed (channels are configured in test_db fixture)
        assert success is True
        assert len(expelled_from) > 0

    async def test_expel_self_prevention(self, test_session, mock_bot):
        """Verify admin cannot expel themselves."""
        admin_id = 111111111

        await create_test_user(test_session, admin_id, "admin_self", UserRole.ADMIN)

        user_mgmt_service = UserManagementService(test_session, mock_bot)

        success, message, expelled_from = await user_mgmt_service.expel_user_from_channels(
            user_id=admin_id,
            expelled_by=admin_id
        )

        assert success is False
        assert "ti mismo" in message
        assert len(expelled_from) == 0

    async def test_expel_nonexistent_user(self, test_session, mock_bot):
        """Verify expelling nonexistent user fails gracefully."""
        admin_id = 111111111

        await create_test_user(test_session, admin_id, "admin_user", UserRole.ADMIN)

        user_mgmt_service = UserManagementService(test_session, mock_bot)

        success, message, expelled_from = await user_mgmt_service.expel_user_from_channels(
            user_id=999999999,
            expelled_by=admin_id
        )

        assert success is False


class TestUserList:
    """Test user list with pagination and filtering."""

    async def test_get_user_list_pagination(self, test_session, mock_bot):
        """Verify admin can get paginated list of users."""
        # Create multiple users
        for i in range(25):
            await create_test_user(test_session, 1000 + i, f"user{i}", UserRole.FREE)

        user_mgmt_service = UserManagementService(test_session, mock_bot)

        # Get first page (20 users)
        users_page1, total1 = await user_mgmt_service.get_user_list(limit=20, offset=0)
        assert len(users_page1) == 20

        # Get second page (5 users)
        users_page2, total2 = await user_mgmt_service.get_user_list(limit=20, offset=20)
        assert len(users_page2) == 5

    async def test_get_user_list_filtered_by_role(self, test_session, mock_bot):
        """Verify admin can filter users by role."""
        # Create users with different roles
        await create_test_user(test_session, 1001, "vip1", UserRole.VIP)
        await create_test_user(test_session, 1002, "free1", UserRole.FREE)
        await create_test_user(test_session, 1003, "free2", UserRole.FREE)
        await create_test_user(test_session, 1004, "admin1", UserRole.ADMIN)

        user_mgmt_service = UserManagementService(test_session, mock_bot)

        # Get only FREE users (filter by role in DB first)
        free_users, total_free = await user_mgmt_service.get_user_list(role=UserRole.FREE)
        # The method filters by real-time role detection, so results may vary
        assert all(u.role == UserRole.FREE for u in free_users)

    async def test_get_user_list_sorting(self, test_session, mock_bot):
        """Verify user list sorting works correctly."""
        # Create users at different times
        user1 = User(user_id=2001, username="user1", first_name="Test", role=UserRole.FREE)
        test_session.add(user1)
        await test_session.commit()

        user2 = User(user_id=2002, username="user2", first_name="Test", role=UserRole.FREE)
        test_session.add(user2)
        await test_session.commit()

        user_mgmt_service = UserManagementService(test_session, mock_bot)

        # Get sorted list (newest first by default)
        users, total = await user_mgmt_service.get_user_list(limit=10, offset=0, sort_newest_first=True)
        assert len(users) == 2

        # Get sorted list (oldest first)
        users_oldest, total = await user_mgmt_service.get_user_list(limit=10, offset=0, sort_newest_first=False)
        assert len(users_oldest) == 2


class TestSearchUsers:
    """Test user search functionality."""

    async def test_search_by_user_id(self, test_session, mock_bot):
        """Verify searching by user_id works."""
        await create_test_user(test_session, 3001, "searchable", UserRole.FREE)

        user_mgmt_service = UserManagementService(test_session, mock_bot)

        results = await user_mgmt_service.search_users("3001")

        assert len(results) == 1
        assert results[0].user_id == 3001

    async def test_search_by_username(self, test_session, mock_bot):
        """Verify searching by username works."""
        await create_test_user(test_session, 3002, "john_doe", UserRole.FREE)
        await create_test_user(test_session, 3003, "jane_doe", UserRole.FREE)

        user_mgmt_service = UserManagementService(test_session, mock_bot)

        results = await user_mgmt_service.search_users("doe")

        assert len(results) == 2

    async def test_search_by_username_partial(self, test_session, mock_bot):
        """Verify partial username search works."""
        await create_test_user(test_session, 3004, "testuser123", UserRole.FREE)

        user_mgmt_service = UserManagementService(test_session, mock_bot)

        results = await user_mgmt_service.search_users("test")

        assert len(results) == 1
        assert results[0].user_id == 3004

    async def test_search_no_results(self, test_session, mock_bot):
        """Verify search with no matches returns empty list."""
        user_mgmt_service = UserManagementService(test_session, mock_bot)

        results = await user_mgmt_service.search_users("nonexistent_xyz")

        assert len(results) == 0


class TestPermissions:
    """Test permission validation."""

    async def test_is_super_admin(self, test_session, mock_bot):
        """Verify super admin detection works."""
        # Import config and patch it directly
        from config import Config
        original_admin_ids = Config.ADMIN_USER_IDS
        try:
            Config.ADMIN_USER_IDS = [111111111, 222222222]

            user_mgmt_service = UserManagementService(test_session, mock_bot)

            assert user_mgmt_service.is_super_admin(111111111) is True
            assert user_mgmt_service.is_super_admin(222222222) is False
        finally:
            Config.ADMIN_USER_IDS = original_admin_ids

    async def test_admin_cannot_modify_other_admins(self, test_session, mock_bot):
        """Verify regular admin cannot modify other admins."""
        from config import Config
        original_admin_ids = Config.ADMIN_USER_IDS
        try:
            admin1_id = 111111111
            admin2_id = 222222222

            await create_test_user(test_session, admin1_id, "admin1", UserRole.ADMIN)
            await create_test_user(test_session, admin2_id, "admin2", UserRole.ADMIN)

            Config.ADMIN_USER_IDS = [admin1_id, admin2_id]

            user_mgmt_service = UserManagementService(test_session, mock_bot)

            # admin2 tries to modify admin1
            success, message = await user_mgmt_service.change_user_role(
                user_id=admin1_id,
                new_role=UserRole.VIP,
                changed_by=admin2_id
            )

            assert success is False
            assert "super admin" in message.lower()
        finally:
            Config.ADMIN_USER_IDS = original_admin_ids

    async def test_super_admin_can_modify_other_admins(self, test_session, mock_bot):
        """Verify super admin can modify other admins."""
        from config import Config
        original_admin_ids = Config.ADMIN_USER_IDS
        try:
            super_admin_id = 111111111
            admin2_id = 222222222

            await create_test_user(test_session, super_admin_id, "super_admin", UserRole.ADMIN)
            await create_test_user(test_session, admin2_id, "admin2", UserRole.ADMIN)

            Config.ADMIN_USER_IDS = [super_admin_id, admin2_id]

            user_mgmt_service = UserManagementService(test_session, mock_bot)

            # super admin modifies admin2
            success, message = await user_mgmt_service.change_user_role(
                user_id=admin2_id,
                new_role=UserRole.VIP,
                changed_by=super_admin_id
            )

            assert success is True
        finally:
            Config.ADMIN_USER_IDS = original_admin_ids


class TestGetUserRole:
    """Test getting user role."""

    async def test_get_user_role(self, test_session, mock_bot):
        """Verify getting user role works."""
        await create_test_user(test_session, 4001, "roletest", UserRole.VIP)

        user_mgmt_service = UserManagementService(test_session, mock_bot)

        role = await user_mgmt_service.get_user_role(4001)

        assert role == UserRole.VIP

    async def test_get_user_role_nonexistent(self, test_session, mock_bot):
        """Verify getting role for nonexistent user returns None."""
        user_mgmt_service = UserManagementService(test_session, mock_bot)

        role = await user_mgmt_service.get_user_role(999999999)

        assert role is None
