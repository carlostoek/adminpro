---
phase: quick
plan: 007
type: execute
wave: 1
depends_on: []
files_modified:
  - bot/services/message/user_flows.py
  - bot/handlers/free/callbacks.py
autonomous: true
must_haves:
  truths:
    - "Usuario recibe mensaje de bienvenida con botón callback (no URL directa)"
    - "Al hacer clic en el botón, el bot envía el menú Free al usuario"
    - "El mensaje de bienvenida incluye el enlace al canal para que pueda unirse"
  artifacts:
    - path: "bot/services/message/user_flows.py"
      provides: "Mensaje de aprobación con botón callback y enlace al canal"
      contains: "free_request_approved con callback_data y channel_link"
    - path: "bot/handlers/free/callbacks.py"
      provides: "Handler para callback free:approved:enter"
      contains: "handle_free_approved_enter callback handler"
  key_links:
    - from: "user_flows.py free_request_approved"
      to: "callbacks.py handle_free_approved_enter"
      via: "callback_data='free:approved:enter'"
---

<objective>
Modificar el flujo de aceptación al canal Free para enviar el menú del bot después del mensaje de bienvenida.

**Flujo actual:**
1. Usuario es aceptado → recibe mensaje con botón URL directo al canal
2. Usuario hace clic → ingresa al canal

**Flujo deseado:**
1. Usuario es aceptado → recibe mensaje de bienvenida con botón "Ingresar al canal"
2. Cuando el usuario hace clic en ese botón → el bot le envía el menú Free

**Cambios necesarios:**
1. Modificar `free_request_approved()` en `user_flows.py` para usar callback en lugar de URL directa
2. Agregar handler `handle_free_approved_enter` en `callbacks.py` que envíe el menú
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@/data/data/com.termux/files/home/repos/adminpro/bot/services/message/user_flows.py
@/data/data/com.termux/files/home/repos/adminpro/bot/handlers/free/callbacks.py
@/data/data/com.termux/files/home/repos/adminpro/bot/handlers/free/menu.py
@/data/data/com.termux/files/home/repos/adminpro/bot/services/subscription.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Modificar mensaje de aprobación Free para usar callback</name>
  <files>bot/services/message/user_flows.py</files>
  <action>
    Modificar el método `free_request_approved()` en `UserFlowMessages` clase:

    1. Cambiar el botón de URL directa a callback
    2. El botón debe tener:
       - Texto: "🚀 Ingresar al canal"
       - callback_data: "free:approved:enter"
    3. Agregar el enlace al canal como texto visible en el mensaje (para que el usuario pueda unirse manualmente si lo desea)
    4. Incluir instrucciones claras sobre el flujo

    **Cambios específicos:**
    - Reemplazar `create_inline_keyboard` con botón URL por botón callback
    - Agregar el channel_link como texto plano en el mensaje
    - Mantener la voz de Lucien consistente

    **Nuevo texto del mensaje:**
    ```
    <i>Listo.</i>

    <i>Diana ha permitido su entrada.</i>

    <b>Bienvenido a {channel_name}.</b>

    <i>Este no es el lugar donde ella se entrega.</i>
    <i>Es el lugar donde comienza a insinuarse…</i>
    <i>y donde algunos descubren que ya no quieren quedarse solo aquí.</i>

    <i>Presione el botón para ingresar al canal y recibir su menú personalizado.</i>

    <b>Enlace al canal (por si prefiere ingresar manualmente):</b>
    {channel_link}
    👇
    ```

    **Nuevo keyboard:**
    ```python
    keyboard = create_inline_keyboard([
        [{"text": "🚀 Ingresar al canal", "callback_data": "free:approved:enter"}]
    ])
    ```
  </action>
  <verify>
    Verificar que el método retorna tuple[str, InlineKeyboardMarkup] con callback_data en lugar de URL
  </verify>
  <done>
    - Método `free_request_approved()` usa callback_data="free:approved:enter"
    - El mensaje incluye el channel_link como texto visible
    - La voz de Lucien se mantiene consistente
  </done>
</task>

