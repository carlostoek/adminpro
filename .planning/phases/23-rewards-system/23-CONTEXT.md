# Phase 23: Rewards System - Context

**Gathered:** 2026-02-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Automatic reward distribution when users meet configurable conditions. Users can view available rewards with their conditions, receive notifications when conditions are met, and claim rewards. Conditions include streak, points, level, besitos spent, and event-based triggers. Only applies to future achievements (not retroactive).

</domain>

<decisions>
## Implementation Decisions

### Tipos y estructura de condiciones
- **Condiciones mixtas:** Acumulativas (puntos totales, racha actual, besitos gastados, nivel alcanzado) + Eventos únicos (primer compra, primer regalo diario, primera reacción)
- **Lógica:** AND + OR básico — todas las condiciones usan AND por defecto, pero algunas condiciones pueden agruparse como "una de varias"
- **Exclusiones:** Básicas — se soportan condiciones negativas simples como "no haber reclamado recompensa X antes" o "no ser VIP"
- **Comparadores:** Solo ≥ (mayor o igual que) — se mantiene simple, sin "igual a", "menor que" ni rangos

### Momento de verificación y notificación
- **Verificación:** Event-driven — se verifican condiciones cuando ocurren eventos (reclamar diario, comprar, alcanzar nivel)
- **Notificaciones:** Agrupadas — si en un mismo evento se gana besitos Y se desbloquea recompensa, todo va en un solo mensaje (no dos separados)
- **Canal:** Solo bot privado — las notificaciones no van al canal VIP
- **Retroactividad:** No aplica — las recompensas solo se activan para logros futuros, no para usuarios que ya cumplen condiciones

### Progresión y estados de recompensas
- **Frecuencia:** Ambos tipos — recompensas únicas (una vez por usuario) Y repetibles (se pueden reclamar múltiples veces cumpliendo condiciones nuevamente)
- **Expiración:** Sí, tiempo limitado — el admin configura cuánto tiempo tiene el usuario para reclamar antes de perderla
- **Estados visibles:** Tres estados — Bloqueada (no cumple condiciones), Desbloqueada (cumple, lista para reclamar), Reclamada (ya fue cobrada)
- **Recompensas secretas:** Sí — algunas recompensas solo aparecen en el catálogo cuando se desbloquean (ej: "Racha de 30 días"), para crear sorpresa y descubrimiento

### Claude's Discretion
- Exacta implementación del motor de reglas para condiciones
- Cómo agrupar lógica AND/OR en la base de datos
- Diseño del flujo de notificación agrupada
- UI/UX de la lista de recompensas
- Tiempo por defecto de expiración si no se especifica

</decisions>

<specifics>
## Specific Ideas

- Notificaciones agrupadas: un solo mensaje con múltiples logros en lugar de spam de notificaciones
- Recompensas sorpresa para gamification tipo "easter egg" — aparecen solo cuando se desbloquean
- Estados visuales claros para que el usuario sepa qué puede reclamar vs. qué necesita esforzarse

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 23-rewards-system*
*Context gathered: 2026-02-13*
