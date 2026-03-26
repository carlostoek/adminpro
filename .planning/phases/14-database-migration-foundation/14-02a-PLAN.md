---
phase: 14-database-migration-foundation
plan: 14-02a
type: execute
wave: 2
depends_on: [14-01]
files_modified:
  - requirements.txt
  - alembic.ini
  - alembic/env.py
  - alembic/script.py.mako
autonomous: true
must_haves:
  truths:
    - "Alembic is installed and configured for the project"
    - "alembic.ini points to alembic directory with timestamp-based file naming"
    - "env.py connects to database using same DATABASE_URL as application"
    - "env.py imports all models for autogenerate support"
    - "script.py.mako template generates migration files with standard structure"
  artifacts:
    - path: "requirements.txt"
      provides: "alembic==1.13.1 dependency"
    - path: "alembic.ini"
      provides: "Alembic configuration with DATABASE_URL support"
      min_lines: 40
    - path: "alembic/env.py"
      provides: "Async migration environment with dialect detection"
      contains: ["get_engine", "run_migrations_online", "run_migrations_offline"]
      min_lines: 100
    - path: "alembic/script.py.mako"
      provides: "Migration file template with upgrade/downgrade functions"
      min_lines: 20
  key_links:
    - from: "alembic/env.py"
      to: "bot/database/dialect.py"
      via: "import parse_database_url, DatabaseDialect"
      pattern: "from bot.database.dialect import parse_database_url"
    - from: "alembic/env.py"
      to: "config.py"
      via: "Config.DATABASE_URL for sqlalchemy.url"
      pattern: "Config.DATABASE_URL"
    - from: "alembic/env.py"
      to: "bot/database/base.py"
      via: "import Base for target_metadata"
      pattern: "from bot.database.base import Base"
    - from: "alembic/env.py"
      to: "bot/database/models.py"
      via: "import all models for autogenerate"
      pattern: "from bot.database.models import"
---

# Plan 14-02a: Alembic Configuration

**Wave:** 2
**Depends on:** 14-01 (database dialect detection)

---

## Overview

Configure Alembic for database migrations. This plan sets up the Alembic infrastructure including configuration file, environment setup, and migration template. The next plan (14-02b) will generate the initial migration.

---

## Tasks

<task type="auto">
  <name>Task 1: Install Alembic</name>
  <files>requirements.txt</files>
  <action>Add `alembic==1.13.1` to requirements.txt for migration support.

Add it in a new "Database Migrations" section:
```diff
# Development & Testing
pytest==7.4.3
pytest-asyncio==0.21.1

+ # Database Migrations
+ alembic==1.13.1
```
</action>
  <verify>grep "alembic==1.13.1" requirements.txt returns the line</verify>
  <done>alembic==1.13.1 is present in requirements.txt</done>
</task>

<task type="auto">
  <name>Task 2: Initialize Alembic configuration</name>
  <files>alembic.ini</files>
  <action>Create `alembic.ini` at project root with the following configuration:

```ini
# Alembic Configuration File
[alembic]
# Path to migration scripts
script_location = alembic

# Template used to generate migration files
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d%%(second).2d_%%(slug)s

# sys.path path, will be prepended to sys.path if present.
prepend_sys_path = .

# Timezone for migration timestamps (default: UTC)
timezone = UTC

# max length of characters to apply to the "slug" field
truncate_slug_length = 40

# set to 'true' to run the environment during the 'revision' command
revision_environment = false

# set to 'true' to allow .pyc and .pyo files without a source .py file
sourceless = false

# Version location specification
version_locations = %(here)s/alembic/versions

# Version path separator (default: os.pathsep)
version_path_separator = os

# Output encoding used when revision files are written
output_encoding = utf-8

# Logging configuration
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

Key settings:
- `script_location = alembic` - points to migration directory
- `file_template` - uses timestamp format: `YYYYMMDD_HHMMSS_slug.py`
- `timezone = UTC` - consistent timestamps
</action>
  <verify>
```bash
# Verify file exists and has correct settings
test -f alembic.ini && grep "script_location = alembic" alembic.ini && grep "file_template" alembic.ini
```
</verify>
  <done>
- alembic.ini created at project root
- script_location points to alembic directory
- file_template uses timestamp format: YYYYMMDD_HHMMSS_slug.py
</done>
</task>

<task type="auto">
  <name>Task 3: Create Alembic environment configuration</name>
  <files>alembic/env.py</files>
  <action>Create `alembic/env.py` that connects to the database using the same configuration as the application:

```python
"""Alembic environment configuration."""
import os
import sys
import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import async_engine_from_config, AsyncEngine

