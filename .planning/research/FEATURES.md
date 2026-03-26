# Feature Research: Gamification System

**Domain:** Virtual Currency & Engagement Gamification for Telegram Bot
**Researched:** 2026-02-08
**Confidence:** MEDIUM (based on established gamification patterns + existing codebase analysis)

## Feature Landscape

### Table Stakes (Users Expect These)

Features essential for any gamification system. Missing these = economy feels broken or unfair.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Virtual currency balance** | Users need to see their "besitos" balance clearly | LOW | Display in menu, profile. Core to economy. |
| **Currency earning methods** | Users must know HOW to earn currency | LOW | Reactions, daily gift, streaks. Clear rules. |
| **Currency spending (shop)** | Economy needs a sink or it's meaningless | MEDIUM | Content packages, VIP benefits. Core loop. |
| **Transaction history** | Users want to track where currency came/went | MEDIUM | Audit trail prevents disputes, builds trust. |
| **Daily gift with cooldown** | Standard retention mechanic in gamification | LOW | 24h cooldown, clear claim button. Expected. |
| **Streak system** | Rewards consistent engagement | MEDIUM | Daily consecutive logins, bonus scaling. Standard. |
| **Reaction buttons on content** | Simple engagement mechanic | LOW | Inline buttons (❤️🔥💋😈) on channel posts. |
| **Level/progress indicator** | Users want to see their standing | LOW | XP bar, level number, progress to next. |
| **Shop with purchasable items** | Core economy sink | MEDIUM | Content packages, VIP extensions, perks. |
| **Anti-farming protections** | Prevent abuse of earning mechanics | MEDIUM | Rate limits, duplicate detection, cooldowns. |

### Differentiators (Competitive Advantage)

Features that make the gamification system engaging and unique.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **"Besitos" as soft currency** | Branded currency creates emotional connection | LOW | Cute name fits Diana's voice (🫦). Memorable. |
| **Reaction-to-currency conversion** | Engagement directly rewarded | LOW | Each reaction type = different besito value. |
| **Streak recovery (one-time)** | Compassion for broken streaks increases retention | MEDIUM | One "save" per user, premium or limited use. |
| **Level-based shop discounts** | Higher levels get better prices | LOW | Incentive to engage long-term. Progressive reward. |
| **VIP-only shop items** | Creates aspiration for VIP status | LOW | Exclusive content, perks visible but locked. |
| **Achievement/achievement system** | Recognition beyond currency | HIGH | Configurable conditions, badges, notifications. |
| **Seasonal events (2x besitos)** | Time-limited engagement spikes | LOW | Weekend events, holiday bonuses. Easy wins. |
| **Leaderboard (opt-in)** | Social competition drives engagement | MEDIUM | Top besitos earners, weekly reset. Privacy-aware. |
| **Currency gifting between users** | Social economy layer | HIGH | Transfer besitos, promotes community. Abuse risk. |
| **"Besitos multiplier" for VIPs** | VIP status enhances gamification | LOW | 2x besitos from all sources. VIP value-add. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Real money → besitos conversion IN bot** | "Seamless purchase experience" | Violates Telegram ToS for bots, payment processing complexity, tax implications | External payment (manual), then admin grants besitos |
| **Gambling/lottery with besitos** | "Fun random rewards!" | Regulatory issues, addiction concerns, perceived unfairness | Guaranteed rewards, choice-based purchases |
| **Trading besitos for real money** | "Cash out option!" | Creates regulatory nightmare, money transmission laws | Non-convertible currency, only in-ecosystem value |
| **Unlimited streaks without cap** | "Reward forever loyalty!" | Numbers get absurd, diminishing returns, database bloat | Cap at 30/60/90 days, reset or convert to badge |
| **Automated besitos farming detection** | "Stop cheaters!" | Complex ML, false positives harm legitimate users | Rate limits + manual review for suspicious patterns |
| **Currency inflation (unlimited supply)** | "Everyone gets rich!" | Devalues currency, economy collapses, shop prices must inflate | Controlled supply, sinks match sources, periodic rebalancing |
| **NFT/blockchain integration** | "Web3 is the future!" | Massive complexity, user friction, environmental concerns | Simple database-backed currency |
| **Cross-bot besitos transfer** | "Use currency everywhere!" | Technical complexity, abuse vector, dilutes brand | Self-contained economy, export history only |

