# Pitfalls Research: Menu System for Role-Based Bot Experience

**Domain:** Telegram Bot Menu System with Role-Based Routing
**Researched:** 2026-01-24
**Confidence:** HIGH

## Executive Summary

Implementing a role-based menu system with FSM navigation, content CRUD, and user management introduces critical risks around state management complexity, permission escalation, and notification spam. This research identifies pitfalls from real-world bot menu implementations and FSM-based navigation systems.

**Key Risk:** Menu systems start simple but accumulate state complexity ("FSM state soup"), permission bugs (users accessing wrong menus), and notification fatigue that make the bot unusable or insecure.

---

## Critical Pitfalls

### Pitfall 1: FSM State Soup (Unmanageable State Transitions)

**What goes wrong:**
Menu navigation grows into dozens of FSM states with unclear transitions:
```python
# 6 months later...
class MenuStates(StatesGroup):
    MAIN = State()
    CONTENT_LIST = State()
    CONTENT_DETAIL = State()
    CONTENT_EDIT_TITLE = State()
    CONTENT_EDIT_DESC = State()
    CONTENT_EDIT_MEDIA = State()
    USER_LIST = State()
    USER_DETAIL = State()
    USER_CHANGE_ROLE = State()
    # ... 20 more states

# Back button logic becomes spaghetti
async def handle_back(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state == MenuStates.CONTENT_DETAIL:
        await state.set_state(MenuStates.CONTENT_LIST)
    elif current_state == MenuStates.CONTENT_EDIT_TITLE:
        await state.set_state(MenuStates.CONTENT_DETAIL)
    # ... 20 more if/else branches
```

**Why it happens:**
- Every new feature adds new states without refactoring
- No clear state hierarchy or grouping
- Back button implemented incrementally (one case at a time)
- Developers add "just one more state" instead of rethinking structure

**How to avoid:**
1. **Limit depth to 3 levels maximum:** Main → List → Detail
2. **Group related states:** Use state data, not separate states
3. **Explicit state transitions:** Document allowed transitions in code
4. **Back button pattern:** Store previous state in FSMContext

```python
# GOOD: Shallow hierarchy with context storage
class MenuStates(StatesGroup):
    MAIN = State()              # Level 1
    BROWSE = State()            # Level 2 (all lists use this)
    DETAIL = State()            # Level 3 (all details use this)

# Store what we're browsing in context
async def content_list(callback: CallbackQuery, state: FSMContext):
    await state.set_state(MenuStates.BROWSE)
    await state.update_data(browse_type='content', page=0)

async def user_list(callback: CallbackQuery, state: FSMContext):
    await state.set_state(MenuStates.BROWSE)
    await state.update_data(browse_type='users', page=0)

# Universal back button
async def handle_back(callback: CallbackQuery, state: FSMContext):
    current = await state.get_state()
    if current == MenuStates.DETAIL:
        await state.set_state(MenuStates.BROWSE)  # Always go back to browse
    elif current == MenuStates.BROWSE:
        await state.set_state(MenuStates.MAIN)    # Always go back to main
```

**Warning signs:**
- More than 8 FSM states in total
- Nested if/else for state transitions
- Back button handler >20 lines
- Developers unsure which state handles which callback

**Phase to address:** Phase 2 (FSM States Definition)

**Impact if ignored:** CRITICAL - Unmaintainable navigation, bugs in back button, impossible to add features

---

### Pitfall 2: Role Detection Race Conditions

**What goes wrong:**
User's role changes (VIP expires, admin demoted) but menu still shows old role's options:
```python
# BAD: Role checked once, never rechecked
@vip_menu_router.callback_query(F.data == "menu:main")
async def vip_menu(callback: CallbackQuery, state: FSMContext):
    # Role checked at router level, but state persists for hours
    text = "Contenido VIP exclusivo"
    await callback.message.edit_text(text, reply_markup=vip_keyboard)

# User's VIP expires 5 minutes later
# But they still see VIP menu because they're in VIP FSM state
```

**Why it happens:**
- Role filters applied at router level, not rechecked on each action
- FSM state persists across role changes
- Caching of role status (optimization) becomes stale
- No role revalidation on state transitions

