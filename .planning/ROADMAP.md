# Roadmap: LucienVoiceService

**Project:** Sistema Centralizado de Mensajes con Voz de Lucien
**Created:** 2026-01-23
**Depth:** standard
**Total Phases:** 4

## Overview

This roadmap delivers a centralized message service that maintains Lucien's sophisticated voice consistently across all bot interactions. The approach follows a foundation-first strategy: establish stateless architecture and voice rules before migrating any handlers, then gradually migrate admin flows (lower risk) followed by user flows (higher traffic), and finally add advanced voice features based on user feedback.

The phased delivery ensures zero-downtime migration, prevents critical pitfalls (stateful services, voice inconsistency, template explosion), and validates architecture with lower-risk admin flows before touching high-traffic user interactions.

## Phases

### Phase 1: Service Foundation & Voice Rules ✅ COMPLETE
**Goal:** Establish stateless message service architecture with voice consistency enforcement

**Status:** ✅ Complete (2026-01-23)
**Completion Date:** 2026-01-23

**Dependencies:** None (foundation phase)

**Requirements:**
- TMPL-02 (HTML formatting) ✅
- TMPL-03 (centralized messages) ✅
- TMPL-05 (error/success standards) ✅
- VOICE-03 (tone directives) ✅
- VOICE-04 (anti-pattern validation) ✅
- VOICE-05 (emoji consistency) ✅
- INTEG-01 (ServiceContainer integration) ✅
- INTEG-02 (stateless service) ✅
- INTEG-03 (formatter integration) ✅

**Success Criteria:**
1. LucienVoiceService class exists in ServiceContainer and loads lazily via @property ✅
2. BaseMessageProvider abstract class enforces stateless interface (no session/bot instance variables) ✅
3. CommonMessages provider returns HTML-formatted error and success messages with consistent emoji usage ✅
4. Voice rules documented in docstrings prevent tutear, jerga técnica, and emoji incorrectos ✅
5. Service integrates with existing formatters from utils/formatters.py for dates and numbers ✅

**Plans:** 3 plans in 2 waves - ALL COMPLETE

**Plan List:**
- [x] 01-01-PLAN.md — BaseMessageProvider abstract class with utility methods (_compose, _choose_variant) ✅
- [x] 01-02-PLAN.md — LucienVoiceService with CommonMessages provider integrated into ServiceContainer ✅
- [x] 01-03-PLAN.md — Test suite validating voice consistency, HTML formatting, and stateless design ✅

---

### Phase 2: Template Organization & Admin Migration ✅ COMPLETE
**Goal:** Migrate all admin handlers to use message service with compositional template design

**Status:** ✅ Complete (2026-01-23)
**Started:** 2026-01-23
**Completion Date:** 2026-01-23

**Dependencies:** Phase 1 (requires foundation)

**Requirements:**
- TMPL-01 (variable interpolation)
- TMPL-04 (keyboard integration)
- VOICE-01 (random variations)
- VOICE-02 (weighted variations)
- DYN-01 (conditional blocks)
- DYN-04 (template composition)
- INTEG-04 (keyboard migration)
- REFAC-01 (admin/main.py)
- REFAC-02 (admin/vip.py)
- REFAC-03 (admin/free.py)

**Success Criteria:**
1. Admin can navigate /admin menu and all messages come from LucienVoiceService (zero hardcoded strings in handlers)
2. Admin sees at least 2-3 variations for key messages (greetings, confirmations) using random.choices with weights
3. Token generation messages adapt based on whether VIP channel is configured (conditional content blocks)
4. Message methods return tuple (text, keyboard) with integrated inline keyboards
5. Template composition prevents method explosion (base messages reused with variations)

**Plans:** 3 plans in 2 waves

**Plan List:**
- [x] 02-01-PLAN.md — AdminVIPMessages provider + vip.py handler migration ✅
- [x] 02-02-PLAN.md — AdminFreeMessages provider + free.py handler migration ✅
- [x] 02-03-PLAN.md — AdminMainMessages provider + main.py handler migration + keyboard updates ✅

---

### Phase 3: User Flow Migration & Testing Strategy ✅ COMPLETE
**Goal:** Migrate all user-facing handlers with semantic test helpers preventing brittleness

**Status:** ✅ Complete (2026-01-24)
**Started:** 2026-01-24
**Completion Date:** 2026-01-24

**Dependencies:** Phase 2 (validates architecture with admin flows)

**Requirements:**
- DYN-02 (dynamic lists) ✅
- DYN-03 (contextual adaptation) ✅
- REFAC-04 (user/start.py) ✅
- REFAC-05 (user/vip_flow.py) ✅
- REFAC-06 (user/free_flow.py) ✅
- REFAC-07 (E2E tests pass) ✅
- TEST-01 (semantic helpers) ✅
- TEST-02 (unit tests) ✅
- TEST-03 (integration tests) ✅

