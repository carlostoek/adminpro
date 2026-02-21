---
wave: 2
depends_on: ["01-database-foundation.md"]
files_modified:
  - bot/services/wallet.py
  - bot/services/__init__.py
autonomous: false
---

# Wave 2: WalletService Core Implementation

Implement the core WalletService with atomic operations for balance management, transaction recording, and level calculation.

## Tasks

<task>
<id>1</id>
<description>Create WalletService with initialization and profile management</description>
<file>bot/services/wallet.py</file>
<spec>
Create WalletService class:

__init__(self, session: AsyncSession):
    - Store session
    - Set logger

async def _get_or_create_profile(self, user_id: int) -> UserGamificationProfile:
    - Get profile by user_id
    - Create with defaults if not exists
    - Return profile

async def get_balance(self, user_id: int) -> int:
    - Return current balance (0 if no profile)

async def get_profile(self, user_id: int) -> Optional[UserGamificationProfile]:
    - Return full profile or None

All methods use proper type hints and Google Style docstrings.
Return tuples follow (bool, str, Optional[T]) pattern.
</spec>
</task>

<task>
<id>2</id>
<description>Implement atomic earn_besitos method</description>
<file>bot/services/wallet.py</file>
<spec>
async def earn_besitos(
    self,
    user_id: int,
    amount: int,
    transaction_type: TransactionType,
    reason: str,
    metadata: Optional[Dict] = None
) -> Tuple[bool, str, Optional[Transaction]]:

Validation:
- amount > 0, else return (False, "invalid_amount", None)

Atomic operation:
- Use UPDATE SET balance = balance + :amount, total_earned = total_earned + :amount
- WHERE user_id = :user_id
- If no rows affected, insert new profile with balance = amount

Transaction record:
- Create Transaction with positive amount
- Commit within same transaction block

Return:
- (True, "earned", transaction) on success
- (False, "error_message", None) on failure

This satisfies ECON-04 (atomic) and ECON-05 (audit trail).
</spec>
</task>

<task>
<id>3</id>
<description>Implement atomic spend_besitos with negative balance prevention</description>
<file>bot/services/wallet.py</file>
<spec>
async def spend_besitos(
    self,
    user_id: int,
    amount: int,
    transaction_type: TransactionType,
    reason: str,
    metadata: Optional[Dict] = None
) -> Tuple[bool, str, Optional[Transaction]]:

Validation:
- amount > 0, else return (False, "invalid_amount", None)

Atomic operation with balance check:
- UPDATE user_gamification_profiles
- SET balance = balance - :amount, total_spent = total_spent + :amount
- WHERE user_id = :user_id AND balance >= :amount

Check rows affected:
- If 0 rows: either user has no profile or insufficient balance
- Query current balance to determine which case
- Return (False, "insufficient_funds", None) or (False, "no_profile", None)

Transaction record (only on success):
- Create Transaction with negative amount
- type = transaction_type
- reason = reason
- metadata = metadata

Return:
- (True, "spent", transaction) on success
- (False, "insufficient_funds", None) if would go negative

This satisfies ECON-03 (no negative balance) and ECON-04 (atomic).
</spec>
</task>

<task>
<id>4</id>
<description>Implement transaction history with pagination</description>
<file>bot/services/wallet.py</file>
<spec>
async def get_transaction_history(
    self,
    user_id: int,
    page: int = 1,
    per_page: int = 10,
    transaction_type: Optional[TransactionType] = None
) -> Tuple[List[Transaction], int]:
    """
    Get paginated transaction history for user.

    Args:
        user_id: User ID to query
        page: Page number (1-indexed)
        per_page: Items per page
        transaction_type: Optional filter by type

    Returns:
        Tuple of (transactions list, total count)
    """

Implementation:
- Build query with user_id filter
- Add type filter if provided
- Order by created_at DESC
- Apply offset/limit for pagination
- Execute count query for total
- Return (transactions, total)

This satisfies ECON-02 (transaction history).
</spec>
</task>

<task>
<id>5</id>
<description>Implement level calculation and retrieval</description>
<file>bot/services/wallet.py</file>
<spec>
async def get_user_level(self, user_id: int, formula: Optional[str] = None) -> int:
    """
    Calculate user level based on total_earned.

    Args:
        user_id: User to calculate for
        formula: Optional formula override (uses default if None)

    Returns:
        Current level (1 if no profile)
    """

Implementation:
- Get profile, return 1 if none
- Get formula from parameter or use default: "floor(sqrt(total_earned / 100)) + 1"
- Parse and evaluate formula safely
- Supported operations: sqrt, floor, +, -, *, /, (, )
- Variable: total_earned
- Return calculated level (minimum 1)

async def update_user_level(self, user_id: int, formula: Optional[str] = None) -> int:
    """
    Calculate and update cached level in profile.

    Returns:
        New level value
    """

This satisfies ECON-07 (level based on total earned).
</spec>
</task>

<task>
<id>6</id>
<description>Export WalletService from services package</description>
<file>bot/services/__init__.py</file>
<spec>
Add to imports:
- from bot.services.wallet import WalletService

Add to __all__:
- "WalletService"
</spec>
</task>

## Verification

```python
# Test atomic earn
success, msg, tx = await wallet.earn_besitos(
    user_id=123,
    amount=100,
    transaction_type=TransactionType.EARN_REACTION,
    reason="Reaction to content #456"
)
assert success is True
assert tx.amount == 100

# Test spend with sufficient balance
success, msg, tx = await wallet.spend_besitos(
    user_id=123,
    amount=50,
    transaction_type=TransactionType.SPEND_SHOP,
    reason="Purchase item #789"
)
assert success is True

# Test spend with insufficient balance
success, msg, tx = await wallet.spend_besitos(
    user_id=123,
    amount=1000,
    transaction_type=TransactionType.SPEND_SHOP,
    reason="Purchase expensive item"
)
assert success is False
assert msg == "insufficient_funds"

# Test transaction history
txs, total = await wallet.get_transaction_history(user_id=123)
assert len(txs) == 2
assert total == 2

# Test level calculation
level = await wallet.get_user_level(user_id=123)
assert level >= 1
```

## must_haves

1. earn_besitos uses atomic UPDATE SET balance = balance + amount
2. spend_besitos uses atomic UPDATE with balance >= amount check
3. spend_besitos returns (False, "insufficient_funds", None) for negative balance attempt
4. Every earn/spend creates a Transaction record
5. get_transaction_history returns paginated results with total count
6. get_user_level calculates from total_earned using formula
7. All methods have type hints and Google Style docstrings
