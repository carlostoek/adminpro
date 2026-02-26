# Feature Landscape: v3 Narrativa Branching Story System

**Domain:** Interactive narrative system for Telegram bot
**Researched:** 2026-02-26
**Overall confidence:** HIGH (based on existing codebase analysis)

---

## Executive Summary

The v3 Narrativa system extends the existing DianaBot ecosystem (42k+ lines, gamification, shop, rewards) with a modular branching story engine. Key insight: this is NOT a generic story system - it is deeply integrated with the existing gamification layer (besitos economy, rewards, conditions) and must leverage the cascading condition system already built.

**Core philosophy:** Stories are content that users "play through" - each segment is a node with choices, and choices have consequences (unlock content, trigger rewards, consume items, affect future narrative paths).

---

## Table Stakes Features

Features users expect from ANY narrative system. Missing these = product feels broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Story segments/nodes** | Basic unit of narrative - text + choices | Low | Each node has: text (with media), choices array, optional effects |
| **Branching choices** | Core mechanic - user decisions matter | Low | 1-4 choices per node, each leads to another node or ends story |
| **Progress persistence** | Users expect to resume where they left off | Low | Track current node per user per story |
| **Multiple stories** | Different narratives for different contexts | Medium | Free stories (1-3), VIP stories (4-6), event stories |
| **Start/end states** | Clear story boundaries | Low | Entry nodes, terminal nodes with endings |
| **Visual feedback** | Progress indication | Low | "Part 3 of 12", progress bar, chapter markers |

### Table Stakes - Admin Side

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Story editor** | Create and modify stories | Medium | FSM wizard pattern (existing) |
| **Node management** | CRUD for story nodes | Medium | Link nodes, set choices, configure effects |
| **Activation control** | Publish/unpublish stories | Low | Soft delete pattern (existing) |
| **Preview mode** | Test stories before release | Medium | Admin can run through story as any user type |

---

## Differentiators

Features that make this narrative system unique, leveraging existing infrastructure.

### 1. Deep Gamification Integration

| Feature | Value Proposition | Complexity | Integration Point |
|---------|-------------------|------------|-------------------|
| **Choice costs** | Spend besitos to make choices | Low | Wallet service deduction on choice selection |
| **Story rewards** | Unlock rewards at specific nodes | Low | Hook into existing `RewardService.check_rewards_on_event()` |
| **Conditional paths** | Choices visible only if conditions met | Medium | Reuse `RewardCondition` system (AND/OR groups) |
| **Inventory-gated content** | Require items to proceed | Medium | Check user inventory before showing choice |
| **Story achievements** | Complete story = badge/reward | Low | Trigger reward on reaching terminal node |

### 2. Tiered Narrative Access

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Free tier (levels 1-3)** | Hook users with intro content | Low | Available to all users |
| **VIP tier (levels 4-6)** | Monetization driver | Low | VIP-only stories, or VIP-only paths within stories |
| **Premium moments** | High-value content gates | Medium | Single nodes requiring VIP/Premium, not whole stories |
| **Progressive unlocking** | Complete story A to unlock B | Medium | Story dependencies tracked per user |

### 3. Dual Voice Architecture

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Lucien as guide** | Mayordomo narrates the framework | Low | System messages, transitions, meta-commentary |
| **Diana as presence** | The "character" users interact with | Low | Story content, direct address, intimate moments |
| **Voice switching** | Seamless handoff between voices | Medium | Clear conventions: Lucien = system, Diana = content |

### 4. Content-Rich Delivery

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Media per node** | Photo/video/audio in stories | Medium | Reuse `ContentSet`/`file_ids` pattern from shop |
| **Timed reveals** | Content appears after delay | Medium | Background task + user notification |
| **Multi-message sequences** | Long content split intelligently | Medium | Auto-split with "continues..." indicators |
| **Protected content** | Anti-screenshot/forward flags | Low | Telegram's protect_content parameter |

