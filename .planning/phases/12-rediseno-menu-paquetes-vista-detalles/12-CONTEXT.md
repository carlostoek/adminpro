# Phase 12: Rediseño de Menú de Paquetes con Vista de Detalles - Context

**Gathered:** 2026-01-27
**Status:** Ready for planning

## Phase Boundary

Rediseñar la interfaz de paquetes para mostrar información detallada (descripción, precio) antes de registrar interés, con botones individuales por paquete. El flujo es: lista de paquetes → vista de detalles → registrar interés → mensaje de confirmación con contacto a la creadora.

</domain>

## Implementation Decisions

### Package List Presentation
- **Formato minimalista:** Solo nombre del paquete + emoji (sin precio ni categoría en la lista)
- **Lista vertical:** Un paquete por fila, diseño clásico de menú Telegram
- **Formato de nombre:** Nombre con emoji prefix (configurable por paquete)
- **Ordenamiento:** Por precio, de menor a mayor (si es gratuito, va al principio)

### Detail View Content
- **Descripción completa:** Mostrar descripción completa del paquete (sin truncar)
- **Formato de precio:** Con label prefix: "Precio: $15.00" o "Acceso gratuito"
- **Tipo y categoría:** Badges con emoji (ej: "👑 Premium" / "🌷 Garden" + categoría icono)
- **Metadatos:** Solo campos user-facing (nombre, descripción, precio, tipo, categoría). No mostrar is_active, created_at

### Navigation Flow
- **Botones en vista de detalles:** Solo "← Volver" (sin botón "Salir")
- **Post-acción "Me interesa":** Enviar mensaje de confirmación con:
  - Mensaje directo/cálido: "Gracias por tu interés! 🫶\n\nEn un momento me pongo en contacto personalmente contigo 😊\n\nSi no quieres esperar da clic aquí abajo ⬇️ para escribirme en mi Telegram personal!"
  - Botón: "Escribirme" → tg://resolve?username=<CREATOR_USERNAME> (fallback a profile link si no hay username)
  - Botón: "Regresar" → devuelve al listado de paquetes
  - Botón: "Inicio" → devuelve al menú principal (VIP o Free)
- **Voz del mensaje:** Tono directo/cálido (no Lucien - más personal)

### Callback Structure
- **Lista → Detalle:** `user:packages:{package_id}`
- **Detalle → Interés:** `user:package:interest:{package_id}`
- **Navegación:** `user:packages:back` (volver a listado), `user:package:back` (volver desde detalle)

### Claude's Discretion
- Diseño exacto del layout de mensajes (espaciado, formato HTML)
- Cálculo de ordenamiento por precio (cómo manejar NULL prices, lógica de comparación)
- Manejo de paquetes inactivos en la lista (mostrar vs ocultar)
- Fallback exacto para creator profile link si no hay username disponible

## Specific Ideas

- El flujo de confirmación con contacto directo a la creadora es una característica clave - no es solo interés, sino apertura de canal de comunicación personal
- El mensaje de confirmación debe sentirse cercano y personal, no automatizado
- El ordenamiento por precio ayuda a los usuarios a encontrar opciones accesibles primero

## Deferred Ideas

None — discussion stayed within phase scope.

---

*Phase: 12-rediseno-menu-paquetes-vista-detalles*
*Context gathered: 2026-01-27*
