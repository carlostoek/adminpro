# Stack Research: Role-Based Menu System for Telegram Bot

**Domain:** Menu System with Role-Based Routing, Content Management, and User Notifications
**Researched:** 2026-01-24
**Confidence:** HIGH

## Executive Summary

For building a role-based menu system with content package management and notification features for an existing aiogram 3.4.1 bot, the recommended approach is **extend the existing architecture with FSM-based menu navigation, SQLAlchemy models for content persistence, and callback query routing**. This leverages the current codebase patterns (ServiceContainer, middlewares, FSM states) while adding new models for content packages and interest tracking.

## Recommended Stack

### Core Approach: Build on Existing Architecture

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **aiogram FSM** | 3.4.1 (existing) | Menu state management | Already in use, handles back/navigation naturally |
| **SQLAlchemy** | 2.0.25 (existing) | Content package storage | Existing ORM, async engine, WAL mode SQLite |
| **CallbackQuery filters** | 3.4.1 (existing) | Menu button routing | Standard pattern, already used in admin handlers |
| **aiogram Router** | 3.4.1 (existing) | Role-based handler routing | Separate routers per role, filter by user.role |
| **Lazy loading** | Existing pattern | Menu content providers | Reduce memory, only load menu handlers when accessed |

### New Database Models

| Model | Purpose | Key Fields |
|-------|---------|------------|
| **ContentPackage** | Store content packages with type, title, description, media_url | id, package_type, title, description, media_url, created_at, is_active |
| **InterestNotification** | Track "Me interesa" clicks for admin notification | id, user_id, package_id, created_at, notified |
| **UserRoleChangeLog** | Audit trail for role changes | id, user_id, old_role, new_role, changed_by, changed_at |

### Supporting Patterns

| Pattern | Purpose | When to Use |
|---------|---------|-------------|
| **FSM State per menu level** | Track user's position in menu hierarchy | Main menu, content list, content detail, back navigation |
| **Callback data encoding** | Pack menu action data into callback strings | Format: `action:payload` (e.g., `menu:content:123`) |
| **Role-based Router** | Separate handlers by user role | AdminRouter, VIPRouter, FreeRouter with filters |
| **ServiceContainer extension** | Add MenuService for menu logic | Menu rendering, navigation, permission checks |

## Installation

```bash
# All dependencies already installed
# aiogram 3.4.1
# SQLAlchemy 2.0.25
# aiosqlite 0.19.0
# python-dotenv 1.0.0

# No new dependencies required - build on existing stack
```

## Detailed Approach: Menu System Architecture

### Role-Based Routing

```python
# bot/handlers/menu/
├── __init__.py
├── admin.py          # Admin menu router
├── vip.py            # VIP menu router
├── free.py           # Free menu router
└── common.py         # Shared menu handlers

# Role filter middleware
async def role_filter(message: Message, role: str):
    user = await get_user_role(message.from_user.id)
    return user.role == role

# Router setup
admin_router = Router()
admin_router.message.filter(F.role == "admin")
admin_router.callback_query.filter(F.role == "admin")
```

### FSM Menu State Management

```python
# bot/states/menu.py
class MenuStates(StatesGroup):
    MAIN = State()
    CONTENT_LIST = State()
    CONTENT_DETAIL = State()
    USER_MANAGEMENT = State()
    CONTENT_MANAGEMENT = State()

# Handler example
@admin_router.callback_query(MenuStates.MAIN, F.data == "content_management")
async def content_management_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(MenuStates.CONTENT_MANAGEMENT)
    await render_content_management_menu(callback.message)
```

### Content Package Models

```python
# bot/database/models.py (add to existing)

class ContentPackage(Base):
    """Content packages for display in menus."""
    __tablename__ = "content_packages"

    id = Column(Integer, primary_key=True)
    package_type = Column(String(50), nullable=False)  # 'vip', 'free', 'admin'
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    media_url = Column(String(500), nullable=True)  # Photo/video URL
    file_id = Column(String(255), nullable=True)  # Telegram file_id
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("bot_config.id"), nullable=True)

    # Relationship to interest notifications
    interests = relationship("InterestNotification", back_populates="package")

class InterestNotification(Base):
    """Track user interest in content packages."""
    __tablename__ = "interest_notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    package_id = Column(Integer, ForeignKey("content_packages.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    notified = Column(Boolean, default=False)  # Whether admin was notified

    # Relationships
    package = relationship("ContentPackage", back_populates="interests")
```

### Menu Service

