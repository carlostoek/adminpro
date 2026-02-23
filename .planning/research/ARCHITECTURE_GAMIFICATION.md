# Architecture Research: Gamification Integration

**Domain:** Telegram Bot Gamification System
**Researched:** 2026-02-08
**Confidence:** HIGH

## Executive Summary

This research analyzes how gamification features integrate with the existing VIP/Free Telegram bot architecture. The bot uses a **Layered Service-Oriented Architecture with Dependency Injection**, and gamification must follow these established patterns while adding new cross-cutting concerns (reactions, virtual currency, achievements, streaks).

**Key architectural decisions:**
1. **New services follow existing lazy-loading pattern** in ServiceContainer
2. **Cascading admin flows use nested FSM states** with state data persistence
3. **Reaction tracking hooks into existing content publishing** via ChannelService
4. **Wallet transactions are atomic** and use optimistic locking for concurrency

---

## Current Architecture Overview

### Existing System Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                      HANDLER LAYER                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ admin/      │  │ user/       │  │ vip/         free/      │  │
│  │  menu.py    │  │  start.py   │  │  entry.py    access.py  │  │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┬───────────┘  │
├─────────┴────────────────┴────────────────────────┴─────────────┤
│                      SERVICE LAYER                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              ServiceContainer (DI + Lazy Loading)        │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │    │
│  │  │subscription│ │ channel  │ │  config  │ │  stats   │   │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │    │
│  │  │  pricing   │ │  user    │ │  content │ │  vip_entry│   │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│                      MIDDLEWARE LAYER                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ DatabaseMiddleware│  │ AdminAuthMiddleware│  │  (others)       │  │
│  │  - Injects session │  │  - Validates admin │  │                 │  │
│  │  - Creates container│  │  - Blocks non-admin│  │                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                      DATA LAYER                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │  User    │  │VIPSubscriber│ │InvitationToken│ │ ContentPackage│  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │BotConfig │  │SubscriptionPlan│ │UserInterest│ │ (more...)    │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### Key Architectural Patterns

1. **Service Container with Lazy Loading**: Services instantiated only on first access
2. **DatabaseMiddleware**: Injects `session` and `container` into handler `data` dict
3. **FSM States**: aiogram StatesGroup for multi-step flows
4. **Enum-based Types**: All categorical data uses str enums with display properties
5. **Relationship Pattern**: SQLAlchemy relationships with `back_populates` and `cascade`

---

## Gamification Integration Architecture

### New Components Overview

```
┌─────────────────────────────────────────────────────────────────┐
│              GAMIFICATION SERVICE LAYER (New)                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              ServiceContainer (Extended)                 │    │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │    │
│  │  │   reaction   │ │    wallet    │ │     shop     │    │    │
│  │  │  - Track     │ │  - Balance   │ │  - Catalog   │    │    │
│  │  │  - Stats     │ │  - Transact  │ │  - Purchase  │    │    │
│  │  └──────────────┘ └──────────────┘ └──────────────┘    │    │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │    │
│  │  │    reward    │ │    streak    │ │  (existing)  │    │    │
│  │  │  - Achieve   │ │  - Daily     │ │  services... │    │    │
│  │  │  - Conditions│ │  - Tracking  │ │              │    │    │
│  │  └──────────────┘ └──────────────┘ └──────────────┘    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Integration Points with Existing Components

| Existing Component | Gamification Integration | Pattern |
|-------------------|-------------------------|---------|
| **ChannelService** | Reaction tracking on published content | Hook pattern - `publish_with_reactions()` wrapper |
| **ServiceContainer** | New lazy-loaded service properties | Extend container with new properties |
| **DatabaseMiddleware** | No changes needed - already injects container | Transparent - services accessed via container |
| **ContentPackage** | Reactions linked to packages | Foreign key relationship |
| **User** | Wallet balance, streaks, achievements | One-to-one relationships |
| **BroadcastStates** | Reaction selection in publishing flow | Extend existing FSM |

---

## New Components Specification

### 1. ReactionService

**Responsibility:** Track and manage inline button reactions on channel content

**Integration with existing:**
- Hooks into `ChannelService.send_to_channel()` via wrapper method
- Uses existing `BotConfig.vip_reactions` / `free_reactions` for available emojis
- Stores reaction counts per content item

**Key Methods:**
```python
async def track_content_reactions(
    self,
    content_id: int,
    channel_id: str,
    reactions: List[str]
) -> None:
    """Initialize reaction tracking for new content."""

