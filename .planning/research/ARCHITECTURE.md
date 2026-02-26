# Architecture Research: Branching Narrative System Integration

**Domain:** Telegram Bot - Branching Narrative/Story System
**Researched:** 2026-02-26
**Confidence:** HIGH

## Executive Summary

This research analyzes how a branching narrative system integrates with an existing layered service-oriented architecture. The existing system uses a ServiceContainer with 19 lazy-loaded services, aiogram FSM for multi-step flows, and a cascading condition system (RewardCondition with condition_group). The narrative system must integrate seamlessly without disrupting existing patterns.

---

## Current Architecture Overview

### Existing System Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                      HANDLER LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ admin/      │  │ user/       │  │ vip/, free/             │  │
│  │ - main.py   │  │ - start.py  │  │ - menu.py, callbacks    │  │
│  │ - vip.py    │  │ - vip_entry │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                      SERVICE LAYER (DI Container)                │
├─────────────────────────────────────────────────────────────────┤
│  ServiceContainer (19 services, lazy-loaded)                     │
│  ├── subscription    ├── wallet          ├── reward              │
│  ├── channel         ├── streak          ├── shop                │
│  ├── config          ├── reaction        ├── content             │
│  ├── pricing         ├── user            ├── role_detection      │
│  ├── vip_entry       ├── interest        ├── user_management     │
│  ├── role_change     ├── stats           ├── message (Lucien)    │
│  └── session_history                                                      │
├─────────────────────────────────────────────────────────────────┤
│                      DATA LAYER                                  │
├─────────────────────────────────────────────────────────────────┤
│  SQLAlchemy Async ORM → SQLite (WAL mode)                        │
│  Models: User, VIPSubscriber, Reward, RewardCondition,           │
│          UserGamificationProfile, Transaction, etc.              │
└─────────────────────────────────────────────────────────────────┘
```

### Key Architectural Patterns

1. **Dependency Injection via ServiceContainer**: All services accessed through `container.service_name`
2. **Lazy Loading**: Services instantiated only on first access
3. **Service Inter-dependency**: Services receive other services via constructor injection
4. **FSM States**: aiogram StatesGroup for multi-step user flows
5. **Cascading Conditions**: RewardCondition uses condition_group (0=AND, 1+=OR groups)

---

## Narrative System Integration Architecture

### New Components Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    NARRATIVE HANDLERS                            │
├─────────────────────────────────────────────────────────────────┤
│  bot/handlers/narrativa/                                         │
│  ├── __init__.py         # Router registration                   │
│  ├── story_reader.py     # User story interaction                │
│  └── admin/                                                        │
│      ├── __init__.py                                             │
│      ├── story_editor.py # CRUD for stories                      │
│      └── node_manager.py # Node/choice management                │
├─────────────────────────────────────────────────────────────────┤
│                    NARRATIVE SERVICE LAYER                       │
├─────────────────────────────────────────────────────────────────┤
│  ServiceContainer additions:                                     │
│  ├── narrative          # Story delivery & progress              │
│  └── story_editor       # Admin editing operations               │
├─────────────────────────────────────────────────────────────────┤
│                    NARRATIVE DATA MODEL                          │
├─────────────────────────────────────────────────────────────────┤
│  StoryNode, StoryChoice, UserStoryProgress                       │
│  StoryCondition (extends RewardCondition pattern)                │
└─────────────────────────────────────────────────────────────────┘
```

---

## New Components Detail

### 1. Data Models (New Tables)

| Model | Purpose | Key Relationships |
|-------|---------|-------------------|
| `Story` | Container for a narrative arc | Has many StoryNode |
| `StoryNode` | Individual story segment | Belongs to Story, has many StoryChoice |
| `StoryChoice` | User decision option | Belongs to StoryNode, targets next_node_id |
| `UserStoryProgress` | Tracks user position in story | Belongs to User, Story, current_node |
| `StoryCondition` | Unlock requirements for nodes | Mirrors RewardCondition pattern |

