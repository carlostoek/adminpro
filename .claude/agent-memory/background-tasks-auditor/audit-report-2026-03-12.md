# AUDIT REPORT: Background Tasks & Channel Service

**Fecha:** 2026-03-12
**Auditor:** background-tasks-auditor
**Archivos auditados:**
- `bot/background/tasks.py` (418 líneas)
- `bot/services/channel.py` (660 líneas)
- `bot/services/subscription.py` (métodos relevantes)
- `bot/database/engine.py` (session management)

---

## Executive Summary

- **Total Issues Found:** 8 (2 CRITICAL, 4 HIGH, 2 MEDIUM)
- **Overall Risk Assessment:** HIGH

### Hallazgos por Severidad
| Severidad | Cantidad | Descripción |
|-----------|----------|-------------|
| CRITICAL | 2 | Pueden causar corrupción de datos o inconsistencias entre DB y Telegram |
| HIGH | 4 | Problemas de confiabilidad significativos bajo carga o fallos |
| MEDIUM | 2 | Code smells con potenciales issues en edge cases |

---

## CRITICAL ISSUES

### [CRITICAL-001] Inconsistencia DB/Telegram en expulsión VIP - No hay rollback ni tracking de fallos

**Location:** `bot/services/subscription.py:557-601` (`kick_expired_vip_from_channel`)

**Current Code:**
```python
async def kick_expired_vip_from_channel(self, channel_id: str) -> int:
    # Buscar suscriptores expirados
    result = await self.session.execute(
        select(VIPSubscriber).where(
            VIPSubscriber.status == "expired"
        )
    )
    expired_subscribers = result.scalars().all()

    banned_count = 0
    for subscriber in expired_subscribers:
        try:
            # Banear del canal (permanente - sin unban)
            await self.bot.ban_chat_member(
                chat_id=channel_id,
                user_id=subscriber.user_id
            )
            banned_count += 1
            logger.info(f"🚫 Usuario baneado...")

        except Exception as e:
            logger.warning(
                f"⚠️ No se pudo banear a user {_mask_user_id(subscriber.user_id)}: {e}"
            )
    # ...
    return banned_count
```

**Issue:**
1. El método busca TODOS los suscriptores con `status="expired"`, no solo los recién marcados en esta ejecución
2. Si `ban_chat_member` falla (usuario ya no en canal, permisos insuficientes, rate limit), el error se loguea pero **no hay mecanismo de reintento ni tracking**
3. No hay forma de identificar usuarios "expirados en DB pero no baneados en Telegram"
4. En reejecuciones, se reintenta banear a los mismos usuarios innecesariamente

**Impacto:**
- Usuarios expirados pueden permanecer en el canal VIP indefinidamente si el ban falla
- No hay visibilidad de cuántos usuarios están en estado inconsistente
- El admin no tiene forma de saber que hay "leaks" de seguridad

**Recommendation:**
```python
# Opción 1: Agregar flag 'kicked_from_channel' al modelo VIPSubscriber
# Opción 2: Crear tabla de tracking de operaciones pendientes
# Opción 3: Al menos distinguir entre errores retryables y permanentes

async def kick_expired_vip_from_channel(self, channel_id: str) -> Tuple[int, int, List[int]]:
    """Returns: (success_count, permanent_failures, retryable_failures)"""
    # Solo procesar expirados NO kicked aún
    result = await self.session.execute(
        select(VIPSubscriber).where(
            VIPSubscriber.status == "expired",
            VIPSubscriber.kicked_from_channel == False  # Nuevo campo
        )
    )
    # ...
```

---

### [CRITICAL-002] Race condition en aprobación de solicitudes Free - Doble procesamiento posible

**Location:** `bot/services/subscription.py:1005-1156` (`approve_ready_free_requests`)

