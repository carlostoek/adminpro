# Phase 2: Template Organization & Admin Migration - Context

**Gathered:** 2026-01-23
**Status:** Ready for planning

## Phase Boundary

Migrate all admin handlers (/admin, VIP, Free) from hardcoded strings to centralized LucienVoiceService with template composition, keyboard integration, and message variations. This phase delivers AdminMessages provider and refactored admin handlers — zero new features, only architectural improvement.

## Implementation Decisions

### Message method structure
- **Granularity:** One method per UI screen/state (e.g., `get_vip_menu()`, `token_generated()`, `setup_channel_prompt()`)
- **Organization:** Grouped by feature (VIPMessages, FreeMessages, ConfigMessages classes) matching handler structure
- **Return format:** Tuple `(text, keyboard)` from each method (I'll decide based on best practices)
- **Conditional states:** Technical decision left to implementation (state flags vs internal checks vs separate methods)
- **Variation scope:** Only key messages get variations — greetings and confirmations; errors and informational messages stay static

### Variation strategy
- **Number of variations:** 2 variations per key message (simple, maintainable)
- **Selection method:** Equal random selection (50/50 chance for each variation)
- **Message types with variations:** Menu greetings and confirmations only
- **Variation storage:** To be determined by researcher/planner (lists, dicts, or helper functions)

### Keyboard integration
- **Keyboard building:** Technical decision — use whatever works best for codebase architecture (built-in to message methods or separate factories)
- **Callback format:** Technical decision — maintain consistency with existing pattern or change if beneficial
- **Dynamic keyboards:** Yes, keyboard options vary by context (e.g., channel configured vs not configured)
- **Context-aware buttons:** Show/hide actions based on state, not just disable them

### Conditional content handling
- **State passing format:** Technical decision — boolean flags, string enums, or context objects (I'll choose most maintainable approach)
- **Primary condition:** User role (Free/VIP) is the key differentiator for message content
- **Role differentiation:** Different message content per role — VIP sees channel links, Free sees wait time, Admin sees setup options
- **Error handling:** Error messages show what's missing (e.g., "Channel not configured — please setup first")

### Claude's Discretion
- Exact return format for (text, keyboard) tuples
- How conditional states are checked (flags, internal checks, or separate methods)
- Callback data format for keyboard buttons
- State passing mechanism (boolean flags, string enums, or context objects)
- Where keyboard building logic lives (message methods or separate factories)
- Variation storage mechanism (lists, dicts, helper functions)
- Which specific messages get "key message" variation status beyond greetings/confirmations
- How to handle unavailable features beyond error messages (graceful degradation vs prominent errors)

## Specific Ideas

- Admin messages should sound like Lucien the mayordomo — elegant, mysterious, using "usted" never "tú"
- VIP menu should feel exclusive and sophisticated when configured
- Error messages should guide admin toward solution (e.g., "Diana requires the VIP channel to be configured first")
- Success confirmations for admin actions (token generated, channel configured, etc.)

## Deferred Ideas

None — discussion stayed within phase scope.

---

*Phase: 02-template-organization-admin-migration*
*Context gathered: 2026-01-23*
