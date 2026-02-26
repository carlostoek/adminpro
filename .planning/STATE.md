# Project State: DianaBot v3.0 Narrativa

**Project:** DianaBot - Telegram Bot with VIP/Free Management + Gamification + Narrative
**Current Milestone:** v3.0 Narrativa
**Milestone Goal:** Sistema narrativo modular con historias ramificadas, integrado con gamificación mediante condiciones en cascada.

---

## Current Position

| Attribute | Value |
|-----------|-------|
| Phase | 27-core-narrative-engine |
| Plan | 01 (database models) |
| Status | Completed - ready for Plan 02

**Progress Bar:**
```
v1.0 Voice Service:    [██████████] 100% ✅
v1.1 Menu System:      [██████████] 100% ✅
v1.2 Deployment:       [██████████] 100% ✅
v2.0 Gamification:     [██████████] 100% ✅
v2.1 Deployment Ready: [██████████] 100% ✅
v3.0 Narrativa:        [██░░░░░░░░] 20%  🔄

Phase 27: [████________________] 20% (1/5 tasks - models complete)
```

---

## Project Reference

**Core Value:** Consistencia absoluta en la voz de Lucien: cada mensaje del bot debe sonar elegante, misterioso y natural viniendo del mayordomo, sin importar qué handler o flujo lo invoque.

**Key Constraints:**
- Zero new dependencies (existing stack sufficient)
- Integrate with 19 existing services via ServiceContainer
- Use existing cascading condition system for story conditions
- Leverage existing WalletService for economy operations
- Follow established voice architecture (Diana 🫦 for content, Lucien 🎩 for system)

**Current Focus:** Plan 27-02 - NarrativeService implementation

---

## Performance Metrics

**Codebase (v2.1 baseline):**
- Total lines: ~42,000 Python
- Services: 19
- Database models: 10+ gamification models
- Tests: 409+ total
- Message providers: 13

**v3.0 Target:**
- New models: 4 (Story, StoryNode, StoryChoice, UserStoryProgress)
- New services: 2 (NarrativeService, StoryEditorService)
- New handlers: 3 (story_reader.py, story_editor.py, node_manager.py)
- Expected new tests: 100+

---

## Accumulated Context

**Key Decisions (from research):**
1. Self-referential SQLAlchemy relationships for tree structure (proven pattern)
2. JSON columns for choices and decision history (existing pattern)
3. Dual-track persistence: FSM for UI state, database for story progress
4. Atomic wallet operations with idempotency keys for choice costs
5. Eager loading with selectinload() to prevent N+1 queries

**Technical Risks Identified:**
1. State management conflicts between story FSM and existing flows
2. Database query explosion from graph-structured data
3. Economy-narrative race conditions on rapid clicks
4. Admin editor complexity at 50+ nodes

**Mitigations Planned:**
1. Universal escape hatch button, aggressive Redis TTL (30 min)
2. Auto-save after every choice, recovery on startup
3. Eager loading patterns, story graph cache
4. Atomic UPDATE with WHERE, pre-validation before showing choices
5. Hierarchical organization, validation suite

**Open Questions:**
- Maximum recommended nodes per story (needs load testing)
- Admin story editor UX workflow (needs prototyping in Phase 29)

---

## Session Continuity

**Last Action:** Completed Plan 27-01 - Database models for narrative system
**Next Action:** Plan 27-02 - NarrativeService implementation
**Blockers:** None

**Recent Commits (v3.0 Narrativa):**
- feat(27-01): add narrative system models (Story, StoryNode, StoryChoice, UserStoryProgress)
- feat(27-01): add narrative system enums (StoryStatus, NodeType, StoryProgressStatus)

**Recent Commits (v2.1 shipped):**
- feat(26-03): Data migration with Python seeders
- feat(26-02): Default shop products seeder
- feat(26-01): Idempotent migration design
- feat(25-04): Broadcast options configuration step
- feat(25-03): Content protection toggle per message

---

## Phase Quick Reference

| Phase | Name | Goal | Key Deliverables |
|-------|------|------|------------------|
| 27 | Core Narrative Engine | Foundation models and service | Story models, NarrativeService, StoryEditorService |
| 28 | User Story Experience | User reading flow | Story list, reader handler, progress tracking, escape hatch |
| 29 | Admin Story Editor | Admin content creation | Story/node/choice CRUD, validation, publishing |
| 30 | Economy & Shop Integration | Gamification linkage | Choice costs, rewards, conditions, shop connectivity |

---

## v3.0 Requirements Summary

| Category | Count | Requirements |
|----------|-------|--------------|
| NARR (Narrative Core) | 10 | NARR-01 to NARR-10 |
| ADMIN (Admin Editor) | 12 | ADMIN-01 to ADMIN-12 |
| ECON (Economy Integration) | 8 | ECON-01 to ECON-08 |
| TIER (Tiered Access) | 5 | TIER-01 to TIER-05 |
| SHOP (Shop Integration) | 5 | SHOP-01 to SHOP-05 |
| UX (User Experience) | 6 | UX-01 to UX-06 |
| **Total** | **43** | **100% mapped to phases** |

---

*State file updated: 2026-02-26*

## Plan 27-01 Completion

| Metric | Value |
|--------|-------|
| Duration | ~15 minutes |
| Tasks | 5/5 |
| Commits | 2 |
| Files Modified | 2 |
| Lines Added | ~520 |

**Deliverables:**
- 3 new enums: StoryStatus, NodeType, StoryProgressStatus
- 4 new models: Story, StoryNode, StoryChoice, UserStoryProgress
- All relationships and indexes properly configured

**SUMMARY:** `.planning/phases/27-core-narrative-engine/27-01-SUMMARY.md`
