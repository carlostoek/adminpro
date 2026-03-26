---
phase: 13-vip-ritualized-entry
plan: 04
subsystem: vip-entry
tags: [vip-entry-service, stage-validation, token-generation, invite-link, expiry-cancellation]

# Dependency graph
requires:
  - phase: 13-vip-ritualized-entry
    plan: 01
    provides: vip_entry_stage, vip_entry_token, invite_link_sent_at fields in VIPSubscriber model
provides:
  - VIPEntryService with 6 core methods for ritualized VIP entry flow
  - Stage validation and progression logic (1→2→3→NULL)
  - 64-character unique token generation for Stage 3 links
  - 24-hour invite link creation via SubscriptionService
  - Expiry cancellation integrated in background task
affects:
  - bot/handlers/user/vip_entry.py (Plan 03) - handlers will use VIPEntryService methods
  - bot/background/tasks.py - expire_vip_subscribers now cancels incomplete entry flows

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Service layer separation from handler logic
    - Lazy loading via ServiceContainer
    - Stage progression with validation
    - Token-based one-time invite links
    - Background task integration for expiry cleanup

key-files:
  created:
    - bot/services/vip_entry.py - VIPEntryService with 6 methods
  modified:
    - bot/services/container.py - Added vip_entry property
    - bot/services/subscription.py - Integrated entry cancellation in expire_vip_subscribers()

key-decisions:
  - "13-04-01: VIPEntryService follows existing service pattern - async methods, session injection, no commits"
  - "13-04-02: Stage validation prevents sequential skips - only 1→2, 2→3 allowed"
  - "13-04-03: Token generation uses secrets.token_urlsafe(48) for 64-character unique tokens"
  - "13-04-04: Expiry cancellation only affects incomplete flows (stages 1-2), not completed rituals (NULL)"
  - "13-04-05: Background task integration at SubscriptionService level - VIPEntryService called from expire_vip_subscribers()"

patterns-established:
  - "Service Pattern: VIPEntryService with __init__(session, bot) and subservice composition"
  - "Validation Pattern: advance_stage() checks expiry, stage match, sequential progression"
  - "Token Pattern: generate_entry_token() with uniqueness verification and retry loop"
  - "Cancellation Pattern: cancel_entry_on_expiry() sets stage=NULL and removes from channel"

# Metrics
duration: 7min
completed: 2026-01-27
---

# Phase 13 Plan 04: VIP Entry Service with Link Generation Summary

**VIPEntryService with 6 core methods for ritualized VIP entry flow: stage validation, token generation, 24h invite links, and expiry cancellation**

## Performance

- **Duration:** 7 minutes (442 seconds)
- **Started:** 2026-01-28T03:19:30Z
- **Completed:** 2026-01-28T03:26:52Z
- **Tasks:** 7 (all complete)
- **Files modified:** 3 files created, 2 files modified

## Accomplishments

- Created VIPEntryService with 6 core methods for managing 3-stage VIP entry ritual
- Implemented stage validation with expiry checks and sequential progression enforcement
- Implemented 64-character unique token generation with retry loop (10 attempts)
- Implemented 24-hour invite link creation via SubscriptionService integration
- Implemented expiry cancellation that removes users from channel and cancels incomplete flows
- Integrated VIPEntryService into ServiceContainer with lazy loading
- Integrated entry cancellation in background task expire_vip_subscribers()

## Task Commits

Each task was committed atomically:

1. **Task 1: Create VIPEntryService skeleton** - `4185e95` (feat)
2. **Task 2: Implement stage validation methods** - `393143f` (feat)
3. **Task 3: Implement token generation methods** - `990af28` (feat)
4. **Task 4: Implement invite link creation** - `31d81bc` (feat)
5. **Task 5: Implement expiry cancellation** - `58d00ee` (feat)
6. **Task 6: Add VIPEntryService to ServiceContainer** - `fa2a215` (feat)
7. **Task 7: Integrate entry cancellation in background task** - `6c9d8a1` (feat)

**Total commits:** 7 atomic task commits

## Files Created/Modified

### Created
- `bot/services/vip_entry.py` - VIPEntryService class (330 lines)
  - get_current_stage(): Get user's current VIP entry stage
  - advance_stage(): Validate and advance to next stage
  - generate_entry_token(): Generate unique 64-char token
  - is_entry_token_valid(): Validate entry token
  - create_24h_invite_link(): Create 24-hour invite link
  - cancel_entry_on_expiry(): Cancel flow on subscription expiry
  - _get_vip_channel_id(): Helper to get VIP channel ID

### Modified
- `bot/services/container.py` - Added vip_entry property with lazy loading
  - Added _vip_entry_service instance variable
  - Added @property vip_entry with lazy import
  - Updated get_loaded_services() to include 'vip_entry'

- `bot/services/subscription.py` - Integrated entry cancellation
  - Modified expire_vip_subscribers() to call cancel_entry_on_expiry()
  - Added Phase 13 logic to cancel incomplete flows (stages 1-2)
  - Logs cancellation with stage information

## VIP Entry Service Method Documentation

### Stage Validation Methods

**get_current_stage(user_id: int) -> Optional[int]**
- Returns vip_entry_stage from database (1, 2, 3, or None)
- None = completed ritual or not initiated

**advance_stage(user_id: int, from_stage: int) -> bool**
- Validates subscription not expired
- Validates from_stage matches current stage (race condition prevention)
- Only allows sequential progression (1→2, 2→3)
- Updates vip_entry_stage to next_stage
- Returns bool for success/failure

