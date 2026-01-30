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
