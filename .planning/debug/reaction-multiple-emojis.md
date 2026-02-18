---
status: resolved
trigger: "Reaction system allows users to react multiple times to the same message with different emojis - should only allow ONE reaction per message total"
created: 2026-02-11T00:00:00
updated: 2026-02-11T00:00:00
---

## Current Focus

hypothesis: The unique constraint in UserReaction model and the _is_duplicate_reaction() method both enforce "one reaction per emoji per message" instead of "one reaction per message"
test: Analyze code to confirm root cause
expecting: Confirm the unique constraint includes emoji column
next_action: Document findings and required changes

## Symptoms

expected: User can react with ❤️ to message #123, but CANNOT react with 🔥 to message #123 (already reacted)
actual: User can react with ❤️ AND 🔥 to the same message #123 (different emoji = allowed)
errors: No error - behavior is incorrect by design
reproduction:
  1. User reacts to message #123 with ❤️
  2. User reacts to message #123 with 🔥
  3. Both reactions are accepted (BUG)
started: Always been this way (design flaw)

## Eliminated

## Evidence

- timestamp: 2026-02-11
  checked: bot/database/models.py lines 775-834 (UserReaction model)
  found: Unique constraint on line 823 is `Index('idx_user_content_emoji', 'user_id', 'content_id', 'emoji', unique=True)`
  implication: Database allows multiple reactions per user/content as long as emoji differs

- timestamp: 2026-02-11
  checked: bot/services/reaction.py lines 139-165 (_is_duplicate_reaction method)
  found: Method checks `UserReaction.emoji == emoji` in the WHERE clause
  implication: Application logic also only prevents duplicate (user, content, emoji) combinations

- timestamp: 2026-02-11
  checked: bot/handlers/user/reactions.py lines 153-154
  found: Error message says "Ya reaccionaste con este emoji" (You already reacted with THIS emoji)
  implication: UX messaging confirms the "per emoji" design assumption

## Resolution

root_caused: CONFIRMED - The unique constraint and deduplication logic both include the emoji column, allowing one reaction per emoji per message instead of one reaction per message total.

### Root Cause Explanation

The current implementation enforces uniqueness on the combination of `(user_id, content_id, emoji)`. This means:
- User can react with ❤️ to message #123 (creates row)
- User can react with 🔥 to message #123 (creates different row because emoji differs)

The expected behavior requires uniqueness on `(user_id, content_id)` ONLY, regardless of emoji.

### Required Changes

#### 1. Database Model Change (bot/database/models.py)

**Current (lines 821-828):**
```python
__table_args__ = (
    # Unique constraint: one reaction per user/content/emoji combination
    Index('idx_user_content_emoji', 'user_id', 'content_id', 'emoji', unique=True),
    # Index for "user's recent reactions" queries (rate limiting)
    Index('idx_user_reactions_recent', 'user_id', 'created_at'),
    # Index for "reactions to content" queries
    Index('idx_content_reactions', 'channel_id', 'content_id', 'emoji'),
)
```

**Required:**
```python
__table_args__ = (
    # Unique constraint: one reaction per user/content (regardless of emoji)
    Index('idx_user_content', 'user_id', 'content_id', unique=True),
    # Index for "user's recent reactions" queries (rate limiting)
    Index('idx_user_reactions_recent', 'user_id', 'created_at'),
    # Index for "reactions to content" queries
    Index('idx_content_reactions', 'channel_id', 'content_id', 'emoji'),
)
```

#### 2. Service Logic Change (bot/services/reaction.py)

**Current (lines 139-165):**
```python
async def _is_duplicate_reaction(
    self,
    user_id: int,
    content_id: int,
    emoji: str
) -> bool:
    """
    Verifica si el usuario ya reaccionó con este emoji a este contenido.
    """
    result = await self.session.execute(
        select(UserReaction.id)
        .where(
            UserReaction.user_id == user_id,
            UserReaction.content_id == content_id,
            UserReaction.emoji == emoji  # <-- BUG: includes emoji
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None
```

**Required:**
```python
async def _is_duplicate_reaction(
    self,
    user_id: int,
    content_id: int,
    emoji: str = None  # emoji no longer needed for check, kept for API compatibility
) -> bool:
    """
    Verifica si el usuario ya reaccionó a este contenido (cualquier emoji).
    """
    result = await self.session.execute(
        select(UserReaction.id)
        .where(
            UserReaction.user_id == user_id,
            UserReaction.content_id == content_id
            # Removed: UserReaction.emoji == emoji
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None
```

#### 3. Handler Message Update (bot/handlers/user/reactions.py)

**Current (line 153-154):**
```python
"duplicate": "Ya reaccionaste con este emoji",
```

**Required:**
```python
"duplicate": "Ya reaccionaste a este contenido",
```

### Migration Requirements

A database migration is REQUIRED because:
1. The unique constraint `idx_user_content_emoji` must be dropped
2. A new unique constraint `idx_user_content` must be created
3. Existing data may have violations (users with multiple reactions to same content) that need handling

**Migration Strategy Options:**

**Option A: Keep first reaction, delete duplicates**
```sql
-- For each user_id + content_id combination with multiple reactions,
-- keep the oldest one and delete the rest
DELETE FROM user_reactions
WHERE id NOT IN (
    SELECT MIN(id)
    FROM user_reactions
    GROUP BY user_id, content_id
);
```

**Option B: Fail migration if duplicates exist**
- Check for violations before migration
- Alert admin to manually resolve

**Option C: Migration script (Alembic-style)**
```python
# 1. Create new index without unique constraint first
# 2. Handle data cleanup (keep first reaction per user/content)
# 3. Drop old unique index
# 4. Create new unique index
# 5. Update constraint name
```

### Files That Need Modification

1. `/data/data/com.termux/files/home/repos/adminpro/bot/database/models.py` - Line 823: Change unique constraint
2. `/data/data/com.termux/files/home/repos/adminpro/bot/services/reaction.py` - Lines 139-165: Remove emoji from duplicate check
3. `/data/data/com.termux/files/home/repos/adminpro/bot/handlers/user/reactions.py` - Line 154: Update error message
4. **NEW FILE**: Migration script for existing database instances

### Impact Assessment

**Breaking Changes:**
- Existing data with multiple reactions per user/content will violate new constraint
- Database migration is non-optional

**Behavior Changes:**
- Users can no longer react with multiple emojis to same message
- Only first reaction is preserved
- Subsequent reactions return "duplicate" error

**No Impact On:**
- Rate limiting (still works per user)
- Daily limits (still count total reactions)
- Besitos earning (still earned on first reaction only)
- Content reaction counts (aggregations still work)
