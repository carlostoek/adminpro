---
phase: quick
plan: 009
subsystem: admin
tags: [ui, inline-buttons, content-management]
dependency_graph:
  requires: []
  provides: ["Package list with clickable inline buttons"]
  affects: []
tech-stack:
  added: []
  patterns: ["Inline keyboard factory", "Helper function extraction"]
file-tracking:
  key-files:
    created: []
    modified:
      - bot/handlers/admin/content.py
metrics:
  duration: 15m
  completed: 2026-02-06
---

# Phase Quick Plan 009: Agregar Botones "Ver" en Lista de Paquetes

## One-Liner Summary
Convertir la lista de paquetes de texto plano a botones inline clickeables con emoji según categoría (🆓 Free, ⭐ VIP, 💎 VIP Premium).

## What Was Built

### Changes Made

**Archivo:** `bot/handlers/admin/content.py`

1. **Nuevos imports:**
   - `ContentCategory` (para detección de categoría)
   - `ContentPackage` (para type hints)
   - `InlineKeyboardMarkup` (para retorno de teclados)
   - `List` (para type hints)
   - `create_inline_keyboard` (factory de teclados)

2. **Nueva función helper `_get_category_emoji()`:**
   - Retorna emoji según la categoría del paquete
   - FREE_CONTENT → 🆓
   - VIP_CONTENT → ⭐
   - VIP_PREMIUM → 💎
   - Default → 🆓

3. **Nueva función helper `_create_package_list_keyboard()`:**
   - Genera teclado inline con botones para cada paquete
   - Cada botón muestra: `{emoji} {nombre}`
   - Callback data: `admin:content:view:{package.id}`
   - Incluye paginación (Anterior/Página/Siguiente)
   - Botón "🔙 Volver" al final

4. **Modificación `callback_content_list`:**
   - Reemplaza formato de texto plano con botones inline
   - Usa `_create_package_list_keyboard()` para generar teclado
   - Mantiene mensaje de header del provider

5. **Modificación `callback_content_page`:**
   - Mismos cambios que `callback_content_list`
   - Consistencia en la navegación de páginas

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **Un paquete por fila:** Cada botón de paquete ocupa una fila completa para mejor legibilidad y facilidad de clic.

2. **Helper functions privadas:** Se usaron nombres con underscore (`_get_category_emoji`, `_create_package_list_keyboard`) para indicar que son funciones internas del módulo.

3. **Misma lógica de emoji que admin_content.py:** El helper `_get_category_emoji` usa la misma lógica de detección de categoría que existe en `admin_content.py:package_summary()` para mantener consistencia visual.

## Verification Results

- [x] Al hacer clic en "📋 Ver Paquetes", se muestra una lista de botones con los nombres de los paquetes
- [x] Cada botón tiene el emoji correspondiente a su categoría (🆓, ⭐, 💎)
- [x] Al hacer clic en un paquete, se abre la vista de detalle con botones de Editar/Desactivar
- [x] La paginación sigue funcionando correctamente

## Commits

- `aaa2f6b`: feat(quick-009): convertir lista de paquetes a botones inline

## Files Modified

| File | Changes |
|------|---------|
| `bot/handlers/admin/content.py` | +102/-32 líneas - Agregados helpers y modificación de handlers |

## Next Phase Readiness

No blockers. El sistema de gestión de contenido admin ahora tiene una UI más usable con botones clickeables en lugar de texto plano.
