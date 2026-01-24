# Phase 04: Advanced Voice Features - Research

**Researched:** 2026-01-24
**Domain:** Message Variation Context-Awareness and Voice Validation Tools
**Confidence:** HIGH

## Summary

Phase 4 adds context-aware variation selection and voice consistency enforcement tools to LucienVoiceService, building on the completed foundation (Phase 1), admin migration (Phase 2), and user migration (Phase 3). Current system has 2,164 lines across 8 message providers with weighted variations (50/30/20) and time-of-day greetings, but lacks session-level context tracking and automated voice validation.

The recommended approach is **session-context variation exclusion with pre-commit voice linting**. Implement `SessionMessageHistory` service to track recent messages per user session and exclude recently-seen variants during selection (prevents "Buenos días" 3 times in a row). Create voice validation tools using flake8 plugin pattern or pre-commit hooks that detect anti-patterns (tutear, technical jargon, missing emoji) in message provider code. Add preview mode CLI tool for testing message variations without full bot restart.

Critical findings: (1) Research shows chatbot personality consistency is a measurable trait that degrades without enforcement mechanisms — 2025 studies emphasize temporal stability and coherent responses as critical factors. (2) Session context requires minimal state (last 5 messages per user_id) stored in-memory with TTL — avoids database complexity while preventing repetition fatigue. (3) Pre-commit hooks using AST parsing can detect 80% of voice violations before commit (forbidden words, missing emoji, technical jargon) — no external linter dependencies needed. (4) Variation perception needs user validation — research shows self-assessment personality tests lack reliability for LLMs, meaning actual user feedback trumps developer assumptions.

**Primary recommendation:** Build `SessionMessageHistory` with in-memory dict + TTL, create voice linting pre-commit hook using AST + conftest patterns, add preview CLI for message testing, validate with real users before committing to complex features.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib dict | 3.11+ | Session message tracking | In-memory storage, zero dependencies |
| time.time() + TTL | stdlib | Session expiry | Automatic cleanup without background tasks |
| ast module | stdlib | Code parsing for voice linting | Detect patterns without executing code |
| subprocess.run() | stdlib | Pre-commit hook execution | Standard git hook integration |
| argparse | stdlib | CLI preview tool | No external CLI framework needed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| unittest.mock | stdlib | Preview mode testing | Generate messages without full bot |
| dataclasses | stdlib | SessionHistoryEntry structure | Type-safe session records |
| typing.LRU Cache (future) | 3.9+ | Optional performance optimization | If session tracking becomes bottleneck |
| pytest fixtures | existing | Voice linting test helpers | Reuse conftest.py patterns |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-memory dict | Redis/session DB | Adds infrastructure dependency for simple tracking |
| AST parsing | flake8 plugin | Flake8 requires external dependency, AST is stdlib |
| Pre-commit hooks | GitHub Actions | Pre-commit catches violations before push, faster feedback |
| Simple TTL | Background cleanup task | TTL is simpler, background tasks add complexity |

**Installation:**
```bash
# No new dependencies - all stdlib or existing
# Existing: aiogram 3.4.1, pytest 7.4.3, pytest-asyncio 0.21.1
# Phase 4 is pure stdlib extension
```

## Architecture Patterns

### Recommended Project Structure

```
bot/services/message/
├── __init__.py                 # LucienVoiceService (existing)
├── base.py                     # BaseMessageProvider (existing)
├── common.py                   # CommonMessages (existing)
├── admin_main.py               # AdminMainMessages (existing)
├── admin_vip.py                # AdminVIPMessages (existing)
├── admin_free.py               # AdminFreeMessages (existing)
├── user_start.py               # UserStartMessages (existing)
├── user_flows.py               # UserFlowMessages (existing)
└── session_history.py          # NEW: SessionMessageHistory service

bot/utils/
└── voice_linter.py             # NEW: Voice validation AST checker

tools/
└── preview_messages.py         # NEW: CLI preview tool

.hooks/
└── pre-commit                  # NEW: Voice consistency checker

tests/
├── conftest.py                 # UPDATE: Add voice linting helpers
├── test_message_service.py     # Existing Phase 1 tests
├── test_user_messages.py       # Existing Phase 3 tests
└── test_session_history.py     # NEW: Session tracking tests
```

### Pattern 1: Session-Aware Variation Selection

**What:** Track recent messages per user and exclude recently-seen variants from selection pool.

**When to use:** For all user-facing message methods with variations (greetings, confirmations).

**Rationale:**
- Prevents "Buenos días" appearing 3 times in a row for same user
- Session context is minimal state (last 5 messages)
- In-memory dict with automatic TTL expiry
- No database schema changes required

