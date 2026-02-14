---
phase: 23
plan: 01
subsystem: rewards-system
tags: [database, sqlalchemy, enums, models, gamification]

dependency_graph:
  requires: [22-04]
  provides: [reward-database-foundation]
  affects: [23-02, 23-03, 23-04]

tech-stack:
  added:
    - RewardType enum
    - RewardConditionType enum
    - RewardStatus enum
    - Reward model
    - RewardCondition model
    - UserReward model
  patterns:
    - SQLAlchemy declarative models
    - Enum with display_name and emoji properties
    - One-to-many relationships with back_populates
    - Composite indexes for query optimization

key-files:
  created: []
  modified:
    - bot/database/enums.py
    - bot/database/models.py

decisions:
  - id: D23-01-001
    title: Reward condition group logic
    context: Need to support both AND and OR logic for reward conditions
    decision: Use condition_group field where 0 = AND (all must pass), >0 = OR (at least one in group must pass)
    consequences: Flexible condition system allowing complex unlock requirements
  - id: D23-01-002
    title: Repeatable rewards tracking
    context: Some rewards should be claimable multiple times
    decision: Add is_repeatable flag and claim_count/last_claimed_at fields to UserReward
    consequences: Supports recurring achievements and loyalty programs
  - id: D23-01-003
    title: Secret rewards
    context: Some rewards should be hidden until unlocked (surprise achievements)
    decision: Add is_secret flag to Reward model
    consequences: Enables gamification surprise elements and discovery mechanics
  - id: D23-01-004
    title: Claim window expiration
    context: Rewards should have limited time to claim after unlocking
    decision: Add claim_window_hours to Reward and expires_at to UserReward
    consequences: Creates urgency and prevents reward hoarding

metrics:
  duration: 135
  completed: 2026-02-14
---

# Phase 23 Plan 01: Rewards System Database Foundation Summary

## Overview

Created the database foundation for the Rewards System with three new enums and three new models following existing SQLAlchemy patterns in the codebase.

## Changes Made

### Enums Added (bot/database/enums.py)

1. **RewardType** - Types of rewards:
   - `BESITOS`: Virtual currency reward (💰)
   - `CONTENT`: Content unlock (ContentSet) (🎁)
   - `BADGE`: Achievement badge (cosmetic) (🏆)
   - `VIP_EXTENSION`: Extend VIP subscription (⭐)

2. **RewardConditionType** - Condition types for eligibility:
   - `STREAK_LENGTH`: Current streak >= value
   - `TOTAL_POINTS`: total_earned >= value
   - `LEVEL_REACHED`: level >= value
   - `BESITOS_SPENT`: total_spent >= value
   - `FIRST_PURCHASE`: Has made at least one shop purchase
   - `FIRST_DAILY_GIFT`: Has claimed daily gift at least once
   - `FIRST_REACTION`: Has reacted to content at least once
   - `NOT_VIP`: User is not VIP (exclusion condition)
   - `NOT_CLAIMED_BEFORE`: Has not claimed this reward before

3. **RewardStatus** - Status of reward for a user:
   - `LOCKED`: Conditions not met (🔒)
   - `UNLOCKED`: Conditions met, available to claim (🔓)
   - `CLAIMED`: Already claimed (✅)
   - `EXPIRED`: Claim window passed (⏰)

### Models Added (bot/database/models.py)

1. **Reward Model** (`rewards` table):
   - Core reward definition with name, description, type
   - `reward_value`: JSON field for type-specific data
   - `is_repeatable`: Allow multiple claims
   - `is_secret`: Hidden until unlocked
   - `claim_window_hours`: Time limit to claim (default 168 = 7 days)
   - `is_active` + `sort_order`: For catalog management
   - Relationships: `conditions` (one-to-many), `user_rewards` (one-to-many)
   - Indexes: `idx_reward_active_type`, `idx_reward_sort`

2. **RewardCondition Model** (`reward_conditions` table):
   - Links to reward via `reward_id`
   - `condition_type`: Type of condition check
   - `condition_value`: Numeric threshold (for comparison conditions)
   - `condition_group`: Logic grouping (0 = AND, >0 = OR)
   - `sort_order`: Evaluation order
   - Relationships: `reward` (many-to-one)
   - Indexes: `idx_condition_reward`, `idx_condition_type`

3. **UserReward Model** (`user_rewards` table):
   - Tracks user progress toward each reward
   - `status`: LOCKED/UNLOCKED/CLAIMED/EXPIRED
   - `unlocked_at`: When conditions were first met
   - `claimed_at`: When user claimed the reward
   - `expires_at`: Claim deadline
   - `claim_count` + `last_claimed_at`: For repeatable rewards
   - Relationships: `reward` (many-to-one)
   - Indexes: `idx_user_reward_user_reward` (unique), `idx_user_reward_user_status`, `idx_user_reward_unlocked`, `idx_user_reward_expires`

## Key Design Decisions

### Condition Logic Groups
The `condition_group` field enables complex unlock requirements:
- Group 0: All conditions must pass (AND logic)
- Groups 1, 2, etc.: At least one condition in the group must pass (OR logic)

Example: A reward could require (level >= 5 AND total_earned >= 1000) OR (streak >= 30)

### Repeatable Rewards
The `is_repeatable` flag on Reward combined with `claim_count` on UserReward allows:
- One-time achievements (is_repeatable=False, claim_count 0 or 1)
- Daily/weekly recurring rewards (is_repeatable=True, claim_count tracked)
- Loyalty program milestones (claim every N days)

### Secret Rewards
The `is_secret` flag enables:
- Easter egg achievements
- Surprise milestones
- Hidden loyalty tiers
- Discovery-based gamification

## Verification

All verification criteria met:
- [x] RewardType, RewardConditionType, RewardStatus enums added
- [x] Reward model with conditions and user_rewards relationships
- [x] RewardCondition model with reward relationship
- [x] UserReward model with reward relationship
- [x] All fields, indexes, and constraints properly defined
- [x] Models follow existing SQLAlchemy patterns

## Commits

1. `2c514d0` - feat(23-01): add reward system enums
2. `58008e2` - feat(23-01): add reward system models

## Next Steps

This plan provides the foundation for:
- Plan 23-02: Reward Service Implementation
- Plan 23-03: Reward Evaluation Engine
- Plan 23-04: User Reward Handlers
