---
phase: 30-economy-shop-integration
plan: 04
subsystem: economy
tags: [shop, story-editor, node-unlocking, choice-costs, conditions, rewards]
dependency_graph:
  requires: ["30-02"]
  provides: ["shop-node-integration", "story-editor-economy"]
  affects: ["bot/services/shop.py", "bot/services/story_editor.py"]
tech_stack:
  added: []
  patterns: ["local import to avoid circular dependency", "normalized JSON storage"]
key_files:
  created: []
  modified:
    - bot/services/shop.py
    - bot/services/story_editor.py
decisions:
  - "Use local import of NarrativeService in shop.py to avoid circular dependency"
  - "Normalize conditions to standard format before JSON storage"
  - "Return NodeReward object from attach_reward_to_node for consistency"
metrics:
  duration: "2 minutes"
  completed_date: "2026-03-08"
---

# Phase 30 Plan 04: Shop-Node Integration & Story Editor Economy Summary

**One-liner:** Shop products can unlock story nodes as purchase bonuses; StoryEditorService provides full economy configuration for choice costs, VIP discounts, conditions, and node rewards.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add node unlocking to shop purchase | 9d187f9 | bot/services/shop.py |
| 2 | Add set_choice_cost method | 1632126 | bot/services/story_editor.py |
| 3 | Update attach_reward_to_node method | bbdd6e5 | bot/services/story_editor.py |
| 4 | Add set_choice_conditions method | feef849 | bot/services/story_editor.py |

## Implementation Details

### Task 1: Node Unlocking in Shop Purchase

Enhanced `ShopService.purchase_product()` to unlock story nodes when a product has `unlocks_node_id` set:

- After successful purchase and UserContentAccess creation:
  1. Check if `product.unlocks_node_id` is set
  2. Fetch the node to determine its story
  3. Check if user already has progress for that story
  4. If no progress: create one using `NarrativeService.start_story()`
  5. Update progress to set `current_node_id` to the unlocked node
  6. Log the unlock event
- Returns additional fields in result:
  - `unlocked_node_id`: The node ID unlocked (if applicable)
  - `unlocked_story_id`: The story ID containing the node (if applicable)

**Key code pattern:**
```python
# Local import to avoid circular dependency
from bot.services.narrative import NarrativeService
narrative_service = NarrativeService(self.session)
success, msg, progress = await narrative_service.start_story(...)
```

### Task 2: Choice Cost Configuration

Added `StoryEditorService.set_choice_cost()` method:

```python
async def set_choice_cost(
    self,
    choice_id: int,
    cost_besitos: int,
    vip_cost_besitos: Optional[int] = None
) -> Tuple[bool, str]
```

- Validates `cost_besitos >= 0`
- Validates `vip_cost_besitos >= 0` if provided
- Fetches StoryChoice by ID
- Updates both cost fields
- Returns `(True, "cost_updated")` on success

### Task 3: Reward Attachment Enhancement

Updated `StoryEditorService.attach_reward_to_node()` method:

- Changed return type to `Tuple[bool, str, Optional[NodeReward]]`
- Added validation that node exists AND is active
- Added validation that reward exists AND is active
- Returns existing `NodeReward` if already attached
- Reactivates soft-deleted associations
- Returns appropriate messages: `"node_not_found"`, `"reward_not_found"`, `"already_attached"`, `"reward_attached"`

### Task 4: Choice Conditions Configuration

Added `StoryEditorService.set_choice_conditions()` method:

```python
async def set_choice_conditions(
    self,
    choice_id: int,
    conditions: List[Dict]
) -> Tuple[bool, str]
```

- Validates each condition:
  - `type` must be one of: `"level"`, `"streak"`, `"product_owned"`, `"total_earned"`
  - `value` must be convertible to int
  - `group` must be >= 0 (0=AND, 1+=OR groups)
- Normalizes conditions to standard format:
  ```python
  {
      "condition_type": str,
      "condition_value": int,
      "condition_group": int
  }
  ```
- Stores as JSON in `choice.conditions`
- Returns `(True, "conditions_updated")` on success

## API Reference

### ShopService

| Method | Returns | Description |
|--------|---------|-------------|
| `purchase_product(...)` | `(bool, str, Dict)` | Now includes `unlocked_node_id` and `unlocked_story_id` in result dict when product unlocks a node |

### StoryEditorService

| Method | Returns | Description |
|--------|---------|-------------|
| `set_choice_cost(choice_id, cost_besitos, vip_cost_besitos)` | `(bool, str)` | Set choice costs and VIP discount |
| `attach_reward_to_node(node_id, reward_id)` | `(bool, str, NodeReward\|None)` | Attach reward to node with full validation |
| `set_choice_conditions(choice_id, conditions)` | `(bool, str)` | Configure choice access conditions |

## Deviations from Plan

None - plan executed exactly as written.

## Auth Gates

None encountered.

## Self-Check: PASSED

- [x] All 4 tasks completed
- [x] All commits created successfully
- [x] Files modified as specified
- [x] Verification commands pass:
  - `grep -n "unlocks_node_id" bot/services/shop.py` - Found
  - `grep -n "set_choice_cost" bot/services/story_editor.py` - Found
  - `grep -n "attach_reward_to_node" bot/services/story_editor.py` - Found
  - `grep -n "set_choice_conditions" bot/services/story_editor.py` - Found

## Commits

- `9d187f9`: feat(30-04): add node unlocking to shop purchase
- `1632126`: feat(30-04): add set_choice_cost method to StoryEditorService
- `bbdd6e5`: feat(30-04): update attach_reward_to_node method signature and validation
- `feef849`: feat(30-04): add set_choice_conditions method to StoryEditorService
