# Roadmap: LucienVoiceService - Telegram Bot VIP/Free

## Overview

Transformación desde un bot Telegram local con SQLite hacia una solución production-ready en Railway con PostgreSQL, testing comprehensivo y profiling de performance. El viaje establece infraestructura de despliegue (v1.2), cimiento para caching avanzado (v1.3), y optimización continua.

## Milestones

- ✅ **v1.0 LucienVoiceService** - Phases 1-4 (shipped 2026-01-24)
- ✅ **v1.1 Sistema de Menús** - Phases 5-13 (shipped 2026-01-28)
- 🚧 **v1.2 Primer Despliegue** - Phases 14-18 (in progress)

## Phases

<details>
<summary>✅ v1.0 LucienVoiceService (Phases 1-4) - SHIPPED 2026-01-24</summary>

### Phase 1: Service Foundation & Voice Rules
**Goal**: Centralized message system with Lucien's voice
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — BaseMessageProvider and LucienVoiceService foundation
- [x] 01-02-PLAN.md — Voice consistency rules and variation system
- [x] 01-03-PLAN.md — Common and Admin message providers

### Phase 2: Template Organization & Admin Migration
**Goal**: Variable interpolation and admin handler migration
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md — Template composition and keyboard integration
- [x] 02-02-PLAN.md — Admin main menu migration
- [x] 02-03-PLAN.md — Admin VIP and Free menu migration

### Phase 3: User Flow Migration & Testing Strategy
**Goal**: User handler migration and semantic test helpers
**Plans**: 4 plans

Plans:
- [x] 03-01-PLAN.md — User start and VIP flow migration
- [x] 03-02-PLAN.md — Free flow migration
- [x] 03-03-PLAN.md — Session-aware variation system
- [x] 03-04-PLAN.md — Semantic test helpers

### Phase 4: Advanced Voice Features
**Goal**: Voice validation and message preview tools
**Plans**: 4 plans

Plans:
- [x] 04-01-PLAN.md — Voice validation pre-commit hook
- [x] 04-02-PLAN.md — Message preview CLI tool
- [x] 04-03-PLAN.md — Dynamic content features (conditionals, lists)
- [x] 04-04-PLAN.md — E2E tests and completion

</details>

<details>
<summary>✅ v1.1 Sistema de Menús (Phases 5-13) - SHIPPED 2026-01-28</summary>

Role-based menu system (Admin/VIP/Free) with automatic role detection, content package management, interest notifications, user management, social media integration, VIP ritualized entry flow, and comprehensive documentation.

**9 phases, 48 plans, 57 requirements satisfied (100%)**

**Key features:**
- RoleDetectionService (Admin > VIP > Free priority)
- ContentService CRUD for content packages
- InterestService with 5-minute deduplication
- UserManagementService with audit logging
- Free channel entry flow with social media keyboard
- VIP 3-stage ritualized entry (confirmation → alignment → access)
- Package detail view redesign
- 5,777 lines of documentation

**[Full phases 5-13 archived in previous roadmap]**

</details>

### 🚧 v1.2 Primer Despliegue (In Progress)

**Milestone Goal:** Deploy bot to Railway with PostgreSQL migration, comprehensive test coverage, and performance profiling infrastructure. Redis caching DEFERRED to v1.3.

#### Phase 14: Database Migration Foundation
**Goal**: PostgreSQL-ready database layer with automatic dialect detection and Alembic migrations
**Depends on**: Phase 13 (v1.1 complete)
**Requirements**: DBMIG-01, DBMIG-02, DBMIG-03, DBMIG-04, DBMIG-06, DBMIG-07
**Success Criteria** (what must be TRUE):
  1. Sistema soporta SQLite y PostgreSQL mediante variable de entorno DATABASE_URL
  2. Motor de base de datos detecta automáticamente dialecto (postgresql+asyncpg vs sqlite+aiosqlite)
  3. Alembic está configurado con migración inicial que crea todos los modelos
  4. Sistema ejecuta `alembic upgrade head` automáticamente al iniciar en producción
  5. Rolling back de migraciones funciona con `alembic downgrade`
**Plans**: 4 plans

Plans:
- [x] 14-01: Database abstraction layer with dialect detection
- [x] 14-02a: Alembic configuration
- [x] 14-02b: Initial migration generation
- [x] 14-03: Auto-migration on startup and rollback support

#### Phase 15: Health Check & Railway Preparation
**Goal**: Health monitoring endpoint and Railway deployment configuration
**Depends on**: Phase 14
**Requirements**: HEALTH-01, HEALTH-02, HEALTH-03, HEALTH-04, HEALTH-05, RAIL-01, RAIL-02, RAIL-03, RAIL-04, RAIL-05
**Success Criteria** (what must be TRUE):
  1. Endpoint HTTP /health retorna 200 OK cuando bot y base de datos están funcionando
  2. Health check retorna 503 Service Unavailable cuando hay errores en DB
  3. Bot y API de salud corren concurrentemente (FastAPI en puerto separado)
  4. Railway.toml configurado con comando de inicio y health check path
  5. Dockerfile creado para despliegue en Railway con variables de entorno validadas
  6. Bot responde a Ctrl+C y se detiene limpiamente sin procesos huérfanos
**Plans**: 5 plans

Plans:
- [x] 15-01: FastAPI health check endpoint with DB status
- [x] 15-02: Concurrent bot and health API execution
- [x] 15-03: Railway.toml and Dockerfile configuration
- [x] 15-04: Environment variable validation and webhook/polling mode switching
- [x] 15-05: Graceful shutdown fix - Bot responds to Ctrl+C (gap closure)

