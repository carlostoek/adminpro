# LucienVoiceService - Sistema Centralizado de Mensajes

## What This Is

Un servicio centralizado que gestiona todos los mensajes del bot con la voz caracteristica de Lucien (mayordomo sofisticado de Diana). El servicio provee templates organizados por flujo de navegacion, soporta dinamismo completo (variables, condicionales, listas dinamicas, variaciones aleatorias), y retorna mensajes formateados en HTML junto con sus keyboards inline correspondientes. Diseado para reemplazar todos los mensajes hardcodeados dispersos en los handlers actuales.

## Current Milestone: v1.3 Redis Caching (Planned)

**Goal:** Add Redis caching layer for FSM state persistence and application-level caching (BotConfig, roles, channels).

**Target features:**

### Redis Infrastructure
- Redis connection with async redis-py
- FSM state storage using aiogram RedisStorage
- CacheService for application-level caching
- Multi-layer caching strategy

### Cache Management
- Cache invalidation on write operations
- Graceful degradation when Redis unavailable
- Cache warming on startup for critical data
- TTL configuration per cache type

---

## Current State

**v1.2 SHIPPED** (2026-01-30)

Production-ready deployment infrastructure with PostgreSQL migration support, comprehensive test coverage, health monitoring, and performance profiling:
- PostgreSQL and SQLite dual-dialect support with automatic dialect detection
- Alembic migration system with auto-migration on startup
- FastAPI health check endpoint with database connectivity verification
- Railway deployment configuration (Railway.toml, Dockerfile)
- 212 system tests covering all critical flows
- CLI test runner and Telegram /run_tests command
- Performance profiling with pyinstrument (/profile command)
- N+1 query detection and eager loading optimization
- 37/37 v1.2 requirements satisfied (100%)

**v1.1 SHIPPED** (2026-01-28)

Sistema de menús contextuales según rol (Admin/VIP/Free) completamente integrado:
- RoleDetectionService con detección automática de rol (Admin > VIP > Free)
- 3 nuevos modelos de base de datos (ContentPackage, UserInterest, UserRoleChangeLog)
- ContentService con operaciones CRUD para paquetes de contenido
- InterestService con deduplicación de 5 minutos y notificaciones admin
- UserManagementService con validación de permisos y logging de auditoría
- Flujo de ingreso al canal Free con teclado de redes sociales
- Flujo de entrada VIP ritualizado en 3 etapas
- Vista detallada de paquetes con UX mejorada
- Documentación exhaustiva: MENU_SYSTEM.md (1,353 líneas), INTEGRATION_GUIDE.md (1,393 líneas), EXAMPLES.md (3,031 líneas)
- 1,070+ docstrings en servicios y handlers
- 57/57 requerimientos v1.1 satisfechos (100%)

**v1.0 SHIPPED** (2026-01-24)

The centralized message service is production-ready with:
- 7 message providers delivering Lucien's voice across all bot interactions
- Stateless architecture with lazy loading via ServiceContainer
- Session-aware variation selection preventing repetition
- Voice validation pre-commit hook for consistency enforcement
- Message preview CLI tool for development workflow
- ~330 lines of hardcoded strings eliminated
- 140/140 tests passing

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

**v1.1 Menu System Requirements (ALL SATISFIED):**

Role Detection (MENU):
- ✓ MENU-01: Sistema detecta automáticamente rol del usuario — v1.1
- ✓ MENU-02: Menú principal adaptado según rol — v1.1
- ✓ MENU-03: Admin puede ver rol de cualquier usuario — v1.1
- ✓ MENU-04: Recálculo automático de rol — v1.1

Lucien Menu Providers (VOICE):
- ✓ VOICE-01: UserMenuProvider VIP con voz de Lucien — v1.1
- ✓ VOICE-02: UserMenuProvider Free con voz de Lucien — v1.1
- ✓ VOICE-03: UserFlowProvider bienvenida canal Free con redes sociales — v1.1
- ✓ VOICE-04: UserFlowProvider aprobación acceso con botón al canal — v1.1
- ✓ VOICE-05: UserFlowProvider bienvenida canal VIP — v1.1
- ✓ VOICE-06: Terminología de Lucien en botones de navegación — v1.1

