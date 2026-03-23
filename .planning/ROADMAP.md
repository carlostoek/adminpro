# Roadmap: LucienVoiceService - Telegram Bot VIP/Free

## Overview

Transformación desde un bot Telegram local con SQLite hacia una solución production-ready en Railway con PostgreSQL, testing comprehensivo y profiling de performance. El viaje establece infraestructura de despliegue (v1.2), cimiento para caching avanzado (v1.3), y optimización continua.

## Milestones

- ✅ **v1.0 LucienVoiceService** - Phases 1-4 (shipped 2026-01-24)
- ✅ **v1.1 Sistema de Menús** - Phases 5-13 (shipped 2026-01-28)
- ✅ **v1.2 Primer Despliegue** - Phases 14-18 (shipped 2026-01-30)
- ✅ **v2.0 Gamificación** - Phases 19-24 (shipped 2026-02-17)
- ✅ **v2.1 Deployment Readiness** - Phases 25-26 (shipped 2026-02-21)
- 📋 **v2.2+** - Future enhancements (planned)

## Phases

<details>
<summary>✅ v1.0 LucienVoiceService (Phases 1-4) - SHIPPED 2026-01-24</summary>

### Phase 1: Service Foundation & Voice Rules
**Goal**: Centralized message system with Lucien's voice
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — BaseMessageProvider and LucienVoiceService foundation
- [x] 01-02-PLAN.md — Voice consistency rules and variation system
- [x] 01-03-PLAN.md — Common and Admin message providers

### Phase 2: Template Organization & Admin Migration
**Goal**: Variable interpolation and admin handler migration
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md — Template composition and keyboard integration
- [x] 02-02-PLAN.md — Admin main menu migration
- [x] 02-03-PLAN.md — Admin VIP and Free menu migration

### Phase 3: User Flow Migration & Testing Strategy
**Goal**: User handler migration and semantic test helpers
**Plans**: 4 plans

Plans:
- [x] 03-01-PLAN.md — User start and VIP flow migration
- [x] 03-02-PLAN.md — Free flow migration
- [x] 03-03-PLAN.md — Session-aware variation system
- [x] 03-04-PLAN.md — Semantic test helpers

### Phase 4: Advanced Voice Features
**Goal**: Voice validation and message preview tools
**Plans**: 4 plans

Plans:
- [x] 04-01-PLAN.md — Voice validation pre-commit hook
- [x] 04-02-PLAN.md — Message preview CLI tool
- [x] 04-03-PLAN.md — Dynamic content features (conditionals, lists)
- [x] 04-04-PLAN.md — E2E tests and completion

</details>

<details>
<summary>✅ v1.1 Sistema de Menús (Phases 5-13) - SHIPPED 2026-01-28</summary>

Role-based menu system (Admin/VIP/Free) with automatic role detection, content package management, interest notifications, user management, social media integration, VIP ritualized entry flow, and comprehensive documentation.

**9 phases, 48 plans, 57 requirements satisfied (100%)**

**Key features:**
- RoleDetectionService (Admin > VIP > Free priority)
- ContentService CRUD for content packages
- InterestService with 5-minute deduplication
- UserManagementService with audit logging
- Free channel entry flow with social media keyboard
- VIP 3-stage ritualized entry (confirmation → alignment → access)
- Package detail view redesign
- 5,777 lines of documentation

**[Full phases 5-13 archived in previous roadmap]**

</details>

<details>
<summary>✅ v1.2 Primer Despliegue (Phases 14-18) — SHIPPED 2026-01-30</summary>

Production-ready deployment infrastructure with PostgreSQL migration support, comprehensive test coverage (212 tests), health monitoring endpoint, Railway deployment configuration, and performance profiling tools.

**5 phases, 21 plans, 37 requirements satisfied (100%)**

**Key features:**
- PostgreSQL and SQLite dual-dialect support with automatic dialect detection
- Alembic migration system with auto-migration on startup
- FastAPI health check endpoint with database connectivity verification
- Railway deployment configuration (Railway.toml, Dockerfile, .dockerignore)
- pytest-asyncio testing infrastructure with 7 fixtures and in-memory database
- 212 system tests covering all critical flows
- CLI test runner and Telegram /run_tests command
- Performance profiling with pyinstrument (/profile command)
- N+1 query detection and eager loading optimization

