# Architecture Research: Menu System for Role-Based Bot Experience

**Domain:** Role-Based Menu System with Content Management
**Researched:** 2026-01-24
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     HANDLER LAYER                            │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ /start  │  │  /menu  │  │ Callback│  │ Admin   │        │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘        │
│       │            │            │            │              │
│       └────────────┴────────────┴────────────┘              │
│                         ↓                                    │
│  ┌──────────────────────────────────────────────────┐      │
│  │          ROLE-BASED ROUTER FILTERS                │      │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │      │
│  │  │AdminMenu │  │ VIPMenu  │  │ FreeMenu │       │      │
│  │  │ Router   │  │ Router   │  │ Router   │       │      │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘       │      │
│  └───────┼────────────┼────────────┼───────────────┘      │
│          ↓            ↓            ↓                       │
├──────────┴────────────┴────────────┴─────────────────────┤
│                    FSM STATE LAYER                        │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  MenuStates: MAIN → CONTENT_LIST → CONTENT_DETAIL   │  │
│  │  USER_MGMT → CONTENT_MGMT                          │  │
│  └─────────────────────────────────────────────────────┘  │
│                         ↓                                    │
├─────────────────────────────────────────────────────────────┤
│                    SERVICE CONTAINER (DI)                    │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ Menu       │  │ Subscription│ │ Channel    │            │
│  │ Service    │  │  Service    │  │ Service   │            │
│  └────┬───────┘  └────┬───────┘  └────┬───────┘            │
│       │               │               │                     │
│       └───────────────┴───────────────┘                     │
│                         ↓                                    │
├─────────────────────────────────────────────────────────────┤
│                     DATA ACCESS LAYER                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ Content  │  │ Interest │  │ User     │                   │
│  │ Package  │  │ Notify   │  │ Models   │                   │
│  └──────────┘  └──────────┘  └──────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Role-Based Router** | Route menu callbacks to appropriate handlers based on user role | Separate Router instances per role with F.role filters |
| **FSM Menu States** | Track user's position in menu hierarchy | StatesGroup with MAIN, CONTENT_LIST, CONTENT_DETAIL, etc. |
| **MenuService** | Render menus, handle navigation, permission checks | Service class with get_main_menu(), get_content_list(), etc. |
| **Content Package Model** | Store content with type, title, description, media | SQLAlchemy model with is_active flag |
| **InterestNotification Model** | Track "Me interesa" clicks for admin alerts | SQLAlchemy model linking user_id → package_id |
| **Admin Menu Handlers** | Content CRUD, user management, interest viewer | CallbackQuery handlers in admin.py router |
| **VIP/Free Menu Handlers** | Content browsing, "Me interesa" button | CallbackQuery handlers in vip.py, free.py routers |

## Recommended Project Structure

### Current Structure (Before Menu System)

```
bot/
├── handlers/
│   ├── admin/           # Existing admin command handlers
│   │   ├── main.py      # /admin command
│   │   ├── vip.py       # VIP management
│   │   └── free.py      # Free channel management
│   └── user/
│       ├── start.py     # /start welcome
│       └── *_flow.py    # VIP/Free flows
├── services/
│   ├── container.py     # DI container (EXISTING)
│   ├── subscription.py  # VIP/Free logic
│   ├── channel.py       # Channel management
│   ├── config.py        # Config management
│   └── voice.py         # LucienVoiceService (v1.0)
├── database/
│   └── models.py        # Existing: BotConfig, VIPSubscriber, etc.
├── states/
│   ├── admin.py         # Admin FSM states
│   └── user.py          # User FSM states
├── utils/
│   ├── keyboards.py     # Keyboard factory
│   └── formatters.py    # Data formatters
```

### Proposed Structure (With Menu System)

