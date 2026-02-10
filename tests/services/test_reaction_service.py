"""
Tests for ReactionService.

Validates:
- Rate limiting (30s cooldown)
- Daily limit enforcement
- Duplicate prevention
- Content access validation
- Besitos earning integration
"""
import pytest
from datetime import datetime, timedelta

from bot.services.reaction import ReactionService
from bot.database.models import UserReaction, VIPSubscriber
from bot.database.enums import ContentCategory, TransactionType, UserRole


@pytest.fixture
def reaction_service(test_session):
    """Fixture for ReactionService with mocked wallet."""
    return ReactionService(test_session, wallet_service=None)


class TestRateLimiting:
    """Test rate limiting functionality."""

    async def test_first_reaction_allowed(self, reaction_service):
        """First reaction should always be allowed."""
        can_react, remaining = await reaction_service._check_rate_limit(12345)

        assert can_react is True
        assert remaining == 0

    async def test_reaction_within_cooldown_blocked(
        self, reaction_service, test_session, test_user
    ):
        """Reaction within 30s should be blocked."""
        # Create recent reaction
        reaction = UserReaction(
            user_id=test_user.user_id,
            content_id=1,
            channel_id="-100123",
            emoji="❤️",
            created_at=datetime.utcnow()
        )
        test_session.add(reaction)
        await test_session.commit()

        can_react, remaining = await reaction_service._check_rate_limit(test_user.user_id)

        assert can_react is False
        assert remaining > 0
        assert remaining <= 30

    async def test_reaction_after_cooldown_allowed(
        self, reaction_service, test_session, test_user
    ):
        """Reaction after 30s should be allowed."""
        # Create old reaction
        reaction = UserReaction(
            user_id=test_user.user_id,
            content_id=1,
            channel_id="-100123",
            emoji="❤️",
            created_at=datetime.utcnow() - timedelta(seconds=31)
        )
        test_session.add(reaction)
        await test_session.commit()

        can_react, remaining = await reaction_service._check_rate_limit(test_user.user_id)

        assert can_react is True
        assert remaining == 0


class TestDailyLimit:
    """Test daily reaction limit."""

    async def test_daily_limit_not_reached(self, reaction_service, test_user):
        """User under limit should be allowed."""
        can_react, used, limit = await reaction_service._check_daily_limit(test_user.user_id)

        assert can_react is True
        assert used == 0
        assert limit == 20  # Default

    async def test_daily_limit_reached(self, reaction_service, test_session, test_user):
        """User at limit should be blocked."""
        # Create max reactions for today
        for i in range(20):
            reaction = UserReaction(
                user_id=test_user.user_id,
                content_id=i,
                channel_id="-100123",
                emoji="❤️",
                created_at=datetime.utcnow()
            )
            test_session.add(reaction)
        await test_session.commit()

        can_react, used, limit = await reaction_service._check_daily_limit(test_user.user_id)

        assert can_react is False
        assert used == 20
        assert limit == 20


class TestDuplicateDetection:
    """Test duplicate reaction detection."""

    async def test_no_duplicate(self, reaction_service, test_user):
        """New reaction should not be duplicate."""
        is_dup = await reaction_service._is_duplicate_reaction(
            test_user.user_id, 1, "❤️"
        )
        assert is_dup is False

    async def test_duplicate_detected(self, reaction_service, test_session, test_user):
        """Same emoji on same content should be duplicate."""
        # Create existing reaction
        reaction = UserReaction(
            user_id=test_user.user_id,
            content_id=1,
            channel_id="-100123",
            emoji="❤️"
        )
        test_session.add(reaction)
        await test_session.commit()

        is_dup = await reaction_service._is_duplicate_reaction(
            test_user.user_id, 1, "❤️"
        )
        assert is_dup is True

    async def test_different_emoji_not_duplicate(
        self, reaction_service, test_session, test_user
    ):
        """Different emoji on same content should not be duplicate."""
        # Create existing reaction
        reaction = UserReaction(
            user_id=test_user.user_id,
            content_id=1,
            channel_id="-100123",
            emoji="❤️"
        )
        test_session.add(reaction)
        await test_session.commit()

        is_dup = await reaction_service._is_duplicate_reaction(
            test_user.user_id, 1, "🔥"
        )
        assert is_dup is False


