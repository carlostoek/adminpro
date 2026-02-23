"""
Comprehensive tests for WalletService.

Tests cover:
- Basic operations (balance, profile)
- Earn besitos with atomic operations
- Spend besitos with insufficient funds protection
- Atomic operations and race condition prevention
- Transaction history with pagination
- Admin operations (credit/debit)
- Level calculation with configurable formulas
- Integration with ServiceContainer
"""
import asyncio
import pytest
import pytest_asyncio

from bot.services.wallet import WalletService
from bot.services.config import ConfigService
from bot.database.enums import TransactionType
from bot.database.models import User


@pytest_asyncio.fixture
async def wallet_service(test_session):
    """Fixture: Provides WalletService with test session."""
    return WalletService(test_session)


@pytest_asyncio.fixture
async def config_service(test_session):
    """Fixture: Provides ConfigService with test session."""
    return ConfigService(test_session)


@pytest_asyncio.fixture
async def wallet_test_user(test_session):
    """Fixture: Creates a test user for wallet tests."""
    import random
    user = User(
        user_id=random.randint(100000, 999999),
        username=f"wallettest_{random.randint(1000, 9999)}",
        first_name="Wallet",
        last_name="Test"
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


class TestWalletServiceBasics:
    """Tests for basic wallet operations."""

    async def test_get_balance_no_profile(self, wallet_service):
        """Returns 0 for new user without profile."""
        balance = await wallet_service.get_balance(999999)
        assert balance == 0

    async def test_get_or_create_profile(self, wallet_service, wallet_test_user):
        """Creates profile with defaults when accessed."""
        user_id = wallet_test_user.user_id

        # Get profile (should create it)
        profile = await wallet_service._get_or_create_profile(user_id)

        assert profile is not None
        assert profile.user_id == user_id
        assert profile.balance == 0
        assert profile.total_earned == 0
        assert profile.total_spent == 0
        assert profile.level == 1

    async def test_profile_fields(self, wallet_service, wallet_test_user):
        """Profile has correct default field values."""
        user_id = wallet_test_user.user_id

        profile = await wallet_service._get_or_create_profile(user_id)

        assert profile.balance == 0
        assert profile.total_earned == 0
        assert profile.total_spent == 0
        assert profile.level == 1


class TestEarnBesitos:
    """Tests for earning besitos."""

    async def test_earn_creates_transaction(self, wallet_service, wallet_test_user):
        """Verify Transaction record is created on earn."""
        user_id = wallet_test_user.user_id

        success, msg, tx = await wallet_service.earn_besitos(
            user_id=user_id,
            amount=100,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Test reaction"
        )

        assert success is True
        assert msg == "earned"
        assert tx is not None
        assert tx.user_id == user_id
        assert tx.amount == 100
        assert tx.type == TransactionType.EARN_REACTION
        assert tx.reason == "Test reaction"

    async def test_earn_updates_balance(self, wallet_service, wallet_test_user):
        """Atomic increment of balance."""
        user_id = wallet_test_user.user_id

        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=100,
            transaction_type=TransactionType.EARN_REACTION,
            reason="First earn"
        )

        balance = await wallet_service.get_balance(user_id)
        assert balance == 100

        # Earn more
        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=50,
            transaction_type=TransactionType.EARN_DAILY,
            reason="Daily gift"
        )

        balance = await wallet_service.get_balance(user_id)
        assert balance == 150

    async def test_earn_updates_total_earned(self, wallet_service, wallet_test_user):
        """Tracks lifetime earnings."""
        user_id = wallet_test_user.user_id

        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=100,
            transaction_type=TransactionType.EARN_REACTION,
            reason="First"
        )

        profile = await wallet_service.get_profile(user_id)
        assert profile.total_earned == 100

        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=50,
            transaction_type=TransactionType.EARN_DAILY,
            reason="Second"
        )

        profile = await wallet_service.get_profile(user_id)
        assert profile.total_earned == 150

    async def test_earn_invalid_amount(self, wallet_service, wallet_test_user):
        """Rejects negative or zero amounts."""
        user_id = wallet_test_user.user_id

        # Test zero
        success, msg, tx = await wallet_service.earn_besitos(
            user_id=user_id,
            amount=0,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Invalid"
        )
        assert success is False
        assert msg == "invalid_amount"
        assert tx is None

        # Test negative
        success, msg, tx = await wallet_service.earn_besitos(
            user_id=user_id,
            amount=-10,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Invalid"
        )
        assert success is False
        assert msg == "invalid_amount"
        assert tx is None

    async def test_earn_metadata(self, wallet_service, wallet_test_user):
        """Stores metadata correctly."""
        user_id = wallet_test_user.user_id

        success, msg, tx = await wallet_service.earn_besitos(
            user_id=user_id,
            amount=100,
            transaction_type=TransactionType.EARN_REWARD,
            reason="Achievement unlocked",
            metadata={"achievement_id": "first_reaction", "bonus": True}
        )

        assert success is True
        assert tx.transaction_metadata is not None
        assert tx.transaction_metadata["achievement_id"] == "first_reaction"
        assert tx.transaction_metadata["bonus"] is True