```
bot/
├── handlers/
│   ├── admin/           # Existing admin command handlers
│   │   └── ...          # Keep existing commands
│   ├── user/            # Existing user command handlers
│   │   └── ...          # Keep existing commands
│   └── menu/            # NEW: Menu system handlers
│       ├── __init__.py  # Export all routers
│       ├── admin.py     # Admin menu router
│       ├── vip.py       # VIP menu router
│       ├── free.py      # Free menu router
│       └── common.py    # Shared menu handlers (back, pagination)
├── services/
│   ├── container.py     # Add .menu property
│   ├── menu.py          # NEW: MenuService
│   └── ...              # Existing services unchanged
├── database/
│   ├── models.py        # Add: ContentPackage, InterestNotification
│   └── ...
├── states/
│   ├── menu.py          # NEW: MenuStates FSM group
│   └── ...              # Existing states unchanged
├── utils/
│   ├── keyboards.py     # Add menu keyboard builders
│   └── ...
└── middlewares/
    └── role.py          # NEW: RoleMiddleware (injects user.role)
```

### Structure Rationale

**Why `bot/handlers/menu/` directory:**
- **Separation of concerns:** Menus are navigation layer, distinct from command handlers
- **Router-based organization:** Each role gets its own router for clean filtering
- **Discoverability:** All menu logic in one place, easy to navigate

**Why MenuService (not inline in handlers):**
- **Centralized rendering:** All menu generation in one service
- **Reusable logic:** Content list pagination, detail view used across roles
- **Testability:** Easy to unit test menu rendering independently

**Why FSM States (not stateless callbacks):**
- **Natural navigation:** FSM tracks user's position, back button just transitions state
- **State persistence:** User can leave and return to same menu level
- **Context storage:** Store page number, filters, selected item in FSMContext

## Architectural Patterns

### Pattern 1: Role-Based Router with Filters

**What:** Separate Router instances for each role with aiogram's Magic F filters.

**When to use:** When different user roles need completely different menu experiences.

**Trade-offs:**
- **Pro:** Clean separation, each router has its own handlers
- **Pro:** Automatic role filtering at router level
- **Con:** More boilerplate (separate router file per role)
- **Con:** Cannot easily share handlers between roles

**Example:**
```python
# bot/handlers/menu/admin.py
from aiogram import Router, F
from bot.services.subscription import SubscriptionService
from bot.database.models import BotConfig

admin_menu_router = Router()

# Role filter: only admins
async def admin_filter(callback: CallbackQuery, **kwargs) -> bool:
    config = await BotConfig.get_config(kwargs['session'])
    return config.is_admin(callback.from_user.id)

admin_menu_router.callback_query.filter(admin_filter)

@admin_menu_router.callback_query(F.data == "menu:main")
async def admin_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(MenuStates.MAIN)
    text, keyboard = await container.menu.get_admin_main_menu()
    await callback.message.edit_text(text, reply_markup=keyboard)

# bot/handlers/menu/vip.py
vip_menu_router = Router()

async def vip_filter(callback: CallbackQuery, **kwargs) -> bool:
    user_id = callback.from_user.id
    return await SubscriptionService.is_vip_active(kwargs['session'], user_id)

vip_menu_router.callback_query.filter(vip_filter)

@vip_menu_router.callback_query(F.data == "menu:main")
async def vip_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(MenuStates.MAIN)
    text, keyboard = await container.menu.get_vip_main_menu()
    await callback.message.edit_text(text, reply_markup=keyboard)
```

### Pattern 2: FSM State per Menu Level

**What:** Define FSM State for each menu level in hierarchy. State transitions handle navigation.

**When to use:** When you have multi-level menus (main → list → detail) with back buttons.

**Trade-offs:**
- **Pro:** Natural navigation model (back = previous state)
- **Pro:** State persists across sessions (user can leave and return)
- **Pro:** Context storage in FSMContext (page, filters)
- **Con:** FSM state diagram can get complex with many levels

