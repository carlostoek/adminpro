---
phase: quick
plan: 010
type: execute
wave: 1
depends_on: []
files_modified: [
  "bot/middlewares/admin_auth.py",
  "bot/handlers/admin/main.py",
  "bot/handlers/admin/content.py",
  "bot/handlers/admin/users.py",
  "bot/handlers/admin/interests.py",
  "bot/services/subscription.py",
  "bot/services/config.py"
]
autonomous: true
must_haves:
  truths:
    - "Todos los routers anidados incluyen AdminAuthMiddleware"
    - "AdminAuthMiddleware bloquea eventos no reconocidos en lugar de ejecutarlos"
    - "Los tokens VIP se loguean con máscara (primeros 4 caracteres)"
    - "DATABASE_URL se muestra sin credenciales en logs"
    - "User IDs y PII se loguean de forma anonimizada"
    - "Los errores internos no se exponen al usuario"
    - "Los mensajes de error no filtran estructura interna"
  artifacts:
    - path: "bot/middlewares/admin_auth.py"
      provides: "Validación de autenticación segura"
    - path: "bot/handlers/admin/main.py"
      provides: "Routers anidados con middleware correcto"
    - path: "bot/services/subscription.py"
      provides: "Logging seguro de tokens y PII"
    - path: "bot/services/config.py"
      provides: "Configuración sin exposición de credenciales"
  key_links:
    - from: "admin_router"
      to: "content_router, users_router, interests_router"
      via: "AdminAuthMiddleware en cada router"
---

<objective>
Corregir 7 vulnerabilidades críticas de seguridad identificadas en el reporte SECURITY_AUDIT_2026-02-07.md.

Purpose: Eliminar vectores de ataque que permiten bypass de autenticación, exposición de datos sensibles, y filtración de información interna.
Output: Código con prácticas de seguridad mejoradas y logging sanitizado.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@/data/data/com.termux/files/home/repos/adminpro/bot/middlewares/admin_auth.py
@/data/data/com.termux/files/home/repos/adminpro/bot/handlers/admin/main.py
@/data/data/com.termux/files/home/repos/adminpro/bot/handlers/admin/content.py
@/data/data/com.termux/files/home/repos/adminpro/bot/handlers/admin/users.py
@/data/data/com.termux/files/home/repos/adminpro/bot/handlers/admin/interests.py
@/data/data/com.termux/files/home/repos/adminpro/bot/services/subscription.py
@/data/data/com.termux/files/home/repos/adminpro/bot/services/config.py
</context>

<tasks>

<task type="auto">
  <name>Tarea 1: CRÍTICA-001 - Bypass de Autenticación en Routers Anidados</name>
  <files>bot/handlers/admin/main.py, bot/handlers/admin/content.py, bot/handlers/admin/users.py, bot/handlers/admin/interests.py</files>
  <action>
    Agregar AdminAuthMiddleware a los routers anidados que actualmente solo tienen DatabaseMiddleware.

    En bot/handlers/admin/content.py (líneas 27-29):
    - Agregar: from bot.middlewares import AdminAuthMiddleware
    - Agregar después de crear content_router:
      content_router.callback_query.middleware(AdminAuthMiddleware())
      content_router.message.middleware(AdminAuthMiddleware())

    En bot/handlers/admin/users.py (líneas 25-27):
    - Agregar: from bot.middlewares import AdminAuthMiddleware
    - Agregar después de crear users_router:
      users_router.callback_query.middleware(AdminAuthMiddleware())
      users_router.message.middleware(AdminAuthMiddleware())

    En bot/handlers/admin/interests.py (líneas 20-22):
    - Agregar: from bot.middlewares import AdminAuthMiddleware
    - Agregar después de crear interests_router:
      interests_router.callback_query.middleware(AdminAuthMiddleware())
      interests_router.message.middleware(AdminAuthMiddleware())

    NOTA: El comentario "AdminAuth already on admin_router" es incorrecto - los routers anidados NO heredan middleware del router padre.
  </action>
  <verify>
    Verificar que cada router anidado tenga ambos middlewares:
    grep -n "AdminAuthMiddleware()" bot/handlers/admin/content.py bot/handlers/admin/users.py bot/handlers/admin/interests.py
  </verify>
  <done>
    Los tres routers anidados (content_router, users_router, interests_router) tienen AdminAuthMiddleware aplicado a message y callback_query.
  </done>
</task>

