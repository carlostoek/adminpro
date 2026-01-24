# Phase 3: User Flow Migration & Testing Strategy - Research

**Researched:** 2026-01-23
**Domain:** User Handler Migration with Semantic Testing Patterns
**Confidence:** HIGH

## Summary

Phase 3 migrates user-facing handlers (start.py, vip_flow.py, free_flow.py) to use LucienVoiceService while establishing semantic test helpers that prevent brittleness from hardcoded string matching. Current user handlers contain 327 lines of hardcoded messages across 3 files with deep link activation, VIP token redemption, and Free channel request flows.

The recommended approach is **user message provider with context-aware variations and semantic test assertions**. Create UserStartMessages and UserFlowMessages providers using time-of-day greetings (morning/afternoon/evening), role-based adaptations (admin/VIP/free), and deep link handling. Testing uses semantic helpers (`assert_greeting_present`, `assert_token_error_type`) instead of string matching to survive message variation changes without breaking tests.

Critical findings: (1) User messages benefit MORE from variations than admin — users see greeting repeatedly, admins don't. Use 3 weighted variations (50/30/20) for greetings, 2 for confirmations. (2) Deep link activation requires special messaging — "auto-activation success" differs from "manual token redemption success" in tone and CTAs. (3) Test brittleness is the PRIMARY risk — string matching breaks when adding variations, semantic assertions survive. (4) Time-of-day variations create natural personality without complexity — "Buenos días" (6-12), "Buenas tardes" (12-20), "Buenas noches" (20-6).

**Primary recommendation:** Build UserMessages provider with time/role/context-aware methods, implement semantic test helpers in conftest.py, migrate handlers file-by-file with test validation at each step.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python dataclass | 3.11+ | Message context structures | Memory-efficient, type-safe |
| datetime.now() | stdlib | Time-of-day detection | No external dependencies, <1ms overhead |
| pytest fixtures | 7.4+ | Semantic test helpers | Reusable assertions across tests |
| aiogram.types.User | 3.4.1 | Role detection (admin/VIP/free) | Required for user flow handlers |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| bot.utils.formatters | existing | format_relative_time, format_currency | All dynamic user messages |
| BaseMessageProvider._choose_variant | existing | Weighted variation selection | Greetings, confirmations |
| pytest parametrize | 7.4+ | Test multiple message variations | Validate all greeting variants |
| unittest.mock.AsyncMock | stdlib | Mock Telegram bot API | Test handlers without real bot |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Time-of-day variations | Static greetings | Time variations create natural personality at zero cost |
| Semantic assertions | String matching | String matching breaks when variations change |
| 3 weighted greetings | 5+ variations | More variations = diminishing returns, harder to maintain |
| Separate deep link messages | Reuse redemption messages | Deep link flow needs distinct success messaging |

**Installation:**
```bash
# No new dependencies - all stdlib, pytest, or existing
# Existing: aiogram 3.4.1, pytest 7.4.3, pytest-asyncio 0.21.1
```

## Architecture Patterns

### Recommended Project Structure

```
bot/services/message/
├── __init__.py                 # LucienVoiceService (existing)
├── base.py                     # BaseMessageProvider (existing)
├── common.py                   # CommonMessages (existing)
├── admin_main.py               # AdminMainMessages (Phase 2)
├── admin_vip.py                # AdminVIPMessages (Phase 2)
├── admin_free.py               # AdminFreeMessages (Phase 2)
├── user_start.py               # NEW: UserStartMessages provider
└── user_flows.py               # NEW: UserFlowMessages provider

tests/
├── conftest.py                 # NEW: Semantic test helpers
├── test_message_service.py     # Existing Phase 1 tests
└── test_user_messages.py       # NEW: User message tests
```

### Pattern 1: Time-of-Day Contextual Greetings

**What:** Greetings adapt based on current hour — morning (6-12), afternoon (12-20), evening (20-6).

**When to use:** For /start command and user-facing welcome messages.