**Current Code:**
```python
async def approve_ready_free_requests(self, wait_time_minutes: int, free_channel_id: str):
    # 1. SELECT de solicitudes listas
    result = await self.session.execute(
        select(FreeChannelRequest).where(
            FreeChannelRequest.processed == False,
            FreeChannelRequest.request_date <= cutoff_time
        )
    )
    ready_requests = result.scalars().all()

    # 2. Procesar una por una
    for request in ready_requests:
        try:
            await self.bot.approve_chat_join_request(...)  # API call
            # ...
            request.processed = True  # Marcado DESPUÉS de éxito
            request.processed_at = datetime.utcnow()
            # ...

    # 3. Commit al final
    await self.session.commit()
```

**Issue:**
1. **TOCTOU (Time-of-Check-Time-of-Use):** Entre el SELECT y el UPDATE, otra instancia del worker puede haber procesado la misma solicitud
2. No hay `max_instances=1` en el job de APScheduler (sí está configurado, pero no protege contra múltiples workers/procesos)
3. No se usa `SELECT FOR UPDATE` ni optimistic locking
4. Si el proceso se reinicia durante el loop, las solicitudes parcialmente procesadas quedan en estado inconsistente

**Impacto:**
- Misma solicitud puede ser aprobada múltiples veces (llamadas redundantes a Telegram API)
- Posible rate limiting por Telegram
- Logs confusos con múltiples "aprobaciones" del mismo usuario

**Recommendation:**
```python
# Usar UPDATE atómico con RETURNING para evitar race conditions
from sqlalchemy import update

async def approve_ready_free_requests_atomic(self, ...):
    # Marcar atómicamente las que vamos a procesar
    stmt = (
        update(FreeChannelRequest)
        .where(
            FreeChannelRequest.processed == False,
            FreeChannelRequest.request_date <= cutoff_time
        )
        .values(processed=True, processed_at=datetime.utcnow())
        .returning(FreeChannelRequest.user_id)
    )
    result = await self.session.execute(stmt)
    user_ids_to_process = result.scalars().all()
    await self.session.commit()  # Commit inmediato del marcado

    # Ahora procesar los user_ids (ya están marcados, no hay race)
    for user_id in user_ids_to_process:
        try:
            await self.bot.approve_chat_join_request(...)
        except Exception as e:
            # Log para investigación manual, pero no hay race condition
            logger.error(f"Fallo aprobación para {user_id}: {e}")
```

---

## HIGH ISSUES

### [HIGH-001] Uso de `datetime.utcnow()` en lugar de `datetime.now(timezone.utc).replace(tzinfo=None)`

**Location:** Múltiples ubicaciones

**Instances found:**
1. `bot/background/tasks.py:220` - `cleanup_expired_requests_after_restart`
2. `bot/services/subscription.py:423, 442, 475, 505, 553, 744, 818, 865, 878, 928, 953, 988, 1024, 1118, 1138, 1185`
3. `bot/services/channel.py:557` - `get_or_create_free_channel_invite_link`

**Current Code:**
```python
cutoff_time = datetime.utcnow() - timedelta(minutes=15)
```

**Issue:**
`datetime.utcnow()` retorna un datetime naive (sin timezone info). Aunque el código asume UTC, esto puede causar problemas si:
- La base de datos tiene configuración de timezone diferente
- Se migra a un servidor con configuración local diferente
- Se comparan con datetimes de otras fuentes (ej: Telegram API)

**Impacto:**
- Comparaciones de tiempo potencialmente incorrectas
- Comportamiento inconsistente en diferentes entornos
- Dificultad para debuggear problemas de timing

**Recommendation:**
```python
from datetime import datetime, timezone

# Consistente en todo el codebase
cutoff_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=15)
```

---

### [HIGH-002] Llamadas a Telegram API dentro de transacciones DB abiertas

**Location:** `bot/services/subscription.py:1005-1156`

