# Requirements: Sistema de Menús

**Defined:** 2026-01-24
**Core Value:** Cada usuario recibe una experiencia de menú personalizada según su rol (Admin/VIP/Free), con la voz consistente de Lucien y opciones relevantes a su contexto.

## v1.1 Requirements

Requerimientos para el milestone "Sistema de Menús". Cada requerimiento mapea a una fase específica del roadmap.

### Role Detection (MENU)

- [x] **MENU-01**: Sistema detecta automáticamente el rol del usuario (Admin/VIP/Free)
- [x] **MENU-02**: Menú principal de usuario se adapta según rol detectado
- [x] **MENU-03**: Admin puede ver rol de cualquier usuario en el sistema
- [x] **MENU-04**: Sistema recalcula rol automáticamente cuando cambia estado (Free→VIP, VIP expira)

### Lucien Menu Providers (VOICE)

- [x] **VOICE-01**: UserMenuProvider entrega mensajes para menú VIP con voz de Lucien
- [x] **VOICE-02**: UserMenuProvider entrega mensajes para menú Free con voz de Lucien
- [ ] **VOICE-03**: UserFlowProvider entrega mensaje de bienvenida al canal Free con redes sociales
- [ ] **VOICE-04**: UserFlowProvider entrega mensaje de aprobación de acceso con botón al canal
- [ ] **VOICE-05**: UserFlowProvider entrega mensaje de bienvenida al canal VIP
- [x] **VOICE-06**: Todos los textos de botones de navegación usan terminología de Lucien

### Keyboard & Navigation (NAV)

- [x] **NAV-01**: MenuService centraliza lógica de navegación entre menús
- [x] **NAV-02**: Sistema de callbacks unificado para navegación (menu:main, menu:vip, menu:free)
- [x] **NAV-03**: Navegación jerárquica con botón "Volver" en submenús
- [x] **NAV-04**: Handlers de menú usuario integrados con LucienVoiceService
- [x] **NAV-05**: Sistema de menús reemplaza completamente keyboards.py hardcoded

### User Menu: VIP (VIPMENU)

- [x] **VIPMENU-01**: Menú VIP muestra información de suscripción (fecha expiración, plan actual)
- [x] **VIPMENU-02**: Menú VIP tiene opción "Premium" con información de compra
- [x] **VIPMENU-03**: Cada paquete premium tiene botón "Me interesa" que notifica al admin
- [x] **VIPMENU-04**: Menú VIP tiene botón "Volver" y navegación fluida

### User Menu: Free (FREEMENU)

- [x] **FREEMENU-01**: Menú Free tiene opción "Mi Contenido" que abre submenú de paquetes
- [x] **FREEMENU-02**: Submenú "Mi Contenido" lista paquetes disponibles (cada uno es un botón)
- [x] **FREEMENU-03**: Cada paquete muestra información con botón "Me interesa"
- [x] **FREEMENU-04**: Menú Free tiene opción "Canal VIP" con info de suscripción
- [x] **FREEMENU-05**: Menú Free tiene opción de redes sociales/contenido gratuito

### Content Packages (CONTENT)

- [x] **CONTENT-01**: Base de datos con tabla ContentPackage (id, name, description, price, category)
- [x] **CONTENT-02**: Categorías de paquetes: FREE_CONTENT, VIP_CONTENT, VIP_PREMIUM
- [x] **CONTENT-03**: Servicio ContentService para CRUD de paquetes
- [x] **CONTENT-04**: Admin puede crear paquetes de contenido
- [x] **CONTENT-05**: Admin puede editar paquetes existentes
- [x] **CONTENT-06**: Admin puede eliminar paquetes (soft delete con is_active)
- [x] **CONTENT-07**: Menús de usuario muestran solo paquetes activos (is_active=True)

### Interest Notifications (INTEREST)

- [x] **INTEREST-01**: Botón "Me interesa" en paquetes crea registro de interés
- [x] **INTEREST-02**: Base de datos con tabla UserInterest (id, user_id, package_id, created_at, is_attended)
- [x] **INTEREST-03**: Admin recibe mensaje privado cuando usuario marca "Me interesa"
- [x] **INTEREST-04**: Notificación incluye: nombre de usuario, link al perfil, paquete de interés
- [x] **INTEREST-05**: Servicio InterestService para gestión de intereses

### Admin Menu: User Management (ADMIN-USR)

- [x] **ADMIN-USR-01**: Menú admin tiene opción "Gestión de Usuarios"
- [x] **ADMIN-USR-02**: Admin puede ver información detallada de cualquier usuario
- [x] **ADMIN-USR-03**: Admin puede cambiar rol de usuario (Free↔VIP)
- [x] **ADMIN-USR-04**: Admin puede bloquear usuario (impide usar el bot)
- [x] **ADMIN-USR-05**: Admin puede expulsar usuario (elimina del canal)

### Admin Menu: Interests (ADMIN-INT)

- [x] **ADMIN-INT-01**: Menú admin tiene opción "Intereses" para ver notificaciones pendientes
- [x] **ADMIN-INT-02**: Lista de intereses organizada por fecha (último arriba)
- [x] **ADMIN-INT-03**: Admin puede marcar interés como "Atendido"
- [x] **ADMIN-INT-04**: Admin tiene link directo al perfil de Telegram del usuario
- [x] **ADMIN-INT-05**: Admin puede ver qué paquete interesó al usuario

### Admin Menu: Content Packages (ADMIN-CONTENT)