<task type="auto">
  <name>Tarea 2: CRÍTICA-002 - Validación Incompleta de Eventos</name>
  <files>bot/middlewares/admin_auth.py</files>
  <action>
    Corregir AdminAuthMiddleware para bloquear eventos no reconocidos en lugar de ejecutarlos.

    En bot/middlewares/admin_auth.py (líneas 70-73):
    - Cambiar el comportamiento cuando user is None:

    ANTES:
    ```python
    if user is None:
        logger.warning("⚠️ No se pudo extraer usuario del evento")
        return await handler(event, data)
    ```

    DESPUÉS:
    ```python
    if user is None:
        logger.warning("⚠️ Acceso denegado: no se pudo extraer usuario del evento")
        # Bloquear acceso - no ejecutar handler
        return None
    ```

    Esto previene que eventos como ChatMemberUpdated, Poll, o InlineQuery ejecuten handlers admin sin autenticación.
  </action>
  <verify>
    Verificar que el código bloquee cuando user is None:
    grep -A 3 "if user is None:" bot/middlewares/admin_auth.py
  </verify>
  <done>
    El middleware retorna None (bloquea) cuando no puede extraer el usuario del evento.
  </done>
</task>

<task type="auto">
  <name>Tarea 3: CRÍTICA-003 - Tokens VIP Completos en Logs</name>
  <files>bot/services/subscription.py</files>
  <action>
    Crear función de utilidad para enmascarar tokens y aplicarla en todos los logs.

    1. Agregar función helper al inicio del archivo (después de los imports):
    ```python
    def _mask_token(token: str) -> str:
        """Enmascara un token mostrando solo los primeros 4 caracteres.

        Args:
            token: Token completo a enmascarar

        Returns:
            Token enmascarado (ej: "abcd****")
        """
        if not token or len(token) < 4:
            return "****"
        return f"{token[:4]}****"
    ```

    2. Reemplazar el log en generate_vip_token (líneas 140-143):
    ANTES:
    ```python
    logger.info(
        f"✅ Token VIP generado: {token.token} "
        f"(válido por {duration_hours}h, plan_id: {plan_id}, generado por {generated_by})"
    )
    ```

    DESPUÉS:
    ```python
    logger.info(
        f"✅ Token VIP generado: {_mask_token(token.token)} "
        f"(válido por {duration_hours}h, plan_id: {plan_id}, generado por admin_id={generated_by})"
    )
    ```

    3. Buscar y corregir cualquier otro log que muestre tokens completos.
  </action>
  <verify>
    Verificar que no hay tokens completos en logs:
    grep -n "logger.*token" bot/services/subscription.py | grep -v "_mask_token"
  </verify>
  <done>
    Todos los logs de tokens usan la función _mask_token() para mostrar solo los primeros 4 caracteres.
  </done>
</task>

<task type="auto">
  <name>Tarea 4: CRÍTICA-004 - DATABASE_URL con Credenciales en Logs</name>
  <files>bot/services/config.py</files>
  <action>
    Crear función para sanitizar DATABASE_URL y usarla en get_config_summary.

    1. Agregar función helper (después de los imports):
    ```python
    def _sanitize_db_url(url: Optional[str]) -> str:
        """Sanitiza una URL de base de datos ocultando credenciales.

        Args:
            url: URL completa de la base de datos

        Returns:
            URL con credenciales ocultas (ej: "postgresql://user:***@host/db")
        """
        if not url:
            return "No configurado"

        try:
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(url)

            if parsed.password:
                # Reconstruir URL sin password
                netloc = f"{parsed.username}:***@{parsed.hostname}"
                if parsed.port:
                    netloc += f":{parsed.port}"

                sanitized = urlunparse((
                    parsed.scheme,
                    netloc,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment
                ))
                return sanitized

            return url
        except Exception:
            # Si falla el parsing, mostrar versión muy truncada
            return f"{url[:10]}..." if len(url) > 10 else url
    ```

    2. El método get_config_summary() no muestra DATABASE_URL actualmente, pero verificar que ningún otro método la exponga.

    3. Si existe algún log de DATABASE_URL, reemplazarlo con la versión sanitizada.
  </action>
  <verify>
    Buscar cualquier exposición de DATABASE_URL:
    grep -rn "DATABASE_URL" bot/ --include="*.py" | grep -v "__pycache__"
  </verify>
  <done>
    No hay exposición de credenciales en DATABASE_URL en logs ni mensajes.
  </done>