**Current Code:**
```python
async def approve_ready_free_requests(self, ...):
    # Dentro de una sesión abierta desde el caller (tasks.py)

    # 1. SELECT de solicitudes
    result = await self.session.execute(...)

    # 2. Llamada a Telegram API (DENTRO de la transacción)
    for request in ready_requests:
        await self.bot.approve_chat_join_request(...)  # API externa

        # 3. Más llamadas API
        channel_link = await channel_service.get_or_create_free_channel_invite_link()

        # 4. Envío de mensaje
        await self.bot.send_message(...)

        request.processed = True

    # Commit al final
    await self.session.commit()
```

**Issue:**
1. La transacción DB permanece abierta durante llamadas a API externa (Telegram)
2. Si Telegram es lento o hay rate limiting, la transacción se mantiene abierta por segundos/minutos
3. En PostgreSQL, transacciones largas pueden causar:
   - Bloqueo de vacuum
   - Acumulación de dead tuples
   - Problemas de concurrencia
4. Si hay excepción en la API, toda la transacción se hace rollback, perdiendo el procesamiento de solicitudes exitosas previas

**Impacto:**
- Degradación de performance de base de datos
- Posible bloqueo de operaciones de mantenimiento
- Pérdida de trabajo válido si una solicitud falla

**Recommendation:**
```python
# Separar lectura/escritura DB de llamadas API

# 1. Obtener solicitudes a procesar (transacción corta)
async with get_session() as session:
    requests_to_process = await get_pending_requests(session)

# 2. Procesar fuera de transacción (llamadas API)
results = []
for request in requests_to_process:
    try:
        await self.bot.approve_chat_join_request(...)
        results.append((request.user_id, 'success'))
    except Exception as e:
        results.append((request.user_id, 'error', e))

# 3. Actualizar DB con resultados (nueva transacción corta)
async with get_session() as session:
    await update_request_statuses(session, results)
```

---

### [HIGH-003] Manejo genérico de excepciones en operaciones críticas de Telegram

**Location:** `bot/services/subscription.py:583-596`

**Current Code:**
```python
try:
    await self.bot.ban_chat_member(
        chat_id=channel_id,
        user_id=subscriber.user_id
    )
    banned_count += 1
except Exception as e:
    logger.warning(
        f"⚠️ No se pudo banear a user {_mask_user_id(subscriber.user_id)}: {e}"
    )
```

**Issue:**
1. Se captura `Exception` genérico sin distinguir entre:
   - `TelegramForbiddenError`: Bot no tiene permisos (error permanente)
   - `TelegramBadRequest`: Usuario no existe, ya no está en el canal (error permanente)
   - `TelegramRetryAfter`: Rate limiting (error temporal, debe reintentar)
   - `TelegramNetworkError`: Problema de red (error temporal)

2. No hay estrategia de backoff para rate limits
3. No hay distinción entre "no reintentar" vs "reintentar más tarde"

**Impacto:**
- Rate limits no manejados apropiadamente
- Posible bloqueo temporal de la cuenta del bot
- Operaciones que podrían reintentarse se marcan como fallidas permanentemente

**Recommendation:**
```python
from aiogram.exceptions import (
    TelegramForbiddenError,
    TelegramBadRequest,
    TelegramRetryAfter,
    TelegramNetworkError
)

async def kick_expired_vip_from_channel(self, channel_id: str) -> Tuple[int, List[int]]:
    retryable_failures = []

    for subscriber in expired_subscribers:
        try:
            await self.bot.ban_chat_member(chat_id=channel_id, user_id=subscriber.user_id)
            subscriber.kicked_from_channel = True  # Track success
            banned_count += 1

        except TelegramRetryAfter as e:
            # Rate limit - debe reintentar más tarde
            logger.warning(f"Rate limit, esperar {e.retry_after}s")
            retryable_failures.append(subscriber.user_id)
            break  # Detener para no acumular más rate limit

        except (TelegramForbiddenError, TelegramBadRequest) as e:
            # Error permanente - no reintentar
            logger.error(f"Error permanente baneando {subscriber.user_id}: {e}")
            subscriber.kicked_from_channel = True  # Marcar como "procesado" aunque falló

        except TelegramNetworkError as e:
            # Error de red - reintentable
            logger.warning(f"Error de red, reintentar más tarde: {e}")
            retryable_failures.append(subscriber.user_id)

    await self.session.commit()
    return banned_count, retryable_failures
```

