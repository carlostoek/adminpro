# Pitfalls Research: Adding Gamification to Telegram Bot

**Domain:** Virtual Currency Economy + Gamification in Existing Subscription Bot
**Researched:** 2026-02-08
**Confidence:** HIGH (based on established patterns in virtual economies and Telegram bot architecture)

## Executive Summary

Adding gamification (virtual currency "besitos", reactions, streaks, shop) to an existing VIP/Free subscription bot introduces unique integration risks. The existing system has well-defined roles (FREE/VIP/ADMIN), subscription lifecycle, and database models. Gamification must integrate without destabilizing these foundations.

**Key Risk:** Economy inflation/deflation, exploit vectors through reaction tracking, streak calculation edge cases, and database performance degradation under high-volume transactions. The "cascading" admin UI for reward conditions is particularly vulnerable to logic errors and UX fragmentation.

---

## Critical Pitfalls

### Pitfall 1: Economy Inflation/Deflation (The "Besitos" Death Spiral)

**What goes wrong:**
The virtual currency "besitos" becomes worthless (inflation) or too scarce (deflation), making the gamification system meaningless:

```python
# BAD: No sinks, only faucets - users accumulate infinite besitos
async def give_daily_reward(user_id: int):
    user.besitos += 10  # Faucet: +10 daily
    # No sink: nothing to spend on except expensive shop items

# Result: After 100 days, user has 1000 besitos, shop items cost 50
# Economy is broken - no meaningful choices
```

Or the opposite:
```python
# BAD: Too expensive, no way to earn enough
async def give_daily_reward(user_id: int):
    user.besitos += 1  # Too scarce

# Shop items cost 500 besitos
# User needs 500 days to afford anything - abandonment
```

**Why it happens:**
- No economic modeling (faucets vs sinks balance)
- Shop prices set arbitrarily without earning rate analysis
- Daily rewards not tuned to desired engagement frequency
- No "soft sink" mechanisms (small recurring costs)
- Admin can create reward conditions that flood economy

**How to avoid:**
1. **Define target metrics:** "User should afford 1 shop item per week with daily engagement"
2. **Calculate faucet rate:** Daily reward + average reaction earnings = weekly income
3. **Price shop items:** Tiered pricing (small: 3 days, medium: 1 week, large: 2 weeks)
4. **Implement soft sinks:** Optional cosmetic purchases, streak insurance, reaction boosts
5. **Admin economy controls:** Max besitos per reward condition, warnings for high-value rewards
6. **Monitor M0 money supply:** Track total besitos in circulation vs user count

```python
# GOOD: Economy with balanced faucets and sinks
class EconomyConfig:
    # Faucets (sources)
    DAILY_REWARD_BASE = 5
    DAILY_REWARD_STREAK_BONUS = 1  # +1 per streak day, max +5
    REACTION_REWARD = 1  # Per reaction given

    # Sinks (uses)
    SHOP_SMALL_PRICE = 15    # 3 days of daily
    SHOP_MEDIUM_PRICE = 35   # 1 week of daily
    SHOP_LARGE_PRICE = 70    # 2 weeks of daily

    # Soft sinks
    STREAK_INSURANCE_COST = 10  # Protect streak for 1 day
    REACTION_BOOST_COST = 5     # Double reaction value for 24h

async def get_weekly_earning_potential() -> int:
    """Calculate max besitos earnable per week for pricing decisions."""
    daily_max = EconomyConfig.DAILY_REWARD_BASE + EconomyConfig.DAILY_REWARD_STREAK_BONUS
    weekly_from_daily = daily_max * 7
    weekly_from_reactions = EconomyConfig.REACTION_REWARD * 10  # Assume 10 reactions/week
    return weekly_from_daily + weekly_from_reactions
```

**Warning signs:**
- Average user balance grows >20% week-over-week (inflation)
- <5% of users can afford cheapest shop item (deflation)
- Shop purchase rate <1% per active user per week
- Admin creates reward conditions giving 100+ besitos

**Phase to address:** Phase 1 (Economy Design) - Define faucet/sink rates before implementing features

**Impact if ignored:** CRITICAL - Entire gamification system becomes meaningless, user abandonment

---

### Pitfall 2: Reaction Tracking Exploits (The "Button Masher" Problem)

**What goes wrong:**
Users exploit the reaction system (inline buttons) to farm besitos:

