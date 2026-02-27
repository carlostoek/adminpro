# Project State: DianaBot v3.0 Narrativa

**Project:** DianaBot - Telegram Bot with VIP/Free Management + Gamification + Narrative
**Current Milestone:** v3.0 Narrativa
**Milestone Goal:** Sistema narrativo modular con historias ramificadas, integrado con gamificación mediante condiciones en cascada.

---

## Current Position

| Attribute | Value |
|-----------|-------|
| Phase | 28-user-story-experience |
| Plan | 01 (Story Reading Infrastructure) |
| Status | Completed - ready for Plan 02

**Progress Bar:**
```
v1.0 Voice Service:    [██████████] 100% ✅
v1.1 Menu System:      [██████████] 100% ✅
v1.2 Deployment:       [██████████] 100% ✅
v2.0 Gamification:     [██████████] 100% ✅
v2.1 Deployment Ready: [██████████] 100% ✅
v3.0 Narrativa:        [███░░░░░░░] 25%  🔄

Phase 27: [████████████________] 60% (3/5 plans - Core engine complete)
Phase 28: [██__________________] 10% (1/5 plans - Story infrastructure started)
```

---

## Project Reference

**Core Value:** Consistencia absoluta en la voz de Lucien: cada mensaje del bot debe sonar elegante, misterioso y natural viniendo del mayordomo, sin importar qué handler o flujo lo invoque.

**Key Constraints:**
- Zero new dependencies (existing stack sufficient)
- Integrate with 21 services via ServiceContainer (19 existing + 2 narrative)
- Use existing cascading condition system for story conditions
- Leverage existing WalletService for economy operations
- Follow established voice architecture (Diana 🫦 for content, Lucien 🎩 for system)

**Current Focus:** Plan 28-02 - Story Reader Handlers implementation

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

**Last Action:** Completed Plan 28-01 - Story Reading Infrastructure
**Next Action:** Plan 28-02 - Story Reader Handlers implementation
**Blockers:** None

**Recent Commits (v3.0 Narrativa):**
- feat(28-01): add story keyboard utilities to keyboards.py
- feat(28-01): add StoryReadingStates FSM states for story reading flow
- feat(27-04): add narrative services to ServiceContainer
- feat(27-03): implement StoryEditorService with full CRUD operations
- feat(27-02): implement get_story_progress and abandon_story methods
- feat(27-02): implement make_choice method with immediate persistence
- feat(27-02): implement get_current_node method
- feat(27-02): implement start_story method
- feat(27-02): implement get_available_stories method
- feat(27-02): create NarrativeService skeleton and imports
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

*State file updated: 2026-02-27*

## Plan 27-02 Completion

| Metric | Value |
|--------|-------|
| Duration | ~25 minutes |
| Tasks | 6/6 |
| Commits | 6 |
| Files Created | 1 |
| Lines Added | ~420 |

**Deliverables:**
- NarrativeService with 6 methods:
  - get_available_stories() - List stories by user tier
  - start_story() - Begin or resume stories
  - get_current_node() - Get current node with choices
  - make_choice() - Process choices with immediate persistence
  - get_story_progress() - Check user's progress
  - abandon_story() - Mark story as abandoned
- Dual-track persistence pattern implementation
- Security checks for user ownership

**SUMMARY:** `.planning/phases/27-core-narrative-engine/27-02-SUMMARY.md`

## Plan 27-04 Completion

| Metric | Value |
|--------|-------|
| Duration | ~1 minute |
| Tasks | 3/3 |
| Commits | 2 |
| Files Modified | 2 |
| Lines Added | ~78 |

**Deliverables:**
- ServiceContainer with `narrative` and `story_editor` lazy loading properties
- Updated `get_loaded_services()` to include new services
- Package exports for both services in `__init__.py`

**SUMMARY:** `.planning/phases/27-core-narrative-engine/27-04-SUMMARY.md`

## Plan 27-03 Completion

| Metric | Value |
|--------|-------|
| Duration | ~10 minutes |
| Tasks | 7/7 |
| Commits | 1 |
| Files Created | 1 |
| Lines Added | 508 |

**Deliverables:**
- StoryEditorService with 7 methods: create_story, create_node, create_choice, validate_story, publish_story, get_story_stats
- Full CRUD operations for admin story management
- Story validation workflow (start node, endings, connectivity checks)
- Story analytics (completion rates, popular endings)

**SUMMARY:** `.planning/phases/27-core-narrative-engine/27-03-SUMMARY.md`

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

## Plan 28-01 Completion

| Metric | Value |
|--------|-------|
| Duration | ~5 minutes |
| Tasks | 3/3 |
| Commits | 2 |
| Files Modified | 2 |
| Lines Added | ~198 |

**Deliverables:**
- StoryReadingStates FSM with 4 states:
  - browsing_stories - User viewing available stories (NARR-04)
  - reading_node - User reading a node with choices (NARR-05, NARR-06)
  - story_completed - Story finished, showing summary (NARR-10)
  - confirm_restart - Confirmation to restart completed story (UX-03)
- 5 story keyboard utility functions:
  - get_story_choice_keyboard() - Max 3 per row (UX-05), exit button (NARR-08)
  - get_story_list_keyboard() - Status badges (UX-02)
  - get_story_restart_confirmation_keyboard() - Yes/No confirmation (UX-03)
  - get_story_completed_keyboard() - Post-completion options
  - get_upsell_keyboard() - Premium upsell (TIER-04)

**SUMMARY:** `.planning/phases/28-user-story-experience/28-01-SUMMARY.md`
