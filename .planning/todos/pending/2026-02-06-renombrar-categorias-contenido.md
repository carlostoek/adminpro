---
created: 2026-02-06T12:00
title: Renombrar categorías de contenido (Promos, El Diván, Premium)
area: ui
files:
  - bot/database/enums.py:54-90
  - bot/services/message/user_menu.py:564-568,602-603
  - bot/services/message/admin_content.py:221-232,374-375
  - bot/services/message/admin_interest.py:159-160,227-228,273-274
---

## Problem

Cambiar la nomenclatura de las categorías de contenido según nueva definición:

| Actual | Nuevo |
|--------|-------|
| Contenido gratuito / Contenido Gratuito | Promos |
| Contenido VIP / Contenido VIP | El Diván |
| Contenido Premium / VIP Premium | Premium |

Además, cambiar toda terminología "contenido gratis/gratuito" por "promociones" porque no hay contenido gratis, son promociones para usuarios free.

## Solution

1. Actualizar `ContentCategory.display_name()` en `bot/database/enums.py`
2. Buscar y reemplazar textos en:
   - `bot/services/message/user_menu.py`
   - `bot/services/message/admin_content.py`
   - `bot/services/message/admin_interest.py`
3. Buscar cualquier otro archivo con textos "gratis", "gratuito", "Contenido Gratuito"
4. Verificar que los callbacks no se rompan (usan enums, no textos)

## Archivos a modificar

- `bot/database/enums.py` - Enum ContentCategory con display names
- `bot/services/message/user_menu.py` - Textos de menús y teclados
- `bot/services/message/admin_content.py` - Textos de admin para contenido
- `bot/services/message/admin_interest.py` - Textos de intereses
