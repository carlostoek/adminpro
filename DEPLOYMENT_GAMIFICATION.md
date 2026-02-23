# 🚀 Despliegue del Módulo de Gamificación

## Resumen Ejecutivo

El módulo de gamificación está **listo para producción**. Esta guía verifica que la integración sea correcta y limpia antes de desplegar a Railway.

---

## ✅ Checklist de Integración Completada

### 1. Migraciones de Base de Datos

**Estado:** ✅ COMPLETADO

- **Migración Principal:** `20260221_000001_seed_gamification_data.py`
- **Revisión:** `20260217_000001` → `20260221_000001` (head)
- **Tipo:** DATA migration (seed de datos iniciales)

**Verificación:**
```bash
# Verificar migración actual
alembic current
# Debe mostrar: 20260221_000001 (head)

# Verificar historial
alembic history --verbose
# Debe mostrar la migración de gamificación como head

# Testear migración en limpio
alembic upgrade head
# Debe ejecutar sin errores
```

**Qué hace la migración:**
1. Actualiza `BotConfig` con configuración de economía (level_formula, besitos_per_reaction, etc.)
2. Crea `UserGamificationProfile` para usuarios existentes (backfill)
3. Inserta rewards por defecto (Primeros Pasos, Ahorrador, Racha 7 Días)

**Idempotencia:** ✅ La migración es idempotente (segura para ejecutar múltiples veces)

---

### 2. Handlers Registrados

**Estado:** ✅ COMPLETADO

**Handlers de Gamificación:**
- `streak_router` - Regalo diario y rachas (`/daily_gift`)
- `rewards_router` - Lista y reclamo de recompensas (`/rewards`)
- `shop_router` - Tienda de contenido (`/shop`)
- `reaction_router` - Sistema de reacciones

**Registro en `bot/handlers/user/__init__.py`:**
```python
from bot.handlers.user.streak import streak_router
from bot.handlers.user.shop import shop_router
from bot.handlers.user.rewards import rewards_router

user_router.include_router(streak_router)
user_router.include_router(shop_router)
user_router.include_router(rewards_router)
```

**Comandos Disponibles:**
- `/daily_gift` - Reclamar regalo diario
- `/rewards` - Ver recompensas disponibles
- `/shop` - Tienda de contenido

---

### 3. Servicios Integrados

**Estado:** ✅ COMPLETADO

**Services en `ServiceContainer`:**

| Servicio | Propiedad | Dependencias |
|----------|-----------|--------------|
| `WalletService` | `container.wallet` | Ninguna |
| `StreakService` | `container.streak` | `wallet_service` |
| `ReactionService` | `container.reaction` | `wallet_service`, `streak_service` |
| `ShopService` | `container.shop` | `wallet_service` |
| `RewardService` | `container.reward` | `wallet_service`, `streak_service` |

**Inyección de Dependencias:**
```python
# En container.py
@property
def streak(self):
    if self._streak_service is None:
        from bot.services.streak import StreakService
        self._streak_service = StreakService(
            self._session,
            wallet_service=self.wallet  # Inyectado
        )
    return self._streak_service
```

---

### 4. Background Tasks

**Estado:** ✅ COMPLETADO

**Tarea de Expiración de Rachas:**
- **Función:** `expire_streaks()`
- **Schedule:** Diariamente a medianoche UTC (00:00)
- **Ubicación:** `bot/background/tasks.py`

**Implementación:**
```python
async def expire_streaks(bot: Bot):
    """Resetea rachas DAILY_GIFT y REACTION donde last_activity < hoy UTC"""
    async with get_session() as session:
        container = ServiceContainer(session, bot)
        
        # Process daily gift streak expirations
        daily_reset_count = await container.streak.process_streak_expirations()
        
        # Process reaction streak expirations
        reaction_reset_count = await container.streak.process_reaction_streak_expirations()
```

**Registro en `start_background_tasks()`:**
```python
_scheduler.add_job(
    expire_streaks,
    trigger=CronTrigger(hour=0, minute=0, timezone="UTC"),
    args=[bot],
    id="expire_streaks",
    name="Expiración de rachas diarias"
)
```

---

### 5. Modelos de Base de Datos

**Estado:** ✅ COMPLETADO

**Tablas de Gamificación en `bot/database/models.py`:**

