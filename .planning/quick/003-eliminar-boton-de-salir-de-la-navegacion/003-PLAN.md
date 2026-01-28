# Plan 003: Eliminar botón de salir de create_content_with_navigation (continuación de Quick Task 002)

## Descripción

Completar la eliminación del botón "Salir" del sistema de navegación del bot. Quick Task 002 cambió `create_menu_navigation` pero `create_content_with_navigation` (un wrapper que usa el código base) todavía tenía `include_exit=True` como default.

## Problema

- Quick Task 002 cambió `create_menu_navigation` a `include_exit=False`
- Pero `create_content_with_navigation` todavía tenía `include_exit=True` como default
- El código base usa `create_content_with_navigation` en muchos lugares
- El botón "Salir" todavía aparecía en menús porque el wrapper no estaba actualizado

## Solución

### Tarea 1: Cambiar el valor por defecto de include_exit a False en create_content_with_navigation

**Archivo:** `bot/utils/keyboards.py`

**Cambios:**
1. Cambiar `include_exit: bool = True` a `include_exit: bool = False` en la función `create_content_with_navigation` (línea 223)
2. Actualizar docstring para indicar el nuevo default

## Verificación

- El botón "Salir" ya no aparece en ningún menú del bot
- Ambas funciones (`create_menu_navigation` y `create_content_with_navigation`) tienen `include_exit=False` como default
- Los menús VIP y Free solo muestran botón "Volver"

## Riesgos

- Bajo riesgo - solo cambia un valor por defecto para consistencia
- Completa el trabajo de Quick Task 002

## Commit Message

```
feat(quick-003): remove exit button from create_content_with_navigation default

- Change include_exit default from True to False in create_content_with_navigation
- Update docstring to reflect new default behavior
- Completes Quick Task 002 by fixing the wrapper function
- Exit button no longer appears in any menu navigation
```
