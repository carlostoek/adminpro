# Roadmap: LucienVoiceService - Telegram Bot VIP/Free

## Overview

Transformación desde un bot Telegram local con SQLite hacia una solución production-ready en Railway con PostgreSQL, testing comprehensivo y profiling de performance. El viaje establece infraestructura de despliegue (v1.2), cimiento para caching avanzado (v1.3), y optimización continua.

## Milestones

- ✅ **v1.0 LucienVoiceService** - Phases 1-4 (shipped 2026-01-24)
- ✅ **v1.1 Sistema de Menús** - Phases 5-13 (shipped 2026-01-28)
- ✅ **v1.2 Primer Despliegue** - Phases 14-18 (shipped 2026-01-30)
- ✅ **v2.0 Gamificación** - Phases 19-24 (shipped 2026-02-17)
- ✅ **v2.1 Deployment Readiness** - Phases 25-26 (shipped 2026-02-21)
- 🔄 **v3.0 Narrativa** - Phases 27-30 (in progress)

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
- FastAPI health check endpoint (/health) with database connectivity verification
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
Phases execute in numeric order: 19 → 20 → 21 → 22 → 23 → 24 → 25 → 26 → 27 → 28 → 29 → 30

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
| 27. Core Narrative Engine | v3.0 | 0/0 | Planned | - |
| 28. User Story Experience | v3.0 | 0/0 | Planned | - |
| 29. Admin Story Editor | v3.0 | 0/0 | Planned | - |
| 30. Economy & Shop Integration | v3.0 | 0/0 | Planned | - |

**Overall Progress:** 105 plans complete (0 pending), 4 phases planned

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

**[Full phases 25-26 archived in milestones/v2.1-ROADMAP.md]**

</details>

---

# v3.0 Narrativa - Branching Story System

**Milestone:** v3.0 Narrativa
**Phases:** 27-30
**Requirements:** 43 total (NARR: 10, ADMIN: 12, ECON: 8, TIER: 5, SHOP: 5, UX: 6)
**Depth:** Standard

## Overview

This milestone delivers a modular narrative system with branching stories integrated into the existing gamification infrastructure. The system allows admins to create interactive stories with nodes and choices, while users experience personalized narratives with progress tracking, tiered access (Free/VIP), and economy integration (besitos costs/rewards).

**Architecture approach:** Service-oriented with Dependency Injection via ServiceContainer. Two new services (NarrativeService, StoryEditorService) integrate with 19 existing services. Self-referential SQLAlchemy relationships handle tree-structured stories. Zero new dependencies required.

---

### Phase 27: Core Narrative Engine ✅
**Status:** Complete — 2026-02-26

**Goal:** Foundation database models and core service for story storage, retrieval, and user progress tracking.

**Dependencies:** None (builds on existing v2.1 infrastructure)

**Requirements:**
| ID | Requirement | Status |
|----|-------------|--------|
| NARR-01 | Admin can create a story with metadata (title, description, is_premium) | ✅ |
| NARR-02 | Admin can create story nodes with content (text, media_file_ids) | ✅ |
| NARR-03 | Admin can define choices for a node (text, target_node_id, optional cost) | ✅ |
| NARR-09 | System tracks user story progress (current_node, decisions_made, status) | ✅ |
| TIER-01 | Stories can be marked as Free (levels 1-3) or Premium (levels 4-6) | ✅ |

**Plans:** 4 plans
- [x] 27-01 — Database foundation (Story, StoryNode, StoryChoice, UserStoryProgress models)
- [x] 27-02 — NarrativeService (user-facing story operations)
- [x] 27-03 — StoryEditorService (admin CRUD operations)
- [x] 27-04 — ServiceContainer integration

**Success Criteria:**
1. ✅ Database schema includes Story, StoryNode, StoryChoice, and UserStoryProgress tables with proper relationships
2. ✅ NarrativeService provides API to create stories, add nodes, define choices, and track user progress
3. ✅ StoryEditorService provides admin CRUD operations for story/node/choice management
4. ✅ User progress is persisted to database immediately after each choice (dual-track persistence)
5. ✅ Stories can be marked as Free or Premium and filtered accordingly