## Feature Dependencies

```
[Virtual Currency System]
    └──requires──> [User Model Extension]
                       └──requires──> [Existing User Model]

[Daily Gift System]
    └──requires──> [Currency Service]
    └──requires──> [Streak Tracking Model]
    └──enhances──> [Retention Metrics]

[Reaction System]
    └──requires──> [Channel Message Handler]
    └──requires──> [Currency Service]
    └──uses──> [Existing Reaction Config (BotConfig.vip_reactions)]

[Shop System]
    └──requires──> [Currency Service]
    └──requires──> [Content Package Model (existing)]
    └──requires──> [VIP Subscription Service (existing)]
    └──conflicts──> [Direct Content Purchase with Real Money]

[Level System]
    └──requires──> [XP/Currency Accumulation]
    └──requires──> [Level Config (thresholds, rewards)]
    └──enhances──> [Shop System (level-based discounts)]

[Achievement System]
    └──requires──> [Event Tracking System]
    └──requires──> [Achievement Config Model]
    └──enhances──> [Engagement Metrics]

[Admin Configuration]
    └──requires──> [Cascading Config Pattern]
    └──uses──> [Existing ConfigService Pattern]
    └──replaces──> [Fragmented Config Files]
```

### Dependency Notes

- **Currency System requires User Model Extension:** Need to add `besitos_balance`, `total_earned`, `total_spent` to User model or create UserEconomy model.
- **Daily Gift requires Streak Tracking:** Need `UserStreak` model with `current_streak`, `last_claim_date`, `longest_streak`.
- **Reaction System uses existing config:** BotConfig already has `vip_reactions` and `free_reactions` - extend with currency values.
- **Shop integrates with existing ContentPackage:** Content packages already exist - add `besitos_price` field.
- **Level System builds on currency:** Total lifetime besitos earned = XP. Levels at thresholds (100, 250, 500, etc.).
- **Achievement System is complex:** Requires event emission, condition evaluation, reward distribution. Defer to v2 unless core requirement.
- **Admin Configuration must cascade:** One screen configures reactions → earning values → shop items → levels. No fragmentation.

## MVP Definition

### Launch With (v1 Gamification Core) — Essential Economy

Minimum viable gamification system with working economy loop.

- [ ] **User Economy Model** — `besitos_balance`, `total_earned`, `total_spent`, `xp_total`
- [ ] **Currency Service** — Add/subtract/query besitos with transaction logging
- [ ] **Daily Gift Handler** — Claim button, 24h cooldown, streak tracking
- [ ] **Reaction Earning System** — Click reaction → earn besitos (values configurable)
- [ ] **Basic Shop** — List content packages with besitos prices, purchase flow
- [ ] **Level Display** — Show current level based on total XP (besitos earned)
- [ ] **Transaction History** — Last 20 transactions, earn/spend audit trail
- [ ] **Admin Economy Panel** — Configure earning values, shop items, level thresholds

**Rationale:** These establish the core economy loop. Users earn besitos (reactions, daily), spend besitos (shop), progress (levels). Admin can tune the economy.

### Add After Validation (v1.x) — Enhanced Engagement

Features to add once core economy is working and balanced.

- [ ] **Streak Recovery** — One-time "save" for broken streak (costs besitos or watch ad)
- [ ] **VIP Besitos Multiplier** — 2x earnings for VIP subscribers
- [ ] **Seasonal Events** — Weekend 2x besitos, holiday bonuses
- [ ] **Level-Based Shop Discounts** — Higher levels get X% off
- [ ] **Leaderboard (opt-in)** — Weekly top earners, privacy-respecting
- [ ] **Achievement Badges (simple)** — First purchase, 7-day streak, etc.

**Trigger for adding:** When daily active users stabilize and economy metrics (earning vs spending rates) are understood.