**How to avoid:**
1. **Check role on every action:** Don't rely solely on router filters
2. **Invalidate state on role change:** Clear FSM when role changes
3. **Use fresh role queries:** Always check database, not cached values
4. **Role change hooks:** When role changes, clear user's FSM state

```python
# GOOD: Recheck role on sensitive actions
@vip_menu_router.callback_query(F.data.startswith("vip:content:"))
async def vip_content_access(callback: CallbackQuery, session: AsyncSession):
    # Recheck role (not just router filter)
    user_id = callback.from_user.id
    is_vip = await SubscriptionService.is_vip_active(session, user_id)

    if not is_vip:
        await state.clear()
        await callback.answer("Tu suscripción VIP ha expirado", show_alert=True)
        return await render_free_menu(callback)

    # Proceed with VIP content
    ...

# GOOD: Clear state on role change
async def expire_vip_subscriber(user_id: int):
    # ... expiration logic ...
    # Clear FSM state so user sees updated menu
    await fsm_storage.set_state(user_id, None)
```

**Warning signs:**
- Users report "I still see VIP menu after expiring"
- Role change doesn't affect menu until bot restart
- Router filters are the only role check

**Phase to address:** Phase 1 (Service Design) + Phase 3 (Handler Implementation)

**Impact if ignored:** HIGH - Security vulnerability, unauthorized access, confused users

---

### Pitfall 3: Admin Notification Spam

**What goes wrong:**
"Me interesa" feature sends notification to ALL admins for EVERY click:
```python
# BAD: Spam every admin on every interest
async def notify_admins(package: ContentPackage, user_id: int):
    admins = await get_all_admins()  # 50 admins
    for admin_id in admins:
        await bot.send_message(
            admin_id,
            f"🔔 Interés en: {package.title}\nUsuario: {user_id}"
        )
    # 50 notifications sent per interest click
```

**Why it happens:**
- No notification batching or rate limiting
- All admins treated equally (no notification preferences)
- No deduplication (user clicks "Me interesa" 5 times = 5 notifications)
- Real-time urgency applied to non-urgent events

**How to avoid:**
1. **Deduplicate interests:** One notification per (user, package) pair
2. **Batch notifications:** Collect interests, send periodic digest
3. **Notification preferences:** Let admins opt-in/out of real-time
4. **Rate limiting:** Max 1 notification per minute per admin

```python
# GOOD: Deduplicated + batched notifications
async def handle_interest(user_id: int, package_id: int):
    # Check for duplicate
    existing = await session.execute(
        select(InterestNotification).where(
            InterestNotification.user_id == user_id,
            InterestNotification.package_id == package_id
        )
    )
    if existing.scalar_one_or_none():
        return False  # Already notified

    # Create notification record
    notification = InterestNotification(user_id=user_id, package_id=package_id)
    session.add(notification)
    await session.commit()

    # Don't send immediately, queue for batching
    await notification_queue.add(notification)
    return True

# Background job: send digest every 10 minutes
async def send_interest_digest():
    pending = await get_unnotified_interests(limit=50)
    if not pending:
        return

    # Group by package
    by_package = defaultdict(list)
    for notif in pending:
        by_package[notif.package].append(notif.user)

    # Send one message per package to interested admins
    for package, users in by_package.items():
        admins = await get_admins_who_want_notifications()
        for admin_id in admins:
            await bot.send_message(
                admin_id,
                f"📊 {len(users)} interesados en: {package.title}\n"
                f"Usuarios: {', '.join(map(str, users[:5]))}"
            )

    # Mark as sent
    await mark_notified(pending)
```

**Warning signs:**
- Admins mute bot due to spam
- Multiple notifications for same user/content
- Admins complain about notification volume
- Notification sending blocks menu handlers (slow)

**Phase to address:** Phase 4 (Interest Notification System)

**Impact if ignored:** MEDIUM - Admins disable bot, miss important notifications

---

### Pitfall 4: Content Pagination Off-by-One Errors

**What goes wrong:**
Pagination shows duplicate items, skips items, or shows empty pages:
```python
# BAD: Off-by-one error in pagination
async def get_content_list(page: int):
    offset = page * 10  # Wrong: should be (page - 1) * 10
    result = await session.execute(
        select(ContentPackage)
        .offset(offset)
        .limit(10)
    )
    # Page 1 skips first 10 items, shows items 11-20
```