class TestSpendBesitos:
    """Tests for spending besitos."""

    async def test_spend_with_sufficient_balance(self, wallet_service, wallet_test_user):
        """Success case with sufficient balance."""
        user_id = wallet_test_user.user_id

        # First earn
        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=100,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Initial"
        )

        # Then spend
        success, msg, tx = await wallet_service.spend_besitos(
            user_id=user_id,
            amount=30,
            transaction_type=TransactionType.SPEND_SHOP,
            reason="Buy item"
        )

        assert success is True
        assert msg == "spent"
        assert tx is not None

    async def test_spend_creates_transaction(self, wallet_service, wallet_test_user):
        """Negative amount in transaction for spend."""
        user_id = wallet_test_user.user_id

        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=100,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Initial"
        )

        success, msg, tx = await wallet_service.spend_besitos(
            user_id=user_id,
            amount=30,
            transaction_type=TransactionType.SPEND_SHOP,
            reason="Buy item"
        )

        assert tx.amount == -30  # Negative for spend
        assert tx.type == TransactionType.SPEND_SHOP

    async def test_spend_updates_balance(self, wallet_service, wallet_test_user):
        """Atomic decrement of balance."""
        user_id = wallet_test_user.user_id

        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=100,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Initial"
        )

        await wallet_service.spend_besitos(
            user_id=user_id,
            amount=30,
            transaction_type=TransactionType.SPEND_SHOP,
            reason="First purchase"
        )

        balance = await wallet_service.get_balance(user_id)
        assert balance == 70

    async def test_spend_updates_total_spent(self, wallet_service, wallet_test_user):
        """Tracks lifetime spending."""
        user_id = wallet_test_user.user_id

        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=100,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Initial"
        )

        await wallet_service.spend_besitos(
            user_id=user_id,
            amount=30,
            transaction_type=TransactionType.SPEND_SHOP,
            reason="First purchase"
        )

        profile = await wallet_service.get_profile(user_id)
        assert profile.total_spent == 30

        await wallet_service.spend_besitos(
            user_id=user_id,
            amount=20,
            transaction_type=TransactionType.SPEND_SHOP,
            reason="Second purchase"
        )

        profile = await wallet_service.get_profile(user_id)
        assert profile.total_spent == 50

    async def test_spend_insufficient_funds(self, wallet_service, wallet_test_user):
        """Returns (False, 'insufficient_funds', None) when balance too low."""
        user_id = wallet_test_user.user_id

        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=50,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Initial"
        )

        success, msg, tx = await wallet_service.spend_besitos(
            user_id=user_id,
            amount=100,
            transaction_type=TransactionType.SPEND_SHOP,
            reason="Too expensive"
        )

        assert success is False
        assert msg == "insufficient_funds"
        assert tx is None

        # Verify balance unchanged
        balance = await wallet_service.get_balance(user_id)
        assert balance == 50

    async def test_spend_no_profile(self, wallet_service):
        """Returns (False, 'no_profile', None) for new user."""
        user_id = 999999  # Non-existent user

        success, msg, tx = await wallet_service.spend_besitos(
            user_id=user_id,
            amount=10,
            transaction_type=TransactionType.SPEND_SHOP,
            reason="Purchase"
        )

        assert success is False
        assert msg == "no_profile"
        assert tx is None

    async def test_spend_invalid_amount(self, wallet_service, wallet_test_user):
        """Rejects negative or zero amounts."""
        user_id = wallet_test_user.user_id

        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=100,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Initial"
        )

        # Test zero
        success, msg, tx = await wallet_service.spend_besitos(
            user_id=user_id,
            amount=0,
            transaction_type=TransactionType.SPEND_SHOP,
            reason="Invalid"
        )
        assert success is False
        assert msg == "invalid_amount"

        # Test negative
        success, msg, tx = await wallet_service.spend_besitos(
            user_id=user_id,
            amount=-10,
            transaction_type=TransactionType.SPEND_SHOP,
            reason="Invalid"
        )
        assert success is False
        assert msg == "invalid_amount"


