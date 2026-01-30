# Database Migration Rollback Guide

This guide explains how to rollback database migrations if something goes wrong.

---

## When to Rollback

Rollback is necessary when:
- A migration causes application errors
- Data is corrupted by a migration
- Performance degrades after a migration
- Schema changes need to be reverted

---

## Rollback Methods

### Method 1: Command Line (Recommended)

#### Rollback Last Migration

Revert the most recently applied migration:

```bash
alembic downgrade -1
```

#### Rollback Multiple Migrations

Revert the last N migrations:

```bash
# Revert last 2 migrations
alembic downgrade -2

# Revert last 3 migrations
alembic downgrade -3
```

#### Rollback to Specific Revision

Revert to a specific migration revision:

```bash
alembic downgrade <revision_id>
```

Example:
```bash
alembic downgrade 20250128_140000
```

#### Rollback to Base

Reset database to empty schema (WARNING: drops all tables):

```bash
alembic downgrade base
```

**DANGER:** This will delete all data. Use only for testing.

---

### Method 2: Python Script

Use the migration runner module programmatically:

```python
import asyncio
from bot.database.migrations import rollback_last_migration, rollback_to_base

# Rollback last migration
async def main():
    success = await rollback_last_migration()
    if success:
        print("Rollback successful")
    else:
        print("Rollback failed")

asyncio.run(main())
```

---

### Method 3: Production Rollback

In production, follow these steps:

#### Step 1: Stop the Bot

```bash
# On Railway
railway down

# Or kill the process
pkill -f "python main.py"
```

#### Step 2: Rollback Migration

```bash
# Set DATABASE_URL from Railway dashboard
export DATABASE_URL="postgresql://..."

# Rollback last migration
alembic downgrade -1
```

#### Step 3: Verify Schema

```bash
# Check current revision
alembic current

# View migration history
alembic history
```

#### Step 4: Restart the Bot

```bash
# On Railway
railway up

# Or restart the process
python main.py
```

---

## Migration States

### View Current Revision

```bash
alembic current
```

Output:
```
Current revision(s):
<revision_id> -> <migration_description> (head)
```

### View Migration History

```bash
alembic history
```

---

## Common Scenarios

### Scenario 1: Migration Fails in Production

**Problem:** Bot fails to start because migration failed.

**Solution:**
1. Check error logs for migration failure details
2. Fix the issue in the migration script
3. Rollback the failed migration: `alembic downgrade -1`
4. Update the migration script with the fix
5. Re-apply migration: `alembic upgrade head`

### Scenario 2: Data Loss After Migration

**Problem:** Migration accidentally deleted data.

**Solution:**
1. **STOP:** Do not apply any more migrations
2. Restore from database backup (if available)
3. If no backup, rollback the migration: `alembic downgrade -1`
4. Manually recover data from logs or other sources
5. Create a new migration that properly handles data

### Scenario 3: Performance Degradation

**Problem:** New indexes or schema changes slow down queries.

**Solution:**
1. Identify the problematic migration: `alembic history`
2. Rollback that migration: `alembic downgrade <revision_id>`
3. Analyze performance impact
4. Create optimized migration
5. Test in development first
6. Apply to production

---

## Data Safety Tips

### Always Backup Before Migration

```bash
# SQLite
cp bot.db bot.db.backup

# PostgreSQL
pg_dump $DATABASE_URL > backup.sql
```

### Test Migrations Locally First

```bash
# Test migration with SQLite
DATABASE_URL=sqlite:///test.db alembic upgrade head

# Test migration with PostgreSQL (if available)
DATABASE_URL=postgresql://localhost/test alembic upgrade head
```

### Review Generated Migrations

Autogenerate is not perfect. Always review:

```bash
alembic revision --autogenerate -m "Describe changes"
# Edit the generated file to check for errors
alembic upgrade head
```

---

## Rollback Best Practices

1. **Test downgrades:** Ensure `downgrade()` function works before deploying migration
2. **Document breaking changes:** Note which migrations cannot be safely rolled back
3. **Use transactions:** Alembic runs migrations in transactions by default
4. **Monitor after rollback:** Check application logs for errors after rollback
5. **Have a rollback plan:** Before deploying, know which migration to rollback to if needed

---

## Getting Help

If you encounter issues not covered here:

1. Check Alembic documentation: https://alembic.sqlalchemy.org/
2. Check application logs for detailed error messages
3. Ask for help in project issues/discussions