```python
# BAD: No rate limiting, no deduplication
@router.callback_query(F.data.startswith("react:"))
async def handle_reaction(callback: CallbackQuery):
    content_id = int(callback.data.split(":")[1])

    # User can click same reaction 100 times
    await add_besitos(callback.from_user.id, 1)
    await callback.answer("+1 besito!")

# Exploit: Script to click reaction 1000 times = 1000 besitos
```

Or:
```python
# BAD: No verification user actually viewed content
async def handle_reaction(callback: CallbackQuery):
    # User can react to content without seeing it
    # (just by knowing the callback_data pattern)
    await add_besitos(callback.from_user.id, 1)
```

**Why it happens:**
- Reactions tracked via inline buttons without session validation
- No rate limiting per user per content
- No verification that user has access to content being reacted to
- Reaction rewards processed synchronously (can be spammed)
- No unique constraint on (user_id, content_id, reaction_type)

**How to avoid:**
1. **Deduplicate reactions:** One reward per (user, content, reaction_type)
2. **Rate limit:** Max 1 reaction per minute per user globally
3. **Validate access:** Verify user can view content before rewarding
4. **Async processing:** Queue reaction rewards, process in background
5. **Anomaly detection:** Flag users with >20 reactions per hour for review

```python
# GOOD: Secure reaction tracking
class ReactionService:
    async def process_reaction(
        self,
        user_id: int,
        content_id: int,
        reaction_type: str
    ) -> Tuple[bool, str]:
        # 1. Verify user has access to content
        if not await self.user_can_access_content(user_id, content_id):
            return False, "No access to content"

        # 2. Check for duplicate (user, content, type)
        existing = await self.session.execute(
            select(UserReaction).where(
                UserReaction.user_id == user_id,
                UserReaction.content_id == content_id,
                UserReaction.reaction_type == reaction_type
            )
        )
        if existing.scalar_one_or_none():
            return False, "Already reacted"

        # 3. Rate limit check (1 reaction per 30 seconds)
        recent = await self.session.execute(
            select(UserReaction).where(
                UserReaction.user_id == user_id,
                UserReaction.created_at > datetime.utcnow() - timedelta(seconds=30)
            )
        )
        if recent.scalars().first():
            return False, "Too fast - slow down!"

        # 4. Record reaction (reward processed async)
        reaction = UserReaction(
            user_id=user_id,
            content_id=content_id,
            reaction_type=reaction_type,
            reward_pending=True  # Processed by background task
        )
        self.session.add(reaction)
        await self.session.commit()

        return True, "Reaction recorded!"

# Background task processes rewards with batching
async def process_pending_reaction_rewards():
    pending = await get_pending_reactions(limit=100)
    for reaction in pending:
        await add_besitos(reaction.user_id, REACTION_REWARD)
        reaction.reward_pending = False
    await session.commit()
```

**Warning signs:**
- User with >50 reactions in 1 hour
- Reaction pattern shows robotic timing (every 1.0 seconds exactly)
- User reacting to content they don't have access to
- Database table `user_reactions` growing faster than `content_views`

**Phase to address:** Phase 2 (Reaction System) - Design with security from start

**Impact if ignored:** HIGH - Economy flooded with illegitimate currency, legitimate users disadvantaged

---

### Pitfall 3: Streak Calculation Edge Cases (The "Timezone Hell")

**What goes wrong:**
Streaks break in unexpected ways due to timezone, daylight saving, or edge cases:

```python
# BAD: Naive streak calculation
async def check_streak(user_id: int):
    user = await get_user(user_id)
    last_claim = user.last_daily_claim

    # This breaks across midnight, DST, timezone changes
    if last_claim.date() == datetime.utcnow().date() - timedelta(days=1):
        user.streak += 1
    else:
        user.streak = 1  # Reset - WRONG if same day claim
```

Problems:
- User claims at 23:59 UTC, then 00:01 UTC next day = streak reset (should continue)
- User travels, timezone changes = streak behavior unpredictable
- Daylight saving time shift = duplicate or missing day
- User claims at 23:59 local time (but UTC is next day) = confusion

**Why it happens:**
- Using UTC for user-facing daily boundaries
- No grace period for "same day" claims across midnight
- Not storing timezone per user
- Edge case: claiming twice in same calendar day (should be blocked)
- Edge case: missing exactly one day (should reset, but users expect grace)

