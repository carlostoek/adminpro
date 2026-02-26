# Project Research Summary

**Project:** DianaBot Narrativa v3 - Branching Story System
**Domain:** Interactive Fiction / Branching Narrative System for Telegram Bot
**Researched:** 2026-02-26
**Confidence:** HIGH

## Executive Summary

The narrative system (Narrativa v3) is a branching interactive fiction engine that integrates with an existing gamified Telegram bot. Unlike simple linear stories, this system supports tree-structured narratives with conditional choices, economy integration (besitos costs/rewards), and progression tracking. The existing codebase provides a solid foundation with 19 lazy-loaded services, a sophisticated reward condition system, and a virtual economy (WalletService).

Research confirms that **zero new dependencies** are required. The existing stack (Python 3.11+, SQLAlchemy 2.0.25, aiogram 3.4.1, SQLite/PostgreSQL with JSON support) provides all necessary capabilities. The narrative system should follow established patterns: Dependency Injection via ServiceContainer, lazy loading for services, and FSM states for multi-step flows. Integration points include extending RewardConditionType for story conditions, leveraging WalletService for choice costs, and reusing the existing reaction/engagement system.

The primary risks are state management conflicts between story progression and existing FSM flows, database query explosion from graph-structured data, and economy-narrative race conditions. These can be mitigated by implementing dual-track persistence (FSM for ephemeral UI state, database for persistent story progress), eager loading patterns for story queries, and atomic wallet operations with idempotency keys.

## Key Findings

### Recommended Stack

The narrative system requires **no new core dependencies**. Existing SQLAlchemy JSON columns (already used for `reward_value`, `transaction_metadata`) can store node choices and user decisions. Self-referential relationships (SQLAlchemy `relationship()` with `remote_side`) handle the tree structure. Telegram's existing file_id system stores media without needing external CDN.

**Core technologies:**
- **SQLAlchemy 2.0.25 (existing)**: JSON storage for choices, self-referential relationships for tree structure — already in use, proven pattern
- **aiogram 3.4.1 (existing)**: Media sending via `send_photo()`, `send_video()` — no new dependencies
- **SQLite/PostgreSQL JSON**: Node choices, decision history, conditions — native JSON support

**Optional enhancements (defer):**
- **pydantic 2.5.0+**: Validate node/choice schemas if adding admin API — not needed for MVP
- **python-slugify 8.0.0+**: URL-safe story IDs — not required for MVP

### Expected Features

**Must have (table stakes):**
- **Story nodes with choices** — Core of branching narrative; users expect meaningful decisions
- **Progress tracking** — Users must be able to resume stories; auto-save after each choice
- **Conditional choice availability** — Some choices locked behind conditions (VIP, besitos minimum)
- **Economy integration** — Choice costs and story rewards in besitos
- **Escape hatch** — Universal "Salir de la historia" button to prevent users getting stuck

**Should have (competitive):**
- **Visual story editor for admins** — Hierarchical organization (Stories -> Chapters -> Scenes)
- **Story validation** — Cycle detection, orphaned node detection, dead end warnings
- **Progress indicator** — "Escena 3 de 12" so users know story length
- **Batch reward notifications** — Single consolidated message instead of spam

**Defer (v2+):**
- **Advanced achievement integration** — Event system for narrative achievements
- **Story gifting between users** — Social features
- **Shop rotations for stories** — Limited-time narrative content
- **Quest/mission system** — Time-limited challenges

### Architecture Approach

The narrative system integrates cleanly with the existing service-oriented architecture. Two new services are added to ServiceContainer: `NarrativeService` (story delivery, progress tracking, choice processing) and `StoryEditorService` (admin CRUD operations). The existing RewardCondition system is extended with new condition types (`STORY_NODE_REACHED`, `STORY_CHOICE_MADE`, `STORY_COMPLETED`).

**Major components:**
1. **NarrativeService** — Story delivery, progress tracking, choice processing with WalletService integration
2. **StoryEditorService** — Admin CRUD for stories/nodes/choices, validation, publishing
3. **Story/StoryNode/StoryChoice models** — Tree-structured narrative data with self-referential relationships
4. **UserStoryProgress model** — Persistent story state (current node, decision history, status)
5. **Narrative handlers** — `story_reader.py` for users, `story_editor.py` and `node_manager.py` for admins

### Critical Pitfalls

1. **State Machine Hell (User Stuck in Story)** — Users trapped in narrative FSM states with no escape. *Avoid by:* Universal escape hatch button, command override with `State("*")`, aggressive Redis TTL (30 min).

2. **Progress Loss on Bot Restart** — FSM state lost on deployment. *Avoid by:* Dual-track persistence (FSM for UI, database for story progress), auto-save after every choice, recovery on startup.

