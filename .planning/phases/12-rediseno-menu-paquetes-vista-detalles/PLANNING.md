# Phase 12: Rediseño de Menú de Paquetes con Vista de Detalles - Planning Summary

**Planned:** 2026-01-27
**Status:** ✅ Complete (with post-phase fixes)
**Plans:** 4 plans in 2 waves
**Completed:** 2026-01-27

---

## Phase Overview

Rediseñar la interfaz de paquetes para mostrar información detallada (descripción, precio) antes de registrar interés, con botones individuales por paquete. El flujo nuevo es: lista de paquetes → vista de detalles → registrar interés → mensaje de confirmación con contacto a la creadora.

### Current Problem

El sistema actual (Phase 6-8) muestra paquetes en lista con botones "⭐ {name} - Me interesa" que registran interés inmediatamente sin que el usuario vea detalles del paquete (descripción, precio completo, tipo). Esto genera:

- Leads de baja calidad (usuarios interesados sin información completa)
- Pérdida de potencial de conversión (no hay narrativa previa al interés)
- Falta de transparencia (usuario no sabe qué está "comprando")

### Solution Architecture

**Nuevo flujo de 4 pasos:**
1. **Lista minimalista**: Solo nombre del paquete (sin precio, sin descripción)
2. **Vista de detalles**: Nombre, descripción completa, precio, tipo/categoría, botón "Me interesa"
3. **Confirmación personal**: Mensaje cálido de Diana con botón de contacto directo
4. **Navegación flexible**: Regresar a listado o volver al menú principal desde cualquier punto

---

## Wave Structure

| Wave | Plans | Description | Parallel? |
|------|-------|-------------|-----------|
| 1 | 12-01, 12-02 | Lista minimalista + vista de detalles | ✅ Yes |
| 2 | 12-03, 12-04 | Confirmación post-interés + navegación completa | ✅ Yes |

**Wave 1** can execute in parallel because:
- 12-01 modifies UserMenuMessages (lista de paquetes)
- 12-02 adds new detail view method + handlers (no overlap with 12-01)

**Wave 2** depends on Wave 1 because:
- 12-03 requires package_detail_view() from 12-02 for confirmation message context
- 12-04 requires confirmation message handlers from 12-03 for navigation targets

---

## Plan Breakdown

### 12-01: Rediseñar presentación de paquetes en lista minimalista
**Wave:** 1
**Files:** `bot/services/message/user_menu.py`

**Tasks:**
1. Add `_sort_packages_by_price()` helper method (free first, then ascending)
2. Update `vip_premium_section()` to minimal list format (name only)
3. Update `free_content_section()` to minimal list format (name only)
4. Remove obsolete `_create_package_buttons()` method

**Key Changes:**
- Callback pattern: `interest:package:{id}` → `user:packages:{id}`
- List format: "⭐ {name} - Me interesa" → "📦 {name}"
- Sorting: By price (free first, then ascending)

---

### 12-02: Crear vista de detalles con información completa
**Wave:** 1
**Files:** `bot/services/message/user_menu.py`, `bot/handlers/vip/callbacks.py`, `bot/handlers/free/callbacks.py`

**Tasks:**
1. Add `package_detail_view()` method to UserMenuMessages
2. Add `user:packages:{id}` handler to VIP router
3. Add `user:packages:{id}` handler to Free router

**Key Changes:**
- New callback pattern: `user:packages:{package_id}` for detail view
- Detail view shows: name, description, price, category badges
- "Me interesa" button: callback `user:package:interest:{package_id}`

---

### 12-03: Implementar flujo post-interés con confirmación
**Wave:** 2
**Files:** `bot/services/message/user_flow.py`, `bot/handlers/vip/callbacks.py`, `bot/handlers/free/callbacks.py`

**Tasks:**
1. Add `package_interest_confirmation()` method to UserFlowMessages
2. Add `user:package:interest:{id}` handler to VIP router
3. Add `user:package:interest:{id}` handler to Free router

