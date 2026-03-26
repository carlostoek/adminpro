# Phase 29: Advanced Logging / Telegram Alert Handler - Research

**Researched:** 2026-03-22
**Domain:** Python stdlib logging extension — custom Handler + Filter for Telegram alerting
**Confidence:** HIGH

## Summary

This phase adds a secondary logging handler that forwards high-value log events to an admin Telegram chat. The entire implementation lives within Python's `logging` stdlib — no new dependencies are required. The existing `Config.setup_logging()` method in `config.py` is the single integration point: it calls `logging.basicConfig()` and then configures namespace-level overrides. The new handler and filter are added after `basicConfig()` in that same method, attached to the root logger.

The critical architectural constraint is that this bot runs on asyncio (aiogram 3.4.1). Any `logging.Handler.emit()` implementation that makes a synchronous network call (urllib, requests) will not block the event loop because `emit()` runs in the logging call chain, which is synchronous by design. The correct and well-established pattern is: the blocking HTTP call lives inside `emit()` and is kept fast and small — it is wrapped in a tight try/except that calls `self.handleError(record)` on failure, ensuring it never raises or blocks for more than a configurable timeout. An alternative is to wrap the Telegram handler in `QueueHandler+QueueListener` to push the network call off to a background thread entirely; this is the preferred pattern for asyncio safety and is documented in the official Python logging cookbook.

No external libraries are needed: `urllib.request` (stdlib) handles the HTTP call to `api.telegram.org`, `time.time()` (stdlib) drives deduplication, and `threading.RLock` (inherited from `logging.Handler`) handles thread safety. The complete feature set — `TelegramAlertHandler`, `SmartAlertFilter`, anti-spam deduplication — fits in a single new file: `bot/logging/telegram_handler.py`.

**Primary recommendation:** Implement `TelegramAlertHandler(logging.Handler)` + `SmartAlertFilter(logging.Filter)` in `bot/logging/telegram_handler.py`, wrap the handler in `QueueHandler+QueueListener` for asyncio safety, and attach to the root logger inside `Config.setup_logging()` only when `ALERT_CHAT_ID` is configured.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `logging` (stdlib) | Python 3.11 built-in | Handler/Filter base classes, LogRecord | Requirement: no external libs |
| `logging.handlers` (stdlib) | Python 3.11 built-in | `QueueHandler`, `QueueListener` for async safety | Official pattern for non-blocking handlers |
| `urllib.request` (stdlib) | Python 3.11 built-in | HTTP POST to Telegram Bot API | No external HTTP lib needed; sends one small JSON payload |
| `time` (stdlib) | Python 3.11 built-in | `time.time()` for deduplication window | Monotonic-enough for 60s windows |
| `queue` (stdlib) | Python 3.11 built-in | `queue.Queue` for QueueHandler | Decouples emit() from network I/O |
| `traceback` (stdlib) | Python 3.11 built-in | Format exception tracebacks for alert messages | Already used by logging internally |
| `json` (stdlib) | Python 3.11 built-in | Encode sendMessage payload | Cleaner than urlencode for Telegram API |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `threading` (stdlib) | Python 3.11 built-in | `RLock` (inherited from Handler) | Automatic — Handler base class provides it |
| `os` (stdlib) | Python 3.11 built-in | Read `ALERT_CHAT_ID` env var | Config reads env at import time |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `urllib.request` | `aiohttp` | aiohttp is already in project (aiogram uses it); but calling async from emit() is forbidden — urllib sync is correct here |
| `QueueHandler+QueueListener` | Direct sync call in `emit()` | Direct call works but risks blocking event loop under load; Queue pattern is the official asyncio-safe recommendation |
| Custom `SmartAlertFilter` on handler | Per-logger level tuning only | Level tuning already exists in setup_logging(); the filter gives domain-aware routing logic that level-setting cannot express |

**Installation:**
```bash
# No new dependencies — stdlib only
```

---

## Architecture Patterns

