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
