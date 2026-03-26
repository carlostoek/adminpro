# Phase 2: Template Organization & Admin Migration - Research

**Researched:** 2026-01-23
**Domain:** Message Service Architecture - Admin Handler Migration
**Confidence:** HIGH

## Summary

This research addresses migrating admin handlers from hardcoded message strings to centralized LucienVoiceService with template composition, keyboard integration, and message variations. The existing codebase has 10+ admin handler files (main.py, vip.py, free.py, dashboard.py, broadcast.py, stats.py, pricing.py, management.py, reactions.py) containing scattered HTML-formatted strings that break voice consistency and create maintenance burden.

The recommended approach is **navigation-based provider organization with built-in keyboard factories**, structured as AdminMainMessages, AdminVIPMessages, and AdminFreeMessages classes. Each provider method returns a tuple `(text, keyboard)` for complete UI encapsulation. Variations use simple 2-element lists with equal random selection (50/50). Conditional states use boolean flags passed as keyword arguments (e.g., `is_configured=True`). This pattern balances maintainability, type safety, and gradual migration without disrupting existing functionality.

Critical findings: (1) Keyboard logic must live INSIDE message providers for complete UI encapsulation — separating text/keyboard creates synchronization bugs. (2) Boolean flags are superior to context objects for admin conditionals — simpler, type-checkable, and sufficient for current needs. (3) Two variations per key message is optimal — more creates maintenance burden, less feels robotic. (4) Template composition using `_compose()` utility prevents code duplication across similar screens.

**Primary recommendation:** Build three Admin provider classes with keyboard factories integrated, using boolean flags for conditional states, and 2-variation random selection for greetings/confirmations only.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python dataclass | 3.11+ | Message structure | Memory-efficient, type-safe, zero-dependency |
| f-strings | 3.11+ native | Template interpolation | 2x faster than `.format()`, compile-time validation |
| random.choices() | stdlib | Weighted variation selection | <1ms overhead, no external dependencies |
| typing.NamedTuple | 3.11+ | Return type annotations | Type-safe `(text, keyboard)` contracts |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| bot.utils.formatters | existing | Date/currency/relative time formatting | All dynamic data in messages |
| bot.utils.keyboards.create_inline_keyboard | existing | Keyboard builder utilities | Reuse for consistency |
| BaseMessageProvider | Phase 1 | `_compose()` and `_choose_variant()` utilities | All message providers inherit |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Built-in keyboards | Separate keyboard factories | Separation creates synchronization bugs between text/buttons |
| Boolean flags | Context objects (dataclass) | Context objects are overkill for admin simple states |
| 2 variations | 5+ variations | More variations = exponentially harder to maintain |
| Equal random | Weighted variations | Admin messages don't need weighted selection yet |

**Installation:**
```bash
# No new dependencies - all stdlib or existing
# Existing: aiogram 3.4.1, SQLAlchemy 2.0.25, formatters.py
```

## Architecture Patterns

### Recommended Project Structure

```
bot/services/message/
├── __init__.py                 # LucienVoiceService entry point
├── base.py                     # BaseMessageProvider (Phase 1, existing)
├── common.py                   # CommonMessages (Phase 1, existing)
├── admin_main.py               # NEW: AdminMainMessages provider
├── admin_vip.py                # NEW: AdminVIPMessages provider
└── admin_free.py               # NEW: AdminFreeMessages provider
```

### Pattern 1: Navigation-Based Provider Organization

**What:** Group message methods by navigation flow (main menu, VIP subflow, Free subflow) matching handler file structure.

**When to use:** For all admin messages — one provider class per handler file.