- [x] **ADMIN-CONTENT-01**: Menú admin tiene opción "Paquetes de Contenido"
- [x] **ADMIN-CONTENT-02**: Admin puede listar todos los paquetes (activos e inactivos)
- [x] **ADMIN-CONTENT-03**: Admin puede crear nuevo paquete con wizard
- [x] **ADMIN-CONTENT-04**: Admin puede editar paquete existente
- [x] **ADMIN-CONTENT-05**: Admin puede desactivar paquete (soft delete)

### Free Channel Entry Flow (FLOW-FREE)

- [ ] **FLOW-FREE-01**: Mensaje de solicitud de acceso usa voz de Lucien
- [ ] **FLOW-FREE-02**: Mensaje incluye redes sociales de la creadora
- [ ] **FLOW-FREE-03**: Mensaje explica tiempo de espera (justificación de muchas solicitudes)
- [ ] **FLOW-FREE-04**: Mensaje sugiere seguir redes sociales para acelerar ingreso
- [ ] **FLOW-FREE-05**: Mensaje de aprobación incluye botón de acceso directo al canal
- [ ] **FLOW-FREE-06**: Aprobación automática después de tiempo configurado (5 min actual)

### Documentation (DOCS)

- [ ] **DOCS-01**: Documentación exhaustiva del sistema de menús en código (docstrings)
- [ ] **DOCS-02**: Documentación en archivos .md sobre arquitectura de menús
- [ ] **DOCS-03**: Guía de integración para agregar nuevas opciones de menú
- [ ] **DOCS-04**: Ejemplos de uso del sistema de menús

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| MENU-01 | Phase 5 | Complete |
| MENU-02 | Phase 5 | Complete |
| MENU-03 | Phase 9 | Pending |
| MENU-04 | Phase 5 | Complete |
| VOICE-01 | Phase 6 | Complete |
| VOICE-02 | Phase 6 | Complete |
| VOICE-03 | Phase 10 | Pending |
| VOICE-04 | Phase 10 | Pending |
| VOICE-05 | Phase 10 | Pending |
| VOICE-06 | Phase 6 | Complete |
| NAV-01 | Phase 7 | Complete |
| NAV-02 | Phase 7 | Complete |
| NAV-03 | Phase 7 | Complete |
| NAV-04 | Phase 6 | Complete |
| NAV-05 | Phase 6 | Complete |
| VIPMENU-01 | Phase 6 | Complete |
| VIPMENU-02 | Phase 6 | Complete |
| VIPMENU-03 | Phase 6 | Complete |
| VIPMENU-04 | Phase 6 | Complete |
| FREEMENU-01 | Phase 6 | Complete |
| FREEMENU-02 | Phase 6 | Complete |
| FREEMENU-03 | Phase 6 | Complete |
| FREEMENU-04 | Phase 6 | Complete |
| FREEMENU-05 | Phase 6 | Complete |
| CONTENT-01 | Phase 5 | Complete |
| CONTENT-02 | Phase 5 | Complete |
| CONTENT-03 | Phase 5 | Complete |
| CONTENT-04 | Phase 7 | Complete |
| CONTENT-05 | Phase 7 | Complete |
| CONTENT-06 | Phase 7 | Complete |
| CONTENT-07 | Phase 6 | Complete |
| INTEREST-01 | Phase 8 | Complete |
| INTEREST-02 | Phase 8 | Complete |
| INTEREST-03 | Phase 8 | Complete |
| INTEREST-04 | Phase 8 | Complete |
| INTEREST-05 | Phase 8 | Complete |
| ADMIN-USR-01 | Phase 9 | Pending |
| ADMIN-USR-02 | Phase 9 | Pending |
| ADMIN-USR-03 | Phase 9 | Pending |
| ADMIN-USR-04 | Phase 9 | Pending |
| ADMIN-USR-05 | Phase 9 | Pending |
| ADMIN-INT-01 | Phase 8 | Complete |
| ADMIN-INT-02 | Phase 8 | Complete |
| ADMIN-INT-03 | Phase 8 | Complete |
| ADMIN-INT-04 | Phase 8 | Complete |
| ADMIN-INT-05 | Phase 8 | Complete |
| ADMIN-CONTENT-01 | Phase 7 | Complete |
| ADMIN-CONTENT-02 | Phase 7 | Complete |
| ADMIN-CONTENT-03 | Phase 7 | Complete |
| ADMIN-CONTENT-04 | Phase 7 | Complete |
| ADMIN-CONTENT-05 | Phase 7 | Complete |
| FLOW-FREE-01 | Phase 10 | Pending |
| FLOW-FREE-02 | Phase 10 | Pending |
| FLOW-FREE-03 | Phase 10 | Pending |
| FLOW-FREE-04 | Phase 10 | Pending |
| FLOW-FREE-05 | Phase 10 | Pending |
| FLOW-FREE-06 | Phase 10 | Pending |
| DOCS-01 | Phase 11 | Pending |
| DOCS-02 | Phase 11 | Pending |
| DOCS-03 | Phase 11 | Pending |
| DOCS-04 | Phase 11 | Pending |

**Coverage:**
- v1.1 requirements: 60 total
- Mapped to phases: 60
- Complete: 30 (50%)
- Pending: 30
- Unmapped: 0 ✓

## Out of Scope

| Feature | Reason |
|---------|--------|
| Roles personalizados/customizables | Solo 3 roles fijos (Admin/VIP/Free) son suficientes |
| i18n de menús | Solo español en v1.1, estructura puede prepararse pero sin implementación |
| A/B testing de menús | No hay métricas de efectividad aún |
| Menús contextuales según hora/comportamiento | Complejidad innecesaria para v1.1 |
| Historial de navegación de menús | No se requiere para funcionalidad core |

---
*Requirements defined: 2026-01-24*
*Last updated: 2026-01-24 after roadmap creation*
