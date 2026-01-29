# Phase 14: Database Migration Foundation - Planning Summary

**Phase:** 14
**Title:** Database Migration Foundation
**Status:** Ready for Execution
**Plans:** 4 (14-01, 14-02a, 14-02b, 14-03)

---

## Overview

Phase 14 implements PostgreSQL support, Alembic migrations, and automatic migration execution on production startup. This enables deployment to Railway.app while maintaining SQLite support for local development.

---

## Plans Summary

### Plan 14-01: Database Abstraction Layer with Dialect Detection
**Wave:** 1 | **Dependencies:** Phase 13

Creates a database abstraction layer that automatically detects the database dialect from `DATABASE_URL` and configures appropriate drivers and connection pooling.

**Key Deliverables:**
- `bot/database/dialect.py` - URL parser and dialect detector
- Updated `bot/database/engine.py` - Dual SQLite/PostgreSQL support
- Updated `requirements.txt` - Add `asyncpg==0.29.0`
- Updated `.env.example` - PostgreSQL URL examples
- Updated `config.py` - DATABASE_URL validation

**Success Criteria:**
- ✅ System supports both SQLite and PostgreSQL via `DATABASE_URL`
- ✅ Engine auto-detects dialect from URL scheme
- ✅ Appropriate pooling per dialect (QueuePool for PostgreSQL, NullPool for SQLite)
- ✅ SQLite optimizations (WAL mode, cache, PRAGMAs) only applied to SQLite
- ✅ Error handling for invalid URLs (DBMIG-02)
- ✅ Type validation before engine initialization (DBMIG-06)

---

### Plan 14-02a: Alembic Configuration
**Wave:** 2 | **Dependencies:** 14-01

Configures Alembic for database migrations. This plan sets up the Alembic infrastructure including configuration file, environment setup, and migration template.

**Key Deliverables:**
- `alembic.ini` - Alembic configuration with timestamp-based naming
- `alembic/env.py` - Async migration environment with `DATABASE_URL` support and dialect detection
- `alembic/script.py.mako` - Migration file template
- Updated `requirements.txt` - Add `alembic==1.13.1`

**Success Criteria:**
- ✅ Alembic configured with `sqlalchemy.url` in `alembic.ini`
- ✅ `env.py` detects `DATABASE_URL` from environment
- ✅ `env.py` imports all models for autogenerate
- ✅ Dialect detection in env.py for type validation (DBMIG-06)

---

### Plan 14-02b: Initial Migration Generation
**Wave:** 2 | **Dependencies:** 14-02a

Generates the initial Alembic migration that captures all existing models and creates helper tooling for manual migration operations.

**Key Deliverables:**
- `alembic/versions/20250128_140000_initial_schema.py` - Initial migration with all 9 tables
- Updated `.gitignore` - Alembic version control configuration
- `scripts/migrate.py` - Convenience script for manual migration operations

**Success Criteria:**
- ✅ Initial migration file generated with all 9 tables
- ✅ Migration creates all tables with correct schema
- ✅ Migration downgrade drops all tables in reverse order
- ✅ Helper script exists for manual operations

---

### Plan 14-03: Auto-Migration on Startup and Rollback Support
**Wave:** 3 | **Dependencies:** 14-02b

Implements automatic migration execution on production startup and documents rollback procedures.

**Key Deliverables:**
- `bot/database/migrations.py` - Migration runner module
- Updated `main.py` - Integrate auto-migration into startup
- Updated `config.py` - Add `ENV` environment variable
- Updated `.env.example` - Add `ENV=production` example
- `docs/ROLLBACK.md` - Comprehensive rollback documentation
- Updated `README.md` - Migration documentation for developers

**Success Criteria:**
- ✅ Bot detects production mode via `ENV=production` (DBMIG-04)
- ✅ In production, auto-runs `alembic upgrade head` on startup (DBMIG-04)
- ✅ Logs all migration activity (verbose logging)
- ✅ Migration failures fail-fast (bot does not start) (DBMIG-04)
- ✅ Rollback procedure documented (DBMIG-07)

