# Architecture Research: Message Service Integration

**Domain:** Centralized Message Templating for Telegram Bot
**Researched:** 2026-01-23
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     HANDLER LAYER                            │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ /admin  │  │  /start │  │VIP Flow │  │Free Flow│        │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘        │
│       │            │            │            │              │
│       └────────────┴────────────┴────────────┘              │
│                         ↓                                    │
├─────────────────────────────────────────────────────────────┤
│                    SERVICE CONTAINER (DI)                    │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ Message    │  │Subscription│  │  Channel   │            │
│  │ Service    │  │  Service   │  │  Service   │  ...       │
│  └────┬───────┘  └────┬───────┘  └────┬───────┘            │
│       │               │               │                     │
│       └───────────────┴───────────────┘                     │
│                         ↓                                    │
├─────────────────────────────────────────────────────────────┤
│                     UTILS LAYER                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Keyboards  │  Formatters  │  Validators  │         │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│                     DATA ACCESS LAYER                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │  Models  │  │  Engine  │  │ Session  │                   │
│  └──────────┘  └──────────┘  └──────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **MessageService** | Provides localized message text with dynamic data injection. Owns all message templates organized by navigation flow. | Service class with methods returning formatted strings. Integrates with i18n middleware for multi-language support. |
| **KeyboardFactory** | Creates InlineKeyboardMarkup objects. May integrate with MessageService for consistent message+keyboard pairing. | Factory functions or class methods. Currently in utils/keyboards.py. |
| **Formatters** | Format data types (dates, currency, numbers) for display. Reusable across messages. | Pure functions in utils/formatters.py. No business logic. |
| **Handlers** | Orchestrate user interactions. Delegate message composition to MessageService, keyboard creation to factory, and business logic to services. | Async functions decorated with router filters. Thin layer - mostly coordination. |
| **ServiceContainer** | Manages service lifecycle with lazy loading and dependency injection. | Property-based lazy loading. Injects session and bot into all services. |

## Recommended Project Structure

### Current Structure (Before Message Service)

```
bot/
├── handlers/
│   ├── admin/           # Hardcoded messages inline
│   │   ├── main.py      # "📺 Gestión Canal VIP\n\n✅ Canal configurado..."
│   │   ├── vip.py       # "⚠️ Canal VIP no configurado..."
│   │   └── free.py      # Messages scattered in handlers
│   └── user/
│       ├── start.py     # "👋 Hola <b>{user_name}</b>!..."
│       └── vip_flow.py  # More hardcoded messages
├── services/
│   ├── container.py     # DI container (EXISTING)
│   ├── subscription.py  # VIP/Free logic
│   └── channel.py       # Channel management
├── utils/
│   ├── keyboards.py     # Keyboard factory (EXISTING)
│   └── formatters.py    # Data formatters (EXISTING)
```

### Proposed Structure (With Message Service)

```
bot/
├── handlers/
│   ├── admin/           # Delegates to MessageService
│   │   ├── main.py      # await msg.admin.main_menu(is_configured=True)
│   │   ├── vip.py       # await msg.admin.vip.channel_configured(channel_name, id)
│   │   └── free.py      # await msg.admin.free.not_configured()
│   └── user/
│       ├── start.py     # await msg.user.welcome(user_name, role)
│       └── vip_flow.py  # await msg.user.vip.token_activated(days)
├── services/
│   ├── container.py     # Adds .message property
│   ├── message.py       # NEW: MessageService (core)
│   ├── subscription.py
│   └── channel.py
├── messages/            # NEW: Template organization
│   ├── __init__.py      # Exports
│   ├── base.py          # BaseMessageProvider abstract class
│   ├── admin/           # Admin flow messages
│   │   ├── __init__.py
│   │   ├── main.py      # MainMenuMessages class
│   │   ├── vip.py       # VIPMessages class
│   │   └── free.py      # FreeMessages class
│   └── user/            # User flow messages
│       ├── __init__.py
│       ├── common.py    # WelcomeMessages class
│       ├── vip.py       # VIPFlowMessages class
│       └── free.py      # FreeFlowMessages class
├── utils/
│   ├── keyboards.py     # May integrate with message service
│   └── formatters.py    # Used BY message providers
```