class TestAtomicOperations:
    """Critical tests for ECON-04: Atomic operations without race conditions.

    Note: True concurrency tests require separate database connections.
    These tests verify the atomic UPDATE patterns work correctly within
    a single session, which demonstrates the correct SQL patterns.
    """

    async def test_sequential_earns_all_apply(self, wallet_service, wallet_test_user):
        """Multiple sequential earns all apply correctly (no lost updates)."""
        user_id = wallet_test_user.user_id

        # Perform 10 sequential earns
        for i in range(10):
            success, msg, tx = await wallet_service.earn_besitos(
                user_id=user_id,
                amount=10,
                transaction_type=TransactionType.EARN_REACTION,
                reason=f"Reaction {i}"
            )
            assert success is True, f"Earn {i} should succeed"

        # Balance should be exactly 100 (10 * 10), no lost updates
        balance = await wallet_service.get_balance(user_id)
        assert balance == 100

        # Total earned should also be 100
        profile = await wallet_service.get_profile(user_id)
        assert profile.total_earned == 100

    async def test_atomic_spend_respects_balance(self, wallet_service, wallet_test_user):
        """Spend operations respect balance atomically."""
        user_id = wallet_test_user.user_id

        # Start with 50 besitos
        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=50,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Initial"
        )

        # Try to spend 30 besitos sequentially 3 times (total 90, but only have 50)
        results = []
        for i in range(3):
            result = await wallet_service.spend_besitos(
                user_id=user_id,
                amount=30,
                transaction_type=TransactionType.SPEND_SHOP,
                reason=f"Purchase {i}"
            )
            results.append(result)

        # Count successful spends
        successful_spends = [r for r in results if r[0]]

        # Balance should never go negative
        balance = await wallet_service.get_balance(user_id)
        assert balance >= 0, "Balance should never go negative"

        # Verify total spent doesn't exceed initial balance
        profile = await wallet_service.get_profile(user_id)
        assert profile.total_spent <= 50

        # With 50 initial and 30 per spend, should have 1 success (30 spent) and 20 remaining
        # OR if first two succeed somehow, balance would be -10 (but that's prevented)
        assert balance == 20, f"Should have 20 remaining (50 - 30 = 20), got {balance}"
        assert len(successful_spends) == 1, "Should have exactly 1 successful spend"

    async def test_atomic_update_pattern_used(self, wallet_service, wallet_test_user):
        """Verify atomic UPDATE SET pattern is used (not read-modify-write)."""
        # This test verifies the implementation uses atomic UPDATE SET
        # The actual verification is done by code inspection:
        # - earn_besitos uses: UPDATE SET balance = balance + amount
        # - spend_besitos uses: UPDATE SET balance = balance - amount
        #   with WHERE balance >= amount condition

        # We verify behavior matches atomic semantics
        user_id = wallet_test_user.user_id

        # Multiple earns should all apply
        for i in range(5):
            await wallet_service.earn_besitos(
                user_id=user_id,
                amount=10,
                transaction_type=TransactionType.EARN_REACTION,
                reason=f"Earn {i}"
            )

        balance = await wallet_service.get_balance(user_id)
        assert balance == 50, "All earns should apply atomically"

        # Spends should be limited by balance
        for i in range(3):
            await wallet_service.spend_besitos(
                user_id=user_id,
                amount=15,
                transaction_type=TransactionType.SPEND_SHOP,
                reason=f"Spend {i}"
            )

        balance = await wallet_service.get_balance(user_id)
        assert balance >= 0, "Balance should never go negative"
        assert balance == 5, "Should have 5 remaining (50 - 15 - 15 - 15 = 5)"