**How to avoid:**
1. **Store user timezone:** Default to UTC, allow override
2. **Define "day":** 00:00-23:59 in user's local timezone
3. **Grace period:** Allow claim within 6 hours of previous claim to maintain streak
4. **Idempotent claims:** Same-day claim returns "already claimed" not error
5. **Visual clarity:** Show "next claim available in X hours" not just date

```python
# GOOD: Robust streak calculation
class StreakService:
    GRACE_PERIOD_HOURS = 6  # Claim within 6h of previous to maintain streak

    async def process_daily_claim(self, user_id: int) -> Dict[str, any]:
        user = await self.get_user(user_id)
        now = datetime.utcnow()
        user_tz = pytz.timezone(user.timezone or 'UTC')
        now_local = now.astimezone(user_tz)

        # Check if already claimed today (local time)
        if user.last_daily_claim:
            last_claim_local = user.last_daily_claim.astimezone(user_tz)
            if last_claim_local.date() == now_local.date():
                return {
                    "success": False,
                    "reason": "already_claimed",
                    "next_claim_at": self._get_next_midnight(user_tz)
                }

        # Calculate streak
        streak = user.streak or 0
        if user.last_daily_claim:
            hours_since = (now - user.last_daily_claim).total_seconds() / 3600

            if hours_since <= 24 + self.GRACE_PERIOD_HOURS:
                # Within grace period - continue streak
                streak += 1
            elif hours_since <= 48:
                # Missed one day exactly - reset (or use streak insurance)
                streak = 1
            else:
                # Missed multiple days - reset
                streak = 1
        else:
            streak = 1

        # Calculate reward with streak bonus
        base_reward = EconomyConfig.DAILY_REWARD_BASE
        streak_bonus = min(streak - 1, 5)  # Max +5 for streak
        total_reward = base_reward + streak_bonus

        # Update user
        user.besitos += total_reward
        user.streak = streak
        user.last_daily_claim = now
        await self.session.commit()

        return {
            "success": True,
            "reward": total_reward,
            "streak": streak,
            "streak_bonus": streak_bonus
        }
```

**Warning signs:**
- Users complaining about streak resets they didn't expect
- Support tickets: "I claimed daily but streak reset"
- Streaks >100 days (possible but suspicious without grace period)
- Duplicate claims on same day (database constraint missing)

**Phase to address:** Phase 3 (Daily Rewards) - Design streak logic with edge cases

**Impact if ignored:** HIGH - User frustration, loss of engagement, support burden

---

### Pitfall 4: Database Performance Collapse (The "Transaction Avalanche")

**What goes wrong:**
High-frequency gamification transactions overwhelm SQLite (or even PostgreSQL):

```python
# BAD: Synchronous transaction per reaction
@router.callback_query(F.data.startswith("react:"))
async def handle_reaction(callback: CallbackQuery, session: AsyncSession):
    # Each reaction = one transaction
    await add_besitos(session, user_id, 1)  # UPDATE users SET besitos = besitos + 1
    await add_reaction_record(session, user_id, content_id)  # INSERT
    await session.commit()  # SYNC WRITE - blocks other operations

# With 100 concurrent users clicking reactions:
# - 100 concurrent transactions
# - SQLite WAL mode helps but still serializes writes
# - Response time: 500ms+ per reaction
```

**Why it happens:**
- SQLite WAL mode has limits (concurrent readers, single writer)
- Each gamification action = immediate database write
- No batching of small transactions
- No read replicas for balance queries
- Missing indexes on (user_id, created_at) for reaction lookups

**How to avoid:**
1. **Batch writes:** Accumulate rewards, flush every 10 seconds
2. **In-memory counters:** Use Redis/caching for hot paths, persist periodically
3. **Background processing:** Queue rewards, process async
4. **Proper indexing:** Index all gamification query patterns
5. **Connection pooling:** For PostgreSQL; connection limits for SQLite

