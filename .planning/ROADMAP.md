# Roadmap: LucienVoiceService - Telegram Bot VIP/Free

## Overview

Transformación desde un bot Telegram local con SQLite hacia una solución production-ready en Railway con PostgreSQL, testing comprehensivo y profiling de performance. El viaje establece infraestructura de despliegue (v1.2), cimiento para caching avanzado (v1.3), y optimización continua.

## Milestones

- ✅ **v1.0 LucienVoiceService** - Phases 1-4 (shipped 2026-01-24)
- ✅ **v1.1 Sistema de Menús** - Phases 5-13 (shipped 2026-01-28)
- ✅ **v1.2 Primer Despliegue** - Phases 14-18 (shipped 2026-01-30)
- 🚧 **v2.0 Gamificación** - Phases 19-24 (in progress)

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
<summary>🚧 v2.0 Gamificación (Phases 19-24) — IN PROGRESS</summary>

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

### Phase 20: Reaction System
**Goal:** Users can react to channel content with inline buttons and earn besitos
**Requirements:** REACT-01 through REACT-07 (7 requirements)
**Dependencies:** Phase 19 (WalletService)
**Plans:** 4 plans

**Success Criteria:**
1. Every message in channels displays inline reaction buttons with configured emojis
2. User can tap reaction buttons and receives immediate visual feedback
3. User cannot react twice with same emoji to same content
4. User sees cooldown message if reacting within 30 seconds
5. User receives besitos immediately after valid reaction
6. User cannot exceed daily reaction limit
7. VIP content reactions rejected for non-VIP users

Plans:
- [ ] 20-01 — Database and Service foundation (UserReaction model, ReactionService core)
- [ ] 20-02 — ServiceContainer integration and keyboard utilities
- [ ] 20-03 — Callback handlers and reaction flow
- [ ] 20-04 — Channel integration and REACT requirements verification

### Phase 21: Daily Rewards & Streaks
**Goal:** Users can claim daily rewards with streak bonuses
**Requirements:** STREAK-01 through STREAK-07 (7 requirements)
**Dependencies:** Phase 19 (WalletService)

**Success Criteria:**
1. User sees "Claim Daily Gift" button when available
2. User receives base besitos + streak bonus upon claiming
3. Streak counter increases for consecutive daily claims
4. Streak resets to 0 if user misses a day
5. Current streak visible in user menu
6. Reaction streak tracks separately
7. Background job runs at UTC midnight for streak expiration

### Phase 22: Shop System
**Goal:** Users can browse and purchase content with besitos
**Requirements:** SHOP-01 through SHOP-08 (8 requirements)
**Dependencies:** Phase 19 (WalletService), Phase 20 (content access)

**Success Criteria:**
1. User can browse shop catalog with prices
2. Content packages available for purchase
3. VIP membership extension available
4. System prevents purchase with insufficient balance
5. Purchase completes atomically (deduct + deliver)
6. Purchased content immediately accessible
7. User can view purchase history
8. VIP users see discounted prices where configured

### Phase 23: Rewards System
**Goal:** Users automatically receive rewards when meeting conditions
**Requirements:** REWARD-01 through REWARD-06 (6 requirements)
**Dependencies:** Phase 19 (WalletService), Phase 21 (streak data)

**Success Criteria:**
1. User can view available rewards with conditions
2. System checks reward eligibility automatically
3. User receives reward notification when conditions met
4. Rewards support streak, points, level, besitos spent conditions
5. Multiple conditions use AND logic
6. Reward value capped at maximum

### Phase 24: Admin Configuration
**Goal:** Admins can configure all gamification parameters
**Requirements:** ADMIN-01 through ADMIN-08 (8 requirements)
**Dependencies:** All previous phases

**Success Criteria:**
1. Admin can configure besitos values and daily limits
2. Admin can create shop products with besitos price
3. Admin can enable/disable shop products
4. Admin can create rewards with cascading condition creation
5. Admin can create conditions inline from reward flow
6. Admin dashboard displays economy metrics
7. Admin can view user's complete gamification profile

</details>

## Progress

**Execution Order:**
Phases execute in numeric order: 19 → 20 → 21 → 22 → 23 → 24

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
| 20. Reaction System | v2.0 | 0/4 | Pending | — |
| 21. Daily Rewards & Streaks | v2.0 | 0/0 | Pending | — |
| 22. Shop System | v2.0 | 0/0 | Pending | — |
| 23. Rewards System | v2.0 | 0/0 | Pending | — |
| 24. Admin Configuration | v2.0 | 0/0 | Pending | — |

**Overall Progress:** 68/68 plans complete for v1.x (100%) | 0/43 requirements for v2.0 (0%)

---

*Last updated: 2026-02-08 after v2.0 roadmap creation*