"""
Message Service Package

Provides centralized message generation with Lucien's voice consistency.

Architecture:
- BaseMessageProvider: Abstract base enforcing stateless interface
- CommonMessages: Shared messages (errors, success, greetings)
- AdminMessages: Admin-specific messages (by navigation flow)
- UserMessages: User-specific messages (by navigation flow)

All providers are stateless: no session/bot stored as instance variables.
All messages use formatters from bot.utils.formatters for dates/numbers.

Usage in handlers:
    from bot.services.container import ServiceContainer

    # Lazy-loaded via ServiceContainer.message property
    msg = container.message.common.error('something failed')
"""

from .base import BaseMessageProvider

__all__ = ["BaseMessageProvider"]
