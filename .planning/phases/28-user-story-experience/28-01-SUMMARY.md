---
phase: 28-user-story-experience
plan: 01
name: Story Reading Infrastructure
subsystem: narrative
status: completed

requires:
  - 27-core-narrative-engine/27-01 (Story models)
  - 27-core-narrative-engine/27-02 (NarrativeService)

provides:
  - StoryReadingStates FSM
  - Story keyboard utilities

affects:
  - bot/states/user.py
  - bot/utils/keyboards.py

tech-stack:
  added: []
  patterns:
    - FSM StatesGroup pattern (aiogram)
    - TYPE_CHECKING for circular imports
    - InlineKeyboardMarkup factory functions

key-files:
  created: []
  modified:
    - bot/states/user.py
    - bot/utils/keyboards.py

decisions: []

metrics:
  duration: ~5 minutes
  completed-date: 2026-02-27
  tasks: 3/3
  commits: 2
  files-modified: 2
  lines-added: ~198
---

# Phase 28 Plan 01: Story Reading Infrastructure Summary

## One-Liner
Created foundational FSM states and keyboard utilities for interactive story reading flow.

## What Was Built

### StoryReadingStates (bot/states/user.py)
Four-state FSM for managing story reading flow:

| State | Purpose | Requirements |
|-------|---------|--------------|
| `browsing_stories` | User viewing available stories | NARR-04 |
| `reading_node` | User reading node with choices | NARR-05, NARR-06 |
| `story_completed` | Story finished, showing summary | NARR-10 |
| `confirm_restart` | Confirmation to restart completed story | UX-03 |

State transitions documented in bilingual docstring following project conventions.

### Story Keyboard Utilities (bot/utils/keyboards.py)

Five keyboard factory functions for story UI:

| Function | Purpose | Key Features |
|----------|---------|--------------|
| `get_story_choice_keyboard()` | Choice buttons for story node | Max 3 per row (UX-05), exit button (NARR-08) |
| `get_story_list_keyboard()` | Story list with status badges | 📖🔴⏸️✅ badges per UX-02, 💎 premium indicator |
| `get_story_restart_confirmation_keyboard()` | Yes/No confirmation | UX-03 compliance |
| `get_story_completed_keyboard()` | Post-completion options | Restart or back to list |
| `get_upsell_keyboard()` | Premium upsell | TIER-04 compliance |

Callback data format: `story:{action}:{story_id}:{choice_id}`

## Architecture Decisions

### TYPE_CHECKING Pattern
Added `TYPE_CHECKING` block to avoid circular imports while maintaining type hints:
```python
if TYPE_CHECKING:
    from bot.database.models import Story, StoryChoice, UserStoryProgress
```

### Keyboard Layout (UX-05)
Choice buttons arranged in rows of maximum 3, with exit button always at bottom (escape hatch pattern per NARR-08).

## Commits

| Hash | Message | Files |
|------|---------|-------|
| b220ddc | feat(28-01): add StoryReadingStates FSM states | bot/states/user.py |
| 168057d | feat(28-01): add story keyboard utilities | bot/utils/keyboards.py |

## Verification Results

- [x] StoryReadingStates has 4 states: browsing_stories, reading_node, story_completed, confirm_restart
- [x] Keyboard functions follow existing code patterns and naming conventions
- [x] get_story_choice_keyboard respects max 3 buttons per row (UX-05)
- [x] get_story_choice_keyboard includes exit button (NARR-08)
- [x] get_story_list_keyboard shows status badges (UX-02)
- [x] All callback data follows format "story:{action}:{story_id}:{choice_id}"

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- [x] bot/states/user.py contains StoryReadingStates with 4 required states
- [x] bot/utils/keyboards.py contains 5 story keyboard functions
- [x] Type hints are correct with TYPE_CHECKING imports
- [x] Code follows existing patterns from streak.py and shop.py
- [x] Commits b220ddc and 168057d exist in git log

## Next Steps

Plan 28-02 will implement the story reader handlers using these states and keyboards.
