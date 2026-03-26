---
phase: 011-corregir-vulnerabilidades-altas-004-006
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - config.py
  - main.py
  - bot/middlewares/webhook_auth.py
autonomous: true

must_haves:
  truths:
    - "BOT_TOKEN no tiene valor por defecto inseguro (string vacio)"
    - "DATABASE_URL no tiene valor por defecto inseguro en produccion"
    - "El bot falla explicitamente si faltan variables requeridas"
    - "El webhook valida que las peticiones vengan de IPs oficiales de Telegram"
    - "Peticiones a webhook desde IPs no autorizadas son rechazadas con 403"
  artifacts:
    - path: "config.py"
      provides: "Configuracion sin valores por defecto inseguros"
      changes:
        - "BOT_TOKEN: str = os.getenv('BOT_TOKEN')  # Sin default"
        - "DATABASE_URL: validacion explicita en no-testing"
    - path: "bot/middlewares/webhook_auth.py"
      provides: "Middleware de validacion de IPs de Telegram"
      exports: ["TelegramIPValidationMiddleware"]
    - path: "main.py"
      provides: "Integracion del middleware en el webhook"
      changes:
        - "Importar TelegramIPValidationMiddleware"
        - "Aplicar middleware al webhook endpoint"
  key_links:
    - from: "main.py"
      to: "bot/middlewares/webhook_auth.py"
      via: "import y uso en dp.start_webhook"
    - from: "config.py"
      to: "bot startup"
      via: "Config.validate() falla si faltan vars requeridas"
---

<objective>
Corregir las vulnerabilidades de severidad ALTA del reporte de seguridad:
- ALTA-004: Valores por defecto inseguros en config.py (BOT_TOKEN="", DATABASE_URL)
- ALTA-006: Falta validacion de IPs de Telegram en webhook

Purpose: Eliminar vectores de ataque por configuracion insegura y spoofing de webhooks
Output: Configuracion segura sin defaults inseguros + validacion de IPs de Telegram
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@/data/data/com.termux/files/home/repos/adminpro/config.py
@/data/data/com.termux/files/home/repos/adminpro/main.py
</context>

<tasks>

<task type="auto">
  <name>Tarea 1: Eliminar valores por defecto inseguros en config.py (ALTA-004)</name>
  <files>config.py</files>
  <action>
    Corregir ALTA-004 - Valores por defecto inseguros:

    1. Linea 26: Cambiar BOT_TOKEN para que NO tenga valor por defecto:
       - De: BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
       - A: BOT_TOKEN: str = os.getenv("BOT_TOKEN")  # Sin default - debe estar en .env

    2. Lineas 64-68: Modificar logica de DATABASE_URL:
       - Mantener el comportamiento especial para testing mode (in-memory)
       - En modo NO-testing: NO usar valor por defecto, requerir explicitamente DATABASE_URL
       - Cambiar logica para que si no esta en testing y no hay DATABASE_URL, falle explicitamente

    3. Actualizar validate_required_vars() si es necesario para manejar None en lugar de string vacio

    4. Agregar validacion temprana en import time que falle si BOT_TOKEN es None o vacio
       (evita que el bot inicie con configuracion insegura)

    Agente especializado recomendado: security-architecture-auditor
    - Enfocado en configuracion segura
    - Validacion de secrets management
    - Fail-secure defaults
  </action>
  <verify>
    - python -c "import os; os.environ.pop('BOT_TOKEN', None); os.environ.pop('DATABASE_URL', None); import config" debe fallar con error claro
    - python -c "import os; os.environ['BOT_TOKEN']='test_token_12345'; os.environ['DATABASE_URL']='sqlite+aiosqlite:///test.db'; import config; print('OK')" debe funcionar
  </verify>
  <done>
    - BOT_TOKEN no tiene valor por defecto (usa os.getenv("BOT_TOKEN") sin default)
    - DATABASE_URL requiere valor explicito en produccion (no-testing)
    - El bot falla explicitamente al importar si faltan variables requeridas
    - Mensaje de error claro indica que variables faltan
  </done>
</task>

<task type="auto">
  <name>Tarea 2: Implementar validacion de IPs de Telegram en webhook (ALTA-006)</name>
  <files>bot/middlewares/webhook_auth.py, main.py</files>
  <action>
    Corregir ALTA-006 - Falta validacion de IPs de Telegram:

    1. Crear nuevo archivo bot/middlewares/webhook_auth.py:
       - Definir lista de rangos de IPs oficiales de Telegram para webhooks
         (Documentados en https://core.telegram.org/bots/webhooks)
       - Implementar TelegramIPValidationMiddleware
       - Validar IP de origen de cada request contra la lista blanca
       - Retornar 403 Forbidden si la IP no esta autorizada
       - Logging de intentos de acceso desde IPs no autorizadas

    2. IPs oficiales de Telegram (documentadas):
       - 149.154.160.0/20
       - 91.108.4.0/22
       (Verificar lista actualizada en documentacion de Telegram)

    3. Modificar main.py:
       - Importar TelegramIPValidationMiddleware
       - Aplicar el middleware al webhook endpoint antes de procesar updates
       - Asegurar que se ejecute antes de cualquier procesamiento de mensajes

    4. Considerar headers X-Forwarded-For si el bot esta detras de proxy/load balancer
       (Railway, etc.) - validar IP real vs IP del proxy

    Agente especializado recomendado: telegram-auth-auditor
    - Enfocado en autenticacion de webhooks de Telegram
    - Validacion de IPs y headers
    - Seguridad de APIs de Telegram
  </action>
  <verify>
    - python -c "from bot.middlewares.webhook_auth import TelegramIPValidationMiddleware; print('Import OK')"
    - Crear test simple que simule request desde IP no autorizada (127.0.0.1) y verifique que se rechaza
    - Crear test que simule request desde IP autorizada (149.154.160.1) y verifique que pasa
  </verify>
  <done>
    - Archivo bot/middlewares/webhook_auth.py creado con middleware de validacion
    - Lista de IPs de Telegram definida y documentada
    - Middleware integrado en main.py para modo webhook
    - Requests desde IPs no autorizadas retornan 403
    - Logging de intentos de acceso no autorizados
  </done>
</task>

</tasks>

<verification>
1. Verificar ALTA-004 corregida:
   - Sin BOT_TOKEN en .env: el bot debe fallar al iniciar con mensaje claro
   - Sin DATABASE_URL en produccion: el bot debe fallar al iniciar
   - Con ambos configurados: el bot inicia normalmente

2. Verificar ALTA-006 corregida:
   - Webhook rechaza peticiones desde IPs no Telegram
   - Webhook acepta peticiones desde IPs oficiales de Telegram
   - Headers X-Forwarded-For manejados correctamente si aplica
</verification>

<success_criteria>
- [ ] config.py no tiene valores por defecto inseguros para BOT_TOKEN ni DATABASE_URL
- [ ] El bot falla explicitamente si faltan variables requeridas (fail-secure)
- [ ] bot/middlewares/webhook_auth.py existe y valida IPs de Telegram
- [ ] main.py integra el middleware de validacion de IPs
- [ ] Peticiones a webhook desde IPs no autorizadas son rechazadas
</success_criteria>

<output>
After completion, create `.planning/quick/011-corregir-vulnerabilidades-altas-004-006/011-SUMMARY.md`
</output>
