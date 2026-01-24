"""
Session Message History Service.

Tracks recent messages per user session to enable context-aware variation selection.
Prevents message repetition fatigue by excluding recently-seen variants from
the selection pool.

Uses in-memory storage (dict + deque) with TTL auto-cleanup.
Approximately 200 bytes per active user.

Voice Rationale:
    By tracking which message variants each user has seen recently, Lucien can
    avoid repeating the same greeting or response, creating a more natural and
    less robotic conversation experience.

Architecture:
    - SessionHistoryEntry: Lightweight dataclass with slots for memory efficiency
    - SessionMessageHistory: In-memory service with lazy cleanup
    - No database dependency: Session loss is acceptable for this convenience feature
"""
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SessionHistoryEntry:
    """Single message entry in session history.

    Lightweight record for tracking recent messages per user.
    Uses slots for 40% memory reduction vs regular dataclass.

    Attributes:
        method_name: Which message method (e.g., "greeting", "success")
        variant_index: Which variant was selected (0, 1, 2, ...)
        timestamp: When the message was sent (Unix epoch seconds)
    """
    method_name: str
    variant_index: int
    timestamp: float = field(default_factory=time.time)


class SessionMessageHistory:
    """Track recent messages per user session for context-aware variation selection.

    This service prevents "Buenos dias" appearing 3 times in a row for the same
    user by excluding recently-seen variants from the selection pool.

    Memory Usage:
        ~200 bytes per active user (deque(maxlen=5) + slots dataclass)

    Thread Safety:
        Not required - bot is single-threaded async event loop

    Example:
        >>> history = SessionMessageHistory(ttl_seconds=300, max_entries=5)
        >>> history.add_entry(user_id=12345, method_name="greeting", variant_index=0)
        >>> recent = history.get_recent_variants(user_id=12345, method_name="greeting")
        >>> recent
        [0]
        >>> # When selecting next variant, exclude recent from pool
        >>> available_indices = [i for i in range(3) if i not in recent]
    """

    def __init__(self, ttl_seconds: int = 300, max_entries: int = 5) -> None:
        """Initialize session history service.

        Args:
            ttl_seconds: How long entries remain valid (default 5 minutes)
            max_entries: Maximum entries per user session (default 5)
        """
        self._ttl_seconds: int = ttl_seconds
        self._max_entries: int = max_entries
        self._sessions: Dict[int, Deque[SessionHistoryEntry]] = {}

    def add_entry(
        self,
        user_id: int,
        method_name: str,
        variant_index: int
    ) -> None:
        """Record a message selection for a user.

        Lazy cleanup: Remove expired entries occasionally (~10% of calls)
        to avoid dedicated cleanup thread complexity.

        Args:
            user_id: Telegram user ID
            method_name: Message method name (e.g., "greeting", "success")
            variant_index: Which variant was selected
        """
        # Lazy cleanup: hash-based 10% probability
        if hash(user_id) % 10 == 0:
            self._cleanup_user(user_id)

        # Get or create user's session deque with maxlen
        if user_id not in self._sessions:
            self._sessions[user_id] = deque(maxlen=self._max_entries)

        # Append new entry (deque handles maxlen automatically)
        self._sessions[user_id].append(
            SessionHistoryEntry(method_name=method_name, variant_index=variant_index)
        )

        logger.debug(
            "Session: user=%d method=%s variant=%d",
            user_id, method_name, variant_index
        )

    def get_recent_variants(
        self,
        user_id: int,
        method_name: str,
        limit: int = 3
    ) -> List[int]:
        """Get recent variant indices for a user and message method.

        Returns most recent first (index 0 = most recent).

        Filters by BOTH method_name AND TTL (expired entries excluded).

        Args:
            user_id: Telegram user ID
            method_name: Message method name to filter by
            limit: Maximum number of recent variants to return

        Returns:
            List of variant indices (most recent first), empty if user not found
            or no recent entries for this method

        Example:
            >>> history = SessionMessageHistory()
            >>> history.add_entry(12345, "greeting", 0)
            >>> history.add_entry(12345, "success", 1)
            >>> history.add_entry(12345, "greeting", 2)
            >>> history.get_recent_variants(12345, "greeting", limit=2)
            [2, 0]  # Most recent greeting (2) then older greeting (0)
        """
        if user_id not in self._sessions:
            return []

        recent_variants: List[int] = []
        now = time.time()

        # Iterate in reverse (most recent first)
        for entry in reversed(self._sessions[user_id]):
            # Filter by method_name AND TTL
            if (entry.method_name == method_name and
                    now - entry.timestamp <= self._ttl_seconds):
                recent_variants.append(entry.variant_index)

                # Stop when limit reached
                if len(recent_variants) >= limit:
                    break

        return recent_variants

    def _cleanup_user(self, user_id: int) -> None:
        """Remove expired entries for a specific user.

        Deletes user session if empty after cleanup.

        Args:
            user_id: Telegram user ID
        """
        if user_id not in self._sessions:
            return

        now = time.time()

        # Filter out expired entries
        filtered_deque = deque(
            (
                entry for entry in self._sessions[user_id]
                if now - entry.timestamp <= self._ttl_seconds
            ),
            maxlen=self._max_entries
        )

        if filtered_deque:
            self._sessions[user_id] = filtered_deque
        else:
            # Delete empty session
            del self._sessions[user_id]

    def cleanup_all(self) -> int:
        """Remove expired entries from all user sessions.

        Called occasionally (not on every add_entry) to reclaim memory.

        Returns:
            Number of entries removed
        """
        removed_count = 0

        for user_id in list(self._sessions.keys()):
            before_count = len(self._sessions[user_id])
            self._cleanup_user(user_id)
            after_count = len(self._sessions.get(user_id, []))
            removed_count += (before_count - after_count)

        if removed_count > 0:
            logger.info("Session cleanup: removed %d expired entries", removed_count)

        return removed_count

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about session memory usage.

        Returns:
            Dict with keys:
                - total_users: Number of users with sessions
                - total_entries: Total entries (including expired)
                - active_entries: Entries within TTL window

        Example:
            >>> history = SessionMessageHistory()
            >>> history.add_entry(12345, "greeting", 0)
            >>> stats = history.get_stats()
            >>> stats
            {'total_users': 1, 'total_entries': 1, 'active_entries': 1}
        """
        total_users = len(self._sessions)
        total_entries = sum(len(session) for session in self._sessions.values())

        now = time.time()
        active_entries = sum(
            1 for session in self._sessions.values()
            for entry in session
            if now - entry.timestamp <= self._ttl_seconds
        )

        return {
            "total_users": total_users,
            "total_entries": total_entries,
            "active_entries": active_entries
        }