### 5. Metagame Elements

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Hidden paths** | Secret choices unlockable | Medium | Condition-based visibility |
| **Consequence tracking** | Decisions affect future stories | High | Cross-story state variables |
| **Collectible endings** | Multiple endings per story | Medium | Track which endings user has seen |
| **Story replay** | Re-experience with different choices | Low | Reset progress, keep endings unlocked |

---

## Anti-Features

Features to explicitly NOT build - common traps in narrative systems.

| Anti-Feature | Why Avoid | What To Do Instead |
|--------------|-----------|-------------------|
| **AI-generated content** | Inconsistent voice, quality issues | Hand-crafted stories with strict voice guidelines |
| **Sentiment analysis** | Unreliable, adds complexity | Explicit choice architecture - user clicks button, we know intent |
| **Procedural generation** | Feels generic, hurts immersion | Static stories with conditional branches (hand-authored) |
| **Real-time multiplayer** | Sync complexity, low value | Async shared experiences (same story, different times) |
| **Complex inventory puzzles** | Friction, user frustration | Simple item checks: have it or don't, choice visible or hidden |
| **Branching tree visualization** | Admin UI complexity | List view with parent/child references, not visual graph |
| **User-generated stories** | Moderation burden, quality control | Admin-only story creation |
| **Save/load slots** | Overkill for Telegram context | Auto-save at every node, single linear progress |
| **Difficulty levels** | Narrative doesn't need difficulty | Different stories for different engagement levels |
| **Voice acting** | File size, delivery complexity | Text with optional audio attachments |

---

## Feature Dependencies

```
Story Node
  ├── Text content (required)
  ├── Media attachments (optional)
  ├── Choices (1-4)
  │     ├── Choice text
  │     ├── Target node (next)
  │     ├── Visibility conditions (optional)
  │     ├── Cost (besitos, optional)
  │     └── Effects (optional)
  │           ├── Unlock reward
  │           ├── Grant item
  │           ├── Set flag
  │           └── Trigger event
  └── Node effects (on entry)
        └── Same as choice effects

Story
  ├── Entry node
  ├── Terminal nodes (endings)
  ├── Tier (Free/VIP/Premium)
  ├── Prerequisites (stories to complete first)
  └── Published flag

User Progress
  ├── Current node per story
  ├── Completed stories
  ├── Unlocked endings
  └── Story flags (consequences)
```

---

## Integration with Existing Systems

### Gamification Integration Points

| System | Integration | Implementation |
|--------|-------------|----------------|
| **Wallet/Besitos** | Choice costs, story unlocks | `WalletService.spend_besitos()` before choice processing |
| **Rewards** | Story completion rewards | `RewardService.check_rewards_on_event("story_completed")` |
| **Conditions** | Choice visibility | Reuse `RewardCondition` pattern with AND/OR groups |
| **Inventory** | Item-gated choices | Check `UserContentAccess` or new inventory table |
| **Shop** | Buy story access | Product type = "story_unlock" |

### Content System Integration

| System | Integration | Implementation |
|--------|-------------|----------------|
| **ContentSet** | Media in stories | Node has optional `content_set_id` |
| **ContentPackage** | Story as product | Package type extension or new category |
| **ShopProduct** | Sell story access | Link product to story unlock |

### Admin System Integration

| System | Integration | Implementation |
|--------|-------------|----------------|
| **FSM Wizards** | Story creation flow | Extend existing wizard pattern |
| **Admin messages** | Lucien voice for admin | Use `AdminMainMessages` provider |
| **Pagination** | Story lists | Reuse `Paginator` utility |
| **Soft delete** | Unpublish stories | `is_active` flag pattern |

---

## MVP Recommendation

### Phase 1: Core Narrative Engine

Prioritize:
1. **Story node model** - Basic node with text + choices
2. **User progress tracking** - Current node per story
3. **Story reader handler** - Display node, handle choice selection
4. **Admin story wizard** - Create story, add nodes, link choices
5. **Simple progression** - Linear path, no conditions yet

Defer:
- Choice costs (Phase 2)
- Conditional visibility (Phase 2)
- Media attachments (Phase 2)
- Multiple endings tracking (Phase 3)
- Cross-story consequences (Phase 3)

### Phase 2: Gamification Hooks

