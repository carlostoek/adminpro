---
phase: 21
name: Daily Rewards & Streaks
description: Users can claim daily rewards with streak bonuses. 7 requirements (STREAK-01 through STREAK-07).
status: Ready for Execution
---

# Phase 21: Daily Rewards & Streaks

## Overview
Implement daily gift system with streak tracking. Users claim besitos daily with increasing bonuses for consecutive days. Includes separate reaction streak tracking and UTC midnight background job for streak expiration.

## Phase Goal
Users can claim daily rewards with streak bonuses. 7 requirements (STREAK-01 through STREAK-07).

## Requirements
- STREAK-01: User can claim daily gift once per 24h period
- STREAK-02: User earns besitos for daily gift (base + streak bonus)
- STREAK-03: Streak increases with consecutive daily claims
- STREAK-04: Streak resets to 0 if missed (no grace period for v2.0)
- STREAK-05: Streak displayed in user menu
- STREAK-06: Reaction streak tracked separately (consecutive days with reactions)
- STREAK-07: Background job handles streak expiration at UTC midnight

## Wave Structure

### Wave 1: Core Infrastructure
**Goal:** Database models and service layer
**Parallel Execution:** Yes

| Plan | File | Description | Dependencies |
|------|------|-------------|--------------|
| 21-01 | 21-01-PLAN.md | Database Model - UserStreak | None |
| 21-02 | 21-02-PLAN.md | StreakService - Core Logic | 21-01 |
| 21-03 | 21-03-PLAN.md | Reaction Streak Tracking | 21-02 |

### Wave 2: User Interface
**Goal:** Handlers and menu integration
**Parallel Execution:** Yes (after Wave 1)

| Plan | File | Description | Dependencies |
|------|------|-------------|--------------|
| 21-04 | 21-04-PLAN.md | Daily Gift Handler | 21-02 |
| 21-05 | 21-05-PLAN.md | Streak Display in User Menu | 21-02, 21-04 |

### Wave 3: Background & Testing
**Goal:** Background job and comprehensive tests
**Parallel Execution:** Yes (after Wave 1)

| Plan | File | Description | Dependencies |
|------|------|-------------|--------------|
| 21-06 | 21-06-PLAN.md | UTC Midnight Background Job | 21-02, 21-03 |
| 21-07 | 21-07-PLAN.md | Streak System Tests | All above |

## Key Implementation Decisions

### Daily Gift Amounts
- Base amount: **20 besitos** per daily claim
- Claim window: Available any time after UTC midnight
- Streak bonus formula: +2 besitos per streak day, capped at 50 bonus

### Streak Bonus
- Bonus calculation: +2 besitos per day of current streak
- Maximum cap: 50 bonus besitos (reached at 25+ day streak)

### Streak Display
- Visual style: Fire emoji with day count (e.g., "🔥 5 days")
- First claim handling: Starts at 1 (first day counts as streak day 1)
- Streak risk warning: Yes - show "claim today" reminder before reset

### Reaction Streak Mechanics
- Tracking method: Consecutive days with any reaction
- Bonus system: Tracked separately, rewards in future phase
- UI placement: Visible in profile/stats

### Claim Button Experience
- Button placement: Main user menu (VIP/Free menu)
- Post-claim state: Shows countdown until next claim available
- Visual feedback: Detailed breakdown showing base + streak bonus

## Voice Guidelines

All system messages use **Lucien's voice** (🎩):
- Formal, mayordomo, elegante
- Tercera persona/usted ("su/su solicitud/le")
- Emoji 🎩 como firma

Streak display uses fire emoji (🔥) as specified, not as Lucien's voice.

## Files to Modify

### Database
- `bot/database/models.py` - Add UserStreak model
- `bot/database/enums.py` - Add StreakType enum

### Services
- `bot/services/streak.py` - NEW: StreakService
- `bot/services/container.py` - Add streak service property
- `bot/services/reaction.py` - Integrate streak tracking

### Handlers
- `bot/handlers/user/streak.py` - NEW: Daily gift handlers
- `bot/handlers/user/menu.py` - Update with streak display
- `bot/handlers/user/__init__.py` - Register streak handlers

### States
- `bot/states/user.py` - Add StreakStates

### Messages
- `bot/services/message/user_menu.py` - Add streak display

### Background
- `bot/background/tasks.py` - Add streak expiration job

### Tests
- `tests/unit/services/test_streak.py` - NEW
- `tests/integration/test_daily_gift.py` - NEW

## Success Criteria

1. User sees "Claim Daily Gift" button when available
2. User receives base besitos + streak bonus upon claiming
3. Streak counter increases for consecutive daily claims
4. Streak resets to 0 if user misses a day
5. Current streak visible in user menu
6. Reaction streak tracks separately
7. Background job runs at UTC midnight for streak expiration

## Dependencies
- Phase 19 (Economy Foundation): WalletService for besitos
- Phase 20 (Reaction System): ReactionService integration point

## Risk Mitigation
- UTC date handling tested across DST transitions
- Atomic operations prevent race conditions on claim
- Background job idempotent (safe to run multiple times)
