"""
Telegram Alert Handler for logging.

Provides a secondary logging handler that forwards high-value log events
to an admin Telegram chat via Bot API.

Usage:
    from bot.logging import setup_telegram_alert_handler
    setup_telegram_alert_handler(bot_token, chat_id, dedup_window_seconds=60)
"""
from bot.logging.telegram_handler import (
    TelegramAlertHandler,
    SmartAlertFilter,
    AlertFormatter,
    setup_telegram_alert_handler,
)

__all__ = [
    "TelegramAlertHandler",
    "SmartAlertFilter",
    "AlertFormatter",
    "setup_telegram_alert_handler",
]