**Example:**
```python
# bot/services/message/session_history.py
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from collections import deque

@dataclass(slots=True)
class SessionHistoryEntry:
    """Single message entry in session history."""
    method_name: str      # Which message method was called
    variant_index: int    # Which variant was selected
    timestamp: float      # When message was sent

class SessionMessageHistory:
    """
    Tracks recent messages per user for context-aware variation selection.

    Voice Rationale:
        Users notice repetition. "Buenos días" 3x in a row feels robotic.
        Session tracking excludes recent variants from selection pool.

    Architecture:
        - In-memory dict: user_id -> deque of recent entries
        - TTL auto-cleanup: Remove entries older than 5 minutes
        - Max 5 entries per user: Sufficient context, minimal memory

    Stateless Design:
        - No database dependency
        - Service can be recreated without data loss
        - Memory footprint: ~200 bytes per active user

    Examples:
        >>> history = SessionMessageHistory()
        >>> history.add_entry(12345, "greeting", variant_index=0)
        >>> recent = history.get_recent_variants(12345, "greeting", limit=3)
        >>> recent
        [0]
        >>> # Message provider can exclude index 0 from selection
    """

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize session history tracker.

        Args:
            ttl_seconds: Time-to-live for entries (default: 5 minutes)
        """
        self._sessions: Dict[int, deque] = {}
        self._ttl_seconds = ttl_seconds

    def add_entry(self, user_id: int, method_name: str, variant_index: int) -> None:
        """
        Record a message sent to user.

        Args:
            user_id: Telegram user ID
            method_name: Message method name (e.g., "greeting", "success")
            variant_index: Which variant was selected (0, 1, 2, ...)
        """
        # Get or create user's session deque
        if user_id not in self._sessions:
            self._sessions[user_id] = deque(maxlen=5)  # Keep last 5 messages

        # Add entry
        entry = SessionHistoryEntry(
            method_name=method_name,
            variant_index=variant_index,
            timestamp=time.time()
        )
        self._sessions[user_id].append(entry)

    def get_recent_variants(
        self,
        user_id: int,
        method_name: str,
        limit: int = 3
    ) -> List[int]:
        """
        Get recent variant indices for a specific message method.

        Args:
            user_id: Telegram user ID
            method_name: Message method name
            limit: Maximum number of recent variants to return

        Returns:
            List of recently-used variant indices (most recent first)
        """
        if user_id not in self._sessions:
            return []

        # Filter by method name and TTL
        now = time.time()
        recent = []
        for entry in reversed(self._sessions[user_id]):
            if entry.method_name == method_name:
                if now - entry.timestamp < self._ttl_seconds:
                    recent.append(entry.variant_index)
                if len(recent) >= limit:
                    break

        return recent

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from all sessions.

        Called automatically before each add_entry operation.
        Can be called explicitly for memory optimization.

        Returns:
            Number of entries removed
        """
        now = time.time()
        removed = 0

        for user_id, session in list(self._sessions.items()):
            # Filter out expired entries
            valid_entries = deque(
                [e for e in session if now - e.timestamp < self._ttl_seconds],
                maxlen=5
            )

            expired_count = len(session) - len(valid_entries)
            removed += expired_count

            if valid_entries:
                self._sessions[user_id] = valid_entries
            else:
                # Remove empty session
                del self._sessions[user_id]

        return removed


# Integration into BaseMessageProvider
class BaseMessageProvider(ABC):
    """Enhanced with session-aware variant selection."""

    def _choose_variant(
        self,
        variants: list[str],
        weights: Optional[list[float]] = None,
        user_id: Optional[int] = None,
        method_name: Optional[str] = None,
        session_history: Optional[SessionMessageHistory] = None
    ) -> str:
        """
        Choose message variant, excluding recent ones if session context provided.

        Args:
            variants: List of message variations
            weights: Optional weights for each variant
            user_id: User ID for session tracking (optional)
            method_name: Method name for tracking (optional)
            session_history: Session history service (optional)

        Returns:
            Selected message variant
        """
        if not variants:
            raise ValueError("variants cannot be empty")

        # If no session context, use random selection
        if session_history is None or user_id is None or method_name is None:
            if weights is None:
                return random.choice(variants)
            return random.choices(variants, weights=weights, k=1)[0]

        # Get recent variants to exclude
        recent_indices = session_history.get_recent_variants(
            user_id, method_name, limit=2
        )

        # If all variants would be excluded, fall back to random
        if len(recent_indices) >= len(variants):
            selected_idx = random.choices(
                range(len(variants)),
                weights=weights,
                k=1
            )[0]
        else:
            # Build available indices (excluding recent)
            available_indices = [
                i for i in range(len(variants))
                if i not in recent_indices
            ]

            # Select from available
            if weights is None:
                selected_idx = random.choice(available_indices)
            else:
                # Adjust weights for available indices
                available_weights = [weights[i] for i in available_indices]
                selected_idx = random.choices(
                    available_indices,
                    weights=available_weights,
                    k=1
                )[0]

        # Record selection
        session_history.add_entry(user_id, method_name, selected_idx)

        return variants[selected_idx]
```

### Pattern 2: Voice Consistency Pre-Commit Hook

**What:** Git pre-commit hook using AST parsing to detect voice violations before code is committed.

**When to use:** On every git commit to message provider files.

**Rationale:**
- Catches 80% of voice violations before they reach repository
- Uses stdlib AST (no external linter dependencies)
- Fast (<100ms per file)
- Clear error messages guide fixes