**Why it happens:**
- Page numbering confusion (0-indexed vs 1-indexed)
- No validation of page parameter (negative, huge numbers)
- COUNT query not run, so no total pages
- Previous/Next buttons enabled when they shouldn't be

**How to avoid:**
1. **Explicit page numbering:** Decide 0-indexed or 1-indexed, stick to it
2. **Validate page parameter:** Reject negative, cap at max page
3. **Count total items:** Calculate total_pages, show to user
4. **Disable buttons at bounds:** Previous disabled on page 0, Next disabled on last page

```python
# GOOD: Correct pagination with validation
async def get_content_list(package_type: str, page: int = 0):
    page_size = 10

    # Count total items
    total_count = await session.execute(
        select(func.count(ContentPackage.id)).where(
            ContentPackage.package_type == package_type,
            ContentPackage.is_active == True
        )
    )
    total = total_count.scalar()

    # Validate page
    max_page = max(0, (total - 1) // page_size)
    page = max(0, min(page, max_page))

    # Query with correct offset
    offset = page * page_size  # 0-indexed pages
    result = await session.execute(
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

    # Build keyboard with disabled buttons at bounds
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="⬅️",
                callback_data=f"content:list:{page-1}" if page > 0 else "disabled"
            ),
            InlineKeyboardButton(text=f"Página {page+1}/{max_page+1}", callback_data="noop"),
            InlineKeyboardButton(
                text="➡️",
                callback_data=f"content:list:{page+1}" if page < max_page else "disabled"
            )
        ]
    ])

    return packages, keyboard
```

**Warning signs:**
- Users report duplicate items across pages
- Items missing (skipped) from list
- Empty pages shown
- "Previous" button shows new items instead of old

**Phase to address:** Phase 3 (Admin Menu - Content List)

**Impact if ignored:** MEDIUM - Broken UX, user frustration, data inconsistency

---

### Pitfall 5: Permission Escalation via Callback Manipulation

**What goes wrong:**
User crafts callback_data to access admin functions:
```python
# User inspects keyboard, sees: callback_data="admin:delete_user:123"
# User edits keyboard, changes to: callback_data="admin:delete_user:456"
# User clicks button, deletes user 456 without being admin
```

**Why it happens:**
- Callback data trusted without permission check
- Router filters only check role on menu entry
- Individual actions assume user has permission
- No audit trail for sensitive actions

**How to avoid:**
1. **Check permission on EVERY action:** Not just router level
2. **Audit sensitive operations:** Log who did what
3. **Confirm destructive actions:** Require confirmation for delete/block
4. **Action-specific permissions:** Different admin levels for different actions

```python
# GOOD: Permission check on every action
@router.callback_query(F.data.startswith("admin:delete_user:"))
async def delete_user(callback: CallbackQuery, session: AsyncSession):
    # Check permission (even though router has admin filter)
    admin_id = callback.from_user.id
    if not await is_admin(session, admin_id):
        logger.warning(f"Non-admin {admin_id} attempted delete_user")
        await callback.answer("Acceso denegado", show_alert=True)
        return

    # Parse target
    target_id = int(callback.data.split(':')[2])

    # Prevent self-deletion
    if target_id == admin_id:
        await callback.answer("No puedes borrarte a ti mismo", show_alert=True)
        return

    # Require confirmation
    await state.update_data(pending_delete=target_id)
    await callback.message.edit_text(
        f"⚠️ Confirmar: ¿Borrar usuario {target_id}?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Confirmar", callback_data=f"admin:confirm_delete:{target_id}")],
            [InlineKeyboardButton(text="Cancelar", callback_data="admin:user_list")]
        ])
    )

# Confirmation handler
@router.callback_query(F.data.startswith("admin:confirm_delete:"))
async def confirm_delete_user(callback: CallbackQuery, session: AsyncSession):
    target_id = int(callback.data.split(':')[2])

    # Check permission AGAIN
    if not await is_admin(session, callback.from_user.id):
        return await callback.answer("Acceso denegado", show_alert=True)

    # Perform deletion
    await delete_user_from_db(session, target_id)

    # Audit log
    await audit_log.info(
        "User deleted",
        admin_id=callback.from_user.id,
        target_id=target_id,
        timestamp=datetime.utcnow()
    )

    await callback.answer("Usuario eliminado")
```