### 2. New Services

| Service | Responsibility | Dependencies |
|---------|---------------|--------------|
| `NarrativeService` | Story delivery, progress tracking, choice processing | WalletService, RewardService, session |
| `StoryEditorService` | Admin CRUD for stories/nodes/choices | session only (admin operations) |

### 3. New Handlers

| Handler | Purpose | FSM States |
|---------|---------|------------|
| `story_reader.py` | User interaction with active story | `NarrativeStates.reading_node`, `making_choice` |
| `admin/story_editor.py` | Admin story creation/editing | `StoryEditStates.creating_story`, `editing_node` |
| `admin/node_manager.py` | Node and choice management | `NodeEditStates.*` |

---

## Integration Points

### Integration with Existing Economy (WalletService)

**Pattern: Service Injection via Container**

```python
# In ServiceContainer:
@property
def narrative(self):
    if self._narrative_service is None:
        from bot.services.narrative import NarrativeService
        self._narrative_service = NarrativeService(
            self._session,
            wallet_service=self.wallet,  # Inject wallet
            reward_service=self.reward   # Inject reward
        )
    return self._narrative_service
```

**Use Cases:**
- Choice costs besitos: `wallet.spend_besitos()` before advancing
- Story rewards: `wallet.earn_besitos()` on node completion
- Purchase story access: Integration with shop for story unlocks

### Integration with Reward System

**Pattern: Event-Driven Reward Checking**

```python
# NarrativeService triggers reward checks
async def advance_story(self, user_id: int, choice_id: int):
    # ... process choice ...

    # Check for narrative-related rewards
    unlocked = await self.reward_service.check_rewards_on_event(
        user_id=user_id,
        event_type="story_node_completed",
        event_data={"story_id": story.id, "node_id": node.id}
    )
    return {"new_node": next_node, "unlocked_rewards": unlocked}
```

**New RewardCondition Types:**
- `STORY_NODE_REACHED`: User reached specific node
- `STORY_CHOICE_MADE`: User made specific choice
- `STORY_COMPLETED`: Finished entire story arc

### Integration with Existing Condition System

**Pattern: Extend RewardConditionType Enum**

The existing cascading condition system (group 0=AND, groups 1+=OR) supports narrative conditions naturally:

```python
# bot/database/enums.py - Add to RewardConditionType:
STORY_NODE_REACHED = "STORY_NODE_REACHED"      # requires_value: node_id
STORY_CHOICE_MADE = "STORY_CHOICE_MADE"        # requires_value: choice_id
STORY_COMPLETED = "STORY_COMPLETED"            # requires_value: story_id
```

**Evaluation in RewardService:**

```python
# In RewardService._evaluate_event_condition()
elif condition_type == RewardConditionType.STORY_NODE_REACHED:
    result = await self.session.execute(
        select(func.count(UserStoryProgress.id)).where(
            UserStoryProgress.user_id == user_id,
            UserStoryProgress.current_node_id == threshold
        )
    )
    return (result.scalar_one_or_none() or 0) > 0
```

---

## Data Flow

### User Story Flow

```
User sends /story
    ↓
NarrativeHandler → container.narrative.get_available_stories(user_id)
    ↓
Check StoryConditions (reuse RewardService logic)
    ↓
Display available stories with inline keyboard
    ↓
User selects story
    ↓
NarrativeService.load_story(user_id, story_id)
    - Get/create UserStoryProgress
    - Find current node (or start_node if new)
    ↓
Display StoryNode content + StoryChoice buttons
    ↓
User makes choice
    ↓
NarrativeService.process_choice(user_id, choice_id)
    1. Validate choice is available from current node
    2. Check choice cost (WalletService.spend_besitos)
    3. Update UserStoryProgress.current_node
    4. Check for rewards (RewardService.check_rewards_on_event)
    5. Return next node content
    ↓
Display next node or ending
```