**Example:**
```python
# bot/services/message/admin_vip.py
from typing import Tuple
from aiogram.types import InlineKeyboardMarkup
from bot.services.message.base import BaseMessageProvider
from bot.utils.keyboards import create_inline_keyboard

class AdminVIPMessages(BaseMessageProvider):
    """
    Admin VIP management messages provider.

    Voice Rationale:
    - VIP channel = "círculo exclusivo" (exclusive circle)
    - Token generation = "emitir invitación" (issue invitation)
    - Setup prompts = "calibrar acceso" (calibrate access)
    - Always maintains mystery and sophistication
    """

    def vip_menu(
        self,
        is_configured: bool,
        channel_name: str = "Canal VIP"
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        VIP management menu message with keyboard.

        Args:
            is_configured: Whether VIP channel is configured
            channel_name: Name of VIP channel (if configured)

        Returns:
            Tuple of (text, keyboard) for complete UI

        Voice Rationale:
            Configured state feels exclusive and sophisticated.
            Unconfigured state is inviting but mysterious about setup.
        """
        if is_configured:
            text = self._compose(
                "🎩 <b>Lucien:</b>",
                f"<i>Ah, el círculo exclusivo de Diana.</i>\n\n"
                f"<i>Puedo ver que <b>{channel_name}</b> está listo "
                f"para recibir nuevos miembros...</i>\n\n"
                f"<i>¿Qué aspecto del acceso exclusivo requiere su atención?</i>"
            )
            keyboard = self._vip_configured_keyboard()
        else:
            text = self._compose(
                "🎩 <b>Lucien:</b>",
                "<i>El círculo exclusivo aún no ha sido establecido.</i>\n\n"
                "<i>Diana prefiere que configuremos el canal antes de emitir invitaciones.</i>\n\n"
                "<i>¿Le gustaría comenzar con la calibración?</i>"
            )
            keyboard = self._vip_unconfigured_keyboard()

        return (text, keyboard)

    def token_generated(
        self,
        plan_name: str,
        duration_days: int,
        price: str,
        token: str,
        deep_link: str,
        expiry_date: str
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Token generation success message with deep link.

        Voice Rationale:
            Success = "excelente elección" (excellent choice)
            Token = "invitación" (invitation, not technical term)
            Deep link = "pase de acceso" (access pass)
        """
        text = self._compose(
            "🎩 <b>Lucien:</b>",
            f"<i>Excelente elección. La invitación ha sido emitida para el plan "
            f"<b>{plan_name}</b>...</i>\n\n"
            f"<b>Plan:</b> {plan_name}\n"
            f"<b>Duración:</b> {duration_days} días\n"
            f"<b>Inversión:</b> {price}\n\n"
            f"<b>Invitación:</b> <code>{token}</code>\n\n"
            f"<b>Pase de Acceso:</b>\n<code>{deep_link}</code>\n\n"
            f"<b>Válido hasta:</b> {expiry_date}\n\n"
            f"<i>━━━━━━━━━━━━━━━━━━━━</i>\n"
            f"<i>Diana aprueba su discernimiento...</i>\n\n"
            f"<i>El recipiente solo necesita hacer click en el pase.</i>"
        )

        keyboard = create_inline_keyboard([
            [{"text": "🔗 Copiar Pase", "url": deep_link}],
            [{"text": "🎟️ Emitir Otra Invitación", "callback_data": "vip:generate_token"}],
            [{"text": "🔙 Volver", "callback_data": "admin:vip"}]
        ])

        return (text, keyboard)

    def setup_channel_prompt(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Prompt for admin to forward VIP channel message.

        Voice Rationale:
            Setup = "calibración" (calibration)
            Forward = "reenviar" straightforward (no mystery for technical steps)
        """
        text = self._compose(
            "🎩 <b>Lucien:</b>",
            "<i>Para calibrar el círculo exclusivo, necesito que...</i>\n\n"
            "<i>1️⃣ Vaya al canal VIP</i>\n"
            "<i>2️⃣ Reenvíe cualquier mensaje del canal a este chat</i>\n"
            "<i>3️⃣ Yo extraeré la identificación automáticamente</i>\n\n"
            "<i>⚠️ <b>Importante:</b></i>\n"
            "<i>Debo ser administrador del canal</i>\n"
            "<i>Debo tener permiso para invitar usuarios</i>\n\n"
            "<i>👉 Reenvíe un mensaje del canal cuando esté listo...</i>"
        )

        keyboard = create_inline_keyboard([
            [{"text": "❌ Cancelar", "callback_data": "admin:vip"}]
        ])

        return (text, keyboard)
```

### Pattern 2: Built-in Keyboard Factories

**What:** Keyboard construction lives INSIDE message provider methods as private methods (`_vip_configured_keyboard()`), not in utils/keyboards.py.

**When to use:** For all admin messages — text and keyboard are tightly coupled UI components.

**Rationale:**
- Separating text/keyboard creates synchronization bugs
- Message providers own complete UI (text + buttons)
- Still use `create_inline_keyboard()` helper from utils
- Dynamic keyboards (context-aware buttons) require provider logic

