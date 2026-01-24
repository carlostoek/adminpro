# LucienVoiceService - Sistema Centralizado de Mensajes

## What This Is

Un servicio centralizado que gestiona todos los mensajes del bot con la voz caracteristica de Lucien (mayordomo sofisticado de Diana). El servicio provee templates organizados por flujo de navegacion, soporta dinamismo completo (variables, condicionales, listas dinamicas, variaciones aleatorias), y retorna mensajes formateados en HTML junto con sus keyboards inline correspondientes. Diseado para reemplazar todos los mensajes hardcodeados dispersos en los handlers actuales.

## Current State

**v1.0 SHIPPED** (2026-01-24)

The centralized message service is production-ready with:
- 7 message providers delivering Lucien's voice across all bot interactions
- Stateless architecture with lazy loading via ServiceContainer
- Session-aware variation selection preventing repetition
- Voice validation pre-commit hook for consistency enforcement
- Message preview CLI tool for development workflow
- ~330 lines of hardcoded strings eliminated
- 140/140 tests passing

## Core Value

Consistencia absoluta en la voz de Lucien: cada mensaje del bot debe sonar elegante, misterioso y natural viniendo del mayordomo, sin importar que handler o flujo lo invoque.

## Requirements

### Validated

Infraestructura existente que funciona y ha sido preservada:

- ✓ Bot de Telegram funcional con aiogram 3.4.1 — v1.0
- ✓ Sistema VIP/Free completo (tokens, canjes, solicitudes, background tasks) — v1.0
- ✓ Service Container con DI y lazy loading — v1.0
- ✓ 6 servicios de negocio (Subscription, Channel, Config, Pricing, Stats, User) — v1.0
- ✓ Middlewares (Database session injection, AdminAuth) — v1.0
- ✓ FSM States para flujos multi-paso (admin y user) — v1.0
- ✓ Handlers organizados por rol (admin/, user/) — v1.0
- ✓ Utilities (Formatters, Keyboards, Validators, Pagination) — v1.0
- ✓ SQLAlchemy Async ORM con SQLite — v1.0
- ✓ Background tasks con APScheduler — v1.0
- ✓ Suite de tests E2E — v1.0

**v1.0 Message Service Requirements (ALL SATISFIED):**

Template Foundation:
- ✓ TMPL-01: Variable interpolation — v1.0
- ✓ TMPL-02: HTML formatting — v1.0
- ✓ TMPL-03: Centralized messages — v1.0
- ✓ TMPL-04: Keyboard integration — v1.0
- ✓ TMPL-05: Error/success standards — v1.0

Voice Consistency:
- ✓ VOICE-01: Random variations — v1.0
- ✓ VOICE-02: Weighted variations — v1.0
- ✓ VOICE-03: Tone directives — v1.0
- ✓ VOICE-04: Anti-pattern validation — v1.0
- ✓ VOICE-05: Emoji consistency — v1.0

Dynamic Content:
- ✓ DYN-01: Conditional blocks — v1.0
- ✓ DYN-02: Dynamic lists — v1.0
- ✓ DYN-03: Contextual adaptation — v1.0
- ✓ DYN-04: Template composition — v1.0

Integration:
- ✓ INTEG-01: ServiceContainer integration — v1.0
- ✓ INTEG-02: Stateless service — v1.0
- ✓ INTEG-03: Formatter integration — v1.0
- ✓ INTEG-04: Keyboard migration — v1.0

Handler Refactoring:
- ✓ REFAC-01: admin/main.py migration — v1.0
- ✓ REFAC-02: admin/vip.py migration — v1.0
- ✓ REFAC-03: admin/free.py migration — v1.0
- ✓ REFAC-04: user/start.py migration — v1.0
- ✓ REFAC-05: user/vip_flow.py removed (deep link only) — v1.0
- ✓ REFAC-06: user/free_flow.py migration — v1.0
- ✓ REFAC-07: E2E tests passing — v1.0

Testing:
- ✓ TEST-01: Semantic helpers — v1.0
- ✓ TEST-02: Unit tests — v1.0
- ✓ TEST-03: Integration tests — v1.0

### Active

No active requirements. v1.0 complete. Next milestone TBD.

### Out of Scope

Caracteristicas explcitamente excluidas de v1:

