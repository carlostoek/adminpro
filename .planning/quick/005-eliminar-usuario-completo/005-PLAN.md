---
phase: quick
plan: 005
type: execute
wave: 1
depends_on: []
files_modified:
  - bot/services/subscription.py
  - bot/services/message/admin_user.py
  - bot/handlers/admin/users.py
  - bot/states/admin.py
autonomous: true

must_haves:
  truths:
    - "Admin can delete a user completely from the system"
    - "All user-related entities are removed (VIPSubscriber, FreeChannelRequest, InvitationToken, UserInterest, UserRoleChangeLog)"
    - "Confirmation dialog is shown before deletion"
    - "Works on both SQLite and PostgreSQL using SQLAlchemy ORM"
    - "User receives notification about account deletion"
  artifacts:
    - path: "bot/services/subscription.py"
      provides: "delete_user_completely method"
      contains: "async def delete_user_completely"
    - path: "bot/services/message/admin_user.py"
      provides: "Delete confirmation and success messages"
      contains: "delete_confirm, delete_success"
    - path: "bot/handlers/admin/users.py"
      provides: "Delete user handlers"
      contains: "callback_user_delete, callback_user_delete_confirm"
    - path: "bot/states/admin.py"
      provides: "Delete confirmation state"
      contains: "UserManagementStates.deleting_user"
  key_links:
    - from: "bot/handlers/admin/users.py"
      to: "bot/services/subscription.py"
      via: "container.subscription.delete_user_completely"
    - from: "bot/handlers/admin/users.py"
      to: "bot/services/message/admin_user.py"
      via: "container.message.admin.user.delete_confirm"
---

<objective>
Implementar funcionalidad para eliminar un usuario completamente del sistema, incluyendo todas sus interacciones con el bot.

Purpose: Permitir a los administradores eliminar completamente a un usuario y todos sus datos asociados del sistema.
Output: Método de servicio, mensajes de confirmación, handlers y botón en panel de gestión de usuarios.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@/data/data/com.termux/files/home/repos/adminpro/bot/database/models.py
@/data/data/com.termux/files/home/repos/adminpro/bot/services/subscription.py
@/data/data/com.termux/files/home/repos/adminpro/bot/services/message/admin_user.py
@/data/data/com.termux/files/home/repos/adminpro/bot/handlers/admin/users.py
@/data/data/com.termux/files/home/repos/adminpro/bot/states/admin.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add delete_user_completely method to SubscriptionService</name>
  <files>bot/services/subscription.py</files>
  <action>
Add a new async method `delete_user_completely` to the SubscriptionService class that:

1. Accepts parameters: `user_id: int`, `deleted_by: int`
2. Returns: `Tuple[bool, str, Optional[User]]` - (success, message, deleted_user_info)
3. Uses SQLAlchemy ORM delete operations (compatible with SQLite and PostgreSQL)
4. Deletes all related entities in the correct order to avoid FK constraint errors:
   - First: UserInterest (user_id FK)
   - Second: UserRoleChangeLog (user_id FK)
   - Third: FreeChannelRequest (user_id FK)
   - Fourth: VIPSubscriber (user_id FK) - this also cascades to related tokens via subscribers relationship
   - Fifth: InvitationToken where generated_by=user_id OR used_by=user_id
   - Finally: User (the user record itself)

5. Before deleting, fetch user info to return it for notification purposes
6. Use `await self.session.execute(delete(Model).where(...))` pattern
7. Commit transaction after all deletions
8. Log the deletion with admin ID
9. Return appropriate error messages if user not found or deletion fails

IMPORTANT: Do NOT use raw SQL. Use SQLAlchemy's `delete()` construct for cross-database compatibility.
  </action>
  <verify>grep -n "delete_user_completely" bot/services/subscription.py</verify>
  <done>Method exists with proper signature, deletes all related entities in correct order, uses SQLAlchemy ORM only</done>
</task>

<task type="auto">
  <name>Task 2: Add delete confirmation and success messages</name>
  <files>bot/services/message/admin_user.py</files>
  <action>
