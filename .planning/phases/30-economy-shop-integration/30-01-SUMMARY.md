---
phase: 30-economy-shop-integration
plan: 01
subsystem: economy-integration
completed: 2026-03-08
duration: ~10 minutes
tags: [economy, database, models, narrative, service-injection]
dependency_graph:
  requires: []
  provides: [30-02, 30-03, 30-04]
  affects: [bot/database/enums.py, bot/database/models.py, bot/services/narrative.py]
tech_stack:
  added: []
  patterns: [service-injection, cascading-conditions]
key_files:
  created: []
  modified:
    - bot/database/enums.py
    - bot/database/models.py
    - bot/services/narrative.py
decisions:
  - "TransactionType extended with story economy types for audit trail"
  - "StoryChoice.vip_cost_besitos allows VIP-specific pricing (null = use regular price)"
  - "ShopProduct.unlocks_node_id enables shop-to-narrative linkage"
  - "NarrativeService uses optional service injection following RewardService pattern"
metrics:
  tasks_completed: 5
  commits: 5
  files_modified: 3
  lines_added: ~320
---

# Phase 30 Plan 01: Economy Integration Foundation Summary

**One-liner:** Extended database models and NarrativeService with economy integration foundation supporting choice costs, VIP discounts, shop-node linkage, and service injection patterns.

## What Was Built

### 1. TransactionType Enum Extension (Task 1)
Added two new transaction types for story economy audit trail:
- `SPEND_STORY_CHOICE` - When users spend besitos on story choices
- `EARN_STORY_COMPLETION` - When users earn besitos from completing stories

Both include proper display names in Spanish for UI consistency.

### 2. StoryChoice VIP Pricing (Task 2)
Extended `StoryChoice` model with VIP discount support:
- Added `vip_cost_besitos` column (nullable Integer)
- Updated `is_free` property to consider both `cost_besitos` and `vip_cost_besitos`
- If `vip_cost_besitos` is null, VIP users pay the regular price

### 3. Shop-Node Linkage (Task 3)
Extended `ShopProduct` model to unlock story nodes on purchase:
- Added `unlocks_node_id` foreign key to `story_nodes` with `SET NULL` on delete
- Added index on `unlocks_node_id` for efficient queries
- Added `unlocked_node` relationship for easy navigation

### 4. Service Injection Pattern (Task 4)
Extended `NarrativeService.__init__` to accept optional service dependencies:
- `wallet_service` - For balance checks, spending, and level queries
- `reward_service` - For claiming node/choice rewards
- `shop_service` - For product ownership verification
- `streak_service` - For streak-based condition checking

Follows the same pattern as `RewardService` for consistency.

### 5. Choice Condition Evaluation (Task 5)
Added comprehensive condition evaluation system:
- `evaluate_choice_conditions()` - Cascading AND/OR logic matching RewardService
- `calculate_choice_cost()` - VIP-aware cost calculation
- `_format_requirement_message()` - Lucien's voice for requirement messages
- Helper methods for each condition type:
  - `_check_level_condition()` - Uses wallet_service
  - `_check_streak_condition()` - Uses streak_service
  - `_check_product_condition()` - Uses shop_service
  - `_check_total_earned_condition()` - Uses wallet_service

## Verification Results

All verification checks passed:
- TransactionType enum includes both new types with proper display names
- StoryChoice model has vip_cost_besitos field and updated is_free property
- ShopProduct model has unlocks_node_id field with foreign key and relationship
- NarrativeService accepts and stores wallet, reward, shop, and streak service dependencies
- NarrativeService has evaluate_choice_conditions, calculate_choice_cost, and _format_requirement_message methods

## Key Design Decisions

1. **Optional VIP Pricing**: `vip_cost_besitos` is nullable - if null, VIP users pay regular price. This allows selective VIP discounts rather than requiring them on all choices.

2. **Service Injection Pattern**: Services are optional parameters (default None) to maintain backward compatibility and allow gradual integration.

3. **Fail-Open Condition Evaluation**: If a service is not available or an error occurs during condition checking, the condition passes (returns True). This prevents blocking users due to infrastructure issues.

4. **Cascading AND/OR Logic**: Group 0 uses AND (all must pass), groups 1+ use OR (at least one must pass). Matches the existing RewardService pattern for consistency.

5. **Lucien's Voice**: Requirement messages use formal, elegant language consistent with the mayordomo character.

## Integration Points

These changes enable:
- **Plan 02**: Choice cost processing with wallet deductions
- **Plan 03**: Node reward delivery via reward_service
- **Plan 04**: Shop product unlocking story nodes

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- [x] TransactionType enum has SPEND_STORY_CHOICE and EARN_STORY_COMPLETION
- [x] StoryChoice model has vip_cost_besitos field
- [x] ShopProduct model has unlocks_node_id field with foreign key
- [x] NarrativeService accepts wallet, reward, shop, and streak services
- [x] NarrativeService has evaluate_choice_conditions method
- [x] NarrativeService has calculate_choice_cost method
- [x] All commits created with proper messages
- [x] SUMMARY.md created in plan directory

## Commits

| Hash | Message |
|------|---------|
| 719652c | feat(30-01): extend TransactionType enum with story economy types |
| dc476f0 | feat(30-01): add vip_cost_besitos field to StoryChoice model |
| ab7283e | feat(30-01): add unlocks_node_id field to ShopProduct model |
| fe3d060 | feat(30-01): extend NarrativeService with service injection |
| 8749d0d | feat(30-01): add choice condition evaluation methods to NarrativeService |