- **Internacionalizacion (i18n)** — Solo espanol por ahora; estructura puede prepararse pero sin implementacion
- **Sistema de gamificacion** — Servicio debe ser extensible pero no incluir mensajes de misiones/logros aun
- **Sistema de narrativa** — Servicio debe ser extensible pero no incluir contenido narrativo aun
- **Persistencia de variaciones** — No rastrear que variante se mostro a cada usuario (puede agregarse despues)
- **A/B testing** — No metricas de efectividad de diferentes variantes
- **Voice profiles alternos** — Solo voz de Lucien, sin variaciones de personalidad

## Context

### Codebase State

El bot tiene una arquitectura solida en produccion con v1.0 message service integrado:

- **Patron arquitectonico**: Layered Service-Oriented con DI
- **Handler layer**: 5 handlers migrated to use LucienVoiceService (admin/, user/)
- **Service layer**: 7 servicios de negocio + 7 message providers
- **Middleware layer**: Session injection y auth
- **Data access layer**: SQLAlchemy Async ORM
- **State management**: aiogram FSM para flujos multi-paso
- **Background tasks**: APScheduler para mantenimiento autonomo
- **Message service**: LucienVoiceService with session-aware variation selection

### Metrics (v1.0)

- Total lines of code: ~13,000 Python
- Message service code: ~3,500 lines
- Test files: 7 (140 tests passing)
- Providers: 7 (Common, AdminMain, AdminVIP, AdminFree, UserStart, UserFlow, SessionHistory)
- Handlers migrated: 5 files
- Hardcoded strings eliminated: ~330 lines
- Memory overhead: ~80 bytes/user for session history
- Voice linter performance: 5.09ms average

### Guia de Estilo

Existe `docs/guia-estilo.md` con 410 lineas que definen:
- Personalidad de Lucien (mayordomo sofisticado, observador, misterioso)
- Patrones de dialogo (inicios, transiciones, referencias a Diana, despedidas)
- Terminologia caracteristica ("visitante", "circulo exclusivo", "moneda especial")
- Estructura visual con emojis ( para Lucien,  para Diana, etc.)

## Constraints

- **Tech stack**: Python 3.12.12, aiogram 3.4.1, SQLAlchemy 2.0.25 — No introducir nuevas dependencias pesadas
- **Platform**: Optimizado para Termux (ambiente lightweight) — Evitar generadores de templates complejos (ej: no Jinja2)
- **Compatibilidad**: Integrado con ServiceContainer existente — Sigue patron de lazy loading
- **Testing**: Todos los tests E2E actuales pasan — Sin romper funcionalidad existente
- **Performance**: Mensajes generan en <10ms (objetivo logrado: ~5ms)
- **Memoria**: Sin caches grandes en memoria — Sistema liviano (~80 bytes/user para sesiones)
- **Deployment**: Sin cambios en main.py mas alla de importar el servicio — Minima invasion

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Sistema hibrido: metodos estaticos + string templates | Pool de variaciones necesita flexibilidad; metodos estaticos mantienen simplicidad y performance; evita overhead de Jinja2 en Termux | ✓ Good |
| Organizacion por flujo de navegacion | Alineado con estructura mental del usuario (main_menu, vip, free) vs tecnico (greetings, errors); facilita encontrar mensajes relacionados | ✓ Good |
| Keyboards integrados con mensajes | Cada mensaje conoce sus acciones asociadas; previene desincronizacion entre texto y botones; API mas limpia para handlers | ✓ Good |
| Refactor completo vs gradual | Mejor consistencia total; evita mantener dos sistemas en paralelo; proyecto pequeno permite refactor completo sin riesgo alto | ✓ Good |
| Variaciones aleatorias con ponderacion | Algunas frases mas "Lucien" que otras; ponderacion permite controlar frecuencia; seed opcional para testing deterministico | ✓ Good |
| Sin i18n por ahora | Espanol es unico idioma necesario; i18n agregaria complejidad sin beneficio inmediato; estructura extensible permite agregarlo despues | — Pending |
| Stateless architecture (no session/bot in __init__) | Previene memory leaks; session context passed as parameters instead; lazy cleanup with hash-based trigger | ✓ Good |
| AST-based voice linting | Pure stdlib ast module for voice violation detection; no external dependencies; 5.09ms performance (20x better than 100ms target) | ✓ Good |
| Session-aware variation selection | Exclusion window of 2 prevents repetition while maintaining small variant set usability; ~80 bytes/user memory overhead | ✓ Good |
| Manual token redemption deprecated | Deep link activation provides better UX (one-click vs manual typing); removed vip_flow.py (188 lines) | ✓ Good |

---

*Last updated: 2026-01-24 after v1.0 milestone*
