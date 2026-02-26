---
phase: quick
plan: 12
type: execute
wave: 1
depends_on: []
files_modified:
  - bot/handlers/admin/users.py
  - bot/handlers/admin/interests.py
  - bot/handlers/admin/content.py
  - bot/handlers/user/shop.py
  - bot/handlers/user/streak.py
  - bot/handlers/user/rewards.py
  - bot/handlers/user/vip_entry.py
  - bot/handlers/user/start.py
  - bot/handlers/vip/callbacks.py
  - bot/handlers/free/callbacks.py
autonomous: true

must_haves:
  truths:
    - DatabaseMiddleware solo se aplica globalmente en main.py
    - No hay middlewares locales redundantes de DatabaseMiddleware
    - AdminAuthMiddleware se mantiene en routers de admin (necesario)
    - El bot funciona igual sin los middlewares locales removidos
  artifacts:
    - path: "bot/handlers/admin/users.py"
      provides: "Sin DatabaseMiddleware local"
    - path: "bot/handlers/admin/interests.py"
      provides: "Sin DatabaseMiddleware local"
    - path: "bot/handlers/admin/content.py"
      provides: "Sin DatabaseMiddleware local"
    - path: "bot/handlers/user/shop.py"
      provides: "Sin DatabaseMiddleware local"
    - path: "bot/handlers/user/streak.py"
      provides: "Sin DatabaseMiddleware local"
    - path: "bot/handlers/user/rewards.py"
      provides: "Sin DatabaseMiddleware local"
    - path: "bot/handlers/user/vip_entry.py"
      provides: "Sin DatabaseMiddleware local"
    - path: "bot/handlers/user/start.py"
      provides: "Sin DatabaseMiddleware local"
    - path: "bot/handlers/vip/callbacks.py"
      provides: "Sin DatabaseMiddleware local"
    - path: "bot/handlers/free/callbacks.py"
      provides: "Sin DatabaseMiddleware local"
  key_links:
    - from: "main.py"
      to: "DatabaseMiddleware global"
      via: "dp.update.middleware(DatabaseMiddleware())"
---

<objective>
Eliminar middlewares locales redundantes de DatabaseMiddleware que ya se aplican globalmente en main.py.

Purpose: Simplificar el código y evitar duplicación innecesaria. DatabaseMiddleware ya se aplica globalmente a todas las actualizaciones en main.py, por lo que aplicarlo también a nivel de router es redundante.

Output: Handlers limpios sin middlewares locales de DatabaseMiddleware.
</objective>

<execution_context>
@/data/data/com.termux/files/home/.claude/get-shit-done/workflows/execute-plan.md
@/data/data/com.termux/files/home/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

## Análisis de Redundancia

**Global middlewares en main.py:324-326:**
```python
dp.update.middleware(DatabaseMiddleware())
dp.update.middleware(UserRegistrationMiddleware())
dp.update.middleware(RoleDetectionMiddleware())
```

**Middlewares locales redundantes a eliminar:**

1. `bot/handlers/admin/users.py:26-27` - DatabaseMiddleware (AdminAuthMiddleware se mantiene)
2. `bot/handlers/admin/interests.py:21` - DatabaseMiddleware (AdminAuthMiddleware se mantiene)
3. `bot/handlers/admin/content.py:28-29` - DatabaseMiddleware (AdminAuthMiddleware se mantiene)
4. `bot/handlers/user/shop.py:38-39` - DatabaseMiddleware
5. `bot/handlers/user/streak.py:30` - DatabaseMiddleware
6. `bot/handlers/user/rewards.py:29-30` - DatabaseMiddleware
7. `bot/handlers/user/vip_entry.py:46-47` - DatabaseMiddleware
8. `bot/handlers/user/start.py:29-30` - DatabaseMiddleware
9. `bot/handlers/vip/callbacks.py:30` - DatabaseMiddleware
10. `bot/handlers/free/callbacks.py:29` - DatabaseMiddleware

**Nota:** AdminAuthMiddleware NO se elimina en ningún archivo porque es necesario para proteger las rutas de administración, y solo se aplica a routers específicos de admin, no globalmente.
</context>

<tasks>

<task type="auto">
  <name>Limpiar middlewares locales en handlers de admin</name>
  <files>
    bot/handlers/admin/users.py
    bot/handlers/admin/interests.py
    bot/handlers/admin/content.py
  </files>
  <action>
    Eliminar las líneas que aplican DatabaseMiddleware localmente en los routers de admin.
    Mantener AdminAuthMiddleware (es necesario para protección de rutas admin).

    Archivo bot/handlers/admin/users.py:
    - Eliminar líneas 26-27 (users_router.callback_query.middleware(DatabaseMiddleware()) y users_router.message.middleware(DatabaseMiddleware()))
    - Mantener líneas 28-29 (AdminAuthMiddleware)

    Archivo bot/handlers/admin/interests.py:
    - Eliminar línea 21 (interests_router.callback_query.middleware(DatabaseMiddleware()))
    - Mantener líneas 22-23 (AdminAuthMiddleware)

    Archivo bot/handlers/admin/content.py:
    - Eliminar líneas 28-29 (content_router.callback_query.middleware(DatabaseMiddleware()) y content_router.message.middleware(DatabaseMiddleware()))
    - Mantener líneas 30-31 (AdminAuthMiddleware)
  </action>
  <verify>
    grep -n "DatabaseMiddleware" bot/handlers/admin/users.py bot/handlers/admin/interests.py bot/handlers/admin/content.py
    # Debe retornar solo resultados de imports, no de aplicación de middleware
  </verify>
  <done>
    Los tres archivos de admin no tienen DatabaseMiddleware aplicado localmente, solo AdminAuthMiddleware.
  </done>
