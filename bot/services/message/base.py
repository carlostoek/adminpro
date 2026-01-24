"""
Base Message Provider - Foundation for all message providers.

This module provides the abstract base class that enforces stateless interface
and provides utility methods for template composition.
"""
import random
from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseMessageProvider(ABC):
    """
    Base abstract class for all message providers.

    Enforces stateless interface: providers MUST NOT store session or bot
    as instance variables. All context must be passed as method parameters.

    Voice Rules (from docs/guia-estilo.md):
    - Siempre habla de "usted", nunca tutea
    - Usa lenguaje refinado pero natural
    - Emoji caracteristico: 🎩 para Lucien
    - Referencias a Diana con 🌸
    - Nunca usa jerga técnica directa
    - Emplea pausas dramáticas con "..."

    Anti-Patterns to Avoid:
    - NEVER: self.session, self.bot (causes memory leaks)
    - NEVER: Formatting logic in handlers (causes voice inconsistency)
    - NEVER: Hardcoded strings without voice rationale in docstring
    """

    def _compose(self, header: str, body: str, footer: str = "") -> str:
        """
        Compose message from header, body, and optional footer.

        Args:
            header: Message header (e.g., "🎩 Lucien:")
            body: Main message content
            footer: Optional footer text

        Returns:
            Composed HTML-formatted message

        Voice Rationale:
            Separating composition enables template reuse while maintaining
            consistent Lucien voice across all message types.

        Examples:
            >>> provider = BaseMessageProvider()
            >>> msg = provider._compose(
            ...     "🎩 Lucien:",
            ...     "Bienvenido al círculo exclusivo.",
            ...     "Diana lo espera."
            ... )
            >>> print(msg)
            🎩 Lucien:

            Bienvenido al círculo exclusivo.

            Diana lo espera.

            >>> msg = provider._compose("🎩 Lucien:", "Hola")
            >>> print(msg)
            🎩 Lucien:

            Hola
        """
        parts = [header, body]
        if footer:
            parts.append(footer)
        return "\n\n".join(parts)

    def _choose_variant(
        self,
        variants: list[str],
        weights: Optional[list[float]] = None,
        user_id: Optional[int] = None,
        method_name: Optional[str] = None,
        session_history: Optional["SessionMessageHistory"] = None
    ) -> str:
        """
        Choose a message variant randomly (with optional weights and session context).

        When session context is provided (user_id, method_name, session_history),
        excludes recently-seen variants from selection to prevent repetition.

        Args:
            variants: List of message variations
            weights: Optional weights for each variant (must sum to 1.0)
            user_id: Optional Telegram user ID for session-aware selection
            method_name: Optional message method name for session tracking
            session_history: Optional SessionMessageHistory for context awareness

        Returns:
            Selected message variant

        Voice Rationale:
            Prevents robotic repetition while maintaining Lucien's voice.
            Weighted choices enable "common vs rare" personality variations.
            Session-aware selection prevents "Buenos dias" appearing 3 times
            in a row for the same user by excluding recent variants.

        Raises:
            ValueError: If variants is empty or weights length mismatch

        Examples:
            Equal weights (random choice):
                >>> provider = BaseMessageProvider()
                >>> variants = ["Hola", "Bienvenido"]
                >>> result = provider._choose_variant(variants)
                >>> result in variants
                True

            Weighted (80% common, 20% rare):
                >>> variants = ["Buen día", "Saludos"]
                >>> weights = [0.8, 0.2]
                >>> # "Buen día" appears ~80% of time
                >>> result = provider._choose_variant(variants, weights)
                >>> result in variants
                True

            Session-aware (excludes recent variants):
                >>> from bot.services.message.session_history import SessionMessageHistory
                >>> history = SessionMessageHistory()
                >>> history.add_entry(12345, "greeting", 0)  # User saw variant 0
                >>> # Next selection excludes variant 0 if possible
                >>> variants = ["Buenos días", "Buenas tardes", "Buenas noches"]
                >>> result = provider._choose_variant(
                ...     variants, user_id=12345, method_name="greeting",
                ...     session_history=history
                ... )
                >>> # result will be variant 1 or 2 (not 0)
        """
        if not variants:
            raise ValueError("variants cannot be empty")

        # Backward compatible: use existing random selection when no session context
        if session_history is None or user_id is None or method_name is None:
            if weights is None:
                return random.choice(variants)

            if len(weights) != len(variants):
                raise ValueError("weights and variants must have same length")

            return random.choices(variants, weights=weights, k=1)[0]

        # Session-aware selection: exclude recent variants
        recent_indices = session_history.get_recent_variants(
            user_id, method_name, limit=2
        )

        # Build available indices (excluding recent)
        available_indices = [
            i for i in range(len(variants))
            if i not in recent_indices
        ]

        # If all variants would be excluded, fall back to all variants
        if not available_indices:
            available_indices = list(range(len(variants)))

        # Select from available indices
        if weights is None:
            selected_idx = random.choice(available_indices)
        else:
            if len(weights) != len(variants):
                raise ValueError("weights and variants must have same length")

            # Adjust weights to available subset
            available_weights = [weights[i] for i in available_indices]
            selected_idx = random.choices(
                available_indices,
                weights=available_weights,
                k=1
            )[0]

        # Record selection in session history
        session_history.add_entry(user_id, method_name, selected_idx)

        return variants[selected_idx]
