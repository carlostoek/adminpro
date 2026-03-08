---
phase: 30-economy-shop-integration
plan: 03
subsystem: story-handlers
tags: [economy, ui, handlers, choices]
dependency_graph:
  requires: ["30-02"]
  provides: ["30-04", "30-05"]
  affects: ["bot/handlers/user/story.py", "bot/utils/keyboards.py"]
tech_stack:
  added: []
  patterns: ["choice state evaluation", "confirmation dialog flow", "insufficient funds UX"]
key_files:
  created: []
  modified:
    - bot/handlers/user/story.py
    - bot/utils/keyboards.py
decisions:
  - "Lock indicators: 🔒 for costly, 🚫 for condition-locked"
  - "Confirmation dialog shows VIP discount format"
  - "Lucien's voice for insufficient funds with recovery path"
  - "Choice states prepared before keyboard rendering"
metrics:
  duration: "~15 minutes"
  completed_date: "2026-03-08"
  tasks: 5/5
  commits: 5
  files_modified: 2
  lines_added: ~400
---

# Phase 30 Plan 03: User Choice Economy UI Summary

**One-liner:** Implemented user-facing handlers for story choices with cost display, confirmation dialogs, and elegant insufficient balance messages.

## Overview

This plan delivers the UI layer for economy integration in the narrative system. Users now see choice buttons with appropriate lock indicators, receive confirmation dialogs for costly choices with VIP discounts displayed, and get elegant insufficient balance messages with recovery paths.

## Changes Made

### Task 1: Choice Keyboard with Lock Indicators
**File:** `bot/utils/keyboards.py`

Updated `get_story_choice_keyboard()` to accept optional `choice_states` parameter:
- Shows 🔒 emoji for costly choices
- Shows 🚫 emoji for condition-locked choices
- Maintains backward compatibility when `choice_states` is None
- Truncates text appropriately for each indicator type

### Task 2: Choice State Preparation Helper
**File:** `bot/handlers/user/story.py`

Added `_prepare_choice_states()` async helper function:
- Evaluates choice conditions using `container.narrative.evaluate_choice_conditions()`
- Calculates costs with VIP discounts via `container.narrative.calculate_choice_cost()`
- Returns state dicts for keyboard builder
- Determines `available`/`costly`/`condition_locked` states

### Task 3: Choice Confirmation Dialog Handler
**File:** `bot/handlers/user/story.py`

Added `handle_confirm_choice()` callback handler for `story:confirm` callbacks:
- Shows cost and VIP discount in confirmation dialog
- Handles balance check before charging
- Deducts besitos and processes choice
- Shows target node content after confirmation
- Handles story completion flow

### Task 4: Insufficient Funds Handler
**File:** `bot/handlers/user/story.py`

Added elegant insufficient funds UX:
- `_get_insufficient_funds_message()` with Lucien's voice
- `handle_insufficient_funds()` async function
- Recovery keyboard with daily gift and economy info buttons
- Allows returning to the story

### Task 5: Updated Choice Selection Flow
**File:** `bot/handlers/user/story.py`

Updated `handle_make_choice()` to integrate economy flow:
- Condition checks before processing
- Confirmation dialog for costly choices
- Added `handle_back_to_story()` handler for cancel flow
- Updated `handle_start_story()` to use choice states
- Process free choices immediately, costly ones with confirmation

## User Flow

```
User sees node with choices
    ↓
Choices displayed with indicators:
  - 🔒 for costly choices
  - 🚫 for condition-locked
  - No indicator for available
    ↓
User selects costly choice
    ↓
Confirmation dialog appears:
  "🎩 Confirmar decisión

   [Choice text]

   Costo: 40 besitos (VIP: era 50)
   Tu balance: 100 besitos

   ¿Desea proceder?"
    ↓
User confirms
    ↓
Balance checked → Charge applied → Choice processed
    ↓
Show target node with new choices
```

## Insufficient Funds Flow

```
User selects costly choice (cost: 50)
    ↓
Balance check: 30 besitos available
    ↓
Show elegant message:
  "🎩 Atención

   Para esta decisión necesita hacer una
   inversión de 50 besitos, ahora cuenta
   con 30 besitos.

   Le sugiero que vaya a reclamar su
   regalo del día, tal vez con eso
   pueda acceder."
    ↓
Recovery keyboard:
  - 🎁 Ir a regalo diario
  - 💰 Cómo ganar besitos
  - 🔙 Volver a la historia
```

## API Changes

### Keyboard Builder
```python
def get_story_choice_keyboard(
    story_id: int,
    choices: List[StoryChoice],
    show_exit: bool = True,
    choice_states: Optional[List[Dict]] = None  # NEW
) -> InlineKeyboardMarkup
```

### Choice State Dict
```python
{
    "choice_id": int,
    "state": "available" | "costly" | "condition_locked",
    "cost": int,
    "vip_cost": int,
    "missing_requirements": List[str]
}
```

## Verification

- [x] Choice keyboards show 🔒 for costly and 🚫 for condition-locked choices
- [x] Cost is displayed in confirmation dialog with VIP discount format
- [x] Insufficient balance shows Lucien's voice message with recovery path
- [x] Confirmation dialog appears before charging for costly choices
- [x] Batched reward notification shown after reaching node (handled in 30-02)

## Commits

| Hash | Message |
|------|---------|
| d6da797 | feat(30-03): update choice keyboard with lock indicators |
| a91d435 | feat(30-03): add choice state preparation helper |
| 0a74bd0 | feat(30-03): add choice confirmation dialog handler |
| 4bc1410 | feat(30-03): add insufficient funds handler |
| bc7cadf | feat(30-03): update choice selection with economy flow |

## Deviations from Plan

None - plan executed exactly as written.

## Next Steps

Plan 30-04 (Node Reward Delivery) can now leverage these handlers to show reward notifications when users reach nodes with attached rewards.