**Example:**
```python
# bot/services/message/user_start.py
from datetime import datetime
from typing import Tuple
from aiogram.types import InlineKeyboardMarkup
from bot.services.message.base import BaseMessageProvider
from bot.utils.keyboards import create_inline_keyboard

class UserStartMessages(BaseMessageProvider):
    """
    User /start command messages provider.

    Voice Characteristics:
    - Warmer than admin messages (users need welcoming)
    - Time-of-day awareness (natural personality)
    - Role-based adaptation (admin/VIP/free see different content)
    - Deep link handling (auto-activation flow)

    Variations:
    - Greetings: 3 weighted (50%, 30%, 20%)
    - Confirmations: 2 equal (50%, 50%)
    - Errors: Static (consistency more important)
    """

    def greeting(
        self,
        user_name: str,
        is_admin: bool = False,
        is_vip: bool = False,
        vip_days_remaining: int = 0
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Context-aware greeting for /start command.

        Args:
            user_name: User's first name
            is_admin: Whether user is an admin
            is_vip: Whether user has active VIP subscription
            vip_days_remaining: Days remaining on VIP (if is_vip=True)

        Returns:
            Tuple of (text, keyboard) for complete UI

        Voice Rationale:
            Time-of-day creates natural personality.
            Admin redirected to /admin (concise).
            VIP sees encouragement and days remaining.
            Free users see warm welcome with clear options.

        Examples:
            Morning admin:
                >>> msg = UserStartMessages()
                >>> # Mocked datetime: 9:00 AM
                >>> text, kb = msg.greeting("Juan", is_admin=True)
                >>> "Buenos días" in text or "Buen día" in text
                True

            Evening VIP:
                >>> # Mocked datetime: 8:00 PM
                >>> text, kb = msg.greeting("María", is_vip=True, vip_days_remaining=15)
                >>> "Buenas noches" in text and "15" in text
                True
        """
        # Time-of-day detection
        hour = datetime.now().hour

        if 6 <= hour < 12:
            time_greetings = [
                "Buenos días",
                "Buen día",
                "Bienvenido esta mañana"
            ]
            weights = [0.5, 0.3, 0.2]
        elif 12 <= hour < 20:
            time_greetings = [
                "Buenas tardes",
                "Bienvenido",
                "Buena tarde"
            ]
            weights = [0.5, 0.3, 0.2]
        else:  # 20-6
            time_greetings = [
                "Buenas noches",
                "Buena noche",
                "Bienvenido esta noche"
            ]
            weights = [0.5, 0.3, 0.2]

        time_greeting = self._choose_variant(time_greetings, weights)

        # Role-based content
        if is_admin:
            text = self._compose(
                f"🎩 <b>Lucien:</b>",
                f"<i>{time_greeting}, <b>{user_name}</b>.</i>\n\n"
                f"<i>Como custodio de los dominios de Diana, "
                f"le sugiero usar /admin para sus responsabilidades.</i>"
            )
            keyboard = None  # No keyboard for admin redirect

        elif is_vip:
            text = self._compose(
                f"🎩 <b>Lucien:</b>",
                f"<i>{time_greeting}, <b>{user_name}</b>.</i>\n\n"
                f"<i>Su acceso al círculo exclusivo está activo.</i>\n\n"
                f"⏱️ <b>Días restantes:</b> {vip_days_remaining}\n\n"
                f"<i>Disfrute del contenido que Diana ha preparado...</i>"
            )
            keyboard = None  # VIP users don't need options

        else:
            # Free user — show options
            text = self._compose(
                f"🎩 <b>Lucien:</b>",
                f"<i>{time_greeting}, <b>{user_name}</b>.</i>\n\n"
                f"<i>Bienvenido a los dominios de Diana...</i>\n\n"
                f"<i>¿Cómo puedo asistirle hoy?</i>"
            )
            keyboard = create_inline_keyboard([
                [{"text": "🎟️ Canjear Invitación VIP", "callback_data": "user:redeem_token"}],
                [{"text": "📺 Solicitar Acceso Free", "callback_data": "user:request_free"}],
            ])

        return (text, keyboard)

    def deep_link_activation_success(
        self,
        user_name: str,
        plan_name: str,
        duration_days: int,
        price: str,
        days_remaining: int,
        invite_link: str
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Success message after VIP activation via deep link.

        Args:
            user_name: User's first name
            plan_name: Plan name (e.g., "Plan Mensual")
            duration_days: Plan duration (e.g., 30)
            price: Formatted price (e.g., "$9.99")
            days_remaining: Days remaining on subscription
            invite_link: Telegram invite link to VIP channel

        Returns:
            Tuple of (text, keyboard) for complete UI

        Voice Rationale:
            Deep link activation is AUTOMATIC — celebrate this.
            Message is warmer than manual redemption (user took action).
            CTA is clear: "Join now" not "Here's your link".
            Link expiry creates urgency (5 hours).

        Examples:
            >>> msg = UserStartMessages()
            >>> text, kb = msg.deep_link_activation_success(
            ...     "Pedro", "Premium", 30, "$9.99", 30, "https://t.me/+ABC"
            ... )
            >>> "🎉" in text and "activ" in text.lower()
            True
        """
        # Two celebration variants (equal weight)
        celebrations = [
            "¡Excelente! Su suscripción VIP ha sido activada.",
            "¡Bienvenido al círculo exclusivo! Todo está listo."
        ]
        celebration = self._choose_variant(celebrations)

        text = self._compose(
            "🎩 <b>Lucien:</b>",
            f"<i>{celebration}</i>\n\n"
            f"🎉 <b>Plan:</b> {plan_name}\n"
            f"💰 <b>Inversión:</b> {price}\n"
            f"📅 <b>Duración:</b> {duration_days} días\n"
            f"⏱️ <b>Días Restantes:</b> {days_remaining}\n\n"
            f"<i>━━━━━━━━━━━━━━━━━━━━</i>\n\n"
            f"<i>Diana le espera en el canal exclusivo...</i>\n\n"
            f"<b>Siguiente Paso:</b>\n"
            f"<i>Haga click en el botón para unirse ahora.</i>\n\n"
            f"⚠️ <i>El acceso expira en 5 horas.</i>"
        )

        keyboard = create_inline_keyboard([
            [{"text": "⭐ Unirse al Canal VIP", "url": invite_link}]
        ])

        return (text, keyboard)
```

### Pattern 2: Role-Based Message Adaptation

**What:** Messages adapt content and tone based on user's role (admin/VIP/free).

**When to use:** For all user-facing messages where role matters.

**Rationale:**
- Admins need quick redirect to /admin (no clutter)
- VIP users see encouragement and status (days remaining)
- Free users see options (redeem token, request free)
- Same method handles all cases with boolean flags

**Example:**
```python
def greeting(
    self,
    user_name: str,
    is_admin: bool = False,
    is_vip: bool = False,
    vip_days_remaining: int = 0
) -> Tuple[str, InlineKeyboardMarkup]:
    """Single method adapts to all three roles."""
    if is_admin:
        # Concise redirect
        return (admin_text, None)
    elif is_vip:
        # Status + encouragement
        return (vip_text, None)
    else:
        # Options for free users
        return (free_text, options_keyboard)
```

### Pattern 3: Deep Link Flow Separation

**What:** Deep link activation uses different messaging than manual token redemption.

**When to use:** For VIP activation via t.me/bot?start=TOKEN vs manual input.

**Rationale:**
- Deep link = user clicked link (automatic, seamless)
- Manual redemption = user typed token (deliberate, needs validation)
- Deep link success is more celebratory
- Manual redemption includes "token redeemed" confirmation

