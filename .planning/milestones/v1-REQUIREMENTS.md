# Requirements Archive: v1 LucienVoiceService

**Archived:** 2026-01-24
**Status:** SHIPPED

This is the archived requirements specification for v1.0 LucienVoiceService - Sistema Centralizado de Mensajes con Voz de Lucien.

For current requirements, see `.planning/REQUIREMENTS.md` (created for next milestone).

---

# Requirements: LucienVoiceService

**Defined:** 2026-01-23
**Core Value:** Consistencia absoluta en la voz de Lucien: cada mensaje del bot debe sonar elegante, misterioso y natural viniendo del mayordomo, sin importar qué handler o flujo lo invoque.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Template Foundation

- [x] **TMPL-01**: Servicio soporta interpolacion de variables (nombres, fechas, numeros, estados) - Phase 2 - SATISFIED
- [x] **TMPL-02**: Todos los mensajes retornan HTML formateado para Telegram (bold, italic, code, links) - Phase 1 - SATISFIED
- [x] **TMPL-03**: Mensajes centralizados en servicio (cero strings hardcodeados en handlers) - Phase 1 - SATISFIED
- [x] **TMPL-04**: Cada mensaje retorna tupla (text, keyboard) con botones integrados - Phase 2 - SATISFIED
- [x] **TMPL-05**: Estandares consistentes para mensajes de error y exito - Phase 1 - SATISFIED

### Voice Consistency

- [x] **VOICE-01**: Sistema de variaciones aleatorias (minimo 2-3 versiones por mensaje clave) - Phase 2 - SATISFIED
- [x] **VOICE-02**: Variaciones ponderadas (comunes vs raras) usando random.choices - Phase 2 - SATISFIED
- [x] **VOICE-03**: Tone directives integradas (reglas de voz de Lucien en codigo) - Phase 1 - SATISFIED
- [x] **VOICE-04**: Validacion automatica de anti-patrones (tutear, jerga tecnica, emoji incorrecto) - Phase 1 - SATISFIED
- [x] **VOICE-05**: Cada mensaje usa emoji caracteristico de Lucien (para el,  para Diana) - Phase 1 - SATISFIED

### Dynamic Content

- [x] **DYN-01**: Bloques condicionales (contenido diferente segun rol VIP/Free/Admin) - Phase 2 - SATISFIED
- [x] **DYN-02**: Renderizado de listas dinamicas (suscriptores, tokens, solicitudes) - Phase 3 - SATISFIED
- [x] **DYN-03**: Adaptacion contextual (saludos varian por hora del dia, frecuencia de uso) - Phase 3 - SATISFIED
- [x] **DYN-04**: Composicion de templates (base + variantes) sin duplicacion de codigo - Phase 2 - SATISFIED

### Integration

- [x] **INTEG-01**: Servicio integrado en ServiceContainer con lazy loading - Phase 1 - SATISFIED
- [x] **INTEG-02**: Servicio es stateless (no acumula state entre llamadas) - Phase 1 - SATISFIED
- [x] **INTEG-03**: Servicio usa formatters existentes (bot/utils/formatters.py) para fechas/numeros - Phase 1 - SATISFIED
- [x] **INTEG-04**: Migracion de keyboards de bot/utils/keyboards.py al servicio - Phase 2 - SATISFIED

### Handler Refactoring

- [x] **REFAC-01**: Migrar handlers admin/main.py (menu principal) - Phase 2 - SATISFIED
- [x] **REFAC-02**: Migrar handlers admin/vip.py (gestion VIP) - Phase 2 - SATISFIED
- [x] **REFAC-03**: Migrar handlers admin/free.py (gestion Free) - Phase 2 - SATISFIED
- [x] **REFAC-04**: Migrar handlers user/start.py (comando /start) - Phase 3 - SATISFIED
- [x] **REFAC-05**: Migrar handlers user/vip_flow.py (canje de tokens) - Phase 3 - SATISFIED (DEPRECATED: removed in favor of deep link activation)
- [x] **REFAC-06**: Migrar handlers user/free_flow.py (solicitudes Free) - Phase 3 - SATISFIED
- [x] **REFAC-07**: Todos los tests E2E existentes siguen pasando despues de refactor - Phase 3 - SATISFIED

### Testing