Keyboard & Navigation (NAV):
- ✓ NAV-01: MenuService centraliza navegación — v1.1
- ✓ NAV-02: Callbacks unificados (menu:main, menu:vip, menu:free) — v1.1
- ✓ NAV-03: Navegación jerárquica con botón "Volver" — v1.1
- ✓ NAV-04: Handlers integrados con LucienVoiceService — v1.1
- ✓ NAV-05: Sistema reemplaza keyboards.py hardcoded — v1.1

VIP Menu (VIPMENU):
- ✓ VIPMENU-01: Menú VIP muestra info de suscripción — v1.1
- ✓ VIPMENU-02: Menú VIP tiene opción "Premium" — v1.1
- ✓ VIPMENU-03: Botón "Me interesa" en paquetes premium — v1.1
- ✓ VIPMENU-04: Navegación fluida en menú VIP — v1.1

Free Menu (FREEMENU):
- ✓ FREEMENU-01: Menú Free tiene opción "Mi Contenido" — v1.1
- ✓ FREEMENU-02: Submenú lista paquetes disponibles — v1.1
- ✓ FREEMENU-03: Botón "Me interesa" en cada paquete — v1.1
- ✓ FREEMENU-04: Menú Free tiene opción "Canal VIP" — v1.1
- ✓ FREEMENU-05: Menú Free tiene opción redes sociales — v1.1

Content Packages (CONTENT):
- ✓ CONTENT-01: Tabla ContentPackage en BD — v1.1
- ✓ CONTENT-02: Categorías FREE_CONTENT, VIP_CONTENT, VIP_PREMIUM — v1.1
- ✓ CONTENT-03: ContentService para CRUD — v1.1
- ✓ CONTENT-04: Admin puede crear paquetes — v1.1
- ✓ CONTENT-05: Admin puede editar paquetes — v1.1
- ✓ CONTENT-06: Admin puede desactivar paquetes (soft delete) — v1.1
- ✓ CONTENT-07: Menús muestran solo paquetes activos — v1.1

Interest Notifications (INTEREST):
- ✓ INTEREST-01: Botón "Me interesa" crea registro — v1.1
- ✓ INTEREST-02: Tabla UserInterest en BD — v1.1
- ✓ INTEREST-03: Admin recibe notificación privada — v1.1
- ✓ INTEREST-04: Notificación incluye info usuario y paquete — v1.1
- ✓ INTEREST-05: InterestService para gestión — v1.1

Admin User Management (ADMIN-USR):
- ✓ ADMIN-USR-01: Menú admin tiene "Gestión de Usuarios" — v1.1
- ✓ ADMIN-USR-02: Admin puede ver info detallada de usuario — v1.1
- ✓ ADMIN-USR-03: Admin puede cambiar rol de usuario — v1.1
- ✓ ADMIN-USR-04: Admin puede bloquear usuario — v1.1
- ✓ ADMIN-USR-05: Admin puede expulsar usuario del canal — v1.1

Admin Interests (ADMIN-INT):
- ✓ ADMIN-INT-01: Menú admin tiene "Intereses" — v1.1
- ✓ ADMIN-INT-02: Lista de intereses organizada por fecha — v1.1
- ✓ ADMIN-INT-03: Admin puede marcar como "Atendido" — v1.1
- ✓ ADMIN-INT-04: Admin tiene link al perfil del usuario — v1.1
- ✓ ADMIN-INT-05: Admin puede ver paquete de interés — v1.1