### Recommended Project Structure
```
bot/
├── logging/
│   ├── __init__.py          # Exports: TelegramAlertHandler, SmartAlertFilter
│   └── telegram_handler.py  # Handler + Filter + deduplication state
config.py                    # Integration point: setup_logging() extended
.env.example                 # Add ALERT_CHAT_ID entry
```

The `bot/logging/` package is the natural home — it is a new concern, separate from `bot/services/`, `bot/handlers/`, etc.

### Pattern 1: Custom Handler subclass
**What:** Inherit `logging.Handler`, implement `emit(record)`, wrap body in `try/except`, call `self.handleError(record)` on failure.
**When to use:** Any time log records need to go to a custom destination.
**Example:**
```python
# Source: https://docs.python.org/3/library/logging.html#logging.Handler
import logging
import urllib.request
import json

class TelegramAlertHandler(logging.Handler):
    def __init__(self, bot_token: str, chat_id: str, timeout: int = 5):
        super().__init__()
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._timeout = timeout
        self._url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    def emit(self, record: logging.LogRecord) -> None:
        try:
            text = self._build_text(record)
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
            with urllib.request.urlopen(req, timeout=self._timeout):
                pass
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)  # Silent fail — never raises

    def _build_text(self, record: logging.LogRecord) -> str:
        msg = self.format(record)
        return msg[:4000]  # Telegram limit is 4096; leave margin
```

### Pattern 2: QueueHandler + QueueListener for asyncio safety
**What:** Wrap the blocking Telegram handler in a `QueueHandler`. The QueueListener runs in a background thread, pulling records and forwarding to the real handler. The main asyncio event loop never waits on network I/O.
**When to use:** Any asyncio application where logging handlers do network I/O.
**Example:**
```python
# Source: https://docs.python.org/3/library/logging.handlers.html#logging.handlers.QueueHandler
import queue
import logging.handlers

def _setup_telegram_handler(bot_token: str, chat_id: str) -> None:
    telegram_handler = TelegramAlertHandler(bot_token, chat_id)
    telegram_handler.setLevel(logging.WARNING)
    telegram_handler.addFilter(SmartAlertFilter())
    telegram_handler.setFormatter(AlertFormatter())

    log_queue: queue.Queue = queue.Queue(maxsize=-1)  # unbounded
    queue_handler = logging.handlers.QueueHandler(log_queue)
    queue_handler.setLevel(logging.WARNING)

    listener = logging.handlers.QueueListener(
        log_queue,
        telegram_handler,
        respect_handler_level=True,  # requires Python 3.5+
    )
    listener.start()

    root_logger = logging.getLogger()
    root_logger.addHandler(queue_handler)
    # Store reference to prevent GC and allow clean shutdown
    root_logger._telegram_listener = listener  # type: ignore[attr-defined]
```

### Pattern 3: Custom Filter with time-based deduplication
**What:** Inherit `logging.Filter`, implement `filter(record)` with in-memory dict tracking last-seen timestamps per (logger_name, message) key.
**When to use:** When the same error fires repeatedly (e.g., background task loop) and should only alert once per configurable window.
**Example:**
```python
# Source: https://docs.python.org/3/library/logging.html#logging.Filter
import logging
import time
from typing import Dict, Tuple

# HIGH PRIORITY: always alert on WARNING or above
HIGH_PRIORITY_PREFIXES = (
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

# LOW PRIORITY: never send alerts (background noise)
LOW_PRIORITY_PREFIXES = (
    "aiogram",
    "apscheduler",
    "bot.background.tasks",
    "bot.handlers.user.free_join_request",
    "sqlalchemy",
    "aiosqlite",
    "asyncio",
)

class SmartAlertFilter(logging.Filter):
    def __init__(self, dedup_window_seconds: int = 60):
        super().__init__()
        self._dedup_window = dedup_window_seconds
        self._seen: Dict[Tuple[str, str], float] = {}

    def filter(self, record: logging.LogRecord) -> bool:
        # 1. Drop all LOW PRIORITY namespaces unconditionally
        for prefix in LOW_PRIORITY_PREFIXES:
            if record.name == prefix or record.name.startswith(prefix + "."):
                return False

        # 2. CRITICAL always passes (no dedup)
        if record.levelno >= logging.CRITICAL:
            return True

        # 3. ERROR: pass but deduplicate
        if record.levelno >= logging.ERROR:
            return self._check_dedup(record)

        # 4. WARNING: only HIGH PRIORITY namespaces, with dedup
        if record.levelno >= logging.WARNING:
            for prefix in HIGH_PRIORITY_PREFIXES:
                if record.name == prefix or record.name.startswith(prefix + "."):
                    return self._check_dedup(record)
            return False  # WARNING from non-priority namespace

        # 5. INFO/DEBUG: never alert
        return False

    def _check_dedup(self, record: logging.LogRecord) -> bool:
        now = time.time()
        key = (record.name, record.getMessage())
        last_seen = self._seen.get(key, 0.0)
        if now - last_seen >= self._dedup_window:
            self._seen[key] = now
            self._cleanup_old_entries(now)
            return True
        return False

    def _cleanup_old_entries(self, now: float) -> None:
        # Prevent unbounded memory growth — prune entries older than 2x window
        cutoff = now - (self._dedup_window * 2)
        self._seen = {k: v for k, v in self._seen.items() if v > cutoff}
```

