---
phase: 05-role-detection-database
plan: 001
type: execute
wave: 1
depends_on: []
files_modified:
  - /data/data/com.termux/files/home/repos/c1/main.py
  - /data/data/com.termux/files/home/repos/c1/bot/services/subscription.py
  - /data/data/com.termux/files/home/repos/c1/bot/background/tasks.py
autonomous: true
gap_closure: true

must_haves:
  truths:
    - "RoleDetectionMiddleware está registrado en main.py y funciona"
    - "Sistema detecta automáticamente cambios de rol cuando VIP expira"
    - "Background tasks loguean cambios de rol al expirar VIPs"
  artifacts:
    - path: "/data/data/com.termux/files/home/repos/c1/main.py"
      provides: "Registro de middlewares activo"
      contains: "dispatcher.update.middleware(RoleDetectionMiddleware())"
    - path: "/data/data/com.termux/files/home/repos/c1/bot/services/subscription.py"
      provides: "Integración con RoleChangeService para expiración VIP"
      contains: "await container.role_change.log_role_change"
    - path: "/data/data/com.termux/files/home/repos/c1/bot/background/tasks.py"
      provides: "Background task que loguea cambios de rol"
      contains: "await container.role_change.log_role_change"
  key_links:
    - from: "main.py"
      to: "bot.middlewares.role_detection"
      via: "import RoleDetectionMiddleware"
      pattern: "from bot.middlewares import RoleDetectionMiddleware"
    - from: "bot/services/subscription.py"
      to: "bot/services/role_change.py"
      via: "container.role_change.log_role_change"
      pattern: "container\\.role_change\\.log_role_change"
---

<objective>
Fix Phase 5 gaps identified in VERIFICATION.md:
1. Register RoleDetectionMiddleware in main.py (currently commented out)
2. Integrate automatic role change detection when VIP subscriptions expire

Purpose: Complete the role detection system so it actually works in production. Without middleware registration, role detection is non-functional. Without integration with SubscriptionService, role changes aren't logged when VIPs expire.

Output:
- RoleDetectionMiddleware registered and active
- VIP expiration triggers role change logging
- System automatically detects role changes
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/05-role-detection-database/05-VERIFICATION.md

# Phase 5 implementation files
@/data/data/com.termux/files/home/repos/c1/bot/middlewares/role_detection.py
@/data/data/com.termux/files/home/repos/c1/bot/services/role_change.py
@/data/data/com.termux/files/home/repos/c1/bot/services/subscription.py
@/data/data/com.termux/files/home/repos/c1/bot/background/tasks.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Register RoleDetectionMiddleware in main.py</name>
  <files>/data/data/com.termux/files/home/repos/c1/main.py</files>
  <action>
1. Open main.py and find the TODO section for middleware registration (lines 91-94)
2. Update the imports to include RoleDetectionMiddleware:
   ```python
   from bot.middlewares import DatabaseMiddleware, AdminAuthMiddleware, RoleDetectionMiddleware
   ```
3. Register all three middlewares:
   ```python
   # Registrar middlewares (ONDA 1 - Fase 1.3)
   from bot.middlewares import DatabaseMiddleware, AdminAuthMiddleware, RoleDetectionMiddleware
   dispatcher.update.middleware(DatabaseMiddleware())
   dispatcher.message.middleware(AdminAuthMiddleware())
   dispatcher.update.middleware(RoleDetectionMiddleware())
   dispatcher.callback_query.middleware(RoleDetectionMiddleware())
   ```
4. Remove the TODO comment or update it to indicate completion
5. Also register handlers (uncomment lines 87-89):
   ```python
   # Registrar handlers (ONDA 1 - Fases siguientes)
   from bot.handlers import register_all_handlers
   register_all_handlers(dispatcher)
   ```

Important:
- RoleDetectionMiddleware should be registered on both `dispatcher.update` (global) AND `dispatcher.callback_query` (specific) to ensure it works for all interaction types
- Keep the existing DatabaseMiddleware and AdminAuthMiddleware registrations
- The order matters: DatabaseMiddleware first (session injection), then AdminAuthMiddleware (admin validation), then RoleDetectionMiddleware (role detection)
  </action>
  <verify>Check main.py lines 87-95 contain the updated middleware registration code</verify>
  <done>RoleDetectionMiddleware is imported and registered for both update and callback_query events</done>
</task>

<task type="auto">
  <name>Task 2: Integrate RoleChangeService with VIP expiration</name>
  <files>/data/data/com.termux/files/home/repos/c1/bot/services/subscription.py</files>
  <action>
