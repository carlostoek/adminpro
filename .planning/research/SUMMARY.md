# Project Research Summary: v1.1 "Sistema de Menus"

**Project:** Telegram Bot VIP/Free - Menu System Milestone
**Domain:** Role-Based Menu System with Content Management
**Researched:** 2026-01-24
**Confidence:** HIGH

## Executive Summary

This is a **subsequent milestone (v1.1)** adding new features to an existing Telegram bot with v1.0 (LucienVoiceService) already complete. The goal is to build a role-based menu system with content package management, user management, and notification features.

Based on research, the recommended approach is **extend the existing architecture with FSM-based menu navigation, SQLAlchemy models for content persistence, and role-based router filters**. This leverages the current codebase patterns (ServiceContainer, middlewares, FSM states, LucienVoiceService) while adding new models for content packages and interest tracking.

**Key recommendations:**
1. **Build on existing stack:** No new dependencies required—use aiogram 3.4.1 FSM, SQLAlchemy 2.0.25, and the existing ServiceContainer pattern
2. **Shallow FSM hierarchy:** Limit to 3 levels (MAIN -> BROWSE -> DETAIL) to avoid state complexity
3. **Role-based routers:** Separate Router instances per role (Admin/VIP/Free) with aiogram's Magic F filters
4. **Split services by role:** AdminMenuService, VIPMenuService, FreeMenuService inheriting from BaseMenuService to avoid god object

**Critical risks to mitigate:**
- **FSM state soup:** Unmanageable state transitions if hierarchy grows beyond 3 levels
- **Role race conditions:** User role changes but menu still shows old options
- **Notification spam:** "Me interesa" flooding admins without deduplication/batching
- **Permission escalation:** Callback manipulation allowing unauthorized actions

## Key Findings

### Recommended Stack

**Core technologies with one-line rationale each:**
- **aiogram FSM (3.4.1)** — Already in use, handles back/navigation naturally
- **SQLAlchemy (2.0.25)** — Existing ORM, async engine, WAL mode SQLite for content packages
- **CallbackQuery filters** — Standard pattern, already used in admin handlers for routing
- **Role-based Routers** — Separate Router instances per role with F.role filters for clean separation
- **Lazy loading** — Existing ServiceContainer pattern, reduces memory in Termux

**New database models required:**
- **ContentPackage** — Store content with type, title, description, media file_id, is_active flag
- **InterestNotification** — Track "Me interesa" clicks linking user_id -> package_id
- **UserRoleChangeLog** — Audit trail for role changes (admin_id, old_role, new_role, timestamp)

### Expected Features

**Must have (table stakes) — Core menu system:**
- **Role-based menu routing** — Different menus for Admin/VIP/Free based on user detection
- **FSM menu states** — MAIN, CONTENT_LIST, CONTENT_DETAIL for navigation hierarchy
- **Content list pagination** — LIMIT/OFFSET queries with prev/next buttons (max 10-20 per page)
- **Content detail view** — Show title, description, media with "Me interesa" button
- **Back button navigation** — Return to previous menu level via FSM state transition
- **Admin content CRUD** — Create, read, update, delete, toggle active for content packages

**Should have (differentiators) — Competitive features:**
- **"Me interesa" notification system** — Users express interest, admins get real-time alerts
- **Dynamic menu rendering** — Menus adapt to content availability from database queries
- **User management from menu** — Admin can view users, change roles, block/expel without commands
- **Soft delete for content** — is_active flag hides content without losing data
- **Audit logging** — UserRoleChangeLog tracks all role changes for accountability

**Defer (v2+) — Scale features:**
- **Menu analytics dashboard** — Most viewed content, click-through rates
- **Content scheduling** — Schedule content to appear/disappear at specific times
- **Multi-language menus** — Separate menu flows per locale
- **Advanced search** — Full-text search within content titles/descriptions

### Architecture Approach

**Major components and their responsibilities:**

1. **Role-Based Router Layer** — Separate Router instances (admin_menu_router, vip_menu_router, free_menu_router) with Magic F filters to route callbacks based on user role

