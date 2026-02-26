---
phase: 27-core-narrative-engine
plan: 02
type: execute
subsystem: narrative
status: completed

requires:
  - 27-01
provides:
  - narrative-service-user-api
  - story-discovery
  - story-progression
  - immediate-persistence-pattern

affects:
  - bot/services/narrative.py

tech-stack:
  added:
    - NarrativeService class
  patterns:
    - Dual-track persistence (FSM for UI, DB for progress)
    - Eager loading with selectinload()
    - Tuple return pattern (success, message, data)

key-files:
  created:
    - bot/services/narrative.py
  modified: []

decisions: []

metrics:
  duration: ~25 minutes
  completed: 2026-02-26
  tasks: 6/6
  commits: 6
  lines-added: ~420
---

# Phase 27 Plan 02: NarrativeService Summary

NarrativeService provides the core API for users to discover, start, and progress through interactive stories.

## One-liner

User-facing story service with immediate persistence after each choice, implementing dual-track pattern for narrative progression.

## What Was Built

### NarrativeService Class

**Location:** `bot/services/narrative.py`

**Purpose:** Core service for user story operations with immediate database persistence.

**Methods Implemented:**

| Method | Purpose | Key Features |
|--------|---------|--------------|
| `get_available_stories()` | List stories by user tier | Filters by PUBLISHED status, premium access, pagination support |
| `start_story()` | Begin or resume a story | Handles new starts, resumes, reactivations; finds START node |
| `get_current_node()` | Get current node with choices | Eager loading with selectinload(), filters active choices |
| `make_choice()` | Process choice and advance | Validates choice, records decision, detects endings, persists immediately |
| `get_story_progress()` | Check user's progress | Simple lookup by user_id + story_id |
| `abandon_story()` | Mark story as abandoned | Security check, prevents abandoning completed stories |

### Key Implementation Patterns

**1. Dual-Track Persistence**
- FSM (Finite State Machine) for UI state management
- Database for story progress persistence
- Progress saved immediately after each choice (handler commits)

**2. Security Checks**
- User ownership verification in `make_choice()` and `abandon_story()`
- Prevents users from manipulating other users' progress

**3. Eager Loading**
- Uses `selectinload()` for `StoryNode.choices` and `StoryChoice.target_node`
- Prevents N+1 query problems in graph-structured data

**4. State Transitions**
```
ACTIVE <-> PAUSED
  |         |
  v         v
COMPLETED  ABANDONED
```

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

```
✅ File exists: bot/services/narrative.py
✅ All 6 methods implemented
✅ Proper imports (models, enums, sqlalchemy)
✅ Follows service patterns (async, no commits, logging)
✅ Type hints complete
✅ Docstrings follow Google Style
```

## Commits

| Hash | Message |
|------|---------|
| ce88c59 | feat(27-02): create NarrativeService skeleton and imports |
| 70b248d | feat(27-02): implement get_available_stories method |
| 4ec8b9c | feat(27-02): implement start_story method |
| 14de714 | feat(27-02): implement get_current_node method |
| d64c17f | feat(27-02): implement make_choice method with immediate persistence |
| 20ea757 | feat(27-02): implement get_story_progress and abandon_story methods |

## Next Steps

Plan 27-03: StoryEditorService for admin operations (create/edit stories, nodes, choices).

## Self-Check: PASSED

- [x] File created: bot/services/narrative.py
- [x] All commits exist in git log
- [x] Methods follow signature specifications
- [x] No external dependencies added
- [x] Follows existing codebase patterns