| Tabla | Modelo | Descripción |
|-------|--------|-------------|
| `user_gamification_profiles` | `UserGamificationProfile` | Balance, nivel, estadísticas |
| `transactions` | `Transaction` | Audit trail de transacciones |
| `user_reactions` | `UserReaction` | Reacciones a contenido |
| `user_streaks` | `UserStreak` | Rachas diarias |
| `rewards` | `Reward` | Definición de recompensas |
| `reward_conditions` | `RewardCondition` | Condiciones para desbloquear |
| `user_rewards` | `UserReward` | Progreso de usuario |
| `content_sets` | `ContentSet` | Contenido para tienda |
| `shop_products` | `ShopProduct` | Productos de tienda |
| `user_content_access` | `UserContentAccess` | Acceso a contenido |

**Enums en `bot/database/enums.py`:**
- `TransactionType` - EARN_DAILY, EARN_REACTION, EARN_REWARD, SPEND_SHOP, etc.
- `StreakType` - DAILY_GIFT, REACTION
- `RewardType` - BESITOS, BADGE, CONTENT, VIP_EXTENSION
- `RewardConditionType` - STREAK_LENGTH, TOTAL_POINTS, FIRST_REACTION, etc.
- `RewardStatus` - LOCKED, UNLOCKED, CLAIMED, EXPIRED
- `ContentType` - PHOTO_SET, VIDEO, AUDIO, MIXED
- `ContentTier` - FREE, VIP, PREMIUM, GIFT

---

### 6. Configuración Railway

**Estado:** ✅ COMPLETADO

**Variables de Entorno Requeridas en Railway:**

```bash
# Telegram
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_USER_IDS=123456789,987654321

# Environment
ENV=production  # CRÍTICO: Habilita migraciones automáticas

# Database (PostgreSQL en Railway)
DATABASE_URL=postgresql+asyncpg://user:password@host.railway.app:5432/railway

# Webhook (Railway mode)
WEBHOOK_MODE=webhook
WEBHOOK_PATH=/webhook
# WEBHOOK_BASE_URL se auto-detecta desde RAILWAY_PUBLIC_DOMAIN

# Puertos (Railway los asigna automáticamente)
# PORT=8000 (asignado por Railway)
# HEALTH_PORT=8000

# Bot Settings
LOG_LEVEL=WARNING  # Producción: reducir ruido
DEFAULT_WAIT_TIME_MINUTES=5
CLEANUP_INTERVAL_MINUTES=60
PROCESS_FREE_QUEUE_MINUTES=5
```

**Railway.toml Configurado:**
```toml
[deploy]
healthcheckPath = "/health"
healthcheckPort = 8000
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
maxRestartRetries = 10
```

**Dockerfile Listo:**
- Multi-stage build (builder + runtime)
- Usuario no-root (`botuser`)
- Health check configurado
- Python 3.11-slim

---

## 🔍 Verificación Pre-Despliegue

### Tests Locales

```bash
# 1. Verificar migraciones
alembic current
alembic history --verbose
alembic upgrade head

# 2. Ejecutar tests
pytest tests/ -v

# 3. Verificar configuración
python -c "from config import Config; print(Config.get_summary())"

# 4. Testear servicios críticos
python -c "
from bot.database import get_session
from bot.services.container import ServiceContainer
from aiogram import Bot
import asyncio

async def test():
    async with get_session() as session:
        bot = Bot(token='test')
        container = ServiceContainer(session, bot)
        
        # Test wallet service
        balance = await container.wallet.get_balance(123)
        print(f'Wallet OK: balance={balance}')
        
        # Test streak service
        can_claim, status = await container.streak.can_claim_daily_gift(123)
        print(f'Streak OK: can_claim={can_claim}')
        
        # Test reward service
        rewards = await container.reward.get_available_rewards(123)
        print(f'Reward OK: {len(rewards)} rewards')

asyncio.run(test())
"
```

### Comandos para Verificar en Producción

Después del despliegue en Railway:

```bash
# 1. Verificar logs de migración
railway logs | grep "Migration"

# 2. Verificar health check
curl https://tu-app.railway.app/health

# 3. Probar comandos de gamificación en Telegram
/daily_gift
/rewards
/shop
```

---

## 🚀 Pasos de Despliegue

### 1. Preparar GitHub

```bash
# Asegurar que todo está commiteado
git status
git add .
git commit -m "feat: gamification module ready for production"

# Push a GitHub
git push origin gam  # o la rama que uses
```

### 2. Configurar Railway