async def record_reaction(
    self,
    user_id: int,
    content_id: int,
    reaction: str
) -> Tuple[bool, str]:
    """Record user reaction, returns (success, message)."""

async def get_reaction_stats(
    self,
    content_id: int
) -> Dict[str, int]:
    """Get reaction counts for content."""
```

**Database Model:**
```python
class ContentReaction(Base):
    """Reactions on published content."""
    __tablename__ = "content_reactions"

    id = Column(Integer, primary_key=True)
    content_id = Column(Integer, ForeignKey("content_packages.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    reaction = Column(String(10), nullable=False)  # Emoji
    created_at = Column(DateTime, default=datetime.utcnow)

    # Unique constraint: one reaction per user per content
    __table_args__ = (
        Index('idx_reaction_user_content', 'user_id', 'content_id', unique=True),
    )
```

---

### 2. WalletService

**Responsibility:** Virtual currency management with transaction history

**Integration with existing:**
- User model gets `wallet_balance` relationship
- Transactions logged for audit trail
- Atomic operations prevent race conditions

**Key Methods:**
```python
async def get_balance(self, user_id: int) -> Decimal:
    """Get current wallet balance."""

async def add_funds(
    self,
    user_id: int,
    amount: Decimal,
    source: TransactionSource,
    metadata: Optional[Dict] = None
) -> WalletTransaction:
    """Add funds to wallet (rewards, purchases, etc)."""

async def deduct_funds(
    self,
    user_id: int,
    amount: Decimal,
    purpose: TransactionPurpose,
    metadata: Optional[Dict] = None
) -> Tuple[bool, Optional[WalletTransaction]]:
    """Deduct funds, returns (success, transaction)."""

async def get_transaction_history(
    self,
    user_id: int,
    limit: int = 50
) -> List[WalletTransaction]:
    """Get user's transaction history."""
```

**Database Models:**
```python
class UserWallet(Base):
    """Virtual wallet for each user."""
    __tablename__ = "user_wallets"

    user_id = Column(BigInteger, ForeignKey("users.user_id"), primary_key=True)
    balance = Column(Numeric(15, 2), default=0, nullable=False)
    total_earned = Column(Numeric(15, 2), default=0, nullable=False)
    total_spent = Column(Numeric(15, 2), default=0, nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class WalletTransaction(Base):
    """Audit trail of all wallet movements."""
    __tablename__ = "wallet_transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)  # Positive = credit, Negative = debit
    balance_after = Column(Numeric(15, 2), nullable=False)
    source = Column(Enum(TransactionSource), nullable=False)
    purpose = Column(Enum(TransactionPurpose), nullable=True)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Concurrency Strategy:**
- Use `with_for_update()` when reading balance before modification
- Optimistic locking with `version_id` column if high contention expected
- SQLite WAL mode already handles read concurrency

---

### 3. ShopService

**Responsibility:** Product catalog and purchase processing

**Integration with existing:**
- Links to `ContentPackage` for digital goods
- Uses `WalletService` for payment processing
- Admin creates products via cascading FSM flow

**Key Methods:**
```python
async def create_product(
    self,
    name: str,
    description: str,
    price: Decimal,
    product_type: ProductType,
    content_package_id: Optional[int] = None,
    stock: Optional[int] = None,
) -> ShopProduct:
    """Create new product in catalog."""

async def get_available_products(
    self,
    user_role: UserRole
) -> List[ShopProduct]:
    """Get products available to user based on role."""

async def purchase_product(
    self,
    user_id: int,
    product_id: int
) -> Tuple[bool, str, Optional[Purchase]]:
    """Process purchase, returns (success, message, purchase)."""

async def get_user_purchases(
    self,
    user_id: int
) -> List[Purchase]:
    """Get user's purchase history."""
```

**Database Models:**
```python
class ShopProduct(Base):
    """Product in the shop catalog."""
    __tablename__ = "shop_products"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    product_type = Column(Enum(ProductType), nullable=False)
    content_package_id = Column(Integer, ForeignKey("content_packages.id"), nullable=True)
    stock = Column(Integer, nullable=True)  # NULL = unlimited
    is_active = Column(Boolean, default=True)
    min_role = Column(Enum(UserRole), default=UserRole.FREE)  # Role requirement
    created_at = Column(DateTime, default=datetime.utcnow)

class Purchase(Base):
    """Purchase record."""
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    product_id = Column(Integer, ForeignKey("shop_products.id"), nullable=False)
    price_paid = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum(PurchaseStatus), default=PurchaseStatus.COMPLETED)
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

### 4. RewardService

**Responsibility:** Achievement system with configurable conditions

**Integration with existing:**
- **Cascading admin flow**: Creating reward inline with conditions
- Checks conditions via `ConditionEvaluator` strategy pattern
- Awards via `WalletService.add_funds()` or direct benefits

**Key Methods:**
```python
async def create_reward(
    self,
    name: str,
    description: str,
    reward_type: RewardType,
    reward_value: Decimal,
    conditions: List[ConditionConfig],
) -> Reward:
    """Create achievement with conditions."""

async def check_and_award(
    self,
    user_id: int,
    trigger_event: RewardTrigger,
    event_data: Dict,
) -> List[Reward]:
    """Check conditions and award eligible rewards."""

async def get_user_achievements(
    self,
    user_id: int
) -> List[UserAchievement]:
    """Get user's earned achievements."""

async def get_progress(
    self,
    user_id: int,
    reward_id: int
) -> RewardProgress:
    """Get progress toward specific achievement."""
```

**Database Models:**
```python
class Reward(Base):
    """Achievement/quest definition."""
    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=False)
    reward_type = Column(Enum(RewardType), nullable=False)  # CURRENCY, BADGE, ROLE, etc
    reward_value = Column(Numeric(10, 2), nullable=True)  # For currency rewards
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class RewardCondition(Base):
    """Condition for earning a reward."""
    __tablename__ = "reward_conditions"

    id = Column(Integer, primary_key=True)
    reward_id = Column(Integer, ForeignKey("rewards.id"), nullable=False)
    condition_type = Column(Enum(ConditionType), nullable=False)  # STREAK_DAYS, REACTIONS_GIVEN, etc
    operator = Column(Enum(ConditionOperator), nullable=False)  # EQ, GT, GTE, etc
    target_value = Column(Integer, nullable=False)
    priority = Column(Integer, default=0)  # For ordering in cascading creation

class UserAchievement(Base):
    """User's earned achievement."""
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    reward_id = Column(Integer, ForeignKey("rewards.id"), nullable=False)
    earned_at = Column(DateTime, default=datetime.utcnow)

class RewardProgress(Base):
    """Track progress toward conditional rewards."""
    __tablename__ = "reward_progress"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    reward_id = Column(Integer, ForeignKey("rewards.id"), nullable=False)
    current_value = Column(Integer, default=0)
    is_complete = Column(Boolean, default=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

---

### 5. StreakService

**Responsibility:** Daily activity tracking with streak mechanics

**Integration with existing:**
- Background task checks and updates streaks daily
- Triggers `RewardService.check_and_award()` on streak milestones
- Uses `UserActivity` model for granular tracking

**Key Methods:**
```python
async def record_activity(
    self,
    user_id: int,
    activity_type: ActivityType,
) -> None:
    """Record user activity for streak calculation."""

async def get_current_streak(self, user_id: int) -> int:
    """Get current consecutive days streak."""

async def get_streak_info(self, user_id: int) -> StreakInfo:
    """Get detailed streak information."""

async def check_streak_breaks(self) -> List[int]:
    """Background task: identify and reset broken streaks."""
```

**Database Models:**
```python
class UserStreak(Base):
    """User's streak information."""
    __tablename__ = "user_streaks"

    user_id = Column(BigInteger, ForeignKey("users.user_id"), primary_key=True)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_activity_date = Column(Date, nullable=True)
    streak_started_at = Column(Date, nullable=True)

class UserActivity(Base):
    """Granular activity log for streak calculation."""
    __tablename__ = "user_activities"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    activity_type = Column(Enum(ActivityType), nullable=False)
    activity_date = Column(Date, nullable=False)  # Date only for daily tracking
    count = Column(Integer, default=1)  # Multiple activities same day

    __table_args__ = (
        Index('idx_activity_user_date_type', 'user_id', 'activity_date', 'activity_type', unique=True),
    )
```

---

## Cascading Admin Flow Architecture

### The Challenge

Admin must create rewards with conditions **without leaving the flow**. This requires:
1. Nested FSM states (reward creation -> condition creation -> back to reward)
2. State data persistence across transitions
3. Inline condition management (add/edit/remove)

### FSM State Design

```python
class RewardCreationStates(StatesGroup):
    """
    Cascading FSM for reward creation with inline conditions.

    Flow:
    1. waiting_for_name -> Admin enters reward name
    2. waiting_for_description -> Admin enters description
    3. waiting_for_reward_type -> Admin selects type (buttons)
    4. waiting_for_reward_value -> Admin enters value (if applicable)
    5. managing_conditions -> Main state for condition management
       - add_condition_type -> Select condition type
       - add_condition_operator -> Select operator (>, =, etc)
       - add_condition_value -> Enter target value
       - back to managing_conditions
    6. confirm_creation -> Review and confirm
    """

    # Basic reward info
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_reward_type = State()
    waiting_for_reward_value = State()

    # Condition management (cascading)
    managing_conditions = State()  # Main hub state
    add_condition_type = State()
    add_condition_operator = State()
    add_condition_value = State()

    # Final confirmation
    confirm_creation = State()
```

### State Data Structure

```python
# Stored in FSM context (state.get_data() / state.update_data())
reward_draft = {
    "name": "Early Bird",
    "description": "React to 5 posts in first hour",
    "reward_type": "CURRENCY",
    "reward_value": "50.00",
    "conditions": [
        {
            "id": "temp_1",  # Temporary ID for editing
            "type": "REACTIONS_GIVEN",
            "operator": "GTE",
            "target_value": 5,
            "time_window": "1h"  # Optional modifier
        }
    ],
    "editing_condition_id": None,  # Track which condition is being edited
}
```

### UI Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    REWARD CREATION FLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Enter Name] -> [Enter Description] -> [Select Type] -> [Value]   │
│       ↓                                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              MANAGE CONDITIONS SCREEN                    │    │
│  │                                                          │    │
│  │  Current Conditions:                                     │    │
│  │  1. Reactions Given >= 5  [Edit] [Delete]                │    │
│  │  2. Streak Days >= 7      [Edit] [Delete]                │    │
│  │                                                          │    │
│  │  [+ Add Condition]  [Done - Create Reward]              │    │
│  └─────────────────────────────────────────────────────────┘    │
│       ↓ (Add Condition)                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              ADD CONDITION FLOW                          │    │
│  │                                                          │    │
│  │  Step 1: Select Type                                     │    │
│  │  [Streak Days] [Reactions] [Purchases] [Custom]         │    │
│  │       ↓                                                  │    │
│  │  Step 2: Select Operator                                 │    │
│  │  [= Equals] [> Greater] [>= Greater/Eq] [<] [<=]          │    │
│  │       ↓                                                  │    │
│  │  Step 3: Enter Value                                     │    │
│  │  "Send target number (e.g., 5)"                         │    │
│  │       ↓                                                  │    │
│  │  [Back to Manage Conditions]                            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Changes

### Current Flow (Content Publishing)

```
Admin Handler
    ↓
ChannelService.send_to_channel()
    ↓
Telegram API (send message)
    ↓
Message returned with message_id
```

### New Flow (Content Publishing with Reactions)

```
Admin Handler
    ↓
ReactionService.publish_with_reactions(
    content=content,
    reactions=["👍", "❤️", "🔥"],
    channel_id=channel_id
)
    ↓
ChannelService.send_to_channel()  # Existing method
    ↓
Telegram API (send message)
    ↓
Message returned with message_id
    ↓
ContentTracking initialized (message_id, reactions)
    ↓
Reaction keyboard attached to message
```

### Reward Trigger Flow

```
User Action (e.g., gives reaction)
    ↓
Reaction Handler
    ↓
ReactionService.record_reaction()
    ↓
RewardService.check_and_award(
    trigger=REACTION_GIVEN,
    event_data={"content_id": 123, "reaction": "🔥"}
)
    ↓
ConditionEvaluator.check_conditions(user_id, reward)
    ↓
If conditions met:
    - WalletService.add_funds() OR
    - Badge awarded OR
    - Role upgraded
    ↓
User notified of achievement
```

---

## Service Container Extension

### New Properties to Add

```python
class ServiceContainer:
    # ... existing properties ...

    # ===== GAMIFICATION SERVICES =====

    @property
    def reaction(self):
        """Service for tracking content reactions."""
        if self._reaction_service is None:
            from bot.services.reaction import ReactionService
            self._reaction_service = ReactionService(self._session, self._bot)
        return self._reaction_service

    @property
    def wallet(self):
        """Service for virtual currency management."""
        if self._wallet_service is None:
            from bot.services.wallet import WalletService
            self._wallet_service = WalletService(self._session)
        return self._wallet_service

    @property
    def shop(self):
        """Service for product catalog and purchases."""
        if self._shop_service is None:
            from bot.services.shop import ShopService
            self._shop_service = ShopService(self._session, self)
        return self._shop_service

    @property
    def reward(self):
        """Service for achievements and conditions."""
        if self._reward_service is None:
            from bot.services.reward import RewardService
            self._reward_service = RewardService(self._session, self)
        return self._reward_service

    @property
    def streak(self):
        """Service for daily streak tracking."""
        if self._streak_service is None:
            from bot.services.streak import StreakService
            self._streak_service = StreakService(self._session, self)
        return self._streak_service
```

---

## New Enums Required

```python
class TransactionSource(str, Enum):
    """Sources of wallet credits."""
    PURCHASE = "PURCHASE"           # User bought currency
    REWARD = "REWARD"               # Achievement reward
    STREAK_BONUS = "STREAK_BONUS"   # Daily streak bonus
    REFUND = "REFUND"               # Purchase refund
    ADMIN_GRANT = "ADMIN_GRANT"     # Manual admin grant

class TransactionPurpose(str, Enum):
    """Purposes for wallet debits."""
    SHOP_PURCHASE = "SHOP_PURCHASE"
    CONTENT_UNLOCK = "CONTENT_UNLOCK"
    TRANSFER = "TRANSFER"

class ProductType(str, Enum):
    """Types of shop products."""
    DIGITAL_CONTENT = "DIGITAL_CONTENT"  # Links to ContentPackage
    CURRENCY_PACK = "CURRENCY_PACK"      # Buy virtual currency
    BADGE = "BADGE"                      # Cosmetic badge
    ROLE_UPGRADE = "ROLE_UPGRADE"        # Temporary role boost

class RewardType(str, Enum):
    """Types of rewards."""
    CURRENCY = "CURRENCY"        # Virtual currency amount
    BADGE = "BADGE"              # Achievement badge
    ROLE_TEMP = "ROLE_TEMP"      # Temporary role upgrade
    DISCOUNT = "DISCOUNT"        # Shop discount code
    CONTENT = "CONTENT"          # Free content unlock

class ConditionType(str, Enum):
    """Types of achievement conditions."""
    STREAK_DAYS = "STREAK_DAYS"
    REACTIONS_GIVEN = "REACTIONS_GIVEN"
    REACTIONS_RECEIVED = "REACTIONS_RECEIVED"
    PURCHASES_MADE = "PURCHASES_MADE"
    CONTENT_VIEWED = "CONTENT_VIEWED"
    DAYS_SINCE_JOIN = "DAYS_SINCE_JOIN"
    REFERRALS = "REFERRALS"

class ConditionOperator(str, Enum):
    """Comparison operators for conditions."""
    EQ = "EQ"      # Equal
    GT = "GT"      # Greater than
    GTE = "GTE"    # Greater than or equal
    LT = "LT"      # Less than
    LTE = "LTE"    # Less than or equal

class RewardTrigger(str, Enum):
    """Events that can trigger reward checking."""
    REACTION_GIVEN = "REACTION_GIVEN"
    REACTION_RECEIVED = "REACTION_RECEIVED"
    PURCHASE_COMPLETED = "PURCHASE_COMPLETED"
    STREAK_MILESTONE = "STREAK_MILESTONE"
    CONTENT_PUBLISHED = "CONTENT_PUBLISHED"
    DAILY_CHECKIN = "DAILY_CHECKIN"
```

---

## Suggested Build Order

### Phase 1: Foundation (Week 1)

1. **Database Models** (3 days)
   - Create all gamification models
   - Migration script
   - Test data fixtures

2. **Enums** (1 day)
   - All gamification enums
   - Display properties

3. **Service Container Extension** (1 day)
   - Add new service properties
   - Update `get_loaded_services()`

### Phase 2: Core Services (Week 2)

4. **WalletService** (3 days)
   - Balance management
   - Transaction history
   - Concurrency safety

5. **ReactionService** (2 days)
   - Reaction tracking
   - Stats aggregation
   - Integration with ChannelService

### Phase 3: Gamification Features (Week 3)

6. **StreakService** (2 days)
   - Daily tracking
   - Background task integration

7. **RewardService** (3 days)
   - Achievement definitions
   - Condition evaluation engine
   - Progress tracking

### Phase 4: Commerce (Week 4)

8. **ShopService** (2 days)
   - Product catalog
   - Purchase processing

9. **Cascading Admin Flow** (3 days)
   - RewardCreationStates FSM
   - Inline condition management
   - UI/UX polish

### Phase 5: Integration (Week 5)

10. **Handler Integration** (3 days)
    - Admin handlers for gamification
    - User-facing features
    - Callback handlers

11. **Background Tasks** (2 days)
    - Streak break detection
    - Reward evaluation triggers

---

## Anti-Patterns to Avoid

### 1. Service Circular Dependencies

**Bad:**
```python
# RewardService imports WalletService
# WalletService imports RewardService (for rewards)
```

**Good:**
```python
# RewardService receives ServiceContainer
# Accesses wallet via self._container.wallet
# Container handles lazy loading
```

### 2. Direct Model Access in Handlers

**Bad:**
```python
# Handler directly queries Wallet model
async def handler(message: Message, session: AsyncSession):
    wallet = await session.get(UserWallet, user_id)
```

**Good:**
```python
# Handler uses service layer
async def handler(message: Message, container: ServiceContainer):
    balance = await container.wallet.get_balance(user_id)
```

### 3. FSM State Data Bloat

**Bad:**
```python
# Storing large objects in state
await state.update_data(reward_object=reward)  # SQLAlchemy model
```

**Good:**
```python
# Store only IDs and simple data
await state.update_data(reward_id=reward.id, name=reward.name)
# Re-fetch from DB when needed
```

### 4. Race Conditions in Wallet

**Bad:**
```python
# Read then write without locking
balance = await self.get_balance(user_id)
new_balance = balance - amount
# Another transaction could modify balance here!
```

**Good:**
```python
# Atomic update with optimistic locking
result = await session.execute(
    update(UserWallet)
    .where(UserWallet.user_id == user_id)
    .where(UserWallet.balance >= amount)
    .values(balance=UserWallet.balance - amount)
)
if result.rowcount == 0:
    raise InsufficientFundsError()
```

---

## Scaling Considerations

| Scale | Considerations |
|-------|---------------|
| **Current** (< 1K users) | SQLite with WAL mode sufficient. All services in one process. |
| **Growth** (1K - 10K users) | Consider PostgreSQL. Add connection pooling. Background tasks in separate thread. |
| **Scale** (10K+ users) | Redis for session/cache. Separate worker processes for background tasks. Read replicas for analytics. |

### Performance Optimizations

1. **Reaction Aggregation**: Cache reaction counts in Redis to avoid COUNT queries
2. **Streak Calculation**: Batch process streak updates nightly, not per-activity
3. **Reward Evaluation**: Use event queue instead of synchronous checking
4. **Wallet Transactions**: Keep hot balances in cache with DB persistence

---

## Files to Create/Modify

### New Files

```
bot/services/
├── reaction.py          # ReactionService
├── wallet.py            # WalletService
├── shop.py              # ShopService
├── reward.py            # RewardService
├── streak.py            # StreakService
└── condition_evaluator.py  # Strategy pattern for conditions

bot/database/models.py   # Add gamification models
bot/database/enums.py    # Add gamification enums

bot/states/admin.py      # Add RewardCreationStates

bot/handlers/admin/
├── gamification.py      # Admin gamification handlers
└── rewards.py           # Reward creation handlers (cascading flow)

bot/handlers/user/
├── reactions.py         # User reaction handlers
├── wallet.py            # User wallet handlers
├── shop.py              # User shop handlers
└── achievements.py      # User achievement handlers

bot/background/
└── gamification_tasks.py  # Background tasks for gamification
```

### Modified Files

```
bot/services/container.py     # Add new service properties
bot/services/channel.py       # Add publish_with_reactions()
bot/handlers/admin/menu.py    # Add gamification menu options
```

---

## Sources

- Existing codebase analysis (ServiceContainer, models, services)
- aiogram FSM documentation patterns
- SQLAlchemy relationship best practices
- Telegram Bot API inline keyboard patterns

---

*Architecture research for: Gamification Milestone*
*Researched: 2026-02-08*
