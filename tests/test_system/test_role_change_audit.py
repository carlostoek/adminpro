"""
Role Change Audit Log Tests.

Comprehensive tests for role change audit logging:
- Role changes create audit log entries
- Multiple changes create multiple logs
- Role change history retrieval
- Audit log filtering by admin
- Audit log counts
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy import select, func

from bot.database.models import User, UserRoleChangeLog
from bot.database.enums import UserRole, RoleChangeReason
from bot.services.role_change import RoleChangeService


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


class TestRoleChangeAuditLog:
    """Test audit logging for role changes."""

    async def test_role_change_creates_audit_log(self, test_session, mock_bot):
        """Verify role changes are logged."""
        user_id = 555666777
        admin_id = 111111111

        await create_test_user(test_session, user_id, "audit_test", UserRole.FREE)

        role_change_service = RoleChangeService(test_session)

        # Log a role change
        log_entry = await role_change_service.log_role_change(
            user_id=user_id,
            new_role=UserRole.VIP,
            changed_by=admin_id,
            reason=RoleChangeReason.MANUAL_CHANGE,
            previous_role=UserRole.FREE,
            change_source="ADMIN_PANEL"
        )

        await test_session.commit()

        # Verify audit log
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
        assert log.reason == RoleChangeReason.MANUAL_CHANGE
        assert log.change_source == "ADMIN_PANEL"

    async def test_role_change_auto_detects_previous_role(self, test_session, mock_bot):
        """Verify previous role is auto-detected from previous log entry."""
        user_id = 555666778
        admin_id = 111111111

        await create_test_user(test_session, user_id, "auto_detect_test", UserRole.FREE)

        role_change_service = RoleChangeService(test_session)

        # First change: FREE -> VIP (without providing previous_role)
        # For first change, no previous log exists so previous_role will be None
        log_entry1 = await role_change_service.log_role_change(
            user_id=user_id,
            new_role=UserRole.VIP,
            changed_by=admin_id,
            reason=RoleChangeReason.MANUAL_CHANGE,
            change_source="ADMIN_PANEL"
        )

        await test_session.commit()

        # First change has no previous log entry, so previous_role is None
        assert log_entry1.previous_role is None

        # Second change: VIP -> ADMIN (should auto-detect VIP from first log entry)
        log_entry2 = await role_change_service.log_role_change(
            user_id=user_id,
            new_role=UserRole.ADMIN,
            changed_by=admin_id,
            reason=RoleChangeReason.ADMIN_GRANTED,
            change_source="ADMIN_PANEL"
        )

        await test_session.commit()

        # Verify it detected VIP as previous role from first log entry
        assert log_entry2.previous_role == UserRole.VIP

    async def test_multiple_role_changes_create_multiple_logs(self, test_session, mock_bot):
        """Verify each role change creates separate log entry."""
        user_id = 666777888
        admin_id = 111111111

        await create_test_user(test_session, user_id, "multi_audit", UserRole.FREE)

        role_change_service = RoleChangeService(test_session)

        # First change: FREE -> VIP
        await role_change_service.log_role_change(
            user_id=user_id,
            new_role=UserRole.VIP,
            changed_by=admin_id,
            reason=RoleChangeReason.VIP_REDEEMED,
            previous_role=UserRole.FREE,
            change_source="ADMIN_PANEL"
        )

        # Second change: VIP -> ADMIN
        await role_change_service.log_role_change(
            user_id=user_id,
            new_role=UserRole.ADMIN,
            changed_by=admin_id,
            reason=RoleChangeReason.ADMIN_GRANTED,
            previous_role=UserRole.VIP,
            change_source="ADMIN_PANEL"
        )

        await test_session.commit()

        # Verify 2 log entries
        result = await test_session.execute(
            select(func.count(UserRoleChangeLog.id)).where(
                UserRoleChangeLog.user_id == user_id
            )
        )
        count = result.scalar()
        assert count == 2

    async def test_get_user_role_history(self, test_session, mock_bot):
        """Verify admin can view role change history."""
        user_id = 777888999
        admin_id = 111111111

        await create_test_user(test_session, user_id, "history_user", UserRole.FREE)

        role_change_service = RoleChangeService(test_session)

        # Make some changes
        await role_change_service.log_role_change(
            user_id=user_id,
            new_role=UserRole.VIP,
            changed_by=admin_id,
            reason=RoleChangeReason.VIP_REDEEMED,
            previous_role=UserRole.FREE,
            change_source="ADMIN_PANEL"
        )

        await role_change_service.log_role_change(
            user_id=user_id,
            new_role=UserRole.ADMIN,
            changed_by=admin_id,
            reason=RoleChangeReason.ADMIN_GRANTED,
            previous_role=UserRole.VIP,
            change_source="ADMIN_PANEL"
        )

        await test_session.commit()

        # Get history
        history = await role_change_service.get_user_role_history(user_id)

        assert len(history) == 2
        # Most recent first
        assert history[0].new_role == UserRole.ADMIN
        assert history[0].previous_role == UserRole.VIP
        assert history[1].new_role == UserRole.VIP
        assert history[1].previous_role == UserRole.FREE

    async def test_get_user_role_history_with_pagination(self, test_session, mock_bot):
        """Verify role history pagination works."""
        user_id = 777889000
        admin_id = 111111111

        await create_test_user(test_session, user_id, "history_pagination", UserRole.FREE)

        role_change_service = RoleChangeService(test_session)

        # Create 5 changes
        for i in range(5):
            await role_change_service.log_role_change(
                user_id=user_id,
                new_role=UserRole.VIP if i % 2 == 0 else UserRole.FREE,
                changed_by=admin_id,
                reason=RoleChangeReason.MANUAL_CHANGE,
                change_source="ADMIN_PANEL"
            )

        await test_session.commit()

        # Get first 2 entries
        history = await role_change_service.get_user_role_history(user_id, limit=2, offset=0)
        assert len(history) == 2

        # Get next 2 entries
        history_next = await role_change_service.get_user_role_history(user_id, limit=2, offset=2)
        assert len(history_next) == 2

    async def test_get_recent_role_changes(self, test_session, mock_bot):
        """Verify getting recent changes across all users works."""
        user1_id = 888999000
        user2_id = 888999001
        admin_id = 111111111

        await create_test_user(test_session, user1_id, "user1", UserRole.FREE)
        await create_test_user(test_session, user2_id, "user2", UserRole.FREE)

        role_change_service = RoleChangeService(test_session)

        # Changes for different users
        await role_change_service.log_role_change(
            user_id=user1_id,
            new_role=UserRole.VIP,
            changed_by=admin_id,
            reason=RoleChangeReason.VIP_REDEEMED,
            change_source="ADMIN_PANEL"
        )

        await role_change_service.log_role_change(
            user_id=user2_id,
            new_role=UserRole.VIP,
            changed_by=admin_id,
            reason=RoleChangeReason.VIP_PURCHASED,
            change_source="ADMIN_PANEL"
        )

        await test_session.commit()

        # Get recent changes
        recent = await role_change_service.get_recent_role_changes(limit=10)

        assert len(recent) == 2

    async def test_get_changes_by_admin(self, test_session, mock_bot):
        """Verify filtering changes by admin works."""
        user_id = 999000111
        admin1_id = 111111111
        admin2_id = 222222222

        await create_test_user(test_session, user_id, "user_filter", UserRole.FREE)

        role_change_service = RoleChangeService(test_session)

        # Change by admin1
        await role_change_service.log_role_change(
            user_id=user_id,
            new_role=UserRole.VIP,
            changed_by=admin1_id,
            reason=RoleChangeReason.MANUAL_CHANGE,
            change_source="ADMIN_PANEL"
        )

        # Change by admin2
        await role_change_service.log_role_change(
            user_id=user_id,
            new_role=UserRole.ADMIN,
            changed_by=admin2_id,
            reason=RoleChangeReason.ADMIN_GRANTED,
            change_source="ADMIN_PANEL"
        )

        await test_session.commit()

        # Get changes by admin1
        admin1_changes = await role_change_service.get_changes_by_admin(admin1_id)
        assert len(admin1_changes) == 1
        assert admin1_changes[0].changed_by == admin1_id

        # Get changes by admin2
        admin2_changes = await role_change_service.get_changes_by_admin(admin2_id)
        assert len(admin2_changes) == 1
        assert admin2_changes[0].changed_by == admin2_id

    async def test_count_role_changes(self, test_session, mock_bot):
        """Verify counting role changes works."""
        user1_id = 111000222
        user2_id = 111000223
        admin_id = 111111111

        await create_test_user(test_session, user1_id, "user1_count", UserRole.FREE)
        await create_test_user(test_session, user2_id, "user2_count", UserRole.FREE)

        role_change_service = RoleChangeService(test_session)

        # 2 changes for user1
        await role_change_service.log_role_change(
            user_id=user1_id,
            new_role=UserRole.VIP,
            changed_by=admin_id,
            reason=RoleChangeReason.MANUAL_CHANGE,
            change_source="ADMIN_PANEL"
        )

        await role_change_service.log_role_change(
            user_id=user1_id,
            new_role=UserRole.ADMIN,
            changed_by=admin_id,
            reason=RoleChangeReason.ADMIN_GRANTED,
            change_source="ADMIN_PANEL"
        )

        # 1 change for user2
        await role_change_service.log_role_change(
            user_id=user2_id,
            new_role=UserRole.VIP,
            changed_by=admin_id,
            reason=RoleChangeReason.VIP_REDEEMED,
            change_source="ADMIN_PANEL"
        )

        await test_session.commit()

        # Count for user1
        count1 = await role_change_service.count_role_changes(user1_id)
        assert count1 == 2

        # Count for user2
        count2 = await role_change_service.count_role_changes(user2_id)
        assert count2 == 1

        # Total count
        total = await role_change_service.count_role_changes()
        assert total == 3

    async def test_new_user_no_previous_role(self, test_session, mock_bot):
        """Verify new users have None as previous role."""
        user_id = 222333444
        admin_id = 111111111

        # Don't create user - simulating new user

        role_change_service = RoleChangeService(test_session)

        # Log change for new user
        log_entry = await role_change_service.log_role_change(
            user_id=user_id,
            new_role=UserRole.FREE,
            changed_by=0,  # SYSTEM
            reason=RoleChangeReason.SYSTEM_AUTOMATIC,
            change_source="SYSTEM"
        )

        await test_session.commit()

        # Previous role should be None for new user
        assert log_entry.previous_role is None

    async def test_change_source_validation(self, test_session, mock_bot):
        """Verify invalid change source raises error."""
        user_id = 333444555
        admin_id = 111111111

        await create_test_user(test_session, user_id, "source_test", UserRole.FREE)

        role_change_service = RoleChangeService(test_session)

        # Invalid change source should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            await role_change_service.log_role_change(
                user_id=user_id,
                new_role=UserRole.VIP,
                changed_by=admin_id,
                reason=RoleChangeReason.MANUAL_CHANGE,
                change_source="INVALID_SOURCE"
            )

        assert "change_source inválido" in str(exc_info.value)

    async def test_change_with_metadata(self, test_session, mock_bot):
        """Verify role change with metadata is stored correctly."""
        user_id = 444555666
        admin_id = 111111111

        await create_test_user(test_session, user_id, "metadata_test", UserRole.FREE)

        role_change_service = RoleChangeService(test_session)

        metadata = {
            "token": "ABC123",
            "duration_hours": 24,
            "ip_address": "192.168.1.1"
        }

        log_entry = await role_change_service.log_role_change(
            user_id=user_id,
            new_role=UserRole.VIP,
            changed_by=admin_id,
            reason=RoleChangeReason.VIP_REDEEMED,
            previous_role=UserRole.FREE,
            change_source="ADMIN_PANEL",
            change_metadata=metadata
        )

        await test_session.commit()

        # Verify metadata stored
        result = await test_session.execute(
            select(UserRoleChangeLog).where(
                UserRoleChangeLog.user_id == user_id
            )
        )
        log = result.scalar_one()

        assert log.change_metadata == metadata

    async def test_system_role_change(self, test_session, mock_bot):
        """Verify system-initiated role changes work correctly."""
        user_id = 555666777

        await create_test_user(test_session, user_id, "system_test", UserRole.VIP)

        role_change_service = RoleChangeService(test_session)

        # System expires VIP subscription
        log_entry = await role_change_service.log_role_change(
            user_id=user_id,
            new_role=UserRole.FREE,
            changed_by=0,  # SYSTEM
            reason=RoleChangeReason.VIP_EXPIRED,
            previous_role=UserRole.VIP,
            change_source="SYSTEM",
            change_metadata={"expired_at": datetime.utcnow().isoformat()}
        )

        await test_session.commit()

        assert log_entry.changed_by == 0
        assert log_entry.change_source == "SYSTEM"
        assert log_entry.reason == RoleChangeReason.VIP_EXPIRED

    async def test_role_change_timestamps(self, test_session, mock_bot):
        """Verify role change timestamps are set correctly."""
        user_id = 666777888
        admin_id = 111111111

        await create_test_user(test_session, user_id, "timestamp_test", UserRole.FREE)

        role_change_service = RoleChangeService(test_session)

        before = datetime.utcnow()

        log_entry = await role_change_service.log_role_change(
            user_id=user_id,
            new_role=UserRole.VIP,
            changed_by=admin_id,
            reason=RoleChangeReason.MANUAL_CHANGE,
            change_source="ADMIN_PANEL"
        )

        await test_session.commit()

        after = datetime.utcnow()

        # Verify timestamp is within reasonable range
        assert before <= log_entry.changed_at <= after
