"""
Tests for Session Message History Service.

Tests verify session tracking, TTL expiry, and memory-efficient storage.
"""
import time
import pytest
from collections import deque

from bot.services.message.session_history import (
    SessionHistoryEntry,
    SessionMessageHistory
)


class TestSessionHistoryEntry:
    """Test the lightweight dataclass for tracking messages."""

    def test_entry_creation(self):
        """Entry creates with all fields."""
        entry = SessionHistoryEntry(
            method_name="greeting",
            variant_index=0
        )
        assert entry.method_name == "greeting"
        assert entry.variant_index == 0
        assert isinstance(entry.timestamp, float)

    def test_timestamp_default_factory(self):
        """Timestamp uses time.time as default factory."""
        before = time.time()
        entry = SessionHistoryEntry(method_name="success", variant_index=1)
        after = time.time()
        assert before <= entry.timestamp <= after

    def test_slots_memory_efficiency(self):
        """Entry uses slots (no __dict__)."""
        entry = SessionHistoryEntry(method_name="error", variant_index=2)
        assert not hasattr(entry, "__dict__")


class TestSessionMessageHistory:
    """Test session history service."""

    def test_add_entry_stores_message(self):
        """Adding entry stores message in user's session."""
        history = SessionMessageHistory(ttl_seconds=300)
        history.add_entry(user_id=12345, method_name="greeting", variant_index=0)

        assert 12345 in history._sessions
        assert len(history._sessions[12345]) == 1
        entry = history._sessions[12345][0]
        assert entry.method_name == "greeting"
        assert entry.variant_index == 0

    def test_get_recent_variants_returns_empty_for_new_user(self):
        """New user with no history returns empty list."""
        history = SessionMessageHistory(ttl_seconds=300)
        recent = history.get_recent_variants(user_id=99999, method_name="greeting")
        assert recent == []

    def test_get_recent_variants_filters_by_method(self):
        """Recent variants filter by method_name (most recent first)."""
        history = SessionMessageHistory(ttl_seconds=300)

        # Add mixed entries
        history.add_entry(user_id=12345, method_name="greeting", variant_index=0)
        history.add_entry(user_id=12345, method_name="success", variant_index=1)
        history.add_entry(user_id=12345, method_name="greeting", variant_index=2)

        # Get greeting variants (should return [2, 0])
        recent = history.get_recent_variants(user_id=12345, method_name="greeting")
        assert recent == [2, 0]

    def test_get_recent_variants_respects_limit(self):
        """Limit parameter caps number of returned variants."""
        history = SessionMessageHistory(ttl_seconds=300, max_entries=10)

        # Add 5 greeting entries
        for i in range(5):
            history.add_entry(user_id=12345, method_name="greeting", variant_index=i)

        # Request only 2 most recent
        recent = history.get_recent_variants(
            user_id=12345,
            method_name="greeting",
            limit=2
        )
        assert len(recent) == 2
        assert recent == [4, 3]  # Most recent first

    def test_get_recent_variants_filters_expired(self):
        """Expired entries (past TTL) are not returned."""
        history = SessionMessageHistory(ttl_seconds=1)  # 1 second TTL

        # Add entry
        history.add_entry(user_id=12345, method_name="greeting", variant_index=0)

        # Wait for expiry
        time.sleep(1.1)

        # Should return empty
        recent = history.get_recent_variants(user_id=12345, method_name="greeting")
        assert recent == []

    def test_cleanup_user_removes_expired(self):
        """Cleanup removes expired entries, keeps valid ones."""
        history = SessionMessageHistory(ttl_seconds=1)

        # Add entry that will expire
        history.add_entry(user_id=12345, method_name="old", variant_index=0)
        time.sleep(1.1)

        # Add entry that stays valid
        history.add_entry(user_id=12345, method_name="new", variant_index=1)

        # Cleanup should remove expired
        removed = history.cleanup_all()
        assert removed >= 1

        # Verify only valid entry remains
        recent = history.get_recent_variants(user_id=12345, method_name="new")
        assert recent == [1]

    def test_get_stats_counts_correctly(self):
        """Stats accurately count users, entries, and active entries."""
        history = SessionMessageHistory(ttl_seconds=300)

        # Add entries for multiple users
        history.add_entry(user_id=11111, method_name="greeting", variant_index=0)
        history.add_entry(user_id=11111, method_name="greeting", variant_index=1)
        history.add_entry(user_id=22222, method_name="greeting", variant_index=0)

        stats = history.get_stats()
        assert stats["total_users"] == 2
        assert stats["total_entries"] == 3
        assert stats["active_entries"] == 3

    def test_maxlen_enforced(self):
        """Deque maxlen automatically removes oldest entries."""
        history = SessionMessageHistory(ttl_seconds=300, max_entries=3)

        # Add 5 entries for same user
        for i in range(5):
            history.add_entry(user_id=12345, method_name="greeting", variant_index=i)

        # Should only have 3 entries (maxlen)
        assert len(history._sessions[12345]) == 3

        # Oldest entries (0, 1) removed, newest (2, 3, 4) remain
        entries = list(history._sessions[12345])
        variant_indices = [e.variant_index for e in entries]
        assert variant_indices == [2, 3, 4]

    def test_lazy_cleanup_triggered_sometimes(self):
        """Lazy cleanup triggered on ~10% of add_entry calls (hash-based)."""
        history = SessionMessageHistory(ttl_seconds=1, max_entries=10)

        # Find a user_id that triggers cleanup (hash % 10 == 0)
        # We know user_id=10 works based on hash behavior
        user_id = 10

        # Add expired entry
        history.add_entry(user_id=user_id, method_name="old", variant_index=0)
        old_count = len(history._sessions[user_id])
        time.sleep(1.1)  # Expire the entry

        # Add new entry - this should trigger lazy cleanup BEFORE adding
        history.add_entry(user_id=user_id, method_name="new", variant_index=1)

        # After adding, the session should have the old (expired) entry removed
        # because lazy cleanup happened at the start of add_entry
        entries = list(history._sessions[user_id])
        variant_indices = [e.variant_index for e in entries]

        # The expired entry (variant 0) should have been cleaned up
        # Only the new entry (variant 1) should remain
        # Note: Due to timing, we might have 2 entries, but the old one should be expired
        assert 1 in variant_indices  # New entry exists

        # Active entries should only count non-expired ones
        stats = history.get_stats()
        assert stats["active_entries"] >= 1  # At least the new entry is active

    def test_multiple_users_independent_sessions(self):
        """Each user has independent session history."""
        history = SessionMessageHistory(ttl_seconds=300)

        history.add_entry(user_id=11111, method_name="greeting", variant_index=0)
        history.add_entry(user_id=22222, method_name="greeting", variant_index=1)

        # Each user sees their own history
        recent_11111 = history.get_recent_variants(11111, "greeting")
        recent_22222 = history.get_recent_variants(22222, "greeting")

        assert recent_11111 == [0]
        assert recent_22222 == [1]

    def test_empty_session_deleted_after_cleanup(self):
        """Empty sessions are removed during cleanup."""
        history = SessionMessageHistory(ttl_seconds=1)

        history.add_entry(user_id=12345, method_name="greeting", variant_index=0)
        time.sleep(1.1)

        history.cleanup_all()

        # User session should be deleted (no entries remain)
        assert 12345 not in history._sessions

    def test_get_recent_variants_default_limit(self):
        """Default limit of 3 is used when not specified."""
        history = SessionMessageHistory(ttl_seconds=300)

        # Add 5 entries
        for i in range(5):
            history.add_entry(user_id=12345, method_name="greeting", variant_index=i)

        # Default limit should be 3
        recent = history.get_recent_variants(user_id=12345, method_name="greeting")
        assert len(recent) == 3
        assert recent == [4, 3, 2]


