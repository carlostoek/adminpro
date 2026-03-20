---
name: VIP Entry Race Condition Patterns
description: Patrones de race condition identificados en flujo VIP de 3 etapas
type: project
---

## Patrones de Race Condition Críticos Identificados

### 1. SELECT-CHECK-UPDATE Pattern (CRÍTICO)
**Ubicación:** `bot/services/vip_entry.py:advance_stage()`

El código lee el estado actual, valida condiciones, y luego actualiza. Esto es vulnerable a race conditions bajo carga concurrente.

**Patrón vulnerable:**
```python
result = await session.execute(select(Model).where(...))  # SELECT
obj = result.scalar_one_or_none()
if obj.stage == expected:  # CHECK
    obj.stage = new_stage   # UPDATE (en memoria)
```

**Fix aplicable:**
```python
result = await session.execute(
    update(Model)
    .where(Model.id == id, Model.stage == expected)  # Atomic check+update
    .values(stage=new_stage)
)
if result.rowcount != 1:
    raise ConcurrentModificationError()
```

### 2. Token Validation Without Invalidation (CRÍTICO)
**Ubicación:** `bot/services/vip_entry.py:is_entry_token_valid()`

Validar un token sin invalidarlo inmediatamente permite uso múltiple concurrente.

**Regla:** Todo token de un solo uso debe ser invalidado (NULL/used flag) en la MISMA operación atómica que lo valida.

### 3. Token Generation Race (CRÍTICO)
**Ubicación:** `bot/services/vip_entry.py:generate_entry_token()`

Verificar unicidad con SELECT antes de INSERT es no atómico. Usar constraint UNIQUE en BD y manejar IntegrityError.

## Contexto del Proyecto

**Stack:** aiogram 3 + SQLAlchemy 2.0 async + PostgreSQL/SQLite
**Flujo VIP:** 3 etapas (1→2→3→NULL) con token de un solo uso en etapa 3
**Middlewares:** AdminAuthMiddleware, DatabaseMiddleware

## Decisiones de Arquitectura Relevantes

1. **Session management:** DatabaseMiddleware usa `async with get_session()` con commit/rollback automático
2. **No FOR UPDATE:** El codebase no usa bloqueo pesimista en ningún lugar
3. **Optimistic locking:** No implementado (no hay version columns)
4. **Transaction boundary:** Cada handler tiene su propia transacción vía middleware

## Auditorías Relacionadas

- FASE 1.2: Services core (subscription, channel, config)
- FASE 1.3: Middlewares (admin_auth, database) - COMPLETADA
- Phase 13: VIP Entry Ritual (3-stage flow) - EN PROGRESO
