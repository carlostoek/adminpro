---
phase: quick
plan: 008
type: execute
wave: 1
depends_on: []
files_modified:
  - bot/services/content.py
  - bot/handlers/admin/content.py
  - bot/database/models.py
autonomous: true
must_haves:
  truths:
    - "ContentPackage model exists with all required fields"
    - "ContentService provides full CRUD operations"
    - "Admin handlers allow CRUD via Telegram UI"
    - "ServiceContainer exposes content service via lazy loading"
  artifacts:
    - path: "bot/database/models.py"
      provides: "ContentPackage model with CRUD fields"
      contains: "class ContentPackage"
    - path: "bot/services/content.py"
      provides: "ContentService with CRUD operations"
      exports: ["create_package", "get_package", "list_packages", "update_package", "deactivate_package"]
    - path: "bot/handlers/admin/content.py"
      provides: "Admin handlers for content management"
      exports: ["content_router"]
  key_links:
    - from: "bot/services/container.py"
      to: "bot/services/content.py"
      via: "content property lazy loading"
      pattern: "ContentService"
    - from: "bot/handlers/admin/content.py"
      to: "bot/services/content.py"
      via: "container.content.* calls"
      pattern: "container.content\\."
---

<objective>
Verificar y completar la integración del sistema CRUD para paquetes de contenido (ContentPackage) con el sistema de "muestras del jardín" (Free) y "círculo exclusivo" (VIP).

Purpose: Asegurar que el sistema de paquetes de contenido esté completamente funcional y accesible desde el panel de admin, integrado con las secciones Free y VIP existentes.
Output: Sistema CRUD verificado y funcional para gestión de paquetes de contenido.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@/data/data/com.termux/files/home/repos/adminpro/bot/database/models.py
@/data/data/com.termux/files/home/repos/adminpro/bot/services/content.py
@/data/data/com.termux/files/home/repos/adminpro/bot/services/container.py
@/data/data/com.termux/files/home/repos/adminpro/bot/handlers/admin/content.py
@/data/data/com.termux/files/home/repos/adminpro/bot/database/enums.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Verificar integración ContentService con ServiceContainer</name>
  <files>bot/services/container.py</files>
  <action>
Verificar que ServiceContainer tenga la propiedad `content` correctamente implementada para lazy loading de ContentService.

1. Revisar que `_content_service` esté inicializado en `__init__` como None
2. Verificar que la property `content` exista y cargue ContentService lazy
3. Confirmar que `get_loaded_services()` incluya "content" en la lista
4. Verificar que no haya errores de importación circular

Si falta algún elemento, implementarlo siguiendo el patrón de los otros servicios (subscription, channel, config).
  </action>
  <verify>grep -n "content" bot/services/container.py | head -20</verify>
  <done>ServiceContainer tiene propiedad `content` que retorna ContentService con lazy loading correcto</done>
</task>

<task type="auto">
  <name>Task 2: Verificar handlers admin para gestión de paquetes</name>
  <files>bot/handlers/admin/content.py</files>
  <action>
Verificar que los handlers de admin para content packages estén completos y registrados.

1. Confirmar que content_router tenga todos los handlers CRUD:
   - Listar paquetes (callback_content_list, callback_content_page)
   - Ver detalle (callback_content_view)
   - Crear paquete (FSM wizard completo)
   - Editar paquete (callback_content_edit_field, process_content_edit)
   - Activar/Desactivar (callback_content_deactivate, callback_content_reactivate)

2. Verificar que el router esté incluido en el admin main router
3. Confirmar que los estados FSM (ContentPackageStates) existan

Si falta algún handler o registro, implementarlo siguiendo los patrones existentes.
  </action>
  <verify>grep -n "@content_router" bot/handlers/admin/content.py | wc -l && grep -n "content_router" bot/handlers/admin/__init__.py</verify>
  <done>Todos los handlers CRUD existen y el router está registrado en admin</done>
</task>

<task type="auto">
  <name>Task 3: Validar modelo ContentPackage y sus relaciones</name>
  <files>bot/database/models.py</files>
  <action>
Verificar que el modelo ContentPackage tenga todos los campos necesarios para el sistema de paquetes.

Campos requeridos:
- id: Primary key
- name: Nombre del paquete (string)
- description: Descripción (opcional)
- price: Precio (Numeric/Decimal)
- category: Enum (FREE_CONTENT, VIP_CONTENT, VIP_PREMIUM)
- type: Enum (STANDARD, BUNDLE, COLLECTION)
- media_url: URL del contenido (opcional)
- is_active: Estado activo/inactivo
- created_at: Fecha creación
- updated_at: Fecha actualización
- interests: Relación con UserInterest

Verificar que los índices estén definidos para consultas eficientes.
Confirmar que las relaciones con UserInterest funcionen correctamente.
  </action>
  <verify>grep -A 80 "class ContentPackage" bot/database/models.py | head -90</verify>
  <done>Modelo ContentPackage tiene todos los campos requeridos y relaciones correctas</done>
</task>

</tasks>

<verification>
1. ContentService accesible via `container.content`
2. Admin puede crear, listar, editar y desactivar paquetes
3. Modelo tiene campos para integración con Free (FREE_CONTENT) y VIP (VIP_CONTENT, VIP_PREMIUM)
4. Sistema de intereses (UserInterest) relacionado correctamente
</verification>

<success_criteria>
- ServiceContainer expone content service
- Handlers admin permiten gestión completa de paquetes
- Modelo ContentPackage tiene todos los campos necesarios
- Sistema integrado con flujos Free y VIP existentes
</success_criteria>

<output>
After completion, create `.planning/quick/008-implementar-funcionalidades-crud-para-el/008-SUMMARY.md`
</output>