</task>

<task type="auto">
  <name>Tarea 5: CRÍTICA-005 - PII de Usuarios en Logs Extensivos</name>
  <files>bot/services/subscription.py, bot/middlewares/admin_auth.py</files>
  <action>
    Anonimizar User IDs y datos personales en logs.

    1. Crear función helper para anonimizar user IDs:
    ```python
    def _mask_user_id(user_id: int) -> str:
        """Enmascara un user ID mostrando solo primeros y últimos 2 dígitos.

        Args:
            user_id: ID de usuario de Telegram

        Returns:
            ID enmascarado (ej: "12****89")
        """
        user_str = str(user_id)
        if len(user_str) <= 4:
            return "****"
        return f"{user_str[:2]}****{user_str[-2:]}"
    ```

    2. Actualizar logs en subscription.py para usar user_id enmascarado:
    - Línea 258: user {user_id} -> user {_mask_user_id(user_id)}
    - Línea 279: user {user_id} -> user {_mask_user_id(user_id)}
    - Línea 435: user {user_id} -> user {_mask_user_id(user_id)}
    - Línea 450: user {user_id} -> user {_mask_user_id(user_id)}
    - Línea 482: user {subscriber.user_id} -> user {_mask_user_id(subscriber.user_id)}
    - Línea 491: user {subscriber.user_id} -> user {_mask_user_id(subscriber.user_id)}
    - Línea 496: user {subscriber.user_id} -> user {_mask_user_id(subscriber.user_id)}
    - Línea 516: user {subscriber.user_id} -> user {_mask_user_id(subscriber.user_id)}
    - Línea 559: user {subscriber.user_id} -> user {_mask_user_id(subscriber.user_id)}
    - Línea 595: user {user_id} -> user {_mask_user_id(user_id)}
    - Línea 703: user {user_id} -> user {_mask_user_id(user_id)}
    - Línea 720: user {user_id} -> user {_mask_user_id(user_id)}
    - Línea 788: user {user_id} -> user {_mask_user_id(user_id)}
    - etc.

    3. En admin_auth.py (línea 78-81), anonimizar username:
    ```python
    logger.warning(
        f"🚫 Acceso denegado: user {_mask_user_id(user.id)} "
        f"intentó acceder a handler admin"
    )
    ```

    4. Revisar y actualizar todos los logs que contengan full_name, username, first_name, last_name.
  </action>
  <verify>
    Verificar que los logs no contienen PII completa:
    grep -n "logger.info\|logger.warning\|logger.debug\|logger.error" bot/services/subscription.py | head -20
  </verify>
  <done>
    Los logs usan _mask_user_id() para anonimizar IDs de usuario y no muestran nombres completos.
  </done>
</task>

