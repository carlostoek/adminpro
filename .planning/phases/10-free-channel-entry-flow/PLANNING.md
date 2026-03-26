# Phase 10: Free Channel Entry Flow - Planning Summary

**Created:** 2026-01-27
**Status:** ✅ Planning Complete
**Total Plans:** 5
**Estimated Duration:** ~24 minutes

---

## Overview

This phase adapts the existing Free channel entry flow ("Los Kinkys") to use Lucien's voice and adds social media buttons to the initial request message. The flow already works correctly; we're enhancing the user experience.

**Key Changes:**
1. Add social media fields to BotConfig (Instagram, TikTok, X, invite link)
2. Update UserFlowMessages with Lucien's voice + social keyboard generation
3. Update Free flow handler to use new message format
4. Send approval message with channel access button
5. Ensure database columns auto-create on next app start

---

## Plans by Wave

### Wave 1: All 5 Plans (Parallel Execution)

| Plan | Description | Files Modified | Duration |
|------|-------------|----------------|----------|
| **PLAN-01** | Database Extension - Social Media Fields | models.py, config.py | 5 min |
| **PLAN-02** | UserFlowMessages - Lucien Voice + Social Keyboard | user_flows.py | 8 min |
| **PLAN-03** | Free Flow Handler - Social Keyboard Integration | free_flow.py | 4 min |
| **PLAN-04** | Approval Message - Send with Channel Link Button | subscription.py | 5 min |
| **PLAN-05** | Migration & Initialization | engine.py, scripts/ | 2 min |

**Total Wave 1:** ~24 minutes

---

## Plan Dependencies

```
PLAN-01 (Database Extension)
    ↓
PLAN-02 (Message Provider Updates)
    ↓
PLAN-03 (Handler Updates) ────────→ PLAN-04 (Approval Message)
    ↓
PLAN-05 (Migration/Initialization)
```

**Execution Order:**
1. PLAN-01 first (adds database fields)
2. PLAN-02 next (depends on PLAN-01 for ConfigService getters)
3. PLAN-03 and PLAN-04 can run in parallel (both depend on PLAN-02)
4. PLAN-05 last (optional setup script, documentation)

**Autonomous:** All plans are autonomous (can execute without user intervention)

---

## Success Criteria (from ROADMAP.md)

### Phase 10 Success Criteria:

1. ✅ Request message uses Lucien's voice explaining wait time (without specific duration)
   - **Plan:** PLAN-02 (free_request_success() with Lucien header)
   - **Verification:** Message contains "🎩 <b>Lucien:</b>" and NO "5 minutos" mentioned

2. ✅ Message includes creator's social media with clickable buttons (IG → TikTok → X)
   - **Plan:** PLAN-02 (_social_media_keyboard() helper)
   - **Verification:** 3 buttons in fixed order, URLs clickable

3. ✅ Message suggests following social media (prominent first position)
   - **Plan:** PLAN-02 (social CTA in body, keyboard below)
   - **Verification:** "sígueme en" appears before wait time explanation

4. ✅ Approval message includes direct channel access button
   - **Plan:** PLAN-04 (approve_ready_free_requests() extension)
   - **Verification:** "🚀 Acceder al canal" button with channel URL

5. ✅ Automatic approval after configured time (5 min - no changes needed)
   - **Plan:** N/A (existing behavior unchanged)
   - **Verification:** Background task processes queue every 5 minutes

6. ❌ VIP welcome message (NOT in this phase - VIP is separate "Diván de Diana")
   - **Deferred:** Future phase
   - **Note:** This phase is ONLY for Free channel "Los Kinkys"

---

## Implementation Decisions (from 10-CONTEXT.md)

### 1. Request Message Content
- **Voice:** Lucien format ("🎩 <b>Lucien:</b>")
- **Wait time:** NO specific time mentioned (e.g., NOT "5 minutes")
- **Channel name:** "Los Kinkys" (exact)
- **No garden metaphor** (that was for VIP/Free menus - different context)

### 2. Social Media Links
- **Storage:** BotConfig fields (social_instagram, social_tiktok, social_x)
- **Display:** Fixed order (Instagram → TikTok → X)
- **Format:** Emoji + handle (e.g., "📸 @diana_handle")
- **Clickable:** URLs embedded in button links

