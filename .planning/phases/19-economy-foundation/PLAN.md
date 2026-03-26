# Phase 19: Economy Foundation

## Overview

Establish the virtual currency ("besitos") economy system with wallet management, transaction history, and level progression. This is the foundational phase for all gamification features.

**Phase Goal:** Users have a virtual currency wallet with transaction history and level progression

**Requirements:** ECON-01 through ECON-08 (8 requirements)

**Dependencies:** None (builds on v1.2 infrastructure)

---

## Success Criteria

1. User can view current besitos balance in their personal menu
2. User can view paginated transaction history showing earned/spent amounts
3. System rejects any transaction that would result in negative balance
4. Concurrent transactions complete without race conditions
5. Every besito change is recorded with reason, amount, and timestamp
6. Admin can credit or debit besitos to any user with reason note
7. User level displays correctly based on total lifetime besitos earned
8. Admin can configure level progression formula

---

## Architecture Decisions

### Atomic Transaction Pattern
- Use `UPDATE SET col = col + delta` pattern for all besito operations
- Never read-modify-write; always atomic operations at database level
- Prevents race conditions without explicit locking

### Level Calculation
- Levels based on `total_earned` (lifetime besitos), NOT current balance
- Formula stored in BotConfig as configurable expression
- Default: `level = floor(sqrt(total_earned / 100)) + 1`

### Transaction Types
- `EARN_REACTION` - Besitos earned from reacting to content
- `EARN_DAILY` - Daily gift claim
- `EARN_STREAK` - Streak bonus
- `EARN_REWARD` - Achievement reward
- `EARN_ADMIN` - Manual credit by admin
- `SPEND_SHOP` - Purchase in shop
- `SPEND_ADMIN` - Manual debit by admin

---

## Files to Modify

### Database Models
- `bot/database/models.py` - Add UserGamificationProfile and Transaction models
- `bot/database/enums.py` - Add TransactionType enum

### Services
- `bot/services/wallet.py` - New: WalletService (core economy logic)
- `bot/services/container.py` - Add wallet service property
- `bot/services/__init__.py` - Export WalletService

### Configuration
- `bot/services/config.py` - Add level formula and economy config getters/setters

### Alembic Migration
- `alembic/versions/` - New migration for gamification tables

---

## Waves

| Wave | Tasks | Parallel | Description |
|------|-------|----------|-------------|
| 1 | 3 | No | Database foundation (enums, models, migration) |
| 2 | 4 | No | WalletService core implementation |
| 3 | 3 | No | Admin operations and config integration |
| 4 | 3 | No | Integration and testing |

---

## Must-Haves for Goal Verification

These must be true for the phase to be complete:

1. **User balance visibility** (ECON-01)
   - `WalletService.get_balance(user_id)` returns current besitos
   - Balance displays in user menu via handler integration

2. **Transaction history** (ECON-02)
   - `WalletService.get_transaction_history(user_id, page, per_page)` returns paginated results
   - Each record has: amount, type, reason, timestamp

3. **Negative balance prevention** (ECON-03)
   - `WalletService.spend_besitos()` validates sufficient balance before atomic operation
   - Returns `(False, "insufficient_funds", None)` if would go negative

4. **Atomic transactions** (ECON-04)
   - All balance changes use `UPDATE SET balance = balance + delta`
   - No read-modify-write patterns in codebase

5. **Audit trail** (ECON-05)
   - Every balance change creates Transaction record
   - Transaction has: user_id, amount, type, reason, created_at

6. **Admin adjustment** (ECON-06)
   - `WalletService.admin_credit(user_id, amount, reason, admin_id)`
   - `WalletService.admin_debit(user_id, amount, reason, admin_id)`
   - Both create appropriate Transaction records

7. **Level display** (ECON-07)
   - `WalletService.get_user_level(user_id)` returns current level
   - Level calculated from total_earned using configured formula

8. **Configurable formula** (ECON-08)
   - `ConfigService.get_level_formula()` returns current formula string
   - `ConfigService.set_level_formula(formula)` validates and stores
   - Formula supports: total_earned, sqrt, floor, +, -, *, /, (, )

---

## Verification Checklist

- [ ] All 8 ECON requirements satisfied
- [ ] WalletService has 100% type hint coverage
- [ ] All methods have Google Style docstrings
- [ ] Return tuples follow `(bool, str, Optional[T])` pattern
- [ ] Atomic operations prevent race conditions (verified by test)
- [ ] Transaction audit trail complete for all operations
- [ ] Level formula is configurable and validated
- [ ] Service integrated into ServiceContainer with lazy loading
- [ ] Migration creates tables with proper indexes
- [ ] No existing tests broken
