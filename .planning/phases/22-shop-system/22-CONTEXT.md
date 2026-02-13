# Phase 22: Shop System - Context

**Gathered:** 2026-02-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Sistema de tienda donde usuarios pueden navegar y comprar contenido usando "besitos" (moneda virtual). Incluye catálogo browsable, flujo de compra con atomicidad (deducir + entregar), historial de compras, y precios diferenciados VIP. Recompensas automáticas y configuración admin son fases separadas.

</domain>

<decisions>
## Implementation Decisions

### Catálogo de productos
- **Layout:** Lista vertical (uno debajo del otro)
- **Info en listado:** Solo nombre del producto (minimalista, sin precios ni badges)
- **Navegación:** Prev/Next entre páginas
- **Ordenamiento:** Por precio ascendente
- **En detalle:** Se revelan todos los precios con diferenciación VIP/Free

### Flujo de compra
- **Inicio:** Vista de detalle primero (descripción completa del producto)
- **Botones en detalle:** "Comprar ahora" + "Volver al catálogo"
- **Confirmación:** Sí, con resumen antes de cobrar los besitos
- **Saldo insuficiente:** Bloqueo + redirección a cómo ganar besitos

### Precios y descuentos VIP
- **Configuración:** Porcentaje VIP global configurable (ej: 20% en toda la tienda)
- **Visualización VIP:** Precio normal tachado + precio VIP protagonista (💎)
  - Ejemplo: "~~100 besitos~~\n💎 80 besitos"
  - Footer: "Privilegio aplicado a su membresía VIP"
- **Visualización FREE:** Precio normal prominente + precio VIP atenuado
  - Ejemplo: "100 besitos\n💎 Precio VIP: 80 besitos"
  - Footer: "Este beneficio se aplica únicamente a membresías VIP"
- **Tono de mayordomo:**
  - Nunca usar "descuento"
  - Palabras clave: acceso, privilegio, reservado, membresía, exclusivo, cortesía, beneficio
  - Al tocar producto siendo FREE: "Este artículo incluye un privilegio VIP. Al activar su membresía, se aplicará automáticamente."
- **Productos VIP-only:** FREE puede ver todo el contenido, pero al intentar comprar recibe mensaje elegante de exclusividad con botón de regresar (sin redirigir a flujo de upgrade)

### Entrega de contenido
- **Tipos de productos:** Contenido digital, beneficios/activos virtuales, membresía VIP, combinaciones
- **Entrega contenido digital:** Ambos - archivo enviado directo al chat privado + acceso al canal VIP
- **Recompra:** Doble confirmación si el usuario ya posee el artículo ("Ya lo tiene, ¿desea adquirirlo nuevamente?")
- **Historial de compras:** Producto + fecha + precio pagado + estado (activo/consumido)
- **Re-descarga:** Sí, contenido siempre disponible en chat privado indefinidamente

### Claude's Discretion
- Formato exacto de las tarjetas de producto en detalle
- Spacing y tipografía de precios
- Implementación de "activo/consumido" en el historial
- Estructura de navegación Prev/Next

</decisions>

<specifics>
## Specific Ideas

**Psicología de precios VIP (de guía del usuario):**
- "La dopamina no se activa por lo que tienes, sino por lo que podrías tener"
- Ver el precio VIP sin poder usarlo genera FOMO y sensación de estatus inaccesible
- FREE debe sentirse tentado, no castigado
- VIP no ve promociones, ve privilegios

**Ejemplos de tono mayordomo:**
- Producto VIP: "🗝️ Acceso VIP — 7 días"
- Multiplicador: "✨ Multiplicador"
- Set de contenido: "🎁 Set de contenido"

**Integración importante (mencionado por usuario):**
Este módulo tiene relevancia para el sistema de recompensas — los productos de la tienda pueden usarse como condición para desbloquear recompensas. Esto implica que el modelo de productos debe ser referenciable desde el sistema de condiciones de recompensas (Phase 23).

La configuración en cascada debe permitir que, desde la configuración de una recompensa, el admin pueda crear un producto de tienda si lo necesita, sin salir del flujo de configuración de recompensas.

</specifics>

<deferred>
## Deferred Ideas

- **Recompensas automáticas:** Fase 23 — Recompensas que se desbloquean automáticamente al cumplir condiciones
- **Configuración admin:** Fase 24 — UI para que admins configuren productos, precios, y descuentos VIP
- **Upgrade de membresía desde tienda:** Redirigir a flujo de activación VIP cuando un FREE intenta comprar producto VIP (notado pero no implementado — solo mensaje informativo)

</deferred>

---

*Phase: 22-shop-system*
*Context gathered: 2026-02-13*
