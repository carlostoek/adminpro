# Phase 14: Database Migration Foundation - Context

**Gathered:** 2026-01-28
**Status:** Ready for planning

## Phase Boundary

PostgreSQL-ready database layer with automatic dialect detection (SQLite/PostgreSQL via DATABASE_URL), Alembic migrations, and auto-migration on startup for production deployment.

## Implementation Decisions

### Migration behavior
- **Verbose logging:** Log all migration activity — start, each migration applied, warnings, errors. Useful for debugging production issues.
- **Failure handling:** Fail fast with detailed error logs. Do not start the bot if migrations fail. Admin must fix schema manually before restart.
- **Retry logic:** No retry. Migration errors are schema problems, not transient network issues.
- **Startup timing:** Run migrations as early as possible before other services initialize (Claude's discretion — can be adjusted based on actual startup flow).

### Dev workflow
- **Migration naming:** Timestamp prefix with description — `YYYYMMDD_HHMMSS_description.py` (Alembic default). Example: `20250128_143000_add_user_table.py`
- **Migration message:** Required. Developer must provide a descriptive message when creating migrations (commit-style note).
- **Validation approach:** Mixed approach
  - **Local (Termux):** Run `alembic upgrade head` with SQLite before committing
  - **CI (GitHub):** Automatic test with PostgreSQL on PR
  - No extra dependencies needed in Termux
- **Migration creation:** Start with `alembic revision --autogenerate`, then review/edit the generated file to catch anything missed (Claude's discretion).

### Claude's Discretion
- **Startup timing:** When exactly to run migrations during bot initialization (before/after other services)
- **Migration creation method:** autogenerate vs manual vs hybrid — defaulted to autogenerate + review but flexible

## Specific Ideas

- "I want verbose logging so we can debug production migration issues"
- "Termux is limited — CI should handle PostgreSQL testing, local only needs SQLite validation"
- "Migrations should fail fast — if the schema is wrong, don't start the bot"

## Deferred Ideas

None — discussion stayed within phase scope.

---

*Phase: 14-database-migration-foundation*
*Context gathered: 2026-01-28*
