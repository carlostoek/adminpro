# Technology Stack: Narrativa v3 (Branching Story System)

**Domain:** Interactive Fiction / Branching Narrative System for Telegram Bot
**Researched:** 2026-02-26
**Confidence:** HIGH

## Executive Summary

The narrative system requires **zero new dependencies** for core functionality. The existing stack (Python 3.11+, SQLAlchemy 2.0, aiogram 3.4.1, SQLite/PostgreSQL with JSON support) provides all necessary capabilities for:

- Tree-structured story nodes with parent-child relationships
- JSON storage for choices and user decisions
- Media file handling via Telegram's existing APIs
- Condition evaluation using the existing `RewardCondition` system
- Integration with `WalletService` and `RewardService` via ServiceContainer

## Recommended Stack (Additions)

### No New Core Dependencies Required

| Technology | Version | Purpose | Why Not Needed |
|------------|---------|---------|----------------|
| SQLAlchemy JSON | 2.0.25 (existing) | Store node choices, user decisions | `JSON` column type already in use for `reward_value`, `transaction_metadata` |
| Self-Referential Relationships | 2.0.25 (existing) | Tree structure for story nodes | SQLAlchemy `relationship()` with `remote_side` pattern already used |
| aiogram Media | 3.4.1 (existing) | Photo/video/audio in narrative | `Message.answer_photo()`, `answer_video()` already available |

### Supporting Libraries (Optional Enhancements)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | 2.5.0+ | Validate node/choice schemas | If adding admin API for node creation; defer until needed |
| python-slugify | 8.0.0+ | Generate URL-safe story IDs | If stories need human-readable URLs; not required for MVP |

## Database Schema Additions (No New Tech)

Based on existing patterns in `bot/database/models.py`:

```python
# New models using EXISTING SQLAlchemy features

class Story(Base):
    """Story container (e.g., 'El Jardin Prohibido')."""
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    required_role: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # FREE/VIP
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    nodes: Mapped[List["StoryNode"]] = relationship(back_populates="story")


class StoryNode(Base):
    """Individual story node with choices (tree structure)."""
    __tablename__ = "story_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"))
    parent_node_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("story_nodes.id"), nullable=True
    )  # NULL = root node

    # Content
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    content_text: Mapped[str] = mapped_column(Text)
    media_file_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    media_type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # photo, video, audio

    # Choices stored as JSON: [{"text": "...", "next_node_id": 5, "condition": {...}}]
    choices: Mapped[List[dict]] = mapped_column(JSON, default=list)

    # Metadata
    is_start_node: Mapped[bool] = mapped_column(default=False)
    is_end_node: Mapped[bool] = mapped_column(default=False)
    sort_order: Mapped[int] = mapped_column(default=0)

    # Relationships
    story: Mapped["Story"] = relationship(back_populates="nodes")
    parent: Mapped[Optional["StoryNode"]] = relationship(
        remote_side=[id], back_populates="children"
    )
    children: Mapped[List["StoryNode"]] = relationship(back_populates="parent")


class UserStoryProgress(Base):
    """User's position and history in a story."""
    __tablename__ = "user_story_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"))
    current_node_id: Mapped[int] = mapped_column(ForeignKey("story_nodes.id"))

    # Decision history as JSON: [{"node_id": 1, "choice_index": 0, "timestamp": "..."}]
    decision_history: Mapped[List[dict]] = mapped_column(JSON, default=list)

    # Gamification integration
    besitos_earned: Mapped[int] = mapped_column(default=0)
    rewards_claimed: Mapped[List[int]] = mapped_column(JSON, default=list)  # reward_ids

    status: Mapped[str] = mapped_column(String(20), default="active")  # active, completed, abandoned
    started_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    last_interaction_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
```

## Architecture Patterns

### 1. Node Tree Traversal

```python
# Using existing SQLAlchemy patterns
async def get_node_path(self, node_id: int) -> List[StoryNode]:
    """Get path from root to current node (for breadcrumbs/history)."""
    path = []
    current = await self.session.get(StoryNode, node_id)

    while current:
        path.append(current)
        if current.parent_node_id:
            current = await self.session.get(StoryNode, current.parent_node_id)
        else:
            break

    return list(reversed(path))
```

