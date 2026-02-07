---
phase: 011-corregir-vulnerabilidades-altas-004-006
plan: 01
type: execute
wave: 1
subsystem: security
completed: 2026-02-07
duration: 8min
tags: [security, config, webhook, ip-validation, fail-secure]

dependencies:
  requires: []
  provides: [secure-config, webhook-ip-validation]
  affects: []

tech-stack:
  added: []
  patterns:
    - fail-secure-defaults
    - ip-whitelist-validation
    - aiohttp-middleware

key-files:
  created:
    - bot/middlewares/webhook_auth.py
  modified:
    - config.py
    - main.py
    - bot/middlewares/__init__.py

decisions:
  - id: SEC-011-001
    description: "BOT_TOKEN sin valor por defecto - falla explícitamente si no está configurado"
    rationale: "Previene que el bot inicie con configuración insegura por omisión"
  - id: SEC-011-002
    description: "DATABASE_URL sin valor por defecto en producción"
    rationale: "Fuerza configuración explícita de base de datos en producción"
  - id: SEC-011-003
    description: "Validación temprana en import time con sys.exit(1)"
    rationale: "Fail-fast: el bot no puede iniciar con configuración incompleta"
  - id: SEC-011-004
    description: "IPs oficiales de Telegram documentadas en código"
    rationale: "149.154.160.0/20 y 91.108.4.0/22 según documentación oficial"
  - id: SEC-011-005
    description: "Soporte para X-Forwarded-For vía TRUST_X_FORWARDED_FOR env var"
    rationale: "Permite uso detrás de proxies/load balancers (Railway, etc.)"
---

# Quick Task 011: Corregir Vulnerabilidades ALTA-004 y ALTA-006

## Summary

Corrección de dos vulnerabilidades de severidad ALTA identificadas en el reporte de seguridad:

- **ALTA-004**: Valores por defecto inseguros en config.py (BOT_TOKEN="", DATABASE_URL con default)
- **ALTA-006**: Falta validación de IPs de Telegram en webhook (vulnerable a spoofing)

## Changes Made

### ALTA-004: Configuración Segura (Fail-Secure)

**Archivo:** `config.py`

Cambios:
1. `BOT_TOKEN`: Eliminado valor por defecto `""`, ahora es `os.getenv("BOT_TOKEN")` sin default
2. `DATABASE_URL`: En modo no-testing, requiere valor explícito (no hay default)
3. Validación temprana en import time: `sys.exit(1)` si faltan variables críticas
4. `validate_required_vars()`: Ahora detecta `None` además de string vacío

**Comportamiento:**
- Sin BOT_TOKEN: El bot falla inmediatamente al importar config.py
- Sin DATABASE_URL en producción: El bot falla inmediatamente
- Mensaje de error claro indica qué variable falta

### ALTA-006: Validación de IPs de Telegram

**Archivo:** `bot/middlewares/webhook_auth.py` (nuevo)

Implementación:
1. `TelegramIPValidationMiddleware`: Middleware aiohttp que valida IPs de origen
2. Rangos de IPs oficiales documentados:
   - 149.154.160.0/20
   - 91.108.4.0/22
3. Soporte para `X-Forwarded-For` (configurable vía `TRUST_X_FORWARDED_FOR`)
4. Logging de intentos de acceso desde IPs no autorizadas
5. Respuesta 403 Forbidden para IPs no válidas

**Archivo:** `main.py`

Cambios:
1. Importa `SimpleRequestHandler`, `setup_application` de aiogram
2. Importa `web` de aiohttp
3. Crea `web.Application()` con middleware de validación de IPs
4. Usa `AppRunner` y `TCPSite` en lugar de `dp.start_webhook()`
5. Integra `TelegramIPValidationMiddleware` en la cadena de middlewares

**Archivo:** `bot/middlewares/__init__.py`

- Exporta `TelegramIPValidationMiddleware`

## Verification

### ALTA-004

```bash
# Sin BOT_TOKEN - debe fallar
$ (unset BOT_TOKEN; python -c "import config")
CRITICAL: BOT_TOKEN no configurado. Configure BOT_TOKEN en .env
EXIT CODE: 1

# Con BOT_TOKEN válido - debe funcionar
$ python -c "import config; print('OK')"
OK
```

### ALTA-006

```python
from bot.middlewares.webhook_auth import TelegramIPValidationFilter

filter = TelegramIPValidationFilter()

# IPs válidas de Telegram
filter.is_valid_ip("149.154.160.1")    # True
filter.is_valid_ip("91.108.4.1")       # True

# IPs no válidas
filter.is_valid_ip("127.0.0.1")        # False
filter.is_valid_ip("192.168.1.1")      # False
```

## Security Impact

| Vulnerabilidad | Riesgo Anterior | Riesgo Actual |
|----------------|-----------------|---------------|
| ALTA-004 | Bot podía iniciar con token vacío o DB por defecto | Bot falla explícitamente si faltan credenciales |
| ALTA-006 | Cualquier IP podía enviar webhooks falsos | Solo IPs de Telegram pueden enviar webhooks |

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Hash | Message |
|------|---------|
| 01b51f7 | security(ALTA-004): eliminar valores por defecto inseguros en config.py |
| f9d5b0b | security(ALTA-006): implementar validación de IPs de Telegram en webhook |

## Next Steps

- Considerar implementar rate limiting adicional en webhook endpoint
- Evaluar uso de WEBHOOK_SECRET para validación adicional de peticiones
- Documentar configuración de TRUST_X_FORWARDED_FOR para despliegues en Railway
