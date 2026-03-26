# Phase 8: Interest Notification System - Context

**Gathered:** 2026-01-26
**Status:** Ready for planning

<domain>
## Phase Boundary

User clicks "Me interesa" button → system records interest in UserInterest table + sends private notification to all configured admins with user details and package info. Admins can view interests list (sorted newest first) with filters, and mark as attended (removes from main list).

This phase handles the notification pipeline and interest viewing. Direct messaging to interested users and full user management (ban from system) are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Notification delivery
- **Instant (per click):** Each valid click sends immediate notification to all admins (broadcast)
- **Debounce per user:** One notification per user per package within 5-minute window
- **After debounce expires:** Second click after window generates new notification
- **No rate limiting on floods:** Individual debouncing is sufficient protection

### Notification content
- **Must include:** Username + profile link, Timestamp, Package details (name, type, description)
- **Lucien's voice:** Notifications use character voice (consistent with bot)
- **Inline buttons:** View all interests, Mark attended, Message user, Block contact (spammy users only)

### Deduplication behavior
- **During debounce window:** Silently ignore duplicate clicks (no action, no notification)
- **Scope:** Per package (user interested in Package A and B = counted independently)
- **After window expires:** Treat as new interest, create new notification

### Interest list interface
- **Default sort:** Newest first (most recent at top)
- **Quick filter button:** Toggle to show pending-only
- **Available filters:** Pending only, Attended only, By package type
- **Mark attended action:** Removes interest from main list (archived view available via filters)

### Contact blocking (NEW - not in original scope)
- **"Block contact" button:** Blocks user from using interest/contact features ONLY
- **Not system ban:** User can still use bot, just can't express interest or contact admin
- **Purpose:** For spammy users who click repeatedly without real intent
- **Scope:** This is specific to Phase 8 — full system ban belongs in Phase 9

### Claude's Discretion
- Exact wording of Lucien-voiced notifications
- Pagination limit for interest list (10? 20? 50?)
- Whether archived interests should auto-delete after time period
- Contact blocking implementation details (new column? separate table?)

</decisions>

<specifics>
## Specific Ideas

- Notifications should feel like alerts from Lucien about someone showing interest
- Admin wants to quickly identify spammy users ("se la pasan dando clics") and block them from contact features only
- Interest list is like an inbox — pending items are visible, attended ones are archived
- Filters should be one-click accessible, not buried in submenus

</specifics>

<deferred>
## Deferred Ideas

- **Full user ban (system-wide):** Belongs in Phase 9 (User Management Features)
- **Admin can message interested users:** Could be separate phase or Phase 9
- **Analytics on interests:** Which packages get most interest, trends over time — future phase
- **User can view their own interests:** Not in scope for this phase

</deferred>

---

*Phase: 08-interest-notification-system*
*Context gathered: 2026-01-26*
