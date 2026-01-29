# Requirements: LucienVoiceService - v1.2 Primer Despliegue

**Defined:** 2026-01-28
**Core Value:** Consistencia absoluta en la voz de Lucien: cada mensaje del bot debe sonar elegante, misterioso y natural viniendo del mayordomo, sin importar que handler o flujo lo invoque.

## v1.2 Requirements

Requisitos para el hito de despliegue inicial. Cada requisito se mapea a una fase del roadmap.

### Database Migration (DBMIG)

- [ ] **DBMIG-01**: Sistema soporta PostgreSQL y SQLite con cambio vía variable de entorno
- [ ] **DBMIG-02**: Motor de base de datos detecta automáticamente el dialecto (postgresql+asyncpg vs sqlite+aiosqlite)
- [ ] **DBMIG-03**: Alembic está configurado con migración inicial
- [ ] **DBMIG-04**: Sistema ejecuta migraciones automáticamente al iniciar (producción)
- [ ] **DBMIG-05**: Script de migración de datos SQLite → PostgreSQL
- [ ] **DBMIG-06**: Validación de tipos en todos los modelos previo a migración
- [ ] **DBMIG-07**: Rolling back de migraciones soportado

### Health Monitoring (HEALTH)

- [ ] **HEALTH-01**: Endpoint HTTP /health retorna estado del bot
- [ ] **HEALTH-02**: Health check verifica conexión a base de datos
- [ ] **HEALTH-03**: Health check retorna 200 OK si todo está bien, 503 si hay errores
- [ ] **HEALTH-04**: Health check se ejecuta en puerto separado (FastAPI + uvicorn)
- [ ] **HEALTH-05**: Bot y API de salud corren concurrentemente

### Railway Preparation (RAIL)

- [ ] **RAIL-01**: Railway.toml configurado con comando de inicio y health check path
- [ ] **RAIL-02**: Dockerfile creado para despliegue en Railway
- [ ] **RAIL-03**: Variables de entorno requeridas documentadas
- [ ] **RAIL-04**: Validación de variables de entorno al inicio
- [ ] **RAIL-05**: Bot puede cambiar entre polling y webhook vía variable de entorno

### Testing Infrastructure (TESTINF)

