# Database Migration - Phase 13: VIP Entry Stage Fields

## Overview
Add 3 new fields to vip_subscribers table to track 3-stage ritual entry flow.

## New Fields

### vip_entry_stage
- Type: INTEGER (nullable)
- Default: 1
- Purpose: Track progress through ritual (1 -> 2 -> 3 -> NULL)
- Index: Yes (idx_vip_entry_stage)

### vip_entry_token
- Type: VARCHAR(64) (nullable, unique)
- Purpose: One-time token for Stage 3 invite link generation

### invite_link_sent_at
- Type: TIMESTAMP (nullable)
- Purpose: Track when Stage 3 link was sent (24h expiry)

## SQL Migration

### Option 1: Automatic (SQLAlchemy)
SQLAlchemy will create these columns automatically on next app start via `create_all()`.
New columns are nullable, so existing records work without manual migration.

**Steps:**
1. Stop the bot
2. Pull latest code (git pull)
3. Restart bot
4. SQLAlchemy auto-creates columns on first startup

### Option 2: Manual SQL
```sql
-- Add new columns
ALTER TABLE vip_subscribers ADD COLUMN vip_entry_stage INTEGER DEFAULT 1;
ALTER TABLE vip_subscribers ADD COLUMN vip_entry_token VARCHAR(64) UNIQUE;
ALTER TABLE vip_subscribers ADD COLUMN invite_link_sent_at TIMESTAMP;

-- Create index
CREATE INDEX idx_vip_entry_stage ON vip_subscribers(vip_entry_stage);

-- Set NULL for existing active subscribers (skip ritual flow)
UPDATE vip_subscribers SET vip_entry_stage = NULL
WHERE status = 'active' AND vip_entry_stage = 1;

-- Verify
SELECT COUNT(*) FROM vip_subscribers WHERE vip_entry_stage IS NULL;  -- Existing active subs
SELECT COUNT(*) FROM vip_subscribers WHERE vip_entry_stage = 1;      -- New activations
```

## Backward Compatibility

### Existing Active Subscribers
- vip_entry_stage = NULL (skip ritual, already have access)
- Continue to work normally
- No change to existing behavior

### New VIP Activations
- vip_entry_stage = 1 (start ritual)
- Go through 3-stage flow before accessing channel
- UserRole remains FREE until Stage 3 completion

## Verification Queries

```sql
-- Check new columns exist
PRAGMA table_info(vip_subscribers);

-- Check index exists
PRAGMA index_list('vip_subscribers');

-- Count subscribers by stage
SELECT
    vip_entry_stage,
    COUNT(*) as count
FROM vip_subscribers
GROUP BY vip_entry_stage;

-- Verify existing active subscribers have NULL stage
SELECT
    COUNT(*) as existing_active_subs
FROM vip_subscribers
WHERE status = 'active' AND vip_entry_stage IS NULL;
```

## Rollback
```sql
DROP INDEX IF EXISTS idx_vip_entry_stage;
ALTER TABLE vip_subscribers DROP COLUMN IF EXISTS vip_entry_stage;
ALTER TABLE vip_subscribers DROP COLUMN IF EXISTS vip_entry_token;
ALTER TABLE vip_subscribers DROP COLUMN IF EXISTS invite_link_sent_at;
```

## Notes

**Migration Strategy:**
- Automatic (SQLAlchemy): Recommended for production
- Manual SQL: Use if you need explicit control over migration timing

**Data Safety:**
- New columns are nullable with defaults (no data loss)
- Existing records get vip_entry_stage=1 initially, then set to NULL via UPDATE
- No downtime required (columns are nullable)

**Post-Migration:**
- Verify with queries above
- Test new VIP activation flow
- Monitor logs for vip_entry_stage progression
