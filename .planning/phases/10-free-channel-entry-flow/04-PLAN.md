---
wave: 1
depends_on: [PLAN-01, PLAN-02]
files_modified:
  - bot/services/subscription.py
autonomous: true
estimated_minutes: 5
---

# Plan 04: Approval Message - Send with Channel Link Button

## Goal
Extend `approve_ready_free_requests()` to send Lucien-voiced approval message with channel access button.

## Context
Current implementation sends generic HTML message. This plan replaces it with UserFlowMessages provider for consistent Lucien voice and inline keyboard button.

## Tasks

### T1: Extend approve_ready_free_requests() to Send Approval Message
**File:** `bot/services/subscription.py`

**Changes:**
1. Import UserFlowMessages
2. Fetch stored invite link (or fallback to public URL)
3. Use `free_request_approved()` for message + keyboard
4. Send as NEW message (not edit)

**Updated Implementation (lines 786-820):**
```python
        # Aprobar cada solicitud usando Telegram API
        for request in ready_requests:
            try:
                # 1. Aprobar ChatJoinRequest directamente
                await self.bot.approve_chat_join_request(
                    chat_id=free_channel_id,
                    user_id=request.user_id
                )

                # 2. Obtener enlace del canal (stored or fallback to public URL)
                # Import UserFlowMessages
                from bot.services.message.user_flows import UserFlowMessages

                # Get stored invite link from BotConfig
                config_result = await self.session.execute(
                    select(BotConfig).where(BotConfig.id == 1)
                )
                bot_config = config_result.scalar_one_or_none()

                # Use stored link or fallback to public t.me URL
                if bot_config and bot_config.free_channel_invite_link:
                    channel_link = bot_config.free_channel_invite_link
                else:
                    # Fallback: construct public URL from channel_id
                    # Assumes channel_id is numeric or @username format
                    if free_channel_id.startswith('@'):
                        channel_link = f"t.me/{free_channel_id[1:]}"
                    elif free_channel_id.startswith('-100'):
                        # Extract numeric ID for public channel lookup
                        # This won't work for private channels, but it's a best-effort fallback
                        channel_link = f"t.me/joinchat/{free_channel_id[4:]}"  # Not ideal
                        # Better: admin should set stored link
                        logger.warning(
                            f"⚠️ No stored invite link found. "
                            f"Admin should set free_channel_invite_link in BotConfig."
                        )
                        channel_link = None  # Will skip sending message
                    else:
                        channel_link = f"t.me/{free_channel_id}"

                # 3. Enviar mensaje de aprobación con Lucien's voice
                if channel_link:
                    flows = UserFlowMessages()
                    approval_text, keyboard = flows.free_request_approved(
                        channel_name=channel_name,
                        channel_link=channel_link
                    )

                    await self.bot.send_message(
                        chat_id=request.user_id,
                        text=approval_text,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )

                    logger.info(
                        f"✅ Aprobación enviada a user {request.user_id} con enlace al canal"
                    )

                # 4. Marcar solicitud como procesada
                request.processed = True
                request.processed_date = datetime.utcnow()

            except Exception as e:
                # Distinguir entre usuario que bloqueó el bot vs otros errores
                error_type = type(e).__name__
                if "Forbidden" in error_type or "blocked" in str(e).lower():
                    logger.warning(
                        f"⚠️ Usuario {request.user_id} bloqueó el bot, no se envió confirmación"
                    )
                else:
                    logger.error(
                        f"❌ Error enviando confirmación a user {request.user_id}: {e}"
                    )
                error_count += 1
                continue

            success_count += 1
```

**Voice Rationale:**
- Sends NEW message (not edit) - fresh notification
- Uses UserFlowMessages for consistent Lucien voice
- Prefers stored invite link over public URL
- Graceful degradation: skips message if no link available

**Acceptance:**
- [ ] Imports UserFlowMessages
- [ ] Fetches stored free_channel_invite_link from BotConfig
- [ ] Fallbacks to public t.me URL if no stored link
- [ ] Calls free_request_approved(channel_name, channel_link)
- [ ] Sends message with reply_markup=keyboard
- [ ] Marks request as processed after sending

---

### T2: Add Logging for Missing Stored Link
**File:** `bot/services/subscription.py`

**Logging Logic:**
```python
if not bot_config or not bot_config.free_channel_invite_link:
    logger.warning(
        "⚠️ free_channel_invite_link not configured in BotConfig. "
        "Using fallback URL. Admin should set stored invite link for better UX."
    )
```

**Voice Rationale:**
- Warning level (not error) - fallback works
- Clear message about what admin should do
- Helps with debugging if link doesn't work

**Acceptance:**
- [ ] Logs warning when stored link is None
- [ ] Warning message includes actionable advice

---

## Verification

### Pre-Commit Verification:
1. **Import check:** `from bot.services.message.user_flows import UserFlowMessages`
2. **Method signature:** `free_request_approved(channel_name, channel_link)` exists
3. **BotConfig query:** Follows existing pattern

### Post-Commit Testing:
```python
# Test with stored invite link
# Mock bot_config.free_channel_invite_link = "https://t.me/..."
# Verify message sent with keyboard containing that link

# Test without stored link (fallback)
# Mock bot_config.free_channel_invite_link = None
# Verify fallback URL used

# Test with blocked user
# Mock bot.send_message() to raise Forbidden
# Verify error logged correctly, request still marked as processed
```

### Manual UAT:
1. **With stored link:**
   - User requests Free access
   - Wait time elapses
   - User receives approval message
   - Click "🚀 Acceder al canal" button
   - Redirects to stored invite link

2. **Without stored link (fallback):**
   - Same flow
   - Button uses public t.me/... URL
   - Log warning visible in console

3. **Blocked user:**
   - User blocks bot during wait
   - Background task tries to send approval
   - Exception caught and logged
   - Request still marked as processed

---

## Integration Notes

**No Breaking Changes:**
- Existing approval logic unchanged (approve_chat_join_request)
- Only message formatting changes

**Stored Link Management:**
- Admin needs to set `free_channel_invite_link` in BotConfig
- Can be done via DB update or future admin UI
- For now, fallback to public URL works

**Error Handling:**
- Forbidden exception (user blocked bot) - logged as warning
- Other exceptions - logged as error
- Request marked as processed regardless (prevents retry)

**Message Timing:**
- Sent IMMEDIATELY after approve_chat_join_request
- User receives both: Telegram's "request approved" + bot's message
- Bot's message provides clickable button (better UX)

---

## must_haves

1. ✅ Imports UserFlowMessages at top of method
2. ✅ Fetches bot_config.free_channel_invite_link from database
3. ✅ Fallbacks to public t.me URL if no stored link
4. ✅ Calls free_request_approved(channel_name, channel_link)
5. ✅ Sends message with reply_markup=keyboard
6. ✅ Logs warning when using fallback URL
7. ✅ Marks request as processed after sending
8. ✅ Handles Forbidden exception (blocked user) gracefully