2. **FSM State Layer** — MenuStates group with shallow hierarchy (MAIN -> BROWSE -> DETAIL). State data stores context (browse_type='content' vs 'users', page number). FSMContext persists state across sessions.

3. **MenuService Layer** — BaseMenuService for shared logic (pagination, text rendering), with role-specific subclasses (AdminMenuService, VIPMenuService, FreeMenuService). Methods return (text, keyboard) tuples.

4. **Data Access Layer** — ContentPackage model stores content with file_id for media. InterestNotification tracks clicks. Queries use async SQLAlchemy with proper indexing.

5. **Integration Layer** — ServiceContainer extended with .menu property (lazy-loaded). LucienVoiceService used for consistent messaging. Existing SubscriptionService reused for role detection.

**Key architectural patterns:**
- **FSM State per menu level** — Natural back button (state transition to previous)
- **Callback data encoding** — Format: `action:payload` (e.g., `content:detail:123`)
- **ServiceContainer extension** — Add @property menu with lazy loading
- **Keyboard builders separate** — utils/keyboards.py for keyboard construction

### Critical Pitfalls

**Top 5 pitfalls with prevention strategies:**

1. **FSM State Soup** — Limit to 3 levels max, use state data for variations (browse_type='content' vs 'users'), universal back button logic. Prevention: Total states < 8, back button < 20 lines.

2. **Role Race Conditions** — User role changes but menu shows old options. Prevention: Recheck role on EVERY action (not just router filter), clear FSM state when role changes, always query database not cached values.

3. **Admin Notification Spam** — "Me interesa" floods admins. Prevention: Deduplicate (one notification per user/package pair), batch notifications (digest every 10 min), rate limit (max 1/min per admin).

4. **Pagination Off-by-One Errors** — Duplicate/skipped items. Prevention: Explicit page numbering (0-indexed), validate page parameter (reject negative, cap at max), COUNT query for total pages, disable buttons at bounds.

5. **Permission Escalation** — User crafts callback_data to access admin functions. Prevention: Check permission on EVERY action (not just router), audit log all sensitive operations, require confirmation for delete/block.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Database Models and Service Foundation

**Rationale:** Models are foundational—everything depends on them. Build infrastructure first without disrupting existing handlers.

**Delivers:**
- ContentPackage, InterestNotification, UserRoleChangeLog models
- MenuStates FSM group (shallow hierarchy: MAIN, BROWSE, DETAIL)
- BaseMenuService with role-specific subclasses
- ServiceContainer integration (.menu property)

**Addresses:** Features from STACK.md (models), ARCHITECTURE.md (service layer)

**Avoids:** PITFALL.md #6 (god object) — split services by role from start

**Tasks:**
- Add ContentPackage model with file_id, is_active fields
- Add InterestNotification model with notified flag
- Create MenuStates (max 8 states, 3 levels)
- Create BaseMenuService, AdminMenuService, VIPMenuService, FreeMenuService
- Add @property menu to ServiceContainer

### Phase 2: Admin Menu with Content Management

**Rationale:** Admin features first—no user impact if buggy. Validates core menu patterns before user-facing rollout.

**Delivers:**
- admin_menu_router with role filter
- Admin main menu with navigation
- Content list (paginated, filtered by type)
- Content detail view
- Content CRUD (create, edit, delete, toggle active)

**Uses:** Stack elements from STACK.md (FSM, routers, MenuService)

**Implements:** Architecture component (Pattern 1: Role-Based Router, Pattern 3: MenuService)

**Avoids:** PITFALL.md #4 (pagination errors) — validate with 0, 1, many pages; PITFALL.md #7 (media handling) — store file_id not URL

**Tasks:**
- Create admin_menu_router with admin filter
- Implement admin_main_menu handler
- Implement content_list with pagination (offset, limit, COUNT query)
- Implement content_detail with media display
- Implement content_create FSM flow (title -> description -> media)
- Implement content_edit, content_delete, content_toggle_active

### Phase 3: VIP/Free User Menus

**Rationale:** User-facing menus after admin menu validated. Role-based routing proven, patterns established.

**Delivers:**
- vip_menu_router, free_menu_router with role filters
- VIP/Free main menus
- Content browsing (read-only, filtered by access level)
- "Me interesa" button on content detail