**Warning signs:**
- No permission check in action handlers (only router filter)
- Destructive actions execute immediately without confirmation
- No logging of who did what
- Callback data directly used to perform actions

**Phase to address:** Phase 3 (Admin Menu) + Phase 6 (User Management)

**Impact if ignored:** CRITICAL - Security vulnerability, unauthorized actions, data loss

---

### Pitfall 6: MenuService Becoming God Object

**What goes wrong:**
MenuService accumulates all menu logic, becomes 2000+ lines:
```python
# 6 months later...
class MenuService:
    # 50 methods for admin menus
    def get_admin_main_menu(self) -> ...
    def get_admin_content_list(self) -> ...
    def get_admin_user_list(self) -> ...

    # 40 methods for VIP menus
    def get_vip_main_menu(self) -> ...
    def get_vip_content_list(self) -> ...

    # 30 methods for Free menus
    def get_free_main_menu(self) -> ...

    # 20 helper methods
    def _render_text(self) -> ...
    def _build_keyboard(self) -> ...
    # ... 140 more methods
```

**Why it happens:**
- All menu rendering goes through one service
- No separation between different menu types
- "Just add one more method" mentality
- Fear of breaking existing code by refactoring

**How to avoid:**
1. **Split by role:** AdminMenuService, VIPMenuService, FreeMenuService
2. **Base class for shared logic:** Common pagination, text rendering
3. **Limit methods per class:** Max 20 methods per service
4. **Keyboard builders separate:** utils/keyboards.py for keyboard construction

```python
# GOOD: Split by role with base class
class BaseMenuService:
    """Shared menu logic."""
    def __init__(self, session: AsyncSession, bot: Bot):
        self._session = session
        self._bot = bot

    async def _build_pagination_keyboard(self, page, max_page, callback_prefix):
        # Shared pagination logic
        pass

    async def _render_content_list_text(self, packages, page):
        # Shared text rendering
        pass

class AdminMenuService(BaseMenuService):
    """Admin-only menus."""
    async def get_main_menu(self) -> tuple[str, InlineKeyboardMarkup]:
        # Admin-specific logic
        pass

    async def get_content_management_menu(self) -> tuple[str, InlineKeyboardMarkup]:
        # Admin-specific logic
        pass

class VIPMenuService(BaseMenuService):
    """VIP-only menus."""
    async def get_main_menu(self) -> tuple[str, InlineKeyboardMarkup]:
        # VIP-specific logic
        pass

# ServiceContainer routes to correct service
class ServiceContainer:
    @property
    def admin_menu(self) -> AdminMenuService:
        if self._admin_menu is None:
            self._admin_menu = AdminMenuService(self._session, self._bot)
        return self._admin_menu

    @property
    def vip_menu(self) -> VIPMenuService:
        if self._vip_menu is None:
            self._vip_menu = VIPMenuService(self._session, self._bot)
        return self._vip_menu
```

**Warning signs:**
- MenuService >500 lines
- >30 methods in one class
- Method names with 3+ underscores (_render_admin_content_list_text_v2)
- Developers afraid to touch MenuService

**Phase to address:** Phase 2 (MenuService Design) + Ongoing refactoring

**Impact if ignored:** HIGH - Unmaintainable code, slow development, bug-prone

---

### Pitfall 7: Stateful Content Media Handling

**What goes wrong:**
Content media (photos/videos) downloaded and stored as URLs, but URLs expire or files are deleted:
```python
# BAD: Store URL, but URL expires
package = ContentPackage(
    title="My Content",
    media_url="https://temp-storage.com/photo123.jpg"  # Expires in 24h
)
await session.add(package)

# User tries to view content 1 week later
# URL is broken, media doesn't load
```

**Why it happens:**
- Using external file hosting with temporary URLs
- Not storing Telegram file_id (permanent)
- No validation that media URL still works
- No fallback when media fails to load

**How to avoid:**
1. **Store Telegram file_id:** Permanent reference to uploaded file
2. **Upload immediately:** Don't store URLs, upload to Telegram first
3. **Validate on upload:** Check file size, type before storing
4. **Graceful degradation:** Show text if media fails