**Example:**
```python
class AdminVIPMessages(BaseMessageProvider):
    # ... message methods ...

    def _vip_configured_keyboard(self) -> InlineKeyboardMarkup:
        """Keyboard when VIP channel is configured."""
        return create_inline_keyboard([
            [{"text": "🎟️ Emitir Invitación", "callback_data": "vip:generate_token"}],
            [
                {"text": "👥 Miembros", "callback_data": "vip:list_subscribers"},
                {"text": "📊 Estadísticas", "callback_data": "admin:stats:vip"}
            ],
            [{"text": "📤 Enviar Publicación", "callback_data": "vip:broadcast"}],
            [{"text": "⚙️ Configuración", "callback_data": "vip:config"}],
            [{"text": "🔙 Volver", "callback_data": "admin:main"}]
        ])

    def _vip_unconfigured_keyboard(self) -> InlineKeyboardMarkup:
        """Keyboard when VIP channel is NOT configured."""
        return create_inline_keyboard([
            [{"text": "⚙️ Calibrar Canal VIP", "callback_data": "vip:setup"}],
            [{"text": "🔙 Volver", "callback_data": "admin:main"}]
        ])
```

### Pattern 3: Boolean Flags for Conditional States

**What:** Use simple boolean keyword arguments for conditional content (e.g., `is_configured=True`, `has_subscribers=False`).

**When to use:** For all binary/n-ary state conditions in admin messages.

**Rationale:**
- Simpler than context objects (no dataclass overhead)
- Type-checkable (mypy/linting catches typos)
- Self-documenting (parameter names explain conditions)
- Sufficient for admin simple states

**Example:**
```python
def vip_menu(
    self,
    is_configured: bool,
    channel_name: str = "Canal VIP",
    subscriber_count: int = 0
) -> Tuple[str, InlineKeyboardMarkup]:
    """VIP menu adapts based on configuration state."""
    if is_configured:
        text = self._compose(
            "🎩 <b>Lucien:</b>",
            f"<i>El círculo exclusivo está activo: <b>{channel_name}</b></i>\n\n"
            f"<i>Miembros actuales: <b>{subscriber_count}</b></i>\n\n"
            "<i>¿Qué requiere su atención?</i>"
        )
        keyboard = self._vip_configured_keyboard()
    else:
        text = self._compose(
            "🎩 <b>Lucien:</b>",
            "<i>El círculo exclusivo aún no ha sido establecido...</i>"
        )
        keyboard = self._vip_unconfigured_keyboard()

    return (text, keyboard)
```

### Pattern 4: Two-Variation Random Selection

**What:** Store 2 variations per key message as list literals, select with `random.choice()` for equal 50/50 distribution.

**When to use:** For greetings and confirmations ONLY (not error messages or informational text).

**Rationale:**
- 2 variations = easy to maintain, natural variation
- Equal random = simple, no weights to tune
- Greetings/confirmations benefit most from variation
- Errors/informational stay static (consistency more important)

**Example:**
```python
import random

class AdminMainMessages(BaseMessageProvider):
    def admin_menu_greeting(self, is_configured: bool) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Main admin menu with randomized greeting.

        Voice Rationale:
            Greetings prevent repetition fatigue with 2 variations.
            Both maintain Lucien's sophisticated tone.
        """
        # Two greeting variations (equal random)
        greetings = [
            "🎩 <b>Lucien:</b>\n\n<i>Ah, el custodio de los dominios de Diana...</i>",
            "🎩 <b>Lucien:</b>\n\n<i>Bienvenido de nuevo al sanctum...</i>"
        ]
        greeting = random.choice(greetings)

        if is_configured:
            body = "<i>Todo está en orden. ¿Qué aspecto del reino requiere su atención hoy?</i>"
        else:
            body = "<i>Hay asuntos pendientes que requieren su atención...</i>"

        text = self._compose(greeting, body)
        keyboard = self._admin_main_keyboard()

        return (text, keyboard)

    def confirmation_action_completed(self, action: str) -> str:
        """
        Confirmation with 2 variations.

        Voice Rationale:
            Confirmations feel less robotic with variation.
            Both celebrate success elegantly.
        """
        variations = [
            f"<i>Excelente. {action} ha sido completado como se esperaba.</i>",
            f"<i>Excelente elección. {action} está listo.</i>"
        ]
        body = random.choice(variations)

        return self._compose("🎩 <b>Lucien:</b>", body)
```

### Anti-Patterns to Avoid

