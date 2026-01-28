---
phase: 13-vip-ritualized-entry
plan: 03
type: execution
wave: 2
completed: 2026-01-28

duration: 8 minutes

# Tech Stack

tech-stack:
  added:
    - "VIPEntryStates FSM group (3 states)"
    - "VIPEntryService (6 core methods)"
    - "vip_entry_router with stage transition handlers"
  patterns:
    - "Lazy loading for VIPEntryService"
    - "FSM state management with expiry validation"
    - "Sequential stage progression (no skips allowed)"
    - "Service-based business logic separation"

# Dependencies

depends_on:
  - phase: "13-vip-ritualized-entry"
    plan: "01"
    reason: "Database extension (vip_entry_stage, vip_entry_token, invite_link_sent_at)"
  - phase: "13-vip-ritualized-entry"
    plan: "02"
    reason: "VIPEntryFlowMessages provider for ritual messages"

provides:
  - "VIPEntryStates FSM group for 3-stage flow"
  - "VIP entry handler module with stage transitions"
  - "Stage progression validation and expiry checking"
  - "Seamless resumption from current stage after abandonment"

affects:
  - phase: "13-vip-ritualized-entry"
    plan: "04"
    reason: "VIPEntryService integration (already completed in this plan)"
  - phase: "13-vip-ritualized-entry"
    plan: "VERIFICATION"
    reason: "End-to-end testing of complete 3-stage flow"

# Key Files

key-files:
  created:
    - path: "bot/handlers/user/vip_entry.py"
      lines: 236
      description: "VIP entry flow handlers with stage transitions"
    - path: "bot/services/vip_entry.py"
      lines: 331
      description: "VIPEntryService with stage validation and link generation"
  modified:
    - path: "bot/states/user.py"
      lines: 25
      description: "Added VIPEntryStates FSM group"
    - path: "bot/database/enums.py"
      lines: 3
      description: "Added RoleChangeReason.VIP_ENTRY_COMPLETED"
    - path: "bot/services/container.py"
      lines: 35
      description: "Added vip_entry property with lazy loading"
    - path: "bot/handlers/user/start.py"
      lines: -67 +30
      description: "Modified token activation to initiate ritual flow"
    - path: "bot/handlers/vip/menu.py"
      lines: +28
      description: "Added vip_entry_stage check and redirect"
    - path: "bot/handlers/__init__.py"
      lines: +4
      description: "Registered vip_entry_router"

# Decisions Made

decisions:
  - decision: "Implement VIPEntryService in Plan 03 (not Plan 04)"
    rationale: "Plan 03 requires VIPEntryService for stage validation and link generation. Plan 04 was skipped as dependency since it only depends on Plan 01."
    impact: "Combined service and handler implementation in single plan for faster delivery"
  
  - decision: "UserRole changes to VIP only after Stage 3 completion"
    rationale: "Creates psychological commitment through ritual. User invests time in stages 1-2 before receiving access."
    impact: "Increases exclusivity perception and reduces impulsive access"
  
  - decision: "No FSM state cleanup on expiry during stages 1-2"
    rationale: "Flow is cancelled (vip_entry_stage=NULL) but user can restart with new token. No residual state to clean up."
    impact: "Clean expiry handling with minimal database overhead"
  
  - decision: "Seamless resumption without timeout"
    rationale: "No urgency pressure. User can abandon and return whenever they want."
    impact: "Better user experience, no lost progress"

# Deviations

deviations:
  - type: "Rule 3 - Blocking"
    description: "VIPEntryService didn't exist (Plan 04 not executed)"
    found_during: "Task 1 - VIPEntryStates creation"
    fix: "Created VIPEntryService as part of Plan 03 implementation"
    files_modified: "bot/services/vip_entry.py, bot/services/container.py"
    commit: "76a1f3c"

# Implementation Details