**[Full phases 14-18 archived in milestones/v1.2-ROADMAP.md]**

</details>

<details>
<summary>✅ v2.0 Gamificación (Phases 19-24) — SHIPPED 2026-02-17</summary>

Sistema completo de gamificación con moneda virtual "besitos", reacciones con botones inline, tienda de contenido, logros configurables y mecánicas de engagement (regalo diario, rachas, niveles).

**6 phases, 43 requirements**

### Phase 19: Economy Foundation ✅
**Goal:** Users have a virtual currency wallet with transaction history and level progression
**Requirements:** ECON-01 through ECON-08 (8 requirements)
**Dependencies:** None (builds on v1.2 infrastructure)
**Plans:** 4 plans
**Status:** Complete — 2026-02-09

**Success Criteria:**
1. ✅ User can view current besitos balance in their personal menu
2. ✅ User can view paginated transaction history showing earned/spent amounts
3. ✅ System rejects any transaction that would result in negative balance
4. ✅ Concurrent transactions complete without race conditions
5. ✅ Every besito change is recorded with reason, amount, and timestamp
6. ✅ Admin can credit or debit besitos to any user with reason note
7. ✅ User level displays correctly based on total lifetime besitos earned
8. ✅ Admin can configure level progression formula

Plans:
- [x] 19-01 — Database foundation (TransactionType enum, UserGamificationProfile, Transaction models)
- [x] 19-02 — WalletService core (atomic earn/spend, transaction history, level calculation)
- [x] 19-03 — Admin operations (credit/debit, level formula configuration)
- [x] 19-04 — Integration and testing (ServiceContainer integration, ECON requirement tests)

### Phase 20: Reaction System ✅
**Goal:** Users can react to channel content with inline buttons and earn besitos
**Requirements:** REACT-01 through REACT-07 (7 requirements)
**Dependencies:** Phase 19 (WalletService)
**Plans:** 4 plans
**Status:** Complete — 2026-02-10

**Success Criteria:**
1. ✅ Every message in channels displays inline reaction buttons with configured emojis
2. ✅ User can tap reaction buttons and receives immediate visual feedback
3. ✅ User cannot react twice with same emoji to same content
4. ✅ User sees cooldown message if reacting within 30 seconds
5. ✅ User receives besitos immediately after valid reaction
6. ✅ User cannot exceed daily reaction limit
7. ✅ VIP content reactions rejected for non-VIP users

Plans:
- [x] 20-01 — Database and Service foundation (UserReaction model, ReactionService core)
- [x] 20-02 — ServiceContainer integration and keyboard utilities
- [x] 20-03 — Callback handlers and reaction flow
- [x] 20-04 — Channel integration and REACT requirements verification

### Phase 21: Daily Rewards & Streaks ✅
**Goal:** Users can claim daily rewards with streak bonuses
**Requirements:** STREAK-01 through STREAK-07 (7 requirements)
**Dependencies:** Phase 19 (WalletService)
**Plans:** 4 plans
**Status:** Complete — 2026-02-13

**Success Criteria:**
1. ✅ User sees "Claim Daily Gift" button when available
2. ✅ User receives base besitos + streak bonus upon claiming
3. ✅ Streak counter increases for consecutive daily claims
4. ✅ Streak resets to 0 if user misses a day
5. ✅ Current streak visible in user menu
6. ✅ Reaction streak tracks separately
7. ✅ Background job runs at UTC midnight for streak expiration

Plans:
- [x] 21-01 — UserStreak database model with StreakType enum
- [x] 21-02 — StreakService core logic (claim, bonus calculation, UTC boundaries)
- [x] 21-03 — Reaction streak tracking integration
- [x] 21-04 — Daily gift handler with Lucien's voice
- [x] 21-05 — Streak display in user menus
- [x] 21-06 — UTC midnight background job for streak expiration
- [x] 21-07 — Comprehensive streak system tests

### Phase 22: Shop System ✅
**Goal:** Users can browse and purchase content with besitos
**Requirements:** SHOP-01 through SHOP-08 (8 requirements)
**Dependencies:** Phase 19 (WalletService), Phase 20 (content access)
**Plans:** 4 plans
**Status:** Complete — 2026-02-13

