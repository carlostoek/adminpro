# Phase 5: Role Detection & Database Foundation - Context

**Gathered:** 2026-01-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Sistema que detecta automáticamente el rol del usuario (Admin/VIP/Free) basándose en su estado en canales y base de datos, con modelos de datos para contenido (ContentPackage), intereses (UserInterest) y cambios de rol (UserRoleChangeLog), además de ContentService con operaciones CRUD para paquetes de contenido.

</domain>

<decisions>
## Implementation Decisions

### Role detection logic
- **Admin definition**: Use `Config.is_admin(user_id)` from existing BotConfig
- **VIP definition**: Has active `VIPSubscriber` record with `expiry > now`
- **Free definition**: Default fallback when user is neither Admin nor VIP
- **Priority order**: Admin > VIP > Free (first match wins)
- **Role calculation**: Stateless function that checks conditions in priority order

### Content package model
- **Package types**: VIP vs Free packages (distinguish via `type` field)
- **Core fields**: `name`, `description`, `price`, `is_active`, `category`, `type`, `media_url`
- **Pricing model**: Single `price` field (Decimal) for base currency
- **Active/inactive**: Use `is_active` boolean for soft delete

### Interest tracking
- **UserInterest fields**: `user_id`, `package_id`, `created_at`, `is_attended`, `attended_at`
- **Deduplication**: Update `created_at` timestamp on re-click (shows renewed interest)
- **Expired VIP interests**: Archive (preserve but mark as archived rather than delete)

### Claude's Discretion
- Exact schema for UserRoleChangeLog (what events to track, level of detail)
- Whether to add `updated_at` timestamp to ContentPackage for change tracking
- Index strategy for database queries (what to index for performance)
- How to handle role changes during active menu session (edge case noted in STATE.md)

</decisions>

<specifics>
## Specific Ideas

- Role detection should be fast (called on every user interaction)
- ContentService should follow the same pattern as SubscriptionService (async methods, session injection)
- Use existing VIPSubscriber model from Phase 1.2, extend with new models

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

---

*Phase: 05-role-detection-database*
*Context gathered: 2026-01-24*