1. In the `expire_vip_subscribers` method (around line 383), add role change logging when VIPs expire
2. After marking a subscriber as expired (line 403-405), add a call to log the role change:
   ```python
   # After line 405: logger.info(f"⏱️ VIP expirado: user {subscriber.user_id}")

   # Log role change from VIP to FREE
   try:
       # Get role_change service from container (requires bot instance)
       # Since this is called from background task, we need to pass container
       # The method signature needs to accept container parameter
       # For now, we'll modify the method to accept optional container
       pass
   except Exception as e:
       logger.error(f"Error logging role change for user {subscriber.user_id}: {e}")
   ```
3. Actually, better approach: Modify the `expire_vip_subscribers` method to accept a `container` parameter and log role changes:
   ```python
   async def expire_vip_subscribers(self, container: Optional[ServiceContainer] = None) -> int:
       """
       Marca como expirados los suscriptores VIP cuya fecha pasó.

       Si se proporciona container, también loguea cambios de rol.

       Esta función se ejecuta periódicamente en background.

       Args:
           container: ServiceContainer opcional para logging de cambios de rol

       Returns:
           Cantidad de suscriptores expirados
       """
       # ... existing code ...

       for subscriber in expired_subscribers:
           subscriber.status = "expired"
           count += 1
           logger.info(f"⏱️ VIP expirado: user {subscriber.user_id}")

           # Log role change if container provided
           if container and container.role_change:
               try:
                   await container.role_change.log_role_change(
                       user_id=subscriber.user_id,
                       new_role=UserRole.FREE,
                       changed_by=0,  # SYSTEM
                       reason=RoleChangeReason.VIP_EXPIRED,
                       change_source="SYSTEM",
                       previous_role=UserRole.VIP,
                       change_metadata={
                           "vip_subscriber_id": subscriber.id,
                           "expired_at": datetime.utcnow().isoformat(),
                           "original_expiry": subscriber.expiry_date.isoformat() if subscriber.expiry_date else None
                       }
                   )
                   logger.debug(f"✅ Role change logged for expired VIP user {subscriber.user_id}")
               except Exception as e:
                   logger.error(f"Error logging role change for user {subscriber.user_id}: {e}")

       # ... rest of method ...
   ```
4. Add necessary imports at top of file:
   ```python
   from typing import Optional
   from bot.services.container import ServiceContainer
   from bot.database.models import UserRole, RoleChangeReason
   from datetime import datetime
   ```
5. Update the background task to pass container to expire_vip_subscribers
  </action>
  <verify>Check that expire_vip_subscribers method now accepts container parameter and logs role changes</verify>
  <done>VIP expiration triggers role change logging with proper metadata</done>
</task>

<task type="auto">
  <name>Task 3: Update background task to log role changes</name>
  <files>/data/data/com.termux/files/home/repos/c1/bot/background/tasks.py</files>
  <action>
1. In the `expire_and_kick_vip_subscribers` function (around line 27), update the call to `expire_vip_subscribers` to pass the container:
   ```python
   # After line 43: container = ServiceContainer(session, bot)

   # Mark expired VIPs and log role changes
   expired_count = await container.subscription.expire_vip_subscribers(container=container)
   ```
2. Add logging to show role changes were processed:
   ```python
   if expired_count > 0:
       logger.info(f"✅ {expired_count} VIP(s) expirados y cambios de rol logueados")
   else:
       logger.info("✅ No hay VIPs para expirar")
   ```
3. Update the function docstring to reflect the new behavior
4. Also update the `kick_expired_vip_from_channel` call to use the same container if needed (though it doesn't need role logging)
  </action>
  <verify>Check that background task passes container to expire_vip_subscribers and logs results</verify>
  <done>Background task successfully logs role changes when VIPs expire</done>
</task>

</tasks>

<verification>
1. Run a quick syntax check: `python -m py_compile main.py`
2. Verify middleware imports are correct: `grep -n "RoleDetectionMiddleware" main.py`
3. Check subscription service integration: `grep -n "log_role_change" bot/services/subscription.py`
4. Verify background task integration: `grep -n "expire_vip_subscribers.*container" bot/background/tasks.py`
</verification>

<success_criteria>
1. RoleDetectionMiddleware registered in main.py (not commented out)
2. VIP expiration triggers role change logging in UserRoleChangeLog table
3. System automatically detects role changes from VIP to FREE when subscriptions expire
4. All code compiles without syntax errors
</success_criteria>

<output>
After completion, create `.planning/quick/001-fix-phase-5-gaps/001-SUMMARY.md`
</output>
