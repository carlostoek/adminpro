# Auditoría de Seguridad: config.py, interest.py, content.py

**Fecha:** 2026-03-12
**Auditor:** config-interest-auditor
**Scope:** Servicios de configuración, intereses y contenido

---

## Resumen Ejecutivo

| Componente | Estado | Issues Críticos | Issues Warning |
|------------|--------|-----------------|----------------|
| config.py | ⚠️ WARNING | 0 | 3 |
| interest.py | ⚠️ WARNING | 0 | 4 |
| content.py | ✅ LIMPIO | 0 | 0 |

**Hallazgos Principales:**
1. Uso de `datetime.utcnow()` deprecado en múltiples archivos (Python 3.12+)
2. Race condition potencial en deduplicación de intereses (TOCTOU)
3. Falta de commit en operaciones de mark_as_attended
4. Falta de índice compuesto óptimo en UserInterest para queries frecuentes

---

## [WARNING] Uso de datetime.utcnow() deprecado

**Archivo:** interest.py, content.py, config.py (implícito en modelos)
**Líneas:** interest.py:141,147,347,441; content.py:106-107,288,317,342,366

**Descripción técnica:**
El código utiliza `datetime.utcnow()` que está deprecado en Python 3.12+. Aunque el modelo BotConfig usa el patrón correcto (`datetime.now(timezone.utc).replace(tzinfo=None)`), los servicios interest.py y content.py usan `datetime.utcnow()` directamente.

**Escenario de fallo:**
En Python 3.12+, `datetime.utcnow()` genera deprecation warnings. En futuras versiones podría ser removido. Además, puede causar inconsistencias de timezone si el servidor cambia de configuración.

**Impacto:**
- Deprecation warnings en logs
- Potencial fallo en futuras versiones de Python
- Inconsistencia con el patrón usado en modelos

**Fix recomendado:**
```python
from datetime import datetime, timezone

# Reemplazar:
datetime.utcnow()

# Por:
datetime.now(timezone.utc).replace(tzinfo=None)
```

---

## [WARNING] Race Condition en Deduplicación de Intereses (TOCTOU)

**Archivo:** interest.py
**Línea:** 119-164 (método register_interest)

**Descripción técnica:**
El método `register_interest()` implementa un patrón check-then-create que es vulnerable a race conditions:
1. Línea 128: SELECT para verificar interés existente
2. Línea 149-158: CREATE si no existe

Entre el SELECT y el INSERT, otro request concurrente puede crear el mismo interés, causando IntegrityError.

**Escenario de fallo:**
1. Usuario A hace clic en "Me interesa" (request 1)
2. Usuario A hace clic nuevamente rápidamente (request 2)
3. Ambos requests pasan el check de existencia simultáneamente
4. Ambos intentan crear el registro
5. Uno falla con IntegrityError o se crean duplicados (sin unique constraint apropiado)

**Impacto:**
- IntegrityError no manejado expuesto al usuario
- Posibles registros duplicados si no hay unique constraint en DB
- Inconsistencia en notificaciones (doble notificación al admin)

**Fix recomendado:**
Usar patrón UPSERT con `on_conflict_do_update` (PostgreSQL) o manejar IntegrityError:

```python
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

async def register_interest(self, user_id: int, package_id: int):
    try:
        # Intentar insertar directamente
        stmt = insert(UserInterest).values(
            user_id=user_id,
            package_id=package_id,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None)
        ).on_conflict_do_update(
            index_elements=['user_id', 'package_id'],
            set_=dict(created_at=datetime.now(timezone.utc).replace(tzinfo=None))
        )
        await self.session.execute(stmt)
        await self.session.commit()

        # Verificar si fue insert o update para notificación
        # ...
    except IntegrityError:
        await self.session.rollback()
        # Manejar error
```

O alternativamente, manejar el IntegrityError:
```python
from sqlalchemy.exc import IntegrityError

try:
    new_interest = UserInterest(...)
    self.session.add(new_interest)
    await self.session.flush()
    return (True, "created", new_interest)
except IntegrityError:
    await self.session.rollback()
    # Re-fetch y verificar debounce
    existing = await self._get_existing_interest(user_id, package_id)
    if existing and self._is_within_debounce_window(existing.created_at):
        return (False, "debounce", existing)
```

---

## [WARNING] Falta de Commit en mark_as_attended

**Archivo:** interest.py
**Línea:** 318-354

**Descripción técnica:**
El método `mark_as_attended()` modifica el objeto interest (líneas 346-347) pero nunca hace commit ni flush. Esto contradice el patrón documentado en content.py donde explícitamente NO se hace commit para dejar que el handler lo gestione.

**Escenario de fallo:**
Si el handler que llama a este método no hace commit explícito, los cambios se pierden silenciosamente.

**Impacto:**
- Intereses marcados como atendidos pero sin persistir
- Datos inconsistentes entre sesiones
- Posible pérdida de auditoría

**Fix recomendado:**
Agregar consistencia con el patrón del proyecto. Si los handlers gestionan transacciones, documentarlo explícitamente. Si no, agregar commit:

```python
# Opción 1: Agregar commit (si el service es autónomo)
interest.is_attended = True
interest.attended_at = datetime.now(timezone.utc).replace(tzinfo=None)
await self.session.commit()  # O flush() según el patrón

# Opción 2: Documentar explícitamente que el handler debe hacer commit
"""
Note:
    Este método NO hace commit. El handler debe gestionar la transacción
    con SessionContextManager o llamar session.commit() explícitamente.
"""
```

