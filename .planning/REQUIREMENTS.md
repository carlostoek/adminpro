# Requirements: LucienVoiceService

**Defined:** 2026-01-23
**Core Value:** Consistencia absoluta en la voz de Lucien: cada mensaje del bot debe sonar elegante, misterioso y natural viniendo del mayordomo, sin importar qué handler o flujo lo invoque.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Template Foundation

- [ ] **TMPL-01**: Servicio soporta interpolación de variables (nombres, fechas, números, estados)
- [ ] **TMPL-02**: Todos los mensajes retornan HTML formateado para Telegram (bold, italic, code, links)
- [ ] **TMPL-03**: Mensajes centralizados en servicio (cero strings hardcodeados en handlers)
- [ ] **TMPL-04**: Cada mensaje retorna tupla (text, keyboard) con botones integrados
- [ ] **TMPL-05**: Estándares consistentes para mensajes de error y éxito

### Voice Consistency

- [ ] **VOICE-01**: Sistema de variaciones aleatorias (mínimo 2-3 versiones por mensaje clave)
- [ ] **VOICE-02**: Variaciones ponderadas (comunes vs raras) usando random.choices
- [ ] **VOICE-03**: Tone directives integradas (reglas de voz de Lucien en código)
- [ ] **VOICE-04**: Validación automática de anti-patrones (tutear, jerga técnica, emoji incorrecto)
- [ ] **VOICE-05**: Cada mensaje usa emoji característico de Lucien (🎩 para él, 🌸 para Diana)

### Dynamic Content

- [ ] **DYN-01**: Bloques condicionales (contenido diferente según rol VIP/Free/Admin)
- [ ] **DYN-02**: Renderizado de listas dinámicas (suscriptores, tokens, solicitudes)
- [ ] **DYN-03**: Adaptación contextual (saludos varían por hora del día, frecuencia de uso)
- [ ] **DYN-04**: Composición de templates (base + variantes) sin duplicación de código

### Integration

- [ ] **INTEG-01**: Servicio integrado en ServiceContainer con lazy loading
- [ ] **INTEG-02**: Servicio es stateless (no acumula state entre llamadas)
- [ ] **INTEG-03**: Servicio usa formatters existentes (bot/utils/formatters.py) para fechas/números
- [ ] **INTEG-04**: Migración de keyboards de bot/utils/keyboards.py al servicio

### Handler Refactoring

- [ ] **REFAC-01**: Migrar handlers admin/main.py (menú principal)
- [ ] **REFAC-02**: Migrar handlers admin/vip.py (gestión VIP)
- [ ] **REFAC-03**: Migrar handlers admin/free.py (gestión Free)
- [ ] **REFAC-04**: Migrar handlers user/start.py (comando /start)
- [ ] **REFAC-05**: Migrar handlers user/vip_flow.py (canje de tokens)
- [ ] **REFAC-06**: Migrar handlers user/free_flow.py (solicitudes Free)
- [ ] **REFAC-07**: Todos los tests E2E existentes siguen pasando después de refactor

### Testing

- [ ] **TEST-01**: Helpers semánticos para tests (assert_message_contains_greeting vs string matching)
- [ ] **TEST-02**: Tests unitarios para cada tipo de mensaje (greetings, errors, confirmations)
- [ ] **TEST-03**: Tests de integración con handlers refactorizados

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Voice Features

- **VOICE-06**: Preview mode (ver todas las variaciones de un mensaje sin ejecutar bot)
- **VOICE-07**: Voice audit dashboard (métricas de consistencia por handler)
- **VOICE-08**: Persistencia de variaciones (rastrear qué variante vio cada usuario)

### Advanced Testing

- **TEST-04**: A/B testing framework (comparar efectividad de variaciones)
- **TEST-05**: Voice regression tests (detectar cambios no intencionales en tono)

### Scalability

- **SCALE-01**: Cache de mensajes frecuentes (optimización para >1000 usuarios)
- **SCALE-02**: Lazy loading de templates (solo cargar categorías usadas)

### Future Features

- **i18n-01**: Estructura extensible para agregar idiomas (sin implementación aún)
- **GAMIF-01**: Mensajes para sistema de gamificación (misiones, logros)
- **NARR-01**: Mensajes para sistema narrativo (contenido exclusivo, secretos)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Database-stored messages | Versión control en código es superior; BD complica deployment y testing |
| Dynamic template generation (eval/exec) | Riesgo de seguridad; f-strings son suficientes y más rápidas |
| Per-user message customization | Rompe consistencia de voz; todos deben recibir Lucien auténtico |
| Real-time translation | i18n diferido a v2+; español es único idioma requerido ahora |
| Jinja2/Mako templates | Overhead innecesario (50ms+, 5MB+); stdlib f-strings <5ms |
| Multi-personality support | Solo voz de Lucien; otros personajes fuera de scope |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TMPL-01 | TBD | Pending |
| TMPL-02 | TBD | Pending |
| TMPL-03 | TBD | Pending |
| TMPL-04 | TBD | Pending |
| TMPL-05 | TBD | Pending |
| VOICE-01 | TBD | Pending |
| VOICE-02 | TBD | Pending |
| VOICE-03 | TBD | Pending |
| VOICE-04 | TBD | Pending |
| VOICE-05 | TBD | Pending |
| DYN-01 | TBD | Pending |
| DYN-02 | TBD | Pending |
| DYN-03 | TBD | Pending |
| DYN-04 | TBD | Pending |
| INTEG-01 | TBD | Pending |
| INTEG-02 | TBD | Pending |
| INTEG-03 | TBD | Pending |
| INTEG-04 | TBD | Pending |
| REFAC-01 | TBD | Pending |
| REFAC-02 | TBD | Pending |
| REFAC-03 | TBD | Pending |
| REFAC-04 | TBD | Pending |
| REFAC-05 | TBD | Pending |
| REFAC-06 | TBD | Pending |
| REFAC-07 | TBD | Pending |
| TEST-01 | TBD | Pending |
| TEST-02 | TBD | Pending |
| TEST-03 | TBD | Pending |

**Coverage:**
- v1 requirements: 28 total
- Mapped to phases: 0 (will be mapped by roadmapper)
- Unmapped: 28 ⚠️

---
*Requirements defined: 2026-01-23*
*Last updated: 2026-01-23 after initial definition*
