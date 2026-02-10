"""
REACT Requirements Verification Tests.

Each test maps directly to a REACT requirement from the roadmap.
Run with: pytest tests/requirements/test_react_requirements.py -v
"""
import pytest


class TestREACT01_InlineButtons:
    """REACT-01: Channel messages display inline reaction buttons (❤️, 🔥, 💋, 😈)."""

    def test_react_01_keyboard_has_four_emojis(self):
        """Reaction keyboard must have 4 default emojis."""
        from bot.utils.keyboards import get_reaction_keyboard

        keyboard = get_reaction_keyboard(content_id=1, channel_id="-100123")
        buttons = keyboard.inline_keyboard[0]

        assert len(buttons) == 4
        # Check default emojis are present
        emojis = [btn.text for btn in buttons]
        assert "❤️" in emojis or "❤️ " in " ".join(emojis)
        assert "🔥" in emojis or "🔥 " in " ".join(emojis)

    def test_react_01_callback_data_format(self):
        """Reaction buttons must have proper callback data."""
        from bot.utils.keyboards import get_reaction_keyboard

        keyboard = get_reaction_keyboard(content_id=100, channel_id="-100123")
        button = keyboard.inline_keyboard[0][0]

        assert button.callback_data.startswith("react:")
        parts = button.callback_data.split(":")
        assert len(parts) == 4  # react, channel_id, content_id, emoji


class TestREACT02_UserCanReact:
    """REACT-02: User can react to content via inline buttons."""

    async def test_react_02_reaction_saved_to_db(self, test_session, test_user):
        """Tapping reaction button must save reaction to database."""
        from bot.services.reaction import ReactionService

        service = ReactionService(test_session, wallet_service=None)

        success, code, _ = await service.add_reaction(
            user_id=test_user.user_id,
            content_id=100,
            channel_id="-100123",
            emoji="❤️",
            content_category=None
        )

        assert success is True, f"Reaction failed with code: {code}"

        # Verify in database
        from bot.database.models import UserReaction
        from sqlalchemy import select

        result = await test_session.execute(
            select(UserReaction).where(
                UserReaction.user_id == test_user.user_id,
                UserReaction.content_id == 100
            )
        )
        assert result.scalar_one_or_none() is not None


class TestREACT03_Deduplication:
    """REACT-03: System deduplicates reactions (one per user per content per emoji)."""

    async def test_react_03_duplicate_blocked(self, test_session, test_user):
        """Same user cannot react twice with same emoji to same content."""
        from bot.services.reaction import ReactionService
        from bot.database.models import UserReaction
        import asyncio

        service = ReactionService(test_session, wallet_service=None)

        # First reaction
        await service.add_reaction(
            user_id=test_user.user_id,
            content_id=100,
            channel_id="-100123",
            emoji="❤️"
        )
        await test_session.commit()

        # Wait for rate limit to pass before testing deduplication
        await asyncio.sleep(31)

        # Second reaction (should fail with duplicate, not rate_limited)
        success, code, _ = await service.add_reaction(
            user_id=test_user.user_id,
            content_id=100,
            channel_id="-100123",
            emoji="❤️"
        )

        assert success is False
        assert code == "duplicate"


class TestREACT04_RateLimiting:
    """REACT-04: Rate limiting prevents reaction spam (30s cooldown)."""

    async def test_react_04_cooldown_enforced(self, test_session, test_user):
        """User must wait 30 seconds between reactions."""
        from bot.services.reaction import ReactionService
        from datetime import datetime

        service = ReactionService(test_session, wallet_service=None)

        # First reaction
        await service.add_reaction(
            user_id=test_user.user_id,
            content_id=100,
            channel_id="-100123",
            emoji="❤️"
        )
        await test_session.commit()

        # Immediate second reaction
        success, code, data = await service.add_reaction(
            user_id=test_user.user_id,
            content_id=101,
            channel_id="-100123",
            emoji="🔥"
        )

        assert success is False
        assert code == "rate_limited"
        assert data["seconds_remaining"] <= 30


class TestREACT05_BesitosEarning:
    """REACT-05: User earns besitos for valid reactions (configurable amount)."""

    async def test_react_05_besitos_earned(self, test_session, test_user):
        """Valid reaction must earn besitos."""
        from bot.services.reaction import ReactionService
        from bot.services.wallet import WalletService

        wallet = WalletService(test_session)
        service = ReactionService(test_session, wallet_service=wallet)

        success, code, data = await service.add_reaction(
            user_id=test_user.user_id,
            content_id=100,
            channel_id="-100123",
            emoji="❤️"
        )

        assert success is True
        assert data["besitos_earned"] > 0

        # Verify balance
        balance = await wallet.get_balance(test_user.user_id)
        assert balance == data["besitos_earned"]


class TestREACT06_DailyLimit:
    """REACT-06: Daily reaction limit per user (configurable)."""

    async def test_react_06_daily_limit_enforced(self, test_session, test_user):
        """User cannot exceed daily reaction limit."""
        from bot.services.reaction import ReactionService
        from bot.database.models import UserReaction
        from datetime import datetime, timedelta

        service = ReactionService(test_session, wallet_service=None)

        # Create max reactions with timestamps in the past (beyond rate limit window)
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

        # Try to exceed limit
        success, code, data = await service.add_reaction(
            user_id=test_user.user_id,
            content_id=999,
            channel_id="-100123",
            emoji="🔥"
        )

        assert success is False
        assert code == "daily_limit_reached"


class TestREACT07_AccessControl:
    """REACT-07: Only accessible content can be reacted to (VIP for VIP content)."""

    async def test_react_07_vip_content_blocked(self, test_session, test_user):
        """Non-VIP user cannot react to VIP content."""
        from bot.services.reaction import ReactionService
        from bot.database.enums import ContentCategory

        service = ReactionService(test_session, wallet_service=None)

        success, code, _ = await service.add_reaction(
            user_id=test_user.user_id,
            content_id=100,
            channel_id="-100123",
            emoji="❤️",
            content_category=ContentCategory.VIP_CONTENT
        )

        assert success is False
        assert code == "no_access"