- [x] **TEST-01**: Helpers semanticos para tests (assert_message_contains_greeting vs string matching) - Phase 3 - SATISFIED
- [x] **TEST-02**: Tests unitarios para cada tipo de mensaje (greetings, errors, confirmations) - Phase 3 - SATISFIED
- [x] **TEST-03**: Tests de integracion con handlers refactorizados - Phase 3 - SATISFIED

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Voice Features

- [ ] **VOICE-06**: Preview mode (ver todas las variaciones de un mensaje sin ejecutar bot) - DELIVERED in Phase 4
- [ ] **VOICE-07**: Voice audit dashboard (metricas de consistencia por handler)
- [ ] **VOICE-08**: Persistencia de variaciones (rastrear que variante vio cada usuario)

### Advanced Testing

- [ ] **TEST-04**: A/B testing framework (comparar efectividad de variaciones)
- [ ] **TEST-05**: Voice regression tests (detectar cambios no intencionales en tono)

### Scalability

- [ ] **SCALE-01**: Cache de mensajes frecuentes (optimizacion para >1000 usuarios)
- [ ] **SCALE-02**: Lazy loading de templates (solo cargar categorias usadas)

### Future Features

- [ ] **i18n-01**: Estructura extensible para agregar idiomas (sin implementacion aun)
- [ ] **GAMIF-01**: Mensajes para sistema de gamificacion (misiones, logros)
- [ ] **NARR-01**: Mensajes para sistema narrativo (contenido exclusivo, secretos)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Database-stored messages | Version control en codigo es superior; BD complica deployment y testing |
| Dynamic template generation (eval/exec) | Riesgo de seguridad; f-strings son suficientes y mas rapidas |
| Per-user message customization | Rompe consistencia de voz; todos deben recibir Lucien autentico |
| Real-time translation | i18n diferido a v2+; espanol es unico idioma requerido ahora |
| Jinja2/Mako templates | Overhead innecesario (50ms+, 5MB+); stdlib f-strings <5ms |
| Multi-personality support | Solo voz de Lucien; otros personajes fuera de scope |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TMPL-01 | Phase 2 | Complete |
| TMPL-02 | Phase 1 | Complete |
| TMPL-03 | Phase 1 | Complete |
| TMPL-04 | Phase 2 | Complete |
| TMPL-05 | Phase 1 | Complete |
| VOICE-01 | Phase 2 | Complete |
| VOICE-02 | Phase 2 | Complete |
| VOICE-03 | Phase 1 | Complete |
| VOICE-04 | Phase 1 | Complete |
| VOICE-05 | Phase 1 | Complete |
| DYN-01 | Phase 2 | Complete |
| DYN-02 | Phase 3 | Complete |
| DYN-03 | Phase 3 | Complete |
| DYN-04 | Phase 2 | Complete |
| INTEG-01 | Phase 1 | Complete |
| INTEG-02 | Phase 1 | Complete |
| INTEG-03 | Phase 1 | Complete |
| INTEG-04 | Phase 2 | Complete |
| REFAC-01 | Phase 2 | Complete |
| REFAC-02 | Phase 2 | Complete |
| REFAC-03 | Phase 2 | Complete |
| REFAC-04 | Phase 3 | Complete |
| REFAC-05 | Phase 3 | Complete (file removed) |
| REFAC-06 | Phase 3 | Complete |
| REFAC-07 | Phase 3 | Complete |
| TEST-01 | Phase 3 | Complete |
| TEST-02 | Phase 3 | Complete |
| TEST-03 | Phase 3 | Complete |

**Coverage:**
- v1 requirements: 28 total
- Phase 1 complete: 9/28 (32%)
- Phase 2 complete: 10/28 (36%)
- Phase 3 complete: 9/28 (32%)
- Total complete: 28/28 (100%)
- Mapped to phases: 28
- Unmapped: 0

---

## Milestone Summary

**Shipped:** 28 of 28 v1 requirements (100%)
**Adjusted:**
- REFAC-05 (user/vip_flow.py) - File removed as manual token redemption deprecated in favor of deep link activation
**Dropped:** None

---

*Archived: 2026-01-24 as part of v1.0 milestone completion*
*Requirements defined: 2026-01-23*
*Last updated: 2026-01-24 after Phase 4 completion*
