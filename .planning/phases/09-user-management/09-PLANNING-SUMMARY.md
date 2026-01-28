# Phase 9: User Management Features - Planning Summary

**Phase:** 09 - User Management Features
**Status:** 📋 Planning Complete - Ready for Execution
**Plans Created:** 4 (09-01 through 09-04)
**Date:** 2026-01-26

## Overview

Phase 9 enables administrators to manage users through a comprehensive interface including:
- Viewing detailed user profiles with tabbed interface (Overview, Subscription, Activity, Interests)
- Changing user roles (Free ↔ VIP ↔ Admin) with audit logging
- Expelling users from channels (VIP and Free)
- Placeholder for block/unblock functionality (requires database migration)
- Search and filter users by role
- Permission boundaries (super admin only can modify other admins, no self-actions)

## Plans Summary

### Wave 1: User Management Service (09-01)
**File:** `bot/services/user_management.py`
**Lines:** ~400+
**Methods:** 10+ async methods

Key Components:
- `get_user_info()` - Detailed user profile with subscription, interests, role changes
- `change_user_role()` - Role changes with RoleChangeService audit logging
- `block_user()` / `unblock_user()` - Placeholders for future implementation
- `expel_user_from_channels()` - Uses bot.ban_chat_member for VIP/Free channels
- `get_user_list()` - List users with role filter and pagination
- `search_users()` - Search by username or user_id
- `is_super_admin()` - Checks Config.ADMIN_USER_IDS[0]
- `_can_modify_user()` - Permission validation (self-action, admin-on-admin)
- `get_user_role()` - Get user's current role

### Wave 2: Admin User Messages (09-02)
**File:** `bot/services/message/admin_user.py`
**Lines:** ~300+
**Methods:** 13+ message methods

Key Components:
- `users_menu()` - Main menu with user counts
- `users_list()` - Paginated list with role badges (👑 Admin, 💎 VIP, 👤 Free)
- `user_detail_overview()` - Tab 1: Basic user info
- `user_detail_subscription()` - Tab 2: VIP subscription status
- `user_detail_activity()` - Tab 3: Role change history
- `user_detail_interests()` - Tab 4: User's registered interests
- `change_role_confirm()` - Before/after role display
- `expel_confirm()` - Explanation of expulsion action
- `user_search_prompt()` / `user_search_results()` - Search UI
- `action_error()` - Error messages

### Wave 3: User Management Handlers (09-03)
**File:** `bot/handlers/admin/users.py`
**Lines:** ~350+
**Handlers:** 10+ callback handlers

Key Components:
- Navigation handlers (menu, list, page, filters)
- Search flow (FSM state: UserManagementStates.searching_user)
- User detail view with tab support (overview, subscription, activity, interests)
- Role change with selection dialog and confirmation
- Permission validation for all actions
- Integration with admin router

Callback Pattern:
- `admin:users` - Main menu
- `admin:users:list:{filter}` - List with filter (all, vip, free)
- `admin:users:page:{page}:{filter}` - Pagination
- `admin:users:search` - Search prompt
- `admin:user:view:{id}:{tab}` - Detail view with tabs
- `admin:user:role:{id}` - Role change dialog
- `admin:user:role:confirm:{id}:{role}` - Execute role change
- `admin:users:filters:{current}` - Filter selection

### Wave 4: Expel and Block Handlers (09-04)
**File:** `bot/handlers/admin/users.py` (additional)
**Lines:** ~150+ (additional)

Key Components:
- `callback_user_expel()` - Show confirmation dialog
- `callback_user_expel_confirm()` - Execute expulsion
- `callback_user_block()` - Placeholder for future implementation

Callback Pattern:
- `admin:user:expel:{id}` - Show expel confirmation
- `admin:user:expel:confirm:{id}` - Execute expel
- `admin:user:block:{id}` - Show placeholder message

## Permission Boundaries

### Super Admin Concept
- First admin in `Config.ADMIN_USER_IDS` list is the super admin
- Only super admin can modify other admins
- Implemented in `is_super_admin()` method