**Uses:** Stack elements from STACK.md (role filters, MenuService)

**Implements:** Architecture component (Pattern 2: FSM State per Level)

**Avoids:** PITFALL.md #2 (role race conditions) — recheck role on every action

**Tasks:**
- Create vip_menu_router with VIP filter (is_vip_active)
- Create free_menu_router (all users)
- Implement vip_main_menu, free_main_menu
- Implement content browsing (reuse pagination from admin)
- Implement content_detail with "Me interesa" button

### Phase 4: Interest Notification System

**Rationale:** "Me interesa" buttons exist from Phase 3, now implement notification logic.

**Delivers:**
- MenuService.handle_interest() with deduplication
- Admin notification sender (batched, rate-limited)
- Interest list viewer for admins
- Notification preferences (opt-in/out)

**Uses:** Stack elements from STACK.md (InterestNotification model)

**Implements:** FEATURE.md differentiator (interest notification system)

**Avoids:** PITFALL.md #3 (notification spam) — deduplicate, batch, rate limit

**Tasks:**
- Implement handle_interest with duplicate check
- Implement notification batching (digest every 10 min)
- Add admin_interest_list viewer
- Implement notification preferences (admin setting)

### Phase 5: User Management Features

**Rationale:** Admin controls validated, now add user management power tools.

**Delivers:**
- User info viewer (search/view user details)
- Role change functionality (promote/demote VIP <-> Free)
- Block/expel user functionality
- UserRoleChangeLog audit trail

**Uses:** Stack elements from STACK.md (UserRoleChangeLog model)

**Implements:** FEATURE.md differentiator (user management from menu)

**Avoids:** PITFALL.md #5 (permission escalation) — check permission on every action, require confirmation, audit log

**Tasks:**
- Implement user_list viewer (paginated)
- Implement user_detail view
- Implement role_change with confirmation
- Implement user_block, user_expel with confirmation
- Add UserRoleChangeLog entries for all changes

### Phase 6: Free Channel Entry Flow

**Rationale:** Optional growth feature—lowest priority, can be deferred if needed.

**Delivers:**
- Social media links display
- Follow verification (optional)
- Free channel invite generation

**Uses:** Stack elements from STACK.md (ChannelService integration)

**Implements:** FEATURE.md differentiator (social media entry flow)

**Avoids:** PITFALL.md — standard patterns, low risk

**Tasks:**
- Create social_media_config model or use BotConfig
- Implement social_links_display handler
- Implement follow_verification (if needed)
- Integrate with ChannelService.create_invite_link

### Phase Ordering Rationale

**Why this order based on dependencies:**
- Phase 1 (Models/Service) must be first—foundational, everything depends on it
- Phase 2 (Admin Menu) before Phase 3 (User Menus)—admin features safer to test first, no user impact
- Phase 3 (User Menus) before Phase 4 (Notifications)—"Me interesa" buttons added in Phase 3, notifications wired in Phase 4
- Phase 5 (User Management) after Phase 2—leverages admin menu patterns proven in Phase 2
- Phase 6 (Free Entry) last—optional growth feature, no dependencies on other phases

**Why this grouping based on architecture:**
- Phases 1-2: Admin-only features (safe to develop, no user disruption)
- Phases 3-4: User-facing features (requires proven admin patterns)
- Phase 5: Power user features (builds on validated menu system)
- Phase 6: Growth features (can be deferred if time-constrained)

**How this avoids pitfalls:**
- Phase 1 addresses PITFALL #6 (god object) by splitting services by role
- Phase 2 addresses PITFALL #4 (pagination), #7 (media) with careful implementation
- Phase 3 addresses PITFALL #2 (role conditions) with rechecking on actions
- Phase 4 addresses PITFALL #3 (notification spam) with batching/deduplication
- Phase 5 addresses PITFALL #5 (permission escalation) with confirmation/audit

### Research Flags

**Phases likely needing deeper research during planning:**

- **Phase 3 (VIP/Free User Menus):** Role detection logic needs validation—how to handle users in transition (VIP expired but not yet kicked from channel?). Edge cases around role changes during active menu session.

