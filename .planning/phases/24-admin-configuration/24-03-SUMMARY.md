---
phase: 24-admin-configuration
plan: 03
name: Reward Management Handlers
subsystem: admin
tags: [rewards, handlers, admin, fsm]
dependencies:
  requires: ["24-02"]
  provides: ["admin:rewards", "admin:reward:create", "admin:reward:condition:add"]
tech-stack:
  added: []
  patterns: [FSM, InlineKeyboard, LucienVoice]
key-files:
  created:
    - bot/handlers/admin/reward_management.py
  modified:
    - bot/states/admin.py
    - bot/handlers/admin/__init__.py
    - bot/services/message/admin_main.py
decisions: []
metrics:
  duration: 15
  tasks-completed: 2
  files-created: 1
  files-modified: 3
  lines-added: ~650
---

# Phase 24 Plan 03: Reward Management Handlers Summary

**Reward management handlers with cascading condition creation and inline condition management.**

## Overview

Implemented comprehensive admin handlers for reward and condition management, allowing administrators to create rewards with integrated condition creation flows. The implementation follows the established FSM pattern and maintains Lucien's voice (🎩) throughout all interactions.

## Tasks Completed

### Task 1: Create Reward Management Handler Module

**Files Created:**
- `bot/handlers/admin/reward_management.py` (~650 lines)

**Files Modified:**
- `bot/states/admin.py` - Added RewardCreateState and RewardConditionState

**Features Implemented:**

1. **Main Menu Handler** (`admin:rewards`)
   - Lucien's voice (🎩) for all messages
   - Options: Create Reward, List Rewards, Back

2. **Reward List Handler** (`admin:reward:list`)
   - Paginated display (5 per page)
   - Type emojis: 💰 BESITOS, 🎁 CONTENT, 🏆 BADGE, ⭐ VIP_EXTENSION
   - Status emojis: 🟢 Active, 🔴 Inactive, 🔒 Secret
   - Toggle button per reward

3. **Reward Details Handler** (`admin:reward:details:{id}`)
   - Full reward information display
   - Condition list with values
   - Actions: Add Condition, Toggle, Delete

4. **Toggle Reward Handler** (`admin:reward:toggle:{id}`)
   - Toggle is_active status
   - Confirmation with new status

5. **Create Reward Flow** (8-step FSM)
   - Step 1: Name input (validation: non-empty, max 200 chars)
   - Step 2: Description input (optional, max 1000 chars)
   - Step 3: Type selection (BESITOS, CONTENT, BADGE, VIP_EXTENSION)
   - Step 4: Value input (type-specific validation)
   - Step 5-7: Behavior configuration (repeatable, secret, claim window)
   - Step 8: Create reward with optional condition creation

6. **Inline Condition Creation Flow**
   - Condition type selection with categories (Numeric, Event, Exclusion)
   - Value input for numeric conditions (validated ranges)
   - Group selection for AND/OR logic
   - Support for adding multiple conditions

7. **Delete Reward Handler**
   - Confirmation dialog
   - Cascade delete for conditions

### Task 2: Register Router and Add Menu Button

**Files Modified:**
- `bot/handlers/admin/__init__.py` - Import and include reward_router
- `bot/services/message/admin_main.py` - Add 🏆 Recompensas button

**Integration:**
- Reward router registered in admin router
- Menu button positioned between Tienda and Intereses
- Callback data: `admin:rewards`

## State Classes Added

```python
class RewardCreateState(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_type = State()
    waiting_for_besitos_amount = State()
    waiting_for_content_set = State()
    waiting_for_badge_name = State()
    waiting_for_badge_emoji = State()
    waiting_for_vip_days = State()
    waiting_for_behavior = State()
    waiting_for_repeatable = State()
    waiting_for_secret = State()
    waiting_for_claim_window = State()
    waiting_for_conditions = State()

class RewardConditionState(StatesGroup):
    waiting_for_type = State()
    waiting_for_value = State()
    waiting_for_group = State()
```

## Handlers Implemented

| Handler | Callback/State | Description |
|---------|---------------|-------------|
| `callback_rewards_menu` | `admin:rewards` | Main reward management menu |
| `callback_reward_list` | `admin:reward:list` | Paginated reward list |
| `callback_reward_details` | `admin:reward:details:{id}` | Reward detail view |
| `callback_reward_toggle` | `admin:reward:toggle:{id}` | Toggle active status |
| `callback_reward_create_start` | `admin:reward:create:start` | Start creation flow |
| `process_reward_name` | `waiting_for_name` | Name input handler |
| `process_reward_description` | `waiting_for_description` | Description input |
| `callback_reward_type_selected` | `reward_type:{type}` | Type selection |
| `process_besitos_amount` | `waiting_for_besitos_amount` | Besitos value |
| `process_badge_name` | `waiting_for_badge_name` | Badge name |
| `process_badge_emoji` | `waiting_for_badge_emoji` | Badge emoji |
| `process_vip_days` | `waiting_for_vip_days` | VIP days |
| `callback_repeatable_selected` | `reward:repeatable:{yes/no}` | Repeatable config |
| `callback_secret_selected` | `reward:secret:{yes/no}` | Secret config |
| `callback_window_selected` | `reward:window:{hours}` | Claim window |
| `callback_reward_delete` | `admin:reward:delete:{id}` | Delete confirmation |
| `callback_reward_delete_confirm` | `admin:reward:delete:confirm:{id}` | Confirm delete |
| `callback_condition_add` | `admin:reward:condition:add:{id}` | Add condition |
| `callback_condition_type_selected` | `cond_type:{type}` | Condition type |
| `process_condition_value` | `waiting_for_value` | Condition value |
| `callback_group_selected` | `cond_group:{group}` | Group selection |

## Helper Functions

- `format_reward_value()` - Format reward value for display
- `get_condition_type_display()` - Human-readable condition names
- `validate_condition_value()` - Validate value ranges
- `get_reward_status_emoji()` - Status emoji helper
- `show_behavior_config()` - Behavior configuration UI
- `show_group_selection()` - Group selection UI

## Validation Rules

### Reward Values
- BESITOS: 10-1000
- VIP_EXTENSION: 1-30 days
- CONTENT: Valid ContentSet ID
- BADGE: Non-empty name and emoji

### Condition Values
- STREAK_LENGTH: 1-365
- TOTAL_POINTS: 1-100000
- LEVEL_REACHED: 1-100
- BESITOS_SPENT: 1-100000

## Voice Consistency

All messages use Lucien's voice (🎩):
- Formal mayordomo tone
- Third person/usted
- Elegant terminology
- Emoji 🎩 as signature

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Hash | Message |
|------|---------|
| [existing] | feat(24-03): create reward management handlers with FSM flows |
| 00f5513 | feat(24-03): register reward router and add menu button |

## Verification

- [x] Rewards menu displays correctly with Lucien's voice
- [x] Reward list shows all rewards with pagination
- [x] Reward creation flow works through all FSM states
- [x] Type-specific value inputs work correctly
- [x] Inline condition creation works during reward creation
- [x] Standalone condition addition works from reward details
- [x] Condition groups (AND/OR) work correctly
- [x] Toggle activation works and persists
- [x] Router registered in admin/__init__.py
- [x] Menu button added to admin main menu

## Next Steps

Plan 24-03 is complete. The reward management system is now fully integrated into the admin interface, allowing administrators to:
- Create and manage rewards
- Configure conditions with AND/OR logic
- Toggle reward activation
- Delete rewards with confirmation

The system is ready for use and all handlers are registered and functional.