from alembic import context

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import base and models for Autogenerate support
from bot.database.base import Base
from bot.database.models import (
    BotConfig, User, SubscriptionPlan, InvitationToken,
    VIPSubscriber, FreeChannelRequest, UserInterest,
    UserRoleChangeLog, ContentPackage
)
from bot.database.enums import UserRole, ContentCategory, RoleChangeReason, PackageType

# Import config for DATABASE_URL
from config import Config

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set logger for Alembic
logger = logging.getLogger("alembic.env")

# Set sqlalchemy.url in Alembic config from DATABASE_URL
# This allows Alembic to use the same database as the application
config.set_main_option("sqlalchemy.url", Config.DATABASE_URL)

# Add metadata for autogenerate
target_metadata = Base.metadata


def get_engine() -> AsyncEngine:
    """
    Create async engine for Alembic migrations.

    Uses the same configuration as the application (bot/database/engine.py).
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = Config.DATABASE_URL

    # Detect dialect from DATABASE_URL
    from bot.database.dialect import parse_database_url, DatabaseDialect

    try:
        dialect, _ = parse_database_url(Config.DATABASE_URL)
        logger.info(f"🔍 Alembic: Dialect detectado: {dialect.value}")
    except Exception as e:
        logger.error(f"❌ Alembic: Error detectando dialecto: {e}")
        raise

    # Create async engine with appropriate pool
    if dialect == DatabaseDialect.POSTGRESQL:
        # PostgreSQL: QueuePool for connection reuse
        configuration["poolclass"] = "sqlalchemy.pool.QueuePool"
        configuration["pool_size"] = "5"
        configuration["max_overflow"] = "10"
    else:
        # SQLite: NullPool
        configuration["poolclass"] = "sqlalchemy.pool.NullPool"

    return async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Actual migration execution callback."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    """Run migrations in async mode."""
    connectable = get_engine()

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a
    connection with the context.
    """
    import asyncio
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

IMPORTANT:
- Must import ALL models for autogenerate to detect them
- Must use Config.DATABASE_URL for consistency
- Must detect dialect from bot.database.dialect for type validation (DBMIG-06)
</action>
  <verify>
```python
# Test that env.py can be imported without errors
import sys
sys.path.insert(0, '.')
from alembic import env
assert hasattr(env, 'get_engine')
assert hasattr(env, 'run_migrations_online')
assert hasattr(env, 'run_migrations_offline')

# Verify models are imported
from bot.database.models import BotConfig, User, SubscriptionPlan
```
</verify>
  <done>
- alembic/env.py imports all models for autogenerate
- get_engine() uses Config.DATABASE_URL from environment
- run_migrations_online() runs async migrations
- Dialect detection works for both SQLite and PostgreSQL (DBMIG-06)
</done>
</task>

<task type="auto">
  <name>Task 4: Create migration script template</name>
  <files>alembic/script.py.mako</files>
  <action>Create `alembic/script.py.mako` template for consistent migration file generation:

```python
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

This template ensures:
- Standard Alembic revision identifiers
- Type hints for revision/down_revision
- upgrade() and downgrade() functions
- Message injection via ${message} variable
</action>
  <verify>
```bash
# Verify template exists and has required sections
test -f alembic/script.py.mako && grep -E "def upgrade|def downgrade" alembic/script.py.mako
```
</verify>
  <done>
- Template includes standard Alembic revision identifiers
- Template includes upgrade() and downgrade() functions
- Template supports message injection via ${message} variable
</done>
</task>

---

## Verification Criteria

**Must-haves (goal-backward verification):**

1. ✅ Alembic configured with `sqlalchemy.url` in `alembic.ini`
   - `alembic.ini` created with valid configuration
   - `script_location` set to `alembic`

2. ✅ `env.py` detects `DATABASE_URL` from environment
   - `env.py` reads `Config.DATABASE_URL` from environment variable
   - `env.py` passes URL to Alembic config

3. ✅ `alembic/` directory structure created
   - `alembic/versions/` directory exists
   - `alembic/script.py.mako` template exists

4. ✅ `env.py` imports all models for autogenerate
   - `env.py` imports all 9 models from bot.database.models
   - target_metadata is set to Base.metadata

5. ✅ Dialect detection in env.py for type validation (DBMIG-06)
   - `env.py` calls `parse_database_url()` to detect dialect
   - Engine configuration adjusted based on dialect
   - Type comparison enabled (compare_type=True)

---

## Success Metrics

- ✅ `alembic.ini` exists with valid configuration
- ✅ `alembic/env.py` connects using same DATABASE_URL as application
- ✅ `alembic/script.py.mako` template generates proper migration files
- ✅ All models imported for autogenerate support
- ✅ Dialect detection ensures type compatibility (DBMIG-06)

---

## Output

After completion, create `.planning/phases/14-database-migration-foundation/14-02a-SUMMARY.md`
