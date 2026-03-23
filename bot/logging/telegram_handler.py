"""
Telegram Alert Handler implementation.

Provides handler, filter, formatter and wiring function for sending
high-priority log alerts to a Telegram chat.

Design principles:
- stdlib only (no new pip dependencies)
- QueueHandler + QueueListener pattern (never blocks asyncio event loop)
- Smart filtering (high/low priority namespaces, deduplication)
- Graceful degradation (handler errors never crash the bot)
"""
import json
import logging
import logging.handlers
import queue
import time
import traceback
import urllib.request
from typing import Dict, Tuple


# High-priority namespaces: these get WARNING+ alerts
HIGH_PRIORITY_PREFIXES: Tuple[str, ...] = (
    "bot.services.subscription",
    "bot.services.wallet",
    "bot.services.pricing",
    "bot.services.reward",
    "bot.services.shop",
    "bot.services.vip_entry",
    "bot.services.role_change",
    "bot.handlers.user.vip_entry",
    "bot.handlers.admin",
    "config",
)

# Low-priority namespaces: these never trigger alerts (too noisy)
LOW_PRIORITY_PREFIXES: Tuple[str, ...] = (
    "aiogram",
    "apscheduler",
    "bot.background.tasks",
    "bot.handlers.user.free_join_request",
    "sqlalchemy",
    "aiosqlite",
    "asyncio",
)

# Emoji mapping for log levels
_LEVEL_EMOJI: Dict[int, str] = {
    logging.WARNING: "⚠️",
    logging.ERROR: "🔴",
    logging.CRITICAL: "🚨",
}


class AlertFormatter(logging.Formatter):
    """
    Formatter for Telegram alerts with HTML formatting.

    Features:
    - Level emoji prefix
    - Shortened logger name (last 2 components)
    - Truncated traceback in <pre> block
    - Overall 4000 char limit (Telegram message limit)
    """

    def format(self, record: logging.LogRecord) -> str:
        emoji = _LEVEL_EMOJI.get(record.levelno, "📋")
        parts = record.name.split(".")
        short_name = ".".join(parts[-2:]) if len(parts) > 2 else record.name
        msg = record.getMessage()
        lines = [
            f"{emoji} <b>{record.levelname}</b> | <code>{short_name}</code>",
            msg,
        ]
        if record.exc_info:
            tb = "".join(traceback.format_exception(*record.exc_info))
            header_len = len("\n".join(lines))
            max_tb = 3500 - header_len
            if max_tb >= 200:
                lines.append(f"<pre>{tb[-max_tb:]}</pre>")
        full = "\n".join(lines)
        return full[:4000]


class SmartAlertFilter(logging.Filter):
    """
    Filter that implements smart alert routing with deduplication.

    Rules:
    1. LOW_PRIORITY namespaces: never alert (regardless of level)
    2. CRITICAL: always alert (no deduplication)
    3. ERROR: alert with deduplication
    4. WARNING: only from HIGH_PRIORITY namespaces, with deduplication
    5. INFO/DEBUG: never alert
    """

    def __init__(self, dedup_window_seconds: int = 60) -> None:
        super().__init__()
        self._dedup_window = dedup_window_seconds
        self._seen: Dict[Tuple[str, str], float] = {}  # INSTANCE variable (not class)

    def filter(self, record: logging.LogRecord) -> bool:
        # 1. Drop all LOW_PRIORITY namespaces unconditionally
        for prefix in LOW_PRIORITY_PREFIXES:
            if record.name == prefix or record.name.startswith(prefix + "."):
                return False

        # 2. CRITICAL always passes — no dedup
        if record.levelno >= logging.CRITICAL:
            return True

        # 3. ERROR passes with dedup
        if record.levelno >= logging.ERROR:
            return self._check_dedup(record)

        # 4. WARNING only from HIGH_PRIORITY with dedup
        if record.levelno >= logging.WARNING:
            for prefix in HIGH_PRIORITY_PREFIXES:
                if record.name == prefix or record.name.startswith(prefix + "."):
                    return self._check_dedup(record)
            return False

        # 5. INFO/DEBUG never alert
        return False

    def _check_dedup(self, record: logging.LogRecord) -> bool:
        """Check if record passes deduplication window."""
        now = time.time()
        key = (record.name, record.getMessage())
        last_seen = self._seen.get(key, 0.0)
        if now - last_seen >= self._dedup_window:
            self._seen[key] = now
            self._cleanup_old_entries(now)
            return True
        return False

    def _cleanup_old_entries(self, now: float) -> None:
        """Remove entries older than 2x dedup window to prevent memory growth."""
        cutoff = now - (self._dedup_window * 2)
        self._seen = {k: v for k, v in self._seen.items() if v > cutoff}


class TelegramAlertHandler(logging.Handler):
    """
    Handler that sends log alerts to Telegram via Bot API.

    Uses urllib.request (stdlib) for HTTP POST. Runs in QueueListener
    background thread so it never blocks the asyncio event loop.

    Errors during emit() are handled gracefully (via handleError)
    and never propagate out.
    """

    def __init__(self, bot_token: str, chat_id: str, timeout: int = 5) -> None:
        super().__init__()
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._timeout = timeout
        self._url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    def emit(self, record: logging.LogRecord) -> None:
        """Send log record to Telegram chat."""
        try:
            text = self.format(record)
            payload = json.dumps({
                "chat_id": self._chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_notification": record.levelno < logging.ERROR,
            }).encode("utf-8")
            req = urllib.request.Request(
                self._url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                resp.read()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)  # Never raises; respects logging.raiseExceptions


def setup_telegram_alert_handler(
    bot_token: str,
    chat_id: str,
    dedup_window_seconds: int = 60
) -> None:
    """
    Wire TelegramAlertHandler into the root logger via QueueHandler+QueueListener.

    This is the main entry point for configuring the alert handler.

    Args:
        bot_token: Telegram bot token for sending alerts
        chat_id: Telegram chat ID to receive alerts
        dedup_window_seconds: Deduplication window for non-CRITICAL alerts

    Safe to call multiple times — exits early if already configured.
    Filter lives on TelegramAlertHandler (not QueueHandler) per official recommendation.

    Design:
    - QueueHandler is the cheap gate on the hot path (asyncio event loop side)
    - QueueListener runs in a background daemon thread (never blocks event loop)
    - TelegramAlertHandler does the actual HTTP POST
    """
    root_logger = logging.getLogger()

    # Guard: do not add a second listener if already configured
    if hasattr(root_logger, "_telegram_listener"):
        return

    # Build real (blocking) handler
    telegram_handler = TelegramAlertHandler(bot_token, chat_id)
    telegram_handler.setLevel(logging.WARNING)
    telegram_handler.addFilter(SmartAlertFilter(dedup_window_seconds))
    telegram_handler.setFormatter(AlertFormatter())

    # Queue for async decoupling
    log_queue: queue.Queue = queue.Queue(maxsize=-1)

    # QueueHandler is the cheap gate on the hot path (asyncio event loop side)
    queue_handler = logging.handlers.QueueHandler(log_queue)
    queue_handler.setLevel(logging.WARNING)
    # NOTE: SmartAlertFilter is NOT added to queue_handler — only to telegram_handler

    # QueueListener runs in a background daemon thread (never blocks event loop)
    listener = logging.handlers.QueueListener(
        log_queue,
        telegram_handler,
        respect_handler_level=True,
    )
    listener.start()

    root_logger.addHandler(queue_handler)
    root_logger._telegram_listener = listener  # type: ignore[attr-defined]
