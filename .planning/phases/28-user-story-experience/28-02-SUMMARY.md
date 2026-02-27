---
phase: 28-user-story-experience
plan: 02
name: Story Reader Handlers
subsystem: narrative
status: completed
completed_at: 2026-02-27
tags: [handlers, narrative, story-reading, fsm]
dependency_graph:
  requires: ["28-01", "27-02", "27-04"]
  provides: ["story-reading-flow"]
  affects: ["user-experience"]
tech_stack:
  added: []
  patterns:
    - Voice Architecture (Lucien/Diana)
    - FSM State Management
    - Router Pattern with Middleware
    - Service Container Injection
key_files:
  created:
    - bot/handlers/user/story.py
  modified:
    - bot/handlers/user/__init__.py
decisions:
  - Voice architecture: Lucien (🎩) for system messages, Diana (🫦) for content nodes
  - Single-file handler with 7 handler functions
  - Media display supports single photo, multiple photos (media group), and text-only nodes
  - Escape hatch (exit button) on every reading node
metrics:
  duration_minutes: ~15
  tasks_completed: 7
  commits: 2
  files_created: 1
  files_modified: 1
  lines_added: ~625
---

# Phase 28 Plan 02: Story Reader Handlers Summary

## Overview

Complete implementation of story reading handlers for the interactive narrative system. This delivers the user-facing reading experience with tier filtering, progress tracking, escape hatch, and voice-appropriate messaging.

## Deliverables

### 1. Story Handler (`bot/handlers/user/story.py`)

**621 lines** implementing 7 handlers and helper functions:

#### Handlers:
| Handler | Purpose | Requirements |
|---------|---------|--------------|
| `cmd_stories` | /stories command - list available stories | NARR-04, TIER-02, TIER-03 |
| `handle_start_story` | Start/resume story from list | NARR-04, NARR-07, UX-03, TIER-04 |
| `handle_make_choice` | Process user choice selection | NARR-06, NARR-10 |
| `handle_story_exit` | Escape hatch to exit story | NARR-08 |
| `handle_back_to_list` | Return to story list | Navigation |
| `handle_restart_request` | Show restart confirmation | UX-03 |
| `handle_confirm_restart` | Confirm and restart completed story | UX-03 |

#### Voice Helpers:
- **Lucien (🎩)**: `_get_lucien_header()`, `_get_story_list_header()`, `_get_empty_stories_message()`, `_get_upsell_message()`, `_get_restart_confirmation_message()`, `_get_story_completed_message()`, `_get_exit_message()`, `_get_error_message()`
- **Diana (🫦)**: `_get_diana_header()`, `_format_node_content()`

#### Utility Helpers:
- `_format_progress_indicator()` - Shows "Escena X de Y" progress
- `_get_status_badge()` - Returns emoji badge for story status
- `_display_node_media()` - Handles single photo, media group, or text-only nodes

### 2. Router Registration (`bot/handlers/user/__init__.py`)

- Imported `story_router` from story.py
- Included router in `user_router`
- Added to `__all__` exports

## Requirements Mapping

### NARR (Narrative Core)
| Requirement | Status | Implementation |
|-------------|--------|----------------|
| NARR-04 | ✅ | `cmd_stories` shows list, `handle_start_story` starts stories |
| NARR-05 | ✅ | Node content displayed with `_format_node_content` |
| NARR-06 | ✅ | `handle_make_choice` processes choices and saves progress |
| NARR-07 | ✅ | `start_story` service method handles resume |
| NARR-08 | ✅ | Escape hatch button on every node via `get_story_choice_keyboard` |
| NARR-10 | ✅ | Completion detection and message in `handle_make_choice` |

### TIER (Tiered Access)
| Requirement | Status | Implementation |
|-------------|--------|----------------|
| TIER-02 | ✅ | `get_available_stories` filters by `is_premium_user` |
| TIER-03 | ✅ | VIP users see all stories, Free users see only non-premium |
| TIER-04 | ✅ | Upsell message and keyboard for premium content attempt |

### UX (User Experience)
| Requirement | Status | Implementation |
|-------------|--------|----------------|
| UX-01 | ✅ | Progress indicator "Escena X de Y" |
| UX-02 | ✅ | Status badges (📖🔴⏸️✅🚪) in story list |
| UX-03 | ✅ | Restart confirmation flow with Yes/No keyboard |

## Voice Architecture

### Lucien (🎩) - System Messages
Used for all system-level communication:
- Story list header
- Empty stories message
- Upsell for premium content
- Restart confirmation
- Story completed message
- Exit message
- Error messages

### Diana (🫦) - Content Nodes
Used for narrative content:
- Node content text
- Progress indicator footer
- "Continúa cuando estés lista..." prompt after media groups

## Key Design Decisions

1. **Single File Organization**: All story handlers in one file for maintainability
2. **Media Display Flexibility**: `_display_node_media` handles text-only, single photo, and media group scenarios
3. **Progress Placeholder**: Uses hardcoded 12 nodes for progress indicator (will be enhanced when story total nodes available)
4. **Error Handling**: All handlers wrapped in try-except with Lucien error messages
5. **FSM Integration**: Proper state transitions between browsing_stories → reading_node → story_completed

## Testing Notes

The handlers integrate with:
- `NarrativeService` for story operations
- `StoryReadingStates` for FSM management
- Keyboard utilities from `bot/utils/keyboards.py`
- ServiceContainer for dependency injection

## Commits

1. `977393b` - feat(28-02): implement story reading handlers
2. `b3fb243` - feat(28-02): register story_router in user handlers

## Next Steps

Plan 28-03 (Story Progress Tracking) will build on these handlers to add:
- Detailed progress analytics
- Reading time tracking
- Choice history visualization
