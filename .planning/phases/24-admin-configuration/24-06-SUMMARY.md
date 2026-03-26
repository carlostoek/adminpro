---
phase: 24-admin-configuration
plan: "06"
subsystem: admin
tags: [contentset, crud, fsm, handlers]
dependency_graph:
  requires: ["24-02"]
  provides: ["shop-product-creation"]
  affects: ["bot/handlers/admin"]
tech-stack:
  added: []
  patterns: ["FSM Wizard", "CRUD Handlers", "File Upload via Forward"]
key-files:
  created:
    - bot/handlers/admin/content_set_management.py
  modified:
    - bot/states/admin.py
    - bot/handlers/admin/__init__.py
    - bot/services/message/admin_main.py
decisions: []
metrics:
  duration: 15
  completed_date: 2026-02-20
---

# Phase 24 Plan 06: ContentSet Management Handlers

**Objective:** Create ContentSet management handlers to enable product creation in shop.

**Purpose:** The shop product creation wizard requires ContentSets to exist, but there was no admin interface to create them. This gap blocked the entire product creation flow.

## Summary

Completed ContentSet CRUD module with menu integration. Admin can now create, list, view, toggle, and delete ContentSets through a 6-step FSM wizard with file upload support.

## Tasks Completed

### Task 1: Create ContentSetCreateState FSM states
**Status:** ✅ Complete
**Commit:** `128160f`

Added `ContentSetCreateState` StatesGroup to `bot/states/admin.py` with 6 states:
- `waiting_for_name` - Nombre del ContentSet (requerido)
- `waiting_for_description` - Descripción (opcional)
- `waiting_for_content_type` - Tipo de contenido via botones
- `waiting_for_tier` - Tier via botones
- `waiting_for_files` - Recolectando file_ids de mensajes forwarded
- `waiting_for_confirmation` - Confirmación final

### Task 2: Create content_set_management.py handlers
**Status:** ✅ Complete
**Commit:** `6c34fb3`

Created comprehensive CRUD handlers (899 lines):

**Menu Handler:**
- `callback_admin_content_sets` - Main menu with create/list options

**List Handlers:**
- `callback_content_set_list` - Paginated list (5 items per page)
- `callback_content_set_list_page` - Navigation between pages
- `_show_content_set_list` - Helper for rendering list

**Detail Handlers:**
- `callback_content_set_details` - Full ContentSet info display
- `callback_content_set_toggle` - Activate/deactivate toggle
- `callback_content_set_delete` - Delete confirmation dialog
- `callback_content_set_delete_confirm` - Execute deletion

**FSM Creation Wizard:**
- `callback_content_set_create_start` - Initialize FSM
- `process_content_set_name` - Name validation (max 200 chars)
- `process_content_set_description` - Optional description with /skip
- `process_content_set_type` - Content type buttons (photo/video/audio/mixed)
- `process_content_set_tier` - Tier buttons (free/vip/premium/gift)
- `process_content_set_file` - File extraction from forwarded messages
- `process_content_set_done` - /done command to finish upload
- `process_content_set_creation` - Final creation and DB persistence

**File Extraction Support:**
- Photos: `message.photo[-1].file_id`
- Videos: `message.video.file_id`
- Audio: `message.audio.file_id`
- Voice: `message.voice.file_id`

**Voice:** All messages use Lucien's formal mayordomo tone (🎩)

### Task 3: Register router and add menu button
**Status:** ✅ Complete
**Commit:** `3418f71`

- Imported `content_set_router` in `bot/handlers/admin/__init__.py`
- Added `admin_router.include_router(content_set_router)` before user_gamification_router
- Added `📁 ContentSets` button to admin main menu between "Paquetes de Contenido" and "Tienda"

## Verification

All verification criteria met:
- ✅ Import ContentSetCreateState in content_set_management.py works
- ✅ All callbacks follow pattern: admin:content_sets:*
- ✅ File extraction handles photo, video, audio, voice message types
- ✅ Lucien's voice (🎩) used consistently
- ✅ Menu button appears in admin main menu

## Success Criteria

- ✅ Admin can click "📁 ContentSets" in main menu
- ✅ Admin can create ContentSet via 6-step FSM wizard
- ✅ Admin can list and view ContentSet details
- ✅ Admin can toggle ContentSet active status
- ✅ Shop product creation wizard can find ContentSets

## Files Modified

| File | Lines | Changes |
|------|-------|---------|
| bot/states/admin.py | +37 | Added ContentSetCreateState class |
| bot/handlers/admin/content_set_management.py | +899 | New CRUD handlers file |
| bot/handlers/admin/__init__.py | +2 | Import and include router |
| bot/services/message/admin_main.py | +1 | Add menu button |

## Commits

1. `128160f` - feat(24-06): add ContentSetCreateState FSM states
2. `6c34fb3` - feat(24-06): create ContentSet management handlers
3. `3418f71` - feat(24-06): register ContentSet router and add menu button

## Deviations from Plan

None - plan executed exactly as written.

## Auth Gates

None encountered.

## Self-Check

- ✅ All created files exist
- ✅ All commits recorded
- ✅ Router properly registered
- ✅ Menu button visible
- ✅ FSM states defined
- ✅ File extraction handles all media types