---

## Phase 28: User Story Experience

**Goal:** Complete user-facing story reading experience with progress tracking, tier filtering, and polished UX.

**Dependencies:** Phase 27 (Core Narrative Engine)

**Plans:** 3 plans

Plans:
- [ ] 28-01-PLAN.md — FSM States and Keyboard Utilities (StoryReadingStates, story keyboards)
- [ ] 28-02-PLAN.md — Story Reading Handler Core Flow (story.py with all handlers)
- [ ] 28-03-PLAN.md — Handler Integration and Edge Cases (router registration, menu integration)

**Requirements:
| ID | Requirement |
|----|-------------|
| NARR-04 | User can start an available story from the story list |
| NARR-05 | User sees current node content with inline button choices |
| NARR-06 | User choice transitions to next node and saves progress |
| NARR-07 | User can resume a story from where they left off |
| NARR-08 | User has escape hatch button to exit story at any time |
| NARR-10 | System handles story completion (end nodes) and records ending reached |
| TIER-02 | Free users see only Free stories in their list |
| TIER-03 | VIP users see both Free and Premium stories |
| TIER-04 | Free users attempting Premium story see upsell message with VIP info |
| UX-01 | User sees progress indicator ("Escena 3 de 12") during story |
| UX-02 | User sees story list with completion status (not started, in progress, completed) |
| UX-03 | User can restart a completed story (with confirmation) |
| UX-04 | Story content uses Diana's voice (🫦), system messages use Lucien's (🎩) |
| UX-05 | Choices are presented as inline keyboard buttons (max 3 per row, max 10 total) |
| UX-06 | Media content (photos/videos) displays correctly in sequence with text |

**Success Criteria:**
1. User can view list of available stories filtered by their tier (Free/VIP)
2. User can start a story and see node content with inline choice buttons
3. Selecting a choice transitions to next node and persists progress automatically
4. User can resume in-progress stories from where they left off
5. Universal "Salir" escape hatch button visible at all times during story
6. Story completion is detected and recorded when reaching end nodes
7. Progress indicator shows current position (e.g., "Escena 3 de 12")
8. Story list shows completion status badges (not started, in progress, completed)
9. Diana's voice (🫦) used for story content, Lucien's (🎩) for system messages
10. Media attachments display correctly with text content

---

## Phase 29: Admin Story Editor

**Goal:** Complete admin interface for creating, editing, validating, and publishing stories.

**Dependencies:** Phase 27 (Core Narrative Engine), Phase 28 (User Story Experience - for testing)

**Requirements:**
| ID | Requirement |
|----|-------------|
| ADMIN-01 | Admin can list all stories with status (draft/published/archived) |
| ADMIN-02 | Admin can edit story metadata (title, description, premium flag) |
| ADMIN-03 | Admin can publish/unpublish stories (only published visible to users) |
| ADMIN-04 | Admin can delete draft stories (soft delete with is_active) |
| ADMIN-05 | Admin can create nodes via FSM wizard with content input |
| ADMIN-06 | Admin can edit node content and media attachments |
| ADMIN-07 | Admin can delete nodes (with cascade handling for choices) |
| ADMIN-08 | Admin can create choices linking nodes with optional besitos cost |
| ADMIN-09 | Admin can edit choice text and target node |
| ADMIN-10 | Admin can delete choices |
| ADMIN-11 | System validates stories (detect cycles, orphaned nodes, dead ends) |
| ADMIN-12 | Admin can view story statistics (total nodes, completion count) |
| TIER-05 | Individual nodes can have tier restrictions (early levels Free, later Premium) |

**Success Criteria:**
1. Admin can list all stories with status badges (draft/published/archived)
2. Admin can create/edit story metadata via FSM wizard
3. Admin can publish/unpublish stories; only published stories appear to users
4. Admin can soft-delete draft stories
5. Admin can create/edit/delete nodes via FSM wizard with content and media
6. Admin can create/edit/delete choices linking nodes with optional costs
7. Story validation detects cycles, orphaned nodes, and dead ends before publishing
8. Admin can view story statistics (total nodes, user completions)
9. Individual nodes can be marked with tier restrictions beyond story-level tier

