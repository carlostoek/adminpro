# Project Research Summary

**Project:** Telegram Bot VIP/Free - Gamification Milestone
**Domain:** Virtual currency economy, reaction tracking, daily rewards, streaks, shop system
**Researched:** 2026-02-08
**Confidence:** HIGH

## Executive Summary

The gamification milestone adds a virtual currency economy ("besitos") to the existing VIP/Free Telegram bot. This is a content creator monetization bot where users earn currency through engagement (reactions, daily check-ins, streaks) and spend it in a shop for content packages and VIP perks. Research shows this type of system requires careful economic balancing and robust anti-exploit measures.

The recommended approach leverages the existing aiogram 3.x + SQLAlchemy 2.x stack with no new dependencies. The architecture follows established patterns: ServiceContainer DI for dependency injection, atomic database updates for currency operations, and cascading FSM flows for admin configuration. Key architectural decisions include using atomic `UPDATE SET col = col + delta` patterns for besito transactions (preventing race conditions) and implementing wizard-style FSM states for the "cascading" reward condition configuration requirement.

The primary risks are economy inflation/deflation (if faucet/sink rates aren't balanced), reaction tracking exploits (if deduplication and rate limiting are skipped), and streak calculation edge cases (timezone/DST issues). These can be mitigated through careful economic modeling upfront, strict validation in reaction handlers, and UTC-based streak calculation with grace periods.

## Key Findings

### Recommended Stack

**No new dependencies required.** The existing stack (aiogram 3.4.1+, SQLAlchemy 2.0.25, APScheduler 3.10.4, aiosqlite 0.19.0) handles all gamification requirements. Aiogram's `InlineKeyboardMarkup` with callback_data supports reaction tracking natively. SQLAlchemy's atomic update patterns prevent race conditions in currency operations. APScheduler's CronTrigger handles daily reward reset and streak expiration jobs.

**Core technologies:**
- **aiogram 3.4.1+**: Inline reaction buttons, callback queries — already in use, handles reaction tracking natively
- **SQLAlchemy 2.0.25**: Atomic besito updates, transaction audit — existing ORM with atomic `UPDATE SET col = col + delta` pattern
- **APScheduler 3.10.4**: Daily rewards, streak expiration jobs — already configured in background tasks
- **aiosqlite 0.19.0**: Async SQLite for gamification tables — existing driver with WAL mode for concurrent reads

**What NOT to add:** Redis (overkill for single-bot), external payment processors (scope creep), pydantic (dataclasses sufficient), Celery (APScheduler handles jobs), web dashboard (Telegram admin menus sufficient).

### Expected Features

**Must have (table stakes):**
- Virtual currency balance display — users need to see their "besitos" clearly
- Currency earning methods (reactions, daily gift, streaks) — core economy loop
- Currency spending (shop) — economy needs a sink or it's meaningless
- Transaction history — audit trail prevents disputes, builds trust
- Daily gift with 24h cooldown — standard retention mechanic
- Streak system — rewards consistent engagement
- Reaction buttons on content — simple engagement mechanic
- Level/progress indicator — users want to see their standing
- Anti-farming protections — prevent abuse of earning mechanics

**Should have (competitive):**
- "Besitos" branded currency — creates emotional connection, fits Diana's voice
- Reaction-to-currency conversion — engagement directly rewarded
- Streak recovery (one-time) — compassion for broken streaks increases retention
- Level-based shop discounts — incentive to engage long-term
- VIP-only shop items — creates aspiration for VIP status
- VIP besitos multiplier (2x) — VIP status enhances gamification

**Defer (v2+):**
- Configurable achievement system — complex event system, conditions
- Currency gifting between users — social economy layer, abuse risk
- Leaderboard — social competition, privacy concerns
- Quests/missions — time-limited challenges
- Economy analytics dashboard — sink vs source rates, inflation tracking

### Architecture Approach

The gamification module integrates with the existing Layered Service-Oriented Architecture with Dependency Injection. New services (ReactionService, WalletService, ShopService, RewardService, StreakService) follow the lazy-loading pattern in ServiceContainer. The "cascading" admin requirement is implemented via nested FSM states with state data persistence — allowing admins to create reward conditions inline without leaving the reward creation flow.

**Major components:**
1. **ReactionService** — Track and manage inline button reactions on channel content, hooks into ChannelService
2. **WalletService** — Virtual currency management with atomic transactions and audit trail
3. **ShopService** — Product catalog and purchase processing, links to ContentPackage
4. **RewardService** — Achievement system with configurable conditions using strategy pattern
5. **StreakService** — Daily activity tracking with streak mechanics and background checks

### Critical Pitfalls

1. **Economy Inflation/Deflation** — Virtual currency becomes worthless (too many faucets) or too scarce (too few). *Avoid by:* defining target metrics (user affords 1 shop item per week), calculating faucet/sink rates, implementing soft sinks, monitoring M0 money supply.

2. **Reaction Tracking Exploits** — Users farm besitos by spamming reaction buttons. *Avoid by:* deduplicating reactions (one per user/content/type), rate limiting (1 per 30 seconds), validating content access, async reward processing.

3. **Streak Calculation Edge Cases** — Timezone changes, DST shifts, and midnight boundaries break streaks unexpectedly. *Avoid by:* storing user timezone, defining "day" in local time, 6-hour grace period, idempotent same-day claims.

4. **Database Performance Collapse** — High-frequency gamification transactions overwhelm SQLite. *Avoid by:* batching writes, background processing, proper indexing on (user_id, created_at), connection pooling.

5. **Cascading Reward Logic Errors** — Complex AND/OR conditions create ambiguous evaluation and unintended compound rewards. *Avoid by:* explicit condition types, priority-ordered evaluation, preview mode, reward caps (max 100 besitos per action).

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Economy Foundation
**Rationale:** Database models and core currency service must exist before any gamification features. Economic parameters must be defined before implementation.
**Delivers:** UserEconomy model, WalletService with atomic transactions, Transaction audit table, economy configuration constants
**Addresses:** Virtual currency balance, transaction history, anti-farming foundations
**Avoids:** Economy inflation/deflation (by designing faucets/sinks upfront)

### Phase 2: Reaction System
**Rationale:** Reactions are the primary engagement faucet; must be secure from exploits before earning begins.
**Delivers:** ReactionService, deduplication logic, rate limiting, content reaction tracking
**Uses:** SQLAlchemy atomic updates, aiogram callback queries
**Implements:** ReactionService component
**Avoids:** Reaction tracking exploits (deduplication, rate limiting built in from start)

### Phase 3: Daily Rewards & Streaks
**Rationale:** Secondary earning source; depends on WalletService. Streak logic is complex and needs thorough edge case testing.
**Delivers:** Daily gift handler, UserStreak model, StreakService, background jobs for streak expiration
**Uses:** APScheduler CronTrigger, UTC datetime handling
**Implements:** StreakService component
**Avoids:** Streak calculation edge cases (timezone handling, grace period)

### Phase 4: Shop System
**Rationale:** Economy sink; requires WalletService for payments. Shop must be available before users accumulate too many besitos.
**Delivers:** ShopProduct model, ShopService, purchase flow, inventory management
**Uses:** Atomic check-and-deduct transactions
**Implements:** ShopService component
**Avoids:** Database performance collapse (batching, async processing)

### Phase 5: Rewards & Admin Configuration
**Rationale:** Most complex phase; requires all previous services. Cascading admin UI needs careful FSM design.
**Delivers:** RewardService, RewardCondition model, cascading FSM wizard, admin handlers
**Uses:** Nested FSM states, condition evaluator strategy pattern
**Implements:** RewardService component, cascading admin flow
**Avoids:** Cascading reward logic errors (explicit AND semantics, preview mode, reward caps)

### Phase 6: Integration & Polish
**Rationale:** Connect all components, add level system, ensure unified admin UX.
**Delivers:** Level system, unified admin views, economy dashboard, user 360 view
**Uses:** All gamification services
**Avoids:** Admin UX fragmentation (unified content-economy view, contextual configuration)

### Phase Ordering Rationale

- **Foundation first:** Database models and WalletService must exist before any earning or spending features
- **Security second:** Reaction system with exploit prevention before users can earn
- **Sinks before inflation:** Shop system before users accumulate unspendable currency
- **Complexity last:** Reward conditions and cascading admin UI after core economy is stable
- **Integration final:** Polish and unified views after all components exist

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 5 (Rewards & Admin):** Cascading FSM wizard is complex nested state management; may need UI flow research
- **Phase 6 (Integration):** Economy balancing may need tuning based on early metrics

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** Standard SQLAlchemy models, established Service pattern
- **Phase 2 (Reaction System):** Well-documented aiogram callback patterns
- **Phase 3 (Daily Rewards):** Standard APScheduler job pattern
- **Phase 4 (Shop System):** Standard e-commerce patterns, atomic transactions

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Existing codebase uses these exact versions; no new dependencies needed |
| Features | MEDIUM | Based on established gamification patterns + existing codebase analysis |
| Architecture | HIGH | Follows existing ServiceContainer DI pattern; clear integration points |
| Pitfalls | HIGH | Virtual economy anti-patterns well-documented; mitigation strategies established |

**Overall confidence:** HIGH

### Gaps to Address

- **Economy tuning parameters:** Exact besito values for daily rewards, reactions, shop prices need validation during Phase 1. Create a faucet/sink spreadsheet and test with hypothetical user scenarios.
- **Streak grace period duration:** 6-hour grace period is recommended but may need adjustment based on user behavior. Monitor support tickets.
- **Reaction rate limits:** 30-second cooldown is conservative; may need tuning for engagement vs. exploit balance.
- **Admin preview mode for rewards:** Phase 5 requires testing rule evaluation against sample users before deployment.

## Sources

### Primary (HIGH confidence)
- `/data/data/com.termux/files/home/repos/adminpro/requirements.txt` — Existing dependency versions verified
- `/data/data/com.termux/files/home/repos/adminpro/bot/services/container.py` — DI pattern reference
- `/data/data/com.termux/files/home/repos/adminpro/bot/background/tasks.py` — APScheduler integration pattern
- `/data/data/com.termux/files/home/repos/adminpro/bot/database/models.py` — Existing model patterns
- aiogram 3.x documentation — CallbackQuery handling patterns
- SQLAlchemy 2.0 documentation — Atomic update patterns

### Secondary (MEDIUM confidence)
- Octalysis Framework (yukaichou.com) — Core drives for engagement
- Virtual Economy Design (Gamasutra) — Currency flow principles
- Mobile Game Retention mechanics — Daily rewards, streaks patterns

### Tertiary (LOW confidence)
- Anti-patterns in Gamification (GDC Vault) — UX pitfalls, needs validation with actual users

---

*Research completed: 2026-02-08*
*Ready for roadmap: yes*