1. **Conectar repositorio de GitHub**
   - Ir a Railway.app
   - "New Project" → "Deploy from GitHub"
   - Seleccionar repositorio `adminpro`

2. **Configurar Variables de Entorno**
   ```
   ENV=production
   BOT_TOKEN=<tu_token>
   ADMIN_USER_IDS=<tus_admin_ids>
   DATABASE_URL=<postgresql_url_de_railway>
   WEBHOOK_MODE=webhook
   LOG_LEVEL=WARNING
   ```

3. **Configurar PostgreSQL**
   - "New" → "Database" → "Add PostgreSQL"
   - Railway genera `DATABASE_URL` automáticamente
   - Copiar URL y agregar en Variables

4. **Deploy**
   - Railway detecta `Dockerfile` automáticamente
   - Build inicia automáticamente
   - Esperar a que el deploy complete (~2-3 min)

### 3. Verificar Despliegue

```bash
# 1. Health check
curl https://tu-app.railway.app/health
# Debe retornar: {"status": "healthy"}

# 2. Logs de migración
railway logs | grep -E "(Migration|gamification|alembic)"
# Debe mostrar: "Running upgrade ... -> 20260221_000001"

# 3. Logs de startup
railway logs | grep -E "(Production mode|Background tasks|Streak)"
# Debe mostrar: "Production mode detected. Running migrations..."
#              "Background tasks iniciados correctamente"
#              "Tarea programada: Expiración de rachas (medianoche UTC)"
```

### 4. Probar Funcionalidad

En Telegram:

1. **Iniciar bot:** `/start`
2. **Reclamar regalo diario:** `/daily_gift`
   - Debe mostrar mensaje de Lucien
   - Debe otorgar besitos (20 base + streak bonus)
3. **Ver recompensas:** `/rewards`
   - Debe mostrar lista de recompensas disponibles
4. **Ver tienda:** `/shop`
   - Debe mostrar productos disponibles

---

## ⚠️ Puntos Críticos

### 1. Migración Automática

**CRÍTICO:** `ENV=production` es obligatorio para migraciones automáticas.

```python
# En bot/database/migrations.py
def is_production() -> bool:
    return os.getenv("ENV", "").lower() == "production"

async def run_migrations_if_needed() -> bool:
    if not is_production():
        logger.info("Development mode. Skipping migrations.")
        return True
    
    # Production: run migrations automatically
    await run_migrations("upgrade", "head")
```

**Sin `ENV=production`:**
- Las migraciones NO se ejecutan automáticamente
- El bot inicia pero puede fallar por schema incompleto
- **Solución:** Ejecutar manualmente `alembic upgrade head`

### 2. DATABASE_URL con Driver Correcto

**Formato correcto para PostgreSQL:**
```bash
# ✅ Correcto (asyncpg)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# ❌ Incorrecto (psycopg2)
DATABASE_URL=postgresql://user:pass@host:5432/db
```

Railway provee URL sin driver. Debes agregar `+asyncpg`:
```bash
# En Railway Variables
DATABASE_URL=postgresql+asyncpg://...
```

### 3. Webhook vs Polling

**Railway requiere WEBHOOK:**
```bash
WEBHOOK_MODE=webhook
# PORT=8000 (Railway lo asigna automáticamente)
# WEBHOOK_BASE_URL=https://tu-app.railway.app (auto-detectado)
```

**Desarrollo local usa POLLING:**
```bash
WEBHOOK_MODE=polling
```

### 4. Background Task de Expiración

**Verificar que esté registrada:**
```bash
railway logs | grep "expire_streaks"
# Debe mostrar: "Tarea programada: Expiración de rachas (medianoche UTC)"
```

**Si no está registrada:**
- Revisar `bot/background/tasks.py` → `start_background_tasks()`
- Verificar que `expire_streaks` se agrega al scheduler

---

## 📊 Monitoreo Post-Despliegue

### Logs Clave

```bash
# Migraciones
railway logs | grep -E "(alembic|Migration|upgrade)"

# Background tasks
railway logs | grep -E "(Background|scheduler|streak)"

# Errores críticos
railway logs | grep -E "(ERROR|CRITICAL|Exception)"

# Uso de servicios
railway logs | grep -E "(WalletService|StreakService|RewardService)"
```

### Health Check

```bash
# Endpoint
GET https://tu-app.railway.app/health

# Respuesta esperada
{
  "status": "healthy",
  "timestamp": "2026-02-23T00:00:00Z",
  "database": "connected",
  "bot": "running"
}
```

