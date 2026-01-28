# Phase 9: User Management Features - Context

**Gathered:** 2026-01-26
**Status:** Ready for planning

## Phase Boundary

Admin can manage users (view info, change roles, block, expel) with audit logging. Users can be searched or browsed from a list. Admin has control over user accounts with appropriate permission boundaries.

## Implementation Decisions

### User Info Display
- **Profile content:** Detailed with history - User ID, username, role, subscription status, join date, recent activity log, interest history
- **Profile structure:** Tabbed interface with "Overview", "Subscription", "Activity", "Interests" tabs
- **User discovery:** Search by username, user ID, or select from a list of VIP/Free users
- **List visual indicators:** Emoji badges for roles (👑 Admin, 💎 VIP, 👤 Free) + status badges (⏳ Expiring, 🚫 Blocked)

### Role Change Interface
- **Confirmation style:** Clear before/after display - shows user's current role and the new role they'll become
- **Flow:** One-step confirmation - admin selects action, confirms immediately
- **Feedback:** Success with explanation - e.g., "Role changed successfully. User is now VIP, access granted"
- **Allowed changes:** All users manageable (except permission boundaries apply)

### Block vs. Expel Actions
- **UI clarification:** Explain difference in menu - "Blocking: User cannot use the bot. Expelling: User is removed from channels but can still use the bot."
- **User message:** Generic restriction message - "You have been restricted" (same for both actions)
- **Confirmation flow:** Single confirmation
- **Blocking duration:** Permanent until manually reversed

### Permission Boundaries
- **Admin-on-admin:** Super admin only - first admin in ADMIN_USER_IDS config list is the super admin
- **Self-actions:** Blocked - admins cannot block or expel themselves
- **Restricted action feedback:** Generic error message - "You don't have permission for this action"

### Claude's Discretion
- Tab switching implementation details
- Pagination for user list
- Exact wording of confirmation messages
- Search/filter functionality specifics

## Specific Ideas

- Tabbed interface for user profile (Overview, Subscription, Activity, Interests)
- Emoji badges for visual clarity in user lists
- Super admin concept: first admin in ADMIN_USER_IDS from config

## Deferred Ideas

- None — discussion stayed within phase scope

---

*Phase: 09-user-management*
*Context gathered: 2026-01-26*