### Future Consideration (v2+) — Advanced Gamification

Features to defer until economy is proven and user base is engaged.

- [ ] **Configurable Achievement System** — Admin-defined conditions and rewards
- [ ] **Currency Gifting** — Users can send besitos to each other
- [ ] **Shop Rotations** — Limited-time items, flash sales
- [ ] **Quests/Missions** — Time-limited challenges for bonus besitos
- [ ] **Guild/Team System** — Group competitions, shared goals
- [ ] **Economy Analytics Dashboard** — Sink vs source rates, inflation tracking

**Why defer:** These add complexity without validating core value (engagement through virtual economy). Build after earning/spending patterns are understood.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Risk Level |
|---------|------------|---------------------|----------|------------|
| User Economy Model | CRITICAL | LOW | **P0** | Low - extends existing User |
| Currency Service | CRITICAL | LOW | **P0** | Low - standard CRUD pattern |
| Daily Gift Handler | HIGH | LOW | **P0** | Low - cooldown pattern exists |
| Reaction Earning System | HIGH | LOW | **P0** | Low - extends existing reactions |
| Basic Shop | HIGH | MEDIUM | **P0** | Medium - purchase flow, inventory |
| Level Display | MEDIUM | LOW | **P1** | Low - calculated field |
| Transaction History | MEDIUM | MEDIUM | **P1** | Low - audit table pattern |
| Admin Economy Panel | HIGH | MEDIUM | **P1** | Medium - cascading config UI |
| Streak Recovery | MEDIUM | MEDIUM | **P2** | Medium - one-time flag logic |
| VIP Besitos Multiplier | MEDIUM | LOW | **P2** | Low - conditional multiplier |
| Seasonal Events | MEDIUM | LOW | **P2** | Low - time-based flags |
| Level-Based Discounts | LOW | LOW | **P2** | Low - formula adjustment |
| Leaderboard | LOW | MEDIUM | **P3** | Medium - aggregation query |
| Achievement Badges | LOW | HIGH | **P3** | High - event system, conditions |
| Currency Gifting | LOW | HIGH | **P3** | High - abuse prevention, transfers |

**Priority key:**
- **P0**: Must have for v1 gamification — Core economy loop
- **P1**: Should have for v1.1 — Admin control and trust features
- **P2**: Nice to have, v1.2 — Enhanced engagement
- **P3**: Future consideration — Advanced features

## Economy Design Principles

### Currency Flow (Sources and Sinks)

```
SOURCES (Besitos Entering Economy):
├── Reactions on channel content
│   ├── ❤️ Heart = 1 besito
│   ├── 🔥 Fire = 2 besitos (VIP only)
│   ├── 💋 Kiss = 1 besito
│   └── 😈 Devil = 3 besitos (VIP only)
├── Daily Gift
│   ├── Base: 10 besitos
│   └── Streak bonus: +1 per day (max +7)
├── Achievements (future)
│   └── One-time rewards for milestones
└── Admin grants (manual)
    └── Support, compensation, contests

SINKS (Besitos Leaving Economy):
├── Shop purchases
│   ├── Content packages: 50-500 besitos
│   ├── VIP time extension: 1000 besitos
│   └── Exclusive perks: variable
├── Streak recovery (future)
│   └── 50 besitos to restore broken streak
└── Currency sinks (rebalancing)
    └── Periodic shop items that destroy currency
```

### Level Thresholds (Recommended)

| Level | Total Besitos Earned | Reward |
|-------|---------------------|--------|
| 1 | 0 | Starting level |
| 2 | 100 | Shop discount 5% |
| 3 | 250 | Shop discount 10% |
| 4 | 500 | Shop discount 15% |
| 5 | 1000 | VIP day (1 day free) |
| 6 | 2000 | Shop discount 20% |
| 7+ | +2000 per level | Badge + bragging rights |

### Anti-Farming Measures

