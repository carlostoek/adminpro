---
phase: 29-admin-story-editor
plan: 02
name: Story Management Handlers
completed: 2026-02-28
duration: ~25 minutes
tasks: 5/5
subsystem: narrative

key-files:
  created:
    - bot/handlers/admin/story_management.py (760 lines)
  modified:
    - bot/states/admin.py (+73 lines)
    - bot/handlers/admin/__init__.py (+2 lines)
    - bot/handlers/admin/menu.py (+2 lines)

tech-stack:
  patterns:
    - FSM (Finite State Machine) for multi-step flows
    - Lucien voice (🎩) for all admin messages
    - ServiceContainer dependency injection
    - Soft delete pattern (is_active=False)
  services:
    - StoryEditorService (via container.story_editor)

metrics:
  handlers: 18+
  states: 7
  lines-added: 835
  commits: 3
---

# Phase 29 Plan 02: Story Management Handlers Summary

## Overview

Implemented comprehensive story management handlers for admin CRUD operations, enabling administrators to create, edit, publish, and manage interactive stories through the Telegram bot interface.

## Deliverables

### 1. StoryEditorStates FSM States (bot/states/admin.py)

Added 7 states for story management flows:

| State | Purpose |
|-------|---------|
| `waiting_for_title` | Story creation - title input (1-200 chars) |
| `waiting_for_description` | Story creation - description input (optional, max 1000 chars) |
| `waiting_for_premium` | Story creation - premium flag selection |
| `waiting_for_edit_field` | Story edit - field selection (title/description/premium) |
| `waiting_for_edit_value` | Story edit - new value input |
| `waiting_for_publish_confirm` | Publish confirmation (if validation warnings) |
| `waiting_for_delete_confirm` | Delete confirmation (soft delete) |

### 2. Story Management Handlers (bot/handlers/admin/story_management.py)

Created 760-line module with 18+ handlers:

**Menu & List Handlers:**
- `callback_stories_menu` - Main story management menu
- `callback_story_list` - Paginated story list with status badges
- `callback_story_details` - Story detail view with actions

**Creation Flow (3-step wizard):**
- `callback_story_create_start` - Start creation flow
- `process_story_title` - Handle title input with validation
- `process_story_description` - Handle description (with /skip)
- `callback_story_premium_selected` - Create story with premium flag

**Edit Handlers:**
- `callback_story_edit` - Show edit menu
- `callback_story_edit_title` - Edit title
- `callback_story_edit_description` - Edit description
- `callback_story_edit_premium` - Toggle premium status
- `process_story_edit_value` - Process edit value input

**Publish/Unpublish:**
- `callback_story_publish` - Validate and publish story
- `callback_story_unpublish` - Set back to draft

**Delete:**
- `callback_story_delete` - Show delete confirmation
- `callback_story_delete_confirm` - Soft delete (is_active=False)

**Stats:**
- `callback_story_stats` - Show story statistics (starts, completions, completion rate)

### 3. Visual Indicators

**Status Badges:**
- 🟢 Publicada (Published)
- 🟡 Borrador (Draft)
- ⚠️ Archivada (Archived)
- 🗑️ Eliminada (Deleted/Inactive)

**Premium Indicators:**
- 💎 Premium
- 🆓 Free

### 4. Integration

- Registered `story_router` in `bot/handlers/admin/__init__.py`
- Added "📖 Crear Historia" button to admin menu
- All messages use Lucien voice (🎩) with elegant mayordomo tone
- Uses `StoryEditorService` via `ServiceContainer.story_editor`

## Key Features

1. **Story Creation Wizard**: 3-step flow (title → description → premium)
2. **Validation**: Pre-publish validation using StoryEditorService.validate_story()
3. **Soft Delete**: Only draft stories can be deleted (is_active=False)
4. **Statistics**: Shows total starts, active users, completions, completion rate
5. **Inline Editing**: Edit title, description, or toggle premium status
6. **Status Badges**: Visual indicators for story status in lists

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- ✅ Python syntax check passed
- ✅ StoryEditorStates import works with all 7 states
- ✅ story_router registered in admin/__init__.py
- ✅ Menu button added
- ✅ 760 lines of handler code
- ✅ 18+ callback handlers implemented

## Commits

1. `50f14c0` - feat(29-02): add StoryEditorStates FSM states for story management
2. `36948ed` - feat(29-02): create story_management.py with CRUD handlers
3. `20c3031` - feat(29-02): register story_router and add menu button

## Next Steps

Plan 29-03: Node Management Handlers - Implement handlers for creating and managing story nodes (START, STORY, CHOICE, ENDING) and choices.