- **Phase 4 (Interest Notification System):** Admin notification UX needs research—how many admins is "too many" for real-time? What's the optimal batching interval (5 min, 10 min, 30 min)? Need to validate with admin use cases.

- **Phase 5 (User Management Features):** Permission model needs clarification—can admins modify other admins? Can admins block themselves? Self-deletion prevention logic needs design.

**Phases with standard patterns (skip research-phase):**

- **Phase 1 (Database Models):** Standard SQLAlchemy async patterns, well-documented. No research needed.
- **Phase 2 (Admin Menu):** aiogram FSM + Router patterns are standard. Follow existing admin handler patterns.
- **Phase 6 (Free Channel Entry Flow):** ChannelService integration exists, social media links are static config. Low complexity.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies already in use (aiogram 3.4.1, SQLAlchemy 2.0.25). No new dependencies. |
| Features | HIGH | Menu systems are well-documented in aiogram community. Pagination, role-based routing are standard patterns. |
| Architecture | HIGH | FSM-based navigation is aiogram best practice. Role-based routers documented in aiogram docs. |
| Pitfalls | HIGH | Based on real-world FSM state management issues, aiogram documentation, and common bot security mistakes. |

**Overall confidence:** HIGH

**Reasoning:** This is a subsequent milestone building on proven v1.0 architecture. All technologies are existing and familiar. The patterns (FSM, routers, ServiceContainer) are already used in the codebase. Main risks are around state management complexity and permission handling, both of which have clear mitigation strategies.

### Gaps to Address

Areas where research was inconclusive or needs validation during implementation:

1. **Content package types:** How many types needed? (vip, free, admin, custom?) Affects database schema and filtering logic. Validate during planning: what content categories will admins create?

2. **Interest notification urgency:** Real-time vs batched? Research recommends batching (digest every 10 min), but admins may want real-time for high-value content. Validate during planning: talk to admins about their notification preferences.

3. **User management permissions:** Can admins modify other admins? Can admins block themselves? Self-protection rules unclear. Validate during planning: define admin privilege levels.

4. **Social media links:** Static config or database-stored? Free channel entry flow needs social media links. Validate during planning: how often will links change?

5. **Content approval workflow:** Do packages need approval before appearing? Research assumes auto-publish (is_active=True by default). Validate during planning: is content moderation needed?

**How to handle during planning/execution:**
- Gaps 1-3: Resolve during Phase 1 planning (define schema, permissions, notification UX)
- Gap 4: Can defer to Phase 6 (implementation decision, doesn't affect architecture)
- Gap 5: Defer to v1.2 (content workflow is enhancement, not MVP)

## Sources

### Primary (HIGH confidence)

- [aiogram FSM Documentation](https://docs.aiogram.dev/en/latest/dispatcher/finite_state_machine.html) — State management patterns, official documentation
- [aiogram Router Documentation](https://docs.aiogram.dev/en/latest/dispatcher/router.html) — Router patterns, Magic F filters
- [Telegram Bot API: Inline Keyboards](https://core.telegram.org/bots/features#inline-keyboards) — Inline keyboard guidelines
- [SQLAlchemy Async Patterns](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) — Async ORM usage

### Secondary (MEDIUM confidence)

- [Building Nested Menu Systems in aiogram](https://mastergroosha.github.io/telegram-tutorial-2/levelup/) — Menu state patterns
- [Role-Based Access Control Patterns](https://auth0.com/docs/manage-users/access-control) — RBAC design patterns
- [Database-Driven Bot Content](https://dev.to/codesphere/building-a-telegram-bot-with-database-driven-content-3m1a) — Content CRUD patterns
- [Telegram Bot Notification Patterns](https://www.twilio.com/blog/notifications-telegram-bot) — Async notifications

### Tertiary (LOW confidence)

- [Menu Navigation Patterns](https://surikov.dev/telegram-bot-nested-menus/) — State hierarchy (needs validation for 3-level limit)
- [Notification UX Best Practices](https://www.nngroup.com/articles/notification-ux/) — User experience (needs real-world validation)

---
*Research completed: 2026-01-24*
*Ready for roadmap: yes*
*Subsequent milestone: v1.1 building on v1.0 (LucienVoiceService)*