class TestTransactionHistory:
    """Tests for transaction history pagination."""

    async def test_get_history_empty(self, wallet_service):
        """Returns empty list for new user."""
        user_id = 999998

        txs, total = await wallet_service.get_transaction_history(user_id)

        assert txs == []
        assert total == 0

    async def test_get_history_pagination(self, wallet_service, wallet_test_user):
        """Multiple pages work correctly."""
        user_id = wallet_test_user.user_id

        # Create 25 transactions
        for i in range(25):
            await wallet_service.earn_besitos(
                user_id=user_id,
                amount=10,
                transaction_type=TransactionType.EARN_REACTION,
                reason=f"Reaction {i}"
            )

        # Page 1 (10 items)
        txs, total = await wallet_service.get_transaction_history(
            user_id=user_id, page=1, per_page=10
        )
        assert len(txs) == 10
        assert total == 25

        # Page 2 (10 items)
        txs, total = await wallet_service.get_transaction_history(
            user_id=user_id, page=2, per_page=10
        )
        assert len(txs) == 10
        assert total == 25

        # Page 3 (5 items)
        txs, total = await wallet_service.get_transaction_history(
            user_id=user_id, page=3, per_page=10
        )
        assert len(txs) == 5
        assert total == 25

    async def test_get_history_ordering(self, wallet_service, wallet_test_user):
        """Most recent first."""
        user_id = wallet_test_user.user_id

        # Create transactions in sequence
        for i in range(5):
            await wallet_service.earn_besitos(
                user_id=user_id,
                amount=10,
                transaction_type=TransactionType.EARN_REACTION,
                reason=f"Reaction {i}"
            )

        txs, total = await wallet_service.get_transaction_history(
            user_id=user_id, page=1, per_page=5
        )

        # Should be ordered by created_at desc (most recent first)
        assert len(txs) == 5
        # The last created should be first
        assert "Reaction 4" in txs[0].reason
        assert "Reaction 0" in txs[4].reason

    async def test_get_history_with_filter(self, wallet_service, wallet_test_user):
        """Filter by transaction type."""
        user_id = wallet_test_user.user_id

        # Create different types
        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=10,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Reaction"
        )
        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=20,
            transaction_type=TransactionType.EARN_DAILY,
            reason="Daily"
        )
        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=30,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Another reaction"
        )

        # Filter by REACTION type
        txs, total = await wallet_service.get_transaction_history(
            user_id=user_id, transaction_type=TransactionType.EARN_REACTION
        )

        assert total == 2
        assert all(t.type == TransactionType.EARN_REACTION for t in txs)

    async def test_get_history_total_count(self, wallet_service, wallet_test_user):
        """Returns correct total regardless of pagination."""
        user_id = wallet_test_user.user_id

        # Create 15 transactions
        for i in range(15):
            await wallet_service.earn_besitos(
                user_id=user_id,
                amount=10,
                transaction_type=TransactionType.EARN_REACTION,
                reason=f"Reaction {i}"
            )

        # Different page sizes should all report total=15
        for per_page in [5, 10, 20]:
            txs, total = await wallet_service.get_transaction_history(
                user_id=user_id, page=1, per_page=per_page
            )
            assert total == 15


class TestAdminOperations:
    """Tests for admin credit/debit operations."""

    async def test_admin_credit(self, wallet_service, wallet_test_user):
        """Creates EARN_ADMIN transaction."""
        user_id = wallet_test_user.user_id

        success, msg, tx = await wallet_service.admin_credit(
            user_id=user_id,
            amount=200,
            reason="Bonus",
            admin_id=999
        )

        assert success is True
        assert msg == "credited"
        assert tx is not None
        assert tx.type == TransactionType.EARN_ADMIN
        assert tx.amount == 200

    async def test_admin_credit_metadata(self, wallet_service, wallet_test_user):
        """Contains admin_id in metadata."""
        user_id = wallet_test_user.user_id

        success, msg, tx = await wallet_service.admin_credit(
            user_id=user_id,
            amount=100,
            reason="Test",
            admin_id=555
        )

        assert tx.transaction_metadata is not None
        assert tx.transaction_metadata["admin_id"] == 555
        assert tx.transaction_metadata["action"] == "credit"

    async def test_admin_debit_success(self, wallet_service, wallet_test_user):
        """Creates SPEND_ADMIN transaction."""
        user_id = wallet_test_user.user_id

        # First credit
        await wallet_service.admin_credit(
            user_id=user_id,
            amount=200,
            reason="Initial",
            admin_id=999
        )

        # Then debit
        success, msg, tx = await wallet_service.admin_debit(
            user_id=user_id,
            amount=50,
            reason="Penalty",
            admin_id=999
        )

        assert success is True
        assert msg == "debited"
        assert tx is not None
        assert tx.type == TransactionType.SPEND_ADMIN
        assert tx.amount == -50

    async def test_admin_debit_insufficient_funds(self, wallet_service, wallet_test_user):
        """Respects balance limit."""
        user_id = wallet_test_user.user_id

        await wallet_service.admin_credit(
            user_id=user_id,
            amount=50,
            reason="Small credit",
            admin_id=999
        )

        success, msg, tx = await wallet_service.admin_debit(
            user_id=user_id,
            amount=100,
            reason="Too much",
            admin_id=999
        )

        assert success is False
        assert msg == "insufficient_funds"

    async def test_admin_debit_metadata(self, wallet_service, wallet_test_user):
        """Contains admin_id in metadata."""
        user_id = wallet_test_user.user_id

        await wallet_service.admin_credit(
            user_id=user_id,
            amount=200,
            reason="Initial",
            admin_id=999
        )

        success, msg, tx = await wallet_service.admin_debit(
            user_id=user_id,
            amount=50,
            reason="Test",
            admin_id=777
        )

        assert tx.transaction_metadata is not None
        assert tx.transaction_metadata["admin_id"] == 777
        assert tx.transaction_metadata["action"] == "debit"