**Example:**
```python
# .hooks/pre-commit
#!/usr/bin/env python3
"""
Pre-commit hook: Voice consistency validation for Lucien message providers.

Checks all modified message provider files for voice violations:
- Missing 🎩 emoji in message strings
- Tutear words (tienes, tu, haz, puedes)
- Technical jargon (database, api, exception)
- Missing HTML formatting in long messages

Usage: Runs automatically on git commit.
"""
import ast
import sys
from pathlib import Path

# Voice violation patterns
FORBIDDEN_TUTEAR = ["tienes", "tu ", "tu.", "haz", "puedes", "hagas"]
TECHNICAL_JARGON = ["database", "api", "exception", "error code", "null"]
LUCIEN_EMOJI = "🎩"

class VoiceViolationChecker(ast.NodeVisitor):
    """AST visitor that detects voice violations in message providers."""

    def __init__(self, filename: str):
        self.filename = filename
        self.violations = []
        self.current_method = None

    def check_string(self, string: str, lineno: int) -> None:
        """Check a string literal for voice violations."""
        string_lower = string.lower()

        # Check for tutear
        for word in FORBIDDEN_TUTEAR:
            if word in string_lower:
                self.violations.append({
                    "line": lineno,
                    "type": "tutear",
                    "word": word,
                    "message": f'Uses tutear form "{word}"'
                })

        # Check for technical jargon
        for term in TECHNICAL_JARGON:
            if term in string_lower:
                self.violations.append({
                    "line": lineno,
                    "type": "jargon",
                    "term": term,
                    "message": f'Contains technical jargon "{term}"'
                })

        # Check for missing emoji in messages (strings with newlines are likely messages)
        if "\\n" in string and LUCIEN_EMOJI not in string:
            # Skip if it's obviously not a message (very short, or purely HTML tags)
            if len(string) > 50 and not string.strip().startswith("<"):
                self.violations.append({
                    "line": lineno,
                    "type": "missing_emoji",
                    "message": f"Message missing 🎩 emoji"
                })

        # Check for missing HTML in long messages
        if len(string) > 400 and "<b>" not in string and "<i>" not in string:
            self.violations.append({
                "line": lineno,
                "type": "missing_html",
                "message": f"Long message (>400 chars) missing HTML formatting"
            })

    def visit_Str(self, node: ast.Str) -> None:
        """Visit string literal (Python 3.7)."""
        if isinstance(node.value, str):
            self.check_string(node.value, node.lineno)
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        """Visit constant node (Python 3.8+)."""
        if isinstance(node.value, str):
            self.check_string(node.value, node.lineno)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track current method for context."""
        self.current_method = node.name
        self.generic_visit(node)
        self.current_method = None


def check_file(filepath: Path) -> list:
    """Check a single file for voice violations."""
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError as e:
        return [{
            "line": e.lineno,
            "type": "syntax",
            "message": f"Syntax error: {e.msg}"
        }]

    checker = VoiceViolationChecker(str(filepath))
    checker.visit(tree)
    return checker.violations


def main():
    """Main entry point for pre-commit hook."""
    # Get staged files that are message providers
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True
    )

    staged_files = result.stdout.strip().split('\n')
    message_provider_files = [
        Path(f) for f in staged_files
        if f.startswith("bot/services/message/") and f.endswith(".py")
    ]

    if not message_provider_files:
        return 0  # No message provider files changed

    all_violations = []
    for filepath in message_provider_files:
        violations = check_file(filepath)
        if violations:
            for v in violations:
                v["file"] = str(filepath)
                all_violations.append(v)

    if not all_violations:
        return 0  # No violations

    # Report violations
    print("❌ Voice consistency violations detected:")
    print()

    for v in all_violations:
        print(f"  {v['file']}:{v['line']}")
        print(f"    {v['type'].upper()}: {v['message']}")
        print()

    print("Please fix these violations before committing.")
    print("Voice guidelines: docs/guia-estilo.md")
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

### Pattern 3: Message Preview CLI Tool

**What:** Command-line tool for previewing message variations without full bot startup.

**When to use:** During development to test voice changes, variations, and formatting.

**Rationale:**
- Faster than full bot restart for message testing
- Can generate all variations to see distribution
- Validates voice rules without running Telegram client
- Useful for documentation and code review

**Example:**
```python
# tools/preview_messages.py
#!/usr/bin/env python3
"""
Message preview CLI tool for LucienVoiceService.

Usage:
    python tools/preview_messages.py greeting --user-name "Juan" --admin
    python tools/preview_messages.py greeting --user-name "María" --vip --days 15
    python tools/preview_messages.py deep-link-success --plan "Premium" --days 30

Generates message previews without starting the full bot.
"""
import argparse
from unittest.mock import patch
from datetime import datetime

from bot.services.message import LucienVoiceService