### Métricas de Gamificación

```sql
-- En Railway PostgreSQL console
-- Usuarios con perfil de gamificación
SELECT COUNT(*) FROM user_gamification_profiles;

-- Transacciones totales
SELECT COUNT(*) FROM transactions;

-- Recompensas reclamadas
SELECT COUNT(*) FROM user_rewards WHERE status = 'CLAIMED';

-- Rachas activas
SELECT COUNT(*) FROM user_streaks WHERE current_streak > 0;
```

---

## 🐛 Troubleshooting

### Problema: Migración falla en producción

**Síntoma:**
```
ERROR: Migration failed: Command 'alembic upgrade head' returned non-zero exit status 1
```

**Causas posibles:**
1. DATABASE_URL sin driver correcto
2. Tablas ya existen con schema diferente
3. Permisos insuficientes en PostgreSQL

**Solución:**
```bash
# 1. Verificar DATABASE_URL
echo $DATABASE_URL
# Debe incluir +asyncpg

# 2. Testear migración localmente
docker run --rm -e DATABASE_URL=$DATABASE_URL tu-imagen alembic upgrade head

# 3. Verificar logs detallados
railway logs --verbose
```

### Problema: Background tasks no se ejecutan

**Síntoma:**
```
No hay logs de "Expiración de rachas" a medianoche
```

**Causas posibles:**
1. Scheduler no se inicializó
2. Timezone incorrecto (debe ser UTC)
3. Error en `expire_streaks()`

**Solución:**
```bash
# 1. Verificar scheduler
railway logs | grep "Background tasks iniciados"

# 2. Verificar jobs programados
railway logs | grep "Tarea programada"

# 3. Testear manualmente (Python console)
from bot.background.tasks import expire_streaks
import asyncio
asyncio.run(expire_streaks(bot))
```

### Problema: Comandos de gamificación no responden

**Síntoma:**
```
/daily_gift no responde o da error
```

**Causas posibles:**
1. Handlers no registrados
2. ServiceContainer no inicializado
3. Error en base de datos

**Solución:**
```bash
# 1. Verificar handlers registrados
railway logs | grep "Handlers registrados correctamente"

# 2. Verificar servicios cargados
railway logs | grep "Lazy loading.*Service"

# 3. Buscar errores específicos
railway logs | grep -A 5 "daily_gift"
```

---

## 📝 Resumen de Archivos Clave

| Archivo | Propósito |
|---------|-----------|
| `alembic/versions/20260221_000001_seed_gamification_data.py` | Migración de gamificación |
| `bot/database/models.py` | Modelos de gamificación |
| `bot/database/enums.py` | Enums de gamificación |
| `bot/services/wallet.py` | Gestión de besitos |
| `bot/services/streak.py` | Rachas diarias |
| `bot/services/reward.py` | Recompensas y logros |
| `bot/services/shop.py` | Tienda de contenido |
| `bot/services/reaction.py` | Sistema de reacciones |
| `bot/handlers/user/streak.py` | Handlers de rachas |
| `bot/handlers/user/rewards.py` | Handlers de recompensas |
| `bot/handlers/user/shop.py` | Handlers de tienda |
| `bot/handlers/user/reactions.py` | Handlers de reacciones |
| `bot/background/tasks.py` | Background tasks (expiración) |
| `bot/services/container.py` | Service Container |
| `main.py` | Entry point del bot |
| `Railway.toml` | Configuración Railway |
| `Dockerfile` | Build de producción |

---

## ✅ Checklist Final Pre-Deploy

- [ ] Migración `20260221_000001` aplicada localmente
- [ ] Tests ejecutados sin errores
- [ ] `ENV=production` configurado en Railway
- [ ] `DATABASE_URL` con driver `+asyncpg`
- [ ] `WEBHOOK_MODE=webhook` configurado
- [ ] `BOT_TOKEN` y `ADMIN_USER_IDS` configurados
- [ ] PostgreSQL provisionado en Railway
- [ ] Dockerfile y Railway.toml verificados
- [ ] Health check endpoint accesible
- [ ] Logs de migración verificados
- [ ] Background tasks programados
- [ ] Comandos de gamificación probados

---

**Estado:** ✅ LISTO PARA PRODUCCIÓN

**Próximo paso:** Push a GitHub → Deploy en Railway → Verificar logs