Add:
1. **Choice costs** - Besitos deduction
2. **Story rewards** - Completion triggers reward unlock
3. **Conditional paths** - Reuse condition system
4. **VIP gating** - Role-based story access
5. **Media support** - ContentSet integration

### Phase 3: Advanced Features

Add:
1. **Multiple endings** - Track and display unlocked endings
2. **Story dependencies** - Complete A to unlock B
3. **Hidden paths** - Secret choices
4. **Timed content** - Delayed reveals
5. **Story replay** - Reset progress

---

## Database Schema (Proposed)

### Core Tables

```sql
-- Stories table
stories:
  - id (PK)
  - name
  - description
  - tier (FREE/VIP/PREMIUM)
  - entry_node_id (FK -> story_nodes)
  - is_active
  - created_at
  - updated_at

-- Story nodes table
story_nodes:
  - id (PK)
  - story_id (FK)
  - node_type (TEXT/CHOICE/TERMINAL)
  - content_text
  - content_set_id (FK, optional)
  - voice (LUCIEN/DIANA)
  - sort_order
  - created_at

-- Choices table
story_choices:
  - id (PK)
  - source_node_id (FK)
  - target_node_id (FK)
  - choice_text
  - choice_order
  - cost_besitos (default 0)
  - is_hidden (default false)
  - condition_group_id (FK, optional)

-- User progress table
user_story_progress:
  - id (PK)
  - user_id (FK)
  - story_id (FK)
  - current_node_id (FK)
  - status (IN_PROGRESS/COMPLETED/ABANDONED)
  - started_at
  - completed_at
  - last_accessed_at

-- User endings table
user_story_endings:
  - id (PK)
  - user_id (FK)
  - story_id (FK)
  - ending_node_id (FK)
  - unlocked_at

-- Story effects table (for both nodes and choices)
story_effects:
  - id (PK)
  - parent_type (NODE/CHOICE)
  - parent_id
  - effect_type (UNLOCK_REWARD/GRANT_ITEM/SET_FLAG/TRIGGER_EVENT)
  - effect_data (JSON)
  - sort_order
```

---

## UI/UX Patterns

### Reader Experience

```
[Story Title]

[Node content - Diana's voice]

<i>"El texto de la historia aquí..."</i>

[Media if present]

[Choices as inline buttons]
[Choice 1] -> leads to node X
[Choice 2] -> leads to node Y

[Progress indicator]
<i>Parte 3 de 12</i>
```

### Admin Experience

Reuse existing FSM wizard pattern:
1. Create story (name, description, tier)
2. Create first node (content)
3. Add choices (text, target node)
4. Create target nodes or link existing
5. Set effects (optional)
6. Publish

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Table stakes | HIGH | Standard narrative system patterns |
| Gamification integration | HIGH | Existing systems are mature and well-architected |
| Dual voice | HIGH | Voice architecture already established |
| Admin FSM | HIGH | Pattern proven in content/reward management |
| Database design | HIGH | Fits existing SQLAlchemy patterns |
| Telegram limitations | MEDIUM | Message length (4096), button limits (100 total, 3 per row) |
| Media handling | HIGH | ContentSet pattern already exists |

---

## Gaps to Address

1. **Story state machine** - Need clear IN_PROGRESS/COMPLETED/ABANDONED lifecycle
2. **Choice timeout** - What happens if user doesn't choose? (auto-save, allow resume)
3. **Concurrent story access** - Can user read multiple stories simultaneously? (recommend: yes)
4. **Story analytics** - Completion rates, choice popularity (defer to Phase 2)
5. **Content migration** - How to update published stories? (versioning vs immutable)

---

## Sources

- `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/database/models.py` - Existing models
- `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/services/reward.py` - Condition system
- `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/handlers/admin/reward_management.py` - FSM patterns
- `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/handlers/admin/content.py` - Admin CRUD patterns
- `/data/data/com.termux/files/home/repos/adminpro-narrativa2/docs/narrativa/diseno_conceptua.md` - Product vision
- `/data/data/com.termux/files/home/repos/adminpro-narrativa2/CLAUDE.md` - Architecture conventions
