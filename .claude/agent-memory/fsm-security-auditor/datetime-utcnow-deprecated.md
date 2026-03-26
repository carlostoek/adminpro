---
name: datetime.utcnow() Deprecated Pattern
description: Uso inconsistente de datetime.utcnow() vs timezone-aware datetime
type: project
---

## Problema Identificado

El codebase usa `datetime.utcnow()` (deprecated en Python 3.12+) mezclado con `datetime.now(timezone.utc).replace(tzinfo=None)`.

**Impacto:**
- Deprecation warnings en Python 3.12+
- Inconsistencias potenciales en comparaciones de tiempo
- Deuda técnica acumulada

## Conteo de Usos por Archivo

| Archivo | Usos de utcnow() | Severidad |
|---------|------------------|-----------|
| bot/services/stats.py | 20+ | Medium |
| bot/services/subscription.py | 15+ | High |
| bot/services/content.py | 5+ | Low |
| bot/services/interest.py | 5+ | Medium |
| bot/services/user_management.py | 2 | Medium |
| bot/services/role_change.py | 1 | Low |
| bot/services/vip_entry.py | 1 | High |

## Patrón Correcto Usado en el Proyecto

El modelo `VIPSubscriber` usa el patrón correcto:

```python
from datetime import datetime, timezone

# Correcto (usado en VIPSubscriber.is_expired)
datetime.now(timezone.utc).replace(tzinfo=None)

# Incorrecto (deprecated, usado en múltiples servicios)
datetime.utcnow()
```

## Fix Recomendado

Crear un utility module `bot/utils/datetime.py`:

```python
from datetime import datetime, timezone

def utc_now() -> datetime:
    """Return timezone-naive UTC datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
```

Reemplazar todos los usos de `datetime.utcnow()` con `utc_now()`.

## Notas

- PostgreSQL maneja bien datetime naive en UTC
- SQLite almacena como string, comportamiento consistente
- El `.replace(tzinfo=None)` es necesario para compatibilidad con columnas DateTime sin timezone
