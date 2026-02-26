# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-26)

**Core value:** Consistencia absoluta en la voz de Lucien: cada mensaje del bot debe sonar elegante, misterioso y natural viniendo del mayordomo, sin importar qué handler o flujo lo invoque.

**Current focus:** v3.0 Narrativa - Building modular narrative system with branching stories

## Current Position

**Milestone:** v3.0 Narrativa 🔄 STARTING
**Phase:** 27 - (Not started)
**Status:** Defining requirements

**Milestone v2.1 COMPLETE** — Phases 25-26 finished and archived

### Progress Overview

```
v1.0 Voice Service:    [██████████] 100% ✅
v1.1 Menu System:      [██████████] 100% ✅
v1.2 Deployment:       [██████████] 100% ✅
v2.0 Gamification:     [██████████] 100% ✅
v2.1 Deployment Ready: [██████████] 100% ✅
v3.0 Narrativa:        [░░░░░░░░░░] 0%   🔄
```

## Accumulated Context

### Key Architectural Decisions (Preserved from v2.x)

| Decision | Rationale | Status |
|----------|-----------|--------|
| Cascading condition system | AND/OR logic with condition_group for complex requirements | **Reusable for narrative** |
| Atomic transaction pattern | UPDATE SET col = col + delta for thread-safety | **Active** |
| FSM for admin flows | Consistent wizard patterns | **Extend for story editor** |
| Service Container DI | Lazy loading, clean dependencies | **Continue using** |

### v3.0 Narrativa Architecture Notes

**Condition System Extension:**
- Existing RewardConditionType covers: STREAK_LENGTH, TOTAL_POINTS, LEVEL_REACHED, BESITOS_SPENT, FIRST_PURCHASE, FIRST_DAILY_GIFT, FIRST_REACTION, NOT_VIP, NOT_CLAIMED_BEFORE
- v3 adds narrative conditions: REACTION_TIME, TIME_IN_BOT, NARRATIVE_PATH_TAKEN, FRAGMENT_COMPLETED
- Same cascading UI pattern, extended condition enum

**Narrative State Tracking:**
- UserStoryProgress model: user_id, story_id, current_node_id, decisions_made (JSON), ending_reached
- StoryNode model: id, story_id, content, media_file_ids, choices (JSON), unlock_conditions
- Choice leads to next_node_id with optional cost (besitos) or requirements

**Integration Points:**
- Narrative unlocks → triggers RewardService.check_rewards_on_event()
- Shop purchase → can unlock story fragments
- Story completion → can grant besitos, items, VIP extension

---

## Session Continuity

**Last session:** 2026-02-26 — Started v3.0 Narrativa milestone
**Stopped at:** Requirements definition phase
**Next:** Research (optional) → Requirements → Roadmap

### Quick Reference

**Files:**
- Roadmap: `.planning/ROADMAP.md`
- Requirements: `.planning/REQUIREMENTS.md`
- Research: `.planning/research/SUMMARY.md`

---

*State updated: 2026-02-26 - Milestone v3.0 started*
