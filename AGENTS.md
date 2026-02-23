# Gamification Review — Sistema de Agentes

## Cómo usar este archivo
Coloca este archivo en la raíz del proyecto como `AGENTS.md`.
Claude Code lo leerá automáticamente y sabrá cómo asignar tareas de revisión.

---

## Orchestrator

Cuando se solicite una revisión del sistema de gamificación:

1. Identifica el módulo afectado usando la tabla de rutas de abajo.
2. Ejecuta el agente correspondiente (o varios si la tarea cruza módulos).
3. Consolida los hallazgos en un reporte con este formato:

```
## Reporte de Revisión — [módulo] — [fecha]

### CRITICAL (bloquea funcionalidad o es exploit)
- [descripción + archivo + línea]

### WARNING (comportamiento incorrecto o bug latente)
- [descripción + archivo + línea]

### INFO (mejora o deuda técnica menor)
- [descripción + archivo + línea]
```

### Tabla de rutas por módulo

| Área | Archivos primarios | Agente |
|------|-------------------|--------|
| Balance / transacciones | `services/wallet.py` | economy |
| Reacciones | `services/reaction.py`, `handlers/*/reaction_handlers.py` | reactions |
| Streaks / daily gift | `services/streak.py`, `background/tasks.py` | streaks |
| Tienda | `services/shop.py`, `handlers/admin/shop_management.py` | shop |
| Recompensas | `services/reward.py`, `handlers/admin/reward_management.py` | rewards |
| Config admin | `handlers/admin/economy_config.py`, `services/config.py` | admin |
| Base de datos | `database/models.py`, `alembic/versions/` | database |

---

## Agent: economy

**Scope:** `bot/services/wallet.py`, `bot/database/models.py` (UserGamificationProfile, Transaction)

**Revisar:**
- Atomicidad real de earn/spend: las operaciones usan `UPDATE SET col = col + delta` pero el flush posterior al create de Transaction no está dentro de una transacción explícita — verificar que el commit de la sesión envuelve ambas operaciones.
- Race condition en `_get_or_create_profile`: es check-then-create, no atómico. Usar INSERT ... ON CONFLICT o manejar la IntegrityError.
- El `eval()` en `_evaluate_level_formula`: validar que la fórmula almacenada en DB nunca pueda contener código malicioso. Considerar reemplazarlo con un parser limitado (e.g., `asteval` o lógica hardcoded con parámetros).
- Level drift: `earn_besitos` no llama a `update_user_level`. Confirmar dónde y cuándo se actualiza `profile.level` y si puede mostrarse desincronizado al usuario.
- `get_transaction_history` hace dos queries separadas (count + paginated select). Verificar que ambas apliquen el mismo filtro `transaction_type`.

**Output esperado:** Lista de issues con severidad, archivo y línea.

---

## Agent: reactions

**Scope:** `bot/services/reaction.py`, handlers de reacciones bajo `bot/handlers/`

**Revisar:**
- Implementación del rate limit de 30s: ¿es in-memory o persiste en DB? Si es in-memory, se pierde al reiniciar el bot.
- Deduplicación: existe unique index `(user_id, content_id, emoji)` en DB — verificar que el handler maneja correctamente el IntegrityError sin exponer error al usuario.
- Límite diario de reacciones: `get_user_reactions_today()` — confirmar que usa UTC y que el corte de "día" es consistente con el job de expire_streaks.
- Verificación VIP en `add_reaction()`: ¿es una query adicional o se pasa como parámetro? Si es query, puede ser N+1 en canales con muchos posts.
- El callback de reacción debe manejar `callback_query.message` que puede ser None (mensaje muy antiguo en Telegram). Verificar que hay try/except apropiado.

**Output esperado:** Lista de issues con severidad, archivo y línea.

---

## Agent: streaks

**Scope:** `bot/services/streak.py`, `bot/background/tasks.py`

**Revisar:**
- Lógica de "día perdido": ¿compara `date` UTC o `datetime`? Si usa datetime, un claim a las 23:59 UTC y el siguiente a las 00:01 UTC podría considerarse mismo día dependiendo de la implementación.
- El job `expire_streaks` con CronTrigger: confirmar que el timezone es UTC explícito, no el timezone del servidor.
- Condición de reset a 1 vs reset a 0: cuando se pierde la racha, ¿el siguiente claim empieza en 1 (correcto) o requiere primero resetear a 0?
- StreakType.REACTION: ¿se actualiza la racha de reacciones en el mismo request que el earn_besitos, o en un job separado? Si es separado, puede haber desincronización.
- `can_claim_daily_gift()`: verificar que compara `date.today()` UTC y no local, especialmente en deploys en Railway que puede tener timezone distinto.

**Output esperado:** Lista de issues con severidad, archivo y línea.

---

## Agent: shop

**Scope:** `bot/services/shop.py`, `bot/handlers/admin/shop_management.py`

