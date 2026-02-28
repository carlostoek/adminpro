---
phase: 29-admin-story-editor
plan: 03
subsystem: narrative
status: completed
tags: [narrative, admin, node-wizard, conditions, rewards]

requires:
  - 29-01-node-condition-reward-models
  - 29-02-story-management-handlers
  - 27-03-story-editor-service
  - 27-04-narrative-services-container

provides:
  - node-creation-wizard
  - condition-configuration-flow
  - reward-attachment-system
  - choice-creation-flow
  - checkpoint-resume-pattern

affects:
  - bot/services/story_editor.py
  - bot/handlers/admin/story_management.py
  - bot/states/admin.py

tech-stack:
  added: []
  patterns:
    - "Checkpoint/Resume pattern for inline reward creation"
    - "FSM wizard flow with 5 steps"
    - "Soft delete cascade for nodes"
    - "Checkbox toggle UI for reward selection"

key-files:
  created: []
  modified:
    - bot/services/story_editor.py
    - bot/handlers/admin/story_management.py
    - bot/states/admin.py

decisions:
  - "Reused RewardConditionState for condition configuration to maintain consistency"
  - "Implemented checkpoint/resume pattern to prevent data loss during inline reward creation"
  - "Used soft delete cascade for nodes to preserve referential integrity"
  - "Checkbox toggle UI for reward selection provides intuitive multi-select"

metrics:
  duration: "~45 minutes"
  completed-date: "2026-02-28"
  tasks: 6
  commits: 3
  files-modified: 3
  lines-added: ~1400
---

# Phase 29 Plan 03: Node Creation Wizard Summary

## Overview

Implemented comprehensive node creation wizard enabling admins to build story structure by creating nodes with content, configuring access conditions, attaching rewards, and linking nodes with choices.

## Deliverables

### 1. Extended StoryEditorService (9 new methods)

**File:** `bot/services/story_editor.py`

- `create_node_condition()` - Create NodeCondition records for access control
- `attach_reward_to_node()` - Attach rewards via NodeReward junction
- `detach_reward_from_node()` - Soft-delete reward attachments
- `get_node_conditions()` - Query active conditions for a node
- `get_node_rewards()` - Query attached rewards for a node
- `update_node()` - Update node fields (content, media, tier, etc.)
- `delete_node()` - Soft delete with cascade to choices
- `update_choice()` - Update choice fields (text, target, cost)
- `delete_choice()` - Soft delete individual choices

### 2. Node Creation Wizard Handlers

**File:** `bot/handlers/admin/story_management.py`

**Wizard Flow (5 steps):**
1. **Content Input** (`process_node_content`)
   - Accepts text, photo, or video
   - Validates at least one content type exists
   - Stores file_ids for media

2. **Type Selection** (`callback_node_type_selected`)
   - START, STORY, CHOICE, ENDING types
   - ENDING type skips to final confirmation

3. **Condition Configuration** (`callback_node_conditions_start`)
   - Reuses existing RewardConditionState
   - Supports LEVEL_REACHED, TIER_REQUIRED, STREAK_LENGTH, TOTAL_POINTS, PRODUCT_OWNED
   - Checkpoint pattern for condition editing

4. **Reward Selection** (`callback_node_rewards_question`)
   - Checkbox toggle UI with ☑️/⬜️ indicators
   - Inline reward creation with checkpoint/resume
   - Auto-selects newly created rewards

5. **Choice Creation** (`callback_node_create_choices`)
   - Link to existing nodes or create new
   - Cost configuration (0-20+ besitos)
   - Multi-choice support with "create another" flow

### 3. Node Management Handlers

- `callback_node_list()` - List all nodes with type emoji and choice count
- `callback_node_edit()` - Edit menu with condition/reward/choice counts
- `callback_node_delete()` - Soft delete with cascade warning
- `callback_choice_list()` - List choices with cost indicators
- `callback_choice_delete()` - Soft delete with refresh

### 4. FSM States Added

**File:** `bot/states/admin.py`

```python
# Node creation
waiting_for_content
waiting_for_node_type
waiting_for_conditions
waiting_for_rewards
waiting_for_final_decision

# Choice creation
waiting_for_choice_text
waiting_for_target_node
waiting_for_cost_besitos

# Node edit
waiting_for_edit_content
```

## Key Design Patterns

### Checkpoint/Resume Pattern
```python
# Before branching to reward creation
await state.update_data(
    checkpoint_state="waiting_for_rewards",
    checkpoint_data={...},  # All node data
    return_to="story_editor",
    return_callback="node:reward:created"
)

# After reward creation
await callback_node_reward_created(callback, state, session)
# Restores checkpoint_data and continues
```

### Checkbox Toggle UI
```python
is_selected = reward.id in selected_rewards
checkbox = "☑️" if is_selected else "⬜️"
# Toggle on click, refresh display
```

### Soft Delete Cascade
```python
# delete_node() soft-deletes node AND all associated choices
node.is_active = False
for choice in choices:
    choice.is_active = False
```

## Verification

All verification commands from plan pass:

```bash
# Service methods
grep -n "create_node_condition\|attach_reward_to_node" bot/services/story_editor.py
# ✓ 9 new methods present

# Content handlers
grep -n "process_node_content\|callback_node_type_selected" bot/handlers/admin/story_management.py
# ✓ Task 2 handlers present

# Condition handlers
grep -n "callback_node_condition" bot/handlers/admin/story_management.py
# ✓ Task 3 handlers present

# Checkpoint pattern
grep -n "checkpoint_state\|callback_node_reward_created" bot/handlers/admin/story_management.py
# ✓ Task 4 checkpoint pattern present

# Choice handlers
grep -n "process_choice_text\|callback_choice_target" bot/handlers/admin/story_management.py
# ✓ Task 5 handlers present

# Edit/delete handlers
grep -n "callback_node_edit\|callback_choice_list" bot/handlers/admin/story_management.py
# ✓ Task 6 handlers present
```

## Integration Points

### With Existing Systems
- **RewardConditionState** - Reused for condition configuration
- **RewardCreateState** - Used for inline reward creation
- **StoryEditorService** - Extended with 9 new methods
- **ServiceContainer** - Provides service access to handlers

### Callback Data Patterns
```
admin:story:node:create:{story_id}     # Start node creation
node_type:{START|STORY|CHOICE|ENDING}   # Type selection
node:conditions:{yes|no|skip}           # Condition flow
node:reward:toggle:{reward_id}          # Toggle selection
node:reward:create:inline               # Inline creation
choice:target:{node_id|new}             # Target selection
choice:cost:{0|5|10|20}                 # Cost selection
admin:node:edit:{node_id}               # Edit menu
admin:node:choices:{node_id}            # Choice list
```

## Voice Architecture Compliance

All handlers use **Lucien voice** (🎩) for system/admin messages:
- "🎩 <b>Crear Nodo de Historia</b>"
- "🎩 <b>Configurar Condición</b>"
- "🎩 <b>Crear Elección</b>"

## Deviations from Plan

None - plan executed exactly as written.

## Next Steps

Plan 29-04 should focus on:
- Story preview/testing functionality
- Node reordering capabilities
- Import/export story structure
- Advanced validation (detecting cycles, unreachable nodes)

## Self-Check: PASSED

- [x] All 9 StoryEditorService methods implemented
- [x] All 6 task handler groups implemented
- [x] Checkpoint/resume pattern functional
- [x] All FSM states added
- [x] Syntax check passes
- [x] All commits atomic with proper messages
- [x] Lucien voice (🎩) used throughout
