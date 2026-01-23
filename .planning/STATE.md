# Project State: LucienVoiceService

**Last Updated:** 2026-01-23
**Project Status:** Planning

## Project Reference

**Core Value:**
Consistencia absoluta en la voz de Lucien: cada mensaje del bot debe sonar elegante, misterioso y natural viniendo del mayordomo, sin importar qué handler o flujo lo invoque.

**Current Focus:**
Establishing foundation for centralized message service with voice consistency enforcement before migrating any handlers.

## Current Position

**Phase:** 1 - Service Foundation & Voice Rules
**Plan:** Not yet created
**Status:** Pending
**Progress:** ░░░░░░░░░░ 0%

### Phase Goal
Establish stateless message service architecture with voice consistency enforcement

### Phase Requirements (9 total)
- TMPL-02: HTML formatting support
- TMPL-03: Centralized messages
- TMPL-05: Error/success standards
- VOICE-03: Tone directives
- VOICE-04: Anti-pattern validation
- VOICE-05: Emoji consistency
- INTEG-01: ServiceContainer integration
- INTEG-02: Stateless service
- INTEG-03: Formatter integration

### Success Criteria
1. LucienVoiceService class exists in ServiceContainer and loads lazily via @property
2. BaseMessageProvider abstract class enforces stateless interface (no session/bot instance variables)
3. CommonMessages provider returns HTML-formatted error and success messages with consistent emoji usage
4. Voice rules documented in docstrings prevent tutear, jerga técnica, and emoji incorrectos
5. Service integrates with existing formatters from utils/formatters.py for dates and numbers

## Performance Metrics

**Project-level:**
- Total phases: 4
- Phases complete: 0
- Requirements coverage: 28/28 (100%)
- Overall progress: 0%

**Current phase:**
- Tasks complete: 0
- Tasks remaining: TBD (plan not created)
- Phase progress: 0%
- Estimated effort: TBD

## Accumulated Context

### Key Decisions Made
- **Architecture:** stdlib-only templating (no Jinja2) for Termux constraints and performance
- **Organization:** Navigation-based (admin/, user/) not feature-based for discoverability
- **Migration:** Foundation-first strategy prevents critical pitfalls (stateful services, voice inconsistency)
- **Phasing:** Admin flows before user flows (lower risk validation)

### Current Blockers
None (project starting)

### Open Questions
1. **Performance validation:** Need to profile message generation after Phase 2 to confirm <5ms target on Termux
2. **Variation perception:** Phase 4 features need user testing to validate context-aware variation feels natural
3. **Voice enforcement:** Pre-commit hooks need to be refined based on real violations in Phases 2-3

### TODOs
- [ ] Create Phase 1 execution plan via /gsd:plan-phase
- [ ] Validate existing codebase integration points (ServiceContainer, formatters)
- [ ] Review docs/guia-estilo.md for voice rules to encode

## Session Continuity

### What We're Building
A centralized message service (LucienVoiceService) that maintains Lucien's sophisticated mayordomo personality consistently across all 15+ bot handlers currently using hardcoded strings.

### Why This Matters
Current bot has messages scattered across handlers causing voice inconsistency (elegant vs technical), duplicated text, and maintenance burden. Centralized service ensures every message sounds authentically like Lucien regardless of which developer adds new features.

### How It Works
Service integrated into existing ServiceContainer pattern with lazy loading. Message providers organized by navigation flow (admin/, user/) return HTML-formatted text with integrated keyboards. Handlers call container.message.admin.vip.method() instead of hardcoded strings.

### Next Step
Execute `/gsd:plan-phase 1` to create detailed implementation plan for Service Foundation & Voice Rules phase.

---

*State initialized: 2026-01-23*
*Context preserved for: GSD Plan-Phase Agent*