| Risk | Mitigation |
|------|------------|
| Reaction spam | Max 1 reaction per message per user; reactions only count on messages < 24h old |
| Daily gift abuse | 24h cooldown from last claim, not calendar day; timezone-aware |
| Streak manipulation | Streak breaks if > 48h between claims; no backdating |
| Shop exploit | Purchases are final; no refunds except admin intervention |
| Multi-account | Device/IP tracking (basic); focus on engagement quality over quantity |

## Competitor/Reference Analysis

Examined patterns from gaming and bot economies:

| Feature | Discord Bots | Mobile Games | Our Approach (Gamification) |
|---------|--------------|--------------|----------------------------|
| **Virtual Currency** | "Points", "credits" | Gems, coins, tokens | **"Besitos"** — Branded, fits voice |
| **Daily Rewards** | Fixed amount | Increasing with streak | **Streak-scaling** — Rewards consistency |
| **Engagement Rewards** | Message count | Ad watches, sessions | **Reactions** — Low friction, content-aligned |
| **Shop Items** | Roles, cosmetics | Power-ups, cosmetics | **Content + VIP time** — Value-aligned |
| **Level System** | XP from activity | XP from everything | **Besitos earned = XP** — Unified metric |
| **Anti-Farming** | Rate limits | CAPTCHA, detection | **Time windows + deduplication** — Simple, effective |

**Key Differentiator:** Most systems separate "points" from "currency". Our approach unifies them: **total besitos earned = XP = level progress**. This simplifies mental model: "Everything I earn progresses me."

## Database Schema Additions

### New Models Required

```python
class UserEconomy(Base):
    """Extends User with gamification data."""
    user_id = FK(User)
    besitos_balance = Integer(default=0)
    total_earned = Integer(default=0)  # XP source
    total_spent = Integer(default=0)
    current_level = Integer(default=1)

class UserStreak(Base):
    """Daily gift streak tracking."""
    user_id = FK(User)
    current_streak = Integer(default=0)
    longest_streak = Integer(default=0)
    last_claim_date = DateTime
    recovery_used = Boolean(default=False)

class Transaction(Base):
    """Audit trail for all currency movements."""
    user_id = FK(User)
    amount = Integer  # positive = earn, negative = spend
    type = Enum(EARN_REACTION, EARN_DAILY, EARN_STREAK, SPEND_SHOP, ADMIN_GRANT)
    description = String
    created_at = DateTime

class ShopItem(Base):
    """Items available for purchase with besitos."""
    name = String
    description = String
    besitos_price = Integer
    item_type = Enum(CONTENT_PACKAGE, VIP_EXTENSION, PERK)
    reference_id = Integer  # FK to content package, etc.
    stock = Integer(nullable=True)  # NULL = unlimited
    is_active = Boolean(default=True)

class LevelConfig(Base):
    """Level thresholds and rewards."""
    level = Integer(primary_key)
    xp_required = Integer  # Total besitos earned needed
    reward_type = Enum(DISCOUNT, VIP_TIME, BADGE)
    reward_value = String  # JSON or scalar
```

## Feature Implementation Order

### Order by Dependency and Risk

1. **UserEconomy Model** (LOW risk, no dependencies)
   - Foundation for all gamification
   - Simple model extension
   - Migration: Add table, backfill zeros

2. **Currency Service** (LOW risk, depends on UserEconomy)
   - Core service for all economy operations
   - Methods: earn(), spend(), get_balance()
   - Integrates with ServiceContainer

3. **Transaction Model** (LOW risk, depends on Currency Service)
   - Audit trail
   - Simple append-only table
   - Enables history feature

4. **Daily Gift Handler** (LOW risk, depends on Currency Service)
   - Claim command/button
   - Cooldown check
   - Streak calculation

5. **UserStreak Model** (LOW risk, depends on Daily Gift)
   - Streak tracking
   - Can be built parallel with Daily Gift

6. **Reaction Earning System** (MEDIUM risk, depends on Currency Service)
   - Callback handler for reactions
   - Rate limiting
   - Integration with existing reaction config

7. **ShopItem Model** (LOW risk, no dependencies)
   - Shop inventory
   - Can be populated via admin

8. **Shop Handler** (MEDIUM risk, depends on ShopItem + Currency Service)
   - Browse items
   - Purchase flow
   - Inventory management