### Structure Rationale

**Why `bot/messages/` directory:**
- **Separation of concerns:** Messages are content, not business logic. Separate folder clarifies this boundary.
- **Navigation-based organization:** Mirrors handler structure (admin/, user/). Developers navigate intuitively.
- **Discoverability:** All templates in one place. Easy to find and modify without hunting through handlers.

**Why message providers (not raw templates):**
- **Type safety:** Methods with type hints. IDEs autocomplete message signatures.
- **Dynamic composition:** Methods can accept parameters, format data, inject keyboard references.
- **Testability:** Easy to unit test message generation without running handlers.

**Why keep keyboards separate (initially):**
- **Gradual migration:** Keyboards already work. Don't force refactor until needed.
- **Cross-cutting concern:** Keyboards may be reused across multiple messages. Utils layer appropriate.
- **Future integration:** Can later add `with_keyboard()` pattern if keyboard+message coupling emerges.

## Architectural Patterns

### Pattern 1: Service-Based Message Providers

**What:** Message templates organized into provider classes accessible via MessageService. Each provider corresponds to a navigation flow or feature area.

**When to use:** When migrating from hardcoded messages to centralized templates without rewriting entire application.

**Trade-offs:**
- **Pro:** Type-safe, IDE-friendly, gradual migration path
- **Pro:** Encapsulates message logic and formatting
- **Con:** Slightly more boilerplate than raw string templates
- **Con:** Not true i18n (but can evolve into it)

**Example:**
```python
# bot/messages/admin/vip.py
from bot.messages.base import BaseMessageProvider
from bot.utils.formatters import format_datetime

class VIPMessages(BaseMessageProvider):
    """Message templates for VIP management flow."""

    def channel_configured(self, channel_name: str, channel_id: str) -> str:
        """Message shown when VIP channel is configured."""
        return (
            f"📺 <b>Gestión Canal VIP</b>\n\n"
            f"✅ Canal configurado: <b>{channel_name}</b>\n"
            f"ID: <code>{channel_id}</code>\n\n"
            f"Selecciona una opción:"
        )

    def channel_not_configured(self) -> str:
        """Message shown when VIP channel is not configured."""
        return (
            "📺 <b>Gestión Canal VIP</b>\n\n"
            "⚠️ Canal VIP no configurado\n\n"
            "Configura el canal para comenzar a generar tokens."
        )

    def token_generated(self, token: str, deep_link: str, plan_name: str, duration_hours: int) -> str:
        """Message shown after generating VIP token."""
        return (
            f"🎟️ <b>Token VIP Generado</b>\n\n"
            f"Plan: <b>{plan_name}</b>\n"
            f"Duración: {duration_hours}h\n\n"
            f"Token: <code>{token}</code>\n"
            f"Deep Link: {deep_link}\n\n"
            f"Envía el deep link al usuario. Al hacer click, su suscripción se activará automáticamente."
        )

# bot/services/message.py
class MessageService:
    """Centralized message service with lazy-loaded providers."""

    def __init__(self, session: AsyncSession, bot: Bot):
        self._session = session
        self._bot = bot
        self._admin_vip = None
        self._admin_free = None
        self._user_common = None
        # ... etc

    @property
    def admin(self):
        """Namespace for admin messages."""
        if self._admin_namespace is None:
            self._admin_namespace = AdminNamespace(self)
        return self._admin_namespace

class AdminNamespace:
    """Namespace for admin message providers."""

    def __init__(self, message_service):
        self._msg_service = message_service
        self._vip = None
        self._free = None

    @property
    def vip(self):
        if self._vip is None:
            from bot.messages.admin.vip import VIPMessages
            self._vip = VIPMessages(self._msg_service._session, self._msg_service._bot)
        return self._vip

    @property
    def free(self):
        if self._free is None:
            from bot.messages.admin.free import FreeMessages
            self._free = FreeMessages(self._msg_service._session, self._msg_service._bot)
        return self._free

# Usage in handler:
async def callback_vip_menu(callback: CallbackQuery, session: AsyncSession):
    container = ServiceContainer(session, callback.bot)
    is_configured = await container.channel.is_vip_channel_configured()

    if is_configured:
        vip_channel_id = await container.channel.get_vip_channel_id()
        channel_info = await container.channel.get_channel_info(vip_channel_id)
        channel_name = channel_info.title if channel_info else "Canal VIP"

        text = container.message.admin.vip.channel_configured(channel_name, vip_channel_id)
    else:
        text = container.message.admin.vip.channel_not_configured()

    await callback.message.edit_text(text, parse_mode="HTML", ...)
```

