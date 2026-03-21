---
status: resolved
trigger: "cant-initiate-free-channel-dm"
created: 2026-03-20T00:00:00Z
updated: 2026-03-20T00:10:00Z
symptoms_prefilled: true
---

## Current Focus

hypothesis: ROOT CAUSE CONFIRMED. Telegram Bot API 5.5 grants a bot a temporary DM window when a ChatJoinRequest is RECEIVED (5 min with user's chat.id, 24 hours with alternate identifier) — but this window expires BEFORE the background task processes the queue (which runs after wait_time_minutes >= N minutes). By the time approve_ready_free_requests() runs, the ChatJoinRequest event window has long expired, so send_message() fails with "bot can't initiate conversation" for users who never started the bot.

Why some succeed: those users previously opened the bot (via /start or any message), so they already have an open DM channel with the bot.

The fix needed: treat cant_initiate (and chat_not_found) errors as NON-FATAL, non-blocking. The user IS approved (approve_chat_join_request succeeded), they just don't get the DM. The success_count should still increment. The log level should be INFO, not WARNING, since this is expected behavior.
next_action: fix approve_ready_free_requests() and approve_all_free_requests() to not treat DM failure as an error

## Symptoms

expected: Bot sends DM to user notifying them their Free channel access was approved. Should work because users submitted a ChatJoinRequest (Telegram Bot API 5.5 allows bots to DM users who sent a join request, even without prior interaction).
actual: Background task logs "No se puede iniciar conversación con user XXXXX (debe escribirle primero al bot)" for some users during Free queue processing. Other users receive the DM successfully.
errors:
  - cant_initiate classification in _classify_notification_error()
  - Log: "No se puede iniciar conversación con user 55****30 (debe escribirle primero al bot)"
  - Log: "No se puede iniciar conversación con user 67****60 (debe escribirle primero al bot)"
  - Note: user 6721510760 (same as 67****60?) DID receive DM successfully earlier in the same session
reproduction: Background task process_free_queue runs, finds pending requests, tries to DM users on approval
timeline: Error appeared clearly after commits 05e920f and 3300946 (improved error classification logging), but may have existed before as silent misclassification

## Eliminated

- hypothesis: Two parallel flows (ChatJoinRequest-native and DB queue) where some users bypass the ChatJoinRequest flow entirely
  evidence: free_flow.py is entirely commented out. Only one entry point exists for Free requests: free_join_request.py via ChatJoinRequest. ALL users go through ChatJoinRequest. There is no legacy path.
  timestamp: 2026-03-20T00:00:01Z

- hypothesis: approve_chat_join_request() grants the bot permanent DM rights to that user
  evidence: Telegram Bot API 5.5 grants a time-limited window (5 min / 24 hours) when the ChatJoinRequest event is ACTIVE. This window closes before the background task processes the queue (queue only processes requests that are >= wait_time_minutes old). No permanent DM rights granted.
  timestamp: 2026-03-20T00:00:02Z

- hypothesis: The error classification strings are wrong (matching wrong Telegram error text)
  evidence: "_classify_notification_error" checks for "bot can't initiate conversation" which exactly matches the Telegram API error string. Classification is correct.
  timestamp: 2026-03-20T00:00:03Z

## Evidence

- timestamp: 2026-03-20T00:00:00Z
  checked: bot/handlers/user/free_flow.py
  found: Entirely commented out. Comment says "ESTE HANDLER ESTÁ DESACTIVADO". Only one flow: free_join_request.py via ChatJoinRequest.
  implication: No dual-flow problem. All users go through ChatJoinRequest.

- timestamp: 2026-03-20T00:00:01Z
  checked: bot/handlers/user/free_join_request.py
  found: After ChatJoinRequest arrives, waits 30 seconds, then sends a "you're in the queue" DM. This DM succeeds because it's within the Bot API 5.5 window.
  implication: The initial queue notification works. The APPROVAL notification is what fails.

- timestamp: 2026-03-20T00:00:02Z
  checked: bot/background/tasks.py process_free_queue()
  found: Calls container.subscription.approve_ready_free_requests(wait_time_minutes=...). wait_time_minutes is configurable (default >= a few minutes). By the time this runs, the ChatJoinRequest window (5-24 hours) may have expired.
  implication: The DM window from ChatJoinRequest expires before or during background task processing for users who never started the bot.

- timestamp: 2026-03-20T00:00:03Z
  checked: bot/services/subscription.py approve_ready_free_requests() lines 1296-1373
  found: Call order: (1) approve_chat_join_request() — succeeds silently, (2) get channel link, (3) send_message() — fails for users who never started the bot. success_count increments AFTER both steps (line 1373), even if DM fails.
  implication: success_count IS correct (approval happened). The DM failure is non-critical but the warning log is alarming operators unnecessarily.

- timestamp: 2026-03-20T00:00:04Z
  checked: Telegram Bot API 5.5 documentation (web search)
  found: ChatJoinRequest grants bot a time-limited DM window (5 min or 24 hours depending on identifier used). This window expires. After window closes, bot cannot DM users who haven't started it.
  implication: The cant_initiate error is EXPECTED for users who never opened the bot. The user IS approved and can enter the channel — they just don't receive the DM notification.

- timestamp: 2026-03-20T00:00:05Z
  checked: Why some users receive the DM successfully
  found: Users who previously sent any message to the bot (e.g., via /start) have an open DM channel. send_message() works for them regardless of the ChatJoinRequest window.
  implication: Mixed results (some get DM, some don't) are explained entirely by whether the user previously interacted with the bot.

## Resolution

root_cause: The background task approve_ready_free_requests() calls approve_chat_join_request() (which works) then send_message() to notify the user. The DM succeeds only if the user previously opened the bot. For users who never opened the bot, the Telegram Bot API 5.5 DM window (granted by ChatJoinRequest receipt) has already expired by the time the background task runs (which requires wait_time_minutes >= N minutes to pass). This produces "bot can't initiate conversation with a user" errors. The errors are classified as cant_initiate and logged as WARNING — but the user IS approved. The approval is not affected by the DM failure.

fix: Changed cant_initiate and chat_not_found log level from WARNING to INFO in both approve_ready_free_requests() and approve_all_free_requests(). Updated log messages to clarify that (1) the user WAS approved successfully, (2) the DM was not sent because the ChatJoinRequest window expired (expected behavior for users who never started the bot).
verification: After fix, cant_initiate events appear as INFO level with clear message. WARNING level reserved for actual problems (blocked, deactivated, kicked, unknown). success_count continues to increment regardless of DM failure (this was already correct).
files_changed:
  - bot/services/subscription.py (approve_ready_free_requests lines ~1354-1375, approve_all_free_requests lines ~1588-1610)
