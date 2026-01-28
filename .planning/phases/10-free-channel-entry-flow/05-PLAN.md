---
wave: 1
depends_on: [PLAN-01]
files_modified:
  - bot/database/engine.py
autonomous: true
estimated_minutes: 2
---

# Plan 05: Database Migration - Auto-Create New Columns

## Goal
Ensure new BotConfig columns are auto-created on next app start without explicit migration script.

## Context
Phase 10 adds 4 new fields to BotConfig: `social_instagram`, `social_tiktok`, `social_x`, `free_channel_invite_link`. SQLAlchemy's `create_all()` should auto-add these columns since they're nullable.

## Tasks

### T1: Verify Auto-Creation Behavior
**File:** `bot/database/engine.py`

**Check:**
- Existing `create_all()` call in `init_db()`
- No explicit migration needed (new columns are nullable)

**Verification:**
```python
# In bot/database/engine.py, init_db() should have:
async def init_db():
    async with engine.begin() as conn:
        # This creates all tables that don't exist
        # and adds new nullable columns to existing tables
        await conn.run_sync(Base.metadata.create_all)
```

**Voice Rationale:**
- SQLAlchemy's `create_all()` is idempotent
- New nullable columns are auto-added to existing tables
- No data loss (columns are nullable, no defaults)

**Acceptance:**
- [ ] Verify `create_all()` exists in init_db()
- [ ] Confirm no explicit migration script needed
- [ ] Document that new columns will be auto-created

---

### T2: Create Initial Data Setup Script (Optional)
**File:** `scripts/init_social_media.py` (NEW FILE)

**Purpose:**
Allow admin to set initial social media values via script.

**Implementation:**
```python
"""
Initial Social Media Setup Script.

Run this to set initial social media links for Free channel entry flow.

Usage:
    python scripts/init_social_media.py
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.engine import get_session
from bot.services.config import ConfigService


async def setup_social_media():
    """Set initial social media links."""
    async with get_session() as session:
        config_service = ConfigService(session)

        # Set social media links (modify these values)
        await config_service.set_social_instagram("@diana_handle")
        await config_service.set_social_tiktok("@diana_tiktok")
        await config_service.set_social_x("@diana_x")

        # Set Free channel invite link (get from Telegram)
        await config_service.set_free_channel_invite_link("https://t.me/joinchat/...")

        # Commit changes
        await session.commit()

        print("✅ Social media links configured successfully")
        print(f"Instagram: {await config_service.get_social_instagram()}")
        print(f"TikTok: {await config_service.get_social_tiktok()}")
        print(f"X: {await config_service.get_social_x()}")
        print(f"Free channel link: {await config_service.get_free_channel_invite_link()}")


if __name__ == "__main__":
    asyncio.run(setup_social_media())
```

**Voice Rationale:**
- Optional helper script (not required)
- Allows quick setup without manual DB queries
- Can be deleted after initial setup

**Acceptance:**
- [ ] Script file created in scripts/ directory
- [ ] Script sets all 4 new BotConfig fields
- [ ] Script commits changes and prints confirmation

---

### T3: Update README.md with Setup Instructions
**File:** `README.md` (if exists)

**Add Section:**
```markdown
## Social Media Setup (Phase 10)

The Free channel entry flow displays creator's social media buttons. To configure:

### Option 1: Setup Script
```bash
python scripts/init_social_media.py
```

### Option 2: Manual Database Update
```sql
UPDATE bot_config SET
  social_instagram = '@diana_handle',
  social_tiktok = '@diana_tiktok',
  social_x = '@diana_x',
  free_channel_invite_link = 'https://t.me/joinchat/...'
WHERE id = 1;
```

### Getting Invite Link:
1. Open Free channel in Telegram
2. Go to Channel Info → Administrators
3. Click "Invite Link" → Create new link
4. Copy link and set in `free_channel_invite_link`
```

**Acceptance:**
- [ ] README.md updated with social media setup instructions
- [ ] Instructions include both script and manual options
- [ ] Instructions explain how to get invite link from Telegram

---

## Verification

### Pre-Commit Verification:
1. **Engine check:** `create_all()` exists in init_db()
2. **Script check:** `scripts/init_social_media.py` imports work

### Post-Commit Testing:
```bash
# 1. Start app - columns should be auto-created
python main.py

# 2. Check database schema
sqlite3 bot.db ".schema bot_config"
# Should show: social_instagram, social_tiktok, social_x, free_channel_invite_link

# 3. Run setup script
python scripts/init_social_media.py
# Should print success message with configured values

# 4. Verify in database
sqlite3 bot.db "SELECT social_instagram, social_tiktok, social_x, free_channel_invite_link FROM bot_config WHERE id = 1;"
```

---

## Integration Notes

**No Breaking Changes:**
- New columns are nullable (existing BotConfig records work)
- SQLAlchemy auto-adds columns on next app start
- No explicit migration script needed

**Data Safety:**
- `create_all()` is idempotent (safe to run multiple times)
- Existing data preserved (columns are nullable)
- No defaults set (all fields start as NULL)

**Admin Action Required:**
After deployment, admin MUST:
1. Get invite link from Free channel settings
2. Set social media handles/URLs
3. Test Free entry flow to verify buttons work

---

## must_haves

1. ✅ Verify `create_all()` exists in bot/database/engine.py
2. ✅ Create optional setup script in scripts/init_social_media.py
3. ✅ Update README.md with social media setup instructions
4. ✅ Document that columns are auto-created (no migration needed)
5. ✅ Include instructions for getting invite link from Telegram
