# 🔧 Fix Railway Migrations Error

## Problema Detectado

Railway tiene un estado de migración inconsistente. El error es:

```
KeyError: 'f9c06e9cc285'
```

Esto ocurre porque:
1. Railway tiene aplicada una migración que referencia `f9c06e9cc285`
2. Pero `f9c06e9cc285` no está en la cadena de migraciones actual de Railway
3. Hay migraciones duplicadas con diferentes IDs para el mismo propósito

## Causa Raíz

Existen DOS migraciones que crean la tabla `user_reactions`:
- `f9c06e9cc285` (20260210_044700_add_user_reactions_table_for_reaction_.py)
- `3d9f8a2e1b5c` → `f9c06e9cc285` → `20260211_000001`

Y la migración `20260211_000001` referencia `f9c06e9cc285` como padre, pero Railway perdió esa referencia.

## Solución (2 Opciones)

### Opción A: Stamp Head (Recomendada - Más Rápida)

Esta opción marca la base de datos de Railway como migrada hasta head sin ejecutar migraciones.

**Pasos:**

1. **Conectar a la base de datos PostgreSQL de Railway:**
   ```bash
   # Obtener DATABASE_URL de Railway
   railway variables get DATABASE_URL
   ```

2. **Hacer stamp head (marcar como migrada hasta head):**
   ```bash
   # En tu entorno local con la DATABASE_URL de Railway
   export DATABASE_URL="postgresql+asyncpg://..."
   alembic stamp head
   ```

3. **Verificar que el stamp funcionó:**
   ```bash
   alembic current
   # Debe mostrar: 20260221_000001 (head)
   ```

4. **Redeploy en Railway:**
   ```bash
   # Forzar nuevo deploy
   railway up
   ```

**Ventajas:**
- Rápido (5 minutos)
- No pierde datos existentes
- Alinea el estado de migraciones

**Riesgos:**
- Asume que las tablas ya existen en Railway
- Si hay diferencias de schema, puede haber errores en runtime

---

### Opción B: Reset Completo de Migraciones (Más Seguro)

Esta opción reconstruye el historial de migraciones desde cero.

**Pasos:**

1. **Backup de la base de datos (CRÍTICO):**
   ```bash
   # Exportar datos importantes
   pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
   ```

2. **Limpiar migraciones huérfanas:**
   
   Las siguientes migraciones parecen estar duplicadas o rotas:
   - `f9c06e9cc285` 
   - `3d9f8a2e1b5c`
   - `2bc8023392e7`
   
   Pero NO las elimines - son necesarias para el historial.

3. **Crear migración de reparación:**
   
   Crear `alembic/versions/20260223_000001_fix_migration_chain.py`:
   
   ```python
   """fix migration chain - stamp to correct head
   
   Revision ID: 20260223_000001
   Revises: 20260221_000001
   Create Date: 2026-02-23 00:00:00.000000+00:00
   
   """
   revision: str = '20260223_000001'
   down_revision: Union[str, None] = '20260221_000001'
   
   def upgrade() -> None:
       # Esta migración es un no-op
       # Solo existe para forzar el re-stamp
       pass
   
   def downgrade() -> None:
       pass
   ```

4. **Hacer stamp a la versión anterior al error:**
   ```bash
   # Stamp a la migración antes del error
   alembic stamp 8938058d20d3
   ```

5. **Aplicar migraciones hasta head:**
   ```bash
   alembic upgrade head
   ```

---

## Procedimiento Recomendado (Paso a Paso)

### Paso 1: Verificar Estado Actual en Railway

```bash
# Conectar a Railway
railway login

# Ver logs del error
railway logs --limit 50 | grep -E "(Migration|alembic|KeyError)"
```

### Paso 2: Obtener DATABASE_URL

```bash
# En Railway dashboard o CLI
railway variables get DATABASE_URL
```

### Paso 3: Probar Conexión Local

```bash
# Exportar DATABASE_URL
export DATABASE_URL="postgresql+asyncpg://postgres:...@postgres.railway.internal:5432/railway"

# Testear conexión
psql $DATABASE_URL -c "SELECT 1"
```

### Paso 4: Verificar Tablas Existentes

```bash
# Conectar a PostgreSQL
psql $DATABASE_URL

# Ver tablas
\dt

# Ver estado de migraciones
SELECT * FROM alembic_version;
```

### Paso 5: Ejecutar Stamp Head

```bash
# En tu máquina local
cd /path/to/adminpro
export DATABASE_URL="postgresql+asyncpg://..."

# Stamp head (marca como migrada hasta head sin ejecutar)
alembic stamp head

# Verificar
alembic current
# Debe mostrar: 20260221_000001 (head)
```

### Paso 6: Redeploy en Railway

```bash
# Forzar nuevo deploy
railway up

# O hacer commit y push
git add .
git commit -m "fix: stamp migrations to head"
git push origin gam
```

### Paso 7: Verificar Deploy

```bash
# Ver logs en tiempo real
railway logs --follow

# Verificar health check
curl https://tu-app.railway.app/health
```

---

## Si Stamp Head Falla

Si `alembic stamp head` falla, significa que hay un problema con el schema.

### Opción de Emergencia: Reset Total

**ADVERTENCIA:** Esto borra TODOS los datos.

```bash
# 1. Backup (si es posible)
pg_dump $DATABASE_URL > backup.sql

# 2. Drop todas las tablas
psql $DATABASE_URL << EOF
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
EOF

# 3. Aplicar migraciones desde cero
alembic upgrade head

# 4. Verificar
alembic current
```

---

## Verificación Post-Fix

Después de aplicar el fix, verifica:

```bash
# 1. Migración actual
alembic current
# Debe: 20260221_000001 (head)

# 2. Health check
curl https://tu-app.railway.app/health
# Debe: {"status": "healthy"}

# 3. Logs sin errores de migración
railway logs | grep -E "(ERROR|Migration)" | tail -20

# 4. Comandos de gamificación funcionan
# En Telegram: /daily_gift, /rewards, /shop
```

---

## Prevención Futura

Para evitar este problema en el futuro:

1. **Siempre verificar migraciones antes de deploy:**
   ```bash
   alembic current
   alembic history
   ```

2. **No eliminar migraciones aplicadas:**
   - Si necesitas revertir, usa `alembic downgrade`
   - No borres archivos `.py` de migraciones aplicadas

3. **Usar migraciones merge cuando haya branches:**
   ```bash
   alembic merge -m "merge feature branches"
   ```

4. **Testear migraciones en staging antes de producción:**
   ```bash
   # Crear base de datos de test
   createdb test_migrations
   
   # Testear migraciones
   DATABASE_URL=postgresql://localhost/test_migrations alembic upgrade head
   ```

---

## Resumen del Error

**Error:** `KeyError: 'f9c06e9cc285'`

**Causa:** Railway tiene una referencia a una migración que no existe en su árbol de migraciones

**Solución:** `alembic stamp head` para alinear el estado

**Tiempo estimado:** 5-10 minutos

**Riesgo:** Bajo (asumiendo que las tablas ya existen)