```python
# GOOD: Batched transaction approach
class BesitosLedger:
    """Accumulate changes, flush periodically."""

    def __init__(self):
        self._pending: Dict[int, int] = {}  # user_id -> delta
        self._last_flush = datetime.utcnow()

    def add(self, user_id: int, delta: int):
        self._pending[user_id] = self._pending.get(user_id, 0) + delta

        # Flush if accumulated enough or time elapsed
        if (len(self._pending) >= 50 or
            (datetime.utcnow() - self._last_flush).seconds > 10):
            asyncio.create_task(self._flush())

    async def _flush(self):
        if not self._pending:
            return

        pending = self._pending.copy()
        self._pending.clear()
        self._last_flush = datetime.utcnow()

        async with get_session() as session:
            for user_id, delta in pending.items():
                await session.execute(
                    update(User)
                    .where(User.user_id == user_id)
                    .values(besitos=User.besitos + delta)
                )
            await session.commit()

# Usage in handlers - non-blocking
ledger = BesitosLedger()

@router.callback_query(F.data.startswith("react:"))
async def handle_reaction(callback: CallbackQuery):
    # Fast - just add to in-memory ledger
    ledger.add(callback.from_user.id, 1)
    await callback.answer("+1 besito!")
```

**Warning signs:**
- Reaction handler latency >200ms
- "Database is locked" errors (SQLite)
- Connection pool exhaustion (PostgreSQL)
- CPU usage spikes during peak activity

**Phase to address:** Phase 2 (Reaction System) + Phase 4 (Shop) - Design for write throughput

**Impact if ignored:** CRITICAL - Bot becomes unresponsive, timeouts, data corruption

---

### Pitfall 5: Cascading Reward Logic Errors (The "Admin Footgun")

**What goes wrong:**
The "cascading" admin UI for reward conditions creates complex logic that's hard to validate:

```python
# BAD: Nested conditions with ambiguous evaluation
class RewardCondition:
    if_role = "VIP"  # AND
    if_streak_min = 7  # AND
    if_content_reacted = [1, 2, 3]  # OR within list?
    # What does this mean?
    # (role=VIP AND streak>=7 AND (reacted_to_1 OR reacted_to_2 OR reacted_to_3))?
    # Or all conditions must be met including ALL reactions?

# Admin creates condition:
# "Give 100 besitos if VIP AND streak>7"
# But also creates:
# "Give 50 besitos if streak>7"
# Result: VIP with streak>7 gets 150 besitos - intended?
```

**Why it happens:**
- No clear semantics for AND vs OR in condition lists
- Multiple matching conditions stack (unintended compound rewards)
- No validation that conditions are achievable
- No preview/test mode for conditions
- UI shows conditions but not "effective reward" calculation

**How to avoid:**
1. **Explicit condition types:** AND group, OR group, NOT
2. **Single evaluation path:** Conditions evaluated in priority order, first match wins
3. **Preview mode:** Admin can test condition against any user
4. **Conflict detection:** Warn if multiple conditions match same scenario
5. **Reward caps:** Max besitos per action regardless of conditions matched

```python
# GOOD: Explicit condition evaluation with priority
class RewardRule:
    """Single rule with clear semantics."""
    priority: int  # Lower = evaluated first
    conditions: List[Condition]  # All must match (AND)
    reward_besitos: int
    max_applications_per_user: int = 1  # Prevent farming

class Condition:
    type: ConditionType  # ROLE, STREAK_MIN, STREAK_MAX, CONTENT_REACTED, etc.
    operator: Operator   # EQ, NEQ, GT, LT, IN, NOT_IN
    value: Any

class RewardEngine:
    async def evaluate_rules(self, user_id: int, context: RewardContext) -> int:
        """Evaluate all rules, return total reward (with cap)."""
        user = await self.get_user(user_id)
        total_reward = 0
        applied_rules = []

        # Sort by priority
        rules = sorted(await self.get_active_rules(), key=lambda r: r.priority)

        for rule in rules:
            if await self._rule_matches(rule, user, context):
                # Check max applications
                applications = await self._count_rule_applications(rule.id, user_id)
                if applications < rule.max_applications_per_user:
                    total_reward += rule.reward_besitos
                    applied_rules.append(rule)

                    # Hard cap per action
                    if total_reward >= 100:  # Max 100 besitos per action
                        logger.warning(f"Reward cap hit for user {user_id}")
                        break

        return min(total_reward, 100)  # Absolute cap

    async def _rule_matches(self, rule: RewardRule, user: User, context: RewardContext) -> bool:
        """All conditions must match (AND semantics)."""
        for condition in rule.conditions:
            if not await self._evaluate_condition(condition, user, context):
                return False
        return True
```

