---
phase: 27-core-narrative-engine
plan: "01"
subsystem: database
tags: [narrative, models, enums, database]
dependency_graph:
  requires: []
  provides: ["27-02", "27-03", "27-04"]
  affects: ["bot/database/enums.py", "bot/database/models.py"]
tech_stack:
  added: []
  patterns:
    - "SQLAlchemy 2.0 declarative models"
    - "Enum classes with str mixin"
    - "Self-referential relationships"
    - "JSON columns for flexible data"
key_files:
  created: []
  modified:
    - path: "bot/database/enums.py"
      changes: "Added StoryStatus, NodeType, StoryProgressStatus enums"
    - path: "bot/database/models.py"
      changes: "Added Story, StoryNode, StoryChoice, UserStoryProgress models"
decisions: []
metrics:
  duration: "15 minutes"
  completed_date: "2026-02-26"
---

# Phase 27 Plan 01: Narrative Database Models Summary

Foundation for story storage, retrieval, and user progress tracking. These models enable the core narrative functionality where users can experience interactive stories with choices.

## One-Liner

Created 3 narrative enums and 4 database models enabling interactive story system with node-based graph structure and user progress tracking.

## What Was Built

### Enums Added (bot/database/enums.py)

| Enum | Values | Purpose |
|------|--------|---------|
| StoryStatus | DRAFT, PUBLISHED, ARCHIVED | Lifecycle states for stories |
| NodeType | START, STORY, CHOICE, ENDING | Types of story nodes |
| StoryProgressStatus | ACTIVE, PAUSED, COMPLETED, ABANDONED | User's progress state |

### Models Added (bot/database/models.py)

| Model | Key Fields | Relationships |
|-------|------------|---------------|
| Story | title, description, is_premium, status | → StoryNode (1:N), → UserStoryProgress (1:N) |
| StoryNode | story_id, node_type, content_text, media_file_ids, tier_required | → Story (N:1), → StoryChoice (1:N source), → StoryChoice (1:N target) |
| StoryChoice | source_node_id, target_node_id, choice_text, cost_besitos | → StoryNode (source), → StoryNode (target) |
| UserStoryProgress | user_id, story_id, current_node_id, decisions_made, status | → User (N:1), → Story (N:1), → StoryNode (N:1) |

## Key Design Decisions

1. **Self-referential relationships**: StoryChoice uses source_node_id and target_node_id both referencing story_nodes.id, enabling graph traversal
2. **JSON columns**: decisions_made and media_file_ids use JSON for flexible array storage
3. **Tier system**: tier_required (1-6) distinguishes Free (1-3) from Premium (4-6) content
4. **Unique constraint**: (user_id, story_id) unique index prevents duplicate progress records
5. **Cascade deletes**: Story deletion cascades to nodes and progress records; node deletion cascades to choices

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 9a75c06 | feat(27-01): add narrative system enums |
| 2-5 | 7169bbd | feat(27-01): add narrative system models |

## Verification Results

```
✓ StoryStatus enum exists with DRAFT, PUBLISHED, ARCHIVED values
✓ NodeType enum exists with START, STORY, CHOICE, ENDING values
✓ StoryProgressStatus enum exists with ACTIVE, PAUSED, COMPLETED, ABANDONED values
✓ Story model exists with title, description, is_premium, status fields
✓ StoryNode model exists with story_id, node_type, content_text, media_file_ids, tier_required fields
✓ StoryChoice model exists with source_node_id, target_node_id, choice_text, cost_besitos fields
✓ UserStoryProgress model exists with user_id, story_id, current_node_id, decisions_made, status fields
✓ All relationships defined with proper cascade and lazy loading
✓ Proper indexes created for query optimization
```

## Self-Check: PASSED

- [x] bot/database/enums.py exists and contains new enums
- [x] bot/database/models.py exists and contains new models
- [x] All imports properly updated
- [x] Commits 9a75c06 and 7169bbd exist in git history

## Deviations from Plan

None - plan executed exactly as written.

## Next Steps

Plan 27-02 (NarrativeService) can now proceed, building on these models to implement:
- Story retrieval and filtering
- Node navigation
- Choice validation and cost deduction
- Progress tracking and persistence