<task type="auto">
  <name>Task 2: Agregar handler para callback de aprobación Free</name>
  <files>bot/handlers/free/callbacks.py</files>
  <action>
    Agregar un nuevo handler en `free_callbacks_router` para manejar el callback `free:approved:enter`:

    1. Crear función `handle_free_approved_enter(callback: CallbackQuery, container)`
    2. El handler debe:
       - Responder al callback con `callback.answer()`
       - Enviar el menú Free al usuario usando `show_free_menu()`
       - Manejar errores apropiadamente

    **Implementación:**
    ```python
    @free_callbacks_router.callback_query(lambda c: c.data == "free:approved:enter")
    async def handle_free_approved_enter(callback: CallbackQuery, container):
        """
        Maneja el clic en "Ingresar al canal" desde el mensaje de aprobación.

        Envía el menú Free al usuario cuando hace clic en el botón
        después de ser aceptado en el canal.

        Args:
            callback: CallbackQuery de Telegram
            container: ServiceContainer inyectado por middleware
        """
        user = callback.from_user

        if not container:
            await callback.answer("⚠️ Error: servicio no disponible", show_alert=True)
            return

        try:
            # Confirmar recepción del callback
            await callback.answer("✅ Bienvenido a Los Kinkys")

            # Preparar data para el menú
            data = {"container": container}

            # Enviar el menú Free
            from .menu import show_free_menu
            await show_free_menu(
                callback.message,
                data,
                user_id=user.id,
                user_first_name=user.first_name
            )

            logger.info(f"🆓 Menú Free enviado a usuario aprobado {user.id}")

        except Exception as e:
            logger.error(f"Error enviando menú Free a usuario aprobado {user.id}: {e}", exc_info=True)
            await callback.answer("⚠️ Error cargando el menú", show_alert=True)
    ```

    3. Registrar el handler en el router (ya está implícito con el decorator)
    4. Asegurar que el handler esté antes de handlers más genéricos para evitar conflictos
  </action>
  <verify>
    - El handler responde al callback "free:approved:enter"
    - Llama a show_free_menu() con los parámetros correctos
    - Maneja errores con logging apropiado
  </verify>
  <done>
    - Handler `handle_free_approved_enter` existe y está registrado
    - Envía el menú Free cuando el usuario hace clic
    - Logging apropiado para debugging
  </done>
</task>

<task type="auto">
  <name>Task 3: Verificar integración con approve_ready_free_requests</name>
  <files>bot/services/subscription.py</files>
  <action>
    Verificar que `approve_ready_free_requests()` en `subscription.py` sigue funcionando correctamente con los cambios:

    1. Revisar que el método usa `UserFlowMessages.free_request_approved()` correctamente
    2. Verificar que los parámetros (channel_name, channel_link) se pasan correctamente
    3. Confirmar que no hay cambios necesarios en este archivo (solo verificación)

    **Líneas a revisar:** ~1036-1066 en subscription.py

    El método ya debería funcionar sin cambios porque:
    - Llama a `flows.free_request_approved(channel_name, channel_link)`
    - Envía el mensaje con `await self.bot.send_message()`
    - El cambio de URL a callback es transparente para este método
  </action>
  <verify>
    - No se requieren cambios en subscription.py
    - La integración funciona correctamente
  </verify>
  <done>
    - Verificación completada
    - approve_ready_free_requests() funciona con el nuevo flujo
  </done>
</task>

</tasks>

<verification>
1. El mensaje de aprobación Free tiene botón con callback_data (no URL)
2. El handler `handle_free_approved_enter` existe y está registrado
3. Al hacer clic en el botón, se envía el menú Free al usuario
4. El enlace al canal sigue visible en el mensaje como texto
</verification>

<success_criteria>
- [ ] Mensaje de aprobación usa callback "free:approved:enter" en lugar de URL directa
- [ ] Handler procesa el callback y envía el menú Free
- [ ] Usuario puede unirse al canal manualmente (enlace visible en texto)
- [ ] Flujo completo funciona: aprobación → clic → menú
</success_criteria>

<output>
After completion, create `.planning/quick/007-modificar-flujo-de-aceptacion-free-para-/007-SUMMARY.md`
</output>