**Example:**
```python
# bot/states/menu.py
from aiogram.fsm.state import State, StatesGroup

class MenuStates(StatesGroup):
    """Menu navigation states."""
    MAIN = State()                      # Main menu
    CONTENT_LIST = State()              # Content list (paginated)
    CONTENT_DETAIL = State()            # Single content detail
    USER_MANAGEMENT = State()           # User list, user detail
    CONTENT_MANAGEMENT = State()        # Content CRUD

# Navigation handler
@admin_menu_router.callback_query(MenuStates.CONTENT_LIST, F.data == "back")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.set_state(MenuStates.MAIN)
    text, keyboard = await container.menu.get_admin_main_menu()
    await callback.message.edit_text(text, reply_markup=keyboard)
```

### Pattern 3: MenuService with Render Methods

**What:** Central service for all menu rendering. Methods return (text, keyboard) tuples.

**When to use:** When multiple roles need similar menus with small variations.

**Trade-offs:**
- **Pro:** Single source of truth for menu structure
- **Pro:** Reusable logic (pagination, filtering)
- **Pro:** Easy to test (mock service, assert return values)
- **Con:** Service can become large (many menu methods)
- **Con:** Need to keep service and handlers in sync

**Example:**
```python
# bot/services/menu.py
from aiogram.types import InlineKeyboardMarkup
from bot.database.models import ContentPackage

class MenuService:
    """Centralized menu rendering service."""

    def __init__(self, session: AsyncSession, bot: Bot):
        self._session = session
        self._bot = bot

    async def get_admin_main_menu(self) -> tuple[str, InlineKeyboardMarkup]:
        """Render admin main menu."""
        text = await self._render_admin_main_text()
        keyboard = await self._build_admin_main_keyboard()
        return text, keyboard

    async def get_content_list(
        self,
        package_type: str,
        page: int = 0,
        page_size: int = 10
    ) -> tuple[str, InlineKeyboardMarkup]:
        """Render paginated content list."""
        offset = page * page_size

        # Query active content of this type
        result = await self._session.execute(
            select(ContentPackage)
            .where(
                ContentPackage.package_type == package_type,
                ContentPackage.is_active == True
            )
            .order_by(ContentPackage.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        packages = result.scalars().all()

        text = self._render_content_list_text(packages, page)
        keyboard = await self._build_content_list_keyboard(
            packages, page, package_type
        )
        return text, keyboard

    async def get_content_detail(
        self,
        package_id: int,
        user_id: int
    ) -> tuple[str, InlineKeyboardMarkup]:
        """Render content detail with 'Me interesa' button."""
        package = await self._session.get(ContentPackage, package_id)

        if not package or not package.is_active:
            return self._content_not_found(), InlineKeyboardMarkup()

        text = await self._render_content_detail(package)
        keyboard = await self._build_content_detail_keyboard(
            package_id, user_id
        )
        return text, keyboard

    async def handle_interest(
        self,
        user_id: int,
        package_id: int
    ) -> bool:
        """Record 'Me interesa' click and notify admins."""
        # Check for duplicate
        existing = await self._session.execute(
            select(InterestNotification).where(
                InterestNotification.user_id == user_id,
                InterestNotification.package_id == package_id
            )
        )
        if existing.scalar_one_or_none():
            return False  # Already expressed interest

        # Create notification
        notification = InterestNotification(
            user_id=user_id,
            package_id=package_id,
            notified=False
        )
        self._session.add(notification)
        await self._session.commit()

        # Notify admins
        await self._notify_admins(notification)

        return True

    async def _notify_admins(self, notification: InterestNotification):
        """Send real-time notification to all admins."""
        config = await BotConfig.get_config(self._session)
        admins = await config.get_admin_ids(self._session)

        package = await self._session.get(
            ContentPackage,
            notification.package_id
        )

        for admin_id in admins:
            try:
                await self._bot.send_message(
                    admin_id,
                    f"🔔 Nuevo interés en: {package.title}\n"
                    f"Usuario: {notification.user_id}",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")

        notification.notified = True
        await self._session.commit()
```

### Pattern 4: Callback Data Encoding

**What:** Encode menu actions and payloads into callback_data strings using format `action:payload`.