---

## Phase 30: Economy & Shop Integration

**Goal:** Full integration with existing gamification systems - choice costs, rewards, conditions, and shop connectivity.

**Dependencies:** Phase 27 (Core Narrative Engine), Phase 28 (User Story Experience), existing WalletService/RewardService/ShopService

**Requirements:**
| ID | Requirement |
|----|-------------|
| ECON-01 | Choices can have besitos cost (deducted on selection) |
| ECON-02 | Users with insufficient besitos see locked choices with cost displayed |
| ECON-03 | Story completion can trigger reward (besitos, items, VIP extension) |
| ECON-04 | Story nodes can unlock rewards when reached |
| ECON-05 | Choices can have conditions (level, streak, total earned) via extended condition system |
| ECON-06 | Conditions are evaluated using existing cascading condition system (AND/OR groups) |
| ECON-07 | Economy operations are atomic (no double-charging on rapid clicks) |
| ECON-08 | Reward notifications are batched (not spam per node) |
| SHOP-01 | Shop products can unlock specific story levels/nodes as purchase bonus |
| SHOP-02 | Story completion can grant shop products as reward |
| SHOP-03 | Story nodes can require ownership of specific shop product to access |
| SHOP-04 | Product ownership is checked via existing UserContentAccess model |
| SHOP-05 | Shop integration uses existing condition system (extend with PRODUCT_OWNED condition) |

**Success Criteria:**
1. Choices display besitos cost; insufficient balance shows locked state with cost
2. Selecting a costly choice atomically deducts besitos (no double-charging)
3. Story completion triggers configurable rewards via existing RewardService
4. Individual nodes can unlock rewards when reached
5. Choices support conditions (level, streak, total earned) using cascading condition system
6. Conditions evaluated with AND/OR group logic as per existing pattern
7. Reward notifications batched into single message instead of per-node spam
8. Shop products can unlock story nodes as purchase bonus
9. Story completion can grant shop products
10. Nodes can require specific product ownership (checked via UserContentAccess)
11. PRODUCT_OWNED condition type added to existing condition system

---

## v3.0 Progress Tracking

| Phase | Status | Requirements | Success Criteria Met |
|-------|--------|--------------|---------------------|
| 27 - Core Narrative Engine | **Complete** | 5/5 | 5/5 |
| 28 - User Story Experience | Planned | 15/15 | 0/10 |
| 29 - Admin Story Editor | Planned | 13/13 | 0/9 |
| 30 - Economy & Shop Integration | Planned | 10/10 | 0/11 |

**Coverage:** 43/43 requirements mapped (100%)

---

## Dependency Graph

```
Phase 27 (Core Engine)
    ↓
Phase 28 (User Experience)
    ↓
Phase 29 (Admin Editor)
    ↓
Phase 30 (Economy Integration)
```

**Key Dependencies:**
- Models must exist before services (Phase 27)
- Services before handlers (Phase 27-28)
- User experience before admin editor (admins need to test stories)
- Core engine before economy integration (stable foundation required)

---

## Research Flags

Per research/SUMMARY.md:

| Phase | Research Flag | Notes |
|-------|---------------|-------|
| 27 | Standard patterns | Skip deep research - well-documented tree structures |
| 28 | Standard patterns | Skip deep research - existing handler patterns |
| 29 | Needs UX validation | Admin workflow for story structure needs prototyping |
| 30 | Standard patterns | Skip deep research - existing WalletService integration |

---

## Out of Scope (v3.1+)

- ADV-01 through ADV-04: Advanced narrative (consequences, hidden paths, variables, timed choices)
- ANAL-01 through ANAL-03: Analytics (choice popularity, completion rates, time tracking)
- SOC-01 through SOC-02: Social features (story sharing, community choices)
- Sentiment analysis, NLP, procedural generation

---

*Last updated: 2026-02-26 after Phase 27 completion*
*Next step: `/gsd:plan-phase 28` to begin User Story Experience*