</task>

<task type="auto">
  <name>Limpiar middlewares locales en handlers de usuario</name>
  <files>
    bot/handlers/user/shop.py
    bot/handlers/user/streak.py
    bot/handlers/user/rewards.py
    bot/handlers/user/vip_entry.py
    bot/handlers/user/start.py
  </files>
  <action>
    Eliminar todas las líneas que aplican DatabaseMiddleware localmente en los handlers de usuario.

    Archivo bot/handlers/user/shop.py:
    - Eliminar líneas 38-39 (shop_router.callback_query.middleware(DatabaseMiddleware()) y shop_router.message.middleware(DatabaseMiddleware()))

    Archivo bot/handlers/user/streak.py:
    - Eliminar línea 30 (streak_router.callback_query.middleware(DatabaseMiddleware()))

    Archivo bot/handlers/user/rewards.py:
    - Eliminar líneas 29-30 (rewards_router.callback_query.middleware(DatabaseMiddleware()) y rewards_router.message.middleware(DatabaseMiddleware()))

    Archivo bot/handlers/user/vip_entry.py:
    - Eliminar líneas 46-47 (vip_entry_router.callback_query.middleware(DatabaseMiddleware()) y vip_entry_router.message.middleware(DatabaseMiddleware()))

    Archivo bot/handlers/user/start.py:
    - Eliminar líneas 29-30 (user_router.message.middleware(DatabaseMiddleware()) y user_router.callback_query.middleware(DatabaseMiddleware()))
  </action>
  <verify>
    grep -n "DatabaseMiddleware" bot/handlers/user/shop.py bot/handlers/user/streak.py bot/handlers/user/rewards.py bot/handlers/user/vip_entry.py bot/handlers/user/start.py
    # Debe retornar solo resultados de imports, no de aplicación de middleware
  </verify>
  <done>
    Los cinco archivos de usuario no tienen DatabaseMiddleware aplicado localmente.
  </done>
</task>

<task type="auto">
  <name>Limpiar middlewares locales en handlers VIP y Free</name>
  <files>
    bot/handlers/vip/callbacks.py
    bot/handlers/free/callbacks.py
  </files>
  <action>
    Eliminar las líneas que aplican DatabaseMiddleware localmente en los callbacks de VIP y Free.

    Archivo bot/handlers/vip/callbacks.py:
    - Eliminar línea 30 (vip_callbacks_router.callback_query.middleware(DatabaseMiddleware()))

    Archivo bot/handlers/free/callbacks.py:
    - Eliminar línea 29 (free_callbacks_router.callback_query.middleware(DatabaseMiddleware()))
  </action>
  <verify>
    grep -n "DatabaseMiddleware" bot/handlers/vip/callbacks.py bot/handlers/free/callbacks.py
    # Debe retornar solo resultados de imports, no de aplicación de middleware

    # Verificación final global:
    grep -rn "\.middleware(DatabaseMiddleware())" bot/handlers/
    # No debe retornar resultados (solo debe estar en main.py globalmente)
  </verify>
  <done>
    Los handlers de VIP y Free no tienen DatabaseMiddleware aplicado localmente.
    Verificación global confirma que DatabaseMiddleware solo se aplica en main.py.
  </done>
</task>

</tasks>

<verification>
1. Ejecutar grep para confirmar que no quedan middlewares locales de DatabaseMiddleware en handlers:
   `grep -rn "\.middleware(DatabaseMiddleware())" bot/handlers/`
   Resultado esperado: sin coincidencias

2. Verificar que el bot inicia correctamente (si es posible hacer smoke test)

3. Confirmar que AdminAuthMiddleware sigue aplicado en routers de admin:
   `grep -rn "\.middleware(AdminAuthMiddleware())" bot/handlers/admin/`
   Resultado esperado: coincidencias en users.py, interests.py, content.py, main.py, tests.py, profile.py
</verification>

<success_criteria>
- DatabaseMiddleware solo se aplica globalmente en main.py
- No hay aplicaciones locales de DatabaseMiddleware en ningún handler
- AdminAuthMiddleware permanece en todos los routers de admin
- El código es más limpio y mantenible
</success_criteria>

<output>
After completion, create `.planning/quick/12-limpiar-middlewares-locales-redundantes/12-SUMMARY.md`
</output>
