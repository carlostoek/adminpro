# Phase 18: Admin Test Runner & Performance Profiling

**Goal:** Centralized test execution and performance bottleneck detection

**Status:** 🔄 Planning Complete

**Plans:** 4 plans

**Dependencies:** Phase 17 (System Tests)

---

## Overview

Phase 18 implements a comprehensive test runner system that allows administrators to execute tests both from the command line and directly from Telegram. It also integrates performance profiling tools to identify bottlenecks in handlers and database queries.

**Key Features:**
- CLI script `/run_tests` for local test execution
- Telegram command `/run_tests` for remote test execution
- Detailed test reports with pass/fail status and coverage metrics
- Performance profiling with pyinstrument integration
- N+1 query detection via SQLAlchemy logging
- SQLite to PostgreSQL data migration script

---

## Plans

| Plan | Wave | Focus | Files Created |
|------|------|-------|---------------|
| 18-01 | 1 | Admin test runner script and Telegram command | `scripts/run_tests.py`, `bot/handlers/admin/tests.py` |
| 18-02 | 2 | Test reporting with coverage and detailed results | `bot/services/test_runner.py`, `bot/utils/test_report.py` |
| 18-03 | 2 | Performance profiling with pyinstrument integration | `scripts/profile_handler.py`, `bot/handlers/admin/profile.py` |
| 18-04 | 3 | SQLite to PostgreSQL migration and N+1 detection | `scripts/migrate_to_postgres.py`, `bot/utils/query_analyzer.py` |

---

## Success Criteria

1. Script `/run_tests` ejecuta todos los tests desde linea comandos
2. Admin puede ejecutar tests desde Telegram con comando `/run_tests`
3. Test runner envia reporte detallado (pass/fail, coverage) al admin via mensaje
4. Integracion con pyinstrument permite profiling de handlers especificos
5. Script de migracion de datos SQLite → PostgreSQL funciona sin perdida de datos

---

## Requirements Coverage

| Requirement | Status | Plan |
|-------------|--------|------|
| ADMINTEST-01: Script /run_tests ejecuta todos los tests | 🔄 18-01 | `scripts/run_tests.py` |
| ADMINTEST-02: Admin puede ejecutar tests desde Telegram | 🔄 18-01 | `bot/handlers/admin/tests.py` |
| ADMINTEST-03: Test runner retorna resultado detallado | 🔄 18-02 | `bot/services/test_runner.py` |
| ADMINTEST-04: Test runner envia reporte al admin via mensaje | 🔄 18-02 | `bot/utils/test_report.py` |
| PERF-01: Integracion con pyinstrument para profiling | 🔄 18-03 | `scripts/profile_handler.py` |
| PERF-02: Script para profiling de handlers especificos | 🔄 18-03 | `bot/handlers/admin/profile.py` |
| PERF-03: Deteccion de N+1 queries con logs de SQLAlchemy | 🔄 18-04 | `bot/utils/query_analyzer.py` |
| PERF-04: Optimizacion de eager loading (selectinload) | 🔄 18-04 | Analysis + fixes |
| DBMIG-05: Script de migracion SQLite → PostgreSQL | 🔄 18-04 | `scripts/migrate_to_postgres.py` |

---

## Architecture

```
+------------------+     +------------------+     +------------------+
|   CLI Interface  |     | Telegram Command |     |  Admin Handler   |
|  scripts/run_    |     |   /run_tests     |     |  admin/tests.py  |
|    tests.py      |     |                  |     |                  |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         v                        v                        v
+--------+-----------------------------------------------+---------+
|                    Test Runner Service                            |
|              bot/services/test_runner.py                          |
+--------+----------------------------------------------------------+
         |
         +------------------+------------------+
         |                  |                  |
         v                  v                  v
+------------------+ +----------------+ +----------------+
|  pytest runner   | | Coverage tool  | | Report builder |
|  (subprocess)    | | (pytest-cov)   | | (HTML/text)    |
+------------------+ +----------------+ +----------------+
```

---

## Key Technical Decisions

1. **Subprocess isolation**: Tests run in subprocess to avoid affecting running bot
2. **Async-safe profiling**: pyinstrument wrapped for async handler compatibility
3. **Query logging**: SQLAlchemy events used for N+1 detection without code changes
4. **Streaming reports**: Large reports split into multiple Telegram messages
5. **Migration validation**: Checksum verification for data integrity

---

## Verification Commands

```bash
# Run all tests via CLI
python scripts/run_tests.py

# Run with coverage
python scripts/run_tests.py --coverage

# Run specific test file
python scripts/run_tests.py tests/test_system/test_startup.py

# Profile a handler
python scripts/profile_handler.py bot.handlers.admin.main.cmd_admin

# Run migration
python scripts/migrate_to_postgres.py --source bot.db --target postgresql://...
```

---

## Security Considerations

1. **Admin-only access**: Telegram /run_tests restricted to Config.is_admin()
2. **Subprocess sandbox**: Test runner uses limited environment variables
3. **No sensitive data in reports**: Database URLs and tokens redacted
4. **Rate limiting**: Test execution throttled to prevent abuse

---

## Next Steps

After Phase 18 completion:
1. Deploy to production with full test coverage
2. Schedule automated test runs via background tasks
3. Set up performance regression monitoring
4. Document troubleshooting procedures

---

**Phase Leader:** Claude (gsd-planner)
**Last Updated:** 2026-01-30
**Status:** ✅ Planning Complete