```python
# GOOD: Store Telegram file_id
@admin_menu_router.message(MenuStates.CONTENT_CREATION_MEDIA, F.photo)
async def receive_content_photo(message: Message, state: FSMContext):
    # Get largest photo
    photo = message.photo[-1]
    file_id = photo.file_id  # Permanent reference

    # Store file_id, not URL
    data = await state.get_data()
    data['media_file_id'] = file_id
    data['media_type'] = 'photo'
    await state.update_data(data)

    await message.answer("Foto recibida. Guardando contenido...")

    # Create content package
    package = ContentPackage(
        title=data['title'],
        description=data['description'],
        file_id=file_id,  # Store permanent file_id
        package_type='vip',
        is_active=True
    )
    await session.add(package)
    await session.commit()

# When rendering content
async def get_content_detail(package_id: int):
    package = await session.get(ContentPackage, package_id)

    if package.file_id:
        if package.media_type == 'photo':
            # Send using file_id (permanent, no bandwidth)
            await bot.send_photo(chat_id, photo=package.file_id, caption=package.description)
        elif package.media_type == 'video':
            await bot.send_video(chat_id, video=package.file_id, caption=package.description)
    else:
        # Fallback to text only
        await bot.send_message(chat_id, package.description)
```

**Warning signs:**
- Media URLs stored instead of file_id
- Broken media icons in old content
- "Media not found" errors
- High bandwidth usage (re-downloading media)

**Phase to address:** Phase 3 (Admin Menu - Content Creation)

**Impact if ignored:** MEDIUM - Broken content, poor UX, wasted bandwidth

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip role checks on actions | Faster development | Security vulnerability | Never (safety critical) |
| Hardcoded menu keyboards | Quick menu implementation | Cannot add dynamic content | Only for prototypes |
| Send notifications immediately | Real-time feel for admins | Notification spam, performance | Only for <10 admins |
| Store URLs instead of file_id | No upload logic needed | Broken media, bandwidth waste | Never |
| One giant MenuService | No upfront design | Unmaintainable god object | Never |
| Skip pagination for lists | Simpler queries | List too long, performance | Only for <20 items |
| State caching for role check | Fewer database queries | Stale permissions | Never (security) |

---

## Integration Gotchas

Common mistakes when connecting menu system to existing bot components.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| ServiceContainer | Add MenuService without splitting by role | Split into AdminMenuService, VIPMenuService, FreeMenuService |
| FSM States | Add state for every menu variation | Use state data for variations (browse_type='content' vs 'users') |
| LucienVoiceService | Hardcode messages in handlers | Call voice service from MenuService |
| SubscriptionService | Duplicate role logic in menu handlers | Reuse is_vip_active(), get_user_role() |
| ChannelService | Assume channel always configured | Check is_configured() before using |
| Admin Middleware | Only check at router level | Recheck permission on sensitive actions |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| N+1 queries in content list | Slow list render, high DB CPU | Use selectinload/joinedload for relationships | >50 items |
| Sending notifications synchronously | Handler timeout, slow menu response | Queue notifications, send in background | >5 admins |
| No pagination on content lists | UI lag, timeout on large lists | Always paginate, max 20 items per page | >30 items |
| Re-rendering full menu on every action | Slow updates, flickering | Use edit_text/edit_reply_markup, not full rebuild | >100 menu opens/hour |
| Storing media in DB (base64) | DB bloat, slow queries | Store file_id, media in Telegram | >100 content items |
| No caching of role checks | Repeated DB queries | Cache role in FSMContext for session duration | >1000 users |

**Note for this project:** Termux environment has memory constraints. Even "small scale" performance issues matter. Keep menu rendering lightweight.

---

## Security Mistakes

Domain-specific security issues for menu systems.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Callback data trusted blindly | Privilege escalation, data manipulation | Validate on every action, check permissions |
| No confirmation for delete | Accidental data loss, malicious actions | Require confirmation for destructive actions |
| Admin can delete other admins | Power struggles, bot administration breakdown | Prevent admin-on-admin actions |
| No audit trail | Cannot investigate security incidents | Log all sensitive actions with who/when/what |
| Role change without state clear | User retains old menu access | Clear FSM state when role changes |
| File upload without validation | Malicious files, DoS | Validate file size, type, dimensions |
| SQL injection in content search | Data breach, DB corruption | Use parameterized queries (SQLAlchemy handles this) |

