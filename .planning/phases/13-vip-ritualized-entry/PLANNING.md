# Phase 13: VIP Ritualized Entry Flow - PLANNING

**Phase:** 13-vip-ritualized-entry
**Mode:** standard
**Status:** Ready for execution
**Created:** 2026-01-27

---

## Phase Overview

Replace the current VIP access flow (immediate link delivery after token activation) with a 3-phase sequential admission process that increases exclusivity perception, reduces impulsive access, and psychologically prepares users for the content type.

**Entry Condition:** User has valid VIPSubscriber record with `vip_entry_stage=1` (triggered by activation link)

**Exit Condition:** User completes Stage 3, receives 24-hour invite link, joins channel, and is assigned UserRole.VIP

---

## Plans Breakdown

### Plan 01: Database Extension - VIP Entry Stage Fields
**Wave:** 1
**Depends on:** []
**Files Modified:**
  - bot/database/models.py (VIPSubscriber model)
  - bot/services/subscription.py (activation logic)

**Objective:** Add database fields to track VIP entry stage progression (vip_entry_stage, vip_entry_token, invite_link_sent_at) and update activation logic to initialize stage=1.

**Key Changes:**
- Add `vip_entry_stage` column (Integer, default=1) to VIPSubscriber
- Add `vip_entry_token` column (String(64), unique, nullable) for one-time entry token
- Add `invite_link_sent_at` column (DateTime, nullable) for 24h link tracking
- Update `activate_vip_subscription()` to set `vip_entry_stage=1` on activation
- Add index on `vip_entry_stage` for efficient queries

---

### Plan 02: VIP Entry Flow Messages Provider
**Wave:** 1
**Depends on:** []
**Files Modified:**
  - bot/services/message/vip_entry.py (NEW FILE)

**Objective:** Create VIPEntryFlowMessages provider with Lucien's voice for 3-phase ritual (activation confirmation, expectation alignment, access delivery).

**Key Methods:**
- `stage_1_activation_confirmation()` - Mysterious acknowledgment
- `stage_2_expectation_alignment()` - Intimate warning about space nature
- `stage_3_access_delivery()` - Dramatic delivery with link button
- `expired_subscription_message()` - Lucien-voiced expiry blocking
- `stage_resumption_message()` - Seamless return to current stage

**Message Design:**
- Stage 1: "Veo que ha dado el paso que muchos contemplan... y pocos toman."
- Stage 2: "El Diván no es un lugar donde se mira y se olvida..."
- Stage 3: "Entonces no le haré esperar más. Diana le abre la puerta al Diván."
- Button progression: "Continuar" → "Estoy listo" → "Cruzar el umbral"

---

### Plan 03: VIP Entry FSM States and Handlers
**Wave:** 2
**Depends on:** [01, 02]
**Files Modified:**
  - bot/states/user.py (add VIPEntryStates)
  - bot/handlers/user/vip_entry.py (NEW FILE)
  - bot/handlers/user/start.py (modify activation logic)

**Objective:** Implement VIPEntryStates FSM group and handlers for 3-stage flow with stage transition validation and resumption logic.

**FSM States:**
```python
class VIPEntryStates(StatesGroup):
    stage_1_confirmation = State()  # Awaiting "Continuar"
    stage_2_alignment = State()     # Awaiting "Estoy listo"
    stage_3_delivery = State()      # Link sent, awaiting join
```

**Handler Logic:**
- Check `vip_entry_stage` on /start to determine current stage
- Validate VIPSubscriber expiry before allowing continuation
- Handle button clicks: "Continuar" (stage 1→2), "Estoy listo" (stage 2→3)
- Seamless resumption: return to current stage if user abandons
- Expiry check: show Lucien's expiry message if subscription expired

---

### Plan 04: VIP Entry Service with Link Generation
**Wave:** 2
**Depends on:** [01]
**Files Modified:**
  - bot/services/vip_entry.py (NEW FILE)
  - bot/services/container.py (add vip_entry property)

**Objective:** Create VIPEntryService with stage validation, 24-hour invite link generation, and expiry cancellation logic.

**Service Methods:**
```python
class VIPEntryService:
    async def get_current_stage(user_id: int) -> int
    async def advance_stage(user_id: int, from_stage: int) -> bool
    async def generate_entry_token(user_id: int) -> str
    async def is_entry_token_valid(token: str) -> bool
    async def create_24h_invite_link(user_id: int) -> ChatInviteLink
    async def cancel_entry_on_expiry(user_id: int) -> None
```

**Key Logic:**
- Stage progression: 1 → 2 → 3 → complete (vip_entry_stage = None)
- Generate unique `vip_entry_token` for one-time use
- Create invite link with 24h expiry (member_limit=1)
- Cancel entry if VIPSubscriber expires during flow
- Integration with existing `expire_vip_subscribers()` background task

---

## Integration Points

### Entry Point (start.py - line 177+)
**Current Flow:**
1. Token validated → VIPSubscriber created
2. UserRole set to VIP
3. Invite link generated immediately
4. Success message with link sent

