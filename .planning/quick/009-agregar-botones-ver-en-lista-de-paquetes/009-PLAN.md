---
phase: quick
plan: 009
type: execute
wave: 1
depends_on: []
files_modified:
  - bot/handlers/admin/content.py
autonomous: true
must_haves:
  truths:
    - "Los paquetes en la lista se muestran como botones inline clickeables"
    - "Cada botón tiene el nombre del paquete y emoji según categoría"
    - "El callback_data apunta a admin:content:view:{id}"
  artifacts:
    - path: "bot/handlers/admin/content.py"
      provides: "Lista de paquetes con botones inline (Opción B)"
      exports: ["callback_content_list", "callback_content_page"]
---

<objective>
Modificar los handlers de listado de paquetes para mostrar cada paquete como un botón inline con su nombre (Opción B), en lugar de texto plano.

Purpose: Permitir que el admin pueda hacer clic en un paquete de la lista para ver sus detalles y acceder a las funciones de editar/desactivar.
</objective>

<execution_context>
El problema actual es que `callback_content_list` y `callback_content_page` muestran los paquetes como texto plano usando `format_items_list()`, sin botones de acción. El admin no puede acceder al detalle de un paquete desde la lista.

El handler `callback_content_view` ya existe y funciona correctamente con el callback pattern `admin:content:view:{id}`.
</execution_context>

<context>
@/data/data/com.termux/files/home/repos/adminpro/bot/handlers/admin/content.py
@/data/data/com.termux/files/home/repos/adminpro/bot/services/message/admin_content.py
</context>

<tasks>

<task type="auto">
  <name>Modificar callback_content_list para botones inline</name>
  <files>bot/handlers/admin/content.py</files>
  <action>
Modificar el handler `callback_content_list` (líneas ~72-140) para:

1. En lugar de usar `format_items_list()` para generar texto, crear botones inline para cada paquete
2. Cada botón debe mostrar: `{emoji} {nombre}` donde el emoji depende de la categoría:
   - FREE_CONTENT = 🆓
   - VIP_CONTENT = ⭐
   - VIP_PREMIUM = 💎
3. El callback_data debe ser: `admin:content:view:{package.id}`
4. Mantener la paginación actual (create_pagination_keyboard)
5. El texto del mensaje debe ser un header simple sin la lista de paquetes

Ejemplo de estructura de botones:
```
[🆓 Paquete Gratis 1]
[⭐ Paquete VIP 1]
[💎 Paquete Premium 1]
[◀️ Anterior] [Página 1/3] [Siguiente ▶️]
[🔙 Volver]
```
  </action>
  <done>Handler callback_content_list muestra botones inline para cada paquete</done>
</task>

<task type="auto">
  <name>Modificar callback_content_page para botones inline</name>
  <files>bot/handlers/admin/content.py</files>
  <action>
Aplicar los mismos cambios al handler `callback_content_page` (líneas ~143-208):

1. Crear botones inline para cada paquete en la página actual
2. Usar el mismo formato de emoji + nombre
3. Mismo callback_data pattern: `admin:content:view:{package.id}`
4. Mantener paginación

Ambos handlers deben compartir la misma lógica de generación de botones (posiblemente extraer a una función helper `_create_package_list_keyboard()`).
  </action>
  <done>Handler callback_content_page también muestra botones inline</done>
</task>

</tasks>

<verification>
1. Al hacer clic en "📋 Ver Paquetes", se muestra una lista de botones con los nombres de los paquetes
2. Cada botón tiene el emoji correspondiente a su categoría (🆓, ⭐, 💎)
3. Al hacer clic en un paquete, se abre la vista de detalle con botones de Editar/Desactivar
4. La paginación sigue funcionando correctamente
</verification>

<success_criteria>
- Los paquetes se muestran como botones clickeables en lugar de texto plano
- Cada botón lleva al detalle del paquete (admin:content:view:{id})
- Se mantiene la funcionalidad de paginación
- Los emojis indican el tipo de contenido (Free/VIP/Premium)
</success_criteria>

<output>
After completion, create `.planning/quick/009-agregar-botones-ver-en-lista-de-paquetes/009-SUMMARY.md`
</output>