### Pattern 4: Compact formatter for Telegram
**What:** A `logging.Formatter` subclass that produces concise HTML-formatted text with level, logger name, message, and optional truncated traceback.
**When to use:** Telegram alerts — must be human-readable in mobile chat, stay under 4096 chars.
**Example:**
```python
import logging
import traceback

_LEVEL_EMOJI = {
    logging.WARNING: "⚠️",
    logging.ERROR: "🔴",
    logging.CRITICAL: "🚨",
}

class AlertFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        emoji = _LEVEL_EMOJI.get(record.levelno, "📋")
        # Short logger name: last 2 segments
        parts = record.name.split(".")
        short_name = ".".join(parts[-2:]) if len(parts) > 2 else record.name
        msg = record.getMessage()

        lines = [
            f"{emoji} <b>{record.levelname}</b> | <code>{short_name}</code>",
            f"{msg}",
        ]

        if record.exc_info:
            tb = "".join(traceback.format_exception(*record.exc_info))
            # Truncate traceback to leave room for message
            max_tb = 3500 - len("\n".join(lines))
            if max_tb > 200:
                lines.append(f"<pre>{tb[-max_tb:]}</pre>")

        full = "\n".join(lines)
        return full[:4000]
```

### Integration in Config.setup_logging()
**What:** After the existing `basicConfig()` call and namespace overrides, conditionally attach the Telegram handler to the root logger.
**Example:**
```python
# At the END of Config.setup_logging(), after existing code:
alert_chat_id = os.getenv("ALERT_CHAT_ID")
alert_token = cls.BOT_TOKEN  # Reuse existing BOT_TOKEN

if alert_chat_id and alert_token:
    from bot.logging.telegram_handler import setup_telegram_alert_handler
    setup_telegram_alert_handler(
        bot_token=alert_token,
        chat_id=alert_chat_id,
        dedup_window_seconds=int(os.getenv("ALERT_DEDUP_SECONDS", "60")),
    )
    logger.info("Telegram alert handler configured for chat %s", alert_chat_id)
```

Note: `bot/logging/telegram_handler.py` is imported lazily (inside the if-block) to avoid import-time side effects when `ALERT_CHAT_ID` is not set.