#### Phase 16: Testing Infrastructure
**Goal**: pytest-asyncio setup with fixtures and in-memory database
**Depends on**: Phase 15
**Requirements**: TESTINF-01, TESTINF-02, TESTINF-03, TESTINF-04, TESTINF-05
**Success Criteria** (what must be TRUE):
  1. pytest-asyncio configurado con async_mode=auto
  2. Fixtures creados (test_db, mock_bot, container) para todos los tests
  3. Base de datos en memoria se crea y limpia automáticamente entre tests
  4. Tests están aislados (cleanup completo entre tests)
  5. Coverage reporting configurado para medir cobertura de código
**Plans**: 5 plans

Plans:
- [x] 16-01: pytest-asyncio configuration with async_mode=auto
- [x] 16-02: Core test fixtures (test_db, mock_bot, container)
- [x] 16-03: In-memory database setup with automatic cleanup
- [x] 16-04: Test isolation with transaction rollback
- [x] 16-05: Coverage reporting configuration

#### Phase 17: System Tests
**Goal**: Comprehensive test coverage for critical flows and message providers
**Depends on**: Phase 16
**Requirements**: TESTSYS-01, TESTSYS-02, TESTSYS-03, TESTSYS-04, TESTSYS-05, TESTSYS-06, TESTSYS-07, TESTSYS-08, TESTSYS-09, TESTSYS-10
**Success Criteria** (what must be TRUE):
  1. Test de arranque verifica que bot inicia, DB conecta, y servicios cargan
  2. Tests de menú principal Admin cubren todos los comandos y callbacks
  3. Tests de menú VIP y Free verifican navegación y rol routing
  4. Test de detección de roles valida prioridad Admin > VIP > Free
  5. Tests de flujos VIP/Free verifican tokens, entrada ritual, y aprobación Free
**Plans**: 4 plans

Plans:
- [x] 17-01: System startup and configuration tests
- [x] 17-02: Menu system tests (Admin/VIP/Free with FSM)
- [x] 17-03: Role detection and user management tests
- [x] 17-04: VIP/Free flow tests and message provider tests

**Status:** Complete — 212 tests created, all passing

#### Phase 18: Admin Test Runner & Performance Profiling
**Goal**: Centralized test execution and performance bottleneck detection
**Depends on**: Phase 17
**Requirements**: ADMINTEST-01, ADMINTEST-02, ADMINTEST-03, ADMINTEST-04, PERF-01, PERF-02, PERF-03, PERF-04, DBMIG-05
**Success Criteria** (what must be TRUE):
  1. Script /run_tests ejecuta todos los tests desde línea comandos
  2. Admin puede ejecutar tests desde Telegram con comando /run_tests
  3. Test runner envía reporte detallado (pass/fail, coverage) al admin via mensaje
  4. Integración con pyinstrument permite profiling de handlers específicos
  5. Script de migración de datos SQLite → PostgreSQL funciona sin pérdida de datos
**Plans**: 4 plans

Plans:
- [ ] 18-01: Admin test runner script and Telegram command
- [ ] 18-02: Test reporting with coverage and detailed results
- [ ] 18-03: Performance profiling with pyinstrument integration
- [ ] 18-04: SQLite → PostgreSQL data migration script and N+1 query detection

### 📋 v1.3 Redis Caching (Planned)

**Milestone Goal:** Add Redis caching layer for FSM state persistence and application-level caching (BotConfig, roles, channels).

*Note: Redis requirements (CACHE-01 through CACHE-05) are DEFERRED to v1.3.*

## Progress

**Execution Order:**
Phases execute in numeric order: 14 → 15 → 16 → 17 → 18

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Service Foundation & Voice Rules | v1.0 | 3/3 | Complete | 2026-01-23 |
| 2. Template Organization & Admin Migration | v1.0 | 3/3 | Complete | 2026-01-23 |
| 3. User Flow Migration & Testing Strategy | v1.0 | 4/4 | Complete | 2026-01-24 |
| 4. Advanced Voice Features | v1.0 | 4/4 | Complete | 2026-01-24 |
| 5. Role Detection & Database Foundation | v1.1 | 6/6 | Complete | 2026-01-25 |
| 6. VIP/Free User Menus | v1.1 | 4/4 | Complete | 2026-01-25 |
| 7. Admin Menu with Content Management | v1.1 | 4/4 | Complete | 2026-01-26 |
| 8. Interest Notification System | v1.1 | 4/4 | Complete | 2026-01-26 |
| 9. User Management Features | v1.1 | 6/6 | Complete | 2026-01-26 |
| 10. Free Channel Entry Flow | v1.1 | 5/5 | Complete | 2026-01-27 |
| 11. Documentation | v1.1 | 4/4 | Complete | 2026-01-28 |
| 12. Rediseño de Menú de Paquetes | v1.1 | 4/4 | Complete | 2026-01-27 |
| 13. VIP Ritualized Entry Flow | v1.1 | 4/4 | Complete | 2026-01-27 |
| 14. Database Migration Foundation | v1.2 | 4/4 | Complete | 2026-01-29 |
| 15. Health Check & Railway Preparation | v1.2 | 5/5 | Complete | 2026-01-29 |
| 16. Testing Infrastructure | v1.2 | 5/5 | Complete | 2026-01-29 |
| 17. System Tests | v1.2 | 4/4 | Complete | 2026-01-30 |
| 18. Admin Test Runner & Performance Profiling | v1.2 | 0/4 | Not started | - |

**Overall Progress:** 67/68 plans complete (99%)