### 2. Choice Condition Evaluation

Reuse existing `RewardService.evaluate_single_condition()`:

```python
async def evaluate_choice_conditions(
    self,
    user_id: int,
    choice: dict  # From node.choices JSON
) -> Tuple[bool, str]:
    """
    Check if user meets conditions for a choice.

    Conditions use same format as RewardCondition:
    {
        "type": "BESITOS_MINIMUM",
        "value": 100,
        "or_group": 0  # 0 = AND, 1+ = OR groups
    }
    """
    condition_data = choice.get("condition")
    if not condition_data:
        return True, "no_conditions"

    # Map to existing RewardConditionType or extend enum
    condition_type = condition_data["type"]

    # Use existing profile data
    profile = await self.wallet.get_profile(user_id)

    if condition_type == "BESITOS_MINIMUM":
        return profile.balance >= condition_data["value"], "insufficient_besitos"

    if condition_type == "VIP_REQUIRED":
        user = await self.session.get(User, user_id)
        return user.role == UserRole.VIP, "vip_required"

    # Delegate to RewardService for complex conditions
    # ...
```

### 3. Media Handling

```python
async def send_node_content(
    self,
    chat_id: int,
    node: StoryNode,
    keyboard: InlineKeyboardMarkup
) -> Message:
    """Send node content with appropriate media type."""

    if not node.media_file_id:
        # Text-only node
        return await self.bot.send_message(
            chat_id=chat_id,
            text=node.content_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    # Use existing aiogram methods based on media_type
    if node.media_type == "photo":
        return await self.bot.send_photo(
            chat_id=chat_id,
            photo=node.media_file_id,  # Telegram file_id (persistent)
            caption=node.content_text[:1024],  # Telegram caption limit
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    if node.media_type == "video":
        return await self.bot.send_video(
            chat_id=chat_id,
            video=node.media_file_id,
            caption=node.content_text[:1024],
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    # Fallback to text
    return await self.bot.send_message(
        chat_id=chat_id,
        text=node.content_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
```

### 4. Integration with Existing Services

```python
class NarrativeService:
    """
    Narrative system service following existing patterns.

    Integrates with:
    - WalletService: besitos costs/rewards for choices
    - RewardService: unlock narrative achievements
    - ShopService: purchase story unlocks
    """

    def __init__(
        self,
        session: AsyncSession,
        bot: Bot,
        wallet_service: Optional[WalletService] = None,
        reward_service: Optional[RewardService] = None
    ):
        self.session = session
        self.bot = bot
        self.wallet = wallet_service
        self.reward = reward_service

    async def process_choice(
        self,
        user_id: int,
        node_id: int,
        choice_index: int
    ) -> Tuple[bool, str, Optional[StoryNode]]:
        """
        Process user choice with full gamification integration.
        """
        # Get current progress
        progress = await self._get_or_create_progress(user_id, node_id)
        node = await self.session.get(StoryNode, node_id)
        choice = node.choices[choice_index]

        # Check conditions
        can_choose, reason = await self.evaluate_choice_conditions(user_id, choice)
        if not can_choose:
            return False, reason, None

        # Deduct besitos if choice has cost
        cost = choice.get("cost_besitos", 0)
        if cost > 0 and self.wallet:
            success, msg, _ = await self.wallet.spend_besitos(
                user_id=user_id,
                amount=cost,
                transaction_type=TransactionType.SPEND_SHOP,  # Or new NARRATIVE_CHOICE
                reason=f"Story choice: {choice['text'][:50]}"
            )
            if not success:
                return False, "insufficient_funds", None

        # Record decision
        progress.decision_history.append({
            "node_id": node_id,
            "choice_index": choice_index,
            "choice_text": choice["text"],
            "timestamp": datetime.utcnow().isoformat(),
            "cost_paid": cost
        })

        # Advance to next node
        next_node_id = choice.get("next_node_id")
        if next_node_id:
            progress.current_node_id = next_node_id
            next_node = await self.session.get(StoryNode, next_node_id)

            # Check for rewards on node entry
            if self.reward:
                await self.reward.check_rewards_on_event(
                    user_id=user_id,
                    event_type="story_node_reached",
                    event_data={"node_id": next_node_id, "story_id": node.story_id}
                )

            await self.session.flush()
            return True, "advanced", next_node

        # End of story
        progress.status = "completed"
        progress.completed_at = datetime.utcnow()
        await self.session.flush()
        return True, "completed", None
```

