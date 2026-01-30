"""
VIP Token Flow Tests - Comprehensive tests for VIP token lifecycle.

Tests cover:
- Token generation (unique, 16-character tokens)
- Token validation (valid, expired, used)
- Token redemption (creates VIP subscription)
- Double redemption prevention
"""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from bot.services.subscription import SubscriptionService
from bot.database.models import InvitationToken, VIPSubscriber, User
from bot.database.enums import UserRole


async def test_generate_vip_token(test_session, mock_bot):
    """Verify admin can generate VIP tokens."""
    subscription_service = SubscriptionService(test_session, mock_bot)
    admin_id = 123456789

    token = await subscription_service.generate_vip_token(
        generated_by=admin_id,
        duration_hours=24
    )

    assert token is not None
    assert len(token.token) == 16  # 16-character unique token
    assert token.generated_by == admin_id
    assert token.used is False
    assert token.duration_hours == 24

    # Verify expiry is approximately 24 hours from creation
    expiry_time = token.created_at + timedelta(hours=token.duration_hours)
    time_diff = expiry_time - datetime.utcnow()
    assert timedelta(hours=23) < time_diff < timedelta(hours=25)


async def test_validate_vip_token(test_session, mock_bot):
    """Verify token validation works."""
    subscription_service = SubscriptionService(test_session, mock_bot)

    # Generate token
    token = await subscription_service.generate_vip_token(
        generated_by=123456789,
        duration_hours=24
    )

    await test_session.commit()  # Commit to persist token

    # Validate token
    is_valid, message, token_obj = await subscription_service.validate_token(
        token.token
    )

    assert is_valid is True
    assert token_obj is not None
    assert token_obj.id == token.id


async def test_validate_expired_token(test_session, mock_bot):
    """Verify expired tokens are rejected."""
    # Create expired token directly in database
    expired_token = InvitationToken(
        token="X" * 16,
        generated_by=123456789,
        created_at=datetime.utcnow() - timedelta(hours=25),  # Created 25 hours ago
        duration_hours=24,  # 24 hour duration = expired
        used=False
    )
    test_session.add(expired_token)
    await test_session.commit()

    subscription_service = SubscriptionService(test_session, mock_bot)

    # Validate expired token
    is_valid, message, token_obj = await subscription_service.validate_token(
        expired_token.token
    )

    assert is_valid is False
    assert "expirado" in message.lower() or "expiró" in message.lower()
    assert token_obj is not None  # Returns token even if expired


async def test_validate_used_token(test_session, mock_bot):
    """Verify used tokens are rejected."""
    # Create used token directly in database
    used_token = InvitationToken(
        token="Y" * 16,
        generated_by=123456789,
        created_at=datetime.utcnow(),
        duration_hours=24,
        used=True,
        used_by=987654321,
        used_at=datetime.utcnow()
    )
    test_session.add(used_token)
    await test_session.commit()

    subscription_service = SubscriptionService(test_session, mock_bot)

    # Validate used token
    is_valid, message, token_obj = await subscription_service.validate_token(
        used_token.token
    )

    assert is_valid is False
    assert "usado" in message.lower() or "used" in message.lower()
    assert token_obj is not None  # Returns token even if used


async def test_validate_nonexistent_token(test_session, mock_bot):
    """Verify non-existent tokens are rejected."""
    subscription_service = SubscriptionService(test_session, mock_bot)

    # Validate non-existent token
    is_valid, message, token_obj = await subscription_service.validate_token(
        "NONEXISTENT12345"
    )

    assert is_valid is False
    assert token_obj is None
    assert "no encontrado" in message.lower() or "not found" in message.lower()


async def test_redeem_vip_token(test_session, mock_bot):
    """Verify token redemption creates VIP subscription."""
    subscription_service = SubscriptionService(test_session, mock_bot)

    # Generate token
    token = await subscription_service.generate_vip_token(
        generated_by=123456789,
        duration_hours=24
    )

    await test_session.commit()  # Commit to persist token

    user_id = 987654321

    # Create user first (required for VIPSubscriber foreign key)
    user = User(
        user_id=user_id,
        first_name="Test",
        role=UserRole.FREE
    )
    test_session.add(user)
    await test_session.commit()

    # Redeem token
    success, message, subscriber = await subscription_service.redeem_vip_token(
        token_str=token.token,
        user_id=user_id
    )

    assert success is True
    assert subscriber is not None
    assert subscriber.user_id == user_id

    await test_session.commit()  # Commit redemption

    # Verify VIP subscription created
    result = await test_session.execute(
        select(VIPSubscriber).where(VIPSubscriber.user_id == user_id)
    )
    vip_sub = result.scalar_one_or_none()
    assert vip_sub is not None
    assert vip_sub.status == "active"

    # Verify token marked as used
    await test_session.refresh(token)
    assert token.used is True
    assert token.used_by == user_id
    assert token.used_at is not None


