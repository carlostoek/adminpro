---
phase: quick
plan: 005
name: Eliminar Usuario Completo
subsystem: admin
completed: 2026-02-04
duration: 15min

tech-stack:
  added: []
  patterns:
    - SQLAlchemy ORM delete for cross-database compatibility
    - FSM state for confirmation flow
    - Transaction rollback on error

key-files:
  created: []
  modified:
    - bot/services/subscription.py
    - bot/services/message/admin_user.py
    - bot/handlers/admin/users.py
    - bot/states/admin.py

dependencies:
  requires: []
  provides:
    - User deletion functionality
  affects:
    - Future user management features

decisions:
  - "FK deletion order: UserInterest → UserRoleChangeLog → FreeChannelRequest → VIPSubscriber → InvitationToken → User"
  - "User notification sent BEFORE deletion (best effort, handles blocked bot)"
  - "FSM state used for confirmation flow (deleting_user)"
  - "Transaction rollback on any error during deletion"
---

# Quick Task 005: Eliminar Usuario Completo - Summary

## Overview

Implemented complete user deletion functionality allowing administrators to permanently remove a user and all their associated data from the system.

## What Was Built

### 1. Service Layer (`bot/services/subscription.py`)

**Method: `delete_user_completely(user_id, deleted_by)`**

- Deletes all user-related entities in correct FK order to avoid constraint errors
- Uses SQLAlchemy ORM `delete()` construct for SQLite/PostgreSQL compatibility
- Returns deleted user info for notification purposes
- Includes transaction handling with rollback on error
- Logs deletion with admin ID for audit trail

**Deletion Order:**
1. UserInterest (user_id FK)
2. UserRoleChangeLog (user_id FK)
3. FreeChannelRequest (user_id FK)
4. VIPSubscriber (user_id FK)
5. InvitationToken (generated_by or used_by)
6. User (the user record itself)

### 2. Message Layer (`bot/services/message/admin_user.py`)

**Methods Added:**
- `delete_confirm(user_info)` - Warning dialog listing all data to be deleted
- `delete_success(user_info)` - Success message with Lucien's voice
- `_delete_confirm_keyboard(user_id)` - Confirm/Cancel buttons
- `_delete_success_keyboard()` - Return to list button

**Lucien's Voice Examples:**
- "Una acción irreversible..."
- "El habitante será borrado del jardín"
- "El habitante ha sido removido..."
- "Su presencia en el jardín ha llegado a su fin..."

### 3. Handler Layer (`bot/handlers/admin/users.py`)

**Handlers Added:**
- `callback_user_delete` - Shows confirmation dialog, sets FSM state
- `callback_user_delete_confirm` - Executes deletion, notifies user, clears state

**Features:**
- Permission checking via `_can_modify_user`
- User notification before deletion (handles blocked bot gracefully)
- FSM state management for confirmation flow
- Proper error handling and logging

### 4. State Management (`bot/states/admin.py`)

**State Added:**
- `deleting_user = State()` - For confirmation flow

### 5. UI Integration (`bot/services/message/admin_user.py`)

**Button Added:**
- "🗑️ Eliminar" next to "🚪 Expulsar" in user detail view

## Verification

All verification criteria met:

- [x] Method `delete_user_completely` exists in SubscriptionService
- [x] Method deletes all related entities in correct FK order
- [x] Uses SQLAlchemy ORM delete (not raw SQL)
- [x] Messages `delete_confirm` and `delete_success` exist with Lucien voice
- [x] Handlers `callback_user_delete` and `callback_user_delete_confirm` exist
- [x] Button "🗑️ Eliminar" appears in user detail view
- [x] Confirmation dialog shown before deletion
- [x] User receives notification before deletion
- [x] Works with both SQLite and PostgreSQL

## Success Criteria

All success criteria met:

1. [x] Admin can click "🗑️ Eliminar" in user detail view
2. [x] Confirmation dialog shows with warning about irreversible action
3. [x] Upon confirmation, all user data is deleted from database
4. [x] User receives notification about account deletion
5. [x] Success message shown to admin
6. [x] No database constraint errors during deletion

## Commits

1. `2115d3f` - feat(quick-005): add delete_user_completely method to SubscriptionService
2. `aa19262` - feat(quick-005): add delete confirmation and success messages
3. `0d547cd` - feat(quick-005): add delete user handlers and UI integration

## Deviations from Plan

None - plan executed exactly as written.

## Cross-Database Compatibility

The implementation uses SQLAlchemy ORM's `delete()` construct exclusively:

```python
await self.session.execute(
    delete(Model).where(Model.user_id == user_id)
)
```

This ensures compatibility with both SQLite and PostgreSQL without requiring dialect-specific SQL.

## Security Considerations

1. **Permission Checking:** Uses existing `_can_modify_user` to prevent unauthorized deletions
2. **Confirmation Flow:** FSM state ensures two-step confirmation before deletion
3. **Audit Logging:** All deletions logged with admin ID
4. **Transaction Safety:** Rollback on any error prevents partial deletions
