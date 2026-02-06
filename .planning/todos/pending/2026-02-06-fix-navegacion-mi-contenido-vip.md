---
created: 2026-02-06T12:00
title: Fix navegación "Mi contenido" VIP - botón volver
area: ui
files:
  - bot/handlers/vip/callbacks.py:86-135,141-160,709-719
  - bot/services/message/user_flows.py:438
---

## Problem

En la sección "Mi contenido" para usuarios VIP:
- Cuando un VIP entra a "Mi contenido" (contenido Free/Promos)
- Abre un paquete específico
- Le da al botón "Envolver" (Volver)
- **BUG:** Lo regresa a "El Diván" (Contenido VIP) en lugar de regresar a "Mi contenido"

## Solution

El problema está en los handlers de navegación en `bot/handlers/vip/callbacks.py`:

1. Revisar `handle_vip_free_content()` - muestra contenido Free a VIP
2. Revisar callbacks de navegación `vip:packages:back`, `vip:packages:back:{role}`
3. Cuando el usuario viene de "Mi contenido" (callback `vip:free_content`), el botón volver debe retornar a esa sección, no al menú VIP principal

Posible solución:
- Pasar contexto adicional en el callback_data para saber de dónde viene el usuario
- O usar FSM state para trackear la navegación
- O crear un callback específico `vip:free:packages:back` que ya existe pero verificar que se use correctamente

## Archivos a modificar

- `bot/handlers/vip/callbacks.py` - Lógica de navegación desde "Mi contenido"
- Posiblemente `bot/services/message/user_flows.py` - Botón "Regresar" con callback correcto