**Example:**
```python
class UserFlowMessages(BaseMessageProvider):
    """User flow messages (VIP redemption, Free requests)."""

    def token_redemption_success(
        self,
        days_remaining: int,
        invite_link: str
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """Manual token redemption success (user typed token)."""
        text = self._compose(
            "🎩 <b>Lucien:</b>",
            "<i>Excelente. La invitación ha sido validada.</i>\n\n"
            f"⏱️ <b>Duración:</b> {days_remaining} días\n\n"
            "<i>Use el enlace abajo para unirse al círculo exclusivo...</i>"
        )
        keyboard = create_inline_keyboard([
            [{"text": "⭐ Unirse al Canal VIP", "url": invite_link}]
        ])
        return (text, keyboard)

    # Deep link activation uses different message
    # (more celebratory, auto-activation focus)
```

### Pattern 4: Semantic Test Helpers

**What:** Test helpers that check message semantics (greeting present, error type) instead of exact strings.

**When to use:** For ALL message provider tests to prevent brittleness.

**Rationale:**
- String matching breaks when adding variations
- Semantic assertions survive message changes
- Tests focus on INTENT not EXACT WORDING
- Easy to extend for new message types

**Example:**
```python
# tests/conftest.py
import pytest

@pytest.fixture
def assert_greeting_present():
    """
    Semantic assertion: message contains a greeting.

    Checks for common Spanish greetings regardless of exact wording.
    Survives variation changes without breaking tests.

    Usage:
        >>> text = "Buenos días, Juan"
        >>> assert_greeting_present(text)  # Passes
        >>> text = "Error occurred"
        >>> assert_greeting_present(text)  # Fails
    """
    def _assert(text: str):
        greetings = [
            "buenos días", "buen día", "buenas tardes", "buena tarde",
            "buenas noches", "buena noche", "bienvenido", "bienvenida",
            "hola", "saludos"
        ]
        text_lower = text.lower()
        has_greeting = any(g in text_lower for g in greetings)
        assert has_greeting, f"Message must contain greeting, got: {text[:100]}"

    return _assert


@pytest.fixture
def assert_lucien_voice():
    """
    Semantic assertion: message maintains Lucien's voice.

    Checks for voice characteristics:
    - 🎩 emoji present
    - No tutear (tú form)
    - No technical jargon
    - HTML formatting

    Usage:
        >>> text = "🎩 <b>Lucien:</b> <i>Buenos días</i>"
        >>> assert_lucien_voice(text)  # Passes
        >>> text = "Error: database connection failed"
        >>> assert_lucien_voice(text)  # Fails (technical jargon)
    """
    def _assert(text: str):
        # Check emoji
        assert "🎩" in text, "Message must include 🎩 emoji"

        # Check no tutear
        forbidden = ["tienes", "tu ", "tu.", "haz", "puedes"]
        text_lower = text.lower()
        for word in forbidden:
            assert word not in text_lower, f"Voice violated: tutear found ('{word}')"

        # Check no technical jargon
        technical = ["database", "api", "exception", "error code", "null"]
        for term in technical:
            assert term not in text_lower, f"Voice violated: technical jargon ('{term}')"

        # Check HTML formatting
        assert "<b>" in text or "<i>" in text, "Message must use HTML formatting"

    return _assert


@pytest.fixture
def assert_token_error_type():
    """
    Semantic assertion: token error message indicates specific error type.

    Checks for error category (invalid, expired, used) without matching exact strings.

    Usage:
        >>> text = "La invitación ya fue utilizada anteriormente"
        >>> assert_token_error_type(text, "used")  # Passes
        >>> assert_token_error_type(text, "invalid")  # Fails
    """
    def _assert(text: str, error_type: str):
        error_indicators = {
            "invalid": ["inválid", "no válid", "incorrec"],
            "expired": ["expirad", "vencid", "caducad"],
            "used": ["usado", "utilizado", "canjeado", "ya fue"]
        }

        indicators = error_indicators.get(error_type, [])
        text_lower = text.lower()

        has_indicator = any(ind in text_lower for ind in indicators)
        assert has_indicator, \
            f"Message must indicate '{error_type}' error, got: {text[:100]}"

    return _assert


@pytest.fixture
def assert_time_aware():
    """
    Semantic assertion: message adapts to time of day.

    Checks if greeting matches expected time period.

    Usage:
        >>> text = "Buenos días, Juan"
        >>> assert_time_aware(text, "morning")  # Passes
        >>> assert_time_aware(text, "evening")  # Fails
    """
    def _assert(text: str, time_period: str):
        time_indicators = {
            "morning": ["buenos días", "buen día", "mañana"],
            "afternoon": ["buenas tardes", "buena tarde"],
            "evening": ["buenas noches", "buena noche", "noche"]
        }

        indicators = time_indicators.get(time_period, [])
        text_lower = text.lower()

        has_indicator = any(ind in text_lower for ind in indicators)
        assert has_indicator, \
            f"Message must be {time_period}-aware, got: {text[:100]}"

    return _assert
```

### Pattern 5: Parametrized Variation Testing

**What:** Use pytest.mark.parametrize to test all message variations systematically.

**When to use:** For messages with multiple variations (greetings, confirmations).

