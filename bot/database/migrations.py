"""Alembic migration runner for automatic schema updates on startup.

This module provides:
- Automatic migration on production startup
- Verbose logging for debugging
- Fail-fast on migration errors
- Rollback support via Alembic commands

Usage:
    # In main.py startup handler:
    await run_migrations_if_needed()
"""
import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from alembic.config import Config
from alembic import command

from config import Config as AppConfig

logger = logging.getLogger(__name__)


MigrationLevel = Literal["INFO", "WARNING", "ERROR", "CRITICAL"]


def is_production() -> bool:
    """
    Detect if running in production mode.

    Production mode is enabled by setting ENV=production environment variable.
    In production, migrations run automatically on startup.

    Returns:
        True if ENV=production, False otherwise
    """
    return os.getenv("ENV", "").lower() == "production"


def get_alembic_config() -> Config:
    """
    Create Alembic config object from project configuration.

    Uses the same DATABASE_URL as the application.

    Returns:
        Alembic Config object
    """
    alembic_cfg = Config("alembic.ini")
    # Ensure DATABASE_URL is set from environment
    alembic_cfg.set_main_option("sqlalchemy.url", AppConfig.DATABASE_URL)
    return alembic_cfg


def _get_current_revision_sync() -> str | None:
    """
    Synchronous version: Get current database migration revision.

    Returns:
        Current revision hash or None if database is not migrated
    """
    try:
        cfg = get_alembic_config()
        command.current(cfg, verbose=True)
        # Note: command.current() prints to stdout, doesn't return value
        return None  # Placeholder - would need DB query for actual value
    except Exception as e:
        logger.warning(f"Could not get current revision: {e}")
        return None


async def get_current_revision() -> str | None:
    """
    Get current database migration revision.

    Runs in thread pool to avoid blocking the event loop.

    Returns:
        Current revision hash or None if database is not migrated
    """
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as executor:
        return await loop.run_in_executor(executor, _get_current_revision_sync)


def _show_migration_history_sync() -> None:
    """Synchronous version: Show full migration history (for debugging)."""
    cfg = get_alembic_config()
    logger.info("Migration history:")
    command.history(cfg, verbose=True)


async def show_migration_history() -> None:
    """Show full migration history (for debugging)."""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as executor:
        await loop.run_in_executor(executor, _show_migration_history_sync)


def _run_migrations_sync(
    direction: Literal["upgrade", "downgrade"] = "upgrade",
    revision: str = "head"
) -> bool:
    """
    Run Alembic migrations synchronously (to be called in thread executor).

    Args:
        direction: Either "upgrade" or "downgrade"
        revision: Target revision (default: "head" for upgrade, "-1" for downgrade)

    Returns:
        True if migrations succeeded, False if failed

    Raises:
        Exception: If migration fails
    """
    cfg = get_alembic_config()

    logger.info(f"Running migrations: {direction} to {revision}")

    if direction == "upgrade":
        command.upgrade(cfg, revision)
    elif direction == "downgrade":
        command.downgrade(cfg, revision)
    else:
        raise ValueError(f"Invalid direction: {direction}")

    logger.info(f"Migrations applied successfully ({direction} -> {revision})")
    return True


async def run_migrations(
    direction: Literal["upgrade", "downgrade"] = "upgrade",
    revision: str = "head"
) -> bool:
    """
    Run Alembic migrations in specified direction.

    Runs migrations in a thread pool to avoid conflicts with the async event loop.
    Logs all migration activity with verbose output.
    Fails immediately on error.

    Args:
        direction: Either "upgrade" or "downgrade"
        revision: Target revision (default: "head" for upgrade, "-1" for downgrade)

    Returns:
        True if migrations succeeded, False if failed

    Raises:
        Exception: If migration fails (fail-fast)
    """
    loop = asyncio.get_event_loop()

    try:
        # Run migrations in thread pool to avoid asyncio.run() conflicts
        with ThreadPoolExecutor(max_workers=1) as executor:
            result = await loop.run_in_executor(
                executor,
                _run_migrations_sync,
                direction,
                revision
            )
        return result

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        logger.critical(
            "DATABASE MIGRATION FAILED. "
            "Bot cannot start without proper schema. "
            "Fix the migration issue and restart."
        )
        raise


async def run_migrations_if_needed() -> bool:
    """
    Run migrations automatically if in production mode.

    In development mode, skip migrations (developer must run manually).
    Logs warnings if migrations fail.

    Returns:
        True if migrations succeeded or were skipped, False if failed
    """
    if not is_production():
        logger.info(
            "Development mode detected. "
            "Skipping automatic migrations. "
            "Run 'alembic upgrade head' manually if needed."
        )
        return True

    # Production mode: run migrations automatically
    logger.info("Production mode detected. Running migrations...")

    try:
        # Show current state
        logger.info("Current migration state:")
        await get_current_revision()

        # Run migrations to head
        await run_migrations("upgrade", "head")

        # Show history for debugging
        await show_migration_history()

        return True

    except Exception as e:
        logger.critical(
            f"CRITICAL: Automatic migrations failed in production. "
            f"The bot cannot start without a valid schema. "
            f"Error: {e}"
        )
        # Re-raise to prevent bot startup
        raise


async def rollback_last_migration() -> bool:
    """
    Rollback the last migration (convenience function).

    This is useful for reverting a problematic migration in production.

    Returns:
        True if rollback succeeded, False if failed

    Raises:
        Exception: If rollback fails
    """
    logger.warning("Rolling back last migration...")
    return await run_migrations("downgrade", "-1")


async def rollback_to_base() -> bool:
    """
    Rollback all migrations to base state (empty schema).

    WARNING: This will drop all tables! Use with caution.

    Returns:
        True if rollback succeeded, False if failed

    Raises:
        Exception: If rollback fails
    """
    logger.critical("Rolling back to base state (all tables will be dropped)...")
    return await run_migrations("downgrade", "base")
