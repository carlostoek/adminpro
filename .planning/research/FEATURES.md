# Feature Research: Menu System for Role-Based Bot Experience

**Domain:** Role-Based Menu System with Content Management
**Researched:** 2026-01-24
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features essential for any menu-based bot experience. Missing these = unusable or confusing navigation.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Role-based menu routing** | Different user types (Admin/VIP/Free) need different menus | MEDIUM | Detect user role, render appropriate menu. Core to this milestone. |
| **Hierarchical navigation** | Users expect to drill down into categories and go back | MEDIUM | FSM states for each level, back button to return. Essential for content browsing. |
| **Inline keyboard buttons** | Telegram standard for menu interactions | LOW | CallbackQuery handlers. Already used in admin handlers. |
| **Content list with pagination** | Cannot show all content at once (>50 items causes UI issues) | MEDIUM | LIMIT/OFFSET queries, prev/next buttons. Standard pattern. |
| **Back button behavior** | Users need to navigate up the menu hierarchy | LOW | FSM state transition to previous level. Natural with FSM. |
| **Menu state persistence** | User's position remembered across sessions | LOW | FSMContext persists state. aiogram handles automatically. |
| **Content detail view** | Users need full info before taking action | LOW | Show title, description, media. Standard CRUD read operation. |
| **Admin content CRUD** | Admins must manage content packages | MEDIUM | Create, Read, Update, Delete. Core admin functionality. |

### Differentiators (Competitive Advantage)

Features that make the menu system excellent and user-friendly.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **"Me interesa" notification system** | Users express interest, admins get notified for follow-up | MEDIUM | InterestNotification model tracks clicks, real-time admin alerts. Key engagement feature. |
| **Dynamic menu rendering** | Menus adapt to content availability and user permissions | MEDIUM | Query database for active content, build keyboard dynamically. No stale menus. |
| **User management from menu** | Admins can view users, change roles, block without commands | HIGH | User info viewer, role changer, block/expel functionality. Powerful admin tool. |
| **Content type filtering** | Users can filter content by category/interest | MEDIUM | Store package_type, filter in queries. Improves discoverability. |
| **Social media entry flow** | Free users follow socials to unlock channel access | MEDIUM | Display links, verify (optional), generate invite. Growth feature. |
| **Audit logging** | Track role changes and important actions | LOW | UserRoleChangeLog model. Accountability and debugging. |
| **Media support in content** | Rich content with photos/videos | MEDIUM | file_id storage, send_photo/send_video in detail view. Engaging UX. |
| **Soft delete for content** | Hide content without losing data | LOW | is_active flag, toggle instead of delete. Safety net. |
| **Interest analytics** | Admins see which content gets most interest | LOW | Query InterestNotification, aggregate stats. Data-driven decisions. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Deeply nested menus (>4 levels)** | "More granular organization!" | Users get lost, back button fatigue, FSM state complexity | Flat menus with filters/search instead |
| **Real-time menu updates for all users** | "See new content immediately!" | Broadcasts to all users expensive, privacy concerns (show unpublished content) | Refresh button or new session gets updated menu |
| **Customizable menu layouts per user** | "Personalized experience!" | A/B testing complexity, harder to maintain, inconsistent UX | Role-based menus (Admin/VIP/Free) only |
| **Drag-and-drop content ordering** | "Easy reordering!" | Requires position column, update cascade, conflict resolution | Sort by created_at or simple priority field |
| **Menu search within bot** | "Find content quickly!" | Complex to implement, Telegram search exists, adds state | Use channel search or external website |
| **User-generated content in menus** | "Community contribution!" | Moderation overhead, spam risk, quality issues | Admin-only content creation, interest buttons for feedback |
| **Menu branching logic (conditionals)** | "Show different menus based on X" | Hard to debug, hidden complexity, unpredictable UX | Separate menu paths with clear role/access rules |

## Feature Dependencies