**Warning signs:**
- Admin confusion: "Why did this user get 500 besitos?"
- Support tickets about unexpected reward amounts
- Users gaming the system by meeting multiple conditions
- Database table `reward_rule_applications` growing exponentially

**Phase to address:** Phase 5 (Admin Reward Configuration) - Design clear semantics

**Impact if ignored:** HIGH - Economy destabilization, admin distrust of system

---

### Pitfall 6: Admin UX Fragmentation (The "Cascading Confusion")

**What goes wrong:**
Despite the "cascading" goal, admin UX becomes fragmented across multiple menus:

```
Current admin flow (without gamification):
/admin → Content Management → Package List → Package Detail

With gamification added poorly:
/admin → Content Management → Package List → Package Detail
     ↓
   Gamification (separate menu)
     ↓
   Reward Rules (another menu)
     ↓
   Shop Management (another menu)
     ↓
   Economy Stats (yet another menu)

Admin must navigate 4 separate sections to understand full picture
```

**Why it happens:**
- Gamification features added as afterthought (separate menus)
- No unified view of "user journey with economy"
- Shop management separate from content management
- Reward rules not visible from content detail
- Stats scattered across multiple reports

**How to avoid:**
1. **Unified content-economy view:** Content detail shows reactions, rewards, shop status
2. **Contextual reward configuration:** Configure rewards from content management
3. **User 360 view:** See all user data (subscription, besitos, streak, purchases) in one place
4. **Economy dashboard:** Single view of faucets, sinks, circulation

```
GOOD: Cascading admin UX

/admin
  └── Content Management
        ├── Package List
        │     └── Package Detail
        │           ├── Content Info (existing)
        │           ├── Reactions (view counts)
        │           ├── Reward Rules (configure here)
        │           └── Shop Settings (if sellable)
        │
        └── Economy Dashboard
              ├── Circulation Stats
              ├── Active Rules
              └── Recent Purchases

/admin
  └── User Management
        └── User Detail
              ├── Subscription (existing)
              ├── Besitos Balance
              ├── Streak Status
              └── Purchase History
```

**Warning signs:**
- Admin asks "Where do I configure X?" repeatedly
- Need to open 3+ menus to answer "How much is this user worth?"
- Duplicate configuration in multiple places
- Admin bypasses UI, asks dev to "just run a query"

**Phase to address:** Phase 5 (Admin UI) - Design integrated, not fragmented

**Impact if ignored:** MEDIUM - Admin inefficiency, configuration errors, system underutilization

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Immediate DB write on reaction | Simpler code, instant feedback | Performance collapse at scale | Never - always batch or queue |
| No timezone handling for streaks | Simpler datetime logic | User confusion, support tickets | Never - store user timezone |
| Hardcoded shop prices | No admin UI needed | Requires deploy to adjust economy | Only for MVP first week |
| Single reward condition type | Simpler rule engine | Limited flexibility, admin frustration | MVP only, plan for v2 |
| Skip reaction deduplication | Faster handler response | Economy exploits, inflation | Never - security critical |
| Inline reward calculation | No background jobs | Blocking handlers, slow UX | Never - always async |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Existing User model | Add besitos column without default | Default 0, backfill existing users |
| Existing VIPSubscriber | Ignore gamification in subscription lifecycle | Award besitos on VIP signup/renewal |
| ContentPackage | Add gamification fields without migration | Proper Alembic migration for new columns |
| ServiceContainer | Add GamificationService as god object | Split: EconomyService, StreakService, ShopService |
| Daily reward job | Run at fixed UTC time | Respect user timezone, or use "last 24h" logic |
| Shop purchase | Deduct besitos without transaction | Atomic check-and-deduct with balance verification |
| Reaction tracking | Trust callback_data without validation | Verify user can access content, rate limit |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| N+1 queries in user lists | Slow admin user list | Eager load besitos, streak | >100 users |
| Synchronous reward processing | Handler timeouts | Queue rewards, process async | >10 reactions/minute |
| No pagination on transaction history | UI freeze, OOM | Paginate ledger queries | >50 transactions/user |
| Calculating streak on every read | Slow profile load | Cache streak, update on write | >1000 daily active users |
| Unindexed reaction queries | Slow content analytics | Index (content_id, created_at) | >1000 reactions |
| Storing all history forever | DB bloat, slow backups | Archive old transactions | >6 months of data |