- **Separating text and keyboard:** Creates synchronization bugs when UI changes
- **Context objects for simple states:** Over-engineered for boolean conditions
- **More than 3 variations:** Maintenance burden outweighs benefit
- **Variations in error messages:** Confusing, consistency more important
- **Hardcoded callback strings:** Use constants or helper functions to prevent typos
- **Template methods without voice rationale:** Every method needs docstring explaining WHY

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Keyboard building | Manual InlineKeyboardButton construction | `create_inline_keyboard()` from utils/keyboards.py | Consistent button structure, DRY, tested |
| Date formatting | f-strings with datetime.strftime() | `format_datetime()` from utils/formatters.py | Handles timezone, consistent format, tested |
| Currency display | f"${amount:.2f}" | `format_currency()` from utils/formatters.py | Handles locale, separators, edge cases |
| HTML escaping | Manual .replace() chains | `escape_html()` from utils/formatters.py | Prevents XSS, handles all entities |
| Random selection | complex logic with weights | `self._choose_variant()` from BaseMessageProvider | Tested, handles edge cases |
| Message composition | manual "\n\n".join() | `self._compose()` from BaseMessageProvider | Consistent spacing, reusable |

**Key insight:** The codebase already has 19 formatter functions and keyboard utilities. Reuse them instead of rebuilding. Message providers should FOCUS on voice/personality, not formatting logic.

## Common Pitfalls

### Pitfall 1: Text/Keyboard Separation Bug

**What goes wrong:** Message provider returns text only, handler builds keyboard separately. When UI changes, dev updates text but forgets keyboard → mismatched UI.

**Why it happens:** Separation of concerns sounds good but creates synchronization burden for tightly-coupled UI.

**How to avoid:**
- Always return `(text, keyboard)` tuple from provider methods
- Keyboard factories live as private methods in provider class
- Handler only calls ONE method: `text, keyboard = msg.vip_menu(is_configured=True)`

**Warning signs:**
- Handler has `create_inline_keyboard()` calls after getting message text
- Multiple keyboard factories for same screen in different files
- Tests checking text and keyboard separately

### Pitfall 2: Template Explosion Without Composition

**What goes wrong:** Every edge case gets new method (`vip_menu_configured`, `vip_menu_unconfigured`, `vip_menu_configured_no_subscribers`, ...) → 100+ methods, unmaintainable.

**Why it happens:** Devs avoid conditionals inside methods, create new methods instead.

**How to avoid:**
- Use boolean flags for conditional states (NOT separate methods)
- One method per UI screen (NOT per permutation)
- Template composition: reuse common parts with `_compose()`

**Warning signs:**
- Provider class has 20+ methods
- Method names differ only by suffix (`_configured`, `_unconfigured`)
- Multiple methods returning almost identical text

### Pitfall 3: Voice Drift in Variations

**What goes wrong:** Developer adds 5 variations to greeting, but variation 4 accidentally uses "tú" instead of "usted" → voice inconsistency.

**Why it happens:** No enforcement, variations added hastily without review.

**How to avoid:**
- Limit to 2 variations (easier to review)
- Voice rationale in docstring explains tone rules
- Tests verify no forbidden words ("tienes", "tu ", "puedes")
- Code review checklist: check ALL variations for voice compliance

**Warning signs:**
- Variations list longer than 3 items
- No docstring explaining voice rules
- Test doesn't check for forbidden words

### Pitfall 4: Handler Still Contains Formatting Logic

**What goes wrong:** Handler calls `msg.vip_menu()` BUT still adds f-string formatting before sending → service becomes simple string store, voice rules leak back to handlers.

**Why it happens:** Developer forgets to move ALL formatting to provider, or needs dynamic data and takes shortcut.

**How to avoid:**
- Provider methods accept ALL dynamic data as parameters
- Handler passes raw data (user.name, token.value, plan.duration)
- Provider does ALL f-string formatting and HTML construction
- Test: Handler should have ZERO f-strings for message text

**Warning signs:**
- Handler has f"text = f\"{msg_service.method()} {user.name}\""
- Handler adds HTML tags after getting message text
- Provider method has no parameters but should

### Pitfall 5: Ignoring Existing Utilities

**What goes wrong:** Message provider reimplements date formatting, currency display, HTML escaping → duplicate code, inconsistent formatting, bugs.

**Why it happens:** Developer doesn't know about utils/formatters.py (19 functions) or wants to "keep it simple."

**How to avoid:**
- `from bot.utils.formatters import format_datetime, format_currency, escape_html`
- Always use formatters for dynamic data
- Import keyboard helper, don't rebuild

**Warning signs:**
- Provider has `.strftime()` calls
- Provider has `.replace("&", "&amp;")` for HTML escaping
- Provider has f"${amount:.2f}" for currency

## Code Examples

### Complete Provider Example