**Example:**
```python
# tests/test_user_messages.py
import pytest
from unittest.mock import patch
from datetime import datetime

class TestUserStartMessages:
    """Test UserStartMessages provider with semantic assertions."""

    @pytest.mark.parametrize("hour,expected_period", [
        (9, "morning"),    # 9 AM
        (15, "afternoon"), # 3 PM
        (22, "evening")    # 10 PM
    ])
    def test_greeting_adapts_to_time(
        self,
        hour,
        expected_period,
        assert_time_aware,
        assert_lucien_voice
    ):
        """Verify greeting changes based on time of day."""
        from bot.services.message.user_start import UserStartMessages

        # Mock datetime to return specific hour
        mock_now = datetime(2026, 1, 23, hour, 0, 0)

        with patch('bot.services.message.user_start.datetime') as mock_dt:
            mock_dt.now.return_value = mock_now

            msg = UserStartMessages()
            text, kb = msg.greeting("TestUser", is_admin=False, is_vip=False)

            # Semantic assertions (survive variation changes)
            assert_time_aware(text, expected_period)
            assert_lucien_voice(text)
            assert "TestUser" in text

    def test_greeting_variations_all_valid(self, assert_lucien_voice):
        """Verify all greeting variations maintain voice consistency."""
        from bot.services.message.user_start import UserStartMessages

        msg = UserStartMessages()

        # Generate 30 greetings, should hit all variations
        seen_greetings = set()
        for _ in range(30):
            text, kb = msg.greeting("User", is_admin=False, is_vip=False)

            # Every variation must maintain voice
            assert_lucien_voice(text)

            # Track unique greetings
            # Extract just the greeting part (first line)
            greeting_line = text.split("\n")[0]
            seen_greetings.add(greeting_line)

        # Should have seen multiple variations (at least 2)
        assert len(seen_greetings) >= 2, \
            "Greetings should have variations"

    def test_admin_redirect_concise(self, assert_lucien_voice):
        """Verify admin greeting redirects to /admin without clutter."""
        from bot.services.message.user_start import UserStartMessages

        msg = UserStartMessages()
        text, kb = msg.greeting("Admin", is_admin=True)

        # Semantic checks
        assert_lucien_voice(text)
        assert "/admin" in text, "Must mention /admin command"
        assert kb is None, "Admin redirect should not have keyboard"

        # Should be concise (no options, no lengthy explanations)
        assert len(text) < 300, "Admin redirect should be brief"

    def test_vip_shows_days_remaining(self, assert_lucien_voice):
        """Verify VIP greeting shows subscription days."""
        from bot.services.message.user_start import UserStartMessages

        msg = UserStartMessages()
        text, kb = msg.greeting("VIPUser", is_vip=True, vip_days_remaining=15)

        # Semantic checks
        assert_lucien_voice(text)
        assert "15" in text, "Must show days remaining"
        assert "activo" in text.lower() or "exclusiv" in text.lower(), \
            "Must indicate VIP status"
```

### Anti-Patterns to Avoid

- **Exact string matching in tests:** Breaks when variations change
- **Single greeting variation:** Feels robotic for users who see /start repeatedly
- **Reusing admin message tone for users:** Users need warmer, more welcoming voice
- **Ignoring deep link context:** Auto-activation deserves celebratory messaging
- **Testing implementation not semantics:** Test "has greeting" not "equals 'Buenos días'"

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Time-of-day detection | Complex timezone logic | `datetime.now().hour` with simple ranges | Sufficient for greeting adaptation, no timezone complexity needed |
| Test assertion helpers | Custom assertion functions per test | Pytest fixtures in conftest.py | Reusable across all tests, discoverable |
| Message variation testing | Manual iteration 100 times | `@pytest.mark.parametrize` | Systematic, reports which case failed |
| HTML escaping user names | Manual .replace() chains | `escape_html()` from utils/formatters.py | Handles all entities, prevents XSS |
| Relative time formatting | Custom "X days ago" logic | `format_relative_time()` from formatters | Tested, handles edge cases |
| Keyboard construction | Manual InlineKeyboardButton loops | `create_inline_keyboard()` from utils/keyboards | Consistent structure, DRY |

**Key insight:** Test helpers in conftest.py create a semantic testing language. Don't write "assert 'Buenos días' in text" 50 times — write `assert_greeting_present(text)` once and reuse everywhere.

## Common Pitfalls

### Pitfall 1: Test Brittleness from String Matching

**What goes wrong:** Tests check exact strings (`assert text == "Buenos días, Juan"`). When adding message variations or improving wording, 20+ tests break even though semantic meaning unchanged.

**Why it happens:** Easiest to write initially, no thought about maintenance.

**How to avoid:**
- Use semantic helpers (`assert_greeting_present(text)`)
- Test message CATEGORY not exact wording
- Semantic helpers survive variation additions

**Warning signs:**
- Test failures after adding variations
- Tests with long string literals
- Multiple tests checking same exact phrase

**Example:**
```python
# BAD: Brittle string matching
def test_greeting():
    text, kb = msg.greeting("User")
    assert text == "🎩 Lucien: Buenos días, User"  # BREAKS if variation added

# GOOD: Semantic assertion
def test_greeting(assert_greeting_present, assert_lucien_voice):
    text, kb = msg.greeting("User")
    assert_greeting_present(text)  # Survives variation changes
    assert_lucien_voice(text)       # Validates voice consistency
    assert "User" in text           # Check dynamic content included
```

### Pitfall 2: Voice Inconsistency Between Admin and User Messages

**What goes wrong:** Admin messages use sophisticated Lucien voice ("círculo exclusivo") but user messages use casual tone ("¡Hola! 😊"). Voice breaks character.

**Why it happens:** Different developers, no voice guidelines enforcement.

**How to avoid:**
- UserMessages providers inherit from BaseMessageProvider
- Voice rationale in docstrings references guia-estilo.md
- Tests use `assert_lucien_voice()` for ALL messages
- Code review checklist: "Does this sound like Lucien?"

**Warning signs:**
- User messages use emojis Lucien wouldn't (😊🔥💯)
- User messages tutear ("tienes que hacer...")
- User messages use technical jargon ("error 404")

### Pitfall 3: Ignoring Time-of-Day Context

**What goes wrong:** User sees "Buenos días" at 11 PM. Feels generic and robotic.

**Why it happens:** Simplest to use static greeting, time detection seems complex.

**How to avoid:**
- Time detection is 3 lines: `hour = datetime.now().hour; if 6 <= hour < 12: ...`
- Performance impact: <0.1ms
- User experience impact: significant (feels personalized)

**Warning signs:**
- Greeting doesn't change throughout day
- No datetime.now() call in greeting methods
- Tests don't mock different hours

### Pitfall 4: Deep Link Messages Identical to Manual Redemption

**What goes wrong:** Deep link activation shows "Token redeemed successfully" — but user never saw a token. Confusing UX.

**Why it happens:** Code reuse without considering UX differences.