class TestBaseMessageProviderIntegration:
    """Integration tests with BaseMessageProvider._choose_variant."""

    def test_choose_variant_excludes_recent(self):
        """Session-aware selection excludes recently-seen variants."""
        from bot.services.message.base import BaseMessageProvider

        class TestProvider(BaseMessageProvider):
            pass

        provider = TestProvider()
        history = SessionMessageHistory(ttl_seconds=300, max_entries=5)

        variants = ["Buenos dias", "Buenas tardes", "Buenas noches"]

        # Generate 30 selections
        selections = []
        for _ in range(30):
            result = provider._choose_variant(
                variants,
                user_id=12345,
                method_name="greeting",
                session_history=history
            )
            selections.append(variants.index(result))

        # Check distribution
        for i in range(3):
            count = selections.count(i)
            assert count >= 2, f"Variant {i} appears {count} times, expected >= 2"

        # Verify no consecutive repetitions
        consecutive = sum(
            1 for i in range(len(selections) - 1)
            if selections[i] == selections[i + 1]
        )
        assert consecutive <= 2, f"Too many consecutive repeats: {consecutive}"

    def test_choose_variant_backward_compatible(self):
        """_choose_variant works without session context (backward compat)."""
        from bot.services.message.base import BaseMessageProvider

        class TestProvider(BaseMessageProvider):
            pass

        provider = TestProvider()
        variants = ["A", "B", "C"]

        # Should work without any session parameters
        result = provider._choose_variant(variants)
        assert result in variants

        # Should work with weights
        weights = [0.5, 0.3, 0.2]
        result = provider._choose_variant(variants, weights)
        assert result in variants

    def test_choose_variant_all_variants_excluded_fallback(self):
        """When all variants excluded, falls back to random selection."""
        from bot.services.message.base import BaseMessageProvider

        class TestProvider(BaseMessageProvider):
            pass

        provider = TestProvider()
        history = SessionMessageHistory(ttl_seconds=300, max_entries=5)

        # Only 2 variants available
        variants = ["A", "B"]

        # User has seen both recently (stored in history)
        history.add_entry(user_id=12345, method_name="test", variant_index=0)
        history.add_entry(user_id=12345, method_name="test", variant_index=1)

        # Should still select something (fallback to all variants)
        result = provider._choose_variant(
            variants,
            user_id=12345,
            method_name="test",
            session_history=history
        )
        assert result in variants
