#!/bin/bash
#
# Git Hook Installation Script
#
# This script installs the voice linter pre-commit hook by creating a symlink
# from .git/hooks/pre-commit to .hooks/pre-commit.
#
# Usage: .hooks/install.sh

set -e

HOOKS_DIR=".git/hooks"
SOURCE_HOOK=".hooks/pre-commit"
TARGET_HOOK="$HOOKS_DIR/pre-commit"

echo "🎩 Installing Lucien Voice Linter pre-commit hook..."

# Check if .git directory exists
if [ ! -d ".git" ]; then
    echo "❌ Error: .git directory not found. Are you in a git repository?"
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p "$HOOKS_DIR"

# Backup existing hook if present
if [ -e "$TARGET_HOOK" ] && [ ! -L "$TARGET_HOOK" ]; then
    BACKUP_HOOK="$TARGET_HOOK.backup.$(date +%s)"
    echo "⚠️  Existing pre-commit hook found, backing up to: $BACKUP_HOOK"
    mv "$TARGET_HOOK" "$BACKUP_HOOK"
fi

# Create symlink
ln -sf "../../$SOURCE_HOOK" "$TARGET_HOOK"
echo "✅ Created symlink: $TARGET_HOOK -> ../../$SOURCE_HOOK"

# Make executable
chmod +x "$TARGET_HOOK"
echo "✅ Made hook executable"

echo ""
echo "✨ Pre-commit hook installed successfully!"
echo ""
echo "The hook will now run automatically on every git commit."
echo "To bypass (use sparingly): git commit --no-verify"
