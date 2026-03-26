---
phase: 14-database-migration-foundation
plan: 14-02b
type: execute
wave: 2
depends_on: [14-02a]
files_modified:
  - alembic/versions/20250128_140000_initial_schema.py
  - .gitignore
  - scripts/migrate.py
autonomous: true
must_haves:
  truths:
    - "Initial migration file is generated with all 9 tables"
    - "Migration creates all tables with correct schema"
    - "Migration downgrade drops all tables in reverse order"
    - "Migration follows naming convention: YYYYMMDD_HHMMSS_description.py"
    - "Helper script exists for manual migration operations"
  artifacts:
    - path: "alembic/versions/20250128_140000_initial_schema.py"
      provides: "Initial migration capturing all existing models"
      contains: ["def upgrade", "def downgrade", "op.create_table"]
      min_lines: 100
    - path: ".gitignore"
      provides: "Alembic version control configuration"
      contains: ["alembic/versions/*.py", "!alembic/versions/20250128_140000_initial_schema.py"]
    - path: "scripts/migrate.py"
      provides: "Convenience script for running Alembic migrations"
      min_lines: 60
  key_links:
    - from: "alembic/versions/20250128_140000_initial_schema.py"
      to: "bot/database/models.py"
      via: "autogenerate reads model metadata"
      pattern: "op.create_table"
    - from: "scripts/migrate.py"
      to: "alembic.ini"
      via: "reads alembic configuration"
      pattern: 'Config\\("alembic.ini"\\)'
---

# Plan 14-02b: Initial Migration Generation

**Wave:** 2
**Depends on:** 14-02a (Alembic configuration)

---

## Overview

Generate the initial Alembic migration that captures all existing models and create helper tooling for manual migration operations. This plan completes the Alembic setup by creating the first migration snapshot.

---

## Tasks

<task type="auto">
  <name>Task 1: Generate initial migration</name>
  <files>alembic/versions/20250128_140000_initial_schema.py</files>
  <action>Generate the initial migration using Alembic autogenerate:

Run the following command:
```bash
alembic revision --autogenerate -m "Initial schema with all models"
```

This will create `alembic/versions/20250128_140000_initial_schema.py` with:
- All 9 tables: bot_config, users, subscription_plans, invitation_tokens, vip_subscribers, free_channel_requests, content_packages, user_interests, user_role_change_log
- All foreign keys defined correctly
- All indexes defined correctly
- downgrade() function that drops all tables in reverse order

CRITICAL: Review the generated file to ensure:
1. All 9 tables are present
2. Foreign keys are correct (token_id, plan_id, user_id, package_id references)
3. Indexes are created for performance-critical columns
4. downgrade() properly drops tables in reverse dependency order
</action>
  <verify>
```bash
# Verify migration file was created
test -f alembic/versions/20250128_140000_initial_schema.py

# Count tables in migration
grep -c "op.create_table" alembic/versions/20250128_140000_initial_schema.py
# Should return 9 (one for each table)

# Verify downgrade exists
grep "def downgrade" alembic/versions/20250128_140000_initial_schema.py

# Verify foreign keys exist
grep "ForeignKeyConstraint" alembic/versions/20250128_140000_initial_schema.py
```
</verify>
  <done>
- Migration file created with timestamp prefix: YYYYMMDD_HHMMSS_*.py
- All 9 tables created in upgrade(): bot_config, users, subscription_plans, invitation_tokens, vip_subscribers, free_channel_requests, content_packages, user_interests, user_role_change_log
- All foreign keys defined correctly
- All indexes defined correctly
- downgrade() function drops all tables in reverse order
</done>
</task>

<task type="auto">
  <name>Task 2: Update .gitignore for Alembic</name>
  <files>.gitignore</files>
  <action>Add Alembic-specific patterns to `.gitignore`:

Strategy: Ignore all migrations by default, then explicitly allow the initial migration.

```diff
# Database
*.db
*.db-shm
*.db-wal

+# Alembic
+# Ignore all migrations by default (developers may generate different timestamps)
+alembic/versions/*.py
+# But allow the initial migration (explicitly committed)
+!alembic/versions/20250128_140000_initial_schema.py
```

DOCUMENT this strategy in a comment above the Alembic section:

```bash
+# Alembic: Strategy is to ignore auto-generated migrations
+# Only the initial migration is committed to establish the baseline
+# Future migrations should be generated per-development-environment
+# This avoids timestamp conflicts when multiple developers create migrations
```
</action>
  <verify>
```bash
# Verify patterns are present
grep "alembic/versions/\*.py" .gitignore
grep "!alembic/versions/20250128_140000_initial_schema.py" .gitignore
```
</verify>
  <done>
