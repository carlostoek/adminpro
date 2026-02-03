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
import subprocess
import sys
from pathlib import Path
from typing import Literal

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


def run_alembic_command(command_args: list[str]) -> tuple[int, str, str]:
    """
    Run alembic command using subprocess (completely isolated from async event loop).

    Args:
        command_args: List of arguments for alembic command

    Returns:
        Tuple of (returncode, stdout, stderr)
    """
    # Find alembic.ini in project root
    project_root = Path(__file__).parent.parent.parent.parent
    alembic_ini = project_root / "alembic.ini"

    if not alembic_ini.exists():
        logger.error(f"❌ alembic.ini not found at {alembic_ini}")
        return 1, "", f"alembic.ini not found at {alembic_ini}"

    # Build command
    cmd = [sys.executable, "-m", "alembic", "-c", str(alembic_ini)] + command_args

    logger.info(f"Running: {' '.join(cmd)}")

    # Set environment with DATABASE_URL
    env = os.environ.copy()
    env["DATABASE_URL"] = AppConfig.DATABASE_URL

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(project_root),
            env=env,
            timeout=120  # 2 minute timeout for migrations
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        logger.error("⏱️ Migration command timed out after 120 seconds")
        return 1, "", "Timeout after 120 seconds"
    except Exception as e:
        logger.error(f"❌ Failed to run alembic command: {e}")
        return 1, "", str(e)


async def get_current_revision() -> str | None:
    """
    Get current database migration revision.

    Returns:
        Current revision hash or None if database is not migrated
    """
    loop = asyncio.get_event_loop()

    def _get_current():
        returncode, stdout, stderr = run_alembic_command(["current", "--verbose"])
        if returncode != 0:
            logger.warning(f"Could not get current revision: {stderr}")
            return None
        # Output is printed to stdout by alembic
        return stdout.strip() if stdout else None

    return await loop.run_in_executor(None, _get_current)


async def show_migration_history() -> None:
    """Show full migration history (for debugging)."""
    loop = asyncio.get_event_loop()

    def _show_history():
        returncode, stdout, stderr = run_alembic_command(["history", "--verbose"])
        if stdout:
            logger.info(f"Migration history:\n{stdout}")
        if stderr:
            logger.warning(f"Migration history stderr: {stderr}")

    await loop.run_in_executor(None, _show_history)


async def run_migrations(
    direction: Literal["upgrade", "downgrade"] = "upgrade",
    revision: str = "head"
) -> bool:
    """
    Run Alembic migrations in specified direction.

    Uses subprocess to completely isolate from the async event loop.
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
    logger.info(f"Running migrations: {direction} to {revision}")

    # Build command
    if direction == "upgrade":
        cmd = ["upgrade", revision]
    elif direction == "downgrade":
        cmd = ["downgrade", revision]
    else:
        raise ValueError(f"Invalid direction: {direction}")

    loop = asyncio.get_event_loop()

    def _run_migration():
        returncode, stdout, stderr = run_alembic_command(cmd)

        # Log output
        if stdout:
            logger.info(f"Migration output:\n{stdout}")
        if stderr:
            # Alembic logs to stderr sometimes, check if it's an error
            if returncode != 0:
                logger.error(f"Migration error:\n{stderr}")
            else:
                logger.info(f"Migration info:\n{stderr}")

        return returncode

    try:
        returncode = await loop.run_in_executor(None, _run_migration)

        if returncode != 0:
            raise RuntimeError(f"Migration failed with return code {returncode}")

        logger.info(f"Migrations applied successfully ({direction} -> {revision})")
        return True

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
