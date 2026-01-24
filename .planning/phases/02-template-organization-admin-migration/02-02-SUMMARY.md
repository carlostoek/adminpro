---
phase: 02-template-organization-admin-migration
plan: 02
subsystem: message-service
tags: [admin-free, message-provider, voice-consistency, template-migration]
requires: [01-03]
provides:
  - AdminFreeMessages provider with Free-specific voice
  - Migrated Free handlers using centralized message service
  - Voice-consistent "vestíbulo" terminology
affects: [02-03]
tech-stack:
  added: []
  patterns:
    - Weighted greeting variations (50%, 30%, 20%)
    - Format_duration_minutes integration
    - Conditional keyboards based on configuration state
key-files:
  created:
    - bot/services/message/admin_free.py
  modified:
    - bot/handlers/admin/free.py
decisions:
  - id: free-terminology
    choice: "Use 'vestíbulo' (vestibule) for Free channel, 'tiempo de contemplación' for wait time"
    rationale: "Maintains narrative consistency with Lucien's voice - Free channel is entry to Diana's exclusive realm"
  - id: validation-messages
    choice: "Keep technical validation errors in handlers (forward validation, channel type check)"
    rationale: "These are technical constraints, not UI messaging - separating concerns appropriately"
  - id: error-message-reasons
    choice: "invalid_wait_time_input() takes reason parameter ('not_number', 'too_low', 'invalid')"
    rationale: "Allows provider to customize error message while handler controls validation logic"
metrics:
  duration: "238 seconds"
  completed: "2026-01-23"
---

# Phase 02 Plan 02: Admin Free Messages Migration Summary

**One-liner:** AdminFreeMessages provider with "vestíbulo" voice and complete Free handler migration using format_duration_minutes

## What Was Built

### AdminFreeMessages Provider (308 lines)
Created comprehensive message provider for Free channel management with Lucien's voice:

**Core Methods (7):**
1. `free_menu()` - Main menu with weighted greeting variations (50%, 30%, 20%)
2. `setup_channel_prompt()` - Channel configuration instructions
3. `channel_configured_success()` - Success confirmation with Diana reference
4. `wait_time_setup_prompt()` - Wait time input instructions
5. `wait_time_updated()` - Success message after wait time change
6. `invalid_wait_time_input(reason)` - Error messages for validation failures
7. `config_menu()` - Configuration submenu

**Private Keyboard Factories (3):**
- `_free_configured_keyboard()` - Configured state options
- `_free_unconfigured_keyboard()` - Unconfigured state prompt
- `_free_config_submenu_keyboard()` - Configuration options

**Voice Characteristics Implemented:**
- Free channel = "vestíbulo" (vestibule/entry to exclusive realm)
- Wait time = "tiempo de contemplación" (contemplation time)
- Queue = "lista de espera" (waiting list)
- Diana references for authority ("Diana observa que...")
- 🎩 emoji in all headers
- "usted" form throughout (never "tú")

**Technical Integration:**
- Uses `format_duration_minutes()` from utils/formatters
- Returns (text, keyboard) tuples for complete UI
- Stateless design (no session/bot instance variables)
- Weighted variations using `_choose_variant()` from BaseMessageProvider

### Handler Migration
Migrated 6 handlers in bot/handlers/admin/free.py:

**Removed:**
- `free_menu_keyboard()` function (51 lines) → Now in provider
- All hardcoded HTML message strings (91 lines total removed)

**Migrated Handlers:**
1. `callback_free_menu()` → Uses `free_menu()` with conditional parameters
2. `callback_free_setup()` → Uses `setup_channel_prompt()`
3. `process_free_channel_forward()` → Uses `channel_configured_success()`
4. `callback_set_wait_time()` → Uses `wait_time_setup_prompt()`
5. `process_wait_time_input()` → Uses `invalid_wait_time_input()` and `wait_time_updated()`
6. `callback_free_config()` → Uses `config_menu()`

**Preserved:**
- Technical validation logic (forward message check, channel type validation)
- FSM state transitions
- Error handling for "message is not modified"
- Logging statements

**Statistics:**
- Message service calls: 9
- Lines removed: 91 (hardcoded strings + keyboard function)
- Lines added: 43 (service integration)
- Net reduction: 48 lines (cleaner, more maintainable)

## Key Implementation Details

### Weighted Greeting Variations
```python
greetings = [
    ("El vestíbulo de Diana permanece accesible, custodio...", 0.5),
    ("La antesala del círculo exclusivo aguarda su calibración...", 0.3),
    ("Bienvenido a la zona de preparación...", 0.2),
]
```
Common variation (50%) appears most frequently, creating familiarity while preventing robotic repetition.

### Format Integration
```python
wait_time_str = format_duration_minutes(wait_time_minutes)
# Returns: "5 minutos", "1 hora, 5 minutos", "1 día", etc.
```
Consistent duration formatting across all messages using existing utility.