**How to avoid:**
- Separate methods: `deep_link_activation_success()` vs `token_redemption_success()`
- Deep link messaging: "Suscripción activada" (no mention of token)
- Manual redemption: "Invitación validada" (confirms token worked)

**Warning signs:**
- Deep link success mentions "token"
- Same message method used for both flows
- User feedback: "What token? I just clicked a link"

### Pitfall 5: Missing Role Detection in Greetings

**What goes wrong:** Admin user sees "Welcome! Here are your options: Redeem Token, Request Free" — but admin needs /admin menu, not user options.

**Why it happens:** Single greeting method, no role branching.

**How to avoid:**
- `greeting()` method accepts `is_admin`, `is_vip` flags
- Admin gets concise redirect to /admin
- VIP gets status + encouragement
- Free users get options

**Warning signs:**
- Admin sees user options
- VIP sees "Redeem Token" (they already have access)
- Single greeting message for all roles

## Code Examples

### Complete User Provider Example

```python
# bot/services/message/user_start.py
from datetime import datetime
from typing import Tuple, Optional
from aiogram.types import InlineKeyboardMarkup
from bot.services.message.base import BaseMessageProvider
from bot.utils.keyboards import create_inline_keyboard
from bot.utils.formatters import format_currency, escape_html

class UserStartMessages(BaseMessageProvider):
    """
    User /start command messages provider.

    Voice Characteristics (from docs/guia-estilo.md):
    - Warmer than admin messages (users need welcoming)
    - Time-of-day awareness (morning/afternoon/evening)
    - Role-based adaptation (admin/VIP/free)
    - Always uses "usted" form
    - Emoji 🎩 for Lucien
    - References Diana with 🌸

    Variations:
    - Greetings: 3 weighted (50%, 30%, 20%) per time period
    - Confirmations: 2 equal (50%, 50%)
    - Errors: Static (consistency more important)

    Stateless Design:
    - No session or bot stored
    - All context passed as parameters
    """

    def greeting(
        self,
        user_name: str,
        is_admin: bool = False,
        is_vip: bool = False,
        vip_days_remaining: int = 0
    ) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """
        Context-aware greeting for /start command.

        Adapts to:
        - Time of day (morning/afternoon/evening)
        - User role (admin/VIP/free)
        - VIP subscription status

        Args:
            user_name: User's first name (escaped in method)
            is_admin: Whether user is an admin
            is_vip: Whether user has active VIP subscription
            vip_days_remaining: Days remaining on VIP (if is_vip=True)

        Returns:
            Tuple of (text, keyboard) for complete UI

        Voice Rationale:
            Time-of-day creates natural personality.
            Admin gets concise redirect (no clutter).
            VIP sees encouragement and status.
            Free users see warm welcome with clear options.
        """
        # Escape user input for HTML safety
        safe_name = escape_html(user_name)

        # Time-of-day detection
        hour = datetime.now().hour

        if 6 <= hour < 12:
            time_greetings = ["Buenos días", "Buen día", "Bienvenido esta mañana"]
            weights = [0.5, 0.3, 0.2]
        elif 12 <= hour < 20:
            time_greetings = ["Buenas tardes", "Bienvenido", "Buena tarde"]
            weights = [0.5, 0.3, 0.2]
        else:  # 20-6
            time_greetings = ["Buenas noches", "Buena noche", "Bienvenido esta noche"]
            weights = [0.5, 0.3, 0.2]

        time_greeting = self._choose_variant(time_greetings, weights)

        # Role-based content
        if is_admin:
            text = self._compose(
                "🎩 <b>Lucien:</b>",
                f"<i>{time_greeting}, <b>{safe_name}</b>.</i>\n\n"
                "<i>Como custodio de los dominios de Diana, "
                "le sugiero usar /admin para sus responsabilidades.</i>"
            )
            return (text, None)

        if is_vip:
            text = self._compose(
                "🎩 <b>Lucien:</b>",
                f"<i>{time_greeting}, <b>{safe_name}</b>.</i>\n\n"
                "<i>Su acceso al círculo exclusivo está activo.</i>\n\n"
                f"⏱️ <b>Días restantes:</b> {vip_days_remaining}\n\n"
                "<i>Disfrute del contenido que Diana ha preparado...</i>"
            )
            return (text, None)

        # Free user — show options
        text = self._compose(
            "🎩 <b>Lucien:</b>",
            f"<i>{time_greeting}, <b>{safe_name}</b>.</i>\n\n"
            "<i>Bienvenido a los dominios de Diana...</i>\n\n"
            "<i>¿Cómo puedo asistirle hoy?</i>"
        )

        keyboard = create_inline_keyboard([
            [{"text": "🎟️ Canjear Invitación VIP", "callback_data": "user:redeem_token"}],
            [{"text": "📺 Solicitar Acceso Free", "callback_data": "user:request_free"}],
        ])

        return (text, keyboard)

    def deep_link_activation_success(
        self,
        user_name: str,
        plan_name: str,
        duration_days: int,
        price: str,
        days_remaining: int,
        invite_link: str
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Success message after VIP activation via deep link.

        Used when user clicks t.me/bot?start=TOKEN (automatic activation).

        Args:
            user_name: User's first name
            plan_name: Plan name (e.g., "Plan Mensual")
            duration_days: Plan duration (e.g., 30)
            price: Formatted price (e.g., "$9.99")
            days_remaining: Days remaining on subscription
            invite_link: Telegram invite link to VIP channel

        Returns:
            Tuple of (text, keyboard) for complete UI

        Voice Rationale:
            Deep link is AUTOMATIC — celebrate this seamlessness.
            More celebratory than manual redemption.
            CTA is clear: "Join now" creates urgency.
            Link expiry (5 hours) mentioned prominently.
        """
        # Two celebration variants (equal weight)
        celebrations = [
            "¡Excelente! Su suscripción VIP ha sido activada.",
            "¡Bienvenido al círculo exclusivo! Todo está listo."
        ]
        celebration = self._choose_variant(celebrations)

        safe_name = escape_html(user_name)

        text = self._compose(
            "🎩 <b>Lucien:</b>",
            f"<i>{celebration}</i>\n\n"
            f"🎉 <b>Plan:</b> {plan_name}\n"
            f"💰 <b>Inversión:</b> {price}\n"
            f"📅 <b>Duración:</b> {duration_days} días\n"
            f"⏱️ <b>Días Restantes:</b> {days_remaining}\n\n"
            "<i>━━━━━━━━━━━━━━━━━━━━</i>\n\n"
            "<i>Diana le espera en el canal exclusivo...</i>\n\n"
            "<b>Siguiente Paso:</b>\n"
            "<i>Haga click en el botón para unirse ahora.</i>\n\n"
            "⚠️ <i>El acceso expira en 5 horas.</i>"
        )

        keyboard = create_inline_keyboard([
            [{"text": "⭐ Unirse al Canal VIP", "url": invite_link}]
        ])

        return (text, keyboard)

    def deep_link_activation_error(
        self,
        error_type: str,
        details: str = ""
    ) -> str:
        """
        Error message for deep link activation failures.

        Args:
            error_type: Type of error ("invalid", "expired", "used", "no_plan")
            details: Optional additional details

        Returns:
            HTML-formatted error message (no keyboard)

        Voice Rationale:
            Errors are polite but clear about the problem.
            Offers next steps (contact admin, try again).
            No panic, maintains Lucien's composure.
        """
        error_messages = {
            "invalid": (
                "<i>La invitación que intentó usar no es válida.</i>\n\n"
                "<i>Posibles causas:</i>\n"
                "• <i>Invitación incorrecta</i>\n"
                "• <i>Invitación ya utilizada</i>\n"
                "• <i>Invitación expirada</i>"
            ),
            "used": (
                "<i>Esta invitación ya fue utilizada anteriormente.</i>\n\n"
                "<i>Diana no permite el uso múltiple de invitaciones.</i>"
            ),
            "expired": (
                "<i>La invitación ha expirado.</i>\n\n"
                "<i>Solicite una nueva invitación al administrador.</i>"
            ),
            "no_plan": (
                "<i>La invitación no tiene un plan de suscripción válido.</i>\n\n"
                "<i>Consulte con el administrador sobre este asunto.</i>"
            )
        }

        body = error_messages.get(error_type, error_messages["invalid"])

        if details:
            body += f"\n\n<i>{details}</i>"

        return self._compose(
            "🎩 <b>Lucien:</b>",
            body
        )


class UserFlowMessages(BaseMessageProvider):
    """
    User flow messages (VIP token redemption, Free requests).

    Voice Characteristics:
    - Warmer than admin (users need guidance)
    - Clear instructions (no mystery for action steps)
    - Encouraging confirmations
    - Polite error handling
    """

    def token_redemption_prompt(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Prompt user to enter VIP token manually.

        Used when user clicks "Redeem Token" button.

        Returns:
            Tuple of (text, keyboard) with cancel button

        Voice Rationale:
            Instructions are clear but maintain Lucien's voice.
            Example token format helps user understand.
            Cancel option always available.
        """
        text = self._compose(
            "🎩 <b>Lucien:</b>",
            "<i>Por favor, envíe su invitación VIP.</i>\n\n"
            "<i>El formato de la invitación es:</i>\n"
            "<code>A1b2C3d4E5f6G7h8</code>\n\n"
            "<i>👉 Copie y pegue su invitación aquí...</i>"
        )

        keyboard = create_inline_keyboard([
            [{"text": "❌ Cancelar", "callback_data": "user:cancel"}]
        ])

        return (text, keyboard)

    def token_redemption_success(
        self,
        days_remaining: int,
        invite_link: str
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Success message after manual token redemption.

        Used when user manually types token (not deep link).

        Args:
            days_remaining: Days remaining on new subscription
            invite_link: Telegram invite link to VIP channel

        Returns:
            Tuple of (text, keyboard) with join button

        Voice Rationale:
            Confirms token was validated.
            Less celebratory than deep link (user did manual work).
            Link expiry (1 hour) creates urgency.
        """
        text = self._compose(
            "🎩 <b>Lucien:</b>",
            "<i>Excelente. La invitación ha sido validada.</i>\n\n"
            f"🎉 <b>Acceso VIP activado</b>\n"
            f"⏱️ <b>Duración:</b> {days_remaining} días\n\n"
            "<i>Use el enlace abajo para unirse al círculo exclusivo...</i>\n\n"
            "⚠️ <b>Importante:</b>\n"
            "• <i>El enlace expira en 1 hora</i>\n"
            "• <i>Solo puede usarlo 1 vez</i>\n"
            "• <i>No lo comparta con otros</i>"
        )

        keyboard = create_inline_keyboard([
            [{"text": "⭐ Unirse al Canal VIP", "url": invite_link}]
        ])

        return (text, keyboard)

    def token_redemption_error(
        self,
        error_type: str
    ) -> str:
        """
        Error message for token redemption failures.

        Args:
            error_type: Type of error ("invalid", "expired", "used")

        Returns:
            HTML-formatted error message (no keyboard, maintains FSM state)

        Voice Rationale:
            Clear about error but offers retry.
            Maintains FSM state (user can try again).
            Suggests contacting admin if persistent.
        """
        error_messages = {
            "invalid": (
                "<i>La invitación que envió no es válida.</i>\n\n"
                "<i>Verifique la invitación e intente nuevamente.</i>"
            ),
            "used": (
                "<i>Esta invitación ya fue utilizada.</i>\n\n"
                "<i>Cada invitación solo puede usarse una vez.</i>"
            ),
            "expired": (
                "<i>La invitación ha expirado.</i>\n\n"
                "<i>Solicite una nueva invitación al administrador.</i>"
            )
        }

        body = error_messages.get(error_type, error_messages["invalid"])
        body += "\n\n<i>Si el problema persiste, consulte con el administrador.</i>"

        return self._compose("🎩 <b>Lucien:</b>", body)

    def free_request_success(
        self,
        wait_time_minutes: int
    ) -> str:
        """
        Success message after Free channel request created.

        Args:
            wait_time_minutes: Wait time configured by admin

        Returns:
            HTML-formatted success message (no keyboard)

        Voice Rationale:
            Confirms request received.
            Sets expectation (wait time).
            Reassures user (automatic, no action needed).
        """
        text = self._compose(
            "🎩 <b>Lucien:</b>",
            "<i>Excelente. Su solicitud ha sido registrada.</i>\n\n"
            f"⏱️ <b>Tiempo de espera:</b> {wait_time_minutes} minutos\n\n"
            "📨 <i>Recibirá un mensaje con el enlace de invitación "
            "cuando el tiempo se cumpla.</i>\n\n"
            "💡 <i>No necesita hacer nada más. El proceso es automático.</i>\n\n"
            "<i>Puede cerrar este chat. Le notificaré cuando esté listo...</i> 🔔"
        )

        return text

    def free_request_duplicate(
        self,
        time_elapsed_minutes: int,
        time_remaining_minutes: int
    ) -> str:
        """
        Message when user already has pending Free request.

        Args:
            time_elapsed_minutes: Minutes since original request
            time_remaining_minutes: Minutes until access granted

        Returns:
            HTML-formatted informational message (no keyboard)

        Voice Rationale:
            Polite reminder of existing request.
            Shows progress (time elapsed).
            Reassures automatic delivery.
        """
        text = self._compose(
            "🎩 <b>Lucien:</b>",
            "<i>Ya tiene una solicitud en proceso.</i>\n\n"
            f"⏱️ <b>Tiempo transcurrido:</b> {time_elapsed_minutes} minutos\n"
            f"⌛ <b>Tiempo restante:</b> {time_remaining_minutes} minutos\n\n"
            "<i>Recibirá el enlace de acceso automáticamente cuando "
            "el tiempo se cumpla.</i>\n\n"
            "💡 <i>Puede cerrar este chat. Le notificaré cuando esté listo.</i>"
        )

        return text
```