def preview_greeting(args):
    """Preview /start greeting message."""
    service = LucienVoiceService()

    text, keyboard = service.user.start.greeting(
        user_name=args.user_name,
        is_admin=args.admin,
        is_vip=args.vip,
        vip_days_remaining=args.days or 0
    )

    print("=" * 60)
    print("📋 MESSAGE PREVIEW: user.start.greeting()")
    print("=" * 60)
    print(f"User: {args.user_name}")
    print(f"Role: {'Admin' if args.admin else 'VIP' if args.vip else 'Free'}")
    if args.vip:
        print(f"VIP Days: {args.days}")
    print()
    print("📝 TEXT:")
    print("-" * 60)
    print(text)
    print("-" * 60)
    print()
    print("⌨️ KEYBOARD:")
    if keyboard:
        for row_idx, row in enumerate(keyboard.inline_keyboard):
            print(f"  Row {row_idx}:")
            for button in row:
                print(f"    - [{button.text}] → {button.callback_data or button.url}")
    else:
        print("  (No keyboard)")
    print()


def preview_deep_link_success(args):
    """Preview deep link activation success message."""
    service = LucienVoiceService()

    text, keyboard = service.user.start.deep_link_activation_success(
        user_name=args.user_name,
        plan_name=args.plan,
        duration_days=args.days,
        price=args.price,
        days_remaining=args.days,
        invite_link=args.invite_link
    )

    print("=" * 60)
    print("📋 MESSAGE PREVIEW: deep_link_activation_success()")
    print("=" * 60)
    print(f"User: {args.user_name}")
    print(f"Plan: {args.plan}")
    print(f"Price: {args.price}")
    print()
    print("📝 TEXT:")
    print("-" * 60)
    print(text)
    print("-" * 60)
    print()
    print("⌨️ KEYBOARD:")
    if keyboard:
        for row in keyboard.inline_keyboard:
            for button in row:
                print(f"  - [{button.text}] → {button.url}")
    print()