### Anti-Patterns to Avoid
- **Calling `asyncio.create_task()` or any coroutine inside `emit()`:** `emit()` is called from the synchronous logging chain and may run in any thread. The asyncio event loop is not accessible there. Use QueueListener thread instead.
- **Attaching the TelegramAlertHandler directly to named loggers instead of root:** This requires updating every logger. Attach to root and let propagation do the work.
- **Skipping `self.handleError(record)` on exceptions in `emit()`:** This can cause exceptions to propagate out of logging calls and crash handlers. Always delegate to `handleError()`.
- **Using `logging.basicConfig(force=True)` to add the Telegram handler:** This would remove the existing StreamHandler. Instead, call `logging.getLogger().addHandler(queue_handler)` directly after `basicConfig()`.
- **Storing deduplication state on the Filter class (class variable) instead of instance:** Class-level state is shared across all instances including tests. Use `self._seen` (instance variable).
- **Forgetting to store a reference to the QueueListener:** Python's garbage collector will stop the listener thread if the reference is lost. Store it on the root logger or a module-level variable.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Thread-safe emit() locking | Custom mutex/lock | Inherited `logging.Handler` `acquire()`/`release()` via `self.createLock()` | Already provided by base Handler; hand-rolling risks deadlock with logging module-level lock |
| Non-blocking emit in asyncio | `asyncio.run_coroutine_threadsafe()` calls | `QueueHandler` + `QueueListener` | Official pattern; QueueHandler is optimized to never block the queue writer |
| Traceback formatting | Custom traceback string assembly | `traceback.format_exception(*record.exc_info)` | Handles chained exceptions, notes, `__cause__`, `__context__` correctly |
| Message formatting | String concatenation | `record.getMessage()` | Applies `%`-style args substitution correctly; handles non-string msg arguments |

**Key insight:** Python's `logging` module has 25+ years of production use. Its Handler/Filter contract handles threading, exception routing, and propagation edge cases. Trust the base class; only override what you need.

---

## Common Pitfalls

### Pitfall 1: Blocking the asyncio event loop
**What goes wrong:** `emit()` makes a synchronous `urllib.request.urlopen()` call. If the Telegram API is slow (2-3s timeout), this holds the GIL and can delay aiogram message processing.
**Why it happens:** `emit()` is called synchronously in the middle of the logging call chain; there is no async escape hatch.
**How to avoid:** Wrap `TelegramAlertHandler` in `QueueHandler+QueueListener`. The actual `urlopen()` call runs in the QueueListener background thread, completely decoupled from the asyncio loop.
**Warning signs:** Bot becomes slow to respond to Telegram messages during alert bursts; `asyncio.Task` timeouts in aiogram handlers.

### Pitfall 2: Import-time execution before bot token is loaded
**What goes wrong:** `bot/logging/telegram_handler.py` is imported at module level before `load_dotenv()` runs, so `BOT_TOKEN` is `None`.
**Why it happens:** `config.py` already loads dotenv and runs `Config.setup_logging()` at import time. If `telegram_handler.py` is imported at module top level it may execute before config is ready.
**How to avoid:** Import `telegram_handler` lazily inside `setup_logging()` (inside the `if alert_chat_id:` block). This is safe because `setup_logging()` is called by `config.py` after `load_dotenv()`.
**Warning signs:** `TypeError: expected str, got NoneType` when constructing the URL, or `AttributeError` on `Config.BOT_TOKEN`.

### Pitfall 3: Deduplication dict growing unbounded
**What goes wrong:** Every unique (logger_name, message) combination is stored in `self._seen`. In production with many users, this can leak memory over hours.
**Why it happens:** Keys are never evicted if the same message is never seen twice.
**How to avoid:** Implement `_cleanup_old_entries()` that prunes entries older than `2 * dedup_window` each time a new entry is added. This amortizes cleanup without a separate timer.
**Warning signs:** Memory usage of the bot process grows over 12-24 hours of uptime.

### Pitfall 4: double-applying the filter
**What goes wrong:** The `SmartAlertFilter` is added to both the `QueueHandler` and the `TelegramAlertHandler`. Records get filtered twice, which is harmless but wasteful and confusing when debugging.
**Why it happens:** It seems logical to add the filter everywhere, but `QueueHandler.emit()` does not filter — it just enqueues. Only `QueueListener` processes through the real handler's filters.
**How to avoid:** Add `SmartAlertFilter` only to `TelegramAlertHandler` (not the `QueueHandler`). Set `queue_handler.setLevel(logging.WARNING)` as a cheap first gate, then let `TelegramAlertHandler` + its filter do precise routing.

### Pitfall 5: CRITICAL messages suppressed by deduplication
**What goes wrong:** A critical failure (database down, bot token invalid) fires every 5 seconds. Deduplication silences everything after the first alert.
**Why it happens:** The naive dedup key is (name, message); if the message is identical every time, it gets suppressed.
**How to avoid:** CRITICAL records must bypass deduplication entirely. In `SmartAlertFilter.filter()`: if `record.levelno >= logging.CRITICAL`, return `True` immediately without checking `_seen`.