---

### [HIGH-004] No hay paginación en operaciones bulk

**Location:** `bot/services/subscription.py:487-555`, `557-601`

**Current Code:**
```python
async def expire_vip_subscribers(self, ...):
    # Busca TODOS los suscriptores expirados sin límite
    result = await self.session.execute(
        select(VIPSubscriber).where(
            VIPSubscriber.status == "active",
            VIPSubscriber.expiry_date < datetime.utcnow()
        )
    )
    expired_subscribers = result.scalars().all()  # Sin límite
```

**Issue:**
1. Si hay miles de suscriptores expirados (ej: después de un downtime prolongado), se cargan todos en memoria
2. El procesamiento puede tomar horas, bloqueando el scheduler
3. No hay mecanismo de checkpoint/resume
4. Risk de OOM (Out of Memory)

**Impacto:**
- Consumo excesivo de memoria
- Tareas que exceden el intervalo de ejecución
- Misfires del scheduler

**Recommendation:**
```python
async def expire_vip_subscribers(self, batch_size: int = 100) -> int:
    total_expired = 0

    while True:
        # Procesar en batches
        result = await self.session.execute(
            select(VIPSubscriber)
            .where(
                VIPSubscriber.status == "active",
                VIPSubscriber.expiry_date < datetime.utcnow()
            )
            .limit(batch_size)
        )
        batch = result.scalars().all()

        if not batch:
            break

        for subscriber in batch:
            subscriber.status = "expired"
            total_expired += 1

        await self.session.commit()

        # Si procesamos un batch completo, probablemente hay más
        if len(batch) < batch_size:
            break

    return total_expired
```

---

## MEDIUM ISSUES

### [MEDIUM-001] Falta `misfire_grace_time` y `coalesce` en APScheduler jobs

**Location:** `bot/background/tasks.py:287-341`

**Current Code:**
```python
_scheduler.add_job(
    expire_and_kick_vip_subscribers,
    trigger=IntervalTrigger(minutes=Config.CLEANUP_INTERVAL_MINUTES, timezone="UTC"),
    args=[bot],
    id="expire_vip",
    name="Expulsar VIPs expirados",
    replace_existing=True,
    max_instances=1
)
```

**Issue:**
1. No se configura `misfire_grace_time`: Si el bot está caído durante un período, los jobs acumulados se ejecutarán todos al reiniciar
2. No se configura `coalesce`: Con `coalesce=False` (default), si hay múltiples ejecuciones pendientes, todas se ejecutarán
3. Para tareas de expiración VIP, ejecutar múltiples veces no es idempotente (logs duplicados, reintentos innecesarios)

**Impacto:**
- Storm de ejecuciones al reiniciar después de downtime
- Logs duplicados/confusos
- Carga innecesaria en la base de datos

**Recommendation:**
```python
_scheduler.add_job(
    expire_and_kick_vip_subscribers,
    trigger=IntervalTrigger(minutes=Config.CLEANUP_INTERVAL_MINUTES, timezone="UTC"),
    args=[bot],
    id="expire_vip",
    name="Expulsar VIPs expirados",
    replace_existing=True,
    max_instances=1,
    misfire_grace_time=300,  # 5 minutos de gracia
    coalesce=True  # Si hay múltiples pendientes, ejecutar solo una
)
```

---

### [MEDIUM-002] No hay verificación de permisos antes de `ban_chat_member`

**Location:** `bot/services/subscription.py:583-588`

**Current Code:**
```python
await self.bot.ban_chat_member(
    chat_id=channel_id,
    user_id=subscriber.user_id
)
```