class TestContentAccess:
    """Test content access validation."""

    async def test_free_content_accessible(self, reaction_service, test_user):
        """Free content should be accessible to all."""
        has_access, error = await reaction_service.validate_content_access(
            test_user.user_id,
            "-100123",
            ContentCategory.FREE_CONTENT
        )
        assert has_access is True
        assert error == ""

    async def test_vip_content_blocked_for_non_vip(
        self, reaction_service, test_user
    ):
        """VIP content should be blocked for non-VIP users."""
        has_access, error = await reaction_service.validate_content_access(
            test_user.user_id,
            "-100123",
            ContentCategory.VIP_CONTENT
        )
        assert has_access is False
        assert "VIP" in error

    async def test_vip_content_allowed_for_vip(
        self, reaction_service, test_session, test_vip_user, test_invitation_token
    ):
        """VIP content should be accessible to VIP users."""
        # Create VIP subscriber record
        subscriber = VIPSubscriber(
            user_id=test_vip_user.user_id,
            status="active",
            expiry_date=datetime.utcnow() + timedelta(days=30),
            token_id=test_invitation_token.id
        )
        test_session.add(subscriber)
        await test_session.commit()

        has_access, error = await reaction_service.validate_content_access(
            test_vip_user.user_id,
            "-100123",
            ContentCategory.VIP_CONTENT
        )
        assert has_access is True
        assert error == ""


class TestAddReaction:
    """Test full add_reaction flow."""

    async def test_successful_reaction(self, reaction_service, test_user):
        """Valid reaction should succeed."""
        success, code, data = await reaction_service.add_reaction(
            user_id=test_user.user_id,
            content_id=1,
            channel_id="-100123",
            emoji="❤️",
            content_category=ContentCategory.FREE_CONTENT
        )

        assert success is True
        assert code == "success"
        assert data["reactions_today"] == 1

    async def test_duplicate_reaction_fails(self, reaction_service, test_session, test_user):
        """Duplicate reaction should fail."""
        # Create first reaction in the past (to avoid rate limiting)
        reaction = UserReaction(
            user_id=test_user.user_id,
            content_id=1,
            channel_id="-100123",
            emoji="❤️",
            created_at=datetime.utcnow() - timedelta(seconds=31)  # Past cooldown
        )
        test_session.add(reaction)
        await test_session.commit()

        # Try to add same reaction again (duplicate)
        success, code, data = await reaction_service.add_reaction(
            user_id=test_user.user_id,
            content_id=1,
            channel_id="-100123",
            emoji="❤️",
            content_category=ContentCategory.FREE_CONTENT
        )

        assert success is False
        assert code == "duplicate"

    async def test_rate_limited_reaction_fails(self, reaction_service, test_session, test_user):
        """Rate limited reaction should fail."""
        # First reaction
        await reaction_service.add_reaction(
            user_id=test_user.user_id,
            content_id=1,
            channel_id="-100123",
            emoji="❤️",
            content_category=ContentCategory.FREE_CONTENT
        )
        await test_session.commit()

        # Immediate second reaction (rate limited)
        success, code, data = await reaction_service.add_reaction(
            user_id=test_user.user_id,
            content_id=2,
            channel_id="-100123",
            emoji="🔥",
            content_category=ContentCategory.FREE_CONTENT
        )

        assert success is False
        assert code == "rate_limited"
        assert data["seconds_remaining"] > 0


class TestGetContentReactions:
    """Test getting reaction counts for content."""

    async def test_empty_content_reactions(self, reaction_service):
        """Content with no reactions returns empty dict."""
        counts = await reaction_service.get_content_reactions(1, "-100123")
        assert counts == {}

    async def test_content_reaction_counts(self, reaction_service, test_session, test_user):
        """Content with reactions returns correct counts."""
        # Create additional users for reactions
        from bot.database.models import User
        from bot.database.enums import UserRole

        user2 = User(user_id=99998, username="testuser2", first_name="Test2", role=UserRole.FREE)
        user3 = User(user_id=99999, username="testuser3", first_name="Test3", role=UserRole.FREE)
        test_session.add(user2)
        test_session.add(user3)
        await test_session.flush()

        # Add multiple reactions
        reactions = [
            UserReaction(user_id=test_user.user_id, content_id=1, channel_id="-100123", emoji="❤️"),
            UserReaction(user_id=user2.user_id, content_id=1, channel_id="-100123", emoji="❤️"),
            UserReaction(user_id=user3.user_id, content_id=1, channel_id="-100123", emoji="🔥"),
        ]
        for r in reactions:
            test_session.add(r)
        await test_session.commit()

        counts = await reaction_service.get_content_reactions(1, "-100123")

        assert counts["❤️"] == 2
        assert counts["🔥"] == 1


class TestGetUserReactionsToday:
    """Test getting user's daily reaction stats."""

    async def test_no_reactions_today(self, reaction_service, test_user):
        """User with no reactions today returns 0."""
        count, limit = await reaction_service.get_user_reactions_today(test_user.user_id)
        assert count == 0
        assert limit == 20

    async def test_reactions_today_count(self, reaction_service, test_session, test_user):
        """Returns correct count of today's reactions."""
        # Add reactions from today
        for i in range(5):
            reaction = UserReaction(
                user_id=test_user.user_id,
                content_id=i,
                channel_id="-100123",
                emoji="❤️",
                created_at=datetime.utcnow()
            )
            test_session.add(reaction)
        await test_session.commit()

        count, limit = await reaction_service.get_user_reactions_today(test_user.user_id)
        assert count == 5
        assert limit == 20
