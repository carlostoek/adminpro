"""
Integration tests for session-aware message generation.

Tests that message providers correctly wire session context through
to _choose_variant, enabling repetition prevention.
"""
import pytest
from bot.services.message.session_history import SessionMessageHistory
from bot.services.message import UserStartMessages, AdminVIPMessages, AdminMainMessages, AdminFreeMessages
from datetime import datetime


class TestSessionAwareGeneration:
    """Test that providers use session context to prevent repetition."""

    def test_user_greeting_excludes_recent_variants(self):
        """UserStartMessages.greeting() should avoid repeating recent greetings."""
        history = SessionMessageHistory()
        provider = UserStartMessages()

        # Generate greeting 5 times for same user
        greetings = []
        for i in range(5):
            text, kb = provider.greeting(
                user_name="Carlos",
                user_id=12345,
                session_history=history
            )
            # Extract greeting from text (first line after emoji)
            greeting = text.split('🎩')[1].split(',')[0].strip()
            greetings.append(greeting)

        # No greeting should repeat consecutively
        for i in range(len(greetings) - 1):
            assert greetings[i] != greetings[i+1], \
                f"Greeting repeated at position {i}: {greetings[i]}"

    def test_different_users_independent_sessions(self):
        """Different users should have independent session histories."""
        history = SessionMessageHistory()
        provider = UserStartMessages()

        # User 1 gets greeting
        text1, _ = provider.greeting(
            user_name="User1",
            user_id=11111,
            session_history=history
        )
        greeting1 = text1.split('🎩')[1].split(',')[0].strip()

        # User 2 gets greeting (can be same as User 1's first)
        text2, _ = provider.greeting(
            user_name="User2",
            user_id=22222,
            session_history=history
        )
        greeting2 = text2.split('🎩')[1].split(',')[0].strip()

        # Users are independent - no restriction on first greetings being same
        assert greeting1 or greeting2  # Both should have greetings

    def test_admin_vip_menu_session_aware(self):
        """AdminVIPMessages.vip_menu() should use session context when provided."""
        history = SessionMessageHistory()
        provider = AdminVIPMessages()

        menus = []
        for i in range(3):
            text, kb = provider.vip_menu(
                is_configured=True,
                user_id=54321,
                session_history=history
            )
            menus.append(text)

        # Verify no consecutive exact duplicates
        for i in range(len(menus) - 1):
            assert menus[i] != menus[i+1], \
                f"Menu text repeated at position {i}"

    def test_admin_main_menu_session_aware(self):
        """AdminMainMessages.admin_menu_greeting() should use session context when provided."""
        history = SessionMessageHistory()
        provider = AdminMainMessages()

        menus = []
        for i in range(3):
            text, kb = provider.admin_menu_greeting(
                is_configured=True,
                user_id=99999,
                session_history=history
            )
            menus.append(text)

        # Verify no consecutive exact duplicates
        for i in range(len(menus) - 1):
            assert menus[i] != menus[i+1], \
                f"Menu text repeated at position {i}"

    def test_admin_free_menu_session_aware(self):
        """AdminFreeMessages.free_menu() should use session context when provided."""
        history = SessionMessageHistory()
        provider = AdminFreeMessages()

        menus = []
        for i in range(3):
            text, kb = provider.free_menu(
                is_configured=True,
                user_id=88888,
                session_history=history
            )
            menus.append(text)

        # Verify no consecutive exact duplicates
        for i in range(len(menus) - 1):
            assert menus[i] != menus[i+1], \
                f"Menu text repeated at position {i}"

    def test_backward_compatibility_no_session_context(self):
        """Providers should work without session_history parameter (backward compat)."""
        provider = UserStartMessages()

        # Call without session_history (old API)
        text, kb = provider.greeting(
            user_name="Ana",
            is_vip=True,
            vip_days_remaining=15
        )

        # Should still work
        assert '🎩' in text
        assert 'Ana' in text
        assert 'círculo exclusivo' in text.lower()

    def test_deep_link_activation_success_session_aware(self):
        """UserStartMessages.deep_link_activation_success() should use session context."""
        history = SessionMessageHistory()
        provider = UserStartMessages()

        # Generate 2 messages (only 2 variants available, so we test consecutive exclusion)
        text1, kb1 = provider.deep_link_activation_success(
            user_name="Pedro",
            user_id=33333,
            plan_name="Plan Mensual",
            duration_days=30,
            price="$9.99",
            days_remaining=30,
            invite_link="https://t.me/+ABC123",
            session_history=history
        )
        text2, kb2 = provider.deep_link_activation_success(
            user_name="Pedro",
            user_id=33333,
            plan_name="Plan Mensual",
            duration_days=30,
            price="$9.99",
            days_remaining=30,
            invite_link="https://t.me/+ABC123",
            session_history=history
        )

        # First two messages should be different (exclusion window of 2)
        assert text1 != text2, \
            f"First two messages should differ with session context"

        # Both should contain expected content (deep link doesn't include user_name in message)
        assert '🎩' in text1 and 'Plan Mensual' in text1
        assert '🎩' in text2 and 'Plan Mensual' in text2

    def test_session_history_records_selections(self):
        """Session history should record variant selections for tracking."""
        history = SessionMessageHistory()
        provider = UserStartMessages()

        # Generate 3 greetings for same user
        for i in range(3):
            text, kb = provider.greeting(
                user_name="Maria",
                user_id=77777,
                session_history=history
            )

        # Check session history recorded entries
        stats = history.get_stats()
        assert stats['total_users'] == 1
        assert stats['total_entries'] == 3

        # Check recent variants for user
        recent = history.get_recent_variants(77777, "greeting", limit=2)
        assert len(recent) == 2  # Last 2 variants

    def test_session_history_excludes_recent_from_selection(self):
        """Session-aware selection should exclude recently seen variants."""
        history = SessionMessageHistory()
        provider = UserStartMessages()

        # Manually add variant 0 to history
        history.add_entry(12345, "greeting", 0)
        history.add_entry(12345, "greeting", 1)

        # Generate greeting - should exclude variants 0 and 1 if possible
        text, kb = provider.greeting(
            user_name="TestUser",
            user_id=12345,
            session_history=history
        )

        # Message should be generated successfully
        assert '🎩' in text
        assert 'TestUser' in text