**Success Criteria:**
1. User receives /start message that adapts based on role (Admin redirected, VIP sees expiry, Free sees options) ✅
2. VIP token redemption messages render dynamic lists (available tokens, subscription history) using consistent formatting ✅
3. All 12 existing E2E tests pass after handler migration (no functionality broken) ✅
4. Test suite uses semantic assertions (assert_message_contains_greeting) instead of exact string matching ✅
5. User flow messages show contextual adaptation (hora del día affects greeting tone) ✅

**Plans:** 4 plans in 2 waves - ALL COMPLETE

**Plan List:**
- [x] 03-01-PLAN.md — UserStartMessages provider (time-aware greetings, deep link activation) ✅
- [x] 03-02-PLAN.md — UserFlowMessages provider (Free channel request flows) ✅
- [x] 03-03-PLAN.md — Semantic test helpers and comprehensive unit tests ✅
- [x] 03-04-PLAN.md — Handler migration, cleanup, and E2E validation ✅

---

### Phase 4: Advanced Voice Features ✅ COMPLETE
**Goal:** Add context-aware variation and voice validation tools based on user feedback

**Status:** ✅ Complete (2026-01-24)
**Started:** 2026-01-24
**Completion Date:** 2026-01-24

**Dependencies:** Phase 3 (requires user flows deployed)

**Requirements:** None (all v1 requirements covered in Phases 1-3)

**Success Criteria:**
1. Message variations avoid repetition within single session (context-aware selection) ✅
2. Pre-commit hook validates new messages against voice rules (automated anti-pattern detection) ✅
3. Preview mode allows testing all message variations without running bot ✅
4. Performance profiling confirms message generation <5ms on Termux environment ✅

**Plans:** 4 plans in 2 waves - ALL COMPLETE

**Plan List:**
- [x] 04-01-PLAN.md — Session Message History Service (infrastructure built) ✅
- [x] 04-02-PLAN.md — Voice Linting Pre-Commit Hook ✅
- [x] 04-03-PLAN.md — Message Preview CLI Tool ✅
- [x] 04-04-PLAN.md — Session Context Integration (gap closure) ✅

**Status Notes:**
- All 4 plans complete
- Gap closure (04-04) successfully integrated SessionMessageHistory into ServiceContainer
- All message providers now accept user_id and session_history parameters
- All handlers pass session context to provider calls
- Session context flow: handler -> provider -> _choose_variant fully wired
- 55 tests passing (18 + 19 + 9 + 9)
- Performance targets achieved: ~80 bytes/user, 5.09ms voice linter

---

## Progress

| Phase | Status | Requirements | Completion |
|-------|--------|--------------|------------|
| 1 - Service Foundation | ✅ Complete | 9 requirements | 100% |
| 2 - Template Organization | ✅ Complete | 10 requirements | 100% |
| 3 - User Flow Migration | ✅ Complete | 9 requirements | 100% |
| 4 - Advanced Voice Features | ✅ Complete | 0 requirements | 100% |

**Total:** 28 v1 requirements mapped
**Phase 1:** 9/9 requirements complete (100%)
**Phase 2:** 10/10 requirements complete (100%)
**Phase 3:** 9/9 requirements complete (100%)
**Phase 4:** 4/4 plans complete (100%)

---

## Dependencies

```
Phase 1 (Foundation) ✅
    ↓
Phase 2 (Admin) ✅ ←→ Phase 3 (User) ✅  [can parallelize after Phase 1]
    ↓
Phase 4 (Advanced) ✅
```

**Critical path:** Phase 1 → Phase 2 → Phase 3 → Phase 4

**Notes:**
- Phases 2 and 3 can parallelize after Phase 1 completes if needed
- Phase 4 provides polish and tooling; core functionality complete after Phase 3
- All 4 phases complete - v1 roadmap achieved

---

## Key Decisions

**Why this phase structure:**
- **Foundation first:** Stateless architecture and voice rules cannot be retrofitted cost-effectively
- **Admin before user:** Lower traffic, easier rollback, validates architecture with lower risk
- **Testing during migration:** User flows change frequently, test strategy must be established during migration
- **Polish deferred:** Variation features need user validation before implementation

**Coverage validation:**
- All 28 v1 requirements mapped to exactly one phase
- No orphaned requirements
- Phase 4 includes no v1 requirements (all advanced features)

---

*Roadmap created: 2026-01-23*
*Phase 1 completed: 2026-01-23*
*Phase 2 completed: 2026-01-23*
*Phase 3 completed: 2026-01-24*
*Phase 4 completed: 2026-01-24*
*v1 roadmap complete: All 4 phases executed*