async def test_double_redeem_blocked(test_session, mock_bot):
    """Verify token cannot be redeemed twice."""
    subscription_service = SubscriptionService(test_session, mock_bot)

    # Generate token
    token = await subscription_service.generate_vip_token(
        generated_by=123456789,
        duration_hours=24
    )

    await test_session.commit()  # Commit to persist token

    user_id_1 = 111111111
    user_id_2 = 222222222

    # Create users first
    user1 = User(user_id=user_id_1, first_name="User1", role=UserRole.FREE)
    user2 = User(user_id=user_id_2, first_name="User2", role=UserRole.FREE)
    test_session.add(user1)
    test_session.add(user2)
    await test_session.commit()

    # First redemption
    success1, message1, sub1 = await subscription_service.redeem_vip_token(
        token_str=token.token,
        user_id=user_id_1
    )
    assert success1 is True
    assert sub1 is not None

    await test_session.commit()  # Commit first redemption

    # Second redemption (should fail)
    success2, message2, sub2 = await subscription_service.redeem_vip_token(
        token_str=token.token,
        user_id=user_id_2
    )
    assert success2 is False
    assert sub2 is None
    assert "usado" in message2.lower() or "used" in message2.lower()


async def test_redeem_expired_token_fails(test_session, mock_bot):
    """Verify expired tokens cannot be redeemed."""
    # Create expired token directly in database
    expired_token = InvitationToken(
        token="Z" * 16,
        generated_by=123456789,
        created_at=datetime.utcnow() - timedelta(hours=25),
        duration_hours=24,
        used=False
    )
    test_session.add(expired_token)
    await test_session.commit()

    subscription_service = SubscriptionService(test_session, mock_bot)

    # Try to redeem expired token
    success, message, subscriber = await subscription_service.redeem_vip_token(
        token_str=expired_token.token,
        user_id=987654321
    )

    assert success is False
    assert subscriber is None
    assert "expirado" in message.lower() or "expiró" in message.lower()


async def test_token_uniqueness(test_session, mock_bot):
    """Verify generated tokens are unique."""
    subscription_service = SubscriptionService(test_session, mock_bot)

    # Generate multiple tokens
    tokens = []
    for i in range(10):
        token = await subscription_service.generate_vip_token(
            generated_by=123456789,
            duration_hours=24
        )
        tokens.append(token.token)

    # Verify all tokens are unique
    assert len(tokens) == len(set(tokens)), "Generated tokens should be unique"


async def test_redeem_token_extends_existing_vip(test_session, mock_bot):
    """Verify redeeming token extends existing VIP subscription."""
    subscription_service = SubscriptionService(test_session, mock_bot)

    # First token redemption
    token1 = await subscription_service.generate_vip_token(
        generated_by=123456789,
        duration_hours=24
    )

    await test_session.commit()  # Commit to persist token

    user_id = 555666777

    # Create user first
    user = User(user_id=user_id, first_name="TestUser", role=UserRole.FREE)
    test_session.add(user)
    await test_session.commit()

    success1, _, sub1 = await subscription_service.redeem_vip_token(
        token_str=token1.token,
        user_id=user_id
    )
    assert success1 is True

    await test_session.commit()  # Commit first redemption

    original_expiry = sub1.expiry_date

    # Second token redemption (should extend)
    token2 = await subscription_service.generate_vip_token(
        generated_by=123456789,
        duration_hours=24
    )

    await test_session.commit()  # Commit to persist second token

    success2, _, sub2 = await subscription_service.redeem_vip_token(
        token_str=token2.token,
        user_id=user_id
    )
    assert success2 is True

    # Verify subscription was extended (same subscriber, new expiry)
    assert sub1.id == sub2.id
    assert sub2.expiry_date > original_expiry
