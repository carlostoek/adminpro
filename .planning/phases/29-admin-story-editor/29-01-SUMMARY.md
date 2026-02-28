---
phase: 29-admin-story-editor
plan: 01
subsystem: database
status: completed
dependencies: []

key-decisions:
  - Reused RewardConditionType enum for NodeCondition to maintain consistency
  - Used condition_group pattern (0=AND, 1+=OR) matching RewardCondition model
  - Added is_active flag to NodeReward for soft-disable without deletion
  - Added unique constraint on (node_id, reward_id) to prevent duplicate associations

tech-stack:
  added: []
  patterns:
    - "SQLAlchemy ORM with declarative base"
    - "Cascade delete for node conditions and rewards"
    - "Junction table pattern for many-to-many relationships"

key-files:
  created: []
  modified:
    - bot/database/enums.py
    - bot/database/models.py

metrics:
  duration: 10 minutes
  tasks: 3/3
  commits: 3
  files_modified: 2
  lines_added: ~176
---

# Phase 29 Plan 01: Node Conditions and Rewards Summary

Extended database models to support node-level conditions and rewards for the admin story editor.

## Deliverables

### 1. PRODUCT_OWNED Condition Type

Added `PRODUCT_OWNED` to `RewardConditionType` enum in `bot/database/enums.py`:
- Enables checking if user owns a specific shop product
- Added display name: "Producto comprado"
- Updated docstring with condition description

### 2. NodeCondition Model

Created `NodeCondition` model in `bot/database/models.py`:

**Fields:**
- `id`: Integer primary key
- `node_id`: ForeignKey to story_nodes.id (CASCADE delete)
- `condition_type`: Enum(RewardConditionType)
- `condition_value`: Integer nullable (threshold value)
- `condition_group`: Integer default=0 (0=AND, 1+=OR)
- `is_active`: Boolean default=True
- `created_at`: DateTime default=utcnow

**Relationships:**
- `NodeCondition.node` -> `StoryNode`
- `StoryNode.conditions` -> List[NodeCondition] (cascade delete)

**Indexes:**
- `idx_node_condition_node`: (node_id, is_active)
- `idx_node_condition_type`: (condition_type, is_active)

### 3. NodeReward Junction Table

Created `NodeReward` model in `bot/database/models.py`:

**Fields:**
- `id`: Integer primary key
- `node_id`: ForeignKey to story_nodes.id (CASCADE delete)
- `reward_id`: ForeignKey to rewards.id (CASCADE delete)
- `is_active`: Boolean default=True (soft-disable support)
- `created_at`: DateTime default=utcnow

**Relationships:**
- `NodeReward.node` -> `StoryNode`
- `NodeReward.reward` -> `Reward`
- `StoryNode.attached_rewards` -> List[NodeReward] (cascade delete)
- `Reward.node_rewards` -> List[NodeReward] (cascade delete)

**Constraints:**
- Unique index on (node_id, reward_id) to prevent duplicates
- `idx_node_reward_node`: (node_id, is_active)
- `idx_node_reward_reward`: (reward_id, is_active)

## Commits

| Hash | Message |
|------|---------|
| 344314c | feat(29-01): add PRODUCT_OWNED to RewardConditionType enum |
| 001a34a | feat(29-01): create NodeCondition model for node-level access conditions |
| 981aa28 | feat(29-01): create NodeReward junction table for node-reward associations |

## Verification

- Python syntax check: PASSED
- Import verification: PASSED
- All model fields verified: PASSED
- All relationships verified: PASSED

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- [x] PRODUCT_OWNED exists in RewardConditionType enum
- [x] NodeCondition model created with all required fields
- [x] NodeReward junction table created with unique constraint
- [x] All relationships defined (StoryNode.conditions, StoryNode.attached_rewards, Reward.node_rewards)
- [x] All commits exist and are properly formatted
- [x] Python syntax valid
- [x] Imports work correctly