<task type="auto">
  <name>Tarea 6: CRÍTICA-006 - Exposición de Detalles de Error Interno</name>
  <files>bot/services/subscription.py</files>
  <action>
    Corregir delete_user_completely para no exponer detalles de errores internos.

    En bot/services/subscription.py (líneas 1417-1420):

    ANTES:
    ```python
    except Exception as e:
        await self.session.rollback()
        logger.error(f"❌ Error eliminando usuario {user_id}: {e}")
        return False, f"❌ Error al eliminar usuario: {str(e)}", None
    ```

    DESPUÉS:
    ```python
    except Exception as e:
        await self.session.rollback()
        logger.error(f"❌ Error eliminando usuario {_mask_user_id(user_id)}: {e}")
        # No exponer detalles del error interno al usuario
        return False, "❌ Error interno al eliminar usuario. Contacte al administrador.", None
    ```

    Buscar y corregir cualquier otro lugar donde se exponga str(e) al usuario final.
  </action>
  <verify>
    Buscar exposición de errores internos:
    grep -n "str(e)" bot/services/subscription.py
    grep -n "f\".*{e}\"" bot/services/*.py
  </verify>
  <done>
    Los errores internos se loguean pero no se exponen al usuario. Los mensajes al usuario son genéricos.
  </done>
</task>

<task type="auto">
  <name>Tarea 7: CRÍTICA-007 - Mensajes de Error que Filtran Estructura</name>
  <files>bot/services/subscription.py, bot/handlers/admin/*.py</files>
  <action>
    Revisar y corregir mensajes de error que filtran información de estructura interna.

    1. En subscription.py, revisar todos los mensajes de error retornados:
    - Buscar patrones como "no encontrado", "inválido", "ya existe"
    - Asegurar que no revelen información sobre la estructura de BD

    2. Mensajes seguros (mantener):
    - "Token no encontrado" -> OK (el usuario ingresó el token)
    - "Este token ya fue usado" -> OK (el usuario tiene el token)
    - "Token expirado" -> OK (el usuario tiene el token)

    3. Mensajes a corregir:
    - Cualquier mensaje que mencione tablas de BD, columnas, constraints
    - Cualquier mensaje que revele rutas de archivo
    - Cualquier mensaje con términos técnicos internos

    4. Ejemplos de corrección:
    - "FK constraint error" -> "Error de validación"
    - "Column 'X' not found" -> "Error interno"
    - "Table users does not exist" -> "Error de configuración"

    5. Revisar handlers en bot/handlers/admin/ para mensajes de error similares.
  </action>
  <verify>
    Buscar mensajes que puedan filtrar estructura:
    grep -rn "constraint\|column\|table\|FK\|foreign key" bot/services/*.py bot/handlers/admin/*.py --include="*.py" | grep -v "__pycache__"
  </verify>
  <done>
    Los mensajes de error no filtran información sobre estructura de base de datos, tablas, o columnas.
  </done>
</task>

</tasks>

<verification>
Verificaciones finales de seguridad:

1. Ejecutar grep para confirmar que todos los routers anidados tienen AdminAuthMiddleware
2. Verificar que AdminAuthMiddleware bloquea cuando user is None
3. Confirmar que ningún log muestra tokens VIP completos
4. Confirmar que ningún log muestra DATABASE_URL con credenciales
5. Verificar que user IDs están enmascarados en logs
6. Confirmar que errores internos no se exponen a usuarios
7. Verificar que mensajes de error no filtran estructura de BD
</verification>

<success_criteria>
- [ ] CRÍTICA-001: content_router, users_router, interests_router tienen AdminAuthMiddleware
- [ ] CRÍTICA-002: AdminAuthMiddleware retorna None cuando no puede extraer usuario
- [ ] CRÍTICA-003: Tokens VIP se loguean con máscara (primeros 4 chars + ****)
- [ ] CRÍTICA-004: DATABASE_URL se sanitiza antes de mostrar en logs
- [ ] CRÍTICA-005: User IDs se enmascaran en todos los logs (12****89)
- [ ] CRÍTICA-006: Errores internos no se exponen en mensajes al usuario
- [ ] CRÍTICA-007: Mensajes de error no revelan estructura interna
</success_criteria>

<output>
After completion, create `.planning/quick/010-corregir-vulnerabilidades-criticas-seguridad/010-SUMMARY.md`
</output>

---

## Agente Especializado por Vulnerabilidad

| Vulnerabilidad | Agente Recomendado | Archivos Principales |
|----------------|-------------------|---------------------|
| CRÍTICA-001: Bypass de Autenticación | telegram-auth-auditor | main.py, content.py, users.py, interests.py |
| CRÍTICA-002: Validación Incompleta de Eventos | telegram-auth-auditor | admin_auth.py |
| CRÍTICA-003: Tokens VIP en Logs | privacy-security-auditor | subscription.py |
| CRÍTICA-004: DATABASE_URL en Logs | security-architecture-auditor | config.py |
| CRÍTICA-005: PII en Logs | privacy-security-auditor | subscription.py, admin_auth.py |
| CRÍTICA-006: Exposición de Errores | error-resilience-auditor | subscription.py |
| CRÍTICA-007: Filtración de Estructura | error-resilience-auditor | subscription.py, handlers/admin/*.py |

## Orden de Ejecución Recomendado

1. **CRÍTICA-001** (Bypass Auth) - Prioridad máxima, vulnerabilidad de acceso
2. **CRÍTICA-002** (Validación Eventos) - Prioridad máxima, vulnerabilidad de acceso
3. **CRÍTICA-003** (Tokens en Logs) - Prioridad alta, exposición de datos
4. **CRÍTICA-005** (PII en Logs) - Prioridad alta, exposición de datos
5. **CRÍTICA-004** (DATABASE_URL) - Prioridad media, exposición de credenciales
6. **CRÍTICA-006** (Errores Internos) - Prioridad media, información sensible
7. **CRÍTICA-007** (Estructura en Errores) - Prioridad baja, hardening
