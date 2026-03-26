# Phase 27 Context: Security Audit Fixes

## Phase Goal
Corregir los 29 hallazgos de seguridad identificados en la auditoría de seguridad del módulo de administración VIP/Free.

## User Decisions (LOCKED)

### Scope
- **Corregir TODOS los issues:** 8 críticos + 21 warnings
- **Tanda 1 (Críticos):** Issues de race condition que permiten bypass económico
- **Tanda 2 (Altos):** Inconsistencias DB/Telegram, transacciones largas
- **Tanda 3 (Warnings):** Deuda técnica y optimizaciones

### Priorización
1. **Inmediata:** Race conditions en tokens, VIP entry, aprobaciones Free
2. **Alta:** Inconsistencias DB/Telegram, transacciones largas
3. **Media:** datetime.utcnow(), rate limiting, paginación

### Estrategia de Implementación
- Usar UPDATE atómico con rowcount check para race conditions
- Separar transacciones DB de llamadas Telegram API
- Agregar constraints UNIQUE a nivel de base de datos
- Implementar SELECT FOR UPDATE donde sea necesario

## Claude's Discretion

### Elecciones de Implementación
- Orden de corrección dentro de cada tanda
- Refactorización opcional de código duplicado
- Nivel de logging adicional para debugging

### Patrones a Seguir
- SQLAlchemy 2.0 async patterns
- PostgreSQL UPSERT (ON CONFLICT)
- SKIP LOCKED para procesamiento concurrente

## Deferred Ideas (Out of Scope)

- Migración completa a PostgreSQL (ya en uso)
- Redis para caching (futuro)
- Rate limiting distribuido (futuro)
- Tests de estrés concurrente (post-fixes)

## Critical Issues Summary

### C-001: Race Condition en redeem_vip_token
- **Archivo:** subscription.py:216-312
- **Problema:** Token puede ser canjeado múltiples veces
- **Fix:** UPDATE atómico con rowcount check

### C-002: Race Condition en create_free_request
- **Archivo:** subscription.py:713-754
- **Problema:** Múltiples solicitudes por usuario posible
- **Fix:** SELECT FOR UPDATE + constraint UNIQUE

### C-003: Inconsistencia DB/Telegram kick_expired_vip
- **Archivo:** subscription.py:557-601
- **Problema:** Usuarios expirados no baneados = huérfanos
- **Fix:** Campo tracking + reintentos

### C-004: Race Condition approve_ready_free_requests
- **Archivo:** subscription.py:1005-1156
- **Problema:** Doble procesamiento de solicitudes
- **Fix:** UPDATE con RETURNING

### C-005: TOCTOU en advance_stage VIP
- **Archivo:** vip_entry.py:~80-150
- **Problema:** Progresión de etapas duplicada
- **Fix:** UPDATE condicional con rowcount

### C-006: Race Condition validación token VIP
- **Archivo:** vip_entry.py:~40-80
- **Problema:** Token reusable durante flujo
- **Fix:** Marcar "en uso" inmediatamente

### C-007: Atomicity failure cambios de rol
- **Archivo:** user_management.py
- **Problema:** Estado inconsistente si falla Telegram
- **Fix:** Reordenar: Telegram primero, luego DB

### C-008: Transacción larga con llamadas Telegram
- **Archivo:** subscription.py:1005-1156
- **Problema:** Locks prolongados en PostgreSQL
- **Fix:** Separar fases SELECT/API/UPDATE

## Files to Modify

### High Priority
- bot/services/subscription.py
- bot/services/vip_entry.py
- bot/services/user_management.py

### Medium Priority
- bot/background/tasks.py
- bot/services/channel.py

### Lower Priority
- bot/services/interest.py
- bot/services/config.py
- bot/services/content.py
- bot/middlewares/admin_auth.py
- bot/middlewares/database.py

## Database Changes Required

```sql
-- Constraint para prevenir múltiples solicitudes Free pendientes
ALTER TABLE free_channel_requests
ADD CONSTRAINT uq_pending_free_request
UNIQUE (user_id, processed)
WHERE processed = false;

-- Campo para tracking de baneos
ALTER TABLE vip_subscribers
ADD COLUMN kicked_from_channel BOOLEAN DEFAULT false;

-- Índice para búsquedas eficientes
CREATE INDEX idx_vip_expired_not_kicked
ON vip_subscribers(status, kicked_from_channel)
WHERE status = 'expired' AND kicked_from_channel = false;
```

## Success Criteria

- [ ] Todos los tests existentes pasan
- [ ] No hay nuevos warnings de mypy/pyright
- [ ] Issues C-001 a C-008 corregidos y verificados
- [ ] datetime.utcnow() migrado a timezone-aware
- [ ] Rate limiting implementado en loops bulk
- [ ] Paginación en operaciones bulk > 100 registros