**Issue:**
1. No se verifica si el bot tiene permisos de administrador antes de intentar banear
2. No se verifica si el usuario está realmente en el canal
3. Cada llamada fallida consume quota de la API de Telegram

**Impacto:**
- Llamadas innecesarias a API
- Logs de error que dificultan el monitoreo
- Posible rate limiting

**Recommendation:**
```python
# Verificar permisos antes de operaciones masivas
channel_service = ChannelService(self.session, self.bot)
can_manage, msg = await channel_service.verify_bot_permissions(channel_id)

if not can_manage:
    logger.error(f"Bot no tiene permisos para banear: {msg}")
    return 0

# Opcionalmente verificar si usuario está en el canal primero
try:
    member = await self.bot.get_chat_member(channel_id, subscriber.user_id)
    if member.status in ['left', 'kicked']:
        continue  # Ya no está, marcar como kicked
except:
    pass  # No se pudo verificar, intentar banear de todos modos
```

---

## OBSERVACIONES POSITIVAS

1. **Session Management Correcto:** Las tareas de background usan `async with get_session() as session` garantizando cleanup

2. **max_instances=1 Configurado:** Todos los jobs de APScheduler tienen `max_instances=1` para prevenir overlap

3. **Timezone UTC Consistente:** APScheduler configurado con `timezone="UTC"` en todos los triggers

4. **Manejo de Errores en ChannelService:** Los métodos de `channel.py` capturan excepciones específicas de Telegram (`TelegramForbiddenError`, `TelegramBadRequest`)

5. **Shutdown Graceful:** `stop_background_tasks()` usa `wait=False` para permitir shutdown rápido

---

## RECOMMENDATIONS PRIORITY

### 1. CRITICAL - Fix Immediately
- [CRITICAL-002] Implementar UPDATE atómico con RETURNING para evitar race conditions en procesamiento Free
- [CRITICAL-001] Agregar tracking de usuarios "expirados pero no baneados" para reintento manual

### 2. HIGH - Fix Before Production Scale
- [HIGH-002] Separar transacciones DB de llamadas API de Telegram
- [HIGH-003] Implementar manejo específico de excepciones de Telegram con retry logic
- [HIGH-004] Implementar paginación/batching en operaciones bulk
- [HIGH-001] Migrar de `datetime.utcnow()` a `datetime.now(timezone.utc).replace(tzinfo=None)`

### 3. MEDIUM - Address in Next Sprint
- [MEDIUM-001] Configurar `misfire_grace_time` y `coalesce` en jobs de APScheduler
- [MEDIUM-002] Verificar permisos antes de operaciones masivas de ban

---

## AGENT MEMORY NOTES

### Patterns Found in This Codebase

**Session Factory Pattern:**
- Uso correcto de `async with get_session() as session:` en tareas de background
- `SessionContextManager` en `engine.py` maneja commit/rollback automáticamente

**APScheduler Configuration:**
- `max_instances=1` configurado para prevenir overlap
- Falta `misfire_grace_time` y `coalesce` en jobs

**Telegram API Error Handling:**
- `channel.py`: Captura específica de `TelegramForbiddenError`, `TelegramBadRequest`
- `subscription.py`: Captura genérica de `Exception` en operaciones críticas (kick_expired_vip_from_channel)

**Database Transaction Boundaries:**
- Las tareas de background mantienen sesiones abiertas durante llamadas API (problema)
- No hay separación entre operaciones DB y operaciones externas

**Datetime Handling:**
- Uso predominante de `datetime.utcnow()` (naive)
- No hay mixing de naive/aware, pero el approach es legacy

**Idempotency:**
- `expire_vip_subscribers`: No idempotente (loguea cambios de rol múltiples veces si se reejecuta)
- `process_free_queue`: Parcialmente idempotente (marcado como procesado)
- `cleanup_old_data`: Idempotente (DELETE con condición)