3. **N+1 Query Explosion** — Story navigation triggers 5+ queries per node. *Avoid by:* Eager loading with `selectinload()`, story graph cache in memory, batch condition evaluation.

4. **Economy-Narrative Race Conditions** — Double-charging for choices with rapid clicks. *Avoid by:* Atomic wallet operations (UPDATE with WHERE), idempotency keys on choice buttons, pre-validation before showing choices.

5. **The Overwhelming Story Editor** — Admins lose track of story structure at 50+ nodes. *Avoid by:* Hierarchical organization, visual graph representation, story templates, validation suite for orphans/dead ends.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Core Story Engine (Foundation)
**Rationale:** Database schema and core service must exist before any UI work. Foundation for all narrative features.
**Delivers:** Story/StoryNode/StoryChoice/UserStoryProgress models, NarrativeService with progress tracking, basic story reader handler.
**Addresses:** Story nodes with choices, progress tracking, escape hatch
**Avoids:** Progress loss (dual-track persistence), state machine hell (escape hatch), N+1 queries (eager loading patterns)
**Research flag:** Standard patterns — skip deep research

### Phase 2: Admin Story Editor
**Rationale:** Admins need tooling to create stories before users can read them. Depends on Phase 1 models.
**Delivers:** StoryEditorService, admin handlers for story/node/choice CRUD, story validation (cycle detection, orphans).
**Addresses:** Visual story editor, story validation
**Avoids:** Circular reference death trap (DAG validation), overwhelming editor (hierarchical organization), message length limits (editor validation)
**Research flag:** Needs UX research — admin workflow validation recommended

### Phase 3: Economy Integration
**Rationale:** Gamification is a key differentiator; requires stable core engine first.
**Delivers:** Choice costs via WalletService, story rewards, condition evaluation for choices, RewardCondition extensions.
**Addresses:** Economy integration, conditional choice availability
**Avoids:** Economy race conditions (atomic operations, idempotency), reward notification spam (batching)
**Research flag:** Standard patterns — existing WalletService integration

### Phase 4: Polish & Advanced Features
**Rationale:** Quality-of-life improvements after core system is stable.
**Delivers:** Progress indicators, batch notifications, story templates, analytics.
**Addresses:** Progress indicator, batch reward notifications
**Avoids:** Tier access sprawl (centralized StoryAccessService)
**Research flag:** Optional — can defer to v2

### Phase Ordering Rationale

- **Models first:** Story/StoryNode/UserStoryProgress must exist before services can use them
- **Services before handlers:** NarrativeService provides API that handlers consume
- **Admin before user:** Admins need to create content before users can consume it
- **Core before polish:** Economy integration depends on stable story engine; advanced features can wait

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Admin Story Editor):** Admin UX workflow — how admins actually think about story structure; may need prototyping
- **Phase 4 (Analytics):** Story completion metrics — what data matters for narrative engagement

Phases with standard patterns (skip research-phase):
- **Phase 1 (Core Story Engine):** Well-documented tree structures, SQLAlchemy patterns established
- **Phase 3 (Economy Integration):** Existing WalletService provides clear integration pattern

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new dependencies; existing JSON and relationship patterns proven in codebase |
| Features | HIGH | Clear table stakes from gamification research; anti-features explicitly excluded per requirements |
| Architecture | HIGH | ServiceContainer pattern established; 19 existing services provide clear integration model |
| Pitfalls | HIGH | Existing codebase analysis (42k lines, 409 tests) reveals specific integration risks |

**Overall confidence:** HIGH

### Gaps to Address

- **Admin story editor UX:** Research shows visual graph editors are critical, but specific admin workflow needs validation during Phase 2 planning
- **Story complexity limits:** No clear guidance on maximum recommended nodes per story; may need load testing
- **Media storage scaling:** Telegram file_id system sufficient for MVP, but CDN may be needed at 100K+ users

## Sources

### Primary (HIGH confidence)
- Existing codebase analysis (`bot/services/container.py`, `bot/database/models.py`) — Service patterns, existing JSON column usage
- SQLAlchemy 2.0 documentation — JSON type support, self-referential relationships
- aiogram 3.x documentation — Media sending methods, FSM storage options

### Secondary (MEDIUM confidence)
- Octalysis Framework — Gamification engagement drives
- Virtual Economy Design (Gamasutra) — Currency flow principles
- Graph Data Modeling Best Practices (Memgraph) — Node-edge relationships

### Tertiary (LOW confidence)
- Open Design Challenges for Interactive Emergent Narrative (UCSC) — Narrative system complexity patterns

---

*Research completed: 2026-02-26*
*Ready for roadmap: yes*
