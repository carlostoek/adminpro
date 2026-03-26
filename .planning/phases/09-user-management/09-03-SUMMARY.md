---
phase: 09
plan: 03
title: "Admin User Handlers - User Management Interface"
completed: "2026-01-26"
duration: "5 min"
status: "complete"
---

# Phase 9 Plan 3: Admin User Handlers

## Summary

Created complete user management interface with FSM states for search flow, comprehensive handler file with navigation, listing, pagination, search, tabbed user detail views, role change with confirmation, expulsion functionality, filter selection, and full integration into admin router with menu button placement following established admin handler patterns (content.py, interests.py).

## One-Liner

User management handlers (users.py) with 13 callback handlers for navigation, listing with pagination, search, tabbed detail views, role change confirmation, and expulsion using UserManagementService and AdminUserMessages.

## Artifacts Created/Modified

### bot/states/admin.py (Modified)
- Added UserManagementStates state group with searching_user state
- Placed after ContentPackageStates for logical organization

### bot/handlers/admin/users.py (Created - 487 lines)

**users_router with DatabaseMiddleware applied**

**13 Callback Handlers:**

| Handler | Callback Pattern | Purpose |
|---------|-----------------|---------|
| `callback_users_menu` | `admin:users` | Show user management menu with counts by role |
| `callback_users_list` | `admin:users:list:{filter}` | List users with filter (all, vip, free) |
| `callback_users_page` | `admin:users:page:{page}:{filter}` | Pagination (20 users per page) |
| `callback_users_search` | `admin:users:search` | Set FSM state for search prompt |
| `callback_users_search_results` | FSM state | Process search query and display results |
| `callback_user_view` | `admin:user:view:{id}:{tab}` | Tabbed user detail view (overview, subscription, activity, interests) |
| `callback_user_role` | `admin:user:role:{id}` | Show role selection dialog |
| `callback_user_role_confirm` | `admin:user:role:confirm:{id}:{role}` | Execute role change with validation |
| `callback_user_expel` | `admin:user:expel:{id}` | Show expel confirmation dialog |
| `callback_user_expel` (confirm) | `admin:user:expel:confirm:{id}` | Execute expulsion from channels |
| `callback_users_filters` | `admin:users:filters` | Show filter selection screen |
| `callback_users_menu_back` | `admin:users:menu` | Return to user management menu |
| `callback_users_noop` | `admin:users:noop` | No-op for pagination page button |

**Key Implementation Details:**
- All handlers use ServiceContainer for service access
- All handlers use AdminUserMessages for UI rendering
- All callback handlers call await callback.answer()
- Handles "message is not modified" errors gracefully with try/except
- Permission validation via UserManagementService._can_modify_user
- Role changes logged via RoleChangeService
- FSM state cleared after search results displayed

### bot/handlers/admin/main.py (Modified)
- Imported admin_users module
- Added admin_router.include_router(admin_users.users_router)
- Placed after interests router inclusion

### bot/services/message/admin_main.py (Modified)
- Added "👥 Gestión de Usuarios" button to admin main menu
- Positioned after Interests and before Config
- Callback data: admin:users

## Callback Data Patterns

**User Management:**
- `admin:users` - Main menu
- `admin:users:list:{filter}` - List with filter (all, vip, free)
- `admin:users:page:{page}:{filter}` - Pagination
- `admin:users:search` - Search prompt
- `admin:users:filters` - Filter selection
- `admin:users:menu` - Back to menu
- `admin:users:noop` - No-op for page button

**User Detail:**
- `admin:user:view:{id}:{tab}` - Detail view (overview, subscription, activity, interests)
- `admin:user:role:{id}` - Role change dialog
- `admin:user:role:confirm:{id}:{role}` - Confirm role change
- `admin:user:expel:{id}` - Expel confirmation
- `admin:user:expel:confirm:{id}` - Confirm expulsion

## Key Implementation Details