### Handler Integration Example (Migrated)

```python
# bot/handlers/user/start.py (MIGRATED)
import logging
from datetime import datetime, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.enums import UserRole
from bot.middlewares import DatabaseMiddleware
from bot.services.container import ServiceContainer
from config import Config

logger = logging.getLogger(__name__)

user_router = Router(name="user")
user_router.message.middleware(DatabaseMiddleware())
user_router.callback_query.middleware(DatabaseMiddleware())


@user_router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession):
    """
    Handler del comando /start para usuarios.

    MIGRATED: Now uses UserStartMessages provider for all UI text/keyboards.

    Comportamiento:
    - Si hay parámetro (deep link) → Activa token automáticamente
    - Si es admin → Redirige a /admin
    - Si es VIP activo → Muestra días restantes
    - Si no es admin → Muestra menú de usuario (VIP/Free)
    """
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Usuario"

    logger.info(f"👋 Usuario {user_id} ({user_name}) ejecutó /start")

    # Crear/obtener usuario
    container = ServiceContainer(session, message.bot)
    user = await container.user.get_or_create_user(
        telegram_user=message.from_user,
        default_role=UserRole.FREE
    )

    # Verificar parámetro (deep link)
    args = message.text.split(maxsplit=1)

    if len(args) > 1:
        # Deep link con token
        token_string = args[1].strip()
        logger.info(f"🔗 Deep link detectado: Token={token_string} | User={user_id}")

        await _activate_token_from_deeplink(
            message, session, container, user, token_string
        )
    else:
        # Mensaje de bienvenida normal
        await _send_welcome_message(message, user, container, user_id)


async def _send_welcome_message(
    message: Message,
    user,
    container: ServiceContainer,
    user_id: int
):
    """
    Envía mensaje de bienvenida usando UserStartMessages provider.

    MIGRATED: All text/keyboard generation delegated to message service.
    """
    user_name = message.from_user.first_name or "Usuario"

    # Detectar rol y estado
    is_admin = Config.is_admin(user_id)
    is_vip = await container.subscription.is_vip_active(user_id)

    vip_days_remaining = 0
    if is_vip:
        subscriber = await container.subscription.get_vip_subscriber(user_id)
        if subscriber and subscriber.expiry_date:
            expiry = subscriber.expiry_date
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            vip_days_remaining = max(0, (expiry - now).days)

    # GET TEXT AND KEYBOARD FROM MESSAGE PROVIDER
    text, keyboard = container.message.user.start.greeting(
        user_name=user_name,
        is_admin=is_admin,
        is_vip=is_vip,
        vip_days_remaining=vip_days_remaining
    )

    # Send message (no formatting logic in handler!)
    await message.answer(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
```