## Service Container Integration

Add to `ServiceContainer` following existing pattern:

```python
# In bot/services/container.py

@property
def narrative(self):
    """
    Service de sistema narrativo (historias ramificadas).

    Se carga lazy (solo en primer acceso).
    """
    if self._narrative_service is None:
        from bot.services.narrative import NarrativeService
        logger.debug("🔄 Lazy loading: NarrativeService")
        self._narrative_service = NarrativeService(
            self._session,
            self._bot,
            wallet_service=self.wallet,
            reward_service=self.reward
        )
    return self._narrative_service
```

## Data Flow: Story Creation to User Interaction

```
Admin Panel (Future)
    ↓
StoryNode records created
    ↓
User starts story via /historia
    ↓
NarrativeService.get_start_node(story_id)
    ↓
Send node content + choices as inline keyboard
    ↓
User clicks choice button
    ↓
Callback handler → narrative.process_choice()
    ↓
[Validate conditions] → [Deduct besitos if needed]
    ↓
[Record decision] → [Check rewards] → [Advance node]
    ↓
Send next node content
```

## JSON Schema for Choices

```python
# Stored in StoryNode.choices (JSON column)
choice_schema = {
    "text": "Investigar la habitación",           # Button text
    "next_node_id": 42,                            # Target node (null = end)
    "condition": {                                 # Optional
        "type": "BESITOS_MINIMUM",
        "value": 50,
        "error_message": "Necesitas 50 besitos"
    },
    "cost_besitos": 50,                           # Optional cost
    "rewards": {                                   # Optional immediate rewards
        "besitos": 10,
        "unlock_achievement": "explorer"
    },
    "style": "primary"                            # Button style (for UI)
}
```

## Media Storage Strategy

| Media Type | Storage | Retrieval |
|------------|---------|-----------|
| Photos | Telegram servers (file_id) | `node.media_file_id` |
| Videos | Telegram servers (file_id) | `node.media_file_id` |
| Audio | Telegram servers (file_id) | `node.media_file_id` |
| Documents | Optional: local + file_id | Fallback chain |

**Admin upload flow:**
1. Admin sends media to bot
2. Bot receives `message.photo[-1].file_id` (highest res)
3. Store file_id in `StoryNode.media_file_id`
4. No local storage needed for MVP

## Alternatives Considered

| Approach | Why Not Used |
|----------|--------------|
| External story engines (Ink, Twine) | Adds complexity; JSON tree sufficient for MVP |
| Graph database (Neo4j) | Overkill; self-referential SQL handles tree fine |
| Separate media CDN | Telegram's file_id system is free and persistent |
| pydantic for all validation | Existing SQLAlchemy validators sufficient |

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Heavy NLP (sentiment, generation) | Out of scope per requirements | Template-based content with variables |
| Full graph DB | Tree structure sufficient | Self-referential SQLAlchemy |
| External narrative engines | Deferred per requirements | Native JSON tree |
| File storage system (S3, etc.) | Telegram handles media | file_id references |
| Real-time sync (WebSockets) | Telegram bot is polling-based | Standard message flow |

## Version Compatibility

| Component | Current | Narrative Addition | Notes |
|-----------|---------|-------------------|-------|
| SQLAlchemy | 2.0.25 | Same | JSON column already used |
| aiogram | 3.4.1+ | Same | Media methods available |
| SQLite | 3.x | Same | JSON1 extension enabled |
| PostgreSQL | 15+ | Same | Native JSONB support |

## Installation (No Changes)

```bash
# No new dependencies required
# Existing requirements.txt sufficient:
# - sqlalchemy==2.0.25
# - aiogram>=3.24.0
```

## Sources

- Existing codebase analysis (`bot/services/`, `bot/database/models.py`)
- SQLAlchemy 2.0 documentation - JSON type support
- aiogram 3.x documentation - Media sending methods
- Project requirements: "No heavy NLP", "External engines deferred"