9. **Level System** (LOW risk, depends on UserEconomy)
   - Calculate level from total_earned
   - Display progress
   - Level-up notifications

10. **LevelConfig Model** (LOW risk, depends on Level System)
    - Thresholds and rewards
    - Admin configurable

11. **Admin Economy Panel** (MEDIUM risk, depends on all above)
    - Cascading configuration
    - Economy tuning
    - Transaction monitoring

12. **Achievement System** (HIGH risk, depends on Event System)
    - Event emission framework
    - Condition evaluation
    - Reward distribution
    - **Defer to v2 unless critical**

## Feature Risk Assessment

| Feature | Risk Type | Mitigation |
|---------|-----------|------------|
| Currency balance accuracy | Data integrity | Database transactions, audit trail, reconciliation job |
| Economy inflation | Balance | Monitor earn/spend ratio, adjust values, add sinks |
| User confusion | UX | Clear earning rules, visible progress, help command |
| Admin misconfiguration | Operational | Sensible defaults, validation, preview mode |
| Reaction farming | Abuse | Time windows, deduplication, rate limits |
| Streak timezone issues | Technical | Store UTC, display local, 48h grace period |
| Shop purchase disputes | Support | Clear "no refunds" policy, transaction history |
| Level calculation performance | Performance | Cache level, recalculate on earn only |
| Achievement complexity | Technical | Start with hardcoded, build config system later |

## Integration with Existing Features

| Existing Feature | Gamification Integration |
|------------------|-------------------------|
| **VIP Subscription** | Besitos multiplier, shop items for VIP extension, VIP-only shop section |
| **Content Packages** | Besitos pricing, "purchased" state, unlock via currency |
| **Reaction System** | Earning source, values configurable per reaction type |
| **Free Channel** | Daily gift reminder in Free menu, engagement before VIP |
| **Admin Panel** | Cascading config for all economy settings |
| **Interest System** | Bonus besitos for expressing interest (future) |

## Voice Architecture Integration

| Context | Voice | Usage |
|---------|-------|-------|
| Daily Gift (claim) | Diana (🫦) | "Toma tus besitos, cariño..." |
| Shop browsing | Diana (🫦) | "Mira lo que tengo para ti..." |
| Level up | Diana (🫦) | "Subiste de nivel... mereces más." |
| Transaction success | Diana (🫦) | "Hecho. Disfruta." |
| Economy admin | Lucien (🎩) | Configuration, stats, reports |
| Error/insufficient funds | Lucien (🎩) | "No tiene fondos suficientes..." |

## Sources

**Gamification Design Patterns:**
- [Octalysis Framework](https://yukaichou.com/gamification-examples/octalysis-complete-gamification-framework/) — Core drives for engagement (MEDIUM confidence)
- [Virtual Economy Design](https://www.gamasutra.com/view/feature/134608/designing_virtual_economies.php) — Currency flow principles (MEDIUM confidence)
- [Mobile Game Retention](https://www.gamedeveloper.com/design/retention-and-monetization-mechanics) — Daily rewards, streaks (MEDIUM confidence)

**Telegram Bot Patterns:**
- [aiogram CallbackQuery Handling](https://docs.aiogram.dev/en/latest/dispatcher/filters/callback_query.html) — Reaction buttons (HIGH confidence)
- [Telegram Inline Keyboards](https://core.telegram.org/bots/api#inlinekeyboardmarkup) — Shop UI (HIGH confidence)

**Existing Codebase:**
- `/data/data/com.termux/files/home/repos/adminpro/bot/database/models.py` — User, ContentPackage models (HIGH confidence)
- `/data/data/com.termux/files/home/repos/adminpro/bot/services/container.py` — Service architecture (HIGH confidence)
- `/data/data/com.termux/files/home/repos/adminpro/bot/database/models.py` — BotConfig reactions config (HIGH confidence)

---

*Feature research for: Gamification System (v1.4)*
*Researched: 2026-02-08*
*Confidence: MEDIUM — Based on established gamification patterns + existing codebase analysis*