---

## UX Pitfalls

Common user experience mistakes in menu systems.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No back button on leaf menus | Stuck, must restart conversation | Always provide back button or "Home" |
| Loading indicators not shown | "Is it broken?" confusion | Send "Cargando..." message, edit when done |
| Empty pages with no message | "Did something go wrong?" | Show "No hay contenido" with placeholder |
| Inconsistent button order | Cognitive load, wrong clicks | Standard order: Back on left, action on right |
| No confirmation on destructive actions | Accidental deletions | Always require confirmation for delete/block |
| Pagination without page info | Lost in list, don't know position | Show "Página X/Y" on pagination buttons |
| Menu doesn't work on mobile | Buttons too small, hard to tap | Test on real device, use full-width buttons |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **FSM States:** States defined but no back button implementation
- [ ] **Role Filtering:** Router filters exist but no permission checks on actions
- [ ] **Pagination:** Implemented but off-by-one errors in offset calculation
- [ ] **Content CRUD:** Create works but edit/delete missing or broken
- [ ] **Notifications:** Sent but no deduplication (spam)
- [ ] **Media Handling:** Stores URL but not file_id (will break)
- [ ] **User Management:** View user works but role change missing
- [ ] **Error Handling:** Works for happy path only, crashes on edge cases
- [ ] **State Persistence:** Menu works in session but breaks after restart
- [ ] **Audit Logging:** Actions work but no logging for security incidents

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| FSM State Soup | HIGH | 1. Map all states and transitions<br>2. Group related states<br>3. Refactor to shallow hierarchy<br>4. Update all handlers |
| Permission Bugs | CRITICAL | 1. Audit all action handlers<br>2. Add permission checks<br>3. Test with non-admin users<br>4. Add audit logging |
| Notification Spam | MEDIUM | 1. Implement deduplication<br>2. Batch existing notifications<br>3. Add rate limiting<br>4. Ask admins to re-enable |
| Pagination Errors | LOW | 1. Fix offset calculation<br>2. Add validation<br>3. Test with empty, single, multi-page<br>4. Fix button enable/disable logic |
| God Object MenuService | HIGH | 1. Extract role-specific services<br>2. Move shared logic to base class<br>3. Update ServiceContainer<br>4. Test all menus |
| Media URL Rot | MEDIUM | 1. Migrate URLs to file_id<br>2. Re-upload content to Telegram<br>3. Update database<br>4. Add fallback for missing media |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| FSM State Soup | Phase 2 (FSM States) | Total states < 8, back button < 20 lines |
| Role Race Conditions | Phase 1 (Service Design) | Role rechecked on every action |
| Notification Spam | Phase 4 (Notifications) | Deduplication works, batched sending |
| Pagination Errors | Phase 3 (Content List) | Validate with 0, 1, many pages |
| Permission Escalation | Phase 3 (Admin Menu) | Permission check on every action |
| God Object MenuService | Phase 2 (Service Design) | Service < 500 lines, < 30 methods |
| Media URL Rot | Phase 3 (Content Creation) | Store file_id, not URL |

---

## Sources

- [FSM State Management Best Practices](https://docs.aiogram.dev/en/latest/dispatcher/finite_state_machine.html) — aiogram FSM guide (HIGH confidence)
- [Telegram Bot Security Checklist](https://core.telegram.org/bots/security) — Official security guidelines (HIGH confidence)
- [Menu Navigation Patterns](https://mastergroosha.github.io/telegram-tutorial-2/levelup/) — Navigation patterns (MEDIUM confidence)
- [Pagination in Web Applications](https://www.postgresql.org/docs/current/queries-limit.html) — Database pagination (HIGH confidence)
- [Notification UX Best Practices](https://www.nngroup.com/articles/notification-ux/) — User experience (MEDIUM confidence)

---

*Pitfalls research for: Menu System (v1.1)*
*Researched: 2026-01-24*
*Confidence: HIGH (based on real-world patterns + aiogram documentation)*
