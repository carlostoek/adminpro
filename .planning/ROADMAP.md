# Roadmap: LucienVoiceService - Telegram Bot VIP/Free

## Overview

Transformación desde un bot Telegram local con SQLite hacia una solución production-ready en Railway con PostgreSQL, testing comprehensivo y profiling de performance. El viaje establece infraestructura de despliegue (v1.2), cimiento para caching avanzado (v1.3), y optimización continua.

## Milestones

- ✅ **v1.0 LucienVoiceService** - Phases 1-4 (shipped 2026-01-24)
- ✅ **v1.1 Sistema de Menús** - Phases 5-13 (shipped 2026-01-28)
- ✅ **v1.2 Primer Despliegue** - Phases 14-18 (shipped 2026-01-30)
- ✅ **v2.0 Gamificación** - Phases 19-24 (shipped 2026-02-17)
- 📋 **v2.1+** - Future enhancements (planned)

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
| 25. Broadcasting Improvements | v2.1 | 1/1 | Planned | - |

**Overall Progress:** 101 plans complete

### Phase 25: Broadcasting Improvements - Optional Reactions and Content Protection 🔄

**Goal:** Mejorar el funcionamiento de broadcasting a los canales con opciones configurables por mensaje
**Requirements:** BROADCAST-01 through BROADCAST-04 (4 requirements)
**Dependencies:** Phase 24 (Admin Configuration complete)
**Status:** Planned

**Success Criteria:**
1. Admin can toggle reaction buttons per message during broadcast flow
2. Admin can enable/disable content protection (no download) per message
3. Broadcast FSM includes step for reaction button configuration
4. Broadcast FSM includes step for content protection configuration

**Description:**
Actualmente las reacciones se envían junto con todos los mensajes al canal. Esta fase hace que sea una funcionalidad opcional:
- El emisor debe poder seleccionar si quiere adjuntar los botones de reacción o no
- También poder activar/desactivar la protección de Telegram (que no se pueda descargar el contenido)
- Ambas opciones se configuran en el flujo de envío del mensaje al canal

Plans:
- [ ] 25-01-PLAN.md — Extend broadcast FSM with optional reactions and content protection

---

*Last updated: 2026-02-21 after Phase 25 planning*