### Tabbed User Detail View
4 tabs available via callback data:
- **overview**: User info with role badge, ID, name, username, member since
- **subscription**: VIP subscription details (expiry, status, token used)
- **activity**: Role change history with reasons and timestamps
- **interests**: User interests in packages with attended/pending status

### Permission Validation
- Self-action prevention: Admins cannot modify themselves
- Admin-on-admin: Only super admin can modify other admins
- Super admin: First admin in Config.ADMIN_USER_IDS
- Validation via UserManagementService._can_modify_user

### Role Change Flow
1. Admin clicks "🔄 Cambiar Rol" from user detail
2. Shows role selection dialog (VIP, Free, Admin options excluding current role)
3. Admin selects new role
4. Shows confirmation dialog with AdminUserMessages.change_role_confirm
5. Admin confirms
6. UserManagementService.change_user_role validates permissions
7. RoleChangeService logs the change
8. Shows success message with AdminUserMessages.role_change_success

### Search Flow
1. Admin clicks "🔍 Buscar Usuario"
2. Sets FSM state UserManagementStates.searching_user
3. Shows search prompt with AdminUserMessages.user_search_prompt
4. Admin enters query (username or ID)
5. UserManagementService.search_users finds matches
6. FSM state cleared
7. Shows results with AdminUserMessages.user_search_results
8. Results have direct "Ver {name}" buttons to user profiles

### Expulsion Flow
1. Admin clicks "🚫 Expulsar" from user detail
2. Shows confirmation with AdminUserMessages.expel_confirm
3. Admin confirms
4. UserManagementService.expel_user_from_channels bans user from VIP and Free channels
5. Shows success with AdminUserMessages.expel_success

## Deviations from Plan

None - plan executed exactly as written.

## Authentication Gates

None encountered.

## Decisions Made

**[09-03-01]: User management handlers follow interests.py pattern**
- Same router structure with DatabaseMiddleware
- Same callback answer pattern
- Same error handling for "message is not modified"
- Same AdminAuthMiddleware inheritance from admin_router

**[09-03-02]: Role selection uses InlineKeyboardBuilder for dynamic options**
- Role options exclude current role (no self-role-change to same role)
- Three role buttons: VIP (💎), Free (👤), Admin (👑)
- Uses InlineKeyboardBuilder instead of AdminUserMessages (dynamic nature)

**[09-03-03]: Search uses FSM state with state clearing after results**
- UserManagementStates.searching_user set on search prompt
- State cleared after displaying results
- Prevents FSM state leaks (Pitfall 1 prevention)

**[09-03-04]: Users button grouped with management features**
- Positioned after Content and Interests
- Before Config (management vs configuration distinction)
- Maintains logical grouping in admin menu

**[09-03-05]: All navigation uses admin:users:* and admin:user:* patterns**
- Hierarchical callback structure
- Separate patterns for user list (admin:users:*) vs user detail (admin:user:*)
- Consistent with content (admin:content:*) and interests (admin:interests:*) patterns

**[09-03-06]: Pagination uses 20 users per page**
- Configured in handlers (not service)
- Consistent with plan specification
- Calculates total pages with (count + 19) // 20 for round-up

**[09-03-07]: Filter mapping uses UserRole enum**
- Filter types: all (None), vip (UserRole.VIP), free (UserRole.FREE)
- Admin role excluded from filters (not shown in user lists)
- Filter selection shows current filter for clarity

## Next Phase Readiness

**Prerequisites for 09-04 (Admin User Management Integration):**
- ✅ UserManagementService with all required methods
- ✅ User management handlers with full navigation
- ✅ FSM states for search flow
- ✅ Admin user interface with tabbed detail views
- ✅ Role change with permission validation
- ✅ Expulsion from channels functionality
- ✅ Users button in admin main menu

**Ready for:** Plan 09-04 - User Management Integration Testing and UAT

**Pending:** None - all tasks complete