stage_flow: |
  Stage 1 (vip_entry_stage=1):
    - User activates token → VIPSubscriber created with vip_entry_stage=1
    - User sees activation confirmation message
    - User clicks "Continuar" (vip_entry:stage_2 callback)
    - Validate: subscription not expired, stage == 1
    - Advance: vip_entry_stage = 2
    - Show Stage 2 message
  
  Stage 2 (vip_entry_stage=2):
    - User sees expectation alignment message
    - User clicks "Estoy listo" (vip_entry:stage_3 callback)
    - Validate: subscription not expired, stage == 2
    - Generate unique vip_entry_token (64 characters)
    - Create 24h invite link
    - Change UserRole: FREE → VIP
    - Log role change with RoleChangeReason.VIP_ENTRY_COMPLETED
    - Advance: vip_entry_stage = 3
    - Show Stage 3 message with link
  
  Stage 3 (vip_entry_stage=3):
    - User sees access delivery message with "Cruzar el umbral" button
    - User clicks URL button → joins VIP channel
    - Flow complete (vip_entry_stage set to NULL by background task or manually)

expiry_handling: |
  Any Stage (1 or 2):
    - Check VIPSubscriber.expiry_date < datetime.utcnow()
    - If expired:
      - Show Lucien's expiry message (VIPEntryFlowMessages.expired_subscription_message())
      - Block stage progression
      - Clear FSM state
      - No retry option (must renew subscription)

resumption_logic: |
  User returns after abandoning:
    - Check vip_entry_stage in database
    - If stage is set (1, 2, or 3):
      - Call show_vip_entry_stage() with current stage
      - No "welcome back" message (seamless resumption)
      - User sees current stage message and continues from there

# Verification

verification:
  must_haves:
    - requirement: "VIPEntryStates FSM group exists with stage_1, stage_2, stage_3 states"
      status: "PASS"
      evidence: "bot/states/user.py contains VIPEntryStates class with 3 states"
    
    - requirement: "/start handler checks vip_entry_stage and routes to vip_entry flow"
      status: "PASS"
      evidence: "bot/handlers/user/start.py _send_welcome_message() checks subscriber.vip_entry_stage"
    
    - requirement: "VIP menu handler checks vip_entry_stage and redirects to entry flow if incomplete"
      status: "PASS"
      evidence: "bot/handlers/vip/menu.py show_vip_menu() redirects to show_vip_entry_stage()"
    
    - requirement: "vip_entry:stage_2 callback advances from stage 1 to stage 2"
      status: "PASS"
      evidence: "handle_vip_entry_stage_transition() validates and advances stage"
    
    - requirement: "vip_entry:stage_3 callback advances from stage 2 to stage 3"
      status: "PASS"
      evidence: "handle_vip_entry_stage_transition() generates token and changes UserRole"
    
    - requirement: "Expiry check blocks continuation if VIPSubscriber expired"
      status: "PASS"
      evidence: "show_vip_entry_stage() checks subscriber.is_expired() before showing stage"
    
    - requirement: "Seamless resumption from current stage if user abandons"
      status: "PASS"
      evidence: "_send_welcome_message() resumes from subscriber.vip_entry_stage"
    
    - requirement: "UserRole changes from FREE to VIP only after Stage 3"
      status: "PASS"
      evidence: "handle_vip_entry_stage_transition() changes role only when target_stage == 3"
    
    - requirement: "VIPEntryFlowMessages accessed via container.message.user.vip_entry"
      status: "PASS"
      evidence: "show_vip_entry_stage() uses container.message.user.vip_entry"

  testing_notes:
    - "Import test: from bot.handlers.user.vip_entry import vip_entry_router - PASSED"
    - "State existence: hasattr(VIPEntryStates, 'stage_1_confirmation') - PASSED"
    - "Handler registration: vip_entry_router registered in dispatcher - PASSED"
    - "Callback patterns: vip_entry:stage_2, vip_entry:stage_3 defined - PASSED"

# Next Steps

next_steps:
  - phase: "13-vip-ritualized-entry"
    plan: "VERIFICATION"
    description: "End-to-end testing of 3-stage ritual flow"
    priority: "HIGH"
    readiness: "Ready - all plans (01-04) complete"
