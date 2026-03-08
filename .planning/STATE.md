# Project State: DianaBot v3.0 Narrativa

**Project:** DianaBot - Telegram Bot with VIP/Free Management + Gamification + Narrative
**Current Milestone:** v3.0 Narrativa
**Milestone Goal:** Sistema narrativo modular con historias ramificadas, integrado con gamificación mediante condiciones en cascada.

---

## Current Position

| Attribute | Value |
|-----------|-------|
| Phase | 30-economy-shop-integration |
| Plan | 01 (Economy Integration Foundation) |
| Status | ✅ COMPLETED - Plan 01 Done

**Progress Bar:**
```
v1.0 Voice Service:    [██████████] 100% ✅
v1.1 Menu System:      [██████████] 100% ✅
v1.2 Deployment:       [██████████] 100% ✅
v2.0 Gamification:     [██████████] 100% ✅
v2.1 Deployment Ready: [██████████] 100% ✅
v3.0 Narrativa:        [███████░░░] 60%  🔄

Phase 27: [████████████________] 60% (3/5 plans - Core engine complete)
Phase 28: [██████______________] 30% (3/5 plans - Story handler integration complete)
Phase 29: [████████████████████] 100% (4/4 plans - Admin story editor complete) ✅
Phase 30: [██__________________] 10% (1/5 plans - Economy foundation complete) 🔄
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

**Current Focus:** Phase 30 - Economy & Shop Integration (connect narrative with gamification)

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

**Last Action:** Completed Plan 30-01 - Economy Integration Foundation (5/5 tasks)
**Next Action:** Plan 30-02 - Choice Cost Processing
**Blockers:** None

**Recent Commits (v3.0 Narrativa):**
- fix(29): add missing 'and_' import in story_management handler
- fix(29): improve node type selection and add missing nodes button
- feat(29): add database migrations for Story.is_active column
- feat(29-04): complete story preview mode and validation display
- feat(29-03): extend StoryEditorService with node conditions and rewards
- feat(29-03): implement node creation wizard with checkpoint/resume
- feat(29-02): create story_management.py with CRUD handlers
- feat(29-02): add StoryEditorStates FSM states for story management
- feat(29-02): register story_router and add menu button
- feat(29-01): create NodeReward junction table for node-reward associations
- feat(29-01): create NodeCondition model for node-level access conditions
- feat(29-01): add PRODUCT_OWNED to RewardConditionType enum
- feat(28-03): add race condition protection and edge case handling
- feat(28-03): add stories button to VIP and Free main menus
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

*State file updated: 2026-02-28*

## Plan 29-03 Completion

| Metric | Value |
|--------|-------|
| Duration | ~45 minutes |
| Tasks | 6/6 |
| Commits | 3 |
| Files Modified | 3 |
| Lines Added | ~1400 |

**Deliverables:**
- `StoryEditorService` extended with 9 new methods:
  - `create_node_condition()` - Node access conditions
  - `attach_reward_to_node()` / `detach_reward_from_node()` - Reward management
  - `get_node_conditions()` / `get_node_rewards()` - Query methods
  - `update_node()` / `delete_node()` - Node management with soft delete
  - `update_choice()` / `delete_choice()` - Choice management
- Node creation wizard with 5-step flow:
  1. Content input (text, photo, video)
  2. Type selection (START, STORY, CHOICE, ENDING)
  3. Condition configuration (reuses RewardConditionState)
  4. Reward selection with checkbox toggle UI
  5. Choice creation with target node selection
- Checkpoint/resume pattern for inline reward creation
- Node list, edit, delete handlers
- Choice list and delete handlers
- All FSM states for node wizard

**SUMMARY:** `.planning/phases/29-admin-story-editor/29-03-SUMMARY.md`

## Plan 29-02 Completion

| Metric | Value |
|--------|-------|
| Duration | ~25 minutes |
| Tasks | 5/5 |
| Commits | 3 |
| Files Created | 1 |
| Files Modified | 3 |
| Lines Added | ~835 |

**Deliverables:**
- `StoryEditorStates` with 7 FSM states for story creation and editing
- `bot/handlers/admin/story_management.py` with 18+ handlers:
  - Story list with status badges (🟢🟡⚠️🗑️) and premium indicators (💎🆓)
  - 3-step creation wizard (title → description → premium)
  - Edit handlers for title, description, premium toggle
  - Publish/unpublish with validation
  - Soft delete for draft stories
  - Statistics view (starts, completions, completion rate)
- Router registration in `bot/handlers/admin/__init__.py`
- "📖 Crear Historia" button in admin menu

**SUMMARY:** `.planning/phases/29-admin-story-editor/29-02-SUMMARY.md`

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

## Plan 28-02 Completion

| Metric | Value |
|--------|-------|
| Duration | ~15 minutes |
| Tasks | 7/7 |
| Commits | 2 |
| Files Created | 1 |
| Files Modified | 1 |
| Lines Added | ~625 |

**Deliverables:**
- `bot/handlers/user/story.py` with 7 handlers:
  - `cmd_stories` - /stories command with tier filtering (NARR-04, TIER-02, TIER-03)
  - `handle_start_story` - Start/resume story with upsell (NARR-04, NARR-07, TIER-04)
  - `handle_make_choice` - Process choices and detect completion (NARR-06, NARR-10)
  - `handle_story_exit` - Escape hatch to exit story (NARR-08)
  - `handle_back_to_list` - Return to story list
  - `handle_restart_request` - Show restart confirmation (UX-03)
  - `handle_confirm_restart` - Confirm and restart completed story
- Voice architecture implementation:
  - Lucien (🎩) for all system messages
  - Diana (🫦) for content nodes
- Helper functions:
  - Progress indicator: "Escena X de Y"
  - Media display: single photo, media group, text-only
  - Status badges for story list
- Router registration in `bot/handlers/user/__init__.py`

**SUMMARY:** `.planning/phases/28-user-story-experience/28-02-SUMMARY.md`

## Plan 28-03 Completion

| Metric | Value |
|--------|-------|
| Duration | ~10 minutes |
| Tasks | 5/5 |
| Commits | 2 |
| Files Modified | 3 |
| Lines Added | ~50 |

**Deliverables:**
- Menu integration: "📖 Historias" button added to VIP and Free main menus
- Race condition protection: `processing_choice` FSM state prevents double-clicks
- Edge case handling:
  - Progress status validation before processing choices
  - Proper state reset on all error paths
  - Handling for nodes without choices that aren't endings
- All 14 requirements (NARR-04 to UX-06) verified implemented

**Key Changes:**
- `bot/services/message/user_menu.py`: Added stories buttons to both VIP and Free menus
- `bot/handlers/user/story.py`: Added `handle_stories_menu` callback and race condition protection
- `bot/states/user.py`: Added `processing_choice` state to StoryReadingStates

**SUMMARY:** `.planning/phases/28-user-story-experience/28-03-SUMMARY.md`

## Plan 29-01 Completion

| Metric | Value |
|--------|-------|
| Duration | ~10 minutes |
| Tasks | 3/3 |
| Commits | 3 |
| Files Modified | 2 |
| Lines Added | ~176 |

**Deliverables:**
- PRODUCT_OWNED added to RewardConditionType enum
- NodeCondition model with fields: id, node_id, condition_type, condition_value, condition_group, is_active, created_at
- NodeReward junction table linking StoryNode and Reward (many-to-many)
- All relationships defined: StoryNode.conditions, StoryNode.attached_rewards, Reward.node_rewards
- Cascade delete configured for all relationships
- Unique constraint on (node_id, reward_id) to prevent duplicates

**Key Design Decisions:**
- Reused RewardConditionType enum for consistency with existing condition system
- Used condition_group pattern (0=AND, 1+=OR) matching RewardCondition model
- Added is_active flag to NodeReward for soft-disable without deletion

**SUMMARY:** `.planning/phases/29-admin-story-editor/29-01-SUMMARY.md`

## Plan 29-04 Completion

| Metric | Value |
|--------|-------|
| Duration | ~5 minutes (verification) |
| Tasks | 4/4 |
| Commits | 1 |
| Files Verified | 3 |

**Deliverables:**
- Validation status display with `format_validation_status()` helper
  - Shows ✅ Jugable, ⚠️ Revisar, or ❌ Bloqueado status
  - Integrated in story list and story details views
  - Blocks publishing if validation fails
- Preview mode for testing stories
  - `callback_story_preview()` - Start preview from any story
  - `callback_preview_choice()` - Navigate choices in preview
  - `callback_preview_exit()` - Exit preview mode
  - Uses Diana's voice (🫦) for content as users see it
- Admin menu integration
  - "📖 Crear Historia" button in admin menu
  - Routes to story management handlers
- Keyboard utilities for all story editor screens
  - `get_story_management_keyboard()` - Main menu
  - `get_story_list_keyboard_admin()` - Paginated story list
  - `get_story_detail_keyboard()` - Story actions
  - `get_node_list_keyboard()` - Node management
  - `get_node_edit_keyboard()` - Node editing
  - `get_choice_list_keyboard()` - Choice management

**All ADMIN-01 through ADMIN-12 requirements satisfied.**

**SUMMARY:** `.planning/phases/29-admin-story-editor/29-04-SUMMARY.md`

## Plan 30-01 Completion

| Metric | Value |
|--------|-------|
| Duration | ~10 minutes |
| Tasks | 5/5 |
| Commits | 5 |
| Files Modified | 3 |
| Lines Added | ~320 |

**Deliverables:**
- `TransactionType` enum extended with `SPEND_STORY_CHOICE` and `EARN_STORY_COMPLETION`
- `StoryChoice` model has `vip_cost_besitos` field for VIP discount flexibility
- `ShopProduct` model has `unlocks_node_id` field with foreign key for shop-node linkage
- `NarrativeService` accepts wallet, reward, shop, and streak service dependencies
- Choice condition evaluation with cascading AND/OR logic:
  - `evaluate_choice_conditions()` - Main evaluation method
  - `calculate_choice_cost()` - VIP-aware cost calculation
  - `_format_requirement_message()` - Lucien's voice formatting
  - Helper methods for level, streak, product, and total_earned conditions

**SUMMARY:** `.planning/phases/30-economy-shop-integration/30-01-SUMMARY.md`