---

## [WARNING] Query Ineficiente en get_interest_stats

**Archivo:** interest.py
**Línea:** 373-420

**Descripción técnica:**
El método `get_interest_stats()` carga TODOS los registros de intereses en memoria para contar por tipo de paquete:

```python
stmt = select(UserInterest).options(...).join(ContentPackage)
result = await self.session.execute(stmt)
all_interests = result.scalars().all()  # Carga TODO en memoria

by_package_type = {}
for interest in all_interests:
    pkg_type = interest.package.category.value
    by_package_type[pkg_type] = by_package_type.get(pkg_type, 0) + 1
```

**Escenario de fallo:**
Con miles de intereses, esto consume memoria innecesariamente y es lento.

**Impacto:**
- Uso excesivo de memoria en producción
- Latencia en dashboard de estadísticas
- No escala con volumen de datos

**Fix recomendado:**
Usar GROUP BY en la base de datos:

```python
from sqlalchemy import func

stmt = select(
    ContentPackage.category,
    func.count(UserInterest.id)
).join(ContentPackage).group_by(ContentPackage.category)

result = await self.session.execute(stmt)
by_package_type = dict(result.all())
```

---

## [WARNING] Falta de Índice para Queries de Intereses Pendientes

**Archivo:** interest.py (modelo models.py)
**Línea:** 437-441 (UserInterest.__table_args__)

**Descripción técnica:**
El modelo UserInterest tiene índices individuales en user_id, package_id, e is_attended, pero no tiene un índice compuesto óptimo para la query más frecuente: "intereses pendientes ordenados por fecha".

La query en `get_interests(is_attended=False)` requiere:
1. Filtrar por is_attended=False
2. Ordenar por created_at DESC

Sin índice compuesto (is_attended, created_at), PostgreSQL debe hacer un seq scan o sort en memoria.

**Impacto:**
- Degradación de performance con muchos intereses
- Latencia en listado de intereses pendientes

**Fix recomendado:**
Agregar índice compuesto en el modelo:

```python
__table_args__ = (
    # ... índices existentes ...
    # Índice para queries de intereses pendientes ordenados por fecha
    Index('idx_interest_attended_created', 'is_attended', 'created_at'),
)
```

---

## [WARNING] Uso de getattr con Default en get_max_reward_besitos

**Archivo:** config.py
**Línea:** 730-750

**Descripción técnica:**
Los métodos `get_max_reward_besitos()` y `get_max_reward_vip_days()` usan `getattr()` con default en lugar de definir defaults en el modelo:

```python
return getattr(config, 'max_reward_besitos', 100)
```

Esto indica que las columnas pueden no existir en el schema actual (migración pendiente).

**Escenario de fallo:**
Si la columna no existe en la base de datos, el código funciona pero:
1. No se puede distinguir entre "columna no existe" vs "valor es NULL"
2. El default 100 puede no ser el valor configurado por el admin
3. Inconsistencia si el admin cambió el valor pero se retorna el default

**Impacto:**
- Comportamiento inconsistente
- Dificultad para debugging
- Potencial pérdida de configuración

**Fix recomendado:**
1. Asegurar que las columnas existan en el schema (migración)
2. Usar el valor directo con default del modelo:

```python
# En modelo:
max_reward_besitos = Column(Integer, default=100, nullable=False)

# En service:
return config.max_reward_besitos  # Siempre existe, default 100
```

---

## [INFO] Observaciones Positivas

### 1. Soft Delete Implementado Correctamente (content.py)
El servicio ContentService implementa soft delete correctamente:
- `is_active` flag con índice
- `deactivate_package()` y `activate_package()` métodos explícitos
- Queries respetan el flag `is_active` cuando es relevante

### 2. Validaciones de Input Robustas
- `create_package()` valida nombre vacío y precios negativos
- `set_wait_time()` valida mínimo 1 minuto
- `set_*_reactions()` valida límites de 1-10 reacciones

### 3. Patrón de No-Commit Consistente (content.py)
ContentService documenta explícitamente que no hace commit, dejando la gestión de transacciones al handler con SessionContextManager.

### 4. Índices Apropiados en UserInterest
El modelo tiene:
- Índice único compuesto (user_id, package_id) para deduplicación
- Índices individuales en campos de filtro frecuente
- Foreign keys con CASCADE delete

### 5. Uso de Numeric para Precios
ContentPackage usa `Numeric(10, 2)` en lugar de Float, evitando problemas de precisión con moneda.

### 6. Deduplicación con Ventana de Tiempo
InterestService implementa deduplicación con ventana de 5 minutos (DEBOUNCE_WINDOW_MINUTES), evitando spam de notificaciones.

---

## Recomendaciones Prioritarias

1. **Alta:** Reemplazar `datetime.utcnow()` con `datetime.now(timezone.utc).replace(tzinfo=None)` en interest.py y content.py
2. **Alta:** Agregar manejo de IntegrityError o usar UPSERT en register_interest()
3. **Media:** Agregar commit explícito o documentar patrón de transacción en mark_as_attended()
4. **Media:** Optimizar get_interest_stats() con GROUP BY
5. **Baja:** Agregar índice compuesto (is_attended, created_at) en UserInterest

---

## Notas de Auditoría

- No se encontraron issues críticos de seguridad (SQL injection, data corruption)
- No se encontraron race conditions críticas en ConfigService (patrón singleton simple)
- El código sigue buenas prácticas generales de SQLAlchemy async
- La arquitectura de soft delete está bien implementada