Add two new methods to AdminUserMessages class:

1. `delete_confirm(self, user_info: Dict[str, Any]) -> Tuple[str, InlineKeyboardMarkup]`:
   - Shows warning about irreversible deletion
   - Lists what will be deleted (account, subscriptions, requests, interests)
   - Uses Lucien's voice: "Una acción irreversible...", "será borrado del jardín"
   - Returns confirmation keyboard with "Eliminar Definitivamente" and "Cancelar"

2. `delete_success(self, user_info: Dict[str, Any]) -> Tuple[str, InlineKeyboardMarkup]`:
   - Shows success message with user name
   - Uses Lucien's voice: "El habitante ha sido removido..."
   - Returns keyboard to return to user list

3. Add helper methods for keyboards:
   - `_delete_confirm_keyboard(user_id)` - Confirm/Cancel buttons
   - `_delete_success_keyboard()` - Return to list button

Follow existing patterns from expel_confirm/expel_success methods. Use proper emojis (⚠️ for warning, ✅ for success).
  </action>
  <verify>grep -n "delete_confirm\|delete_success" bot/services/message/admin_user.py</verify>
  <done>Both message methods exist with proper Lucien voice, confirmation keyboard includes delete and cancel buttons</done>
</task>

<task type="auto">
  <name>Task 3: Add delete user handlers and integrate with user detail view</name>
  <files>bot/handlers/admin/users.py, bot/states/admin.py</files>
  <action>
1. Add new state to UserManagementStates in bot/states/admin.py:
   - `deleting_user = State()` - For confirmation flow

2. Add two new handlers to bot/handlers/admin/users.py:

   Handler 1: `callback_user_delete` - Shows confirmation dialog
   - Route: `admin:user:delete:{user_id}`
   - Check permissions using `_can_modify_user`
   - Show delete_confirm message
   - Set FSM state to `UserManagementStates.deleting_user`

   Handler 2: `callback_user_delete_confirm` - Executes deletion
   - Route: `admin:user:delete:confirm:{user_id}`
   - Call `container.subscription.delete_user_completely(user_id, admin_id)`
   - If success: show delete_success message, notify user
   - If error: show action_error message
   - Clear FSM state

3. Update `_user_detail_keyboard` in bot/services/message/admin_user.py:
   - Add new button "🗑️ Eliminar" next to "🚪 Expulsar"
   - Callback: `admin:user:delete:{user_id}`

4. Add notification to user after deletion (send message before deleting):
   - "Su cuenta ha sido eliminada del sistema por un administrador."
   - Handle case where user blocked the bot

Follow existing patterns from expel handlers. Use proper error handling and logging.
  </action>
  <verify>
grep -n "deleting_user" bot/states/admin.py &&
grep -n "callback_user_delete" bot/handlers/admin/users.py &&
grep -n "admin:user:delete" bot/services/message/admin_user.py
  </verify>
  <done>State added, both handlers implemented, button added to user detail keyboard, user notification implemented</done>
</task>

</tasks>

<verification>
- [ ] Method `delete_user_completely` exists in SubscriptionService
- [ ] Method deletes all related entities in correct FK order
- [ ] Uses SQLAlchemy ORM delete (not raw SQL)
- [ ] Messages `delete_confirm` and `delete_success` exist with Lucien voice
- [ ] Handlers `callback_user_delete` and `callback_user_delete_confirm` exist
- [ ] Button "🗑️ Eliminar" appears in user detail view
- [ ] Confirmation dialog shown before deletion
- [ ] User receives notification before deletion
- [ ] Works with both SQLite and PostgreSQL
</verification>

<success_criteria>
1. Admin can click "🗑️ Eliminar" in user detail view
2. Confirmation dialog shows with warning about irreversible action
3. Upon confirmation, all user data is deleted from database
4. User receives notification about account deletion
5. Success message shown to admin
6. No database constraint errors during deletion
</success_criteria>

<output>
After completion, create `.planning/quick/005-eliminar-usuario-completo/005-SUMMARY.md`
</output>