### 3. Approval Experience
- **Notification:** Send NEW message (don't edit original)
- **Content:** Brief + action-oriented
- **Button:** "🚀 Acceder al canal"
- **Link source:** Stored BotConfig.free_channel_invite_link (fallback to public URL)

### 4. Wait Time Behavior
- **No changes:** Existing wait time logic is correct
- **Duration:** Configurable via BotConfig.wait_time_minutes
- **Cancellation:** No cancel option (processes automatically)
- **During wait:** Silent - no updates until approval

---

## Files Modified Summary

### Database Layer (PLAN-01)
- `bot/database/models.py` - Add 4 fields to BotConfig
- `bot/services/config.py` - Add 4 getters + 4 setters + 1 convenience method

### Message Provider (PLAN-02)
- `bot/services/message/user_flows.py` - Update 3 methods, add 2 new methods

### Handlers (PLAN-03)
- `bot/handlers/user/free_flow.py` - Update 1 handler (unpack tuple, apply keyboard)

### Services (PLAN-04)
- `bot/services/subscription.py` - Extend 1 method (send approval message)

### Migration/Setup (PLAN-05)
- `bot/database/engine.py` - Verify auto-creation (no changes expected)
- `scripts/init_social_media.py` - NEW FILE (optional setup script)
- `README.md` - Add setup instructions

**Total Files:** 7 existing files modified + 1 new file created

---

## Voice Guidelines (from docs/guia-estilo.md)

### Lucien's Personality
- **Mayordomo sofisticado** (sophisticated butler)
- **Observador perceptivo** (perceptive observer)
- **Elegante pero accesible** (elegant but accessible)
- **Misterioso pero servicial** (mysterious but helpful)
- **Leal a Diana** (loyal to Diana)

### Communication Characteristics
- Lenguaje **refinado pero natural** (refined but natural)
- **Pausas dramáticas** con puntos suspensivos (...)
- **Observaciones perspicaces** sobre el usuario
- **Cierto misterio** en explicaciones
- **Nunca es directo** (never direct - always suggests/insinuates)
- Siempre **"usted"**, nunca tuteo

### Required Formatting
```python
# Header (always)
🎩 <b>Lucien:</b>

# Body (italic for narrative voice)
<i>Ah, un nuevo visitante...</i>

# References to Diana
"Diana se complace..."
"Lo cual, debo admitir, no me sorprende..."
```

### Terminology for This Phase
- "Los Kinkys" (channel name - exact)
- "Visitante" (not "usuario")
- "Solicitud de acceso" (not "cola")
- "Diana" (creator name - use in approval message)

---

## Testing Considerations

### Voice Consistency
- All messages follow `docs/guia-estilo.md`
- "Usted" always used (no tuteo)
- 🎩 emoji present in all Lucien messages
- References to Diana where appropriate

### Functional Testing
- Request creates FreeChannelRequest correctly
- Duplicate request shows elapsed/remaining time
- Social media buttons appear in correct order (IG → TikTok → X)
- Approval message sent after wait time elapses
- Channel link button works (stored link or public URL)

### Edge Cases
- Social media fields None in BotConfig → omit buttons gracefully
- No stored invite link → fallback to public t.me/loskinkys
- User clicks request multiple times → show duplicate message
- User blocks bot during wait → exception handled gracefully

---

## Post-Phase Tasks (Out of Scope)

These were mentioned but explicitly deferred to later phases:

1. **VIP Channel Flow ("Diván de Diana"):** Currently users just enter via token link - no special flow. Future enhancement.
2. **Dynamic Social Media Management:** Full admin UI for managing social links (currently using BotConfig fields is sufficient).
3. **Instant Approval with Social Follow:** Future enhancement where following social media accelerates entry.

---

## Next Steps

1. **Execute Plans:**
   ```bash
   # Run all plans in sequence
   /gsd:execute-phase
   ```

2. **Manual Setup (Post-Deployment):**
   - Get invite link from Free channel settings
   - Run `scripts/init_social_media.py` or update DB manually
   - Test Free entry flow with real user

3. **Verification:**
   - Test request flow → see Lucien message + social buttons
   - Test duplicate request → see time progress
   - Test approval → see channel access button
   - Verify all social media links work

**Ready for Execution:** ✅ Yes - all plans created, dependencies clear, scope bounded

---

## Phase Completion Checklist

- [ ] PLAN-01: Database fields added to BotConfig
- [ ] PLAN-01: ConfigService getters/setters implemented
- [ ] PLAN-02: UserFlowMessages updated with Lucien voice
- [ ] PLAN-02: Social media keyboard generation working
- [ ] PLAN-03: Handler unpacks tuple and applies keyboard
- [ ] PLAN-04: Approval message sent with channel button
- [ ] PLAN-05: Setup script created and documented
- [ ] All voice consistency checks passed
- [ ] All functional tests passed
- [ ] Social media links configured in production
- [ ] README.md updated with setup instructions

**Phase 10 COMPLETE when:** All checklist items ✅ + approval message tested in production