**When to use:** When menu buttons need to pass data to callback handlers.

**Trade-offs:**
- **Pro:** Simple parsing with split(':')
- **Pro:** Human-readable callback data for debugging
- **Pro:** No database lookup needed for simple actions
- **Con:** Limited to ~64 bytes (Telegram limit)
- **Con:** Complex payloads need serialization

**Example:**
```python
# Build callback data
def content_item_button(package_id: int) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text="Ver detalles",
        callback_data=f"content:detail:{package_id}"
    )

# Parse callback data
@admin_menu_router.callback_query(F.data.startswith("content:detail:"))
async def content_detail(callback: CallbackQuery, state: FSMContext):
    # Parse: "content:detail:123" -> package_id = 123
    _, _, package_id_str = callback.data.split(':')
    package_id = int(package_id_str)

    await state.set_state(MenuStates.CONTENT_DETAIL)
    text, keyboard = await container.menu.get_content_detail(
        package_id,
        callback.from_user.id
    )
    await callback.message.edit_text(text, reply_markup=keyboard)
```

## Data Flow

### Menu Navigation Flow

```
[User clicks menu button]
    ↓
[CallbackQuery with role_filter]
    ↓
[Router filters by user role]
    ↓
[Handler matches callback_data]
    ↓
[Set FSM state (e.g., MenuStates.CONTENT_LIST)]
    ↓
[Call MenuService.render method]
    ↓
[Query database for content]
    ↓
[Build InlineKeyboardMarkup]
    ↓
[Edit message with new text + keyboard]
    ↓
[Response: Telegram updates user's menu]
```

### Interest Notification Flow

```
[User clicks "Me interesa" button]
    ↓
[Callback handler: content_interest]
    ↓
[Parse package_id from callback_data]
    ↓
[Call MenuService.handle_interest(user_id, package_id)]
    ↓
[Check for duplicate interest]
    ↓
[Create InterestNotification record]
    ↓
[Query all admin users]
    ↓
[Send notification message to each admin]
    ↓
[Update notification.notified = True]
    ↓
[Update button: "Me interesa" → "¡Registrado!"]
```

### Content CRUD Flow (Admin)

```
[Admin selects "Crear contenido"]
    ↓
[Set FSM state: ContentCreation.title]
    ↓
[Message handler: receive title]
    ↓
[Set FSM state: ContentCreation.description]
    ↓
[Message handler: receive description]
    ↓
[Set FSM state: ContentCreation.media]
    ↓
[Message handler: receive photo/video]
    ↓
[Save ContentPackage to database]
    ↓
[Clear FSM state]
    ↓
[Return to content management menu]
    ↓
[Show new content in list]
```

## Integration Points

### ServiceContainer Integration

```python
# bot/services/container.py
class ServiceContainer:
    # ... existing properties ...

    def __init__(self, session: AsyncSession, bot: Bot):
        self._session = session
        self._bot = bot
        self._menu_service = None  # NEW
        # ... existing service refs ...

    @property
    def menu(self) -> 'MenuService':
        """Lazy-loaded menu service."""
        if self._menu_service is None:
            from bot.services.menu import MenuService
            self._menu_service = MenuService(self._session, self._bot)
        return self._menu_service
```

### Router Registration in Main

```python
# main.py
from bot.handlers.menu import admin_menu_router, vip_menu_router, free_menu_router

# Register menu routers with appropriate priority
# Admin router first (more specific filters)
dp.include_router(admin_menu_router)
dp.include_router(vip_menu_router)
dp.include_router(free_menu_router)
```

### Integration with LucienVoiceService

```python
# bot/services/menu.py
from bot.services.voice import LucienVoiceService

class MenuService:
    def __init__(self, session: AsyncSession, bot: Bot):
        self._session = session
        self._bot = bot
        self._voice = LucienVoiceService()  # Or inject via container

    async def get_admin_main_menu(self) -> tuple[str, InlineKeyboardMarkup]:
        # Use voice service for consistent messaging
        text = self._voice.admin.menu.main_menu_greeting()
        keyboard = self._build_admin_main_keyboard()
        return text, keyboard
```