### Conditional Content
```python
if is_configured:
    body = f"✅ Canal configurado: <b>{channel_name}</b>..."
    keyboard = self._free_configured_keyboard()
else:
    body = "⚠️ El vestíbulo aún no ha sido calibrado..."
    keyboard = self._free_unconfigured_keyboard()
```
Single method adapts to configuration state with appropriate content and options.

### Error Message Customization
```python
if reason == "not_number":
    body = "Hmm... parece que ese no es un número válido..."
elif reason == "too_low":
    body = "El tiempo debe ser al menos 1 minuto..."
```
Provider controls voice/phrasing, handler controls validation logic - clean separation.

## Voice Patterns Implemented

### "Vestíbulo" Terminology
- Positions Free channel as entry to exclusive realm
- Implies preparation/contemplation before VIP access
- Maintains mystery and elegance (not just "free tier")

### "Tiempo de contemplación"
- Poetic phrasing for wait time
- Suggests intentional pause, not arbitrary delay
- Aligns with Diana's mystique (visitors must wait thoughtfully)

### Diana References
- "Diana observa que los solicitantes ya pueden pedir su entrada..."
- "Diana prefiere que los visitantes tengan un período mínimo..."
- Establishes authority and narrative consistency

### Lucien's Helpful Corrections
- "Hmm... parece que ese no es un número válido."
- Gentle, sophisticated error handling (not harsh/technical)
- Maintains character even in validation failures

## Deviations from Plan

None - Plan executed exactly as specified.

## Testing Notes

**Manual Verification:**
- AdminFreeMessages class created: ✅ (308 lines, exceeds 180 min)
- All methods return (text, keyboard) tuples: ✅
- Weighted variations implemented: ✅ (50%, 30%, 20%)
- Format_duration_minutes integration: ✅
- Voice consistency: ✅ ("vestíbulo", "tiempo de contemplación", "usted")
- Handler migration: ✅ (9 service calls, zero hardcoded UI strings)

**Integration Validation:**
```bash
# Verify provider pattern
grep "class AdminFreeMessages(BaseMessageProvider)" admin_free.py
# Output: Line 15

# Verify service integration
grep -c "container.message.admin.free" free.py
# Output: 9

# Verify no hardcoded keyboards
grep "create_inline_keyboard" free.py
# Output: (none in handler code, removed from import)
```

## Next Steps

**Immediate (02-03):**
- Create AdminMainMessages provider for main admin menu
- Migrate main.py handlers (admin menu, config display)
- Complete Phase 2 admin handler migration

**Future (Phase 3):**
- User message providers (UserVIPMessages, UserFreeMessages)
- Welcome messages and token redemption flows
- Complete voice consistency across all bot flows

**Voice Consistency Validation:**
- After Phase 2 complete, audit all admin messages for voice patterns
- Verify no "tú" usage, consistent emoji (🎩), Diana references
- Profile message generation performance (<5ms target)

## Files Modified

```
bot/services/message/admin_free.py (NEW)
  - 308 lines
  - 7 public methods
  - 3 keyboard factories
  - Weighted variations with _choose_variant()

bot/handlers/admin/free.py (MODIFIED)
  - Removed: free_menu_keyboard() function
  - Removed: All hardcoded HTML strings
  - Added: 9 container.message.admin.free calls
  - Net: -48 lines (more maintainable)
```

## Commits

1. **feat(02-02): create AdminFreeMessages provider with Free-specific voice** (9f312e9)
   - AdminFreeMessages class with 7 message methods
   - Weighted greeting variations
   - "Vestíbulo" and "tiempo de contemplación" terminology
   - Stateless design with format_duration_minutes integration

2. **feat(02-02): migrate Free handlers to use AdminFreeMessages provider** (9318a39)
   - Removed free_menu_keyboard() function
   - Migrated 6 handlers to centralized service
   - Zero hardcoded UI strings (only validation errors remain)
   - 9 message service integration points

## Performance

- **Execution time:** 238 seconds (~4 minutes)
- **Lines created:** 308 (admin_free.py)
- **Lines removed:** 91 (free.py cleanup)
- **Net improvement:** -48 lines (11% reduction with better separation)
- **Service calls:** 9 (complete coverage of Free UI flow)

## Lessons Learned

1. **Validation separation works well** - Technical validation errors stay in handlers (forward check, type check), UI messaging in provider. Clean separation of concerns.

2. **Format integration is seamless** - `format_duration_minutes()` provides consistent, natural-language duration display across all messages.

3. **Weighted variations add personality** - 50/30/20 split creates familiar-but-not-robotic experience without complexity.

4. **Conditional keyboards simplify handlers** - Provider handling configuration-state keyboards reduces handler complexity significantly.

5. **Removal of keyboard functions** - Previously 51-line `free_menu_keyboard()` now handled entirely in provider, handlers are cleaner.

---

**Phase 2 Progress:** 2/3 plans complete (AdminVIP ✅, AdminFree ✅, AdminMain pending)
**Next:** 02-03 - AdminMainMessages provider and main.py migration