### Self-Action Prevention
- Admins cannot block or expel themselves
- Admins cannot change their own role
- Validated in `_can_modify_user()` method

### Admin-on-Admin Rules
- Non-super-admins receive error when trying to modify other admins
- Generic error message: "Solo el super admin puede modificar otros administradores"

## Technical Patterns

### Service Pattern
- Lazy loading via ServiceContainer
- Stateless (no session/bot storage in service)
- Returns tuples (success, message) for actions
- Uses RoleChangeService for audit logging
- No session.commit() calls

### Message Provider Pattern
- Extends BaseMessageProvider
- Stateless (no session/bot in __init__)
- Returns Tuple[str, InlineKeyboardMarkup]
- Uses Lucien's voice (custodio, círculo exclusivo, jardín)
- Role badges with emojis (👑 Admin, 💎 VIP, 👤 Free)

### Handler Pattern
- Separate router (users_router) included in admin_router
- DatabaseMiddleware for session injection
- AdminAuthMiddleware inherited from admin_router
- Callback handlers call callback.answer()
- try/except for "message is not modified" errors
- FSM state for search flow

## Files Modified/Created

### Created:
- `bot/services/user_management.py` - UserManagementService
- `bot/services/message/admin_user.py` - AdminUserMessages provider
- `bot/handlers/admin/users.py` - User management handlers

### Modified:
- `bot/services/__init__.py` - Export UserManagementService
- `bot/services/container.py` - Add user_management property
- `bot/services/message/__init__.py` - Export AdminUserMessages
- `bot/services/message/lucien_voice.py` - Add admin.user property
- `bot/handlers/admin/main.py` - Include users_router
- `bot/handlers/admin/menu.py` - Add Users button to admin menu
- `bot/states/admin.py` - Add UserManagementStates

## Key Decisions

1. **Block/Unblock as Placeholder**: Requires database migration to add `User.is_blocked` field. Plan shows placeholder message explaining feature is planned for future version.

2. **Super Admin Concept**: First admin in `Config.ADMIN_USER_IDS` is super admin. Simple, clear permission model.

3. **Tabbed Interface**: User profile has 4 tabs (Overview, Subscription, Activity, Interests) for organized information display.

4. **Role Badges**: Emoji badges for visual clarity in user lists (👑 Admin, 💎 VIP, 👤 Free).

5. **Permission Validation**: Centralized in `_can_modify_user()` method, called before any administrative action.

6. **Audit Logging**: All role changes logged via RoleChangeService with changed_by field.

## Success Criteria

1. ✅ Admin can open "Gestión de Usuarios" menu
2. ✅ Admin can view detailed user information with tabs
3. ✅ Admin can change user role with confirmation
4. ✅ Admin can expel user from channels with confirmation
5. ✅ Admin receives error for self-actions
6. ✅ Non-super-admin receives error when modifying admins
7. ✅ Block/unblock show placeholder message
8. ✅ All actions logged for audit
9. ✅ Search and filter functionality works
10. ✅ Pagination works (20 users per page)

## Dependencies

- Phase 8 (Interest Notification System) - Complete
- Config.ADMIN_USER_IDS - Environment variable pattern
- RoleChangeService - For audit logging
- ChannelService - For channel operations
- BaseMessageProvider - For message provider pattern

## Next Steps

Execute plans in order:
1. Execute 09-01-PLAN.md - UserManagementService
2. Execute 09-02-PLAN.md - AdminUserMessages
3. Execute 09-03-PLAN.md - User handlers (navigation, list, detail, role change)
4. Execute 09-04-PLAN.md - Expel and block handlers

After execution, Phase 9 will be complete and Phase 10 (Free Channel Entry Flow) can begin.

---

**Phase Status:** 📋 Plans Created - Ready for Execution
**Total Plans:** 4
**Estimated Duration:** ~16 minutes (4 min per plan based on Phase 8 average)
**Target Completion:** After execution wave