**Revisar:**
- Atomicidad de compra: `spend_besitos` + `deliver_content` deben estar en la misma transacción. Si `deliver_content` falla (Telegram no responde), ¿se hace rollback del gasto o el usuario pierde besitos?
- `deliver_content` envía archivos por DM: si el usuario bloqueó el bot, ¿qué pasa? Verificar manejo de `BotBlocked` exception.
- Descuento VIP (`vip_price`): ¿se valida en el momento del purchase que el usuario sigue siendo VIP, o solo al mostrar el catálogo?
- FSM de 6 pasos para crear producto: verificar que hay un timeout o cancel en cada estado, y que el estado se limpia si el admin abandona el flujo.
- `get_purchase_history` con `UserContentAccess`: verificar que no hay N+1 al cargar los productos asociados.

**Output esperado:** Lista de issues con severidad, archivo y línea.

---

## Agent: rewards

**Scope:** `bot/services/reward.py`, `bot/handlers/admin/reward_management.py`

**Revisar:**
- `check_rewards_on_event()`: ¿se llama correctamente en todos los puntos de entrada relevantes (daily claim, reaction, shop purchase)? Crear un mapa de dónde se llama.
- Lógica AND/OR de condiciones (condition_group): verificar el algoritmo de evaluación — grupo 0 = AND global, grupos > 0 = OR entre grupos. Testear edge case: reward con solo condiciones en grupo 1.
- Reward repetible: `is_repeatable=True` + `claim_window_hours` — verificar que el check de "ya reclamado en esta ventana" usa `last_claimed_at` y no `claimed_at`.
- Notificación automática con "voz de Lucien": verificar que usa `voice_linter.py` o el servicio de mensajes, no strings hardcodeados.
- Reward tipo VIP_EXTENSION: debe coordinar con SubscriptionService para extender la fecha. Verificar que no solo agrega días a `expiry_date` sino que también reactiva si estaba expirado.

**Output esperado:** Lista de issues con severidad, archivo y línea.

---

## Agent: admin

**Scope:** `bot/handlers/admin/economy_config.py`, `bot/handlers/admin/economy_stats.py`, `bot/handlers/admin/user_gamification.py`, `bot/services/config.py`

**Revisar:**
- Validación de fórmula de nivel al guardar desde admin: ¿se prueba la fórmula con un valor antes de persistirla, o puede guardarse una fórmula que rompe el cálculo de nivel para todos?
- Cambios de configuración (max_reactions_per_day, besitos_per_reaction): ¿se aplican inmediatamente o requieren restart? Si el config se cachea en el ServiceContainer, puede no aplicarse hasta el próximo startup.
- `economy_stats.py` con 12 métricas: verificar que las queries de agregación no hacen full table scan en tablas grandes (transactions, user_rewards).
- Protección de rutas admin: verificar que el `admin_auth.py` middleware protege consistentemente todos los handlers admin de gamificación.

**Output esperado:** Lista de issues con severidad, archivo y línea.

---

## Agent: database

**Scope:** `bot/database/models.py`, `alembic/versions/`

**Revisar:**
- Índices en queries frecuentes: `UserReaction(user_id, created_at)` para el daily limit, `Transaction(user_id, created_at)` para historial. Verificar que existen en migraciones.
- `onupdate=datetime.utcnow` en columnas `updated_at`: en SQLAlchemy async, este trigger puede no dispararse en bulk updates. Verificar en wallet.py donde se usa `update()` directo.
- Migración `20260211_000001_fix_reaction_unique_constraint`: revisar qué corrigió — sugiere que hubo un bug de deduplicación en producción.
- `BotConfig` como singleton (id=1): no hay enforcement a nivel DB de que solo exista 1 registro. Verificar que `ConfigService` siempre hace `WHERE id = 1` y no `first()` que podría devolver un registro corrompido.
- Consistencia de `datetime.utcnow` vs `datetime.now(UTC)`: en Python 3.12+ `utcnow()` está deprecado. Verificar si hay impacto en el entorno de deploy.

**Output esperado:** Lista de issues con severidad, archivo y línea.

---

## Notas de contexto para todos los agentes

- El bot corre en Railway (ver `Railway.toml`), timezone puede diferir del UTC que asumen los modelos.
- `ServiceContainer` usa lazy loading — los servicios de gamificación (`wallet`, `reaction`, `streak`, `shop`, `reward`) comparten la misma `AsyncSession` por request. Esto es correcto para transacciones atómicas pero significa que un error en un servicio afecta a los demás.
- Existe `voice_linter.py` en utils — todos los mensajes al usuario deben pasar por él o por `LucienVoiceService`. Reportar como WARNING cualquier string hardcodeado en handlers de gamificación.
- El proyecto tiene `htmlcov/` — revisar cobertura antes de marcar algo como "no testeado".
