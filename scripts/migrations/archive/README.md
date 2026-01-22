# Migration Scripts Archive

This directory contains migration scripts that have already been executed and are kept for reference.

## Purpose

- **Historical Record**: Documents database schema changes over time
- **Rollback Reference**: Can be used to understand what changes were made
- **Audit Trail**: Provides visibility into database evolution

## Scripts

### `add_plan_id_to_tokens.py` (Executed: 2026-01-21)

**Purpose**: Added `plan_id` column to `invitation_tokens` table

**Reason**: Enable deep link activation with plan association (Feature A3)

**Changes**:
- Added `plan_id INTEGER` column to `invitation_tokens`
- Created foreign key reference to `subscription_plans(id)`
- Made column nullable (backward compatibility)

**Status**: ✅ Successfully executed

## Important Notes

⚠️ **Do NOT re-run archived scripts** unless you are absolutely certain about what you're doing.

These scripts:
- Have already been applied to the production database
- May fail if run again (column already exists)
- Are kept for documentation purposes only

## Adding New Archives

When archiving a migration script:

1. Ensure it has been successfully executed
2. Move it to this directory
3. Update this README with:
   - Script name
   - Execution date
   - Purpose
   - Changes made
   - Status
