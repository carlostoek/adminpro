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
from bot.database.dialect import parse_database_url

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set logger for Alembic
logger = logging.getLogger("alembic.env")

# Parse DATABASE_URL to inject async driver (asyncpg/aiosqlite)
# This ensures the URL format is correct for async SQLAlchemy
_, DATABASE_URL_WITH_DRIVER = parse_database_url(Config.DATABASE_URL)

# Set sqlalchemy.url in Alembic config from parsed DATABASE_URL
# This allows Alembic to use the same database as the application
config.set_main_option("sqlalchemy.url", DATABASE_URL_WITH_DRIVER)

# Add metadata for autogenerate
target_metadata = Base.metadata


def get_engine() -> AsyncEngine:
    """
    Create async engine for Alembic migrations.

    Uses the same configuration as the application (bot/database/engine.py).
    """
    configuration = config.get_section(config.config_ini_section)

    # DATABASE_URL_WITH_DRIVER already has the async driver injected
    # (e.g., postgresql+asyncpg:// or sqlite+aiosqlite://)
    configuration["sqlalchemy.url"] = DATABASE_URL_WITH_DRIVER

    # Detect dialect from parsed URL
    from bot.database.dialect import DatabaseDialect

    try:
        dialect, _ = parse_database_url(DATABASE_URL_WITH_DRIVER)
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
        pool_class = pool.QueuePool
    else:
        # SQLite: NullPool
        configuration["poolclass"] = "sqlalchemy.pool.NullPool"
        pool_class = pool.NullPool

    return async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool_class,
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