## Build Order and Dependencies

### Phase 1: Database Models (No Dependencies)

**Goal:** Add new models for content and notifications.

1. **Add ContentPackage model** to `bot/database/models.py`
2. **Add InterestNotification model** to `bot/database/models.py`
3. **Create database migration** (or let SQLAlchemy create table)

**Deliverable:** New tables in database, no handlers changed.

### Phase 2: FSM States and MenuService (Depends on Phase 1)

**Goal:** Create menu infrastructure.

1. **Create MenuStates** in `bot/states/menu.py`
2. **Create MenuService** in `bot/services/menu.py`
3. **Add .menu property** to ServiceContainer

**Deliverable:** MenuService ready for use, FSM states defined.

### Phase 3: Admin Menu Handlers (Depends on Phase 2)

**Goal:** Build admin-only menu with content CRUD.

1. **Create admin_menu_router** in `bot/handlers/menu/admin.py`
2. **Implement admin main menu**
3. **Implement content list (paginated)**
4. **Implement content detail view**
5. **Implement content CRUD (create, edit, delete, toggle)**

**Deliverable:** Admin can manage content via menu.

### Phase 4: VIP/Free Menu Handlers (Depends on Phase 2)

**Goal:** Build user-facing menus.

1. **Create vip_menu_router** in `bot/handlers/menu/vip.py`
2. **Create free_menu_router** in `bot/handlers/menu/free.py`
3. **Implement role-based main menus**
4. **Implement content browsing**
5. **Implement "Me interesa" button**

**Deliverable:** VIP and Free users can browse content and express interest.

### Phase 5: Interest Notification System (Depends on Phase 4)

**Goal:** Real-time admin notifications.

1. **Implement MenuService.handle_interest()**
2. **Implement admin notification sender**
3. **Add interest list viewer for admins**

**Deliverable:** Admins see real-time interest notifications.

### Phase 6: User Management Features (Depends on Phase 2)

**Goal:** Admin can manage users from menu.

1. **Implement user info viewer**
2. **Implement role change functionality**
3. **Implement block/expel user**
4. **Add UserRoleChangeLog model for audit**

**Deliverable:** Full user management from menu.

### Dependency Graph

```
Phase 1 (Models)
    ↓
    ├─→ Phase 2 (FSM + MenuService)
    │       ↓
    │       ├─→ Phase 3 (Admin Menu)
    │       │       ↓
    │       └─→ Phase 4 (User Menus)
    │               ↓
    │           Phase 5 (Notifications)
    │
    └─→ Phase 6 (User Management)
```

**Critical path:** Models must be added before any menu functionality.

**Parallel work:** Phase 3 (Admin) and Phase 6 (User Management) can be developed simultaneously.

## Anti-Patterns

### Anti-Pattern 1: Stateful MenuService

**What people do:** Store navigation state in MenuService instance variables.

```python
# BAD: Stateful service
class MenuService:
    def __init__(self):
        self.current_page = {}  # DANGER
        self.user_filters = {}  # DANGER
```

**Why it's wrong:**
- Service is singleton (one instance for all users)
- Concurrency issues (two users navigating simultaneously)
- Memory leaks (data never cleaned up)

**Do this instead:**
```python
# GOOD: Use FSMContext
# Handler stores state in FSMContext
async def content_list_page(callback: CallbackQuery, state: FSMContext):
    await state.update_data(page=2, filters={'type': 'vip'})

# Handler retrieves state
data = await state.get_data()
page = data.get('page', 0)
```

### Anti-Pattern 2: Hardcoded Menu Keyboards

**What people do:** Build keyboard inline in handler with hardcoded buttons.

```python
# BAD: Hardcoded keyboard
@router.callback_query(F.data == "menu:main")
async def main_menu(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Contenido", callback_data="content:list")],
        [InlineKeyboardButton(text="Usuarios", callback_data="user:list")]
    ])
    await callback.message.edit_text("Menú principal", reply_markup=keyboard)
```