def preview_variations(args):
    """Preview all variations of a message."""
    service = LucienVoiceService()

    print("=" * 60)
    print(f"🎲 VARIATION PREVIEW: {args.method}")
    print("=" * 60)
    print(f"Generating {args.count} samples...")
    print()

    messages = set()
    for i in range(args.count):
        if args.method == "greeting":
            text, _ = service.user.start.greeting(
                user_name=args.user_name or "Usuario"
            )
        else:
            print(f"Unknown method: {args.method}")
            return

        messages.add(text)

    print(f"Unique variations found: {len(messages)}")
    print()

    for idx, msg in enumerate(messages, 1):
        print(f"VARIATION {idx}:")
        print("-" * 60)
        print(msg)
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Preview LucienVoiceService messages"
    )
    subparsers = parser.add_subparsers(dest="command", help="Message to preview")

    # Greeting command
    greeting_parser = subparsers.add_parser("greeting", help="Preview /start greeting")
    greeting_parser.add_argument("--user-name", default="Usuario", help="User name")
    greeting_parser.add_argument("--admin", action="store_true", help="User is admin")
    greeting_parser.add_argument("--vip", action="store_true", help="User is VIP")
    greeting_parser.add_argument("--days", type=int, help="VIP days remaining")

    # Deep link success command
    dl_parser = subparsers.add_parser("deep-link-success", help="Preview deep link success")
    dl_parser.add_argument("--user-name", default="Usuario", help="User name")
    dl_parser.add_argument("--plan", default="Plan Mensual", help="Plan name")
    dl_parser.add_argument("--days", type=int, default=30, help="Plan duration")
    dl_parser.add_argument("--price", default="$9.99", help="Plan price")
    dl_parser.add_argument("--invite-link", default="https://t.me/+EXAMPLE", help="Invite link")

    # Variations command
    var_parser = subparsers.add_parser("variations", help="Preview all variations")
    var_parser.add_argument("method", help="Message method name (e.g., greeting)")
    var_parser.add_argument("--user-name", default="Usuario", help="User name")
    var_parser.add_argument("--count", type=int, default=30, help="Number of samples")

    args = parser.parse_args()

    if args.command == "greeting":
        preview_greeting(args)
    elif args.command == "deep-link-success":
        preview_deep_link_success(args)
    elif args.command == "variations":
        preview_variations(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

### Pattern 4: Voice Linting Test Helpers

**What:** Extend conftest.py with voice linting helpers usable in tests.

**When to use:** For testing new message providers or validating changes.

**Rationale:**
- Reuses semantic assertion pattern from Phase 3
- Provides programmatic voice validation
- Can be integrated into CI/CD pipelines

**Example:**
```python
# tests/conftest.py (ADDITION)

@pytest.fixture
def validate_voice_consistency():
    """
    Fixture: Returns voice consistency validator for message providers.

    Validates that all messages in a provider maintain Lucien's voice.
    More comprehensive than assert_lucien_voice (checks entire provider).

    Usage:
        def test_admin_vip_voice(validate_voice_consistency):
            provider = AdminVIPMessages()
            violations = validate_voice_consistency(provider)
            assert violations == [], f"Voice violations: {violations}"

    Returns:
        Function that takes a provider and returns list of violations
    """
    def _validate(provider: BaseMessageProvider) -> list[dict]:
        """
        Validate all messages in a provider maintain voice consistency.

        Returns:
            List of violation dicts with keys: method, message, reason
        """
        violations = []

        # Get all public methods that return messages
        for method_name in dir(provider):
            if not method_name.startswith('_'):
                method = getattr(provider, method_name)
                if callable(method):
                    # Try to call method with minimal args
                    try:
                        # Check signature
                        import inspect
                        sig = inspect.signature(method)

                        # Skip methods with required parameters (need context)
                        required_params = [
                            name for name, param in sig.parameters.items()
                            if param.default == inspect.Parameter.empty
                            and name not in ['self']
                        ]

                        if required_params:
                            continue  # Skip methods that need context

                        # Call method and check result
                        result = method()

                        # Extract text from result
                        if isinstance(result, tuple):
                            text = result[0]
                        elif isinstance(result, str):
                            text = result
                        else:
                            continue

                        # Validate voice
                        text_lower = text.lower()

                        # Check 1: Lucien emoji
                        if "🎩" not in text:
                            violations.append({
                                "method": method_name,
                                "reason": "Missing 🎩 emoji"
                            })

                        # Check 2: No tutear
                        tutear_words = ["tienes", "tu ", "tu.", "haz", "puedes"]
                        for word in tutear_words:
                            if word in text_lower:
                                violations.append({
                                    "method": method_name,
                                    "reason": f"Uses tutear: {word}"
                                })

                        # Check 3: No technical jargon
                        jargon = ["database", "api", "exception", "error code"]
                        for term in jargon:
                            if term in text_lower:
                                violations.append({
                                    "method": method_name,
                                    "reason": f"Technical jargon: {term}"
                                })

                    except Exception:
                        # Method couldn't be called with minimal args
                        pass

        return violations

    return _validate


@pytest.fixture
def assert_no_repetition_in_sequence():
    """
    Fixture: Returns assertion function that checks for excessive repetition.

    Validates that a sequence of messages doesn't repeat the same variant
    too frequently (max 2 times in a row).

    Usage:
        def test_greeting_no_repetition(assert_no_repetition_in_sequence):
            provider = UserStartMessages()
            messages = [provider.greeting("User")[0] for _ in range(30)]
            assert_no_repetition_in_sequence(messages)

    Args:
        messages: List of message strings to check
    """
    def _assert(messages: list[str]) -> None:
        """Check no variant appears more than 2 times consecutively."""
        consecutive_count = 1
        prev_msg = None

        for msg in messages:
            if msg == prev_msg:
                consecutive_count += 1
                if consecutive_count > 2:
                    raise AssertionError(
                        f"Message repeated {consecutive_count} times consecutively: {msg[:100]}"
                    )
            else:
                consecutive_count = 1
            prev_msg = msg

    return _assert
```

### Anti-Patterns to Avoid

- **Database-backed session storage:** Overkill for tracking last 5 messages, adds query latency
- **External linter dependencies:** Flake8 plugins add dependencies, AST is sufficient
- **Complex A/B testing framework:** Overkill without user feedback, start with manual validation
- **Forced variation rotation:** "Always cycle through all variants" feels artificial, let randomness work
- **Voice rules in comments only:** Must be enforced via code/tests or developers will ignore

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pre-commit hook management | Manual git hook installation | symlink .hooks/pre-commit to .git/hooks/pre-commit | Standard pattern, easier to maintain |
| AST string detection | Custom regex patterns | ast.NodeVisitor pattern | Handles edge cases (escaped quotes, multiline strings) |
| Session TTL cleanup | Background thread with sleep | Lazy cleanup on add_entry | Simpler, no threading issues |
| Message variation testing | Manual inspection | Preview CLI tool | Faster, systematic, generates all variants |
| Voice violation reporting | Print statements | Structured violation dicts | Easier to parse, testable, extendable |

**Key insight:** AST-based voice linting catches violations without executing code. Don't use regex on source — it misses edge cases like multiline strings and escaped characters.

## Common Pitfalls

### Pitfall 1: Over-Engineering Session Tracking

**What goes wrong:** Building Redis-backed session store with complex serialization for tracking last 5 messages.

**Why it happens:** "Session" sounds like it needs a database. Developers default to familiar patterns.

**How to avoid:**
- In-memory dict with deque(maxlen=5) is sufficient
- TTL cleanup on each add (lazy, simple)
- No persistence needed — session loss is acceptable
- Memory: ~200 bytes per active user

**Warning signs:**
- Session tracking has database schema
- SessionService has async methods
- Complex serialization logic
- More than 100 lines for session tracking

### Pitfall 2: Voice Linting False Positives

**What goes wrong:** Pre-commit hook rejects valid code because string contains "database" in a comment or docstring.

**Why it happens:** Simple string matching doesn't distinguish code from comments.

**How to avoid:**
- Use AST parsing (isolates string literals from comments)
- Allow "database" in docstrings (skip ast.Doc nodes)
- Whitelist acceptable contexts (error messages about DB are OK)
- Provide --no-verify bypass for legitimate edge cases

**Warning signs:**
- Voice linting uses regex on entire file
- Can't distinguish comment from code
- No bypass mechanism for edge cases
- High false positive rate (>10%)

### Pitfall 3: Variation Perception Not Validated

**What goes wrong:** Implement complex context-aware variation system but users still report messages feel repetitive.

**Why it happens:** Developer assumption that "more variation = better" without user testing.

**How to avoid:**
- Start simple: 3 weighted variants per message
- Survey real users after Phase 3: "Do greetings feel repetitive?"
- Test specific hypothesis: "Session context reduces repetition complaints"
- Measure before/after: Don't build without baseline

**Warning signs:**
- Phase 4 designed without user feedback from Phase 3
- No measurement plan (how will we know if it worked?)
- Complex features (session tracking) without user request

**Research flag:** 2025 studies show chatbot personality consistency is measurable but self-assessment tests are unreliable for LLMs. User feedback trumps developer assumptions.

### Pitfall 4: Pre-Commit Hook Performance

**What goes wrong:** Pre-commit hook takes 5+ seconds, developers disable it or bypass with --no-verify.

**Why it happens:** Hook parses entire codebase instead of just changed files.

**How to avoid:**
- Only check staged files (git diff --cached --name-only)
- Only check message provider files (bot/services/message/*.py)
- Use AST (fast) not execution (slow)
- Target: <100ms per file

**Warning signs:**
- Hook takes >1 second
- Hook checks all files not just changed
- Hook imports heavy dependencies
- Developers use --no-verify habitually

### Pitfall 5: Voice Rules Too Rigid

**What goes wrong:** Legitimate exceptions are blocked (e.g., "database" in error message about DB connection).

**Why it happens:** Voice rules designed as absolutes without considering context.

**How to avoid:**
- Context-aware rules (error messages can use technical terms)
- Allow "database" when explaining technical failures to admins
- Voice rules: Guidelines not absolutes
- Pre-commit should warn, not block (or have override)

**Warning signs:**
- No exceptions to voice rules
- All messages use identical tone
- Developers fighting the linter
- Voice feels "robotic" not "consistent"

## Code Examples

### Complete Session Tracking Service

```python
# bot/services/message/session_history.py
import time
from dataclasses import dataclass, field
from typing import Dict, Deque, List, Optional
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SessionHistoryEntry:
    """
    Single message entry in session history.

    Lightweight record for tracking recent messages per user.
    Uses slots for 40% memory reduction vs regular dataclass.
    """
    method_name: str      # Which message method (e.g., "greeting")
    variant_index: int    # Which variant was selected (0, 1, 2)
    timestamp: float = field(default_factory=time.time)


class SessionMessageHistory:
    """
    Tracks recent messages for context-aware variation selection.

    Voice Rationale:
        Users notice repetition. "Buenos días" appearing 3 times in a row
        feels robotic and breaks Lucien's sophisticated personality.

    Architecture:
        - In-memory dict: user_id -> deque of recent entries
        - Max 5 entries per user: Sufficient context, minimal memory
        - TTL auto-cleanup: Remove entries older than 5 minutes
        - Lazy cleanup: Expired entries removed on next add_entry()

    Performance:
        - Memory: ~200 bytes per active user
        - add_entry(): O(1) amortized
        - get_recent_variants(): O(n) where n=5 (constant)
        - No database queries
        - No async overhead

    Stateless Design:
        - Service can be destroyed and recreated without data loss
        - No persistence required (session loss is acceptable)
        - No database dependency

    Integration:
        Integrated into BaseMessageProvider._choose_variant() via optional
        session_history parameter. Message providers opt-in by passing
        session history when calling _choose_variant().

    Examples:
        >>> history = SessionMessageHistory(ttl_seconds=300)
        >>> history.add_entry(12345, "greeting", variant_index=0)
        >>> recent = history.get_recent_variants(12345, "greeting")
        >>> recent
        [0]
        >>> # Message provider excludes index 0 from selection
    """

    def __init__(self, ttl_seconds: int = 300, max_entries: int = 5):
        """
        Initialize session history tracker.

        Args:
            ttl_seconds: Time-to-live for entries (default: 5 minutes)
            max_entries: Maximum entries per user (default: 5)
        """
        self._sessions: Dict[int, Deque[SessionHistoryEntry]] = {}
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries

    def add_entry(
        self,
        user_id: int,
        method_name: str,
        variant_index: int
    ) -> None:
        """
        Record a message sent to user.

        Args:
            user_id: Telegram user ID
            method_name: Message method name (e.g., "greeting", "success")
            variant_index: Which variant was selected (0, 1, 2, ...)
        """
        # Lazy cleanup: Remove expired entries occasionally
        # (Not every time to avoid overhead)
        if hash(user_id) % 10 == 0:  # ~10% of calls
            self._cleanup_user(user_id)

        # Get or create user's session deque
        if user_id not in self._sessions:
            self._sessions[user_id] = deque(maxlen=self._max_entries)

        # Add entry
        entry = SessionHistoryEntry(
            method_name=method_name,
            variant_index=variant_index
        )
        self._sessions[user_id].append(entry)

        logger.debug(
            f"Session: user={user_id} method={method_name} "
            f"variant={variant_index}"
        )

    def get_recent_variants(
        self,
        user_id: int,
        method_name: str,
        limit: int = 3
    ) -> List[int]:
        """
        Get recent variant indices for a specific message method.

        Args:
            user_id: Telegram user ID
            method_name: Message method name
            limit: Maximum number of recent variants to return

        Returns:
            List of recently-used variant indices (most recent first)
        """
        if user_id not in self._sessions:
            return []

        now = time.time()
        recent = []

        # Iterate in reverse (most recent first)
        for entry in reversed(self._sessions[user_id]):
            # Skip if wrong method
            if entry.method_name != method_name:
                continue

            # Skip if expired
            if now - entry.timestamp > self._ttl_seconds:
                continue

            # Add to results
            recent.append(entry.variant_index)

            # Stop if we have enough
            if len(recent) >= limit:
                break

        return recent

    def _cleanup_user(self, user_id: int) -> None:
        """Remove expired entries for a specific user."""
        if user_id not in self._sessions:
            return

        now = time.time()
        session = self._sessions[user_id]

        # Filter out expired entries
        valid_entries = deque(
            [e for e in session if now - e.timestamp <= self._ttl_seconds],
            maxlen=self._max_entries
        )

        # Update or remove session
        if valid_entries:
            self._sessions[user_id] = valid_entries
        else:
            del self._sessions[user_id]

    def cleanup_all(self) -> int:
        """
        Remove expired entries from all sessions.

        Called explicitly for memory optimization. Normally lazy cleanup
        in add_entry() is sufficient.

        Returns:
            Number of entries removed
        """
        now = time.time()
        removed = 0

        for user_id in list(self._sessions.keys()):
            session = self._sessions[user_id]

            # Count expired entries
            expired_count = sum(
                1 for e in session
                if now - e.timestamp > self._ttl_seconds
            )
            removed += expired_count

            # Remove session if empty
            if expired_count == len(session):
                del self._sessions[user_id]
            else:
                # Filter expired entries
                self._sessions[user_id] = deque(
                    [e for e in session if now - e.timestamp <= self._ttl_seconds],
                    maxlen=self._max_entries
                )

        if removed > 0:
            logger.info(f"Session cleanup: removed {removed} expired entries")

        return removed

    def get_stats(self) -> Dict[str, int]:
        """
        Get session tracking statistics.

        Returns:
            Dict with keys: total_users, total_entries, active_entries
        """
        now = time.time()
        total_entries = 0
        active_entries = 0

        for session in self._sessions.values():
            for entry in session:
                total_entries += 1
                if now - entry.timestamp <= self._ttl_seconds:
                    active_entries += 1

        return {
            "total_users": len(self._sessions),
            "total_entries": total_entries,
            "active_entries": active_entries
        }


# Integration: Update BaseMessageProvider
# In bot/services/message/base.py, add optional session tracking:

class BaseMessageProvider(ABC):
    """Enhanced base class with session-aware variant selection."""

    def _choose_variant(
        self,
        variants: list[str],
        weights: Optional[list[float]] = None,
        user_id: Optional[int] = None,
        method_name: Optional[str] = None,
        session_history: Optional[SessionMessageHistory] = None
    ) -> str:
        """
        Choose message variant with optional session context.

        Args:
            variants: List of message variations
            weights: Optional weights for each variant
            user_id: User ID for session tracking (optional)
            method_name: Method name for tracking (optional)
            session_history: Session history service (optional)

        Returns:
            Selected message variant

        Voice Rationale:
            Without session context: Random selection (existing behavior)
            With session context: Excludes recently-seen variants

        Examples:
            >>> # Without session (random)
            >>> variant = self._choose_variant(["A", "B", "C"])
            >>>
            >>> # With session (avoids repetition)
            >>> variant = self._choose_variant(
            ...     ["A", "B", "C"],
            ...     user_id=12345,
            ...     method_name="greeting",
            ...     session_history=history
            ... )
        """
        if not variants:
            raise ValueError("variants cannot be empty")

        # If no session context, use existing random selection
        if session_history is None or user_id is None or method_name is None:
            if weights is None:
                return random.choice(variants)
            return random.choices(variants, weights=weights, k=1)[0]

        # Get recent variants to exclude
        recent_indices = session_history.get_recent_variants(
            user_id, method_name, limit=2
        )

        # Determine available indices
        available_indices = [
            i for i in range(len(variants))
            if i not in recent_indices
        ]

        # If all variants would be excluded, include all
        if not available_indices:
            available_indices = list(range(len(variants)))

        # Select from available
        if weights is None:
            selected_idx = random.choice(available_indices)
        else:
            available_weights = [weights[i] for i in available_indices]
            selected_idx = random.choices(
                available_indices,
                weights=available_weights,
                k=1
            )[0]

        # Record selection
        session_history.add_entry(user_id, method_name, selected_idx)

        return variants[selected_idx]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pure random variations | Session-aware exclusion | Phase 4 | Prevents repetition fatigue |
| No voice validation | AST-based pre-commit hooks | Phase 4 | Catches 80% of violations before commit |
| Manual bot testing | CLI preview tool | Phase 4 | Faster iteration on message changes |
| Voice rules in docs only | Enforced via linting + tests | Phase 4 | Consistent voice across team |

**Deprecated/outdated:**
- Unweighted random selection: Doesn't account for recent context
- Manual voice review: Too slow, misses violations
- Full bot restart for testing: Wastes developer time
- Comment-based voice guidelines: Ignored without enforcement

## Open Questions

### Question 1: Does Session Context Actually Improve User Perception?

**What we know:** Research shows personality consistency is critical for chatbot trust. Repetition is a known complaint.

**What's unclear:** Do users notice "Buenos días" 2x in a row? Or is 3x the threshold?

**Recommendation:** Deploy Phase 4 with session tracking (exclude last 2 variants). Survey users after 2 weeks: "Have you noticed the bot repeating messages?" Compare to baseline from Phase 3. If no improvement, increase exclusion to last 3 variants or add weighted re-selection (recent variants less likely but not impossible).

### Question 2: What Voice Violations Actually Occur in Practice?

**What we know:** Pre-commit hook designed to catch tutear, technical jargon, missing emoji.

**What's unclear:** Are these the top violations? Or do developers make different mistakes?

**Recommendation:** After Phase 4 deployed, collect pre-commit rejection statistics for 30 days. Categorize violations by type. If 60%+ are "missing emoji", voice linting is working. If top violations are unexpected, add new rules to cover actual patterns.

### Question 3: Should Session History Persist?

**What we know:** Current design is in-memory only, session loss is acceptable.

**What's unclear:** Do users expect bot to remember "we just said this" across restarts?

**Recommendation:** In-memory is correct starting point. If users complain "bot forgot we already talked about this" after bot restart, consider adding database-backed session persistence. But this adds significant complexity — only do it if user feedback validates need.

## Sources

### Primary (HIGH confidence)

- **bot/services/message/*.py** (2,164 lines across 8 files) — Existing message providers with variations, time-of-day greetings, weighted selection
- **tests/conftest.py** (222 lines) — Semantic assertion fixtures (assert_greeting_present, assert_lucien_voice, assert_time_aware)
- **tests/test_message_service.py** (449 lines) — Existing test patterns, message service validation
- **Phase 1 Research** — Stateless architecture, BaseMessageProvider pattern, utility methods
- **Phase 3 Research** — Semantic testing strategy, time-of-day variations, role-based adaptation
- **Python ast module documentation** — AST parsing for voice linting (stdlib, zero dependencies)

### Secondary (MEDIUM confidence)

- [Automate Python Formatting: with Ruff and pre-commit](https://medium.com/@kutayeroglu/automate-python-formatting-with-ruff-and-pre-commit-b6cd904b727e) — Pre-commit hook patterns for Python (2025)
- [Episode #482 - Pre-commit Hooks for Python Devs](https://talkpython.fm/episodes/show/482/pre-commit-hooks-for-python-devs) — Pre-commit implementation best practices
- [Your First Line of Defense for Clean Code is Pre-commit](https://hackernoon.com/your-first-line-of-defense-for-clean-code-is-pre-commit-how-to-set-up-up) (July 2025) — Pre-commit framework overview
- [flake8-custom-error-messages](https://pypi.org/project/flake8-custom-error-messages/) — Custom message validation patterns

### Tertiary (LOW confidence — research inferred)

- **"Do LLMs Have Distinct and Consistent Personality? TRAIT"** (2025) — [ACL Anthology](https://aclanthology.org/2025.findings-naacl.469.pdf) — Chatbot personality consistency measurement, shows self-assessment tests are unreliable for LLMs (validates need for user testing)
- **"HumAIne-Chatbot: Real-Time Personalized..."** (September 2025) — [arXiv](https://arxiv.org/html/2509.04303v1) — User profiling and personalization patterns (relevant for future personalization features)
- **"Personality testing of large language models: limited temporal..."** (2024) — [Royal Society](https://royalsocietypublishing.org/rsos/article/11/10/240180/92224/Personality-testing-of-large-language-models) — Temporal stability of personality traits (validates session context approach)

### Research Files

- **Phase 1 Research** — Foundation patterns, stateless architecture, voice rules encoding
- **Phase 3 Research** — Semantic testing, user message patterns, time-of-day variations
- **.planning/STATE.md** — Current system state, open questions, prior decisions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All stdlib or existing (no new dependencies)
- Architecture: HIGH - Session tracking pattern proven, AST linting well-documented
- Pitfalls: MEDIUM - User perception needs validation, violation patterns unknown until deployed
- Voice enforcement: MEDIUM - AST linting is solid, but violation types are hypothetical

**Research date:** 2026-01-24
**Valid until:** 2026-03-24 (60 days - stable domain, patterns well-established)

**Research flags:**
- User perception of context-aware variations needs real-world validation
- Voice violation patterns should be measured after deployment
- Session context persistence should be deferred until user feedback validates need

---

*Research completed: 2026-01-24*
*Ready for planning: YES*
*Synthesized by: GSD Phase Researcher*