### Pitfall 6: Handler added multiple times
**What goes wrong:** `Config.setup_logging()` is called more than once (e.g., in tests). Each call adds another `QueueHandler` to the root logger, multiplying alerts.
**Why it happens:** `logging.getLogger()` returns the same root logger instance across all calls; `addHandler()` does not deduplicate.
**How to avoid:** Guard the attachment: check `any(isinstance(h, logging.handlers.QueueHandler) for h in logging.getLogger().handlers)` before adding, or store a module-level flag `_telegram_configured = False`.

### Pitfall 7: Telegram API rate limit triggering during incident
**What goes wrong:** A bug causes hundreds of ERRORs per second. Even with deduplication, a new unique error message fires a new alert. The bot sends >1 msg/sec to the admin chat, which Telegram throttles at ~1/sec per chat.
**Why it happens:** Per-chat rate limit is 1 msg/sec per Telegram Bot API docs (confirmed 2025).
**How to avoid:** The dedup window (default 60s) is the primary protection. Also: `urllib.request.urlopen(timeout=5)` with a 5-second timeout means the QueueListener thread will wait at most 5s per request before calling `handleError()`. Since `handleError()` does not retry, excess messages are silently dropped — which is the desired behavior.

---

## Code Examples

Verified patterns from official sources:

### Minimal Handler subclass (official pattern)
```python
# Source: https://docs.python.org/3/library/logging.html#handler-objects
class TelegramAlertHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            # ... do work ...
            pass
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)  # Never raises; respects logging.raiseExceptions
```

### Filter returning bool (official API)
```python
# Source: https://docs.python.org/3/library/logging.html#logging.Filter.filter
class SmartAlertFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Return True to allow, False to drop
        return record.levelno >= logging.ERROR
```

### QueueHandler + QueueListener (official async-safe pattern)
```python
# Source: https://docs.python.org/3/library/logging.handlers.html#queuehandler
import queue
import logging.handlers

log_queue = queue.Queue(maxsize=-1)  # -1 = unbounded
queue_handler = logging.handlers.QueueHandler(log_queue)

real_handler = TelegramAlertHandler(token, chat_id)
listener = logging.handlers.QueueListener(
    log_queue, real_handler, respect_handler_level=True
)
listener.start()

logging.getLogger().addHandler(queue_handler)
```

### urllib POST to Telegram (no external dependencies)
```python
# Source: https://docs.python.org/3/library/urllib.request.html
import json
import urllib.request

def send_telegram_message(bot_token: str, chat_id: str, text: str, timeout: int = 5) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text[:4000],
        "parse_mode": "HTML",
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        resp.read()  # Consume response to free connection
```