Admin Content (ADMIN-CONTENT):
- ✓ ADMIN-CONTENT-01: Menú admin tiene "Paquetes de Contenido" — v1.1
- ✓ ADMIN-CONTENT-02: Admin puede listar todos los paquetes — v1.1
- ✓ ADMIN-CONTENT-03: Admin puede crear paquete con wizard — v1.1
- ✓ ADMIN-CONTENT-04: Admin puede editar paquete — v1.1
- ✓ ADMIN-CONTENT-05: Admin puede desactivar paquete — v1.1

Free Entry Flow (FLOW-FREE):
- ✓ FLOW-FREE-01: Mensaje solicitud usa voz de Lucien — v1.1
- ✓ FLOW-FREE-02: Mensaje incluye redes sociales — v1.1
- ✓ FLOW-FREE-03: Mensaje explica tiempo de espera — v1.1
- ✓ FLOW-FREE-04: Mensaje sugiere seguir redes sociales — v1.1
- ✓ FLOW-FREE-05: Mensaje aprobación tiene botón acceso — v1.1
- ✓ FLOW-FREE-06: Aprobación automática después de tiempo — v1.1

Documentation (DOCS):
- ✓ DOCS-01: Docstrings exhaustivos en código — v1.1
- ✓ DOCS-02: Documentación .md arquitectura menús — v1.1
- ✓ DOCS-03: Guía integración nuevas opciones — v1.1
- ✓ DOCS-04: Ejemplos de uso del sistema — v1.1

**v1.2 Deployment Requirements (ALL SATISFIED):**

Database Migration (DBMIG):
- ✓ DBMIG-01: Sistema soporta PostgreSQL y SQLite — v1.2
- ✓ DBMIG-02: Motor detecta automáticamente el dialecto — v1.2
- ✓ DBMIG-03: Alembic configurado con migración inicial — v1.2
- ✓ DBMIG-04: Migraciones automáticas al iniciar — v1.2
- ✓ DBMIG-05: Script de migración de datos SQLite → PostgreSQL — v1.2
- ✓ DBMIG-06: Validación de tipos en modelos — v1.2
- ✓ DBMIG-07: Rolling back de migraciones soportado — v1.2

Health Monitoring (HEALTH):
- ✓ HEALTH-01: Endpoint HTTP /health — v1.2
- ✓ HEALTH-02: Health check verifica conexión a base de datos — v1.2
- ✓ HEALTH-03: Retorna 200 OK o 503 según estado — v1.2
- ✓ HEALTH-04: Health check en puerto separado — v1.2
- ✓ HEALTH-05: Bot y API de salud corren concurrentemente — v1.2

Railway Preparation (RAIL):
- ✓ RAIL-01: Railway.toml configurado — v1.2
- ✓ RAIL-02: Dockerfile creado — v1.2
- ✓ RAIL-03: Variables de entorno documentadas — v1.2
- ✓ RAIL-04: Validación de variables al inicio — v1.2
- ✓ RAIL-05: Soporte polling/webhook — v1.2

Testing Infrastructure (TESTINF):
- ✓ TESTINF-01: pytest-asyncio con async_mode=auto — v1.2
- ✓ TESTINF-02: Fixtures creados — v1.2
- ✓ TESTINF-03: Base de datos en memoria — v1.2
- ✓ TESTINF-04: Aislamiento de tests — v1.2
- ✓ TESTINF-05: Coverage reporting — v1.2

System Tests (TESTSYS):
- ✓ TESTSYS-01: Test de arranque del sistema — v1.2
- ✓ TESTSYS-02: Tests de menú principal Admin — v1.2
- ✓ TESTSYS-03: Tests de menú VIP y Free — v1.2
- ✓ TESTSYS-04: Test de detección de roles — v1.2
- ✓ TESTSYS-05: Tests de flujos VIP/Free — v1.2
- ✓ TESTSYS-06: Tests de flujo de entrada al canal Free — v1.2
- ✓ TESTSYS-07: Tests de generación de tokens VIP — v1.2
- ✓ TESTSYS-08: Tests de flujo ritualizado de entrada VIP — v1.2
- ✓ TESTSYS-09: Tests de gestión de configuración — v1.2
- ✓ TESTSYS-10: Tests de proveedores de mensajes — v1.2