- .gitignore includes Alembic patterns
- Initial migration is NOT ignored (will be committed)
- Strategy is documented in .gitignore comments
</done>
</task>

<task type="auto">
  <name>Task 3: Create migration helper script</name>
  <files>scripts/migrate.py</files>
  <action>Create a convenience script `scripts/migrate.py` for running Alembic migrations manually:

```python
#!/usr/bin/env python3
"""Convenience script for running Alembic migrations manually.

Usage:
    python scripts/migrate.py          # Upgrade to latest
    python scripts/migrate.py head     # Same as above
    python scripts/migrate.py +1       # Upgrade 1 version
    python scripts/migrate.py -1       # Downgrade 1 version
    python scripts/migrate.py base     # Downgrade to initial state
    python scripts/migrate.py current  # Show current version
    python scripts/migrate.py history  # Show migration history
"""
import sys
import os
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory

# Alembic config
alembic_cfg = Config("alembic.ini")


def show_current():
    """Show current migration version."""
    script = ScriptDirectory.from_config(alembic_cfg)
    command.current(alembic_cfg, verbose=True)


def show_history():
    """Show migration history."""
    command.history(alembic_cfg, verbose=True)


def upgrade(revision: str = "head"):
    """Upgrade to a specific revision."""
    print(f"🔧 Upgrading to: {revision}")
    command.upgrade(alembic_cfg, revision)
    print("✅ Upgrade complete")


def downgrade(revision: str = "-1"):
    """Downgrade to a specific revision."""
    print(f"🔽 Downgrading to: {revision}")
    command.downgrade(alembic_cfg, revision)
    print("✅ Downgrade complete")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/migrate.py <revision>")
        print("  Examples:")
        print("    python scripts/migrate.py head     # Upgrade to latest")
        print("    python scripts/migrate.py +1       # Upgrade 1 version")
        print("    python scripts/migrate.py -1       # Downgrade 1 version")
        print("    python scripts/migrate.py base     # Downgrade to initial")
        print("    python scripts/migrate.py current  # Show current version")
        print("    python scripts/migrate.py history  # Show history")
        sys.exit(1)

    target = sys.argv[1]

    if target == "current":
        show_current()
    elif target == "history":
        show_history()
    elif target.startswith("+"):
        upgrade(target)
    elif target.startswith("-"):
        downgrade(target)
    else:
        upgrade(target)
```

Make the script executable:
```bash
chmod +x scripts/migrate.py
```
</action>
  <verify>
```bash
# Test script exists and is executable
test -x scripts/migrate.py

# Test help message
python scripts/migrate.py
# Should show usage message
```
</verify>
  <done>
- scripts/migrate.py created
- Script supports upgrade, downgrade, current, history commands
- Script has helpful usage message
- Script is executable (chmod +x)
</done>
</task>

---

## Verification Criteria

**Must-haves (goal-backward verification):**

1. ✅ Initial migration file is generated
   - File exists at `alembic/versions/20250128_140000_initial_schema.py`
   - File follows naming convention: `YYYYMMDD_HHMMSS_description.py`

2. ✅ Migration creates all 9 tables
   - `upgrade()` function creates: bot_config, users, subscription_plans, invitation_tokens, vip_subscribers, free_channel_requests, content_packages, user_interests, user_role_change_log
   - All foreign keys defined correctly

3. ✅ Migration downgrade drops all tables
   - `downgrade()` function drops all tables in reverse order
   - Prevents foreign key constraint violations

4. ✅ Helper script exists for manual operations
   - `scripts/migrate.py` supports upgrade, downgrade, current, history
   - Script provides clear usage instructions

---

## Testing Notes

**Local testing (Termux with SQLite):**
```bash
# Apply migration
alembic upgrade head

# Check current version
alembic current

# Rollback
alembic downgrade -1

# View history
alembic history
```

**Migration validation:**
```bash
# Test migration creates all tables
alembic upgrade head
python -c "from bot.database.models import Base; import asyncio; from bot.database.engine import get_engine; asyncio.run(...)"
# Should NOT create new tables (migration already created them)

# Test rollback
alembic downgrade -1
# Tables should be dropped

# Test upgrade again
alembic upgrade head
# Tables should be recreated
```

---

## Success Metrics

- ✅ `alembic upgrade head` creates all 9 tables in empty database
- ✅ `alembic downgrade -1` reverses last migration
- ✅ Migration file follows naming convention: `YYYYMMDD_HHMMSS_description.py`
- ✅ Migration works for both SQLite (local) and PostgreSQL (production)
- ✅ Helper script provides convenient interface for migration operations

---

## Output

After completion, create `.planning/phases/14-database-migration-foundation/14-02b-SUMMARY.md`