```python
# bot/services/menu.py
class MenuService:
    """Menu rendering and navigation service."""

    def __init__(self, session: AsyncSession, bot: Bot):
        self._session = session
        self._bot = bot

    async def get_main_menu(self, user_id: int) -> tuple[str, InlineKeyboardMarkup]:
        """Render role-appropriate main menu."""
        user = await self._get_user(user_id)
        if user.is_admin:
            return self._admin_main_menu()
        elif await self._is_vip(user_id):
            return self._vip_main_menu()
        else:
            return self._free_main_menu()

    async def get_content_list(self, package_type: str, page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
        """Render paginated content list."""
        # Query content packages by type
        # Build keyboard with pagination
        pass

    async def get_content_detail(self, package_id: int) -> tuple[str, InlineKeyboardMarkup]:
        """Render content detail with 'Me interesa' button."""
        package = await self._get_package(package_id)
        # Build message with media if available
        # Add interest button
        pass

    async def handle_interest(self, user_id: int, package_id: int) -> bool:
        """Record 'Me interesa' click and notify admin."""
        interest = InterestNotification(user_id=user_id, package_id=package_id)
        self._session.add(interest)
        await self._session.commit()
        await self._notify_admin(interest)
        return True
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **FSM-based menus** | Inline-only stateless menus | If you have simple 1-level menus without nested navigation. FSM is better for multi-level with back buttons |
| **SQLAlchemy models** | Redis-based content cache | If you have 100k+ content packages and need sub-ms queries. Not needed for typical bots (<1000 packages) |
| **Callback data encoding** | Separate state table | If you need to track menu analytics across sessions. Encoding is simpler for standard use |
| **Role-based routers** | Single router with if-checks | If you have only 1-2 role differences. Routers scale better with 3+ roles |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Hardcoded menu keyboards** | Cannot render dynamic content lists | Build keyboards dynamically from database |
| **ConversationHandler (telebot style)** | aiogram has FSM which is more powerful | Use FSM States for menu navigation |
| **Global menu state dicts** | Concurrency issues, memory leaks | FSMContext stored by aiogram, scoped per user |
| **Message-only menus** | Cannot use inline buttons, poor UX | CallbackQuery + inline keyboards for menus |
| **Separate "menu" microservice** | Over-engineering, adds latency | MenuService within existing bot process |

## Implementation Strategy

### Phase 1: Database Models and Service (LOW risk)
```python
# bot/database/models.py - Add ContentPackage, InterestNotification
# bot/services/menu.py - Create MenuService with basic methods
# bot/services/container.py - Add @property menu
```

### Phase 2: Admin Menu with Content Management (MEDIUM risk)
```python
# bot/handlers/menu/admin.py - Admin menu handlers
# Content CRUD: create, edit, delete, toggle active
# Content list with pagination
# Interest notification viewer
```

### Phase 3: VIP/Free User Menus (MEDIUM risk)
```python
# bot/handlers/menu/vip.py - VIP menu handlers
# bot/handlers/menu/free.py - Free menu handlers
# Role-based routing with filters
# Content browsing with pagination
```

### Phase 4: Interest Notification System (LOW risk)
```python
# "Me interesa" button on content detail
# Admin notification on interest clicks
# Interest list viewer for admins
```

### Phase 5: User Management Features (MEDIUM risk)
```python
# User info viewer (from admin menu)
# Role change functionality
# Block/expel user functionality
# User activity log
```

### Phase 6: Free Channel Entry Flow (LOW risk)
```python
# Social media link display
# Follow verification (if needed)
# Free channel invite generation
```

## Stack Patterns by Use Case

**If you need multi-level navigation:**
- Use FSM States for each menu level
- Store navigation context in FSMContext (page, filters, selected_item)
- Back buttons restore previous state

**If you need dynamic content:**
- Query ContentPackage from database
- Build keyboard iteratively from results
- Use callback data encoding for actions

**If you need admin notifications:**
- InterestNotification model tracks clicks
- Background job or async task sends admin messages
- Use existing LucienVoiceService for consistent messaging

**If you need role-based access:**
- Check user.role before rendering menu
- Use aiogram's F.filter for router-level filtering
- Hide/show menu options based on permissions

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Python 3.11+ | All patterns (dataclass, async, FSM) | Existing environment |
| aiogram 3.4.1 | FSM, Router, CallbackQuery, F filters | Already in use |
| SQLAlchemy 2.0.25 | New models, async queries | Existing patterns |
| aiosqlite 0.19.0 | Async SQLite access | No changes needed |

## Integration Points

### With Existing Services

```python
# bot/services/container.py
class ServiceContainer:
    # ... existing properties ...

    @property
    def menu(self) -> 'MenuService':
        """Lazy-loaded menu service."""
        if self._menu_service is None:
            from bot.services.menu import MenuService
            self._menu_service = MenuService(self._session, self._bot)
        return self._menu_service
