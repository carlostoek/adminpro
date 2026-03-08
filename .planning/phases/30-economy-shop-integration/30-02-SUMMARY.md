---
phase: 30-economy-shop-integration
plan: 02
type: execute
wave: 2
subsystem: narrative
tags: ["economy", "rewards", "choices", "cost-processing"]

dependency_graph:
  requires: ["30-01"]
  provides: ["30-03", "30-04", "30-05"]
  affects: ["bot/services/narrative.py", "bot/services/container.py"]

tech_stack:
  added: []
  patterns:
    - "Atomic cost deduction with transaction logging"
    - "Idempotency check via transaction query"
    - "Batched reward notification with voice architecture"
    - "Service injection via lazy loading"

key_files:
  created: []
  modified:
    - bot/services/narrative.py
    - bot/services/container.py

decisions:
  - "Use TransactionType.SPEND_STORY_CHOICE for choice costs"
  - "Check claim_count to prevent replay farming on node rewards"
  - "Diana's voice (🫦) for reward notifications (user-facing content)"
  - "Idempotency key combines choice_id + source_node_id for uniqueness"

metrics:
  duration: "~15 minutes"
  tasks_completed: 5/5
  commits: 5
  files_modified: 2
  lines_added: ~395
  methods_added: 5
---

# Phase 30 Plan 02: Choice Cost Processing Summary

**One-liner:** NarrativeService now charges besitos for story choices and delivers node rewards atomically, with double-spending protection via idempotency checks.

## Deliverables

### 1. Choice Cost Deduction (`_deduct_choice_cost`)
- **Location:** `bot/services/narrative.py:1032-1100`
- **Purpose:** Atomic besitos deduction for costly choices
- **Integration:** Uses `wallet_service.spend_besitos()` with `TransactionType.SPEND_STORY_CHOICE`
- **Returns:** `(success, message, transaction)` tuple
- **Features:**
  - VIP cost calculation via `calculate_choice_cost()`
  - Graceful handling when wallet_service unavailable
  - Full metadata logging (choice_id, source/target nodes, user_role)

### 2. Node Reward Delivery (`_deliver_node_rewards`)
- **Location:** `bot/services/narrative.py:853-952`
- **Purpose:** Deliver rewards when user reaches a node
- **Integration:** Uses `reward_service.claim_reward()`
- **Returns:** `(all_delivered, results_list)` tuple
- **Anti-farming Protection:**
  - Checks `claim_count` for non-repeatable rewards
  - Skips already-claimed rewards
  - Tracks delivery results per reward

### 3. Batched Reward Notification (`build_reward_notification`)
- **Location:** `bot/services/narrative.py:954-1029`
- **Purpose:** Build user-facing reward summary message
- **Voice:** Diana (🫦) for intimate user content
- **Formats:**
  - Single reward: "🫦 Sorpresa... Has recibido: +X besitos"
  - Multiple rewards: "🫦 Qué suerte... Has recibido: - item 1 - item 2"
- **Helper:** `_format_reward_description()` handles BESITOS, VIP_EXTENSION, CONTENT, BADGE types

### 4. Enhanced `make_choice` Method
- **Location:** `bot/services/narrative.py:293-490`
- **New Signature:** Added `user_role: str = "FREE"` parameter
- **New Return:** 5-tuple with info dict containing:
  - `cost_deducted: bool`
  - `cost_amount: int`
  - `rewards_delivered: List[Dict]`
  - `notification_text: Optional[str]`
- **New Flow:**
  1. Validate ownership
  2. Fetch choice with eager loading
  3. Validate choice belongs to current node
  4. **NEW:** Validate conditions via `evaluate_choice_conditions()`
  5. **NEW:** Idempotency check (query existing SPEND_STORY_CHOICE transaction)
  6. **NEW:** Deduct cost via `_deduct_choice_cost()`
  7. Record decision (now includes cost info)
  8. Advance to target node
  9. **NEW:** Deliver rewards via `_deliver_node_rewards()`
  10. **NEW:** Build notification via `build_reward_notification()`
  11. Check for story completion

### 5. ServiceContainer Integration
- **Location:** `bot/services/container.py:600-614`
- **Change:** `narrative` property now injects:
  - `wallet_service=self.wallet`
  - `reward_service=self.reward`
  - `shop_service=self.shop`
  - `streak_service=self.streak`
- **Pattern:** Maintains lazy loading - services injected on first access

## Key Design Decisions

### Idempotency Implementation
```python
# Query existing transaction for this choice + source node combination
existing_tx = await self.session.execute(
    select(Transaction).where(
        Transaction.user_id == user_id,
        Transaction.type == TransactionType.SPEND_STORY_CHOICE,
        Transaction.transaction_metadata.contains({"choice_id": choice_id}),
        Transaction.transaction_metadata.contains({"source_node_id": ...})
    )
)
```
- Uses composite key: choice_id + source_node_id
- Prevents double-spending on rapid clicks or retries
- Transaction query is fast (indexed on user_id + type)

### Replay Farming Prevention
```python
# For non-repeatable rewards, check if already claimed
if not reward.is_repeatable:
    user_reward = await self._get_user_reward(user_id, reward.id)
    if user_reward and user_reward.claim_count > 0:
        skip_this_reward()
```
- Only applies to non-repeatable rewards
- Respects the `is_repeatable` flag on Reward model
- Allows legitimate re-claims for repeatable rewards

### Voice Architecture Compliance
- **Diana (🫦):** Reward notifications (user-facing content)
- **Lucien (🎩):** Condition requirement messages (system/service context)

## Commits

| Hash | Message |
|------|---------|
| d025652 | feat(30-02): add choice cost deduction method to NarrativeService |
| 1531a69 | feat(30-02): add node reward delivery method to NarrativeService |
| 3008512 | feat(30-02): add batched reward notification builder |
| 3fc861a | feat(30-02): enhance make_choice with cost and rewards |
| 210ca89 | feat(30-02): update ServiceContainer for NarrativeService injection |

## Verification Checklist

- [x] `_deduct_choice_cost` method exists and uses `wallet_service.spend_besitos`
- [x] `_deliver_node_rewards` method exists and uses `reward_service.claim_reward`
- [x] `build_reward_notification` method exists for batched reward messages
- [x] `make_choice` validates conditions before processing
- [x] `make_choice` checks for existing SPEND_STORY_CHOICE transaction (idempotency)
- [x] `make_choice` deducts cost atomically with SPEND_STORY_CHOICE transaction type
- [x] `make_choice` delivers node rewards after advancing
- [x] ServiceContainer injects wallet, reward, shop, and streak services into NarrativeService

## Deviations from Plan

None - plan executed exactly as written.

## Next Steps

Plan 30-03 (parallel wave 2) will implement:
- Locked choice display in story keyboard
- Insufficient balance handling with recovery paths
- Cost preview in choice confirmation dialogs
