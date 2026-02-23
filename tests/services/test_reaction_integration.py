"""
Integration tests for Reaction System.

Validates all REACT requirements:
- REACT-01: Channel messages display inline reaction buttons
- REACT-02: User can react via inline buttons
- REACT-03: System deduplicates reactions
- REACT-04: Rate limiting (30s cooldown)
- REACT-05: User earns besitos for valid reactions
- REACT-06: Daily reaction limit per user
- REACT-07: Only accessible content can be reacted to
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from bot.services.reaction import ReactionService
from bot.services.wallet import WalletService
from bot.database.models import UserReaction, UserGamificationProfile
from bot.database.enums import ContentCategory, TransactionType, UserRole


@pytest.fixture
async def wallet_service(test_session):
    """Create a real WalletService for integration testing."""
    return WalletService(test_session)


@pytest.fixture
async def reaction_service(test_session, wallet_service):
    """Create ReactionService with real WalletService."""
    return ReactionService(test_session, wallet_service=wallet_service)


class TestREACT01_InlineButtons:
    """REACT-01: Channel messages display inline reaction buttons."""

    async def test_reaction_keyboard_generated(self):
        """Keyboard utility should generate reaction buttons."""
        from bot.utils.keyboards import get_reaction_keyboard

        keyboard = get_reaction_keyboard(
            content_id=100,
            channel_id="-1001234567890"
        )

        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 0
        # Should have 4 reaction buttons in first row
        assert len(keyboard.inline_keyboard[0]) == 4

    async def test_reaction_keyboard_has_callback_data(self):
        """Each button should have proper callback data."""
        from bot.utils.keyboards import get_reaction_keyboard

        keyboard = get_reaction_keyboard(
            content_id=100,
            channel_id="-1001234567890"
        )

        button = keyboard.inline_keyboard[0][0]
        assert button.callback_data.startswith("react:")
        assert "100" in button.callback_data


class TestREACT02_UserCanReact:
    """REACT-02: User can react to content via inline buttons."""

    async def test_user_can_add_reaction(
        self, reaction_service, test_session, test_user
    ):
        """User should be able to add a reaction."""
        success, code, data = await reaction_service.add_reaction(
            user_id=test_user.user_id,
            content_id=100,
            channel_id="-100123",
            emoji="❤️",
            content_category=ContentCategory.FREE_CONTENT
        )

        assert success is True
        assert code == "success"

        # Verify reaction was saved
        from sqlalchemy import select

        result = await test_session.execute(
            select(UserReaction).where(
                UserReaction.user_id == test_user.user_id,
                UserReaction.content_id == 100,
                UserReaction.emoji == "❤️"
            )
        )
        reaction = result.scalar_one_or_none()
        assert reaction is not None


class TestREACT03_Deduplication:
    """REACT-03: System deduplicates reactions."""

    async def test_cannot_react_twice_with_same_emoji(
        self, reaction_service, test_session, test_user
    ):
        """User cannot react twice with same emoji to same content."""
        import asyncio

        # First reaction
        success1, _, _ = await reaction_service.add_reaction(
            user_id=test_user.user_id,
            content_id=100,
            channel_id="-100123",
            emoji="❤️",
            content_category=ContentCategory.FREE_CONTENT
        )
        assert success1 is True
        await test_session.commit()

        # Wait for rate limit to pass before testing deduplication
        await asyncio.sleep(31)

        # Second reaction (duplicate)
        success2, code, _ = await reaction_service.add_reaction(
            user_id=test_user.user_id,
            content_id=100,
            channel_id="-100123",
            emoji="❤️",
            content_category=ContentCategory.FREE_CONTENT
        )

        assert success2 is False
        assert code == "duplicate"

    async def test_cannot_react_with_different_emoji_to_same_content(
        self, reaction_service, test_session, test_user
    ):
        """User cannot react with different emoji to same content (one reaction per content)."""
        # First reaction
        await reaction_service.add_reaction(
            user_id=test_user.user_id,
            content_id=100,
            channel_id="-100123",
            emoji="❤️",
            content_category=ContentCategory.FREE_CONTENT
        )
        await test_session.commit()

        # Wait for rate limit
        import asyncio
        await asyncio.sleep(31)

        # Second reaction with different emoji should be blocked
        success, code, _ = await reaction_service.add_reaction(
            user_id=test_user.user_id,
            content_id=100,
            channel_id="-100123",
            emoji="🔥",
            content_category=ContentCategory.FREE_CONTENT
        )

        assert success is False
        assert code == "duplicate"


class TestREACT04_RateLimiting:
    """REACT-04: Rate limiting prevents reaction spam."""

    async def test_rate_limit_enforced(
        self, reaction_service, test_session, test_user
    ):
        """User cannot react within 30 seconds of previous reaction."""
        # First reaction
        await reaction_service.add_reaction(
            user_id=test_user.user_id,
            content_id=100,
            channel_id="-100123",
            emoji="❤️",
            content_category=ContentCategory.FREE_CONTENT
        )
        await test_session.commit()

        # Immediate second reaction
        success, code, data = await reaction_service.add_reaction(
            user_id=test_user.user_id,
            content_id=101,
            channel_id="-100123",
            emoji="🔥",
            content_category=ContentCategory.FREE_CONTENT
        )

        assert success is False
        assert code == "rate_limited"
        assert data["seconds_remaining"] > 0


class TestREACT05_BesitosEarning:
    """REACT-05: User earns besitos for valid reactions."""

    async def test_reaction_earns_besitos(
        self, reaction_service, wallet_service, test_session, test_user
    ):
        """Valid reaction should earn besitos."""
        success, code, data = await reaction_service.add_reaction(
            user_id=test_user.user_id,
            content_id=100,
            channel_id="-100123",
            emoji="❤️",
            content_category=ContentCategory.FREE_CONTENT
        )

        assert success is True
        assert data["besitos_earned"] > 0

        # Verify balance increased
        balance = await wallet_service.get_balance(test_user.user_id)
        assert balance == data["besitos_earned"]

    async def test_reaction_creates_transaction(
        self, reaction_service, test_session, test_user
    ):
        """Reaction should create EARN_REACTION transaction."""
        from bot.database.models import Transaction
        from sqlalchemy import select

        await reaction_service.add_reaction(
            user_id=test_user.user_id,
            content_id=100,
            channel_id="-100123",
            emoji="❤️",
            content_category=ContentCategory.FREE_CONTENT
        )
        await test_session.commit()

        # Verify transaction exists
        result = await test_session.execute(
            select(Transaction).where(
                Transaction.user_id == test_user.user_id,
                Transaction.type == TransactionType.EARN_REACTION
            )
        )
        transaction = result.scalar_one_or_none()
        assert transaction is not None
        assert transaction.amount > 0


class TestREACT06_DailyLimit:
    """REACT-06: Daily reaction limit per user."""

    async def test_daily_limit_enforced(
        self, reaction_service, test_session, test_user
    ):
        """User cannot exceed daily reaction limit."""
        # Create reactions up to limit with timestamps in the past (beyond rate limit window)
        past_time = datetime.utcnow() - timedelta(seconds=60)
        for i in range(20):
            reaction = UserReaction(
                user_id=test_user.user_id,
                content_id=i,
                channel_id="-100123",
                emoji="❤️",
                created_at=past_time - timedelta(minutes=i)  # Spread them out
            )
            test_session.add(reaction)
        await test_session.commit()

        # Try to add one more
        success, code, data = await reaction_service.add_reaction(
            user_id=test_user.user_id,
            content_id=999,
            channel_id="-100123",
            emoji="🔥",
            content_category=ContentCategory.FREE_CONTENT
        )

        assert success is False
        assert code == "daily_limit_reached"


class TestREACT07_VIPAccessControl:
    """REACT-07: Only accessible content can be reacted to."""

    async def test_vip_content_blocked_for_free_user(
        self, reaction_service, test_user
    ):
        """Free user cannot react to VIP content."""
        success, code, data = await reaction_service.add_reaction(
            user_id=test_user.user_id,
            content_id=100,
            channel_id="-100123",
            emoji="❤️",
            content_category=ContentCategory.VIP_CONTENT
        )

        assert success is False
        assert code == "no_access"

    async def test_vip_content_allowed_for_vip_user(
        self, reaction_service, test_session, test_user
    ):
        """VIP user can react to VIP content."""
        # Make user VIP
        from bot.database.models import VIPSubscriber, InvitationToken

        # Create an invitation token first (required for VIPSubscriber)
        token = InvitationToken(
            token="TEST_TOKEN_123",
            duration_hours=720,
            generated_by=99999,  # Admin user ID
        )
        test_session.add(token)
        await test_session.flush()  # Get the token ID

        test_user.role = UserRole.VIP
        subscriber = VIPSubscriber(
            user_id=test_user.user_id,
            expiry_date=datetime.utcnow() + timedelta(days=30),
            status="active",
            token_id=token.id
        )
        test_session.add(subscriber)
        await test_session.commit()

        success, code, _ = await reaction_service.add_reaction(
            user_id=test_user.user_id,
            content_id=100,
            channel_id="-100123",
            emoji="❤️",
            content_category=ContentCategory.VIP_CONTENT
        )

        assert success is True


class TestEndToEndFlow:
    """End-to-end integration tests."""

    async def test_full_reaction_flow(
        self, reaction_service, wallet_service, test_session, test_user
    ):
        """
        Complete flow: User reacts, earns besitos, sees updated counts.
        """
        # 1. User adds reaction
        success, code, data = await reaction_service.add_reaction(
            user_id=test_user.user_id,
            content_id=100,
            channel_id="-100123",
            emoji="❤️",
            content_category=ContentCategory.FREE_CONTENT
        )

        assert success is True
        besitos_earned = data["besitos_earned"]

        # 2. Verify besitos earned
        balance = await wallet_service.get_balance(test_user.user_id)
        assert balance == besitos_earned

        # 3. Verify reaction counts
        counts = await reaction_service.get_content_reactions(100, "-100123")
        assert counts["❤️"] == 1

        # 4. Verify daily stats
        today_count, limit = await reaction_service.get_user_reactions_today(
            test_user.user_id
        )
        assert today_count == 1
        assert limit == 20
