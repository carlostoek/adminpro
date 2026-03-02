# Phase 27 Research: Core Narrative Engine

**Phase:** 27 - Core Narrative Engine
**Goal:** Foundation database models and core service for story storage, retrieval, and user progress tracking
**Date:** 2026-02-26
**Research Confidence:** HIGH (standard patterns, existing codebase foundation)

---

## Executive Summary

This phase delivers the foundational database models and services for a branching narrative system. Research confirms **zero new dependencies** are required - the existing stack (SQLAlchemy 2.0.25, SQLite/PostgreSQL with JSON) provides all necessary capabilities. Tree-structured stories will use self-referential SQLAlchemy relationships, and user progress tracking will integrate with the existing cascading condition system.

**Key Integration Points:**
- ServiceContainer dependency injection (2 new lazy-loaded services)
- Existing RewardCondition system (extend with STORY_* condition types)
- WalletService for future choice costs (Phase 30)
- FSM states for ephemeral UI state, database for persistent progress

---

## Database Design

### Models Required

```
Story (story catalog)
├── id (PK)
├── title, description
├── is_premium (bool) - TIER-01 requirement
├── status (draft/published/archived)
├── created_at, updated_at
└── nodes (relationship)

StoryNode (individual scenes)
├── id (PK)
├── story_id (FK)
├── node_type (start/standard/end)
├── content_text
├── media_file_ids (JSON array)
├── tier_required (1-6, for node-level restrictions)
├── order_index (for progress "Escena X de Y")
├── is_active (soft delete)
└── choices (relationship)

StoryChoice (branching decisions)
├── id (PK)
├── source_node_id (FK)
├── target_node_id (FK, self-referential nullable for end)
├── choice_text
├── cost_besitos (int, default 0)
├── conditions (JSON - for future ECON-05)
└── is_active

UserStoryProgress (user state)
├── id (PK)
├── user_id (int)
├── story_id (FK)
├── current_node_id (FK, nullable)
├── decisions_made (JSON array of choice IDs)
├── status (not_started/in_progress/completed)
├── started_at, completed_at
├── ending_reached (str, nullable - for multiple endings)
└── unique(user_id, story_id) constraint
```

### Key SQLAlchemy Patterns

**Self-referential relationship for choices:**
```python
# In StoryChoice model
target_node_id: Mapped[Optional[int]] = mapped_column(
    ForeignKey("story_nodes.id"), nullable=True
)
target_node: Mapped[Optional["StoryNode"]] = relationship(
    "StoryNode", remote_side="StoryNode.id", lazy="joined"
)
```

**Eager loading pattern for story traversal:**
```python
# When fetching a node, always load its choices
from sqlalchemy.orm import selectinload

stmt = select(StoryNode).where(
    StoryNode.id == node_id
).options(
    selectinload(StoryNode.choices)
)
```

---

## Service Architecture

### NarrativeService (user-facing)

**Responsibilities:**
- Story delivery and filtering by tier
- Progress tracking and persistence
- Choice processing and validation
- Node traversal (get next node by choice)

**Key Methods:**
```python
async def get_available_stories(self, user_id: int, tier: str) -> List[Story]
async def start_story(self, user_id: int, story_id: int) -> StoryNode
async def get_current_node(self, user_id: int, story_id: int) -> Optional[StoryNode]
async def make_choice(self, user_id: int, choice_id: int) -> Tuple[StoryNode, bool]  # (node, is_end)
async def get_story_progress(self, user_id: int, story_id: int) -> UserStoryProgress
async def abandon_story(self, user_id: int, story_id: int) -> None
```

**Progress persistence pattern:**
```python
# Dual-track: FSM for UI state, DB for actual progress
# After every choice, immediately save to database
progress.decisions_made.append(choice_id)
progress.current_node_id = new_node.id
if new_node.node_type == NodeType.END:
    progress.status = StoryStatus.COMPLETED
await self.session.commit()
```

### StoryEditorService (admin-facing)

**Responsibilities:**
- CRUD operations for stories, nodes, choices
- Story validation (cycles, orphans, dead ends)
- Publishing workflow (draft → published)
- Story statistics