```

### With Existing Middlewares

```python
# bot/middlewares/role.py (NEW)
class RoleMiddleware(BaseMiddleware):
    """Inject user role into callback data."""
    async def process(
        self,
        callback: CallbackQuery,
        data: dict
    ):
        user_id = callback.from_user.id
        data["user_role"] = await self._get_user_role(user_id)
```

### With LucienVoiceService

```python
# Menu messages use voice service for consistency
async def render_main_menu(callback: CallbackQuery, container: ServiceContainer):
    user_role = await container.subscription.get_user_role(callback.from_user.id)

    text = container.voice.menu.main_menu_greeting(
        user_name=callback.from_user.first_name,
        role=user_role
    )
    keyboard = await container.menu.get_main_menu_keyboard(user_role)

    await callback.message.edit_text(text, reply_markup=keyboard)
```

## Performance Considerations

For typical bot usage (<10k users, <1000 content packages):

| Operation | Expected Time | Notes |
|-----------|---------------|-------|
| Menu render from DB | <50ms | Single query, indexed by type/is_active |
| Callback handler | <20ms | FSM context + simple logic |
| Interest notification | <100ms | DB insert + admin message |
| Content list pagination | <50ms | LIMIT/OFFSET query with index |

Bottlenecks to watch:
- N+1 queries when rendering content lists (use selectinload)
- Sending admin notifications (queue if multiple admins)
- Media file downloads (cache file_id after first upload)

## Testing Strategy

```python
# tests/test_menu_service.py
async def test_role_based_menu_rendering():
    """Test that users get correct menu based on role."""
    container = ServiceContainer(session, bot)

    # Admin gets admin menu
    admin_text, admin_kb = await container.menu.get_main_menu(admin_user_id)
    assert "Gestión" in admin_text

    # VIP gets VIP menu
    vip_text, vip_kb = await container.menu.get_main_menu(vip_user_id)
    assert "Contenido VIP" in vip_text

async def test_interest_notification():
    """Test that 'Me interesa' creates notification and notifies admin."""
    result = await container.menu.handle_interest(user_id, package_id)
    assert result is True

    notification = await session.get(InterestNotification, (user_id, package_id))
    assert notification.notified is True
```

## Migration Path

1. **Week 1:** Add database models (ContentPackage, InterestNotification)
2. **Week 2:** Create MenuService with basic render methods
3. **Week 3:** Build admin menu with content CRUD
4. **Week 4:** Implement VIP/Free user menus
5. **Week 5:** Add interest notification system
6. **Week 6:** Implement user management features
7. **Week 7:** Build free channel entry flow
8. **Week 8:** Integration testing and polish

**Risk mitigation:**
- Start with admin-only features (no user impact)
- Add role routing incrementally (one role at a time)
- Test menu navigation thoroughly (back buttons, state transitions)
- Keep FSM states simple (avoid deep nesting)

## Open Questions for Validation

- **Content package types:** How many types? (vip, free, admin, custom?)
- **Interest notification urgency:** Real-time or batched for admins?
- **User management scope:** Can admins modify other admins or only users?
- **Social media links:** Static config or database-stored?
- **Content approval workflow:** Do packages need approval before appearing?

## Sources

**Telegram Bot Menu Patterns:**
- [aiogram FSM Documentation](https://docs.aiogram.dev/en/latest/dispatcher/finite_state_machine.html) — Official FSM guide (HIGH confidence)
- [Building Nested Menu Systems in aiogram](https://mastergroosha.github.io/telegram-tutorial-2/levelup/) — Menu state patterns (MEDIUM confidence)
- [Telegram Bot: Best Practices for Keyboards](https://core.telegram.org/bots/features#inline-keyboards) — Inline keyboard guidelines (HIGH confidence)

**Role-Based Access:**
- [Role-Based Access Control in Bots](https://www.botframework.com/blog/role-based-access-control/) — RBAC patterns (MEDIUM confidence)
- [aiogram Filter Documentation](https://docs.aiogram.dev/en/latest/faq/filters.html) — Magic filter usage (HIGH confidence)

**Content Management:**
- [Database-Driven Bot Content](https://dev.to/codesphere/building-a-telegram-bot-with-database-driven-content-3m1a) — Content CRUD patterns (MEDIUM confidence)
- [SQLAlchemy Async Patterns](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) — Async ORM usage (HIGH confidence)

**Notification Systems:**
- [Telegram Bot Notifications Best Practices](https://www.twilio.com/blog/notifications-telegram-bot) — Notification patterns (MEDIUM confidence)
- [Async Task Queues in Python](https://docs.celeryq.dev/en/stable/) — Background jobs (if needed) (HIGH confidence)

---
*Stack research for: Role-Based Menu System (v1.1)*
*Researched: 2026-01-24*
*Python 3.11+ | aiogram 3.4.1 | SQLAlchemy 2.0.25*