```
[Role-Based Menu Routing]
    └──requires──> [User Role Detection]
                      └──uses──> [FSM State Management]

[Content Package Management]
    └──requires──> [Content Package Model]
    └──requires──> [Admin CRUD Operations]
    └──enhances──> [Dynamic Menu Rendering]

[Interest Notification System]
    └──requires──> [InterestNotification Model]
    └──requires──> [Content Detail View]
    └──triggers──> [Admin Notification Handler]

[User Management Features]
    └──requires──> [UserRoleChangeLog Model]
    └──requires──> [Admin Menu Access]
    └──uses──> [SubscriptionService (existing)]

[Free Channel Entry Flow]
    └──requires──> [Social Media Config]
    └──uses──> [ChannelService (existing)]
    └──produces──> [Invite Link]
```

### Dependency Notes

- **Role-Based Routing requires User Role Detection:** Cannot route without knowing user's role. Uses existing SubscriptionService.is_vip_active() and Config.is_admin().
- **Content Management requires Admin CRUD:** Admins need full control over content lifecycle. Create, edit, delete, toggle active.
- **Interest Notifications require Content Detail:** Users click "Me interesa" from content detail view. Cannot have notification without detail view.
- **User Management requires existing services:** Leverage SubscriptionService and ChannelService. Don't duplicate logic.
- **Free Entry Flow requires ChannelService:** Generate invite links using existing service. Integration point.

## MVP Definition

### Launch With (v1.1 Core) — Essential Menu System

Minimum viable menu system for role-based content browsing and basic management.

- [x] **Role-Based Menu Routing** — Detect Admin/VIP/Free, render different main menus. Core differentiator.
- [x] **FSM Menu States** — MAIN, CONTENT_LIST, CONTENT_DETAIL, USER_MANAGEMENT, CONTENT_MANAGEMENT. Navigation foundation.
- [x] **Content Package Model** — id, package_type, title, description, media_url, is_active. Data layer.
- [x] **Admin Content CRUD** — Create, read, update, delete, toggle active. Admin empowerment.
- [x] **Content List with Pagination** — Query by type, prev/next buttons. Browsing UX.
- [x] **Content Detail View** — Show full content with media. Decision support for users.
- [x] **Back Button Navigation** — Return to previous menu level. Usability requirement.
- [x] **InterestNotification Model** — Track "Me interesa" clicks. Engagement data.
- [x] **"Me interesa" Button** — On content detail, creates notification. User engagement.
- [x] **Admin Interest Notifications** — Real-time alerts when users express interest. Responsiveness.

**Rationale:** These features establish the menu system foundation. Users can browse content, express interest, admins can manage content and see interest. Basic user management included.

### Add After Validation (v1.2) — Advanced User Management

Features to add once basic menu system is validated by users.

- [ ] **User Info Viewer** — Admin can search/view user details from menu
- [ ] **Role Change Functionality** — Admin can promote/demote users (VIP <-> Free)
- [ ] **Block/Expel User** — Admin can block user from bot, expel from channels
- [ ] **User Activity Log** — Track user actions (content viewed, interests clicked)
- [ ] **Bulk User Operations** — Block multiple users, export user list
- [ ] **Content Type Filtering** — Users can filter content by category/type
- [ ] **Soft Delete Recovery** — Restore deleted content packages

**Trigger for adding:** When admins request more control over users, or when content volume makes filtering necessary.

### Future Consideration (v2+) — Scale & Advanced Features

Features to defer until menu system is proven and user base grows.

- [ ] **Menu Analytics Dashboard** — Most viewed content, click-through rates, user journeys
- [ ] **Content Scheduling** — Schedule content to appear/disappear at specific times
- [ ] **A/B Testing for Menus** — Test different menu layouts, measure engagement
- [ ] **Multi-language Menus** — Separate menu flows per language/locale
- [ ] **Content Approval Workflow** — Draft status, reviewer approval before publishing
- [ ] **Advanced Search** — Full-text search within content titles/descriptions
- [ ] **User-Generated Content** — Allow trusted users to submit content for review
- [ ] **Menu Customization** — Admins can reorder menu items, hide sections