**Success Criteria:**
1. ✅ User can browse shop catalog with prices
2. ✅ Content packages available for purchase
3. ✅ VIP membership extension available
4. ✅ System prevents purchase with insufficient balance
5. ✅ Purchase completes atomically (deduct + deliver)
6. ✅ Purchased content immediately accessible
7. ✅ User can view purchase history
8. ✅ VIP users see discounted prices where configured

Plans:
- [x] 22-01-PLAN.md — Database foundation (ContentSet, ShopProduct, UserContentAccess models)
- [x] 22-02-PLAN.md — ShopService core (browse, purchase, deliver, history)
- [x] 22-03-PLAN.md — ServiceContainer integration and user handlers
- [x] 22-04-PLAN.md — Menu wiring and comprehensive tests

### Phase 23: Rewards System ✅
**Goal:** Users automatically receive rewards when meeting conditions
**Requirements:** REWARD-01 through REWARD-06 (6 requirements)
**Dependencies:** Phase 19 (WalletService), Phase 21 (streak data)
**Plans:** 4 plans
**Status:** Complete — 2026-02-14

**Success Criteria:**
1. ✅ User can view available rewards with conditions
2. ✅ System checks reward eligibility automatically
3. ✅ User receives reward notification when conditions met
4. ✅ Rewards support streak, points, level, besitos spent conditions
5. ✅ Multiple conditions use AND logic
6. ✅ Reward value capped at maximum

Plans:
- [x] 23-01-PLAN.md — Database foundation (Reward, RewardCondition, UserReward models, enums)
- [x] 23-02-PLAN.md — RewardService core (condition evaluation, event-driven checking, claiming)
- [x] 23-03-PLAN.md — ServiceContainer integration and user handlers
- [x] 23-04-PLAN.md — Comprehensive tests covering all REWARD requirements

### Phase 24: Admin Configuration ✅
**Goal:** Admins can configure all gamification parameters
**Requirements:** ADMIN-01 through ADMIN-08 (8 requirements)
**Dependencies:** All previous phases
**Status:** Complete — 2026-02-21

**Success Criteria:**
1. ✅ Admin can configure besitos values and daily limits
2. ✅ Admin can create shop products with besitos price
3. ✅ Admin can enable/disable shop products
4. ✅ Admin can create rewards with cascading condition creation
5. ✅ Admin can create conditions inline from reward flow
6. ✅ Admin dashboard displays economy metrics
7. ✅ Admin can view user's complete gamification profile

**Gap Closure Plans (All Complete):**
- [x] 24-06-PLAN.md — ContentSet CRUD handlers (fixes product creation blocker)
- [x] 24-07-PLAN.md — Reward delete error fix (TelegramBadRequest handling)
- [x] 24-08-PLAN.md — Economy stats menu button (missing navigation)
- [x] 24-09-PLAN.md — TransactionType enum fix (EARN_SHOP_REFUND missing)

</details>

## Progress