**Key Changes:**
- New message tone: Warm/personal (Diana's voice, NOT Lucien's)
- Confirmation buttons: "Escribirme" (tg://resolve), "Regresar", "Inicio"
- Preserves Phase 8 admin notification feature

---

### 12-04: Completar navegación completa
**Wave:** 2
**Files:** `bot/handlers/vip/callbacks.py`, `bot/handlers/free/callbacks.py`

**Tasks:**
1. Add `user:packages:back` handler to VIP router (return to list)
2. Add `user:packages:back` handler to Free router (return to list)
3. Add `menu:vip:main` and `menu:free:main` handlers (return to main menu)

**Key Changes:**
- Circular navigation: list ↔ detail ↔ confirmation → list/inicio
- Reuses existing handlers (no code duplication)
- Integrates with Phase 6 navigation patterns

---

## Callback Pattern Migration

### Old Pattern (Phase 6-8)
```
interest:package:{id} → register interest immediately
```

### New Pattern (Phase 12)
```
user:packages:{id} → show package detail view
user:package:interest:{id} → register interest + show confirmation
user:packages:back → return to package list
menu:{vip|free}:main → return to main menu
```

**Rationale:** New pattern separates navigation (`user:packages:`) from action (`user:package:interest:`), enabling the detail view step.

---

## Dependencies

### Internal Dependencies
- **12-02 depends on 12-01:** Requires new callback pattern `user:packages:{id}` introduced in 12-01
- **12-03 depends on 12-02:** Requires `package_detail_view()` method for context in confirmation
- **12-04 depends on 12-03:** Requires confirmation message handlers as navigation targets

### External Dependencies
- **Phase 8 (Interest Notification System):** Preserves existing `InterestService.register_interest()` and admin notification logic
- **Phase 6 (VIP/Free Menus):** Integrates with existing navigation patterns (`menu:back`, `menu:exit`)
- **ContentService (Phase 7):** Uses `get_active_packages()` and `get_package_by_id()` methods

---

## Technical Decisions

### Package Sorting Algorithm
**Decision:** Free packages (price=None) first, then paid packages sorted by price ASC.

**Rationale:** Users see accessible options first, reducing cognitive load and increasing engagement.

**Implementation:** List comprehension with filtering:
```python
free_packages = sorted([p for p in packages if p.price is None], key=lambda p: p.name)
paid_packages = sorted([p for p in packages if p.price is not None], key=lambda p: (p.price, p.name))
return free_packages + paid_packages
```

### Message Tone for Confirmation
**Decision:** Warm, personal tone (Diana's voice, NOT Lucien's).

**Rationale:** Post-interest phase is about personal connection, not butler-client relationship. User is now a "warm lead" talking directly to Diana.

**Implementation:** Direct message without 🎩 emoji, using first-person singular ("me pongo en contacto").

### Navigation Handler Reuse
**Decision:** `user:packages:back` handlers call existing `handle_vip_premium()` and `handle_free_content()` instead of duplicating logic.

**Rationale:** Avoids code duplication, ensures consistent list display, maintains sorting from 12-01.

**Implementation:** Direct function call:
```python
await handle_vip_premium(callback, container)
```

---

## Quality Assurance

### Verification Criteria

**Plan 12-01:**
- [ ] Packages sorted: free first, then by price ascending
- [ ] List shows only "📦 {name}" (no price, no category)
- [ ] Callbacks use `user:packages:{id}` pattern

**Plan 12-02:**
- [ ] Detail view shows: name, description, price, category badges
- [ ] Detail view has "⭐ Me interesa" button
- [ ] Detail view has "⬅️ Volver" button (no "Salir")
- [ ] Callback pattern: `user:package:interest:{id}`

**Plan 12-03:**
- [ ] Confirmation message uses warm/personal tone (no 🎩)
- [ ] Confirmation has "✉️ Escribirme" button with tg://resolve link
- [ ] Confirmation has "📋 Regresar" and "🏠 Inicio" buttons
- [ ] Admin notifications still sent (Phase 8 preserved)

**Plan 12-04:**
- [ ] All navigation paths work without dead ends
- [ ] Circular flow: list ↔ detail ↔ confirmation → list/inicio
- [ ] No code duplication across handlers

### Test Scenarios

**Happy Path:**
1. User opens VIP menu → clicks "Tesoros del Sanctum" → sees package list
2. User clicks package → sees detail view with all info
3. User clicks "Me interesa" → sees confirmation message
4. User clicks "Escribirme" → opens Telegram chat with Diana
5. User clicks "Regresar" → returns to package list
6. User clicks "Inicio" → returns to VIP main menu

**Edge Cases:**
1. Package with price=None (free) → shows "Acceso gratuito"
2. Package with no description → shows "Sin descripción"
3. Invalid package_id → shows error alert
4. Debounce window active → shows "Interés registrado previamente"

---

## Execution Guidelines

### Before Execution
- [ ] Read 12-CONTEXT.md for implementation decisions
- [ ] Review Phase 6-8 summaries for existing patterns
- [ ] Verify ContentService has `get_package_by_id()` method

### During Execution
- [ ] Execute plans by wave (Wave 1 first, then Wave 2)
- [ ] Run plans within each wave in parallel
- [ ] Create SUMMARY.md after each plan completion

### After Execution
- [ ] Update ROADMAP.md phase status to ✅ COMPLETE
- [ ] Update STATE.md with new decisions
- [ ] Run verification checklist from above

---

## Success Metrics

### Functional Requirements
- ✅ User sees package list with individual buttons (name only)
- ✅ User can click package to see detail view
- ✅ Detail view shows complete information (name, description, price, type)
- ✅ Detail view has "Me interesa" button
- ✅ Navigation allows returning to list from detail view
- ✅ Confirmation message shows contact button
- ✅ Navigation allows returning to list or main menu from confirmation

### Non-Functional Requirements
- ✅ Lucien's voice preserved in list and detail views
- ✅ Diana's voice used in confirmation message (personal tone)
- ✅ Admin notifications still sent (Phase 8 integration)
- ✅ No code duplication in navigation handlers
- ✅ Consistent with Phase 6 navigation patterns

---

## Post-Phase Fixes (2026-01-27)

### Issues Identified After Implementation

Following phase completion, 6 architectural issues were identified and fixed:

| Error | Root Cause | Fix |
|-------|------------|-----|
| **Navigation crash** | Generic handler `user:packages:{id}` registered before specific `user:packages:back` | Reordered handlers: specific before generic |
| **AttributeError `.flow`** | Code used `container.message.user.flow` but ServiceContainer exposes `.flows` | Changed to `container.message.user.flows` |
| **Incorrect menu for VIP channel users** | Used `is_vip_active()` which only checks subscription, not channel membership | Changed to `container.role_detection.get_user_role()` |
| **Inconsistent role detection** | Used stale `user.role` from DB instead of real-time detection | Implemented correct priority: Admin > VIP Channel > VIP Subscription > Free |
| **VIP status AttributeError** | Model uses `expiry_date` but code accessed `expires_at` | Changed to `subscriber.expiry_date` |
| **Service container access** | Manual instantiation of RoleDetectionService with `container.session` | Use `container.role_detection` property |

### Commits

- `2c5e62b` - Architectural role detection fixes (6 errors)
- `d6f9cbb` - Fix container.session access
- `8a94e75` - Fix expires_at → expiry_date

### Lessons Learned

1. **Handler Registration Order:** Specific callback patterns must be registered before generic patterns to prevent capture conflicts
2. **Role Detection Priority:** VIP channel membership is the highest priority for VIP detection (above subscription checks)
3. **Service Container Usage:** Always use container properties (e.g., `container.role_detection`) instead of manual service instantiation
4. **Model Attribute Names:** Verify model schema (Column names) before accessing attributes in handlers

---

## Risk Mitigation

### Risk: Breaking existing interest registration
**Mitigation:** Plan 12-03 preserves `InterestService.register_interest()` call and admin notification logic from Phase 8. Old callback pattern `interest:package:{id}` is deprecated but still works.

### Risk: Navigation dead ends
**Mitigation:** Plan 12-04 ensures circular navigation flow. All views have at least one navigation button leading to another valid view.

### Risk: Message tone inconsistency
**Mitigation:** Plan 12-03 specifies Diana's warm/personal voice for confirmation (no 🎩 emoji), distinct from Lucien's butler voice in other views.

---

## Next Steps

After Phase 12 completion:
1. Execute `/gsd:execute-phase 12` to run all 4 plans
2. Verify user flows manually (test scenarios above)
3. Update project documentation with new callback patterns
4. Consider Phase 13 (VIP Ritualized Entry Flow) or Phase 14 (Future Enhancements)

---

*Phase planning completed 2026-01-27*
*4 plans ready for execution in 2 waves*