### Admin Story Creation Flow

```
Admin sends /admin → Story Management
    ↓
StoryEditorHandler → container.story_editor.create_story()
    ↓
FSM: StoryEditStates.creating_story
    ↓
Collect: title, description, start_node_id, access_tier
    ↓
StoryEditorService.create_story() → Story record
    ↓
NodeManagerHandler → Add nodes
    ↓
FSM: NodeEditStates.creating_node
    ↓
Per node: content, media, node_type (story/choice/ending)
    ↓
Per choice: label, cost, target_node, conditions
    ↓
StoryEditorService.publish_story() → Available to users
```

---

## Build Order (Dependency-Aware)

### Phase 1: Foundation (No Dependencies)
1. **Database Models** (`Story`, `StoryNode`, `StoryChoice`, `UserStoryProgress`)
2. **Enums** (`StoryNodeType`, extend `RewardConditionType`)
3. **StoryEditorService** (basic CRUD, no dependencies)

### Phase 2: Core Narrative (Depends on Phase 1)
4. **NarrativeService** (depends on WalletService, RewardService)
5. **Admin Handlers** (story_editor.py, node_manager.py)
6. **User Handlers** (story_reader.py)

### Phase 3: Integration (Depends on Phase 2)
7. **RewardCondition Extensions** (evaluate narrative conditions)
8. **Shop Integration** (stories as purchasable items)
9. **Message Providers** (Lucien voice for narrative)

### Phase 4: Polish
10. **Analytics** (story completion rates, popular choices)
11. **Background Tasks** (story expiration, cleanup)

---

## Modified vs New Components

### New Components (Created)

| Component | Type | Location |
|-----------|------|----------|
| `Story` model | Model | `bot/database/models.py` |
| `StoryNode` model | Model | `bot/database/models.py` |
| `StoryChoice` model | Model | `bot/database/models.py` |
| `UserStoryProgress` model | Model | `bot/database/models.py` |
| `StoryNodeType` enum | Enum | `bot/database/enums.py` |
| `NarrativeService` | Service | `bot/services/narrative.py` |
| `StoryEditorService` | Service | `bot/services/story_editor.py` |
| `NarrativeStates` | States | `bot/states/narrativa.py` |
| `StoryEditStates` | States | `bot/states/narrativa_admin.py` |
| `story_reader.py` | Handler | `bot/handlers/narrativa/story_reader.py` |
| `story_editor.py` | Handler | `bot/handlers/narrativa/admin/story_editor.py` |
| `node_manager.py` | Handler | `bot/handlers/narrativa/admin/node_manager.py` |

### Modified Components (Extended)

| Component | Change | Location |
|-----------|--------|----------|
| `ServiceContainer` | Add `narrative`, `story_editor` properties | `bot/services/container.py` |
| `RewardConditionType` | Add `STORY_*` condition types | `bot/database/enums.py` |
| `RewardService` | Add narrative condition evaluation | `bot/services/reward.py` |
| `event_to_conditions` map | Add narrative events | `bot/services/reward.py` |

---

## Consistency with Existing Patterns

### Service Pattern

**Existing Pattern (WalletService):**
```python
class WalletService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = logging.getLogger(__name__)
```

**NarrativeService Follows Same Pattern:**
```python
class NarrativeService:
    def __init__(self, session: AsyncSession, wallet_service=None, reward_service=None):
        self.session = session
        self.wallet_service = wallet_service
        self.reward_service = reward_service
        self.logger = logging.getLogger(__name__)
```

### Handler Pattern

**Existing Pattern (start.py):**
```python
@user_router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession):
    container = ServiceContainer(session, message.bot)
    user = await container.user.get_or_create_user(...)
```

