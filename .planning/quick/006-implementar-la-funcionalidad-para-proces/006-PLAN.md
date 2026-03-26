---
phase: quick-006
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - bot/services/subscription.py
  - bot/services/message/admin_free.py
  - bot/handlers/admin/free.py
autonomous: true

must_haves:
  truths:
    - Admin can view pending Free requests with approve/reject all options
    - Admin can approve all pending requests in one action
    - Admin can reject all pending requests in one action
    - Approved users receive notification with channel link
    - Rejected users are notified and removed from queue
  artifacts:
    - path: "bot/services/subscription.py"
      provides: "get_pending_free_requests(), approve_all_free_requests(), reject_all_free_requests()"
      exports: ["get_pending_free_requests", "approve_all_free_requests", "reject_all_free_requests"]
    - path: "bot/services/message/admin_free.py"
      provides: "free_queue_view(), free_bulk_approve_confirm(), free_bulk_reject_confirm()"
      exports: ["free_queue_view", "free_bulk_approve_confirm", "free_bulk_reject_confirm"]
    - path: "bot/handlers/admin/free.py"
      provides: "Handlers for viewing queue and bulk actions"
      exports: ["callback_view_free_queue", "callback_approve_all_free", "callback_reject_all_free"]
  key_links:
    - from: "bot/handlers/admin/free.py"
      to: "bot/services/subscription.py"
      via: "ServiceContainer.subscription"
    - from: "bot/handlers/admin/free.py"
      to: "bot/services/message/admin_free.py"
      via: "container.message.admin.free"
    - from: "bot/services/subscription.py"
      to: "bot/database/models.py:FreeChannelRequest"
      via: "SQLAlchemy queries"
---

<objective>
Implementar funcionalidad para procesar solicitudes pendientes del Canal Free en bloque (aprobar o rechazar todas en un solo movimiento).

Purpose: Permitir a los administradores gestionar eficientemente la cola de solicitudes Free sin tener que aprobar/rechazar una por una.
Output: Nuevos métodos en SubscriptionService, nuevos mensajes en AdminFreeMessages, y nuevos handlers en free.py
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@bot/services/subscription.py
@bot/services/message/admin_free.py
@bot/handlers/admin/free.py
@bot/database/models.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Agregar métodos de gestión masiva en SubscriptionService</name>
  <files>bot/services/subscription.py</files>
  <action>
    Agregar tres nuevos métodos a la clase SubscriptionService:

    1. `get_pending_free_requests(self, limit: int = 100) -> List[FreeChannelRequest]`
       - Query solicitudes where processed=False
       - Order by request_date ASC (más antiguas primero)
       - Optional limit parameter
       - Return list of FreeChannelRequest objects

    2. `approve_all_free_requests(self, free_channel_id: str) -> Tuple[int, int]`
       - Get all pending requests via get_pending_free_requests()
       - For each: call bot.approve_chat_join_request(chat_id, user_id)
       - Mark each as processed=True, processed_at=datetime.utcnow()
       - Commit changes
       - Return (success_count, error_count)
       - Log each approval/rejection with user_id

    3. `reject_all_free_requests(self, free_channel_id: str) -> Tuple[int, int]`
       - Similar to approve_all but calls bot.decline_chat_join_request()
       - Mark all as processed=True (with decline flag if needed)
       - Return (success_count, error_count)
       - Log each rejection

    Follow existing patterns in approve_ready_free_requests() for consistency.
    Use proper error handling with try-except around each Telegram API call.
    Log at INFO level for successes, WARNING for individual failures.
  </action>
  <verify>
    grep -n "get_pending_free_requests\|approve_all_free_requests\|reject_all_free_requests" bot/services/subscription.py
  </verify>
  <done>
    Three methods exist in SubscriptionService with proper signatures, following existing code patterns, with logging and error handling.
  </done>
</task>

