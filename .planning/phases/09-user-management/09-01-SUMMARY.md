---
phase: 09
plan: 01
title: "UserManagementService - User Info, Role Change, and Permission Validation"
completed: "2026-01-26"
duration: "5 min"
status: "complete"
---

# Phase 9 Plan 1: UserManagementService

## Summary

Created UserManagementService with comprehensive user management capabilities including user info retrieval, role changes with audit logging, placeholder block/unblock functionality, channel expulsion, user listing with pagination and filtering, search functionality, and robust permission validation (super admin checks, self-action prevention, admin-on-admin restrictions).

## One-Liner

UserManagementService with 10 methods for user management operations including role changes with audit logging, permission validation, and user search/listing capabilities.

## Artifacts Created

### bot/services/user_management.py (436 lines)

**UserManagementService class with methods:**

| Method | Purpose | Returns |
|--------|---------|---------|
| `get_user_info(user_id)` | Get detailed user info with VIP subscription, interests, role changes | Dict or None |
| `change_user_role(user_id, new_role, changed_by)` | Change user role with audit logging | Tuple[bool, str] |
| `block_user(user_id, blocked_by, reason)` | Block user (placeholder - needs DB migration) | Tuple[bool, str] |
| `unblock_user(user_id, unblocked_by)` | Unblock user (placeholder - needs DB migration) | Tuple[bool, str] |
| `expel_user_from_channels(user_id, expelled_by)` | Expel user from VIP/Free channels | Tuple[bool, str] |
| `get_user_list(role, limit, offset, sort_newest_first)` | List users with pagination and role filter | Tuple[List[User], int] |
| `search_users(query, limit)` | Search users by username or ID | List[User] |
| `is_super_admin(user_id)` | Check if user is super admin | bool |
| `_can_modify_user(target_user_id, admin_user_id)` | Validate permissions (private) | Tuple[bool, Optional[str]] |
| `get_user_role(user_id)` | Get user role by ID | Optional[UserRole] |

**Permission validation rules:**
- Self-action prevention: Admins cannot modify themselves
- Admin-on-admin: Only super admin can modify other admins
- Super admin: First admin in Config.ADMIN_USER_IDS

**Audit pattern:**
- All role changes logged via RoleChangeService
- changed_by includes admin user_id (0 for SYSTEM)
- Previous role automatically detected
- change_source="ADMIN_PANEL" for manual changes

### bot/services/__init__.py
- Added UserManagementService import
- Added to __all__ exports

### bot/services/container.py
- Added _user_management_service private attribute
- Added @property user_management with lazy loading
- Updated get_loaded_services() to include "user_management"
- Fixed duplicate utility code issue

## Key Implementation Details

### User Information Structure
```python
{
    "user_id": int,
    "username": str or None,
    "first_name": str,
    "last_name": str or None,
    "role": UserRole enum,
    "created_at": datetime,
    "updated_at": datetime,
    "vip_subscription": {
        "expires_at": datetime,
        "is_active": bool,
        "token_used": str or None
    } or None,
    "interests_count": int,
    "role_changes": [
        {
            "from_role": UserRole,
            "to_role": UserRole,
            "reason": RoleChangeReason,
            "changed_by": int,
            "changed_at": datetime
        }
    ]
}
```

### Channel Expulsion Logic
- Uses ChannelService to get VIP and Free channel IDs
- Calls bot.ban_chat_member() for each channel
- Returns list of channels user was expelled from
- Handles errors gracefully (user may not be member)

### Search Functionality
- Tries to parse query as user_id (exact match)
- Falls back to username ILIKE search (%query%)
- Returns up to 10 results by default

## Deviations from Plan

None - plan executed exactly as written.

## Authentication Gates

None encountered.

## Decisions Made

**[09-01-01]: UserManagementService follows established service pattern**
- Uses AsyncSession injection (no __init__.bot storage)
- No session.commit() calls (SessionContextManager handles it)
- No Telegram message sending (service layer is business logic only)
- Logging at appropriate levels (DEBUG, INFO, WARNING, ERROR)

**[09-01-02]: Block/unblock are placeholders pending DB migration**
- Functions return error message about future implementation
- Maintains API contract for future use
- Requires User.is_blocked field to be added to schema

**[09-01-03]: Super admin is first admin in ADMIN_USER_IDS list**
- Simple pattern: Config.ADMIN_USER_IDS[0]
- No database storage of super admin status
- Relies on environment variable configuration

**[09-01-04]: Role changes use RoleChangeService for audit logging**
- Integrates with existing audit infrastructure
- Automatic previous_role detection
- Change source tagged as "ADMIN_PANEL"

**[09-01-05]: Permission validation is async (database query required)**
- _can_modify_user method fetches target user to check role
- Returns Tuple[bool, Optional[str]] for (can_modify, error_message)
- Called by all modification methods before action

## Next Phase Readiness

**Prerequisites for 09-03 (Admin User Handlers):**
- ✅ UserManagementService created with all required methods
- ✅ ServiceContainer.user_management lazy loading property
- ✅ Permission validation (_can_modify_user) implemented
- ✅ Role change audit logging via RoleChangeService
- ✅ User listing with pagination and role filtering
- ✅ Search by username or ID
- ✅ Channel expulsion functionality

**Ready for:** Plan 09-03 - Admin User Handlers (users.py)

**Pending:** FSM states for user search flow (to be added in 09-03 Task 1)
