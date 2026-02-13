# Phase 21: Daily Rewards & Streaks - Context

**Gathered:** 2026-02-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Users claim daily besitos rewards with streak bonuses that increase for consecutive days. Includes streak tracking for both daily gifts and reactions, streak reset mechanics, and UTC midnight background job for expiration. Shop purchases and reward conditions are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Daily Gift Amounts
- Base amount: **20 besitos** per daily claim
- Claim window: Available any time after UTC midnight
- Streak bonus formula: Claude's discretion (recommend: +2 besitos per streak day, capped)

### Streak Bonus
- Bonus calculation: Claude's discretion
- Maximum cap: Claude's discretion (recommend: cap at 50 bonus besitos)

### Streak Display
- Visual style: Fire emoji with day count (e.g., "🔥 5 days")
- First claim handling: Starts at 1 (first day counts as streak day 1)
- Streak risk warning: Yes - show "claim today" reminder before reset

### Reaction Streak Mechanics
- Tracking method: Claude's discretion (recommend: consecutive days with any reaction)
- Bonus system: Claude's discretion
- UI placement: Claude's discretion

### Claim Button Experience
- Button placement: Main user menu (VIP/Free menu)
- Post-claim state: Shows countdown until next claim available
- Visual feedback: Detailed breakdown showing base + streak bonus

### Claude's Discretion
- Streak bonus formula and cap amount
- Reaction streak tracking logic
- Reaction streak bonus amounts
- Reaction streak UI placement
- Exact countdown format display
- Streak risk warning timing and messaging

</decisions>

<specifics>
## Specific Ideas

- "🔥 5 days" format for streak display
- Detailed breakdown: "20 besitos base + 10 streak bonus = 30 total!"
- Countdown after claim: "Next gift in 14h 32m"
- Streak reminder: "Claim today to keep your 🔥 5 day streak!"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 21-daily-rewards-streaks*
*Context gathered: 2026-02-11*
