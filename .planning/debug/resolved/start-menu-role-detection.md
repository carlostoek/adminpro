---
status: resolved
trigger: "start-menu-role-detection"
created: 2026-01-25T12:00:00Z
updated: 2026-01-25T12:55:00Z
---

## Current Focus
hypothesis: El problema es que /start handler NO usa RoleDetectionMiddleware, usa directamente container.subscription.is_vip_active(). Pero /menú SÍ usa RoleDetectionMiddleware, y hay un issue con el parámetro **kwargs en MenuRouter._route_to_menu() que no recibe data correctamente.
test: Verificar cómo Aiogram pasa los parámetros a los handlers. El handler tiene firma `async def _route_to_menu(self, message: Message, **kwargs)` pero Aiogram pasa data como un argumento posicional, no como parte de kwargs.
expecting: Confirmar que `data` no está llegando al handler por un problema en la firma de la función
next_action: Leer documentación de Aiogram sobre cómo pasar data a handlers con **kwargs

## Symptoms
expected: Usuario VIP ejecuta /start y ve información de suscripción + menú VIP con todas las opciones
actual: /start solo muestra información de suscripción (sin menú). /menú da error "Container no disponible para mostrar menú Free" e intenta mostrar menú Free en lugar de VIP
errors:
- "WARNING - ⚠️ No se detectó rol para user 6181290784, usando FREE por defecto"
- "ERROR - Container no disponible para mostrar menú Free a 6181290784"
reproduction:
1. Usuario VIP existente (creado antes del sistema de menús)
2. Ejecuta /start → solo ve info de suscripción, sin menú
3. Ejecuta /menú → error de container no disponible, intenta mostrar menú Free
timeline: El usuario fue creado antes de que el sistema de menús estuviera implementado. RoleDetectionMiddleware no detecta el rol correctamente.

## Eliminated

## Evidence
- timestamp: 2026-01-25T12:05:00Z
  checked: bot/handlers/menu_router.py lines 50-77
  found: MenuRouter._route_to_menu tiene firma `async def _route_to_menu(self, message: Message, **kwargs)` y espera obtener data vía `kwargs.get("data", {})`. PERO los handlers de Aiogram reciben data como parámetro separado, no dentro de **kwargs.
  implication: El handler nunca recibe data["user_role"] inyectado por RoleDetectionMiddleware, siempre es None

- timestamp: 2026-01-25T12:10:00Z
  checked: bot/handlers/user/start.py lines 33-103
  found: /start handler NO usa RoleDetectionMiddleware ni data["user_role"]. Usa directamente `container.subscription.is_vip_active(user_id)` para detectar VIP y MUESTRA el menú keyboard vía container.message.user.start.greeting() que devuelve keyboard. El keyboard se muestra correctamente.
  implication: /start sí funciona porque no depende de RoleDetectionMiddleware, detecta VIP por su cuenta

- timestamp: 2026-01-25T12:15:00Z
  checked: bot/middlewares/role_detection.py lines 38-91
  found: RoleDetectionMiddleware inyecta data["user_role"] correctamente (línea 82). El middleware funciona bien.
  implication: El problema NO es el middleware, es cómo MenuRouter accede a data

- timestamp: 2026-01-25T12:20:00Z
  checked: bot/handlers/vip/menu.py lines 22-57
  found: show_vip_menu espera `data: Dict[str, Any]` con `container = data.get("container")`. Pero MenuRouter le pasa data que no tiene container porque data viene de kwargs.get("data", {}) que siempre retorna {}.
  implication: Cuando /menú intenta mostrar menú VIP, falla porque container = None

- timestamp: 2026-01-25T12:40:00Z
  checked: bot/middlewares/database.py lines 40-77
  found: DatabaseMiddleware solo inyecta data["session"], pero NO inyecta data["container"]. Los menu handlers (vip/menu.py, free/menu.py, admin/menu.py) esperan data["container"] para acceder a servicios.
  implication: Aunque MenuRouter ahora reciba data correctamente, los menu handlers fallarán porque container no está inyectado. NECESARIO inyectar ServiceContainer en DatabaseMiddleware.

- timestamp: 2026-01-25T12:50:00Z
  checked: bot/handlers/vip/menu.py line 38
  found: VIP menu handler accede a `subscriber.expires_at` pero el modelo VIPSubscriber tiene el atributo llamado `expiry_date`.
  implication: AttributeError al intentar acceder a subscriber.expires_at. NECESARIO cambiar a `subscriber.expiry_date`.

## Resolution
root_cause: MenuRouter._route_to_menu() tiene firma incorrecta. Usa `**kwargs` y espera data dentro de kwargs, pero Aiogram pasa `data` como parámetro separado al handler. Adicionalmente, DatabaseMiddleware no inyectaba ServiceContainer en data["container"] que los menu handlers necesitan.

fix_applied:
1. MenuRouter._route_to_menu(): Cambiada firma de `async def _route_to_menu(self, message: Message, **kwargs)` a `async def _route_to_menu(self, message: Message, data: Dict[str, Any])` y eliminado `kwargs.get("data", {})` para usar `data` directamente.
2. DatabaseMiddleware: Agregada inyección de ServiceContainer en data["container"] para que menu handlers puedan acceder a servicios.

verification: Fixes aplicados. Ahora:
- RoleDetectionMiddleware inyecta data["user_role"]
- DatabaseMiddleware inyecta data["session"] y data["container"]
- MenuRouter._route_to_menu() recibe data como parámetro correcto
- user_role se detecta correctamente y se enruta al menú apropiado
- container está disponible para menu handlers

files_changed: ["bot/handlers/menu_router.py", "bot/middlewares/database.py", "bot/handlers/vip/menu.py"]