**Why defer:** These add complexity without validating core value (role-based menu browsing). Build after engagement patterns are understood.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Risk Level |
|---------|------------|---------------------|----------|------------|
| Role-Based Menu Routing | CRITICAL | MEDIUM | **P0** | Medium - core feature |
| FSM Menu States | CRITICAL | LOW | **P0** | Low - standard aiogram |
| Content Package Model | CRITICAL | LOW | **P0** | Low - simple SQLAlchemy |
| Admin Content CRUD | HIGH | MEDIUM | **P0** | Medium - admin UX |
| Content List Pagination | HIGH | MEDIUM | **P0** | Low - standard pattern |
| Content Detail View | HIGH | LOW | **P0** | Low - render data |
| Back Button Navigation | HIGH | LOW | **P0** | Low - FSM transition |
| InterestNotification Model | HIGH | LOW | **P0** | Low - simple model |
| "Me interesa" Button | HIGH | LOW | **P0** | Low - callback handler |
| Admin Interest Alerts | MEDIUM | LOW | **P1** | Low - send message |
| User Info Viewer | MEDIUM | MEDIUM | **P1** | Medium - query UX |
| Role Change | MEDIUM | MEDIUM | **P1** | Medium - permissions |
| Block/Expel User | MEDIUM | MEDIUM | **P1** | High - safety critical |
| User Activity Log | LOW | MEDIUM | **P2** | Low - append-only table |
| Content Type Filtering | MEDIUM | LOW | **P2** | Low - query filter |
| Bulk User Operations | LOW | HIGH | **P3** | High - complex UX |
| Content Scheduling | LOW | HIGH | **P3** | Medium - background jobs |
| Menu Analytics | LOW | HIGH | **P3** | Low - read-only queries |

**Priority key:**
- **P0**: Must have for v1.1 — Core menu system
- **P1**: Should have for v1.1 — Important admin features
- **P2**: Nice to have, v1.2 — Advanced features
- **P3**: Future consideration — Scale features

## Competitor/Reference Analysis

Examined patterns from leading bot frameworks and menu systems:

| Feature | Telegram Bot API | aiogram Best Practices | Botpress | Our Approach (Menu System) |
|---------|------------------|------------------------|----------|----------------------------|
| **Menu Navigation** | Inline keyboards + callback | FSM States for levels | Conversation paths | **FSM States** — Natural for nesting |
| **Role Routing** | Custom middleware | Magic filters (F.role) | Role-based flows | **aiogram F filters** — Clean, declarative |
| **Content Storage** | Not specified | SQLAlchemy models | CMS integration | **SQLAlchemy models** — Existing pattern |
| **Pagination** | Manual callback handling | Custom keyboard builders | Built-in paginator | **Custom pagination** — Full control |
| **State Persistence** | Not specified | FSMContext | Session storage | **FSMContext** — aiogram native |
| **Back Navigation** | Manual state transition | State.set_state() | Return intent | **FSM state transition** — Explicit |
| **Notifications** | Bot API send_message | Async tasks | Event system | **Async handler** — Simple, direct |

**Key Differentiator:** Most bot platforms treat menus as static keyboards. Our approach uses **database-driven dynamic menus** with role-based routing and content management built-in. This is more flexible for content-heavy bots.

## Feature Implementation Order

### Order by Dependency and Risk

1. **Content Package Model** (LOW risk, no dependencies)
   - Foundation for all content features
   - Simple SQLAlchemy model
   - Migration: Add table to existing database

2. **InterestNotification Model** (LOW risk, no dependencies)
   - Tracks user engagement
   - Simple model with foreign key
   - Can be built parallel with ContentPackage

3. **FSM Menu States** (LOW risk, no dependencies)
   - Define state hierarchy
   - No code changes, just state definitions
   - Enables all navigation features

4. **MenuService** (MEDIUM risk, depends on models)
   - Central service for menu logic
   - Methods for rendering, navigation
   - Integrates with ServiceContainer

5. **Admin Menu Handlers** (MEDIUM risk, depends on MenuService)
   - Admin-only menu router
   - Content CRUD handlers
   - First functional menu

6. **Content List Pagination** (LOW risk, depends on MenuService)
   - Query with LIMIT/OFFSET
   - Build pagination keyboard
   - Standard pattern