### Token Generation Methods

**generate_entry_token(user_id: int) -> str**
- Generates 64-character token using secrets.token_urlsafe(48)
- Verifies uniqueness against existing tokens
- Stores in vip_entry_token field
- Retries up to 10 times before raising RuntimeError
- Returns generated token

**is_entry_token_valid(token: str) -> bool**
- Checks token exists in vip_entry_token field
- Verifies user is at stage 3 (token ready)
- Checks subscription not expired
- Returns bool for validity

### Invite Link Creation

**create_24h_invite_link(user_id: int) -> Optional[ChatInviteLink]**
- Gets VIP channel ID from ConfigService
- Calls SubscriptionService.create_invite_link() with expire_hours=24
- Updates invite_link_sent_at timestamp
- Returns ChatInviteLink on success, None on error

### Expiry Cancellation

**cancel_entry_on_expiry(user_id: int) -> None**
- Only cancels if vip_entry_stage in (1, 2) (incomplete flows)
- Sets vip_entry_stage = NULL (cancel flow)
- Removes user from VIP channel via kick_expired_vip_from_channel()
- Logs cancellation event with old stage
- Graceful handling if channel removal fails

## Stage Progression Logic

```
Stage 1 (vip_entry_stage=1):
  - User clicks "Continuar" button
  - Validate: subscription not expired, stage == 1
  - Action: Set vip_entry_stage = 2
  - Return: success=True

Stage 2 (vip_entry_stage=2):
  - User clicks "Estoy listo" button
  - Validate: subscription not expired, stage == 2
  - Action: Generate vip_entry_token, set vip_entry_stage = 3
  - Return: success=True, token generated

Stage 3 (vip_entry_stage=3):
  - User clicks "Cruzar el umbral" (URL button)
  - Action: Set vip_entry_stage = NULL (complete)
  - Return: N/A (link is URL button, not callback)
```

## Expiry Cancellation Behavior

**Trigger:** Background task expire_vip_subscribers() runs every 60 minutes

**Flow for expired subscribers:**
1. Mark subscriber as expired (status='expired')
2. **Phase 13:** If vip_entry_stage in (1, 2):
   - Call cancel_entry_on_expiry(user_id)
   - Set vip_entry_stage = NULL
   - Remove user from VIP channel
   - Log cancellation with old stage
3. Log role change (VIP → FREE)
4. Kick from VIP channel

**Does NOT affect:**
- Subscribers with vip_entry_stage=NULL (completed rituals)
- Subscribers with vip_entry_stage=3 (token generated, not yet used)

## Service Dependencies

**VIPEntryService uses:**
- SubscriptionService: create_invite_link(), kick_expired_vip_from_channel()
- ConfigService: get_vip_channel_id()
- VIPSubscriber model: vip_entry_stage, vip_entry_token, invite_link_sent_at fields

**VIPEntryService is used by:**
- bot/handlers/user/vip_entry.py (Plan 03) - Stage progression handlers
- bot/background/tasks.py - expire_vip_subscribers() cancellation logic

## Decisions Made

- **13-04-01:** VIPEntryService follows existing service pattern - async methods, session injection via __init__, no session.commit() in service (handlers commit)
- **13-04-02:** Stage validation prevents sequential skips - only allows advancement from stage 1 or 2, prevents race conditions with from_stage matching
- **13-04-03:** Token generation uses secrets.token_urlsafe(48) for 64-character tokens with uniqueness verification and retry loop
- **13-04-04:** Expiry cancellation only affects incomplete flows (stages 1-2), does NOT cancel completed rituals (NULL) or token-ready stage (3)
- **13-04-05:** Background task integration at SubscriptionService level - VIPEntryService.cancel_entry_on_expiry() called from expire_vip_subscribers() for each expired subscriber

## Deviations from Plan

None - plan executed exactly as written. All 7 tasks completed without deviations.

## Verification

### Pre-Commit Verification (Passed)
1. ✅ Import test: `from bot.services.vip_entry import VIPEntryService` - no errors
2. ✅ Method existence: All 6 core methods exist and are callable
3. ✅ Service integration: `ServiceContainer().vip_entry` returns VIPEntryService
4. ✅ Background task: expire_vip_subscribers() calls cancel_entry_on_expiry()

### Post-Commit Testing (Passed)
- ✅ VIPEntryService imports successfully
- ✅ All 6 methods accessible: get_current_stage, advance_stage, generate_entry_token, is_entry_token_valid, create_24h_invite_link, cancel_entry_on_expiry
- ✅ ServiceContainer.vip_entry property exists and returns VIPEntryService

## Next Phase Readiness

**Ready for Phase 13 Plan 03 (FSM States and Handlers):**
- VIPEntryService complete with all 6 methods implemented
- ServiceContainer integration ready for handler access
- Stage validation logic ready for handler integration
- Token generation ready for Stage 3 link creation
- Expiry cancellation integrated in background task
- No blockers or concerns

**Handler integration pattern (Plan 03):**
```python
# In vip_entry.py handlers
service = container.vip_entry

# Validate stage
current = await service.get_current_stage(user_id)

# Advance stage
success = await service.advance_stage(user_id, from_stage=1)

# Generate link (Stage 3)
invite_link = await service.create_24h_invite_link(user_id)
```

---
*Phase: 13-vip-ritualized-entry*
*Plan: 04*
*Completed: 2026-01-27*