### Semantic Test Example

```python
# tests/test_user_messages.py
import pytest
from unittest.mock import patch
from datetime import datetime

class TestUserStartMessages:
    """Test UserStartMessages with semantic assertions."""

    @pytest.mark.parametrize("hour,expected_period", [
        (9, "morning"),
        (15, "afternoon"),
        (22, "evening")
    ])
    def test_greeting_time_awareness(
        self,
        hour,
        expected_period,
        assert_time_aware,
        assert_lucien_voice
    ):
        """Verify greeting adapts to time of day."""
        from bot.services.message.user_start import UserStartMessages

        mock_now = datetime(2026, 1, 23, hour, 0, 0)

        with patch('bot.services.message.user_start.datetime') as mock_dt:
            mock_dt.now.return_value = mock_now

            msg = UserStartMessages()
            text, kb = msg.greeting("TestUser")

            # SEMANTIC ASSERTIONS (survive variation changes)
            assert_time_aware(text, expected_period)
            assert_lucien_voice(text)
            assert "TestUser" in text

    def test_deep_link_activation_success_celebratory(
        self,
        assert_lucien_voice
    ):
        """Verify deep link success is celebratory."""
        from bot.services.message.user_start import UserStartMessages

        msg = UserStartMessages()
        text, kb = msg.deep_link_activation_success(
            user_name="Pedro",
            plan_name="Premium",
            duration_days=30,
            price="$9.99",
            days_remaining=30,
            invite_link="https://t.me/+ABC"
        )

        # Semantic checks (not exact strings)
        assert_lucien_voice(text)
        assert "🎉" in text or "excelente" in text.lower(), \
            "Deep link success should be celebratory"
        assert "Premium" in text
        assert "$9.99" in text
        assert "30" in text

        # Should have join button
        assert kb is not None
        # Button should point to invite link
        assert "ABC" in str(kb)

    def test_token_error_types_distinguishable(
        self,
        assert_token_error_type,
        assert_lucien_voice
    ):
        """Verify different token errors are semantically distinct."""
        from bot.services.message.user_start import UserStartMessages

        msg = UserStartMessages()

        # Test each error type
        invalid_msg = msg.deep_link_activation_error("invalid")
        assert_lucien_voice(invalid_msg)
        assert_token_error_type(invalid_msg, "invalid")

        used_msg = msg.deep_link_activation_error("used")
        assert_lucien_voice(used_msg)
        assert_token_error_type(used_msg, "used")

        expired_msg = msg.deep_link_activation_error("expired")
        assert_lucien_voice(expired_msg)
        assert_token_error_type(expired_msg, "expired")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded strings in user handlers | UserMessages provider with variations | This phase | Users see dynamic, time-aware greetings |
| Exact string matching in tests | Semantic test helpers (conftest.py) | This phase | Tests survive variation changes |
| Static greetings | Time-of-day + role-based adaptation | This phase | Personalized UX at zero performance cost |
| Identical deep link and manual messages | Separate messaging for each flow | This phase | UX matches user journey |
| Single greeting per handler | 3 weighted variations per time period | This phase | Bot feels alive, less repetitive |

**Deprecated/outdated:**
- Hardcoded f-strings in handlers: Violates voice consistency, breaks under variation changes
- `assert text == "..."` in tests: Extremely brittle, breaks when improving messages
- Static greetings ignoring time: Feels robotic, misses easy personalization win

## Open Questions

### Question 1: How Many Greeting Variations is Optimal?

**What we know:** Phase 2 admin messages use 2 variations. User messages might need more (users see /start repeatedly).

**What's unclear:** Does 3 variations provide enough variety without maintenance burden?

**Recommendation:** 3 weighted variations (50%, 30%, 20%) per time period (morning/afternoon/evening) = 9 total greeting variants. This creates rich variety without explosion. Test with 30 /start calls — should see natural distribution, no repetition fatigue. If users report "still feels robotic," increase to 4 per period in Phase 4.

### Question 2: Should Time-of-Day Use User Timezone or Server Timezone?

**What we know:** `datetime.now().hour` uses server timezone (UTC in production). User in GMT-5 sees "Buenas noches" at 7 PM (server midnight).

**What's unclear:** Is server timezone good enough or does time-of-day need user timezone?

**Recommendation:** Server timezone is sufficient for Phase 3. User timezone requires storing timezone per user (DB schema change) and adds complexity. Most users in same timezone as server. If Phase 4 shows timezone mismatches as top complaint, add user timezone preference. For now, KISS principle.

### Question 3: How to Test Weighted Variations Without Flakiness?

**What we know:** Weighted variations (50%, 30%, 20%) are probabilistic. Testing with small sample (N=10) could fail randomly.

**What's unclear:** What sample size guarantees all variations appear at least once?

**Recommendation:** N=30 iterations catches all 3 variations with >99% confidence. Test structure:
```python
seen = set()
for _ in range(30):
    text, kb = msg.greeting("User")
    seen.add(extract_greeting(text))
