---
status: complete
phase: 21-daily-rewards-streaks
source:
  - 21-01-SUMMARY.md
  - 21-02-SUMMARY.md
  - 21-03-SUMMARY.md
  - 21-04-SUMMARY.md
  - 21-05-SUMMARY.md
  - 21-06-SUMMARY.md
  - 21-07-SUMMARY.md
started: 2026-02-13T00:00:00Z
updated: 2026-02-13T00:30:00Z
---

## Current Test

[testing complete - all issues resolved]

## Tests

### 1. Botón "Reclamar regalo diario" visible
expected: Al abrir el menú de usuario (VIP o Free), se muestra el botón "🎁 Reclamar regalo diario" en la parte superior cuando el regalo está disponible.
result: pass
note: "Fix aplicado: callback_data corregido de 'claim_daily_gift' a 'streak:claim_daily'"

### 2. Comando /daily_gift funciona
expected: Al enviar /daily_gift, el bot responde con mensaje de Lucien (🎩) mostrando el botón para reclamar o el tiempo restante.
result: pass

### 3. Reclamar regalo diario - Base + Bonus
expected: Al tocar "Reclamar", se reciben besitos (base 20 + bonus por racha). El mensaje muestra desglose: base, bonus, y total.
result: pass
note: "Funciona, pero usuario sugiere que racha se muestre a partir del día 3 (no desde día 1)"

### 4. Incremento de racha
expected: Al reclamar día consecutivo, el contador de racha (🔥) aumenta en 1. Se muestra "🔥 X días" en el menú.
result: pass

### 5. Mensaje de Lucien con voz correcta
expected: Todos los mensajes del flujo de regalo diario usan 🎩 y tono formal de mayordomo, con referencias a Diana.
result: pass

### 6. Countdown hasta próximo regalo
expected: Después de reclamar, el botón cambia a "⏳ Próximo regalo en Xh Ym" o similar, indicando tiempo restante.
result: pass

### 7. No puede reclamar dos veces
expected: Intentar reclamar nuevamente el mismo día muestra mensaje indicando que ya se reclamó, con tiempo restante.
result: pass

### 8. Rachas de reacción separadas
expected: Las reacciones en contenido del canal incrementan una racha de reacción separada (no afecta racha de regalo diario).
result: pass

### 9. Visualización de racha en menú
expected: El menú de usuario muestra "🔥 X días" o "🔥 Sin racha" junto con el saldo de besitos.
result: pass

### 10. Racha se reinicia al perder día
expected: Si no se reclama un día, la racha vuelve a 1 (no 0) al reclamar nuevamente.
result: pass

### 11. Bonus máximo de 50 besitos
expected: A partir del día 25 de racha, el bonus se mantiene en 50 besitos (total 70 por reclamo).
result: skipped
reason: "Requiere llegar al día 25 de racha - no testeable manualmente en esta sesión. Cubierto por tests automatizados."

### 12. Job de expiración a medianoche UTC
expected: El sistema procesa rachas vencidas a medianoche UTC (background job), reseteando las de usuarios que no reclamaron.
result: skipped
reason: "Requiere esperar hasta medianoche UTC - no testeable manualmente. Cubierto por tests automatizados."

## Summary

total: 12
passed: 10
issues: 0
pending: 0
skipped: 2

## Gaps

[none - all resolved]

## Fix Applied

### Fix #1: Callback data mismatch
**Issue:** Botón del menú no respondía al tocar
**Root cause:** Mismatch en `callback_data` entre teclado y handler

| Componente | Valor anterior | Valor corregido |
|------------|---------------|-----------------|
| Teclado menú | `streak:claim_daily` | `streak:claim_daily` (correcto) |
| Handler | `claim_daily_gift` | `streak:claim_daily` (corregido) |
| Teclado /daily_gift | `claim_daily_gift` | `streak:claim_daily` (corregido) |

### Fix #2: Missing DatabaseMiddleware
**Issue:** Botón se quedaba "pensando" sin respuesta ni logs
**Root cause:** `streak_router` no tenía `DatabaseMiddleware` aplicado, necesario para inyectar `ServiceContainer`

**Cambio:**
```python
# bot/handlers/user/streak.py
from bot.middlewares import DatabaseMiddleware

streak_router = Router(name="streak")

# Apply middleware to this router (required for container injection)
streak_router.callback_query.middleware(DatabaseMiddleware())
```

**Files modificados:**
- `bot/handlers/user/streak.py` - Handler filter, keyboard callback_data, middleware
- `tests/handlers/test_streak_handlers.py` - Test expectation

**Tests:** 17/17 pasando

## Notes

- Sugerencia de mejora: Mostrar racha solo a partir del día 3 (no desde día 1)
- Tests 11 y 12 cubiertos por suite automatizada (40 tests pasando)