class TestLevelCalculation:
    """Tests for user level calculation."""

    async def test_level_formula_default(self, wallet_service, wallet_test_user):
        """Default sqrt-based formula."""
        user_id = wallet_test_user.user_id

        # Default formula: floor(sqrt(total_earned / 100)) + 1
        # total_earned = 0 -> floor(sqrt(0)) + 1 = 1
        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=0,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Zero"
        )

        level = await wallet_service.get_user_level(user_id)
        # With 0 total_earned, level should be 1
        assert level == 1

        # Earn 100 -> floor(sqrt(1)) + 1 = 2
        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=100,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Level up"
        )

        level = await wallet_service.get_user_level(user_id)
        assert level == 2

    async def test_level_minimum_one(self, wallet_service, wallet_test_user):
        """Never returns level < 1."""
        user_id = wallet_test_user.user_id

        # New user should have level 1
        level = await wallet_service.get_user_level(user_id)
        assert level >= 1

        # Even with 0 total_earned
        profile = await wallet_service._get_or_create_profile(user_id)
        level = wallet_service._evaluate_level_formula(0, "")
        assert level >= 1

    async def test_level_with_total_earned(self, wallet_service):
        """Various total_earned values produce expected levels."""
        # Test the formula directly
        formula = "floor(sqrt(total_earned / 100)) + 1"

        test_cases = [
            (0, 1),      # floor(sqrt(0)) + 1 = 1
            (99, 1),     # floor(sqrt(0.99)) + 1 = 1
            (100, 2),    # floor(sqrt(1)) + 1 = 2
            (399, 2),    # floor(sqrt(3.99)) + 1 = 2
            (400, 3),    # floor(sqrt(4)) + 1 = 3
            (900, 4),    # floor(sqrt(9)) + 1 = 4
            (1600, 5),   # floor(sqrt(16)) + 1 = 5
        ]

        for total_earned, expected_level in test_cases:
            level = wallet_service._evaluate_level_formula(total_earned, formula)
            assert level == expected_level, f"total_earned={total_earned} should give level={expected_level}, got {level}"

    async def test_update_level(self, wallet_service, wallet_test_user):
        """Updates cached level in profile."""
        user_id = wallet_test_user.user_id

        # Earn enough to reach level 2
        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=100,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Level up"
        )

        # Update level
        new_level = await wallet_service.update_user_level(user_id)
        assert new_level == 2

        # Verify cached in profile
        profile = await wallet_service.get_profile(user_id)
        assert profile.level == 2


class TestIntegrationWithContainer:
    """Tests for WalletService integration with ServiceContainer."""

    async def test_wallet_service_lazy_loaded(self, container):
        """Not loaded until accessed."""
        # Initially not loaded
        loaded = container.get_loaded_services()
        assert "wallet" not in loaded

        # Access wallet property
        wallet = container.wallet
        assert wallet is not None

        # Now it should be loaded
        loaded = container.get_loaded_services()
        assert "wallet" in loaded

    async def test_wallet_service_cached(self, container):
        """Same instance on second access."""
        wallet1 = container.wallet
        wallet2 = container.wallet

        assert wallet1 is wallet2

    async def test_wallet_in_get_loaded_services(self, container):
        """Appears when loaded."""
        # Trigger lazy load
        _ = container.wallet

        loaded = container.get_loaded_services()
        assert "wallet" in loaded