- [ ] **TESTINF-01**: pytest-asyncio configurado con async_mode=auto
- [ ] **TESTINF-02**: Fixtures creados (test_db, mock_bot, container)
- [ ] **TESTINF-03**: Base de datos en memoria para tests (sqlite+aiosqlite:///:memory:)
- [ ] **TESTINF-04**: Aislamiento de tests (cleanup entre tests)
- [ ] **TESTINF-05**: Configuración de coverage reporting

### System Tests (TESTSYS)

- [ ] **TESTSYS-01**: Test de arranque del sistema (bot inicia, DB conecta, servicios cargan)
- [ ] **TESTSYS-02**: Test de handlers de menú principal Admin
- [ ] **TESTSYS-03**: Test de handlers de menú VIP
- [ ] **TESTSYS-04**: Test de handlers de menú Free
- [ ] **TESTSYS-05**: Test de detección de roles (Admin > VIP > Free)
- [ ] **TESTSYS-06**: Test de flujo de entrada al canal Free
- [ ] **TESTSYS-07**: Test de generación de tokens VIP
- [ ] **TESTSYS-08**: Test de flujo ritualizado de entrada VIP (3 etapas)
- [ ] **TESTSYS-09**: Test de gestión de configuración (BotConfig)
- [ ] **TESTSYS-10**: Test de proveedores de mensajes de Lucien (13 providers)

### Admin Test Runner (ADMINTEST)

- [ ] **ADMINTEST-01**: Script /run_tests ejecuta todos los tests
- [ ] **ADMINTEST-02**: Admin puede ejecutar tests desde Telegram con comando
- [ ] **ADMINTEST-03**: Test runner retorna resultado detallado (pass/fail, coverage)
- [ ] **ADMINTEST-04**: Test runner envía reporte al admin via mensaje

### Performance (PERF)

- [ ] **PERF-01**: Integración con pyinstrument para profiling
- [ ] **PERF-02**: Script para profiling de handlers específicos
- [ ] **PERF-03**: Detección de N+1 queries con logs de SQLAlchemy
- [ ] **PERF-04**: Optimización de eager loading (selectinload) donde sea necesario

## v1.3 Requirements

Diferidas a futuro:

### Redis Caching (CACHE)

- **CACHE-01**: Redis FSM state storage (aiogram RedisStorage)
- **CACHE-02**: CacheService para caching de aplicación
- **CACHE-03**: Invalidation de cache en operaciones de escritura
- **CACHE-04**: Multi-layer caching (BotConfig, roles, channels)
- **CACHE-05**: Graceful degradation cuando Redis no está disponible

## Out of Scope

Explícitamente excluidos de v1.2:

| Feature | Reason |
|---------|--------|
| Railway deployment execution | Preparación solo; deploy execution en v1.3+ |
| Redis caching layer | Requiere arquitectura adicional; diferido a v1.3 |
| Monitoring dashboard | Requiere sistema estable primero; v1.3+ |
| Load testing | Requiere producción estable; v1.3+ |
| Automated backups | Feature de Railway; config en v1.3+ |

## Traceability

Los requisitos se mapean a fases durante la creación del roadmap.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DBMIG-01 | Phase 14 | Pending |
| DBMIG-02 | Phase 14 | Pending |
| DBMIG-03 | Phase 14 | Pending |
| DBMIG-04 | Phase 14 | Pending |
| DBMIG-05 | Phase 18 | Pending |
| DBMIG-06 | Phase 14 | Pending |
| DBMIG-07 | Phase 14 | Pending |
| HEALTH-01 | Phase 15 | Pending |
| HEALTH-02 | Phase 15 | Pending |
| HEALTH-03 | Phase 15 | Pending |
| HEALTH-04 | Phase 15 | Pending |
| HEALTH-05 | Phase 15 | Pending |
| RAIL-01 | Phase 15 | Pending |
| RAIL-02 | Phase 15 | Pending |
| RAIL-03 | Phase 15 | Pending |
| RAIL-04 | Phase 15 | Pending |
| RAIL-05 | Phase 15 | Pending |
| TESTINF-01 | Phase 16 | Pending |
| TESTINF-02 | Phase 16 | Pending |
| TESTINF-03 | Phase 16 | Pending |
| TESTINF-04 | Phase 16 | Pending |
| TESTINF-05 | Phase 16 | Pending |
| TESTSYS-01 | Phase 17 | Pending |
| TESTSYS-02 | Phase 17 | Pending |
| TESTSYS-03 | Phase 17 | Pending |
| TESTSYS-04 | Phase 17 | Pending |
| TESTSYS-05 | Phase 17 | Pending |
| TESTSYS-06 | Phase 17 | Pending |
| TESTSYS-07 | Phase 17 | Pending |
| TESTSYS-08 | Phase 17 | Pending |
| TESTSYS-09 | Phase 17 | Pending |
| TESTSYS-10 | Phase 17 | Pending |
| ADMINTEST-01 | Phase 18 | Pending |
| ADMINTEST-02 | Phase 18 | Pending |
| ADMINTEST-03 | Phase 18 | Pending |
| ADMINTEST-04 | Phase 18 | Pending |
| PERF-01 | Phase 18 | Pending |
| PERF-02 | Phase 18 | Pending |
| PERF-03 | Phase 18 | Pending |
| PERF-04 | Phase 18 | Pending |

**Coverage:**
- v1.2 requirements: 37 total
- Mapped to phases: 37 (100%)
- Unmapped: 0 ✓

**Phase Distribution:**
- Phase 14: 6 requirements (DBMIG-01, DBMIG-02, DBMIG-03, DBMIG-04, DBMIG-06, DBMIG-07)
- Phase 15: 10 requirements (HEALTH-01 to HEALTH-05, RAIL-01 to RAIL-05)
- Phase 16: 5 requirements (TESTINF-01 to TESTINF-05)
- Phase 17: 10 requirements (TESTSYS-01 to TESTSYS-10)
- Phase 18: 6 requirements (ADMINTEST-01 to ADMINTEST-04, PERF-01 to PERF-04, DBMIG-05)

---
*Requirements defined: 2026-01-28*
*Last updated: 2026-01-28 after roadmap creation*