**Execution Order:**
Phases execute in numeric order: 19 → 20 → 21 → 22 → 23 → 24 → 25

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Service Foundation & Voice Rules | v1.0 | 3/3 | Complete | 2026-01-23 |
| 2. Template Organization & Admin Migration | v1.0 | 3/3 | Complete | 2026-01-23 |
| 3. User Flow Migration & Testing Strategy | v1.0 | 4/4 | Complete | 2026-01-24 |
| 4. Advanced Voice Features | v1.0 | 4/4 | Complete | 2026-01-24 |
| 5. Role Detection & Database Foundation | v1.1 | 6/6 | Complete | 2026-01-25 |
| 6. VIP/Free User Menus | v1.1 | 4/4 | Complete | 2026-01-25 |
| 7. Admin Menu with Content Management | v1.1 | 4/4 | Complete | 2026-01-26 |
| 8. Interest Notification System | v1.1 | 4/4 | Complete | 2026-01-26 |
| 9. User Management Features | v1.1 | 6/6 | Complete | 2026-01-26 |
| 10. Free Channel Entry Flow | v1.1 | 5/5 | Complete | 2026-01-27 |
| 11. Documentation | v1.1 | 4/4 | Complete | 2026-01-28 |
| 12. Rediseño de Menú de Paquetes | v1.1 | 4/4 | Complete | 2026-01-27 |
| 13. VIP Ritualized Entry Flow | v1.1 | 4/4 | Complete | 2026-01-27 |
| 14. Database Migration Foundation | v1.2 | 4/4 | Complete | 2026-01-29 |
| 15. Health Check & Railway Preparation | v1.2 | 5/5 | Complete | 2026-01-29 |
| 16. Testing Infrastructure | v1.2 | 5/5 | Complete | 2026-01-29 |
| 17. System Tests | v1.2 | 4/4 | Complete | 2026-01-30 |
| 18. Admin Test Runner & Performance Profiling | v1.2 | 4/4 | Complete | 2026-01-30 |
| 19. Economy Foundation | v2.0 | 4/4 | Complete | 2026-02-09 |
| 20. Reaction System | v2.0 | 4/4 | Complete | 2026-02-10 |
| 21. Daily Rewards & Streaks | v2.0 | 7/7 | Complete | 2026-02-13 |
| 22. Shop System | v2.0 | 4/4 | Complete | 2026-02-13 |
| 23. Rewards System | v2.0 | 4/4 | Complete | 2026-02-14 |
| 24. Admin Configuration | v2.0 | 9/9 | Complete | 2026-02-21 |
| 25. Broadcasting Improvements | v2.1 | 1/1 | Complete | 2026-02-21 |
| 26. Initial Data Migration | v2.1 | 3/3 | Complete | 2026-02-21 |
| 27. Security Audit Fixes | v2.2+ | 5/5 | Complete | 2026-03-17 |
| 28. Corrección total de migraciones | v2.2+ | 4/7 | In Progress | — |
| 29. Telegram Alert Handler | v2.2+ | 1/1 | Complete | 2026-03-23 |
| 30. Admin User Simulation | v2.2+ | 4/4 | Complete | 2026-03-23 |

**Overall Progress:** 110 plans complete (3 pending in phase 28)

<details>
<summary>✅ v2.1 Deployment Readiness (Phases 25-26) — SHIPPED 2026-02-21</summary>

Broadcasting improvements with optional reactions/content protection and complete data migration infrastructure for seamless deployment.

**2 phases, 4 plans, 9 requirements satisfied (100%)**

**Key features:**
- Optional reaction buttons per message during broadcast
- Content protection (no download) toggle per message
- Alembic data migration with idempotent design
- Python seeder module for complex relational data
- Default economy configuration seeded automatically
- Default rewards: Primeros Pasos, Ahorrador Principiante, Racha de 7 Dias
- Default shop products with VIP discounts


### Phase 27: Security Audit Fixes
**Goal:** Fix 29 security findings from audit (8 critical + 21 warnings)
**Requirements:** Security fixes for race conditions, atomicity failures, and code quality
**Dependencies:** All previous phases
**Plans:** 5 plans
**Status:** Complete — 2026-03-17

**Critical Issues:**
- C-001 to C-008: Race conditions in token redemption, VIP entry, and bulk operations

**Wave Structure:**
- Wave 1: Race condition fixes (redeem_vip_token, create_free_request, approve_ready_free_requests, vip_entry)
- Wave 2: Atomicity fixes (user_management role changes, transaction separation)
- Wave 3: Warnings (rate limiting, pagination, datetime migration)

**Success Criteria:**
1. No race conditions in token redemption or VIP entry flow
2. Database and Telegram state remain consistent on failures
3. Bulk operations use rate limiting and pagination
4. All datetime operations use timezone-aware datetimes
5. All existing tests pass

Plans:
- [x] 27-01-PLAN.md — Fix redeem_vip_token and create_free_request race conditions
- [x] 27-02-PLAN.md — Fix approve_ready_free_requests and kick_expired_vip race conditions
- [x] 27-03-PLAN.md — Fix vip_entry.py race conditions in stage progression
- [x] 27-04-PLAN.md — Fix user_management.py atomicity and subscription.py long transactions
- [x] 27-05-PLAN.md — Rate limiting, pagination, datetime fixes

**[Full phases 25-26 archived in milestones/v2.1-ROADMAP.md]**

</details>

### Phase 28: Corrección total de migraciones

**Goal:** All Alembic migrations correctly reflect the current SQLAlchemy models, work on both SQLite and PostgreSQL, and `alembic revision --autogenerate` detects zero schema drift
**Depends on:** Phase 27
**Plans:** 7 plans