<task type="auto">
  <name>Task 2: Agregar mensajes para gestión de cola en AdminFreeMessages</name>
  <files>bot/services/message/admin_free.py</files>
  <action>
    Agregar cuatro nuevos métodos a la clase AdminFreeMessages:

    1. `free_queue_view(self, pending_requests: List[FreeChannelRequest], wait_time_minutes: int) -> Tuple[str, InlineKeyboardMarkup]`
       - Show count of pending requests
       - List first 10 requests with user_id and minutes waiting
       - Show wait time configured
       - Keyboard with: [Aprobar Todas] [Rechazar Todas] [Actualizar] [Volver]
       - Use Lucien voice: "lista de espera", "visitantes aguardando"

    2. `free_bulk_approve_confirm(self, count: int) -> Tuple[str, InlineKeyboardMarkup]`
       - Confirmation dialog before approving all
       - Show count of users to be approved
       - Keyboard: [Confirmar Aprobación] [Cancelar]
       - Lucien voice: "está a punto de conceder acceso a X visitantes"

    3. `free_bulk_reject_confirm(self, count: int) -> Tuple[str, InlineKeyboardMarkup]`
       - Confirmation dialog before rejecting all
       - Show count of users to be rejected
       - Keyboard: [Confirmar Rechazo] [Cancelar]
       - Lucien voice: "está a punto de denegar acceso a X visitantes"

    4. `free_bulk_result(self, action: str, success: int, errors: int) -> Tuple[str, InlineKeyboardMarkup]`
       - Show results after bulk action
       - action: "approved" or "rejected"
       - Show success count and error count (if any)
       - Keyboard: [Ver Cola Actualizada] [Volver al Menú]
       - Lucien voice appropriate for success or partial success

    Update _free_configured_keyboard() to change "📋 Cola de Solicitudes" callback from "free:view_queue" to "admin:free_queue" for consistency with handler naming.
  </action>
  <verify>
    grep -n "free_queue_view\|free_bulk_approve_confirm\|free_bulk_reject_confirm\|free_bulk_result" bot/services/message/admin_free.py
  </verify>
  <done>
    Four methods exist in AdminFreeMessages, following Lucien voice conventions, returning (text, keyboard) tuples.
  </done>
</task>

<task type="auto">
  <name>Task 3: Implementar handlers para gestión masiva de solicitudes Free</name>
  <files>bot/handlers/admin/free.py</files>
  <action>
    Agregar tres nuevos handlers en bot/handlers/admin/free.py:

    1. `callback_view_free_queue(callback: CallbackQuery, session: AsyncSession)`
       - Callback data: "admin:free_queue"
       - Get container = ServiceContainer(session, callback.bot)
       - Get pending requests via container.subscription.get_pending_free_requests()
       - Get wait_time from container.config.get_wait_time()
       - Get message from container.message.admin.free.free_queue_view(pending, wait_time)
       - Edit message with queue view
       - Answer callback

    2. `callback_approve_all_free(callback: CallbackQuery, session: AsyncSession)`
       - Callback data: "free:approve_all"
       - Get pending count first
       - If count == 0: answer "No hay solicitudes pendientes"
       - Get confirmation message from free_bulk_approve_confirm(count)
       - Show confirmation dialog (two-step to prevent accidents)

    3. `callback_confirm_approve_all(callback: CallbackQuery, session: AsyncSession)`
       - Callback data: "free:confirm_approve_all"
       - Get free_channel_id from container.channel.get_free_channel_id()
       - Call container.subscription.approve_all_free_requests(free_channel_id)
       - Get result message from free_bulk_result("approved", success, errors)
       - Edit message with results
       - Answer callback with success message

    4. `callback_reject_all_free(callback: CallbackQuery, session: AsyncSession)`
       - Similar pattern to approve but for rejection
       - Callback data: "free:reject_all" and "free:confirm_reject_all"

    Import needed modules at top of file.
    Follow existing handler patterns for error handling (try-except with logging).
    Use logger.info() for successful operations, logger.error() for failures.
  </action>
  <verify>
    grep -n "callback_view_free_queue\|callback_approve_all_free\|callback_reject_all_free\|callback_confirm_approve_all\|callback_confirm_reject_all" bot/handlers/admin/free.py
  </verify>
  <done>
    Five handlers exist (view queue, approve all, confirm approve, reject all, confirm reject) with proper callback routing and error handling.
  </done>
</task>

</tasks>

<verification>
1. Run syntax check: python -m py_compile bot/services/subscription.py bot/services/message/admin_free.py bot/handlers/admin/free.py
2. Verify imports work: python -c "from bot.services.subscription import SubscriptionService; from bot.services.message.admin_free import AdminFreeMessages; from bot.handlers.admin.free import *"
3. Check no undefined references: grep -n "free_queue_view\|approve_all_free\|reject_all_free" bot/handlers/admin/free.py | head -20
</verification>

<success_criteria>
- Admin can navigate to Free menu and click "Cola de Solicitudes"
- Queue view shows pending requests with Approve All / Reject All buttons
- Bulk actions require confirmation before executing
- After confirmation, all pending requests are processed
- Results show success/error counts
- Users receive appropriate notifications (approved get channel access, rejected are declined)
- All code follows existing patterns (Lucien voice, error handling, logging)
</success_criteria>

<output>
After completion, create `.planning/quick/006-implementar-la-funcionalidad-para-proces/006-SUMMARY.md`
</output>
