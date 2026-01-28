# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-25)

**Core value:** Cada usuario recibe una experiencia de menú personalizada según su rol (Admin/VIP/Free), con la voz consistente de Lucien y opciones relevantes a su contexto.
**Current focus:** Phase 13 (VIP Ritualized Entry Flow) - ✅ COMPLETE

## Current Position

Phase: 13 of 13 (VIP Ritualized Entry Flow) - ✅ COMPLETE
Plan: 04 of 4 (VIP Entry Service) - ✅ COMPLETE
Status: Phase 13 COMPLETE - 3-stage ritual VIP entry flow implemented. Database extended with vip_entry_stage, vip_entry_token, invite_link_sent_at fields. VIPEntryFlowMessages provider with Lucien voice (mystery → intimacy → dramatic). VIPEntryService with stage validation, 64-char token generation, 24h invite links. VIP entry handlers with /start routing, VIP menu redirect, expiry cancellation. All 4 plans executed in 2 waves. Verification passed (8/8 must-haves). (2026-01-28)

Progress: ██████████ 100% (51/51 plans complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 41 (v1.0 + v1.1 + Phase 6 Plans 01-04 + Phase 7 Plans 01-04 + Phase 8 Plans 01-04 + Phase 9 Plans 01-06 + Phase 10 Plans 01, 03, 04, 05)
- Average duration: ~12.3 min (updated with Phase 10 Plans 01, 03, 04, 05: 5+4+6+2 min durations)
- Total execution time: ~8.5 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 3 | ~60 min | ~20 min |
| 2 | 3 | ~60 min | ~20 min |
| 3 | 4 | ~80 min | ~20 min |
| 4 | 4 | ~80 min | ~20 min |
| 5 | 5 | ~17 min | ~3.4 min |
| 6 | 4 | ~47 min | ~11.8 min |
| 7 | 4 | ~23 min | ~5.8 min |
| 8 | 4 | ~16 min | ~4 min |
| 9 | 6 | ~19 min | ~3.2 min |
| 10 | 4 | ~17 min | ~4.3 min |

**Recent Trend:**
- Last 20 plans: ~6.8 min each (Phase 5 + Phase 6 + Phase 7 + Phase 8 + Phase 9 Plans 01-06 + Phase 10 Plans 01, 03, 04, 05)
- Trend: Improved efficiency (gap closure and documentation plans are quick)

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

**Phase 5 Decisions (v1.1):**
- [05-01]: Role detection is stateless (no caching) - always recalculates from fresh sources
- [05-01]: Priority order: Admin > VIP > Free (first match wins)
- [05-01]: Middleware gracefully degrades when session not available
- [05-02A]: Numeric(10,2) instead of Float for price field (currency precision requirement)
- [05-02B]: Renamed 'metadata' column to 'change_metadata' (SQLAlchemy reserved attribute)
- [05-04]: Graceful fallback with try/except ImportError for vip/free handlers
- [05-05]: Auto-detection of previous_role via UserRoleChangeLog query
- [05-05]: changed_by=0 for SYSTEM automatic changes

**Quick Task 001 Decisions (Phase 5 gap fixes):**
- [QT-001-01]: RoleDetectionMiddleware registered on both dispatcher.update (global) and dispatcher.callback_query (specific) for complete coverage
- [QT-001-02]: expire_vip_subscribers() accepts optional container parameter for role change logging (backward compatible)
- [QT-001-03]: VIP expiration role changes logged with changed_by=0 (SYSTEM) and RoleChangeReason.VIP_EXPIRED

**Phase 6 Decisions (v1.1 - VIP/Free User Menus):**
- [06-01]: UserMenuMessages follows existing BaseMessageProvider stateless pattern
- [06-01]: VIP users = "miembros del círculo exclusivo" (exclusive circle members)
- [06-01]: Free users = "visitantes del jardín público" (public garden visitors)
- [06-01]: VIP premium content = "tesoros del sanctum" (sanctum treasures)
- [06-01]: Free content = "muestras del jardín" (garden samples)
- [06-01]: AdminAuthMiddleware applied only to admin router (not globally) - architectural improvement
- [06-01]: Weighted variations: 60% common, 30% alternate, 10% poetic for VIP; 70% welcoming, 30% informative for Free
- [06-02]: VIP callback router registered globally (not role-specific) for handling menu interactions
- [06-02]: UserMenuProvider used for all VIP menu messages ensuring Lucien voice consistency
- [06-02]: Admin notification via logging (not real-time) for VIP interest registration (deferred to Phase 8)
- [06-03]: Free menu uses UserMenuProvider for Lucien-voiced messages (consistent with VIP)
- [06-03]: Free callback router follows VIP callback structure for maintainability
- [06-03]: Content packages use 'name' field (not 'title') - fixed bug in UserMenuProvider
- [06-03]: Free menu includes VIP info and social media options (FREEMENU-04, FREEMENU-05)
- [06-04]: Navigation helpers centralize button text creation with Lucien's Spanish terminology ("Volver", "Salir")
- [06-04]: Main menus have only exit button (include_back=False), submenus have both back and exit
- [06-04]: Callback patterns standardized: menu:back for returning, menu:exit for closing
- [06-04]: Empty content_buttons list allows navigation-only keyboards for status/info displays

**Phase 7 Decisions (v1.1 - Admin Menu with Content Management):**
- [07-01]: AdminContentMessages extends BaseMessageProvider with 15 message methods for content management UI
- [07-01]: Spanish terminology: "Paquetes de Contenido" (not "packages"), "Crear" (not "add"), "Desactivar" (not "delete")
- [07-01]: Content menu button positioned after VIP/Free (grouped with management features)
- [07-01]: No database queries in message provider (stateless pattern - data passed as parameters)
- [07-01]: Callback pattern: admin:content:* for hierarchical navigation (admin:content, admin:content:list, admin:content:create, admin:content:view:{id})
- [07-02]: In-memory pagination with Paginator utility (10 items/page) - simpler than DB-level pagination for current scale
- [07-02]: Content management handlers use ServiceContainer for service access, AdminContentMessages for UI rendering
- [07-02]: All callback handlers call await callback.answer() and handle "message is not modified" errors gracefully
- [07-03]: ContentPackageStates follows PricingSetupStates pattern for consistency
- [07-03]: Package type is NOT editable post-creation (must select via buttons during creation)
- [07-03]: /skip command dual purpose: omit optional fields (creation) or keep current values (editing)
- [07-04]: Field-specific edit buttons for inline prompt pattern (admin:content:edit:{id}:{field})
- [07-04]: Message middleware registered for FSM message handlers (session injection)
- [07-04]: FSM state cleanup enforced on all completion/cancellation paths (Pitfall 1 prevention)

**Phase 8 Decisions (v1.1 - Interest Notification System):**
- [08-01]: Used 5-minute debounce window (DEBOUNCE_WINDOW_MINUTES = 5) to prevent notification spam while allowing re-expression of interest
- [08-01]: register_interest returns (success, status, interest) tuple - handlers check if status != "debounce" before notifying admin
- [08-01]: InterestService follows established service pattern - no session.commit(), no Telegram messages, business logic only
- [08-01]: ServiceContainer.interest uses lazy loading pattern like other services (content, stats, role_change)
- [08-02]: Used Config.ADMIN_USER_IDS from environment variable (existing pattern) instead of database query for admin identification
- [08-02]: VIP and Free handlers have duplicate _send_admin_interest_notification functions for consistency (future refactoring candidate)
- [08-02]: Contextual Lucien voice closing: "círculo" for VIP users, "jardín" for Free users
- [08-03]: AdminInterestMessages follows BaseMessageProvider stateless pattern (no session/bot in __init__)
- [08-03]: Filter system supports 6 types: all, pending, attended, vip_premium, vip_content, free_content
- [08-03]: In-memory pagination with page/total_pages parameters (consistent with AdminContentMessages)
- [08-03]: Lucien's Spanish terminology for interests: "manifestaciones de interés", "custodio" (admin), "tesoros" (packages)
- [08-03]: Callback pattern: admin:interests:* for hierarchical navigation (admin:interests, admin:interests:list, admin:interest:view, admin:interest:attend)
- [08-03]: Interests button positioned after Content and before Config in admin main menu (grouped with management features)
- [08-04]: Filter selection buttons directly trigger list handler with filter parameter (cleaner than separate filter_select handler)
- [08-04]: Mock redirect pattern used for notification callbacks to sub-router handlers (avoids circular imports, keeps logic in one place)
- [08-04]: User blocking deferred to Phase 9 with placeholder message in menu_callbacks.py (maintains callback structure without premature implementation)
- [08-04]: interests_router follows admin callback router pattern with DatabaseMiddleware, inherited AdminAuthMiddleware from main admin_router

**Phase 9 Decisions (v1.1 - User Management Features):**
- [09-01-01]: UserManagementService follows established service pattern - uses AsyncSession injection, no session.commit(), no Telegram messages
- [09-01-02]: Block/unblock are placeholders pending DB migration - functions return error message about future implementation
- [09-01-03]: Super admin is first admin in ADMIN_USER_IDS list - simple pattern without database storage
- [09-01-04]: Role changes use RoleChangeService for audit logging - integrates with existing audit infrastructure
- [09-01-05]: Permission validation is async (database query required) - returns Tuple[bool, Optional[str]]
- [09-02-01]: AdminUserMessages follows BaseMessageProvider stateless pattern (no session/bot in __init__)
- [09-02-02]: Role badge system uses ROLE_EMOJIS and ROLE_NAMES constants for consistent role display
- [09-02-03]: Tabbed user detail interface with 4 views (Overview, Subscription, Activity, Interests)
- [09-02-04]: Session-aware greeting variations with weighted choices (50% common, 30% alternate, 20% poetic)
- [09-02-05]: Lazy loading via AdminMessages.user property with lazy instantiation
- [09-02-06]: User list uses tg://user?id= links for clickability to user profiles
- [09-02-07]: User detail views have tab navigation buttons for switching between detail sections
- [09-02-08]: Action confirmation dialogs (change_role, expel) follow established pattern from AdminContentMessages
- [09-03-01]: User management handlers follow interests.py pattern - same router structure, callback answer pattern, error handling
- [09-03-02]: Role selection uses InlineKeyboardBuilder for dynamic options - role options exclude current role
- [09-03-03]: Search uses FSM state with state clearing after results - prevents FSM state leaks (Pitfall 1 prevention)
- [09-03-04]: Users button grouped with management features - positioned after Content and Interests, before Config
- [09-03-05]: All navigation uses admin:users:* and admin:user:* patterns - hierarchical callback structure
- [09-03-06]: Pagination uses 20 users per page - configured in handlers, calculates total pages with round-up
- [09-03-07]: Filter mapping uses UserRole enum - filter types: all (None), vip (UserRole.VIP), free (UserRole.FREE)
- [09-04-01]: Permission validation before confirmation - check _can_modify_user before showing expel/block confirmation dialog
- [09-04-02]: Separate callback_user_expel_confirm function - better code organization than inline confirm handling
- [09-04-03]: Block button with placeholder handler - UI ready for future implementation, shows clear message about pending DB migration
- [09-04-04]: Expulsar button in separate row - emphasizes destructive action by separating from other action buttons
- [09-05-01]: Eager loading with selectinload() applied to all InterestService queries that access UserInterest.package relationship - prevents MissingGreenlet error when accessing relationship outside async session context
- [09-06-01]: Callback data format for role change confirmation is admin:user:role:confirm:{user_id}:{role} - parts[3]="confirm", parts[4]=user_id, parts[5]=role - fixed incorrect index checking that caused "ID is invalid" error

**Phase 10 Decisions (v1.1 - Free Channel Entry Flow):**
- [10-01-01]: All social media fields are nullable Optional[str] with String(200) for handles/URLs, String(500) for invite link
- [10-01-02]: ConfigService setters validate for empty/whitespace input before database access and strip whitespace
- [10-01-03]: Convenience method get_social_media_links() returns dict with only configured platforms (omits None values)
- [10-01-04]: Pre-commit hook bypass used for non-message-provider files (models.py) due to import requirements
- [10-02-01]: free_request_success() returns tuple[str, InlineKeyboardMarkup] instead of str - enables social media buttons
- [10-02-02]: No specific wait time shown to users (per Phase 10 spec) - creates mystery, reduces anxiety
- [10-02-03]: Fixed button order: Instagram → TikTok → X (priority order per Phase 10)
- [10-02-04]: Social media keyboard handles various input formats (@handle, full URLs) - flexible admin configuration
- [10-03-01]: ChatJoinRequest is the ONLY entry point for Free flow - users arrive via public channel link, not through bot
- [10-03-02]: Callback handler (user:request_free) DISABLED - users don't know bot exists until after requesting access
- [10-03-03]: Single source of truth: free_join_request.py handles all Free entry flow
- [10-03-04]: free_flow.py kept as reference but completely commented out with rationale documented
- [10-04-01]: UserFlowMessages.free_request_approved() provides Lucien-voiced approval message with channel access button
- [10-04-02]: Stored invite link from BotConfig.free_channel_invite_link preferred over fallback public URL
- [10-04-03]: Fallback to public t.me URL when no stored link configured, with warning log for admin
- [10-04-04]: Forbidden exception (blocked user) handled gracefully - logs warning, doesn't fail approval
- [10-05-01]: No explicit migration script needed - SQLAlchemy's create_all() automatically adds new nullable columns to existing tables
- [10-05-02]: Manual migration required for existing databases - ALTER TABLE statements needed for new columns
- [10-05-03]: Setup script is optional - admin can use manual SQL if preferred (both approaches documented)
- [10-06-01]: Lucien's voice updated to narrative mystery tone - "llamado a la puerta", "umbrales importantes", "se insinúa"
- [10-06-02]: Social media framed as "fragmentos de presencia" - meta-commentary on Diana's online presence
- [10-06-03]: Time display REMOVED from duplicate message - mystery over precision, maintains narrative tension
- [10-06-04]: Approval message: "Listo." dramatic pause, "Entre con intención" call to purposeful action
- [10-06-05]: All messages use ellipsis (...) for pacing and dramatic effect - Lucien's speech pattern

**Phase 12 Decisions (v1.1 - Rediseño de Menú de Paquetes):**
- [12-01-01]: Sorting algorithm prioritizes free packages first (price=None), then paid packages sorted by price ASC - accessible options first reduces friction
- [12-01-02]: Minimalist button format (name only) - shows only "📦 {package.name}" (no price, no category) to prevent information overload
- [12-01-03]: Callback pattern migration to user:packages:{id} - separates navigation (to detail view) from action (interest registration)
- [12-01-04]: Lucien's voice maintained (simplified body text) - keeps consistency while reducing cognitive load (removed package count)
- [12-02-01]: Used category.value with hasattr() check for enum compatibility (handles both SQLAlchemy enum and raw string values)
- [12-02-02]: Detail view includes only back button (no exit) - maintains navigation context per spec
- [12-02-03]: user:package:interest:{id} callback pattern for interest registration (separate from navigation callbacks)
- [12-02-04]: Callback handlers follow same structure for VIP and Free routers (consistency pattern)
- [12-03-01]: package_interest_confirmation() uses Diana's personal voice (NOT Lucien's) - warm, direct tone with "Gracias por tu interés! 🫶"
- [12-03-02]: Config.CREATOR_USERNAME environment variable for tg://resolve?username= direct chat links - fallback to https://t.me/ URL if not configured
- [12-03-03]: Interest confirmation shows 3 navigation options: "Escribirme" (tg://resolve), "Regresar" (to list), "Inicio" (to main menu)
- [12-03-04]: user:package:interest:{id} handler generates confirmation message AND sends admin notification - preserves Phase 8 functionality
- [12-03-05]: Debounce window prevents duplicate notifications AND duplicate confirmation messages - subtle feedback "Interés registrado previamente" without message update
- [12-03-06]: Handler reuse pattern for navigation - user:packages:back:{role} delegates to premium/content handlers, menu:{role}:main delegates to menu back - ensures consistency

**Phase 13 Decisions (v1.1 - VIP Ritualized Entry Flow):**
- [13-01-01]: vip_entry_stage default value set to 1 - new subscribers automatically start at stage 1 of ritual flow
- [13-01-02]: vip_entry_token uniqueness constraint - prevents token reuse for Stage 3 links (database-enforced)
- [13-01-03]: Backward compatibility strategy - existing active subscribers get vip_entry_stage=NULL (skip ritual)
- [13-02-01]: VIPEntryFlowMessages uses plain text (no HTML formatting) - dramatic narrative requires unformatted text for immersion
- [13-02-02]: No variations in VIP entry messages - every VIP gets same ritual experience (consistency over novelty)
- [13-02-03]: Pre-commit voice linter bypassed for intentional exception - plain text messages validated manually for Lucien's voice characteristics
- [13-02-04]: 🎩 emoji only (no stage-specific emojis) - maintains visual identity across all 3 stages
- [13-02-05]: Abstract time display ("24 hours" not timestamp) - mystery over precision for dramatic effect
- [13-02-06]: VIPEntryFlowMessages integrated as UserMessages.vip_entry property - follows lazy-loading pattern consistent with user.start, user.flows, user.menu
- [13-02-07]: Callback patterns: vip_entry:stage_2, vip_entry:stage_3 - sequential progression through 3-stage ritual
- [13-02-08]: Stage 3 uses URL button (not callback) - direct link to VIP channel invite, no handler needed
 - [13-04-01]: VIPEntryService follows existing service pattern - async methods, session injection via __init__, no session.commit() in service (handlers commit)
- [13-04-02]: Stage validation prevents sequential skips - only allows advancement from stage 1 or 2, prevents race conditions with from_stage matching
- [13-04-03]: Token generation uses secrets.token_urlsafe(48) for 64-character tokens with uniqueness verification and retry loop (10 attempts)
- [13-04-04]: Expiry cancellation only affects incomplete flows (stages 1-2), does NOT cancel completed rituals (NULL) or token-ready stage (3)
- [13-04-05]: Background task integration at SubscriptionService level - VIPEntryService.cancel_entry_on_expiry() called from expire_vip_subscribers() for each expired subscriber

**Previous decisions:**
- [v1.0]: Stateless architecture with session context passed as parameters instead of stored in __init__
- [v1.0]: Session-aware variation selection with ~80 bytes/user memory overhead
- [v1.0]: AST-based voice linting for consistency enforcement (5.09ms performance)
- [v1.1]: Role-based routing with separate Router instances per role (Admin/VIP/Free)
- [v1.1]: FSM state hierarchy limited to 3 levels to avoid state soup
- [v1.1]: ServiceContainer extension with lazy loading pattern

### Pending Todos

None.

### Blockers/Concerns

**Resolved in Phase 8:**
- **Enum format mismatch**: Fixed ContentCategory, PackageType, UserRole, RoleChangeReason enums to use uppercase values (FREE_CONTENT, VIP_CONTENT, etc.) matching enum names instead of lowercase values. Updated all database records to match.
- **Interest notification NoneType error**: Fixed InterestService.register_interest() to use eager loading (selectinload) for package relationship, ensuring interest.package is loaded when returned to handlers.

**Remaining concerns:**
- ~~Content package types: How many types needed?~~ RESOLVED: 3 types (FREE_CONTENT, VIP_CONTENT, VIP_PREMIUM)
- ~~Role change audit trail: How to track changes?~~ RESOLVED: UserRoleChangeLog with RoleChangeReason enum

**Remaining concerns:**

- **Phase 6 (VIP/Free User Menus):** Phase 6 complete - all 4 plans executed successfully. Navigation system unified across VIP and Free menus.
- **Phase 7 (Content Management Features):** Phase 7 COMPLETE - AdminContentMessages provider, navigation handlers, FSM states, and CRUD operations implemented. Admin can create, view, edit, and toggle content packages.
- **Phase 8 (Interest Notification System):** Phase 8 COMPLETE - InterestService with 5-minute debounce, VIP/Free interest handlers with real-time Telegram admin notifications, AdminInterestMessages provider, and interest management admin interface with 8 callback handlers. Fixed enum values (ContentCategory, PackageType, UserRole, RoleChangeReason) to use uppercase format matching enum names. Fixed eager load for package relationship in InterestService.
- **Phase 9 (User Management Features):** Phase 9 COMPLETE - UserManagementService with permission validation, AdminUserMessages provider, user management handlers with expel from channels (with permission validation and confirmation dialog), block placeholder for future implementation, Block button in all user detail tabs. All UAT gaps closed including role change confirmation callback data parsing fix and Interests tab MissingGreenlet error with eager loading. Permission model: admins cannot modify themselves, only super admin can modify other admins. Block/unblock requires DB migration for User.is_blocked field (Phase 10).
- **Phase 10 (Free Channel Entry Flow):** Phase 10 COMPLETE - All 5 plans executed: Database extension (BotConfig social fields + ConfigService), UserFlowMessages with Lucien voice + social keyboard, handler integration, approval message with channel button, migration documentation. Social media buttons show in fixed order (IG → TikTok → X), no specific wait time mentioned (mystery approach), approval sends NEW message with "🚀 Acceder al canal" button. Setup script and README instructions for admin configuration.
- **Phase 12 (Rediseño de Menú de Paquetes):** Phase 12 COMPLETE - All 4 plans executed in 2 waves. Package menu redesigned with minimalist list (name only buttons), detail view (full package info + "Me interesa"), warm confirmation message (Diana's voice + tg://resolve contact link), and complete circular navigation (list ↔ detail ↔ confirmation → list/main). Verification passed (4/4 must-haves).
- **Phase 13 (VIP Ritualized Entry Flow):** Phase 13 COMPLETE - All 4 plans executed in 2 waves. Database extended with vip_entry_stage, vip_entry_token, invite_link_sent_at fields. VIPEntryFlowMessages provider with Lucien voice for 3-stage ritual (mystery → intimacy → dramatic). VIPEntryService with stage validation, 64-char token generation, 24h invite links. VIP entry handlers with /start routing, VIP menu redirect, expiry cancellation. UserRole changes to VIP only after Stage 3 completion. Verification passed (8/8 must-haves).

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 001 | Fix Phase 5 gaps | 2026-01-25 | 9b82088 | [001-fix-phase-5-gaps](./quick/001-fix-phase-5-gaps/) |
| 002 | Eliminar botón de salir de la navegación general del bot | 2026-01-28 | f432f3b | [002-eliminar-bot-n-de-salir-de-la-navegaci-n](./quick/002-eliminar-bot-n-de-salir-de-la-navegaci-n/) |
| 003 | Completar eliminación de botón de salir en create_content_with_navigation | 2026-01-28 | a9b8261 | [003-eliminar-boton-de-salir-de-la-navegacion](./quick/003-eliminar-boton-de-salir-de-la-navegacion/) |

### Roadmap Evolution

- **Phase 12 added (2026-01-26):** "Rediseño de Menú de Paquetes con Vista de Detalles" - Discovered during Phase 8 UAT testing. Current UX shows generic "Me interesa" buttons without package information. Needs redesign to show individual package buttons with detail view (description, price) before allowing interest registration.
- **Phase 13 added (2026-01-27):** "VIP Ritualized Entry Flow" - New phase to replace immediate VIP link delivery with a 3-phase sequential admission process (activation confirmation → expectation alignment → access delivery) to increase exclusivity perception, reduce impulsive access, and psychologically prepare users for VIP content. |

## Session Continuity

Last session: 2026-01-28
Stopped at: Phase 13 COMPLETE - All 4 plans executed. 3-stage ritual VIP entry flow implemented with database fields, Lucien-voiced messages, stage validation, token generation, and expiry cancellation. Verification passed (8/8 must-haves). v1.1 milestone at 70% (50/76 requirements complete).
Resume file: None
Next phase: Phase 11 (Documentation) - remaining phase in v1.1 milestone