```python
# bot/services/message/admin_vip.py
from typing import Tuple
import random
from aiogram.types import InlineKeyboardMarkup
from bot.services.message.base import BaseMessageProvider
from bot.utils.keyboards import create_inline_keyboard
from bot.utils.formatters import format_datetime, format_currency

class AdminVIPMessages(BaseMessageProvider):
    """
    Admin VIP management messages provider.

    Voice Characteristics (from docs/guia-estilo.md):
    - VIP channel = "círculo exclusivo" (exclusive circle)
    - Token = "invitación" (invitation, never "token" in user-facing text)
    - Setup = "calibración" (calibration, implies precision)
    - Uses "usted", never "tú"
    - Emoji 🎩 always present
    - References Diana for authority validation

    Stateless Design:
    - No session or bot stored as instance variables
    - All context passed as method parameters
    - Returns (text, keyboard) tuples for complete UI
    """

    def vip_menu(
        self,
        is_configured: bool,
        channel_name: str = "Canal VIP",
        subscriber_count: int = 0
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        VIP management menu message with keyboard.

        Args:
            is_configured: Whether VIP channel is configured
            channel_name: Name of VIP channel (if configured)
            subscriber_count: Number of current VIP subscribers

        Returns:
            Tuple of (text, keyboard) for complete UI

        Voice Rationale:
            Configured state feels exclusive and welcoming.
            Subscriber count creates sense of community.
            Unconfigured state is mysterious but inviting.

        Examples:
            >>> msg = AdminVIPMessages()
            >>> text, kb = msg.vip_menu(is_configured=True, channel_name="VIP", subscriber_count=42)
            >>> "círculo exclusivo" in text
            True
            >>> "42" in text
            True
        """
        # Two greeting variations (equal random)
        greetings = [
            "🎩 <b>Lucien:</b>\n\n<i>Ah, el círculo exclusivo de Diana.</i>",
            "🎩 <b>Lucien:</b>\n\n<i>Bienvenido al sanctum del círculo exclusivo.</i>"
        ]
        greeting = random.choice(greetings)

        if is_configured:
            body = (
                f"<i>Puedo ver que <b>{channel_name}</b> está activo.</i>\n\n"
                f"<i>Miembros del círculo: <b>{subscriber_count}</b></i>\n\n"
                "<i>¿Qué aspecto del acceso exclusivo requiere su atención?</i>"
            )
            keyboard = self._vip_configured_keyboard()
        else:
            body = (
                "<i>El círculo exclusivo aún no ha sido establecido.</i>\n\n"
                "<i>Diana prefiere que configuremos el canal antes de emitir invitaciones.</i>\n\n"
                "<i>¿Le gustaría comenzar con la calibración?</i>"
            )
            keyboard = self._vip_unconfigured_keyboard()

        text = self._compose(greeting, body)
        return (text, keyboard)

    def token_generated(
        self,
        plan_name: str,
        duration_days: int,
        price: float,
        currency: str,
        token: str,
        deep_link: str,
        expiry_date: "datetime"
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Token generation success message with deep link.

        Args:
            plan_name: Name of the subscription plan
            duration_days: Duration in days
            price: Plan price
            currency: Currency symbol (e.g., "$", "€")
            token: Generated token value
            deep_link: Telegram deep link (t.me/bot?start=TOKEN)
            expiry_date: Token expiry datetime

        Returns:
            Tuple of (text, keyboard) for complete UI

        Voice Rationale:
            Success = "excelente elección" (excellent choice)
            Token = "invitación" (invitation, not technical)
            Deep link = "pase de acceso" (access pass)
            Diana validates the action

        Examples:
            >>> msg = AdminVIPMessages()
            >>> text, kb = msg.token_generated("Premium", 30, 9.99, "$", "ABC", "t.me/bot?start=ABC", datetime.now())
            >>> "invitación" in text.lower()
            True
            >>> "excelente" in text.lower()
            True
        """
        price_str = format_currency(price, symbol=currency)
        expiry_str = format_datetime(expiry_date, include_time=False)

        text = self._compose(
            "🎩 <b>Lucien:</b>",
            f"<i>Excelente elección. La invitación ha sido emitida para el plan "
            f"<b>{plan_name}</b>...</i>\n\n"
            f"<b>Plan:</b> {plan_name}\n"
            f"<b>Duración:</b> {duration_days} días\n"
            f"<b>Inversión:</b> {price_str}\n\n"
            f"<b>Invitación:</b> <code>{token}</code>\n\n"
            f"<b>Pase de Acceso:</b>\n<code>{deep_link}</code>\n\n"
            f"<b>Válido hasta:</b> {expiry_str}\n\n"
            f"<i>━━━━━━━━━━━━━━━━━━━━</i>\n"
            f"<i>Diana aprobará su discernimiento...</i>\n\n"
            f"<i>El recipiente solo necesita hacer click en el pase.</i>"
        )

        keyboard = create_inline_keyboard([
            [{"text": "🔗 Copiar Pase", "url": deep_link}],
            [{"text": "🎟️ Emitir Otra Invitación", "callback_data": "vip:generate_token"}],
            [{"text": "🔙 Volver", "callback_data": "admin:vip"}]
        ])

        return (text, keyboard)

    def setup_channel_prompt(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Prompt for admin to forward VIP channel message.

        Voice Rationale:
            Setup = "calibración" (calibration, implies precision)
            Instructions are clear but maintain voice
        """
        text = self._compose(
            "🎩 <b>Lucien:</b>",
            "<i>Para calibrar el círculo exclusivo, necesito que...</i>\n\n"
            "<i>1️⃣ Vaya al canal VIP</i>\n"
            "<i>2️⃣ Reenvíe cualquier mensaje del canal a este chat</i>\n"
            "<i>3️⃣ Yo extraeré la identificación automáticamente</i>\n\n"
            "<i>⚠️ <b>Importante:</b></i>\n"
            "<i>Debo ser administrador del canal</i>\n"
            "<i>Debo tener permiso para invitar usuarios</i>\n\n"
            "<i>👉 Reenvíe un mensaje del canal cuando esté listo...</i>"
        )

        keyboard = create_inline_keyboard([
            [{"text": "❌ Cancelar", "callback_data": "admin:vip"}]
        ])

        return (text, keyboard)

    def channel_configured_success(
        self,
        channel_name: str,
        channel_id: str
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Success message after VIP channel is configured.

        Voice Rationale:
            Success = "como se esperaba" (as expected)
            Celebration mentions Diana's approval
        """
        text = self._compose(
            "🎩 <b>Lucien:</b>",
            f"<i>Excelente. El círculo exclusivo ha sido calibrado "
            f"como se esperaba.</i>\n\n"
            f"<b>Canal:</b> {channel_name}\n"
            f"<b>Identificación:</b> <code>{channel_id}</code>\n\n"
            f"<i>Diana aprobará este progreso...</i>\n\n"
            "<i>Ya puede emitir invitaciones para nuevos miembros.</i>"
        )

        keyboard = create_inline_keyboard([
            [{"text": "🎟️ Emitir Invitación", "callback_data": "vip:generate_token"}],
            [{"text": "🔙 Volver", "callback_data": "admin:vip"}]
        ])

        return (text, keyboard)

    def select_plan_for_token(
        self,
        plans: list[dict]  # Each dict: {"name": str, "duration_days": int, "price": float, "currency": str}
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Plan selection menu for token generation.

        Voice Rationale:
            Selection = "elegir" (choose, not "select")
            Plans = "planes de suscripción" (subscription plans)
        """
        # Build plan list
        plans_text = ""
        for plan in plans:
            price_str = format_currency(plan["price"], symbol=plan["currency"])
            plans_text += f"• <b>{plan['name']}</b>: {plan['duration_days']} días • {price_str}\n"

        text = self._compose(
            "🎩 <b>Lucien:</b>",
            "<i>¿Qué plan de suscripción desea para la invitación?</i>\n\n" + plans_text
        )

        # Build keyboard with plan buttons
        buttons = []
        for plan in plans:
            price_str = format_currency(plan["price"], symbol=plan["currency"])
            buttons.append([{
                "text": f"{plan['name']} - {price_str}",
                "callback_data": f"vip:generate:plan:{plan['id']}"
            }])

        buttons.append([{"text": "🔙 Volver", "callback_data": "admin:vip"}])

        keyboard = create_inline_keyboard(buttons)
        return (text, keyboard)

    # ===== PRIVATE KEYBOARD FACTORIES =====

    def _vip_configured_keyboard(self) -> InlineKeyboardMarkup:
        """Keyboard when VIP channel is configured."""
        return create_inline_keyboard([
            [{"text": "🎟️ Emitir Invitación", "callback_data": "vip:generate_token"}],
            [
                {"text": "👥 Miembros", "callback_data": "vip:list_subscribers"},
                {"text": "📊 Estadísticas", "callback_data": "admin:stats:vip"}
            ],
            [{"text": "📤 Enviar Publicación", "callback_data": "vip:broadcast"}],
            [{"text": "⚙️ Configuración", "callback_data": "vip:config"}],
            [{"text": "🔙 Volver", "callback_data": "admin:main"}]
        ])

    def _vip_unconfigured_keyboard(self) -> InlineKeyboardMarkup:
        """Keyboard when VIP channel is NOT configured."""
        return create_inline_keyboard([
            [{"text": "⚙️ Calibrar Canal VIP", "callback_data": "vip:setup"}],
            [{"text": "🔙 Volver", "callback_data": "admin:main"}]
        ])
```