---

## Wave Execution Strategy

### Wave 1 (14-01)
**Parallelization:** Can execute tasks independently
- Task 1: Update requirements.txt with asyncpg
- Task 2: Create dialect.py (blocks Task 3)
- Task 3: Refactor engine.py (depends on Task 2)
- Task 4: Update .env.example with PostgreSQL URLs
- Task 5: Add Config validation for DATABASE_URL (REQUIRED)

**Estimated Time:** 30-45 minutes

### Wave 2 (14-02a, 14-02b)
**14-02a: Alembic Configuration (4 tasks)**
- Task 1: Install Alembic in requirements.txt
- Task 2: Initialize alembic.ini configuration
- Task 3: Create env.py with async support and dialect detection
- Task 4: Create script.py.mako template

**14-02b: Initial Migration (3 tasks)**
- Task 1: Generate initial migration with all 9 tables
- Task 2: Update .gitignore for Alembic
- Task 3: Create migrate.py helper script

**Estimated Time:** 45-60 minutes (both plans)

### Wave 3 (14-03)
**7 tasks, sequential execution**
- Task 1: Create migrations.py module with production mode detection
- Task 2: Integrate migration runner into main.py startup
- Task 3: Add ENV variable to config.py
- Task 4: Update .env.example with ENV variable
- Task 5: Create comprehensive rollback documentation
- Task 6: Update README.md with migration documentation
- Task 7: Verify logging levels for migration monitoring

**Estimated Time:** 60-75 minutes

**Total Estimated Time:** 2.5-3 hours

---

## Testing Strategy

### Local Testing (Termux - SQLite)
```bash
# After each wave, test with SQLite
DATABASE_URL=sqlite+aiosqlite:///test.db python main.py

# Verify dialect detection
python -c "from bot.database.dialect import parse_database_url; print(parse_database_url('sqlite:///test.db'))"

# Test migrations
alembic upgrade head
alembic current
alembic downgrade -1
```

### Production Testing (Railway - PostgreSQL)
```bash
# Set production environment
export ENV=production
export DATABASE_URL="postgresql://user:pass@host:5432/db"

# Test auto-migration
python main.py

# Verify migrations applied
alembic current
```

### CI/CD Testing (GitHub Actions)
Future enhancement: Add PostgreSQL test matrix to CI workflow

---

## Risk Mitigation

### Risk 1: Migration Failure in Production
**Mitigation:** Fail-fast strategy — bot exits if migrations fail, preventing startup with incompatible schema.

### Risk 2: Data Loss During Rollback
**Mitigation:** Document rollback procedures clearly, recommend backups before migration, test downgrades locally.

### Risk 3: SQLite vs PostgreSQL Incompatibilities
**Mitigation:** Use SQLAlchemy dialect-specific types (JSON, Enum), test migrations on both databases.

### Risk 4: Termux Package Limitations
**Mitigation:** Keep PostgreSQL testing optional for local dev, rely on CI for PostgreSQL validation.

---

## Rollback Plan

If Phase 14 needs to be rolled back:

1. **Revert code changes:**
   ```bash
   git revert <commit-range>
   ```

2. **Uninstall Alembic:**
   ```bash
   pip uninstall alembic asyncpg
   ```

3. **Restore pre-migration database:**
   ```bash
   # SQLite
   cp bot.db.backup bot.db

   # PostgreSQL
   psql $DATABASE_URL < backup.sql
   ```

---

## Next Phase

**Phase 15:** To be determined (likely deployment preparation or testing infrastructure)

---

## Contact

For questions about Phase 14 planning, refer to:
- `14-CONTEXT.md` - Context and decisions made
- `14-01-PLAN.md` - Database abstraction layer details
- `14-02a-PLAN.md` - Alembic configuration details
- `14-02b-PLAN.md` - Initial migration generation details
- `14-03-PLAN.md` - Auto-migration and rollback details
