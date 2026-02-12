"""
Free Channel Flow Tests - Comprehensive tests for Free user access flow.

Tests cover:
- Free request creation
- Free queue processing
- Duplicate request handling
- Invite link creation for approved users
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import select

from bot.services.subscription import SubscriptionService
from bot.database.models import FreeChannelRequest, User
from bot.database.enums import UserRole


async def test_create_free_request(test_session, mock_bot):
    """Verify user can create free channel request."""
    subscription_service = SubscriptionService(test_session, mock_bot)

    user_id = 123456789

    # Create user first
    user = User(user_id=user_id, first_name="FreeUser", role=UserRole.FREE)
    test_session.add(user)
    await test_session.commit()

    request = await subscription_service.create_free_request(
        user_id=user_id
    )

    assert request is not None
    assert request.user_id == user_id
    assert request.processed is False
    assert request.processed_at is None
    assert request.request_date is not None


async def test_process_free_queue(test_session, mock_bot):
    """Verify admin can process free queue."""
    subscription_service = SubscriptionService(test_session, mock_bot)

    # Create users and requests
    user_ids = [111111, 222222, 333333]
    for uid in user_ids:
        user = User(user_id=uid, first_name=f"User{uid}", role=UserRole.FREE)
        test_session.add(user)
    await test_session.commit()

    wait_time_minutes = 5

    # Create requests
    for uid in user_ids:
        await subscription_service.create_free_request(uid)

    await test_session.commit()

    # Set request time to past (simulating wait)
    result = await test_session.execute(
        select(FreeChannelRequest).where(FreeChannelRequest.user_id.in_(user_ids))
    )
    requests = result.scalars().all()

    past_time = datetime.utcnow() - timedelta(minutes=wait_time_minutes + 1)
    for req in requests:
        req.request_date = past_time

    await test_session.commit()

    # Process queue
    processed = await subscription_service.process_free_queue(
        wait_time_minutes=wait_time_minutes
    )

    assert len(processed) == 3
    assert all(req.processed for req in processed)
    assert all(req.processed_at is not None for req in processed)


async def test_duplicate_free_request_blocked(test_session, mock_bot):
    """Verify user cannot create duplicate free requests."""
    subscription_service = SubscriptionService(test_session, mock_bot)

    user_id = 444555666

    # Create user first
    user = User(user_id=user_id, first_name="DuplicateUser", role=UserRole.FREE)
    test_session.add(user)
    await test_session.commit()

    # First request
    request1 = await subscription_service.create_free_request(
        user_id=user_id
    )
    assert request1 is not None
    await test_session.commit()

    # Second request (should return existing)
    request2 = await subscription_service.create_free_request(
        user_id=user_id
    )

    assert request2 is not None
    assert request2.id == request1.id  # Same request


async def test_create_free_invite_link(test_session, mock_bot):
    """Verify invite link created for approved free user."""
    subscription_service = SubscriptionService(test_session, mock_bot)

    # Create a simple mock object that mimics ChatInviteLink
    mock_invite_link = MagicMock()
    mock_invite_link.invite_link = "https://t.me/+abc123"
    mock_bot.create_chat_invite_link = AsyncMock(return_value=mock_invite_link)

    user_id = 555666777
    channel_id = "-1001234567890"

    # Create user first
    user = User(user_id=user_id, first_name="TestUser", role=UserRole.FREE)
    test_session.add(user)
    await test_session.commit()

    # Create invite link
    invite_link = await subscription_service.create_invite_link(
        channel_id=channel_id,
        user_id=user_id,
        expire_hours=24
    )

    assert invite_link is not None
    assert invite_link.invite_link == "https://t.me/+abc123"
    mock_bot.create_chat_invite_link.assert_called_once()


async def test_process_free_queue_not_ready(test_session, mock_bot):
    """Verify requests that haven't waited long enough are not processed."""
    subscription_service = SubscriptionService(test_session, mock_bot)

    # Create user and request
    user_id = 666777888
    user = User(user_id=user_id, first_name="NotReadyUser", role=UserRole.FREE)
    test_session.add(user)
    await test_session.commit()

    wait_time_minutes = 30  # 30 minute wait time

    # Create request (just now)
    await subscription_service.create_free_request(user_id)
    await test_session.commit()

    # Process queue immediately (should not process)
    processed = await subscription_service.process_free_queue(
        wait_time_minutes=wait_time_minutes
    )

    assert len(processed) == 0  # No requests ready yet


async def test_get_free_request(test_session, mock_bot):
    """Verify getting pending free request for user."""
    subscription_service = SubscriptionService(test_session, mock_bot)

    user_id = 777888999

    # Create user first
    user = User(user_id=user_id, first_name="GetRequestUser", role=UserRole.FREE)
    test_session.add(user)
    await test_session.commit()

    # Initially no request
    request = await subscription_service.get_free_request(user_id)
    assert request is None

    # Create request
    created_request = await subscription_service.create_free_request(user_id)
    await test_session.commit()

    # Get request
    request = await subscription_service.get_free_request(user_id)
    assert request is not None
    assert request.id == created_request.id
    assert request.user_id == user_id