assert len(seen) >= 2  # At minimum, should see 2 variants
```
Don't assert `len(seen) == 3` (could fail <1% due to randomness). Assert `>= 2` is pragmatic.

## Sources

### Primary (HIGH confidence)

- **bot/handlers/user/start.py** (327 lines) — Current hardcoded messages, deep link flow, role detection
- **bot/handlers/user/vip_flow.py** (189 lines) — Token redemption flow, FSM patterns
- **bot/handlers/user/free_flow.py** (93 lines) — Free request flow, duplicate handling
- **bot/services/message/base.py** — BaseMessageProvider with `_compose()`, `_choose_variant()` utilities
- **tests/test_message_service.py** (449 lines) — Existing test patterns, semantic assertions
- **Phase 2 research** — Admin message patterns, keyboard integration, variation strategy

### Secondary (MEDIUM confidence)

- **.planning/REQUIREMENTS.md** — DYN-02 (lists), DYN-03 (contextual), REFAC-04/05/06 (user handlers)
- **.planning/STATE.md** — Prior decisions (stdlib-only, navigation-based, stateless)
- **docs/guia-estilo.md** — Lucien's voice rules, emoji usage, forbidden patterns
- **pytest documentation** — Fixture patterns, parametrize, AsyncMock usage

### Tertiary (LOW confidence)

- **General testing best practices** — Semantic assertions, test brittleness prevention
- **Telegram bot UX patterns** — Deep link flows, time-of-day greetings

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All stdlib, pytest, or existing (no new dependencies)
- Architecture: HIGH - Patterns proven in Phase 2, user flows well-understood
- Testing strategy: HIGH - Semantic helpers solve known brittleness problems
- Time-of-day variations: MEDIUM - Implementation simple, timezone edge cases exist

**Research date:** 2026-01-23
**Valid until:** 2026-03-23 (60 days - stable domain, patterns unlikely to change)

---

*Research completed: 2026-01-23*
*Ready for planning: YES*
*Synthesized by: GSD Phase Researcher*
