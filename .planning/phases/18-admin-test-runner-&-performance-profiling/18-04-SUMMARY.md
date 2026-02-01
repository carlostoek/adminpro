---
phase: 18
plan: 04
name: SQLite to PostgreSQL Migration and N+1 Query Detection
subsystem: database
completed: 2026-01-30
duration: 8 minutes
tags: [database, migration, postgresql, sqlite, n-plus-one, query-analyzer, performance]
---

# Phase 18 Plan 04: SQLite to PostgreSQL Migration and N+1 Query Detection - Summary

## One-Liner
Created robust SQLite-to-PostgreSQL migration script with row validation and implemented N+1 query detection with SQLAlchemy event monitoring and eager loading utilities.

## What Was Delivered

### 1. Query Analyzer Utility (`bot/utils/query_analyzer.py`)
- **QueryInfo** and **NPlusOnePattern** dataclasses for query tracking
- **QueryAnalyzer** class with SQLAlchemy event listeners
- **analyze_queries()** context manager for convenient usage
- **QueryOptimizationSuggestions** helper with actionable optimization tips
- **detect_n_plus_one_in_service** decorator for automatic service method monitoring
- **get_eager_load_options()** utility for generating selectinload options
- Slow query detection (>100ms) with immediate warning logs
- N+1 pattern detection with configurable threshold (5+ similar queries)

### 2. Services Eager Loading Updates
**`bot/services/subscription.py`:**
- Added `selectinload` import from SQLAlchemy ORM
- Added `get_vip_subscriber_with_relations()` method with eager loading for user, token, and plan
- Added `get_all_vip_subscribers_with_users()` method for bulk operations with user data

**`bot/services/channel.py`:**
- Added `selectinload` import from SQLAlchemy ORM
- Added `get_bot_config_with_channels()` method for optimized config access

### 3. Migration Script (`scripts/migrate_to_postgres.py`)
- **DatabaseMigrator** class with ordered `MIGRATION_ORDER` respecting FK dependencies
- `migrate_table()` method with batch insert support (100 rows per batch)
- `validate_migration()` with row count verification for all tables
- **MigrationReport** dataclass with JSON and text output formats
- CLI with `--source`, `--target`, `--dry-run`, `--validate-only`, `--output` options
- Comprehensive error handling and detailed logging
- Support for SQLite URL auto-conversion (aiosqlite -> sync driver)

### 4. Query Logging Configuration (`bot/database/engine.py`)
- Added `create_async_engine_with_logging()` factory function
- Added `debug_mode` parameter to `init_db()`, `_create_postgresql_engine()`, `_create_sqlite_engine()`
- Configures `sqlalchemy.engine` logger for SQL query output when debug_mode=True
- Updated engine creation to support runtime query logging toggle

### 5. Admin Query Analysis Command (`bot/handlers/admin/profile.py`)
- Added `/analyzeQueries` command for Telegram admin interface
- Runs test operations with `QueryAnalyzer` context manager
- Reports N+1 issues and slow queries (>100ms)
- Provides optimization suggestions with code examples
- Supports file output for detailed reports when message exceeds 4000 chars

## Files Modified/Created

| File | Lines | Type |
|------|-------|------|
| `bot/utils/query_analyzer.py` | 418 | Created |
| `bot/services/subscription.py` | +85 | Modified |
| `bot/services/channel.py` | +30 | Modified |
| `scripts/migrate_to_postgres.py` | 445 | Created |
| `bot/database/engine.py` | +67/-9 | Modified |
| `bot/handlers/admin/profile.py` | +143 | Modified |

## Technical Highlights

### N+1 Detection Algorithm
```python
def _detect_n_plus_one_patterns(self) -> List[NPlusOnePattern]:
    # Agrupar queries por tabla
    query_groups = defaultdict(list)
    for query in self.queries:
        table = extract_table_from_query(query.statement)
        query_groups[table].append(query)

    # Detectar patrones: 1 query base + N queries similares
    for table, queries in query_groups.items():
        if len(queries) >= N_PLUS_ONE_THRESHOLD:
            patterns.append(NPlusOnePattern(...))
```

### Eager Loading Pattern
```python
# Before (N+1 problem)
subscribers = await service.get_all_vip_subscribers()
for sub in subscribers:
    print(sub.user.full_name)  # Query N+1

# After (single query)
subscribers = await service.get_all_vip_subscribers_with_users()
for sub in subscribers:
    print(sub.user.full_name)  # No additional query
```

### Migration Validation
```python
async def validate_migration(self) -> bool:
    for table_name in self.MIGRATION_ORDER:
        source_count = await self._count_source_rows(table_name)
        target_count = await self._count_target_rows(table_name)
        if source_count != target_count:
            logger.error(f"Count mismatch in {table_name}")
            return False
    return True
```

## Anti-Patterns Addressed

1. ✅ **Don't migrate without validation** - Migration script validates row counts match
2. ✅ **Don't use lazy loading in loops** - Added eager loading methods with selectinload
3. ✅ **Don't ignore slow query logs** - Immediate warning for queries >100ms
4. ✅ **Don't migrate to production directly** - Dry-run and validate-only modes
5. ✅ **Don't keep query analysis on in production** - Debug mode is opt-in

## Testing

- All Python files pass `py_compile` syntax validation
- Imports verified: `query_analyzer`, `engine` modules load successfully
- Migration script is executable (`chmod +x` applied)

## API/Interface Changes

### New Commands
- `/analyzeQueries` - Admin command to detect N+1 and slow queries

### New CLI
```bash
python scripts/migrate_to_postgres.py \
    --source sqlite:///bot.db \
    --target postgresql+asyncpg://user:pass@host/db \
    [--dry-run] \
    [--validate-only] \
    [--output report.json]
```

### New Service Methods
- `SubscriptionService.get_vip_subscriber_with_relations(user_id, load_user, load_token)`
- `SubscriptionService.get_all_vip_subscribers_with_users(status, limit, offset, load_tokens)`
- `ChannelService.get_bot_config_with_channels()`

## Decisions Made

1. **N+1 Threshold**: Set at 5 similar queries (configurable via class constant)
2. **Slow Query Threshold**: 100ms (configurable via `SLOW_QUERY_THRESHOLD`)
3. **Migration Batch Size**: 100 rows per INSERT batch for memory efficiency
4. **Debug Mode**: Opt-in via parameter (not environment variable) for flexibility
5. **Eager Loading**: Explicit methods rather than changing default behavior (backward compatible)

## Next Phase Readiness

This plan completes Phase 18 (Admin Test Runner & Performance Profiling). All performance tooling is now in place:

- Test runner with CLI and Telegram commands (18-01)
- Test reporting with coverage and trends (18-02)
- Performance profiling with pyinstrument (18-03)
- N+1 query detection and migration tools (18-04)

The project now has comprehensive testing and performance monitoring infrastructure ready for production deployment and ongoing maintenance.

## Commits

| Hash | Message |
|------|---------|
| 235d848 | feat(18-04): create query analyzer utility with N+1 detection |
| f53f2a6 | feat(18-04): add eager loading methods to services |
| c1707b4 | feat(18-04): create SQLite to PostgreSQL migration script |
| 14c8f28 | feat(18-04): add query logging configuration to database engine |
| b266c99 | feat(18-04): add admin query analysis command |