async def test_cleanup_old_free_requests(test_session, mock_bot):
    """Verify old processed requests are cleaned up."""
    subscription_service = SubscriptionService(test_session, mock_bot)

    # Create users and requests
    user_ids = [100001, 100002, 100003]
    for uid in user_ids:
        user = User(user_id=uid, first_name=f"User{uid}", role=UserRole.FREE)
        test_session.add(user)
    await test_session.commit()

    # Create and process old requests
    for uid in user_ids:
        request = await subscription_service.create_free_request(uid)
        request.processed = True
        request.processed_at = datetime.utcnow() - timedelta(days=31)  # 31 days old
        request.request_date = datetime.utcnow() - timedelta(days=32)

    await test_session.commit()

    # Cleanup old requests (older than 30 days)
    deleted_count = await subscription_service.cleanup_old_free_requests(days_old=30)

    assert deleted_count == 3

    # Verify all deleted
    result = await test_session.execute(
        select(FreeChannelRequest).where(FreeChannelRequest.user_id.in_(user_ids))
    )
    remaining = result.scalars().all()
    assert len(remaining) == 0


async def test_free_request_minutes_since(test_session, mock_bot):
    """Verify minutes_since_request calculation."""
    subscription_service = SubscriptionService(test_session, mock_bot)

    user_id = 888999000

    # Create user first
    user = User(user_id=user_id, first_name="MinutesUser", role=UserRole.FREE)
    test_session.add(user)
    await test_session.commit()

    # Create request with specific time
    request = await subscription_service.create_free_request(user_id)
    request.request_date = datetime.utcnow() - timedelta(minutes=10)
    await test_session.commit()

    # Refresh to get updated values
    await test_session.refresh(request)

    # Verify minutes calculation (approximately 10 minutes)
    minutes = request.minutes_since_request()
    assert 9 <= minutes <= 11  # Allow small variance


async def test_free_request_is_ready(test_session, mock_bot):
    """Verify is_ready method for free requests."""
    subscription_service = SubscriptionService(test_session, mock_bot)

    user_id = 999000111

    # Create user first
    user = User(user_id=user_id, first_name="ReadyUser", role=UserRole.FREE)
    test_session.add(user)
    await test_session.commit()

    # Create request 10 minutes ago
    request = await subscription_service.create_free_request(user_id)
    request.request_date = datetime.utcnow() - timedelta(minutes=10)
    await test_session.commit()

    # Refresh to get updated values
    await test_session.refresh(request)

    # Should be ready for 5 minute wait time
    assert request.is_ready(wait_time_minutes=5) is True

    # Should NOT be ready for 15 minute wait time
    assert request.is_ready(wait_time_minutes=15) is False


async def test_get_or_create_free_channel_invite_link(test_session, mock_bot):
    """Verify ChannelService creates and reuses invite link."""
    from bot.services.channel import ChannelService
    from bot.database.models import BotConfig
    from unittest.mock import patch

    # Setup: Create BotConfig with free channel
    bot_config = await test_session.get(BotConfig, 1)
    bot_config.free_channel_id = "-1001234567890"
    await test_session.commit()

    # Mock the invite link creation and permissions
    mock_invite_link = MagicMock()
    mock_invite_link.invite_link = "https://t.me/+FreeChannelLink123"
    mock_bot.create_chat_invite_link = AsyncMock(return_value=mock_invite_link)

    channel_service = ChannelService(test_session, mock_bot)

    # Patch verify_bot_permissions to return success
    with patch.object(channel_service, 'verify_bot_permissions', return_value=(True, "OK")):
        # First call - should create new link
        link1 = await channel_service.get_or_create_free_channel_invite_link()

        assert link1 is not None
        assert link1 == "https://t.me/+FreeChannelLink123"
        mock_bot.create_chat_invite_link.assert_called_once()

        # Second call - should reuse existing link (not create new one)
        mock_bot.create_chat_invite_link.reset_mock()
        link2 = await channel_service.get_or_create_free_channel_invite_link()

        assert link2 == link1  # Same link
        mock_bot.create_chat_invite_link.assert_not_called()  # Not called again


async def test_get_or_create_free_channel_invite_link_no_channel(test_session, mock_bot):
    """Verify ChannelService returns None when no free channel configured."""
    from bot.services.channel import ChannelService
    from bot.database.models import BotConfig

    # Setup: BotConfig without free channel
    bot_config = await test_session.get(BotConfig, 1)
    bot_config.free_channel_id = None
    await test_session.commit()

    channel_service = ChannelService(test_session, mock_bot)

    # Should return None when no channel configured
    link = await channel_service.get_or_create_free_channel_invite_link()

    assert link is None
    mock_bot.create_chat_invite_link.assert_not_called()


async def test_revoke_free_channel_invite_link(test_session, mock_bot):
    """Verify ChannelService can revoke invite link."""
    from bot.services.channel import ChannelService
    from bot.database.models import BotConfig
    from unittest.mock import patch

    # Setup: Create BotConfig with free channel and existing link
    bot_config = await test_session.get(BotConfig, 1)
    bot_config.free_channel_id = "-1001234567890"
    bot_config.free_channel_invite_link = "https://t.me/+OldLink123"
    await test_session.commit()

    mock_bot.revoke_chat_invite_link = AsyncMock()

    channel_service = ChannelService(test_session, mock_bot)

    # Revoke the link
    success, message = await channel_service.revoke_free_channel_invite_link()

    assert success is True
    assert "revocado" in message.lower() or "revoked" in message.lower()

    # Verify link was cleared from database
    await test_session.refresh(bot_config)
    assert bot_config.free_channel_invite_link is None

    # Verify next call creates new link (with patched permissions)
    mock_invite_link = MagicMock()
    mock_invite_link.invite_link = "https://t.me/+NewLink456"
    mock_bot.create_chat_invite_link = AsyncMock(return_value=mock_invite_link)

    with patch.object(channel_service, 'verify_bot_permissions', return_value=(True, "OK")):
        new_link = await channel_service.get_or_create_free_channel_invite_link()
        assert new_link == "https://t.me/+NewLink456"
        mock_bot.create_chat_invite_link.assert_called_once()