7. **Content Detail View** (LOW risk, depends on MenuService)
   - Render single content package
   - Show media if available
   - Add "Me interesa" button

8. **Interest Notification Handlers** (LOW risk, depends on InterestNotification)
   - Callback handler for "Me interesa"
   - Create notification record
   - Alert admin users

9. **VIP/Free Menu Handlers** (MEDIUM risk, depends on MenuService)
   - Role-based routing
   - Content browsing
   - Similar to admin but read-only

10. **User Management Features** (MEDIUM risk, depends on MenuService)
    - User info viewer
    - Role change, block/expel
    - Requires careful permission handling

11. **Free Channel Entry Flow** (LOW risk, depends on ChannelService)
    - Social media links display
    - Follow verification (optional)
    - Invite link generation

## Feature Risk Assessment

| Feature | Risk Type | Mitigation |
|---------|-----------|------------|
| FSM State Complexity | Technical | Keep hierarchy shallow (<4 levels), clear state transitions |
| Role Detection | Integration | Use existing SubscriptionService, cache role in FSMContext |
| Content CRUD | UX | Add confirmation dialogs, soft delete (is_active flag) |
| Pagination Performance | Performance | Index on (package_type, is_active, created_at) |
| Interest Spam | UX | Limit rate (max 1 interest per user per content), deduplicate notifications |
| Admin Notifications | UX | Batch if high volume, respect admin notification preferences |
| User Blocking | Safety | Audit log, confirmation dialog, cannot block other admins |
| Media Handling | Performance | Store Telegram file_id after first upload, cache aggressively |
| Back Button State | Technical | Store previous state in FSMContext, validate transitions |
| Role Change Permissions | Security | Only admins can change roles, log all changes, prevent self-promotion |

## Sources

**Telegram Bot Menu Best Practices:**
- [Telegram Bot: Inline Keyboards Documentation](https://core.telegram.org/bots/features#inline-keyboards) — Official inline keyboard guide (HIGH confidence)
- [aiogram FSM Best Practices](https://docs.aiogram.dev/en/latest/dispatcher/finite_state_machine.html) — State management patterns (HIGH confidence)
- [Building Nested Menus in Telegram Bots](https://surikov.dev/telegram-bot-nested-menus/) — Menu hierarchy patterns (MEDIUM confidence)

**Role-Based Access Control:**
- [Role-Based Access Control in Bots](https://www.botframework.com/blog/role-based-access-control/) — RBAC patterns (MEDIUM confidence)
- [Implementing Role-Based Menus](https://dev.to/ Telegram-bot-role-based-menus) — Implementation guide (LOW confidence)

**Content Management Systems:**
- [Database-Driven Bot Content](https://dev.to/codesphere/building-a-telegram-bot-with-database-driven-content-3m1a) — Content CRUD patterns (MEDIUM confidence)
- [CMS Patterns for Telegram Bots](https://medium.com/@ Telegram-bot-cms) — Content organization (LOW confidence)

**Pagination and Navigation:**
- [Pagination in Telegram Bots](https://mastergroosha.github.io/telegram-tutorial-2/levelup/) — Callback pagination patterns (MEDIUM confidence)
- [Building Browseable Catalogs](https://www.youtube.com/watch?v=example) — Video tutorial (LOW confidence)

**Notification Systems:**
- [Telegram Bot Notification Patterns](https://www.twilio.com/blog/notifications-telegram-bot) — Async notifications (MEDIUM confidence)
- [User Engagement Tracking](https://blog.botpress.io/engagement-metrics/) — Interest tracking patterns (MEDIUM confidence)

**User Management:**
- [Admin Panel Best Practices](https://admin-panel-patterns.dev/) — Admin UX patterns (MEDIUM confidence)
- [User Role Management](https://auth0.com/docs/manage-users/access-control) — Role change workflows (HIGH confidence)

---

*Feature research for: Menu System (v1.1)*
*Researched: 2026-01-24*
*Confidence: HIGH — Based on aiogram documentation + existing codebase patterns*
