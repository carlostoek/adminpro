---
phase: 25-broadcasting-improvements-optional-reactions-and-content-protection
plan: 01
type: execute
wave: 1
subsystem: broadcast
status: complete

key-decisions:
  - "New configuring_options state inserted between content reception and confirmation"
  - "Default values: reactions ON (True), protection OFF (False) for backward compatibility"
  - "Lucien's voice (formal mayordomo with emoji) used for all configuration messages"
  - "Toggle buttons show opposite action (e.g., 'Disable' when enabled) for clarity"

tech-stack:
  added:
    - "BroadcastStates.configuring_options - new FSM state for options configuration"
  patterns:
    - "FSM state chaining: waiting_for_content -> configuring_options -> waiting_for_confirmation"
    - "Toggle pattern with immediate UI update via callback handlers"
    - "Options persistence in FSM data across state transitions"

key-files:
  created: []
  modified:
    - bot/states/admin.py
    - bot/services/channel.py
    - bot/handlers/admin/broadcast.py

dependency-graph:
  requires: []
  provides:
    - "Optional reaction buttons per broadcast message"
    - "Content protection (no download) toggle per message"
  affects:
    - "Admin broadcast flow UX"
    - "Channel message delivery with optional features"

metrics:
  duration: "4m 19s"
  completed-date: "2026-02-21"
  tasks: 3
  files-modified: 3
  lines-added: ~265
  lines-removed: ~39
---

# Phase 25 Plan 01: Optional Reactions and Content Protection Summary

## One-Liner
Extended broadcast FSM with optional reaction buttons and content protection toggle, giving admins fine-grained control over message features during broadcasting.

## What Was Built

### 1. New FSM State: configuring_options
**File:** `bot/states/admin.py`

Added `configuring_options` state to `BroadcastStates` class, positioned between `waiting_for_content` and `waiting_for_confirmation` in the broadcast flow.

**New Flow:**
```
waiting_for_content -> configuring_options -> waiting_for_confirmation
```

### 2. Channel Service Enhancement
**File:** `bot/services/channel.py`

Extended `send_to_channel()` method with `protect_content` parameter:
- New parameter: `protect_content: bool = False`
- Passed to all aiogram send methods (send_photo, send_video, send_message)
- Maintains backward compatibility with default `False`

### 3. Broadcast Flow Modification
**File:** `bot/handlers/admin/broadcast.py`

Complete overhaul of broadcast flow with options configuration step:

**New Handlers:**
- `_show_options_config_ui()` - Displays options configuration UI
- `callback_toggle_reactions()` - Toggles `add_reactions` in FSM data
- `callback_toggle_protection()` - Toggles `protect_content` in FSM data
- `callback_broadcast_continue()` - Proceeds to confirmation with preview
- `callback_back_to_options()` - Returns to options from preview
- `_update_options_config_ui()` - Updates UI after toggle

**Modified Handlers:**
- `process_broadcast_content()` - Now transitions to `configuring_options` with default settings
- `callback_broadcast_confirm()` - Reads options from FSM data and passes to `send_to_channel()`
- `_generate_preview_text()` - Now includes reaction and protection status

**UI Features:**
- Toggle buttons show opposite action (e.g., "Disable Reactions" when enabled)
- Visual status indicators (✅ ON / ❌ OFF)
- Protection icon (🔒) when content protection is enabled
- Lucien's formal mayordomo voice (🎩) throughout

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | e497ce2 | Add configuring_options state to BroadcastStates |
| 2 | 28cfd8c | Add protect_content parameter to send_to_channel |
| 3 | 72de864 | Add options configuration step to broadcast flow |

## Verification Results

- [x] BroadcastStates has configuring_options state
- [x] send_to_channel accepts protect_content parameter and passes it to aiogram
- [x] process_broadcast_content transitions to configuring_options with default settings
- [x] Options configuration UI shows current toggle states
- [x] Toggle callbacks update FSM data correctly
- [x] Confirm handler reads both options from FSM data and passes to send_to_channel

## Deviations from Plan

None - plan executed exactly as written.

## Success Criteria Verification

1. [x] Admin can start broadcast flow and see options configuration step
2. [x] Admin can toggle reaction buttons on/off before sending
3. [x] Admin can toggle content protection on/off before sending
4. [x] Message is sent with correct reaction and protection settings
5. [x] Both options default to sensible values (reactions ON, protection OFF)

## Self-Check: PASSED

All files verified:
- [x] bot/states/admin.py - configuring_options state present
- [x] bot/services/channel.py - protect_content parameter present
- [x] bot/handlers/admin/broadcast.py - all handlers present

All commits verified:
- [x] e497ce2 - Task 1 commit exists
- [x] 28cfd8c - Task 2 commit exists
- [x] 72de864 - Task 3 commit exists
