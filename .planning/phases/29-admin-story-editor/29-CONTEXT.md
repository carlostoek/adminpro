# Phase 29: Admin Story Editor - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Complete admin interface for creating, editing, validating, and publishing branching stories. Admins can create story structures with nodes and choices, configure access conditions using the existing cascading condition system, attach rewards to nodes, and validate story integrity before publishing. User-facing story experience is already built (Phase 28); this phase focuses on the content creation tools.

</domain>

<decisions>
## Implementation Decisions

### Editor Workflow
- **Entry:** Botón "Crear historia" en el menú de administración
- **Post-creation:** Wizard automático de nodos comienza inmediatamente
- **Node creation flow:**
  1. Contenido del nodo (texto/media)
  2. Configuración de condiciones de acceso (si aplica)
  3. Configuración de recompensas (si aplica)
  4. Declarar nodo final O crear elecciones obligatoriamente
- **After node completion:** Continuar al siguiente nodo automáticamente o mostrar opción de volver al panel

### Condition Configuration (Critical Integration)
- **Timing:** Configuración de condiciones integrada en el wizard ANTES/DURANTE la creación del nodo
- **Scope:** Integración completa con sistema de condiciones existente (cascading conditions)
- **Condition types supported:**
  - Tier (Free/VIP)
  - Level mínimo de gamificación
  - Rachas activas
  - Besitos totales ganados/gastados
  - Objetos de tienda (product ownership)
- **UI:** Bot pregunta "¿Este nodo tiene condiciones de acceso?" → si sí, muestra sistema de condiciones existente

### Reward Configuration (Inline Creation)
- **Timing:** Mismo wizard de nodo, sin salir del flujo
- **Existing rewards:** Bot muestra lista de recompensas disponibles para seleccionar
- **New rewards:** Opción "Crear nueva recompensa" inicia wizard inline de creación de recompensa
- **Return flow:** Al finalizar creación de recompensa, regresar automáticamente al punto del wizard de nodo
- **Trigger:** Recompensas se otorgan al llegar al nodo (entrada), no al salir

### Story Structure Visualization
- **Story list:** Título + cantidad de nodos + progreso de validación (ej: "✅ Jugable", "⚠️ Revisar")
- **Node list:** Lista lineal ordenada por creación cronológica
- **Connections:** No se muestran en la lista general; entras al nodo para ver sus elecciones
- **Global view:** Modo "Preview como usuario" permite probar la historia como la vería un usuario

### Validation Timing & Behavior
- **When:** Validación ejecuta al guardar cada nodo/elección
- **Critical errors (bloquean guardar):**
  - Ciclos infinitos detectados en el grafo
  - Nodos huérfanos (inalcanzables desde el nodo inicial)
  - Nodos sin elecciones que no estén declarados como finales
- **Warnings vs Critical:** Sistema distingue entre crítico (bloquea) y advertencia (notifica)
- **Publishing:** No se permite publicar historias con warnings; debe estar "limpio" para publicar

### Content Input (Media)
- **Methods:** Adjuntar archivo directamente O reenviar mensaje existente de Telegram
- **Quantity:** Un solo archivo por nodo (foto O video, no ambos)
- **Text placement:** Texto del nodo va como caption del media
- **Allowed types:** Fotos (JPG, PNG) y Videos (MP4)

### Blocked Access Experience
- **Message style:** Comunicación por Lucien (🎩) con tono elegante de mayordomo
- **Content:** Explica qué requisitos faltan de forma específica
- **Upsell:** Incluye opciones de upsell relevantes (ej: "Hazte VIP", "Compra en la tienda")

### Claude's Discretion
- Exacto formato de mensajes de validación (emojis, estructura)
- Cómo se visualiza el "progreso de validación" en la lista de historias
- Implementación técnica del wizard inline de recompensas (cómo se suspende/resume el flujo padre)
- Cómo se detectan ciclos en tiempo real (algoritmo específico)
- Diseño de los mensajes de Lucien para acceso bloqueado
- Orden específico de preguntas dentro del wizard de nodo

</decisions>

<specifics>
## Specific Ideas

**Inline reward creation workflow:**
- Cuando el admin quiere agregar una recompensa que no existe, el bot debe:
  1. Guardar el estado actual del wizard de nodo (FSM state checkpoint)
  2. Iniciar wizard de creación de recompensa con contexto de "volver a nodo X de historia Y"
  3. Al completar recompensa, restaurar checkpoint y continuar configuración del nodo

**Condition integration pattern:**
- Reutilizar el sistema de condiciones en cascada existente (AND/OR groups) ya implementado para recompensas
- Extender el sistema con tipo PRODUCT_OWNED si no existe aún
- UI: Mostrar botón "Configurar condiciones" que lanza el mismo wizard usado en recompensas

**Preview mode:**
- Simula la experiencia real del usuario usando NarrativeService
- Muestra exactamente qué vería el usuario en cada nodo
- Permite al admin probar diferentes caminos (como si hiciera elecciones)

</specifics>

<deferred>
## Deferred Ideas

- **Vista de grafo/gráfica:** Representación visual de la estructura (tipo mapa mental) — pertenece a fase futura de "Editor Avanzado"
- **Exportación de estructura:** Generar imagen o texto del grafo para documentación externa — fase de analytics
- **Colaboración multi-admin:** Edición concurrente por múltiples administradores — fase de administración de equipo
- **Versionado de historias:** Guardar versiones, rollback a versiones anteriores — fase de editor avanzado
- **Analytics en tiempo real:** Ver cuántos usuarios han llegado a cada nodo mientras editas — fase de analytics

</deferred>

---

*Phase: 29-admin-story-editor*
*Context gathered: 2026-02-27*
