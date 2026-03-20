---
status: resolved
trigger: "false-bot-blocked-warning-subscription"
created: 2026-03-19T00:00:00Z
updated: 2026-03-19T00:10:00Z
---

## Current Focus

hypothesis: CONFIRMED. The warning "⚠️ Usuario X bloqueó el bot" fires from a condition that matches ANY TelegramForbiddenError, not just "bot was blocked". The check `"Forbidden" in error_type or "blocked" in str(notify_error).lower()` catches all Forbidden errors (e.g., approve_chat_join_request failing because the join request already expired/was cancelled). There are TWO places with this bug in subscription.py.
test: Read subscription.py lines 1272-1281 (approve_ready_free_requests) and lines 1485-1495 (approve_all_free_requests)
expecting: Fix is to log the actual error message so the operator can see the real cause, and tighten the "bot blocked" detection to check for the specific Telegram error string.
next_action: Apply fix to both exception handlers in subscription.py

## Symptoms

expected: Los warnings "bloqueó el bot" deberían aparecer solo cuando Telegram confirma que el usuario bloqueó el bot (error Forbidden: bot was blocked by the user).
actual: Aparecen masivamente desde bot.services.subscription con patrón temporal regular (~cada 5 minutos, siempre a los :54 segundos). Solo 1 warning viene de bot.handlers.user.free_join_request con el error real de Telegram. Los de subscription NO incluyen el mensaje de Telegram en el log.
errors:
  - MUCHOS: bot.services.subscription - WARNING - ⚠️ Usuario XXXXX bloqueó el bot (sin detalle de Telegram)
  - UNO REAL: bot.handlers.user.free_join_request - WARNING - ⚠️ No se pudo notificar a user 6970084428 - Telegram server says - Forbidden: bot was blocked by the user
reproduction: El background task process_free_queue se ejecuta cada 5 minutos. Cuando llama a approve_ready_free_requests(), el bot intenta approve_chat_join_request() y luego send_message(). Si la solicitud ya expiró en Telegram (JOIN REQUEST EXPIRADA, no bot bloqueado), approve_chat_join_request lanza TelegramForbiddenError. Pero la detección de "bot blocked" en el except interno captura CUALQUIER Forbidden, incluyendo los de join request expirado.
started: Desde el arranque del bot, primer batch a los 5 min.

## Eliminated

- hypothesis: Los usuarios realmente bloquearon el bot en masa
  evidence: 16 usuarios diferentes en 8 segundos en el primer batch, patrón imposible para bloqueos humanos. El handler real de free_join_request sí incluye el string de Telegram; subscription.py no.
  timestamp: 2026-03-19T00:05:00Z

- hypothesis: El error viene del send_message() de notificación
  evidence: El send_message() está dentro de un try/except ANIDADO (líneas 1255-1281). Ese bloque interno SÍ tiene la verificación "Forbidden". PERO el approve_chat_join_request() en línea 1229 está en el try EXTERNO (líneas 1227-1309). Si approve_chat_join_request() falla con Forbidden (join request expirada), cae al except externo en línea 1290 que NO emite el warning de "bloqueó el bot". El warning viene del bloque interno de send_message() cuando la send_message falla con Forbidden porque el usuario bloqueó el bot - pero la detección es demasiado amplia.
  timestamp: 2026-03-19T00:08:00Z

## Evidence

- timestamp: 2026-03-19T00:02:00Z
  checked: bot/background/tasks.py - process_free_queue task
  found: Se ejecuta cada Config.PROCESS_FREE_QUEUE_MINUTES (5 min) via IntervalTrigger. Llama a container.subscription.approve_ready_free_requests()
  implication: Confirma el patrón temporal de 5 minutos.

- timestamp: 2026-03-19T00:04:00Z
  checked: subscription.py líneas 1225-1316 - approve_ready_free_requests()
  found: Dos try/except anidados. Bloque EXTERNO (línea 1227) maneja el flujo completo por usuario. Bloque INTERNO (línea 1255) maneja solo el send_message de notificación. El bloque interno en línea 1274 detecta "bot blocked" con: `if "Forbidden" in error_type or "blocked" in str(notify_error).lower()`. Esta condición es TRUE para CUALQUIER TelegramForbiddenError, no solo "bot was blocked by the user".
  implication: Si send_message() falla por cualquier razón Forbidden (usuario baneado del chat, permisos, etc.), emite el mismo warning que si el bot estuviera bloqueado.

- timestamp: 2026-03-19T00:06:00Z
  checked: subscription.py líneas 1485-1495 - approve_all_free_requests()
  found: Mismo patrón de detección incorrecta: `if "Forbidden" in error_type or "blocked" in str(notify_error).lower()` con warning "bloqueó el bot". Además el mensaje es ligeramente diferente pero el mismo problema.
  implication: El bug existe en DOS lugares del mismo archivo.

- timestamp: 2026-03-19T00:07:00Z
  checked: Comparación entre handler real (free_join_request) vs subscription.py
  found: El handler real loguea: f"No se pudo notificar a user {user_id}: {notify_error}" - incluye el error completo de Telegram. subscription.py loguea solo "bloqueó el bot" sin el error real, silenciando la causa verdadera.
  implication: La ausencia del error de Telegram en los logs de subscription.py confirma que la detección es prematura y oculta la causa raíz. El patrón exacto de Telegram para bot bloqueado es: "Forbidden: bot was blocked by the user".

## Resolution

root_cause: En approve_ready_free_requests() y approve_all_free_requests(), la detección de "bot was blocked" usa `"Forbidden" in error_type or "blocked" in str(notify_error).lower()`. Esta condición captura CUALQUIER TelegramForbiddenError (incluyendo join requests expiradas, usuarios sin permisos, etc.) y los loguea como si el usuario hubiera bloqueado el bot. La condición correcta es verificar el string específico de Telegram: "bot was blocked by the user".

fix: Cambiada la condición de detección en ambos lugares de `"Forbidden" in error_type or "blocked" in str(notify_error).lower()` a `"bot was blocked by the user" in str(notify_error)`. Los errores no-blocked ahora se loguean con el mensaje completo de Telegram para diagnóstico.

verification: Las dos instancias en subscription.py fueron corregidas y verificadas visualmente. El string exacto de Telegram "bot was blocked by the user" solo aparece cuando el usuario realmente bloqueó el bot. Cualquier otro Forbidden (join request expirada, usuario baneado, etc.) ahora aparece como WARNING con el mensaje real del error.

files_changed:
  - bot/services/subscription.py (approve_ready_free_requests línea 1274, approve_all_free_requests línea 1488)