### Pattern 2: Formatter Integration

**What:** Message providers use formatter utilities for consistent data display. Formatters remain in utils/ but are called by message providers.

**When to use:** When messages need to display dates, currency, percentages, or other formatted data.

**Trade-offs:**
- **Pro:** Consistent formatting across all messages
- **Pro:** Single source of truth for format rules
- **Pro:** Formatters testable independently
- **Con:** Message providers must know which formatter to use

**Example:**
```python
from bot.utils.formatters import format_currency, format_datetime

class VIPMessages(BaseMessageProvider):
    def subscription_details(self, subscriber: VIPSubscriber, plan: SubscriptionPlan) -> str:
        expires_at = format_datetime(subscriber.expiry_date)
        price = format_currency(plan.price_usd, "USD")

        return (
            f"👤 <b>Suscripción VIP</b>\n\n"
            f"Plan: {plan.name}\n"
            f"Precio: {price}\n"
            f"Expira: {expires_at}\n"
        )
```

### Pattern 3: Lazy-Loaded Namespaces

**What:** MessageService uses property-based lazy loading for message provider namespaces, mirroring the existing ServiceContainer pattern.

**When to use:** When you want memory efficiency and fast bot startup. Only load message providers that are actually used.

**Trade-offs:**
- **Pro:** Memory efficient (Termux environment)
- **Pro:** Fast startup (no upfront loading)
- **Pro:** Consistent with existing architecture
- **Con:** Slightly more complex implementation
- **Con:** First access has small overhead (negligible)

**Example:** See Pattern 1 above (AdminNamespace with lazy loading).

### Pattern 4: Message+Keyboard Coupling (Future)

**What:** Some messages always appear with specific keyboards. Message providers can optionally return (message, keyboard) tuples.

**When to use:** When certain messages ALWAYS have the same keyboard (e.g., main menu). Reduces handler boilerplate.

