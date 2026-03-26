---
wave: 4
depends_on: ["03-admin-operations.md"]
files_modified:
  - bot/services/container.py
  - tests/services/test_wallet.py
autonomous: false
---

# Wave 4: Integration and Testing

Integrate WalletService into ServiceContainer and create comprehensive tests for atomic operations, race conditions, and all success criteria.

## Tasks

<task>
<id>1</id>
<description>Integrate WalletService into ServiceContainer</description>
<file>bot/services/container.py</file>
<spec>
Add to ServiceContainer:

1. In __init__, add:
   - self._wallet_service = None

2. Add property:
   @property
   def wallet(self):
       """
       Service de economía (besitos, transacciones, niveles).

       Se carga lazy (solo en primer acceso).

       Returns:
           WalletService: Instancia del service

       Usage:
           # Credit user
           success, msg, tx = await container.wallet.earn_besitos(...)

           # Check balance
           balance = await container.wallet.get_balance(user_id)

           # Get transaction history
           txs, total = await container.wallet.get_transaction_history(user_id)
       """
       if self._wallet_service is None:
           from bot.services.wallet import WalletService
           logger.debug("🔄 Lazy loading: WalletService")
           self._wallet_service = WalletService(self._session)

       return self._wallet_service

3. In get_loaded_services(), add:
   if self._wallet_service is not None:
       loaded.append("wallet")

4. In preload_critical_services(), consider adding wallet if needed.

Ensure WalletService only receives session (not bot), as it doesn't need Telegram API.
</spec>
</task>

<task>
<id>2</id>
<description>Create comprehensive WalletService tests</description>
<file>tests/services/test_wallet.py</file>
<spec>
Create test file with the following test classes:

### TestWalletServiceBasics
- test_get_balance_no_profile: Returns 0 for new user
- test_get_or_create_profile: Creates profile with defaults
- test_profile_fields: balance=0, total_earned=0, total_spent=0, level=1

### TestEarnBesitos
- test_earn_creates_transaction: Verify Transaction record created
- test_earn_updates_balance: Atomic increment
- test_earn_updates_total_earned: Tracks lifetime earnings
- test_earn_invalid_amount: Rejects negative or zero amounts
- test_earn_metadata: Stores metadata correctly

### TestSpendBesitos
- test_spend_with_sufficient_balance: Success case
- test_spend_creates_transaction: Negative amount in transaction
- test_spend_updates_balance: Atomic decrement
- test_spend_updates_total_spent: Tracks lifetime spending
- test_spend_insufficient_funds: Returns (False, "insufficient_funds", None)
- test_spend_no_profile: Returns (False, "no_profile", None)
- test_spend_invalid_amount: Rejects negative or zero amounts

### TestAtomicOperations (Critical for ECON-04)
- test_concurrent_earns_no_race_condition: 10 parallel earns, verify sum
- test_concurrent_spend_no_overspend: Try to spend more than balance concurrently
- test_read_modify_write_avoided: Verify no SELECT then UPDATE patterns

Implementation for race condition test:
```python
async def test_concurrent_earns_no_race_condition(self):
    user_id = 123
    tasks = [
        wallet.earn_besitos(user_id, 10, TransactionType.EARN_REACTION, f"Reaction {i}")
        for i in range(10)
    ]
    results = await asyncio.gather(*tasks)
    assert all(r[0] for r in results)  # All succeed

    balance = await wallet.get_balance(user_id)
    assert balance == 100  # 10 * 10, no lost updates
```

### TestTransactionHistory
- test_get_history_empty: Returns empty list for new user
- test_get_history_pagination: Multiple pages work correctly
- test_get_history_ordering: Most recent first
- test_get_history_with_filter: Filter by transaction type
- test_get_history_total_count: Returns correct total

### TestAdminOperations
- test_admin_credit: Creates EARN_ADMIN transaction
- test_admin_credit_metadata: Contains admin_id
- test_admin_debit_success: Creates SPEND_ADMIN transaction
- test_admin_debit_insufficient_funds: Respects balance limit
- test_admin_debit_metadata: Contains admin_id

### TestLevelCalculation
- test_level_formula_default: sqrt-based formula
- test_level_minimum_one: Never returns level < 1
- test_level_with_total_earned: Various total_earned values
- test_update_level: Updates cached level in profile

### TestIntegrationWithContainer
- test_wallet_service_lazy_loaded: Not loaded until accessed
- test_wallet_service_cached: Same instance on second access
- test_wallet_in_get_loaded_services: Appears when loaded

Use pytest-asyncio and the existing test fixtures from tests/fixtures/.
</spec>
</task>

<task>
<id>3</id>
<description>Create tests for ConfigService economy settings</description>
<file>tests/services/test_config.py</file>
<spec>
Add tests to existing test_config.py or create test_config_economy.py:

### TestLevelFormula
- test_get_level_formula_default: Returns default formula
- test_set_level_formula_valid: Updates formula
- test_set_level_formula_invalid_syntax: Rejects bad formulas
- test_set_level_formula_dangerous: Rejects code injection attempts