### Handler Integration Example

```python
# bot/handlers/admin/vip.py (MIGRATED)
from aiogram import F
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.main import admin_router
from bot.services.container import ServiceContainer
from bot.states.admin import ChannelSetupStates

@admin_router.callback_query(F.data == "admin:vip")
async def callback_vip_menu(callback: CallbackQuery, session: AsyncSession):
    """
    Muestra el submenú de gestión VIP.

    MIGRATED: Now uses AdminVIPMessages provider for all text/keyboards.
    """
    logger.debug(f"📺 Usuario {callback.from_user.id} abrió menú VIP")

    container = ServiceContainer(session, callback.bot)

    # Get state data
    is_configured = await container.channel.is_vip_channel_configured()

    if is_configured:
        vip_channel_id = await container.channel.get_vip_channel_id()
        channel_info = await container.channel.get_channel_info(vip_channel_id)
        channel_name = channel_info.title if channel_info else "Canal VIP"
        subscriber_count = await container.subscription.get_vip_subscriber_count()
    else:
        channel_name = "Canal VIP"
        subscriber_count = 0

    # GET TEXT AND KEYBOARD FROM MESSAGE PROVIDER
    text, keyboard = await container.message.admin.vip.vip_menu(
        is_configured=is_configured,
        channel_name=channel_name,
        subscriber_count=subscriber_count
    )

    # Send message (no formatting logic in handler!)
    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"Error editando mensaje VIP: {e}")

    await callback.answer()


@admin_router.callback_query(F.data == "vip:setup")
async def callback_vip_setup(callback: CallbackQuery, state: FSMContext):
    """
    Inicia el proceso de configuración del canal VIP.

    MIGRATED: Uses AdminVIPMessages.setup_channel_prompt()
    """
    logger.info(f"⚙️ Usuario {callback.from_user.id} iniciando setup VIP")

    await state.set_state(ChannelSetupStates.waiting_for_vip_channel)

    # GET TEXT AND KEYBOARD FROM MESSAGE PROVIDER
    text, keyboard = container.message.admin.vip.setup_channel_prompt()

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"Error editando mensaje setup VIP: {e}")

    await callback.answer()
```

