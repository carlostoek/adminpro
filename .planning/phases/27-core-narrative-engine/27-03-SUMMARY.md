---
phase: 27-core-narrative-engine
plan: 03
subsystem: narrative
name: StoryEditorService Implementation
description: Admin-facing story management service with CRUD operations, validation, and analytics
tags: [service, admin, crud, validation, narrative]

requires:
  - 27-01 (Database models)
  - 27-02 (NarrativeService - optional, parallel)

provides:
  - StoryEditorService class
  - Admin story CRUD operations
  - Story validation workflow
  - Story publishing workflow
  - Story analytics

affects:
  - bot/services/story_editor.py

tech-stack:
  added:
    - StoryEditorService (508 lines)
  patterns:
    - Async service pattern
    - Session injection (no commits)
    - Tuple return pattern (success, message, data)
    - SQLAlchemy selectinload for eager loading
    - Graph traversal for reachability analysis

key-files:
  created:
    - bot/services/story_editor.py
  modified: []

decisions:
  - "Follow ContentService pattern for consistency"
  - "Return tuples (bool, str, Optional[data]) for all operations"
  - "No commits in service methods - handlers manage transactions"
  - "Use selectinload for eager loading to prevent N+1 queries"
  - "Include unreachable_nodes as info (not error) in validation"

metrics:
  duration: "~10 minutes"
  tasks: 7/7
  commits: 1
  files-created: 1
  lines-added: 508
  methods-implemented: 7
---

# Phase 27 Plan 03: StoryEditorService Summary

**One-liner:** Admin story management service with full CRUD, validation workflow, and analytics for the narrative system.

## Overview

StoryEditorService provides administrators with complete control over interactive story creation and management. It handles the full lifecycle from draft creation through validation to publishing, plus analytics for understanding user engagement.

## Implementation Details

### Service Structure

```
StoryEditorService
├── create_story()        → Create new stories (DRAFT status)
├── create_node()         → Add nodes (START, STORY, CHOICE, ENDING)
├── create_choice()       → Connect nodes with choices
├── validate_story()      → Check story integrity before publish
├── publish_story()       → Make stories available to users
└── get_story_stats()     → Analytics on story engagement
```

### Key Features

**1. Story Creation (create_story)**
- Title validation (required, max 200 chars)
- Optional description
- Premium flag support
- Automatic DRAFT status

**2. Node Creation (create_node)**
- Story existence verification
- Content validation for STORY/START/ENDING types
- Media file IDs support (List[str])
- Tier clamping (1-6 range)
- Order index for sequencing

**3. Choice Creation (create_choice)**
- Source and target node validation
- Same-story verification for nodes
- Choice text validation (required, max 500 chars)
- Cost validation (non-negative)
- JSON conditions support

**4. Story Validation (validate_story)**
- Exactly one START node required
- At least one ENDING node required
- All non-ENDING nodes must have outgoing choices
- All choices must point to existing nodes
- Reachability analysis from START node
- Returns detailed error list and info dict

**5. Publishing (publish_story)**
- Pre-publish validation
- Force publish option (bypass validation)
- Status transition checks (no re-publish, archived handling)
- Automatic updated_at timestamp

**6. Analytics (get_story_stats)**
- Total starts count
- Active/Completed/Abandoned breakdown
- Completion rate calculation
- Average decisions per user
- Most common ending identification

### Validation Rules

| Check | Severity | Description |
|-------|----------|-------------|
| Has nodes | Error | Story must have at least one node |
| Single START | Error | Exactly one START node required |
| Has ENDING | Error | At least one ENDING node required |
| Outgoing choices | Error | Non-ENDING nodes need active choices |
| Valid targets | Error | All choices must point to existing nodes |
| Reachability | Warning | Unreachable nodes reported in info |

## API Reference

### Method Signatures

```python
async def create_story(
    self, title: str, description: Optional[str] = None, is_premium: bool = False
) -> Tuple[bool, str, Optional[Story]]

async def create_node(
    self, story_id: int, node_type: NodeType, content_text: Optional[str] = None,
    media_file_ids: Optional[List[str]] = None, tier_required: int = 1, order_index: int = 0
) -> Tuple[bool, str, Optional[StoryNode]]

async def create_choice(
    self, source_node_id: int, target_node_id: int, choice_text: str,
    cost_besitos: int = 0, conditions: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str, Optional[StoryChoice]]

async def validate_story(
    self, story_id: int
) -> Tuple[bool, List[str], Dict[str, Any]]

async def publish_story(
    self, story_id: int, force: bool = False
) -> Tuple[bool, str]

async def get_story_stats(
    self, story_id: int
) -> Tuple[bool, str, Optional[Dict[str, Any]]]
```

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check

- [x] File exists: bot/services/story_editor.py
- [x] All 7 methods implemented
- [x] Proper imports (models, enums, sqlalchemy)
- [x] Follows codebase patterns (async, no commits, tuple returns)
- [x] Logging implemented
- [x] Type hints complete
- [x] Docstrings (Google style)

## Self-Check: PASSED

## Integration Notes

### Usage in Handlers

```python
from bot.services.story_editor import StoryEditorService

# In handler with session injection
async def handle_create_story(message: Message, session: AsyncSession):
    editor = StoryEditorService(session)
    success, msg, story = await editor.create_story(
        title="My Story",
        description="An interactive adventure",
        is_premium=True
    )
    if success:
        await message.reply(f"Story created: {story.title}")
```

### Service Container Integration

The service can be added to the ServiceContainer for dependency injection:

```python
# In bot/services/container.py
from bot.services.story_editor import StoryEditorService

@property
def story_editor(self) -> StoryEditorService:
    if "story_editor" not in self._services:
        self._services["story_editor"] = StoryEditorService(self.session)
    return self._services["story_editor"]
```

## Next Steps

1. **Phase 28 (User Story Experience):** Build user-facing handlers that read published stories
2. **Phase 29 (Admin Story Editor):** Create admin handlers using StoryEditorService methods
3. **Integration:** Connect with WalletService for choice cost processing

## Commits

| Hash | Message |
|------|---------|
| 8b25729 | feat(27-03): implement StoryEditorService for admin story management |