**Note:** Termux/SQLite environment has stricter limits. Design for 10x headroom.

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Reaction spoofing | Farm besitos without viewing content | Verify content access before reward |
| Balance manipulation | User sets own besitos count | Server-side only, never trust client |
| Shop price tampering | Buy expensive items for cheap | Server validates price at purchase time |
| Streak freezing | User pauses time to maintain streak | Server-side timestamp only |
| Admin reward abuse | Admin gives unlimited besitos | Log all admin rewards, alerts for >1000 |
| Race condition in purchase | Double-spend besitos | Atomic check-and-deduct transaction |
| Replay attacks | Reuse old purchase confirmations | Unique transaction IDs, idempotent processing |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No visual balance indicator | Users forget currency exists | Show besitos in all menus |
| Streak reset without warning | Frustration, abandonment | "Claim in 2 hours or streak resets" |
| Shop purchase without confirmation | Accidental purchases | Confirm for items >20 besitos |
| Reaction spam feedback | "+1" 50 times = notification spam | Batch: "+10 besitos from reactions" |
| No purchase history | Users don't trust system | Show last 10 transactions |
| Daily reward hidden | Users forget to claim | Prominent "Claim Daily" button |
| Streak bonus unclear | Users don't understand reward | Show breakdown: "5 base + 3 streak bonus" |

---

## "Looks Done But Isn't" Checklist

- [ ] **Daily Rewards:** Streak survives DST transitions and timezone changes
- [ ] **Reactions:** Duplicate clicks don't award multiple besitos
- [ ] **Shop:** Purchase validates balance atomically (no negative balances)
- [ ] **Economy:** Admin can see total besitos in circulation
- [ ] **Streaks:** Grace period works (claim within 6h of previous)
- [ ] **Performance:** 100 concurrent reactions don't lock database
- [ ] **Security:** User can't award themselves besitos via crafted callback
- [ ] **Admin UX:** Configure reward rules from content management screen
- [ ] **Migration:** Existing users have besitos=0, not NULL
- [ ] **Monitoring:** Alert when single user earns >100 besitos in 1 hour

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Economy inflation | HIGH | 1. Audit all besitos sources<br>2. Remove illegitimate balances<br>3. Rebalance shop prices<br>4. Add more sinks |
| Reaction exploit | MEDIUM | 1. Identify exploited users<br>2. Deduct illegitimate besitos<br>3. Add deduplication constraint<br>4. Rate limit going forward |
| Streak calculation bug | MEDIUM | 1. Fix calculation logic<br>2. Recalculate all streaks from history<br>3. Compensate affected users<br>4. Add grace period |
| Database performance | LOW | 1. Add missing indexes<br>2. Implement batching<br>3. Archive old data<br>4. Add caching layer |
| Admin UX fragmentation | HIGH | 1. Map current flows<br>2. Design unified navigation<br>3. Migrate configuration<br>4. Retrain admins |
| Cascading logic errors | MEDIUM | 1. Audit all reward rules<br>2. Fix ambiguous conditions<br>3. Add reward caps<br>4. Notify users of corrections |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Economy Inflation/Deflation | Phase 1 (Economy Design) | Faucet/sink spreadsheet, shop prices justified |
| Reaction Tracking Exploits | Phase 2 (Reaction System) | Unit tests for deduplication, rate limiting |
| Streak Calculation Edge Cases | Phase 3 (Daily Rewards) | Test cases for DST, timezone change, grace period |
| Database Performance | Phase 2 + 4 (Reaction + Shop) | Load test 100 concurrent reactions, <100ms latency |
| Cascading Reward Logic | Phase 5 (Admin Configuration) | Admin can preview rule evaluation for any user |
| Admin UX Fragmentation | Phase 5 (Admin UI) | Navigation flow shows <3 clicks to any gamification feature |

---

## Sources

- Virtual Economy Design Patterns - Game Developer Magazine (HIGH confidence)
- SQLite Performance Best Practices - sqlite.org (HIGH confidence)
- Telegram Bot API Documentation - core.telegram.org (HIGH confidence)
- SQLAlchemy Async Patterns - docs.sqlalchemy.org (HIGH confidence)
- Anti-patterns in Gamification - GDC Vault presentations (MEDIUM confidence)
- Personal experience with bot economy systems (HIGH confidence)

---

*Pitfalls research for: Gamification Milestone (Besitos Economy)*
*Researched: 2026-02-08*
*Confidence: HIGH*
