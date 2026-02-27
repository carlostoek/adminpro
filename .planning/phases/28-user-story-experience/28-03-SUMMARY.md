---
phase: 28-user-story-experience
plan: 03
name: Story Handler Integration
subsystem: narrative
status: completed
tags: [narrative, handlers, integration, menu]
dependency_graph:
  requires:
    - 28-02 (Story Reader Handlers)
    - 28-01 (Story FSM States and Keyboards)
  provides:
    - Integrated story router
    - Menu integration for stories
  affects:
    - bot/handlers/user/__init__.py
    - bot/services/message/user_menu.py
    - bot/handlers/user/story.py
tech_stack:
  added: []
  patterns:
    - Race condition protection with FSM intermediate state
    - Menu integration via message providers
    - Voice architecture consistency (Diana/Lucien)
key_files:
  created: []
  modified:
    - bot/handlers/user/__init__.py (story_router already registered)
    - bot/services/message/user_menu.py (added stories buttons)
    - bot/handlers/user/story.py (added menu handler, race condition protection)
    - bot/states/user.py (added processing_choice state)
decisions:
  - Added stories button to both VIP and Free main menus for easy access
  - Implemented processing_choice FSM state to prevent double-click race conditions
  - Used existing message provider pattern for menu integration
  - Maintained voice architecture consistency throughout
metrics:
  duration: ~10 minutes
  completed_date: 2026-02-27
  tasks: 5/5
  commits: 2
  files_modified: 3
  lines_added: ~50
---

# Phase 28 Plan 03: Story Handler Integration Summary

## One-Liner
Integrated story handlers into bot's router system with menu integration and race condition protection.

## What Was Built

### 1. Menu Integration
- Added "📖 Historias" button to VIP main menu (`_vip_main_menu_keyboard`)
- Added "📖 Historias" button to Free main menu (`_free_main_menu_keyboard`)
- Added `stories:menu` callback handler to route menu clicks to story list

### 2. Race Condition Protection
- Added `processing_choice` state to `StoryReadingStates` FSM
- Updated `handle_make_choice` to:
  - Check if already processing a choice (prevent double-clicks)
  - Set intermediate state while processing
  - Validate progress status is ACTIVE before processing
  - Reset state appropriately on all error paths

### 3. Edge Case Handling
- Added validation for missing progress
- Added validation for inactive story status
- Handle nodes without choices that aren't ending nodes
- Proper state cleanup on errors

## Requirements Verification

All 14 requirements (NARR-04 to UX-06) verified implemented:

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| NARR-04 | ✅ | `cmd_stories`, `handle_start_story`, `handle_stories_menu` |
| NARR-05 | ✅ | Node display with choices in `handle_start_story` |
| NARR-06 | ✅ | `handle_make_choice` with progress saving |
| NARR-07 | ✅ | Resume logic in `start_story` service method |
| NARR-08 | ✅ | `handle_story_exit` escape hatch |
| NARR-10 | ✅ | Completion detection in `handle_make_choice` |
| TIER-02 | ✅ | Free-only story filtering in `get_available_stories` |
| TIER-03 | ✅ | VIP sees Free + Premium stories |
| TIER-04 | ✅ | Upsell message in `handle_start_story` |
| UX-01 | ✅ | `_format_progress_indicator` shows "Escena X de Y" |
| UX-02 | ✅ | Status badges in `get_story_list_keyboard` |
| UX-03 | ✅ | Restart confirmation flow |
| UX-04 | ✅ | Diana (🫦) for content, Lucien (🎩) for system |
| UX-05 | ✅ | Max 3 choices per row in `get_story_choice_keyboard` |
| UX-06 | ✅ | `_display_node_media` handles photos/videos |

## Commits

1. **c1cc766** - `feat(28-03): add stories button to VIP and Free main menus`
   - Added 📖 Historias button to VIP menu keyboard
   - Added 📖 Historias button to Free menu keyboard
   - Added `stories:menu` callback handler

2. **52edb99** - `feat(28-03): add race condition protection and edge case handling`
   - Added `processing_choice` state to StoryReadingStates
   - Updated `handle_make_choice` with race condition protection
   - Added progress status validation
   - Added proper error state management

## Integration Points

### Router Registration (Already Done in 28-02)
```python
# bot/handlers/user/__init__.py
from bot.handlers.user.story import story_router
user_router.include_router(story_router)
__all__ = [..., "story_router"]
```

### Menu Integration
```python
# bot/services/message/user_menu.py
content_buttons = [
    [{"text": "🛍️ Tienda", "callback_data": "shop_catalog"}],
    [{"text": "📖 Historias", "callback_data": "stories:menu"}],  # NEW
    ...
]
```

### Race Condition Protection
```python
# bot/handlers/user/story.py
# Set intermediate state to prevent double-clicks
current_state = await state.get_state()
if current_state == "StoryReadingStates:processing_choice":
    await callback.answer("Procesando...", show_alert=False)
    return

await state.set_state(StoryReadingStates.processing_choice)
# ... process choice ...
await state.set_state(StoryReadingStates.reading_node)  # or completed
```

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check

- [x] story_router is registered in bot/handlers/user/__init__.py
- [x] Story handlers are accessible through the bot
- [x] Edge cases (race conditions, missing progress, etc.) are handled
- [x] All 14 requirements (NARR-04 to UX-06) are implemented
- [x] Menu integration complete for both VIP and Free users
- [x] Voice architecture consistent (Diana for content, Lucien for system)
- [x] FSM state transitions are correct
- [x] Error handling covers all edge cases

## Self-Check: PASSED