### LucienVoiceService Integration Example

```python
# bot/services/message/__init__.py (UPDATED)
from .base import BaseMessageProvider
from .common import CommonMessages
from .admin_main import AdminMainMessages
from .admin_vip import AdminVIPMessages
from .admin_free import AdminFreeMessages

class LucienVoiceService:
    """
    Main message service providing access to all message providers.

    Architecture:
        ServiceContainer
            └─ LucienVoiceService
                ├─ common: CommonMessages
                ├─ admin: AdminMessages (namespace)
                │   ├─ main: AdminMainMessages
                │   ├─ vip: AdminVIPMessages
                │   └─ free: AdminFreeMessages
                └─ user: UserMessages (Phase 3)

    Usage:
        container = ServiceContainer(session, bot)

        # Admin messages
        text, kb = container.message.admin.vip.vip_menu(is_configured=True)
        text, kb = container.message.admin.main.admin_menu_greeting(is_configured=True)

        # Common messages
        text = container.message.common.error('al generar token')
    """

    def __init__(self):
        self._common = None
        self._admin = None

    @property
    def common(self) -> CommonMessages:
        """Common messages provider (errors, success, not_found)."""
        if self._common is None:
            self._common = CommonMessages()
        return self._common

    @property
    def admin(self) -> "AdminMessages":
        """Admin messages namespace (main, vip, free)."""
        if self._admin is None:
            self._admin = AdminMessages()
        return self._admin


class AdminMessages:
    """
    Admin messages namespace for organization.

    Provides access to AdminMainMessages, AdminVIPMessages, AdminFreeMessages.

    Usage:
        msg = container.message.admin
        text, kb = msg.vip.vip_menu(is_configured=True)
        text, kb = msg.main.admin_menu_greeting(is_configured=True)
    """

    def __init__(self):
        self._main = None
        self._vip = None
        self._free = None

    @property
    def main(self) -> AdminMainMessages:
        """Main admin menu messages."""
        if self._main is None:
            from .admin_main import AdminMainMessages
            self._main = AdminMainMessages()
        return self._main

    @property
    def vip(self) -> AdminVIPMessages:
        """VIP admin messages."""
        if self._vip is None:
            from .admin_vip import AdminVIPMessages
            self._vip = AdminVIPMessages()
        return self._vip

    @property
    def free(self) -> AdminFreeMessages:
        """Free admin messages."""
        if self._free is None:
            from .admin_free import AdminFreeMessages
            self._free = AdminFreeMessages()
        return self._free
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded strings in handlers | Centralized message providers | This phase | Single source of truth, voice consistency |
| Separate keyboard factories | Built-in keyboard factories | This phase | No synchronization bugs |
| Static messages | Randomized variations (2 per key) | This phase | Bot feels alive, less repetitive |
| Handler formatting logic | Provider encapsulates all UI | This phase | Handlers become thin orchestration |

**Deprecated/outdated:**
- Hardcoded f-strings in handlers: Violates single responsibility, voice rules leak into handlers
- Separate keyboard files for admin: Creates synchronization burden, text/keyboard tightly coupled
- Template engines (Jinja2): Overkill for bot messages, adds 5MB+ dependency

## Open Questions

### Question 1: Callback Data Format Consistency

**What we know:** Current codebase uses colon-separated format (`admin:vip`, `vip:setup`, `vip:generate_token`). New handlers must follow this pattern.

**What's unclear:** Should we define constants or helper functions to prevent typos in callback strings?

**Recommendation:** For Phase 2, continue using string literals (matches existing pattern). If callback typos become a problem in Phase 3, introduce callback constants. Current approach is pragmatic and follows KISS principle.

### Question 2: Migration Strategy (Incremental vs Big Bang)

**What we know:** Admin handlers must be migrated to use message providers. Can do file-by-file (incremental) or all at once (big bang).

**What's unclear:** Which approach minimizes risk and testing burden?

**Recommendation:** Incremental migration by file:
1. Build AdminVIPMessages provider
2. Migrate vip.py handlers
3. Test vip flow thoroughly
4. Repeat for free.py, then main.py
This isolates risks and makes debugging easier. Big bang migration increases risk of breaking all admin flows simultaneously.

### Question 3: Variation Storage (Lists vs Helper Methods)

**What we know:** Need to store 2 variations per key message. Can use inline lists `["var1", "var2"]` or helper methods `_get_greeting_variations()`.

**What's unclear:** Which approach is more maintainable?

**Recommendation:** Inline lists for 2 variations:
```python
greetings = ["Variation 1", "Variation 2"]
greeting = random.choice(greetings)
```
Helper methods only if variations exceed 3 items or need complex logic. Inline lists are simpler and sufficient for admin messages.

## Sources

### Primary (HIGH confidence)

- **bot/handlers/admin/*.py** (10 files) — Current hardcoded message patterns, existing keyboard structures, callback data format
- **bot/services/message/base.py** — BaseMessageProvider with `_compose()` and `_choose_variant()` utilities
- **bot/services/message/common.py** — CommonMessages provider demonstrating voice consistency patterns
- **bot/utils/formatters.py** (19 functions) — Date/currency/HTML formatting utilities to reuse
- **bot/utils/keyboards.py** — `create_inline_keyboard()` helper for consistent keyboard construction
- **docs/guia-estilo.md** — Lucien's voice rules, emoji usage, terminology mappings

### Secondary (MEDIUM confidence)

- **.planning/phases/01-service-foundation/01-RESEARCH.md** — Foundation architecture, stateless design rationale
- **.planning/phases/02-template-organization-admin-migration/02-CONTEXT.md** — Phase decisions, Claude's discretion areas
- **tests/test_message_service.py** — Testing patterns for message providers

### Tertiary (LOW confidence)

- **Phase 1 research** — Standard stack recommendations (stdlib-only, f-strings, dataclass)
- **General bot framework patterns** — Message service architecture from industry best practices

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All stdlib or existing, no new dependencies
- Architecture: HIGH - Patterns proven in Phase 1, matches existing codebase structure
- Pitfalls: HIGH - All pitfalls sourced from real-world refactoring patterns and existing codebase analysis

**Research date:** 2026-01-23
**Valid until:** 2026-03-23 (60 days - stable domain, architecture patterns unlikely to change)

---

*Research completed: 2026-01-23*
*Ready for planning: YES*
*Synthesized by: GSD Phase Researcher*
