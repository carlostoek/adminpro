---
wave: 1
depends_on: []
files_modified:
  - bot/database/models.py
  - bot/services/config.py
autonomous: true
estimated_minutes: 5
---

# Plan 01: Database Extension - Social Media Fields

## Goal
Extend BotConfig model with social media fields and update ConfigService to manage them.

## Context
Phase 10 requires adding creator's social media links (Instagram, TikTok, X) to the Free channel entry flow. These links need persistent storage in BotConfig.

## Tasks

### T1: Add Social Media Fields to BotConfig Model
**File:** `bot/database/models.py`

**Changes:**
```python
class BotConfig(Base):
    # ... existing fields ...

    # Social Media Links (Phase 10)
    social_instagram: str = None  # Instagram handle or URL
    social_tiktok: str = None     # TikTok handle or URL
    social_x: str = None          # X/Twitter handle or URL
    free_channel_invite_link: str = None  # Stored invite link for Free channel
```

**Voice Rationale:**
- Field names use `social_` prefix for clarity
- All fields are nullable (Optional[str]) to allow gradual configuration
- `free_channel_invite_link` stores the link for approval messages

**Acceptance:**
- [ ] Fields added to BotConfig model
- [ ] Fields are nullable (Optional[str])
- [ ] Model repr updated if needed (optional)

---

### T2: Add Getters/Setters to ConfigService
**File:** `bot/services/config.py`

**New Getters:**
```python
async def get_social_instagram(self) -> Optional[str]:
    """Get Instagram handle or URL."""
    config = await self.get_config()
    return config.social_instagram if config.social_instagram else None

async def get_social_tiktok(self) -> Optional[str]:
    """Get TikTok handle or URL."""
    config = await self.get_config()
    return config.social_tiktok if config.social_tiktok else None

async def get_social_x(self) -> Optional[str]:
    """Get X/Twitter handle or URL."""
    config = await self.get_config()
    return config.social_x if config.social_x else None

async def get_free_channel_invite_link(self) -> Optional[str]:
    """Get stored Free channel invite link."""
    config = await self.get_config()
    return config.free_channel_invite_link if config.free_channel_invite_link else None
```

**New Setters:**
```python
async def set_social_instagram(self, handle: str) -> None:
    """
    Set Instagram handle or URL.

    Args:
        handle: Instagram handle (e.g., "@diana") or full URL

    Raises:
        ValueError: If handle is empty or only whitespace
    """
    if not handle or not handle.strip():
        raise ValueError("Instagram handle cannot be empty")

    config = await self.get_config()
    config.social_instagram = handle.strip()

async def set_social_tiktok(self, handle: str) -> None:
    """Set TikTok handle or URL."""
    if not handle or not handle.strip():
        raise ValueError("TikTok handle cannot be empty")

    config = await self.get_config()
    config.social_tiktok = handle.strip()

async def set_social_x(self, handle: str) -> None:
    """Set X/Twitter handle or URL."""
    if not handle or not handle.strip():
        raise ValueError("X handle cannot be empty")

    config = await self.get_config()
    config.social_x = handle.strip()

async def set_free_channel_invite_link(self, link: str) -> None:
    """Set Free channel invite link for approval messages."""
    if not link or not link.strip():
        raise ValueError("Invite link cannot be empty")

    config = await self.get_config()
    config.free_channel_invite_link = link.strip()
```

**Voice Rationale:**
- Follows existing ConfigService pattern (get_config() + field access)
- Validation in setters prevents empty values
- Strip whitespace to avoid accidental spaces

**Acceptance:**
- [ ] 4 getter methods added (3 social + 1 invite link)
- [ ] 4 setter methods added with validation
- [ ] Docstrings follow Google Style
- [ ] Raises ValueError for empty/whitespace-only input

---

### T3: Add Convenience Method for Social Media Dictionary
**File:** `bot/services/config.py`

**New Method:**
```python
async def get_social_media_links(self) -> dict[str, str]:
    """
    Get all configured social media links as dictionary.

    Returns:
        Dict with keys 'instagram', 'tiktok', 'x' for configured platforms only.
        Example: {'instagram': '@diana', 'tiktok': '@diana_tiktok'}
        (Unconfigured platforms omitted)

    Voice Rationale:
        Enables easy iteration for keyboard generation.
        Omitting None values simplifies UI logic.
    """
    config = await self.get_config()
    links = {}

    if config.social_instagram:
        links['instagram'] = config.social_instagram
    if config.social_tiktok:
        links['tiktok'] = config.social_tiktok
    if config.social_x:
        links['x'] = config.social_x

    return links
```

**Voice Rationale:**
- Single call gets all social media for keyboard generation
- Omits None values to avoid empty buttons
- Returns lowercase keys for consistent mapping

**Acceptance:**
- [ ] Method returns dict with configured platforms only
- [ ] Keys are lowercase: 'instagram', 'tiktok', 'x'
- [ ] Values are non-empty strings (no None values in dict)

---

## Verification

### Pre-Commit Verification:
1. **Import test:** `from bot.services.config import ConfigService` - no errors
2. **Method existence:** `hasattr(ConfigService, 'get_social_instagram')` - True
3. **Pattern consistency:** Follows existing `get_wait_time()` pattern

### Post-Commit Testing:
```python
# Test getter
instagram = await container.config.get_social_instagram()
assert instagram is None or isinstance(instagram, str)

# Test setter
await container.config.set_social_instagram("@diana")
instagram = await container.config.get_social_instagram()
assert instagram == "@diana"

# Test validation
try:
    await container.config.set_social_instagram("  ")
    assert False, "Should raise ValueError"
except ValueError:
    pass  # Expected

# Test convenience method
links = await container.config.get_social_media_links()
assert isinstance(links, dict)
assert all(k in ['instagram', 'tiktok', 'x'] for k in links.keys())
```

---

## Integration Notes

**No Breaking Changes:**
- All new fields are nullable (Optional[str])
- Existing BotConfig records work without migration
- New methods don't modify existing behavior

**Admin UI:**
- Admin will set social media via bot (not CLI)
- Future phase could add admin menu for social media management
- For now, direct DB update or script can set initial values

**Database Migration:**
- SQLAlchemy will auto-add columns on next app start (create_all)
- No explicit migration script needed (new fields are nullable)

---

## must_haves

1. ✅ BotConfig has 4 new fields: social_instagram, social_tiktok, social_x, free_channel_invite_link
2. ✅ ConfigService has 4 getters and 4 setters for new fields
3. ✅ Setters validate input (raise ValueError for empty/whitespace)
4. ✅ get_social_media_links() returns dict with only configured platforms
5. ✅ All methods follow existing ConfigService pattern (get_config() + field access)
6. ✅ Docstrings follow Google Style with Voice Rationale
