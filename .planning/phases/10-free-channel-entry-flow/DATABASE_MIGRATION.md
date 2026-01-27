# Database Migration - Phase 10 (Free Channel Entry Flow)

## Auto-Creation Behavior

Phase 10 adds 4 new fields to `BotConfig` model:
- `social_instagram` (Optional[str]) - Instagram handle or URL
- `social_tiktok` (Optional[str]) - TikTok handle or URL
- `social_x` (Optional[str]) - X/Twitter handle or URL
- `free_channel_invite_link` (Optional[str]) - Stored invite link for Free channel

## No Explicit Migration Needed

These columns will be **automatically created** on next app start because:

1. **SQLAlchemy's `create_all()` is idempotent**
   - Safe to run multiple times
   - Only creates tables/columns that don't exist
   - Does not modify existing tables (except adding new nullable columns)

2. **New columns are nullable (Optional[str])**
   - Existing BotConfig records work without modification
   - No data loss (columns start as NULL)
   - No defaults required

3. **Implementation in `bot/database/engine.py`**
   ```python
   async def init_db():
       # ... SQLite configuration ...

       # This creates all tables and adds new nullable columns
       async with _engine.begin() as conn:
           await conn.run_sync(Base.metadata.create_all)
   ```

## Verification

After Plan 01 is executed (model updated with new fields), verify:

```bash
# 1. Start app - columns should be auto-created
python main.py

# 2. Check database schema
sqlite3 bot.db ".schema bot_config"
# Should show: social_instagram, social_tiktok, social_x, free_channel_invite_link
```

## Data Safety

- ✅ Existing data preserved (columns are nullable)
- ✅ No breaking changes (all fields are optional)
- ✅ No manual SQL migration required
- ✅ Works on first app start after model update

## Admin Action Required

After deployment, admin should:
1. Get invite link from Free channel settings
2. Set social media handles/URLs (via admin menu or setup script)
3. Test Free entry flow to verify buttons work