**Gaps addressed:**
- env.py only imported 9 of 20 model classes (autogenerate blind to 11 models)
- VIPSubscriber missing last_kick_notification_sent_at column (in DB but not model)
- shop_products created with price/currency columns — model uses besitos_price/tier
- Seed migration uses PL/pgSQL DO blocks that crash on SQLite
- free_channel_requests partial unique index missing correct dialect WHERE clause
- transactiontype PostgreSQL enum missing 4 values used by application

**Wave Structure:**
- Wave 1: env.py imports + VIPSubscriber model fix (non-breaking, no migrations)
- Wave 2: fix_shop_products migration + seed/index dialect fixes (parallel)
- Wave 3: fix_transactiontype_enum migration
- Wave 4: Human verification checkpoint

Plans:
- [x] 28-01-PLAN.md — Fix env.py imports (all 20 models) + add last_kick_notification_sent_at to VIPSubscriber
- [x] 28-02-PLAN.md — Create fix_shop_products_schema migration (besitos columns, remove price/currency)
- [x] 28-03-PLAN.md — Fix seed migration PL/pgSQL + partial index dialect compatibility
- [x] 28-04-PLAN.md — Create fix_transactiontype_enum migration (all 8 values on PostgreSQL)
- [ ] 28-05-PLAN.md — Verification checkpoint (autogenerate zero drift, alembic upgrade head on SQLite)
- [ ] 28-06-PLAN.md — Additional migration fixes (if needed)
- [ ] 28-07-PLAN.md — Final verification and cleanup

### Phase 29: Telegram Alert Handler — Advanced Logging ✅

**Goal:** Add optional secondary logging handler that forwards ERROR/CRITICAL events from high-priority namespaces to an admin Telegram chat, with anti-spam deduplication and zero impact when ALERT_CHAT_ID is absent
**Depends on:** Phase 28
**Plans:** 1 plan
**Status:** Complete — 2026-03-23

**Key features:**
- TelegramAlertHandler with QueueHandler/QueueListener pattern (non-blocking)
- SmartAlertFilter with deduplication (5-min window) and namespace filtering
- AlertFormatter with HTML formatting and truncation protection
- Auto-integration via config.py and main.py
- Zero impact when ALERT_CHAT_ID not configured

Plans:
- [x] 29-01-PLAN.md — TelegramAlertHandler package + config.py/main.py integration + .env.example docs

### Phase 30: Admin User Simulation @docs/30_Admin_User_Simulation.md @docs/30_Vigilar.md ✅

**Goal:** Implement an Admin User Simulation System for role-based behavior testing inside the Telegram bot. Allow admin users to simulate different user roles (FREE, VIP) without modifying real user data or triggering permanent side effects.
**Depends on:** Phase 29
**Plans:** 4 plans
**Status:** Complete — 2026-03-23 (Verified 6/6 must-haves)

**Key features:**
- SimulationService with SimulationStore (TTL 30-min, per-admin isolation)
- ResolvedUserContext as single source of truth for role checks
- SimulationMiddleware injects user_context into handler data
- /simulate command with VIP/FREE/REAL mode selector keyboard
- Visual banner shows simulation status in admin responses
- Safety guards block wallet/shop/reward state-changing operations

**Wave Structure:**
- Wave 1: Core simulation infrastructure (store, context, service)
- Wave 2: Middleware integration + Admin UI controls
- Wave 3: Safety restrictions (block state-changing operations)

**Success Criteria:**
1. ✅ Admin can activate simulation mode for FREE or VIP role via /simulate command
2. ✅ Simulation context is the single source of truth for all role checks via resolve_user_context()
3. ✅ Context propagates to handlers, services, and middlewares
4. ✅ Visual banner shows simulation status in all admin responses when active
5. ✅ State-changing operations (payments, balance updates, rewards) are blocked during simulation
6. ✅ Simulation is isolated per admin (no cross-user leakage)

Plans:
- [x] 30-01-PLAN.md — Core simulation infrastructure (SimulationService, SimulationStore, ResolvedUserContext, SimulationMode enum)
- [x] 30-02-PLAN.md — Middleware integration (SimulationMiddleware, RoleDetectionMiddleware update)
- [x] 30-03-PLAN.md — Admin UI controls (/simulate command, mode selector keyboard, status display)
- [x] 30-04-PLAN.md — Safety restrictions (block wallet/shop/reward operations, simulation banner)

---

*Last updated: 2026-03-23 after Phase 29-30 documentation closure*