**Narrative Handler Follows Same Pattern:**
```python
@narrative_router.message(Command("story"))
async def cmd_story(message: Message, session: AsyncSession):
    container = ServiceContainer(session, message.bot)
    stories = await container.narrative.get_available_stories(message.from_user.id)
```

### FSM Pattern

**Existing Pattern (VIPEntryStates):**
```python
class VIPEntryStates(StatesGroup):
    stage_1_confirmation = State()
    stage_2_alignment = State()
    stage_3_delivery = State()
```

**Narrative States Follow Same Pattern:**
```python
class NarrativeStates(StatesGroup):
    reading_node = State()      # User viewing story content
    making_choice = State()     # User selecting from choices
    viewing_ending = State()    # User at story ending
```

---

## Scalability Considerations

| Scale | Consideration | Solution |
|-------|---------------|----------|
| 100 users | Story content in DB is fine | Current approach |
| 10K users | UserStoryProgress table grows | Index on (user_id, story_id), cleanup completed |
| 100K users | Story delivery performance | Cache active stories in memory, CDN for media |

### Database Indexes Recommended

```python
# UserStoryProgress - Fast lookup of user's current position
Index('idx_user_story_progress', 'user_id', 'story_id')

# StoryChoice - Fast lookup of choices for a node
Index('idx_story_choice_node', 'current_node_id')

# StoryNode - Fast lookup of node by story
Index('idx_story_node_story', 'story_id', 'node_order')
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Direct Model Access from Handlers

**Wrong:**
```python
# Handler directly queries models
result = await session.execute(select(StoryNode).where(...))
```

**Correct:**
```python
# Use service layer
node = await container.narrative.get_current_node(user_id, story_id)
```

### Anti-Pattern 2: Tight Coupling to Specific Services

**Wrong:**
```python
class NarrativeService:
    def __init__(self, session, wallet_service: WalletService):
        self.wallet = wallet_service  # Required dependency
```

**Correct:**
```python
class NarrativeService:
    def __init__(self, session, wallet_service=None, reward_service=None):
        self.wallet = wallet_service  # Optional, check before use
        self.reward = reward_service
```

### Anti-Pattern 3: Bypassing Condition System

**Wrong:**
```python
# Hardcoded checks in narrative service
if user.balance >= choice.cost:
    # proceed
```

**Correct:**
```python
# Use wallet service for consistency
success, msg, _ = await self.wallet.spend_besitos(
    user_id=user_id,
    amount=choice.cost,
    transaction_type=TransactionType.SPEND_STORY,
    reason=f"Story choice: {choice.label}"
)
```

---

## Migration Path

### Database Migration

```python
# alembic migration
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Stories table
    op.create_table('stories',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('access_tier', sa.Enum(ContentTier), default='free'),
        sa.Column('is_published', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Story nodes, choices, progress tables...
```

### Service Container Registration

```python
# Add to ServiceContainer.__init__
self._narrative_service = None
self._story_editor_service = None

# Add properties
@property
def narrative(self):
    if self._narrative_service is None:
        from bot.services.narrative import NarrativeService
        self._narrative_service = NarrativeService(
            self._session,
            wallet_service=self.wallet,
            reward_service=self.reward
        )
    return self._narrative_service
```

---

## Summary

The branching narrative system integrates cleanly with the existing service-oriented architecture by:

1. **Following established patterns**: DI via ServiceContainer, lazy loading, service dependencies
2. **Reusing existing infrastructure**: RewardCondition system for unlock logic, WalletService for economy
3. **Minimal modifications**: Only 3 existing files need changes (container.py, enums.py, reward.py)
4. **Clear separation**: New handlers in `bot/handlers/narrativa/`, new services isolated
5. **Consistent data model**: Mirrors existing patterns (UserStoryProgress similar to UserReward)

The build order respects dependencies: data models first, then services, then handlers, then integrations. This allows incremental development and testing at each phase.

---

*Architecture research for: DianaBot Narrative System v3*
*Researched: 2026-02-26*