**Trade-offs:**
- **Pro:** Reduces duplication (message and keyboard always together)
- **Pro:** Enforces consistency (can't send message without keyboard)
- **Con:** Less flexibility (what if keyboard needs dynamic parameters?)
- **Con:** More complex return types

**Example:**
```python
# Future enhancement (not MVP):
class MainMenuMessages(BaseMessageProvider):
    def main_menu(self, is_configured: bool) -> MessageWithKeyboard:
        """Returns message AND keyboard together."""
        text = "..."
        keyboard = admin_main_menu_keyboard(is_configured)
        return MessageWithKeyboard(text=text, keyboard=keyboard, parse_mode="HTML")

# Handler usage (future):
async def cmd_admin(message: Message, session: AsyncSession):
    container = ServiceContainer(session, message.bot)
    msg_kb = container.message.admin.main.main_menu(is_configured=True)
    await message.answer(**msg_kb.as_kwargs())
```

**Recommendation:** Start with Pattern 1-3 (separate messages and keyboards). Add Pattern 4 only if duplication becomes pain point.

## Data Flow

### Request Flow (Handler → MessageService → Response)

```
[User Action: /admin]
    ↓
[Handler: cmd_admin]
    ↓
[ServiceContainer: container.message.admin.main]
    ↓ (lazy loads)
[MessageProvider: MainMenuMessages.main_menu(is_configured)]
    ↓ (uses)
[Formatters: format_datetime, etc]
    ↓ (returns)
[Formatted Message String: "📺 <b>Panel Admin</b>..."]
    ↓
[Handler: message.answer(text, keyboard, parse_mode="HTML")]
    ↓
[Response: Telegram sends message to user]
```

### Message Composition Flow

```
Handler needs message
    ↓
Accesses container.message.[namespace].[provider].[method]()
    ↓
Method receives parameters (user_name, channel_id, etc)
    ↓
Method formats using utils/formatters if needed
    ↓
Method composes HTML string with <b>, <code> tags
    ↓
Returns string to handler
    ↓
Handler pairs with keyboard from utils/keyboards.py
    ↓
Handler sends to Telegram with parse_mode="HTML"
```

### Integration with i18n (Future Enhancement)

```
[MessageProvider method called]
    ↓
Accesses self._i18n context (if available)
    ↓
Uses gettext/_() for translatable strings
    ↓
Injects dynamic data into translated template
    ↓
Returns localized message
```

**Current:** All messages in Spanish hardcoded.
**Future:** When i18n needed, message providers can integrate aiogram's built-in i18n middleware.

## Integration Points

### ServiceContainer Integration

**How to integrate:**
1. Add `_message_service = None` to ServiceContainer.__init__
2. Add `@property def message(self):` with lazy loading
3. MessageService constructor takes `(session, bot)` like other services
4. Handlers access via `container.message.admin.vip.method()`

**Why this way:**
- Consistent with existing service pattern
- Lazy loading maintains Termux memory efficiency
- Natural API for handlers (namespace mirrors handler structure)

### Keyboard Factory Integration

**Current state:** Keyboards in utils/keyboards.py with factory functions.

**Integration approach (MVP):**
1. **Keep keyboards separate** - Handlers call keyboard factory and message service independently
2. Message service focuses ONLY on text
3. Handler coordinates: `text = container.message...` and `keyboard = vip_menu_keyboard(...)`

**Future enhancement:**
- Add `with_keyboard()` helper method to message providers if pattern emerges
- Or migrate keyboard factory INTO message service if tight coupling needed

**Example (MVP approach):**
```python
# Handler (current approach, MVP):
text = container.message.admin.vip.channel_configured(channel_name, channel_id)
keyboard = vip_menu_keyboard(is_configured=True)
await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

# Future enhancement IF needed:
msg_kb = container.message.admin.vip.channel_configured_with_keyboard(channel_name, channel_id, is_configured=True)
await callback.message.edit_text(**msg_kb.as_kwargs())
```

### Formatter Integration

**Current state:** utils/formatters.py has 19 formatting functions (dates, currency, etc).

**Integration approach:**
1. Message providers IMPORT formatters at top of file
2. Use formatters in message methods when displaying data
3. No changes to formatters themselves

**Example:**
```python
from bot.utils.formatters import format_currency, format_datetime, format_relative_time

class VIPMessages(BaseMessageProvider):
    def token_details(self, token: InvitationToken, plan: SubscriptionPlan) -> str:
        created = format_datetime(token.created_at)
        expires = format_relative_time(token.expires_at)
        price = format_currency(plan.price_usd, "USD")

        return f"Token: {token.token}\nCreado: {created}\nExpira: {expires}\nPrecio: {price}"
```

### Database Access (Rare)

**Question:** Should message providers access database?

**Answer:** Generally NO, but exceptions exist.

**Guideline:**
- **Prefer:** Handlers fetch data, pass to message provider as parameters
- **Exception:** Message provider may query simple config/lookup data if it avoids parameter explosion

**Example (preferred):**
```python
# Handler fetches data:
subscriber = await container.subscription.get_vip_subscriber(user_id)
plan = await container.pricing.get_plan(subscriber.plan_id)

# Message provider receives data:
text = container.message.admin.vip.subscriber_details(subscriber, plan)
```

**Example (exception allowed):**
```python
# Message provider internally queries emoji config:
class BaseMessageProvider:
    def __init__(self, session, bot):
        self._session = session
        self._bot = bot

    async def _get_status_emoji(self, status: str) -> str:
        """Internal helper can query DB for simple lookups."""
        emoji_config = await self._session.execute(...)
        return emoji_config.get(status, "❓")
```

## Build Order and Dependencies

### Phase 1: Foundation (No Dependencies)

**Goal:** Create infrastructure without disrupting existing handlers.

1. **Create base classes:**
   - `bot/messages/base.py` - BaseMessageProvider abstract class
   - `bot/services/message.py` - MessageService shell with namespace structure

2. **Integrate with ServiceContainer:**
   - Add `.message` property to ServiceContainer
   - Test that lazy loading works

**Deliverable:** Infrastructure ready, no handlers changed yet.

### Phase 2: Admin Messages (Depends on Phase 1)

**Goal:** Migrate admin handler messages to MessageService.

1. **Create admin message providers:**
   - `bot/messages/admin/main.py` - MainMenuMessages
   - `bot/messages/admin/vip.py` - VIPMessages
   - `bot/messages/admin/free.py` - FreeMessages

2. **Refactor admin handlers:**
   - Replace hardcoded messages with `container.message.admin.*` calls
   - One handler at a time (gradual migration)

**Deliverable:** All admin handlers use MessageService.

### Phase 3: User Messages (Depends on Phase 1)

**Goal:** Migrate user handler messages to MessageService.

1. **Create user message providers:**
   - `bot/messages/user/common.py` - WelcomeMessages
   - `bot/messages/user/vip.py` - VIPFlowMessages
   - `bot/messages/user/free.py` - FreeFlowMessages

2. **Refactor user handlers:**
   - Replace hardcoded messages with `container.message.user.*` calls
   - Handle deep link activation messages

**Deliverable:** All user handlers use MessageService.

### Phase 4: Edge Cases and Polish (Depends on Phase 2, 3)

**Goal:** Handle remaining messages and improve API.

1. **Migrate remaining handlers:**
   - Broadcast messages
   - Dashboard messages
   - Error messages

2. **API improvements:**
   - Add helper methods for common patterns
   - Improve type hints and docstrings

**Deliverable:** 100% messages centralized.

### Dependency Graph

```
Phase 1 (Foundation)
    ↓
    ├─→ Phase 2 (Admin Messages)
    │       ↓
    └─→ Phase 3 (User Messages)
            ↓
        Phase 4 (Edge Cases)
```

**Critical path:** Foundation must be complete before any migration.

**Parallel work:** Phase 2 and 3 can be done simultaneously (different handler namespaces).

## Template Organization Strategy

### Question: How to organize templates internally?

**Options Evaluated:**
1. **By navigation flow** (admin/, user/) - Mirrors handler structure
2. **By feature** (vip/, free/, broadcast/) - Mirrors service structure
3. **By message type** (menus/, confirmations/, errors/) - Mirrors UI patterns

**Recommendation:** **By navigation flow** (Option 1)

**Rationale:**
- **Developer mental model:** Handlers are organized by navigation. Message providers mirror this. "Where's the VIP menu message?" → "Same place as VIP menu handler" → `bot/messages/admin/vip.py`
- **Discoverability:** When editing a handler, the corresponding message provider is in the parallel directory structure.
- **Refactoring simplicity:** Migrate handler by handler, not scattered across feature boundaries.
- **Existing pattern:** Current architecture already uses handler-based organization. Don't fight it.

**Alternative considered:** Feature-based organization might be better IF services generate messages (e.g., SubscriptionService generates confirmation messages). But in this architecture, handlers compose messages, so navigation flow wins.

### Internal Class Organization (Within Provider File)

**Strategy:** Group methods by user journey within that flow.

**Example structure for VIPMessages:**
```python
class VIPMessages(BaseMessageProvider):
    # Menu messages:
    def channel_configured(self, ...) -> str: ...
    def channel_not_configured(self) -> str: ...

    # Setup flow:
    def setup_prompt(self) -> str: ...
    def setup_success(self, channel_name) -> str: ...
    def setup_error(self, error_msg) -> str: ...

    # Token generation:
    def token_generated(self, token, deep_link) -> str: ...
    def select_plan_prompt(self, plans: List) -> str: ...

    # Subscriber management:
    def subscriber_list_header(self, total) -> str: ...
    def subscriber_details(self, subscriber) -> str: ...
```

**Benefits:**
- Methods grouped by journey phase
- Docstrings explain context ("shown when...", "sent after...")
- Easy to find message for specific handler state

## Anti-Patterns

### Anti-Pattern 1: Message Providers with Business Logic

**What people do:** Put business logic (validation, calculations, database writes) inside message providers.

**Why it's wrong:**
- Violates separation of concerns (messages are presentation, not logic)
- Hard to test business logic (coupled to message generation)
- Creates circular dependencies (messages depend on services, services depend on messages)

**Do this instead:**
- Handlers orchestrate: call services for logic, pass results to message providers
- Message providers are pure functions: data in, string out
- Complex formatting (like relative time) is OK, but decision-making is NOT

**Example (WRONG):**
```python
class VIPMessages(BaseMessageProvider):
    async def subscriber_status(self, user_id: int) -> str:
        # ❌ BAD: Querying database in message provider
        subscriber = await self._session.execute(...)
        # ❌ BAD: Business logic (calculating expiration)
        if subscriber.expiry_date < datetime.now():
            return "Expired"
        return "Active"
```

**Example (CORRECT):**
```python
# Handler:
subscriber = await container.subscription.get_vip_subscriber(user_id)
is_active = await container.subscription.is_vip_active(user_id)
text = container.message.admin.vip.subscriber_status(subscriber, is_active)

# Message provider:
def subscriber_status(self, subscriber: VIPSubscriber, is_active: bool) -> str:
    # ✅ GOOD: Just formatting, no logic
    status = "Activo" if is_active else "Expirado"
    expires = format_datetime(subscriber.expiry_date)
    return f"Estado: {status}\nExpira: {expires}"
```

### Anti-Pattern 2: Passing Raw Database Models

**What people do:** Pass entire database models (VIPSubscriber, InvitationToken) to message methods.

**Why it's wrong:**
- Couples messages to database schema (schema change breaks messages)
- Tempts message provider to access relationships (subscriber.plan.name → DB query)
- Hard to test (must create full model instances)

**Do this instead:**
- Pass primitive types or simple dataclasses
- Handler extracts needed fields from models
- Message provider receives exactly what it needs

**Example (WRONG):**
```python
# ❌ BAD: Passing full model
text = container.message.admin.vip.subscriber_details(subscriber)

# Message provider:
def subscriber_details(self, subscriber: VIPSubscriber) -> str:
    # ❌ BAD: Coupled to model structure
    # ❌ BAD: What if relationship not loaded?
    plan_name = subscriber.plan.name
    ...
```

**Example (CORRECT):**
```python
# ✅ GOOD: Handler extracts needed data
plan = await container.pricing.get_plan(subscriber.plan_id)
text = container.message.admin.vip.subscriber_details(
    user_id=subscriber.user_id,
    plan_name=plan.name,
    expiry_date=subscriber.expiry_date,
    is_active=subscriber.status == "active"
)

# Message provider:
def subscriber_details(
    self,
    user_id: int,
    plan_name: str,
    expiry_date: datetime,
    is_active: bool
) -> str:
    # ✅ GOOD: Simple parameters, no coupling
    ...
```

**Exception:** It's OK to pass models if message provider ONLY accesses simple scalar fields (no relationships, no methods).

### Anti-Pattern 3: Keyboard Logic in Message Providers

**What people do:** Message providers construct InlineKeyboardMarkup inside message methods.

**Why it's wrong:**
- Mixes concerns (message text vs. keyboard structure)
- Duplicates keyboard factory logic
- Hard to change keyboard layout (scattered across message providers)

**Do this instead:**
- Keep keyboard factory in utils/keyboards.py (or move to MessageService later)
- Message providers return ONLY text
- Handler coordinates message + keyboard

**Example (WRONG):**
```python
def channel_configured_with_keyboard(self, channel_name: str) -> tuple[str, InlineKeyboardMarkup]:
    # ❌ BAD: Message provider building keyboard
    text = f"Canal: {channel_name}"
    keyboard = InlineKeyboardMarkup(...)
    return text, keyboard
```

**Example (CORRECT):**
```python
# Message provider:
def channel_configured(self, channel_name: str) -> str:
    # ✅ GOOD: Only text
    return f"Canal: {channel_name}"

# Handler:
text = container.message.admin.vip.channel_configured(channel_name)
keyboard = vip_menu_keyboard(is_configured=True)
await callback.message.edit_text(text, reply_markup=keyboard)
```

**Future enhancement:** If message+keyboard coupling is ALWAYS the same, add optional `with_keyboard()` pattern (Pattern 4 above). But start simple.

### Anti-Pattern 4: String Concatenation Hell

**What people do:** Build messages with many small string concatenations or format calls.

**Why it's wrong:**
- Hard to read (what does final message look like?)
- Error-prone (missing spaces, newlines)
- Hard to translate (i18n needs whole template, not fragments)

**Do this instead:**
- Use multi-line f-strings or textwrap.dedent
- Keep entire message template visible in one place
- Use named placeholders for clarity

**Example (WRONG):**
```python
def subscriber_details(self, name, plan, expires):
    # ❌ BAD: Concatenation hell
    text = "👤 " + name + "\n"
    text += "Plan: " + plan + "\n"
    text += "Expira: " + expires
    return text
```

**Example (CORRECT):**
```python
def subscriber_details(self, name: str, plan: str, expires: str) -> str:
    # ✅ GOOD: Full template visible
    return (
        f"👤 <b>{name}</b>\n\n"
        f"Plan: {plan}\n"
        f"Expira: {expires}\n"
    )
```

## Scalability Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **Current (single language, <10k users)** | Service-based providers with hardcoded Spanish messages. Lazy loading for memory efficiency. No caching needed. |
| **Multi-language (i18n needed)** | Integrate aiogram's i18n middleware. Message providers use gettext/_() for strings. Template structure stays same, just wrap strings. Load .po files in bot startup. |
| **10k+ active users** | Add Redis caching for frequently accessed messages if message generation becomes bottleneck (unlikely). Lazy loading already handles memory. Monitor message provider instantiation overhead. |
| **Complex personalization** | If messages need per-user customization beyond simple parameters, consider template engine (Jinja2). But ONLY if simple f-strings become unmaintainable. Premature optimization otherwise. |

### Scaling Priorities

1. **First bottleneck:** Database queries in handlers (already addressed by service layer). Message providers are pure functions, won't bottleneck.

2. **Second bottleneck:** If i18n needed, loading .po files is I/O. Solution: Load at startup, cache in memory. aiogram's i18n middleware handles this.

3. **Non-bottleneck:** Message generation itself is fast (string formatting). Don't optimize unless profiling shows problem.

## Sources

### Telegram Bot Architecture
- [Telegram Bot Design Patterns (GitHub)](https://github.com/lucaoflaif/telegram-bot-design-pattern) - Clean structure and middlewares
- [python-telegram-bot Architecture Wiki](https://github.com/python-telegram-bot/python-telegram-bot/wiki/Architecture) - Official architecture documentation
- [Scalable Telegram Bot Architecture (Medium)](https://medium.com/wearewaes/how-to-build-a-reliable-scalable-and-cost-effective-telegram-bot-58ae2d6684b1) - Serverless and event-driven patterns
- [Developer's Guide to Building Telegram Bots in 2025](https://stellaray777.medium.com/a-developers-guide-to-building-telegram-bots-in-2025-dbc34cd22337) - Modern best practices

### Message Service and Bot Framework Architecture
- [Azure Bot Service Architecture (2025)](https://moimhossain.com/2025/05/22/azure-bot-service-microsoft-teams-architecture-and-message-flow/) - Centralized message routing
- [Bot Framework Architecture (Microsoft)](https://learn.microsoft.com/en-us/azure/bot-service/bot-builder-basics?view=azure-bot-service-4.0) - Bot Connector Service patterns
- [Claudia Bot Builder - Telegram Custom Messages](https://github.com/claudiajs/claudia-bot-builder/blob/master/docs/TELEGRAM_CUSTOM_MESSAGES.md) - Template builders
- [Rocket.Chat Bots Architecture](https://developer.rocket.chat/docs/bots-architecture) - Message routing patterns

### Dependency Injection and Service Container
- [Dependency Injection in .NET (Microsoft)](https://learn.microsoft.com/en-us/dotnet/core/extensions/dependency-injection) - Official DI patterns
- [Martin Fowler - Inversion of Control Containers](https://martinfowler.com/articles/injection.html) - Foundational DI concepts
- [Symfony Service Container](https://symfony.com/doc/current/service_container.html) - Advanced service container patterns
- [Service Container Pattern in React/Rails (DEV)](https://dev.to/abdelrahmanallam/simplifying-dependency-injection-with-the-service-container-pattern-in-reactjs-and-ruby-on-rails-525m) - Cross-framework patterns

### i18n and Message Catalogs
- [aiogram i18n Documentation](https://docs.aiogram.dev/en/latest/utils/i18n.html) - Official aiogram translation utilities
- [aiogram/i18n GitHub](https://github.com/aiogram/i18n) - Translation middleware implementation
- [What is i18n? (2026 Edition - Locize)](https://www.locize.com/blog/what-is-i18n/) - Modern i18n trends
- [Rails I18n API Guide](https://guides.rubyonrails.org/i18n.html) - Message catalog patterns

### Keyboard and Template Patterns
- [grammY Inline Keyboards](https://grammy.dev/plugins/keyboard) - Built-in keyboard patterns
- [Telegram.Bot Reply Markup](https://telegrambots.github.io/book/2/reply-markup.html) - Keyboard integration
- [Telegram Bot Inline Keyboard with Dynamic Menus (n8n)](https://n8n.io/workflows/7664-telegram-bot-inline-keyboard-with-dynamic-menus-and-rating-system/) - Dynamic keyboard patterns

### Separation of Concerns and Clean Architecture
- [Separation of Concerns - Fundamental Principle (Medium)](https://medium.com/@shelvindatt02/separation-of-concerns-a-fundamental-principle-in-software-architecture-22dc61f60098) - Architectural principles
- [Go Clean Architecture (Level Up Coding)](https://levelup.gitconnected.com/go-clean-architecture-structuring-go-applications-with-clear-separation-of-concerns-70db67ce943c) - Separation patterns
- [Clean Architecture in Node.js APIs (DEV)](https://dev.to/crit3cal/clean-architecture-in-nodejs-apis-mastering-separation-of-concerns-5cha) - Service layer patterns

---
*Architecture research for: Centralized Message Service Integration*
*Researched: 2026-01-23*