**Why it's wrong:**
- Cannot render dynamic content lists
- Duplicated keyboard logic across handlers
- Hard to maintain (change in one place, not others)

**Do this instead:**
```python
# GOOD: MenuService builds keyboard dynamically
text, keyboard = await container.menu.get_admin_main_menu()
await callback.message.edit_text(text, reply_markup=keyboard)
```

### Anti-Pattern 3: Business Logic in Handlers

**What people do:** Put database queries, permission checks, validation in handlers.

```python
# BAD: Handler does everything
@router.callback_query(F.data.startswith("content:delete:"))
async def delete_content(callback: CallbackQuery):
    # Business logic in handler
    package_id = int(callback.data.split(':')[2])
    package = await session.get(ContentPackage, package_id)

    if not package:
        await callback.answer("Contenido no encontrado", show_alert=True)
        return

    # More logic...
    await session.delete(package)
    await session.commit()
```

**Why it's wrong:**
- Handler is doing service's job
- Hard to test (must run full handler)
- Cannot reuse logic (other handlers need same logic)

**Do this instead:**
```python
# GOOD: Handler delegates to service
@router.callback_query(F.data.startswith("content:delete:"))
async def delete_content(callback: CallbackQuery, session: AsyncSession):
    package_id = int(callback.data.split(':')[2])
    container = ServiceContainer(session, callback.bot)

    success, message = await container.menu.delete_content(package_id)

    if success:
        await callback.answer(message)
        # Refresh menu
    else:
        await callback.answer(message, show_alert=True)
```

## Scalability Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **Current (<1k users, <100 content)** | Simple FSM + SQLAlchemy, no caching needed. |
| **Medium (1k-10k users, 100-1k content)** | Add Redis caching for frequently accessed content. Index on (package_type, is_active, created_at). |
| **Large (10k+ users, 1k+ content)** | Separate read replica for content queries. Consider message queue for admin notifications (Celery/ARQ). |
| **Very Large (100k+ users)** | Shard database by user_id. CDN for media content. Background job for batch notifications. |

### Scaling Priorities

1. **First bottleneck:** Content list queries as packages grow. Solution: Indexing, then caching.
2. **Second bottleneck:** Admin notification spam. Solution: Batch notifications, rate limiting.
3. **Non-bottleneck:** Menu rendering (fast string formatting + keyboard building). Don't optimize prematurely.

## Sources

### Telegram Bot Architecture
- [aiogram Router Documentation](https://docs.aiogram.dev/en/latest/dispatcher/router.html) — Router patterns (HIGH confidence)
- [aiogram FSM Documentation](https://docs.aiogram.dev/en/latest/dispatcher/finite_state_machine.html) — State management (HIGH confidence)
- [Building Menu Systems in aiogram](https://mastergroosha.github.io/telegram-tutorial-2/levelup/) — Menu patterns (MEDIUM confidence)

### Role-Based Access
- [Role-Based Access Control Patterns](https://auth0.com/docs/manage-users/access-control) — RBAC design (HIGH confidence)
- [Magic Filters in aiogram](https://docs.aiogram.dev/en/latest/faq/filters.html) — F.filter usage (HIGH confidence)

### Content Management
- [SQLAlchemy Async Patterns](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) — Async ORM (HIGH confidence)
- [Database-Driven Content Systems](https://dev.to/codesphere/building-a-telegram-bot-with-database-driven-content-3m1a) — Content CRUD (MEDIUM confidence)

### Menu Navigation
- [Nested Menu Best Practices](https://surikov.dev/telegram-bot-nested-menus/) — State hierarchy (MEDIUM confidence)
- [Callback Data Patterns](https://core.telegram.org/bots/api#inlinekeyboardbutton) — Callback encoding (HIGH confidence)

---
*Architecture research for: Menu System (v1.1)*
*Researched: 2026-01-24*
