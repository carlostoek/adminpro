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
        weights: Optional[list[float]] = None
    ) -> str:
        """
        Choose a message variant randomly (with optional weights).

        Args:
            variants: List of message variations
            weights: Optional weights for each variant (must sum to 1.0)

        Returns:
            Selected message variant

        Voice Rationale:
            Prevents robotic repetition while maintaining Lucien's voice.
            Weighted choices enable "common vs rare" personality variations.

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
        """
        if not variants:
            raise ValueError("variants cannot be empty")

        if weights is None:
            return random.choice(variants)

        if len(weights) != len(variants):
            raise ValueError("weights and variants must have same length")

        return random.choices(variants, weights=weights, k=1)[0]