**New Flow:**
1. Token validated → VIPSubscriber created with `vip_entry_stage=1`
2. UserRole remains FREE until stage 3 completion
3. Send Stage 1 message (activation confirmation)
4. User clicks "Continuar" → Stage 2
5. User clicks "Estoy listo" → Stage 3 (link generated, UserRole set to VIP)
6. User joins channel → entry complete

### Role Detection (role_change.py)
**Current:** UserRole.VIP assigned immediately after token activation

**New:** UserRole.VIP assigned only after Stage 3 completion
- During stages 1-2: User still has UserRole.FREE
- After Stage 3: UserRole changes to VIP with RoleChangeReason.VIP_ENTRY_COMPLETED
- RoleDetectionService detects VIPSubscriber + vip_entry_stage to show entry flow

### Background Task (tasks.py)
**Current:** `expire_vip_subscribers()` removes expired users from channel

**New:** Also cancel VIP entry flow if subscription expires during stages 1-2
- Check `vip_entry_stage` field
- If stage < 3 and subscription expired: send expiry message, block continuation

---

## must_haves (Goal-Backward Verification)

1. ✅ User with valid VIPSubscriber but vip_entry_stage=1 receives Stage 1 message (not immediate link)
2. ✅ Stage 1 message has "Continuar" button that advances to Stage 2
3. ✅ Stage 2 message has "Estoy listo" button that advances to Stage 3
4. ✅ Stage 3 message includes "Cruzar el umbral" button with 24-hour invite link
5. ✅ Invite link is unique (vip_entry_token) and expires after 24 hours
6. ✅ UserRole changes from FREE to VIP only after Stage 3 completion
7. ✅ User can abandon flow and resume from current stage (no timeout)
8. ✅ If VIPSubscriber expires during stages 1-2, user sees Lucien's expiry message and cannot continue
9. ✅ All messages use Lucien's voice with 🎩 emoji (no variations, same ritual for everyone)
10. ✅ Stage 3 delivery IS the welcome (no duplicate channel welcome message)

---

## Wave Structure

**Wave 1 (Parallel Execution):**
- Plan 01: Database Extension
- Plan 02: Messages Provider

**Wave 2 (Depends on Wave 1):**
- Plan 03: FSM States and Handlers
- Plan 04: VIP Entry Service

---

## Success Criteria

1. **Ritual Experience:** Every VIP goes through the same 3-stage ceremony with Lucien's voice
2. **Exclusivity Perception:** Users feel they're being admitted to an exclusive space (not just clicking a link)
3. **Psychological Preparation:** Stage 2 sets expectations about intimate, unfiltered content
4. **Reduced Impulsivity:** Sequential progression prevents casual browsing
5. **Technical Robustness:** Seamless resumption, expiry handling, 24-hour link validity

---

## Testing Strategy

### Unit Tests
- VIPEntryService stage progression logic
- Token generation and validation
- Expiry cancellation logic

### Integration Tests
- /start with token activation → Stage 1 message
- Button clicks → Stage transitions
- Abandonment and resumption
- Expiry during flow → blocking message

### E2E Tests
- Complete flow: Token → Stage 1 → Stage 2 → Stage 3 → Channel join
- Role detection: FREE during stages 1-2, VIP after Stage 3
- Expired subscription: Blocking message at any stage

---

## Dependencies

**Internal:**
- Phase 5 (Role Detection & Database Foundation) - VIPSubscriber model
- Phase 6 (VIP/Free User Menus) - User menu structure
- Phase 8 (Interest Notification System) - Not needed for entry flow

**External:**
- Aiogram 3.4.1 FSM states
- SQLAlchemy 2.0.25 async ORM
- Existing background task infrastructure

---

## Risks & Mitigations

**Risk:** Users confused by new multi-stage flow
**Mitigation:** Clear progression with Lucien's narrative voice, explicit button text

**Risk:** Existing VIP subscribers (activated before Phase 13) don't have vip_entry_stage field
**Mitigation:** Migration script sets vip_entry_stage=None for existing active subscribers (skip flow)

**Risk:** 24-hour link expires before user joins
**Mitigation:** User can request new link via /start (restarts from Stage 3 if subscription still valid)

**Risk:** Background task doesn't clean up expired entry flows
**Mitigation:** Integrate with existing expire_vip_subscribers() task, add entry cancellation logic

---

## Migration Strategy

**Existing VIP Subscribers:**
- vip_entry_stage = NULL (completed flow before implementation)
- Continue to work normally (no flow restart)

**New VIP Activations:**
- vip_entry_stage = 1 (start ritual flow)
- UserRole remains FREE until Stage 3 completion
- RoleDetectionService detects vip_entry_stage to show entry flow

**Database Migration:**
```sql
ALTER TABLE vip_subscribers ADD COLUMN vip_entry_stage INTEGER DEFAULT 1;
ALTER TABLE vip_subscribers ADD COLUMN vip_entry_token VARCHAR(64) UNIQUE;
ALTER TABLE vip_subscribers ADD COLUMN invite_link_sent_at TIMESTAMP;
CREATE INDEX idx_vip_entry_stage ON vip_subscribers(vip_entry_stage);

-- Set NULL for existing active subscribers (skip flow)
UPDATE vip_subscribers SET vip_entry_stage = NULL WHERE status = 'active' AND vip_entry_stage = 1;
```

---

*Planning Complete: 2026-01-27*