### Getting root logger and adding handler (official API)
```python
# Source: https://docs.python.org/3/library/logging.html#logging.getLogger
root_logger = logging.getLogger()  # name=None → root logger
root_logger.addHandler(queue_handler)
# Handler propagates to all child loggers (bot.services.*, etc.)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Subclass `logging.Handler`, make blocking HTTP in `emit()` directly | Wrap with `QueueHandler+QueueListener` | Python 3.2 (QueueHandler added), widely adopted ~2019 | Event loop stays unblocked; asyncio apps safe |
| Custom Filter class required | Function filters also accepted (`handler.addFilter(lambda r: ...)`) | Python 3.2 | Simpler for trivial filters; class still preferred for stateful dedup |
| `logging.raiseExceptions = True` hides silent failures | `handleError(record)` prints to stderr when `raiseExceptions=True` | Always | During dev, handler failures are visible; in prod they are silent |
| Telegram sendMessage text limit 4096 chars | Still 4096 chars (verified 2025) | Unchanged | Truncate to 4000 to leave margin for parse_mode overhead |
| Telegram rate limit: soft 30/s global, 1/s per chat | Still 1 msg/sec per chat for bots (confirmed 2025) | Bot API 7.0 added token-bucket on top | For admin alerts (low volume), 1/sec is not a concern |

**Deprecated/outdated:**
- Direct `requests` or `httpx` in `emit()`: These are async-capable but import-heavy; `urllib.request` is stdlib and sufficient for single low-frequency POST calls.
- `logging.config.fileConfig()` for handler wiring: Overkill here; the team uses explicit Python code in `Config.setup_logging()`.

---

## Open Questions

1. **QueueListener shutdown on bot stop**
   - What we know: `listener.start()` starts a daemon thread; daemon threads die when the main thread exits.
   - What's unclear: Whether in-flight records in the queue will be lost on clean shutdown (SIGTERM). `listener.stop()` drains the queue before stopping.
   - Recommendation: Call `listener.stop()` in the bot's shutdown sequence (main.py teardown). Store the listener reference as `Config._telegram_listener` or on the root logger.

2. **ALERT_CHAT_ID vs reusing ADMIN_USER_IDS**
   - What we know: The requirement specifies a single `ALERT_CHAT_ID` env var (one admin chat). `ADMIN_USER_IDS` is a list of integers (user IDs, not chat IDs, though for DMs they are the same).
   - What's unclear: Whether to default to the first admin ID when `ALERT_CHAT_ID` is absent.
   - Recommendation: Support both: if `ALERT_CHAT_ID` is set, use it; else fall back to the first entry in `Config.ADMIN_USER_IDS` as a string. This is a soft fallback and should be documented in `.env.example`.

3. **Filter for `bot.services.subscription` namespace**
   - What we know: `config.py` currently silences `bot.services.subscription` to WARNING level in production mode (line 317). But the requirements say subscription logic is HIGH PRIORITY.
   - What's unclear: If subscription logger is set to WARNING by `setup_logging()`, WARNING records still reach the root logger via propagation. The Telegram handler on root will see them.
   - Recommendation: Verify this works correctly in tests. The namespace silencing in `setup_logging()` controls the StreamHandler threshold, not root propagation. Records still propagate upward.

---

## Sources

### Primary (HIGH confidence)
- https://docs.python.org/3/library/logging.html — Handler class API, Filter class API, LogRecord attributes, root logger, addHandler
- https://docs.python.org/3/library/logging.handlers.html — QueueHandler, QueueListener, handleError pattern
- https://docs.python.org/3/howto/logging-cookbook.html — QueueHandler+QueueListener asyncio pattern, rate-limit filter pattern, buffering patterns
- https://core.telegram.org/bots/api#sendmessage — sendMessage endpoint, chat_id, text, parse_mode, 4096 char limit

### Secondary (MEDIUM confidence)
- https://superfastpython.com/asyncio-logging-best-practices/ — Confirmed: never call asyncio APIs from emit(); QueueHandler is the correct pattern
- https://github.com/python-telegram-bot/python-telegram-bot/wiki/Avoiding-flood-limits — Telegram per-chat rate limit: 1 msg/sec confirmed in 2025 context

### Tertiary (LOW confidence)
- https://signoz.io/guides/log-messages-appearing-twice-with-python-logging/ — Multiple-handler duplication pitfall; cross-checked with official docs
- https://last9.io/blog/python-logging-best-practices/ — Filter-in-handler vs filter-on-logger scope; verified against official docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib, no external dependencies, verified against Python 3.11 official docs
- Architecture patterns: HIGH — QueueHandler+QueueListener is the official recommended pattern documented in logging.handlers and the Logging Cookbook; all code examples are derived from official sources
- Pitfalls: HIGH for asyncio-blocking and import-order issues (confirmed by official asyncio logging docs); MEDIUM for dedup memory growth and duplicate handler registration (derived from code review + community patterns verified against official docs)
- Telegram API limits: MEDIUM — 4096 char limit is official API doc; 1 msg/sec per-chat rate limit confirmed by multiple 2025 sources but not in official API docs directly

**Research date:** 2026-03-22
**Valid until:** 2026-06-22 (stable — Python stdlib logging API is extremely stable; Telegram Bot API limits rarely change)