Admin Test Runner (ADMINTEST):
- ✓ ADMINTEST-01: Script /run_tests — v1.2
- ✓ ADMINTEST-02: Comando /run_tests en Telegram — v1.2
- ✓ ADMINTEST-03: Test runner con coverage — v1.2
- ✓ ADMINTEST-04: Reporte al admin via mensaje — v1.2

Performance (PERF):
- ✓ PERF-01: Integración con pyinstrument — v1.2
- ✓ PERF-02: Script para profiling de handlers — v1.2
- ✓ PERF-03: Detección de N+1 queries — v1.2
- ✓ PERF-04: Optimización de eager loading — v1.2

### Active

**v1.3 Planned Requirements:**

Redis Caching (CACHE):
- [ ] CACHE-01: Redis FSM state storage
- [ ] CACHE-02: CacheService para aplicación
- [ ] CACHE-03: Invalidación de caché en escrituras
- [ ] CACHE-04: Multi-layer caching
- [ ] CACHE-05: Graceful degradation cuando Redis no disponible

### Out of Scope

Caracteristicas explcitamente excluidas:

**v1.x (current):**
- **Internacionalizacion (i18n)** — Solo espanol por ahora; estructura puede prepararse pero sin implementacion
- **Sistema de gamificacion** — Servicio debe ser extensible pero no incluir mensajes de misiones/logros aun
- **Sistema de narrativa** — Servicio debe ser extensible pero no incluir contenido narrativo aun
- **Persistencia de variaciones** — No rastrear que variante se mostro a cada usuario (puede agregarse despues)
- **A/B testing** — No metricas de efectividad de diferentes variantes
- **Voice profiles alternos** — Solo voz de Lucien, sin variaciones de personalidad

**v1.2 (shipped) - Intentionally deferred to v1.3:**
- Railway deployment execution — Preparation only; actual deployment in v1.3+
- Monitoring dashboard — Requires stable system first
- Load testing — Requires production environment
- Automated backups — Railway feature to configure in v1.3+

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

### Metrics (v1.2)

- Total lines of code: ~177,811 Python
- Bot directory: ~24,328 lines of Python
- Message providers: 13 (Common, AdminMain, AdminVIP, AdminFree, UserStart, UserFlow, SessionHistory, UserMenu, AdminContent, AdminInterest, AdminUser, VIPEntryFlow)
- Services: 14 (incl. RoleDetection, Content, Interest, VIPEntry, UserManagement, RoleChange, TestRunner)
- Documentation: 5,777+ lines (4 main .md files + 1,070+ docstrings)
- Handlers organized: 23 files (admin/user split)
- Hardcoded strings eliminated: ~330 lines
- Memory overhead: ~80 bytes/user for session history
- Voice linter performance: 5.09ms average
- Test files: 13 (212 tests passing)
- Test coverage: pytest with asyncio_mode=auto, in-memory SQLite
- Health endpoint: FastAPI on port 8000
- Deployment: Railway-ready with Dockerfile and Railway.toml

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
| Dual-dialect database support | PostgreSQL for production, SQLite for development; automatic dialect detection from URL | ✓ Good |
| Fail-fast migration strategy | Bot does not start if migrations fail in production; prevents running with stale schema | ✓ Good |
| Separate health API | FastAPI health check independent from aiogram bot; allows monitoring even if bot has issues | ✓ Good |
| pytest-asyncio auto mode | No @pytest.mark.asyncio decorator needed; cleaner test code | ✓ Good |
| In-memory SQLite for tests | Fast test execution with proper isolation; no database cleanup needed | ✓ Good |
| Statistical profiling | pyinstrument provides low-overhead profiling suitable for production use | ✓ Good |
| N+1 query detection | SQLAlchemy event monitoring catches performance issues early | ✓ Good |

---

*Last updated: 2026-02-01 after v1.2 milestone completion*
