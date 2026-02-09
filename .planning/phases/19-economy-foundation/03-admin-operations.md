---
wave: 3
depends_on: ["02-wallet-service-core.md"]
files_modified:
  - bot/services/wallet.py
  - bot/services/config.py
autonomous: false
---

# Wave 3: Admin Operations and Configuration

Implement admin credit/debit operations and configurable level progression formula.

## Tasks

<task>
<id>1</id>
<description>Implement admin credit and debit methods</description>
<file>bot/services/wallet.py</file>
<spec>
Add admin adjustment methods to WalletService:

async def admin_credit(
    self,
    user_id: int,
    amount: int,
    reason: str,
    admin_id: int
) -> Tuple[bool, str, Optional[Transaction]]:
    """
    Admin manually credits besitos to user.

    Args:
        user_id: Target user ID
        amount: Amount to credit (positive)
        reason: Human-readable reason for credit
        admin_id: Admin performing the action (for audit)

    Returns:
        (success, message, transaction)
    """
    - Validate amount > 0
    - Call earn_besitos with:
        - transaction_type = TransactionType.EARN_ADMIN
        - metadata = {"admin_id": admin_id, "action": "credit"}
    - Return result

async def admin_debit(
    self,
    user_id: int,
    amount: int,
    reason: str,
    admin_id: int
) -> Tuple[bool, str, Optional[Transaction]]:
    """
    Admin manually debits besitos from user.

    Args:
        user_id: Target user ID
        amount: Amount to debit (positive)
        reason: Human-readable reason for debit
        admin_id: Admin performing the action (for audit)

    Returns:
        (success, message, transaction)
    """
    - Validate amount > 0
    - Call spend_besitos with:
        - transaction_type = TransactionType.SPEND_ADMIN
        - metadata = {"admin_id": admin_id, "action": "debit"}
    - Return result (includes insufficient_funds check)

Both methods ensure full audit trail with admin_id in metadata.
This satisfies ECON-06 (admin can adjust balance).
</spec>
</task>

<task>
<id>2</id>
<description>Add economy configuration to BotConfig model</description>
<file>bot/database/models.py</file>
<spec>
Add fields to BotConfig model (singleton):

- level_formula: String(255), default="floor(sqrt(total_earned / 100)) + 1"
- besitos_per_reaction: Integer, default=5
- besitos_daily_gift: Integer, default=50
- besitos_daily_streak_bonus: Integer, default=10
- max_reactions_per_day: Integer, default=20

These will be used by WalletService and future ReactionService/StreakService.
</spec>
</task>

<task>
<id>3</id>
<description>Add level formula getters/setters to ConfigService</description>
<file>bot/services/config.py</file>
<spec>
Add to ConfigService:

async def get_level_formula(self) -> str:
    """Get current level progression formula."""
    config = await self.get_config()
    return config.level_formula

async def set_level_formula(self, formula: str) -> Tuple[bool, str]:
    """
    Set level progression formula.

    Args:
        formula: Formula string using total_earned variable
                 Supported: sqrt, floor, +, -, *, /, (, ), numbers

    Returns:
        (success, message)
    """
    - Validate formula syntax
    - Test with sample total_earned values
    - Save to config if valid
    - Return (True, "formula_updated") or (False, "invalid_syntax")

Formula validation:
- Allowed tokens: total_earned, sqrt, floor, digits, +, -, *, /, (, ), space
- Reject if contains other identifiers
- Test evaluation with total_earned=0, 100, 10000
- Must produce valid integers >= 1

Add getters for economy values:
- get_besitos_per_reaction() -> int
- get_besitos_daily_gift() -> int
- get_besitos_daily_streak_bonus() -> int
- get_max_reactions_per_day() -> int

And setters with validation:
- set_besitos_per_reaction(value: int) -> Tuple[bool, str]
- set_besitos_daily_gift(value: int) -> Tuple[bool, str]
- set_besitos_daily_streak_bonus(value: int) -> Tuple[bool, str]
- set_max_reactions_per_day(value: int) -> Tuple[bool, str]

All setters validate value > 0.

This satisfies ECON-08 (configurable level formula).
</spec>
</task>

<task>
<id>4</id>
<description>Create Alembic migration for BotConfig economy fields</description>
<file>alembic/versions/</file>
<spec>
Generate migration to add to bot_config table:
- level_formula (VARCHAR 255)
- besitos_per_reaction (INTEGER)
- besitos_daily_gift (INTEGER)
- besitos_daily_streak_bonus (INTEGER)
- max_reactions_per_day (INTEGER)

All columns nullable with defaults handled in application.
</spec>
</task>

## Verification

```python
# Test admin credit
success, msg, tx = await wallet.admin_credit(
    user_id=123,
    amount=500,
    reason="Compensation for service issue",
    admin_id=999
)
assert success is True
assert tx.type == TransactionType.EARN_ADMIN
assert tx.metadata["admin_id"] == 999

# Test admin debit with sufficient balance
success, msg, tx = await wallet.admin_debit(
    user_id=123,
    amount=200,
    reason="Penalty for rule violation",
    admin_id=999
)
assert success is True
assert tx.type == TransactionType.SPEND_ADMIN

# Test admin debit with insufficient balance
success, msg, tx = await wallet.admin_debit(
    user_id=123,
    amount=999999,
    reason="Large penalty",
    admin_id=999
)
assert success is False
assert msg == "insufficient_funds"

# Test formula configuration
success, msg = await config.set_level_formula("floor(total_earned / 500) + 1")
assert success is True
formula = await config.get_level_formula()
assert formula == "floor(total_earned / 500) + 1"

# Test invalid formula
success, msg = await config.set_level_formula("invalid_formula + hack")
assert success is False
```

## must_haves

1. admin_credit creates EARN_ADMIN transaction with admin_id in metadata
2. admin_debit creates SPEND_ADMIN transaction with admin_id in metadata
3. admin_debit respects insufficient_funds check (cannot go negative)
4. set_level_formula validates syntax and rejects invalid formulas
5. Formula supports: total_earned, sqrt, floor, +, -, *, /, (, )
6. All economy config values have getters and setters
7. All setters validate positive values