### TestEconomyConfig
- test_get_besitos_per_reaction_default: Returns default
- test_set_besitos_per_reaction: Updates value
- test_set_besitos_per_reaction_invalid: Rejects <= 0
- test_get_besitos_daily_gift_default: Returns default
- test_set_besitos_daily_gift: Updates value
- test_get_besitos_daily_streak_bonus_default: Returns default
- test_set_besitos_daily_streak_bonus: Updates value
- test_get_max_reactions_per_day_default: Returns default
- test_set_max_reactions_per_day: Updates value

### TestFormulaValidation
- test_formula_with_sqrt: sqrt(total_earned / 100)
- test_formula_with_floor: floor(total_earned / 500)
- test_formula_complex: floor(sqrt(total_earned) / 10) + 1
- test_formula_rejects_arbitrary_code: No __import__, eval, exec, etc.
</spec>
</task>

<task>
<id>4</id>
<description>Verify all ECON requirements are satisfied</description>
<file>tests/</file>
<spec>
Create tests/economy/test_econ_requirements.py that explicitly tests each requirement:

```python
class TestECONRequirements:
    """Tests that verify each ECON requirement is satisfied."""

    async def test_econ_01_user_can_view_balance(self):
        """ECON-01: User can view their besitos balance in menu"""
        # Setup: Create user with known balance
        await wallet.earn_besitos(user_id, 150, ...)

        # Verify: get_balance returns correct amount
        balance = await wallet.get_balance(user_id)
        assert balance == 150

    async def test_econ_02_user_can_view_transaction_history(self):
        """ECON-02: User can view transaction history (earned/spent)"""
        # Setup: Create transactions
        await wallet.earn_besitos(user_id, 100, ...)
        await wallet.spend_besitos(user_id, 30, ...)

        # Verify: get_transaction_history returns paginated results
        txs, total = await wallet.get_transaction_history(user_id)
        assert len(txs) == 2
        assert total == 2
        assert any(t.amount == 100 for t in txs)
        assert any(t.amount == -30 for t in txs)

    async def test_econ_03_system_prevents_negative_balance(self):
        """ECON-03: System prevents negative balance"""
        # Setup: User with 50 besitos
        await wallet.earn_besitos(user_id, 50, ...)

        # Verify: Cannot spend more than balance
        success, msg, _ = await wallet.spend_besitos(user_id, 100, ...)
        assert success is False
        assert "insufficient" in msg.lower()

        # Verify: Balance unchanged
        assert await wallet.get_balance(user_id) == 50

    async def test_econ_04_all_transactions_are_atomic(self):
        """ECON-04: All transactions are atomic (no race conditions)"""
        # Setup: Multiple concurrent operations
        # Run concurrent earns and verify no lost updates
        # (Detailed in TestAtomicOperations)

    async def test_econ_05_transaction_audit_trail(self):
        """ECON-05: Transaction audit trail is maintained"""
        # Setup: Perform operation
        success, _, tx = await wallet.earn_besitos(user_id, 100,
            TransactionType.EARN_REACTION, "Test reason", {"extra": "data"})

        # Verify: Transaction record exists with all fields
        assert tx is not None
        assert tx.user_id == user_id
        assert tx.amount == 100
        assert tx.type == TransactionType.EARN_REACTION
        assert tx.reason == "Test reason"
        assert tx.metadata == {"extra": "data"}
        assert tx.created_at is not None

    async def test_econ_06_admin_can_adjust_balance(self):
        """ECON-06: Admin can adjust user's besitos balance"""
        # Test credit
        success, _, tx = await wallet.admin_credit(user_id, 200, "Bonus", admin_id=999)
        assert success is True
        assert tx.type == TransactionType.EARN_ADMIN
        assert tx.metadata["admin_id"] == 999

        # Test debit
        success, _, tx = await wallet.admin_debit(user_id, 50, "Penalty", admin_id=999)
        assert success is True
        assert tx.type == TransactionType.SPEND_ADMIN
        assert tx.metadata["admin_id"] == 999

    async def test_econ_07_level_based_on_total_earned(self):
        """ECON-07: Level displayed based on total lifetime besitos earned"""
        # Setup: User with specific total_earned
        await wallet.earn_besitos(user_id, 1000, ...)

        # Verify: Level calculated from total_earned
        level = await wallet.get_user_level(user_id)
        # With default formula floor(sqrt(1000/100)) + 1 = floor(3.16) + 1 = 4
        assert level == 4

    async def test_econ_08_level_formula_configurable(self):
        """ECON-08: Level progression formula is configurable by admin"""
        # Setup: Change formula
        success, _ = await config.set_level_formula("floor(total_earned / 200) + 1")
        assert success is True

        # Verify: New formula used in calculation
        formula = await config.get_level_formula()
        assert formula == "floor(total_earned / 200) + 1"
```
</spec>
</task>

## Verification

Run all tests:
```bash
pytest tests/services/test_wallet.py -v
pytest tests/economy/test_econ_requirements.py -v
```

All tests must pass before phase is complete.

## must_haves

1. WalletService accessible via container.wallet
2. Service is lazy-loaded (not created until first access)
3. All 8 ECON requirements have explicit passing tests
4. Race condition tests verify atomic operations work correctly
5. No existing tests broken (run full test suite)
6. 100% type hint coverage on WalletService
7. All methods have Google Style docstrings