**Key Methods:**
```python
async def create_story(self, title: str, description: str, is_premium: bool) -> Story
async def create_node(self, story_id: int, content: str, node_type: str) -> StoryNode
async def create_choice(self, source_id: int, target_id: Optional[int], text: str) -> StoryChoice
async def validate_story(self, story_id: int) -> ValidationResult
async def publish_story(self, story_id: int) -> None
async def get_story_stats(self, story_id: int) -> StoryStats
```

**Validation checks:**
- Cycle detection (DFS traversal from start node)
- Orphaned nodes (nodes not reachable from start)
- Dead ends (nodes with no choices that aren't marked END)
- Missing start node (story must have exactly one START node)

---

## Integration Patterns

### ServiceContainer Integration

```python
# Add to ServiceContainer
@property
@lru_cache()
def narrative(self) -> NarrativeService:
    return NarrativeService(self.session, self.bot)

@property
@lru_cache()
def story_editor(self) -> StoryEditorService:
    return StoryEditorService(self.session, self.bot)
```

### RewardCondition Extension (Phase 30 preparation)

```python
class RewardConditionType(Enum):
    # Existing types...
    STORY_NODE_REACHED = "story_node_reached"
    STORY_CHOICE_MADE = "story_choice_made"
    STORY_COMPLETED = "story_completed"
```

### Tier Filtering (TIER-01)

```python
# Free users: levels 1-3
# VIP users: levels 1-6
async def get_stories_for_user(self, user_id: int) -> List[Story]:
    is_vip = await self.subscription.is_vip_active(user_id)
    max_tier = 6 if is_vip else 3

    stmt = select(Story).where(
        Story.status == StoryStatus.PUBLISHED,
        Story.is_premium.is_(False) | is_vip  # VIP sees all, Free sees only non-premium
    )
    return await self.session.scalars(stmt)
```

---

## Critical Implementation Notes

### 1. Escape Hatch Pattern
Every story interaction must include a "Salir" button that:
- Calls `narrative.abandon_story(user_id, story_id)`
- Clears FSM state
- Returns to main menu

### 2. Atomic Choice Processing
To prevent double-charging (Phase 30):
```python
# Pre-validate before showing choices
valid_choices = []
for choice in node.choices:
    if choice.cost_besitos > 0:
        balance = await self.wallet.get_balance(user_id)
        if balance >= choice.cost_besitos:
            valid_choices.append(choice)
    else:
        valid_choices.append(choice)
```

### 3. N+1 Prevention
Always use eager loading for story queries:
```python
# Bad - N+1
story = await session.get(Story, story_id)
for node in story.nodes:  # Query 1
    for choice in node.choices:  # Query N
        ...

# Good - 1 query
stmt = select(Story).where(Story.id == story_id).options(
    selectinload(Story.nodes).selectinload(StoryNode.choices)
)
```

### 4. Decision History Storage
Store as JSON array of choice IDs for simplicity:
```python
# decisions_made JSON structure
[101, 205, 312]  # List of StoryChoice IDs in order made
```

---

## Testing Strategy

**Unit tests for NarrativeService:**
- Start story creates progress record
- Choice updates current_node_id
- End node marks status completed
- Tier filtering works correctly

**Unit tests for StoryEditorService:**
- Cycle detection identifies circular paths
- Orphan detection finds unreachable nodes
- Dead end detection finds non-end nodes without choices

**Integration tests:**
- Full story flow: start → choices → completion
- Concurrent users don't interfere
- Abandoning story clears state correctly

---

## Success Criteria Mapping

| Criterion | How Addressed |
|-----------|---------------|
| DB schema with proper relationships | Models above with FK constraints |
| NarrativeService API | Methods defined above |
| StoryEditorService admin CRUD | Methods defined above |
| Dual-track persistence | Progress saved to DB after every choice |
| Free/Premium filtering | is_premium field + tier logic |

---

## RESEARCH COMPLETE

This research provides sufficient context for planning Phase 27. All patterns are standard SQLAlchemy/Telegram bot practices. No external research needed.

**Next:** Spawn gsd-planner to create executable plans.
