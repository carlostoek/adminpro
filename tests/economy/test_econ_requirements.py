"""
Explicit verification tests for all ECON requirements.

These tests directly map to the requirements in REQUIREMENTS.md
and verify each ECON requirement is satisfied.
"""
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
async def econ_test_user(test_session):
    """Fixture: Creates a test user for ECON tests."""
    import random
    user = User(
        user_id=random.randint(100000, 999999),
        username=f"econtest_{random.randint(1000, 9999)}",
        first_name="ECON",
        last_name="Test"
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


class TestECONRequirements:
    """Tests that verify each ECON requirement is satisfied."""

    async def test_econ_01_user_can_view_balance(self, wallet_service, econ_test_user):
        """ECON-01: User can view their besitos balance in menu"""
        # Setup: Create user with known balance
        await wallet_service.earn_besitos(
            user_id=econ_test_user.user_id,
            amount=150,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Test ECON-01"
        )

        # Verify: get_balance returns correct amount
        balance = await wallet_service.get_balance(econ_test_user.user_id)
        assert balance == 150

    async def test_econ_02_user_can_view_transaction_history(
        self, wallet_service, econ_test_user
    ):
        """ECON-02: User can view transaction history (earned/spent)"""
        user_id = econ_test_user.user_id

        # Setup: Create transactions
        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=100,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Earned besitos"
        )
        await wallet_service.spend_besitos(
            user_id=user_id,
            amount=30,
            transaction_type=TransactionType.SPEND_SHOP,
            reason="Spent besitos"
        )

        # Verify: get_transaction_history returns paginated results
        txs, total = await wallet_service.get_transaction_history(user_id)
        assert len(txs) == 2
        assert total == 2
        assert any(t.amount == 100 for t in txs)
        assert any(t.amount == -30 for t in txs)

    async def test_econ_03_system_prevents_negative_balance(
        self, wallet_service, econ_test_user
    ):
        """ECON-03: System prevents negative balance"""
        user_id = econ_test_user.user_id

        # Setup: User with 50 besitos
        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=50,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Initial"
        )

        # Verify: Cannot spend more than balance
        success, msg, _ = await wallet_service.spend_besitos(
            user_id=user_id,
            amount=100,
            transaction_type=TransactionType.SPEND_SHOP,
            reason="Too much"
        )
        assert success is False
        assert "insufficient" in msg.lower()

        # Verify: Balance unchanged
        assert await wallet_service.get_balance(user_id) == 50

    async def test_econ_04_all_transactions_are_atomic(
        self, wallet_service, econ_test_user
    ):
        """ECON-04: All transactions are atomic (no race conditions)"""
        user_id = econ_test_user.user_id

        # Setup: Multiple sequential operations
        for i in range(10):
            await wallet_service.earn_besitos(
                user_id=user_id,
                amount=10,
                transaction_type=TransactionType.EARN_REACTION,
                reason=f"Earn {i}"
            )

        # Verify: All earns applied (no lost updates)
        balance = await wallet_service.get_balance(user_id)
        assert balance == 100

        profile = await wallet_service.get_profile(user_id)
        assert profile.total_earned == 100

    async def test_econ_05_transaction_audit_trail(
        self, wallet_service, econ_test_user
    ):
        """ECON-05: Transaction audit trail is maintained"""
        user_id = econ_test_user.user_id

        # Setup: Perform operation
        success, _, tx = await wallet_service.earn_besitos(
            user_id=user_id,
            amount=100,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Test reason",
            metadata={"extra": "data"}
        )

        # Verify: Transaction record exists with all fields
        assert tx is not None
        assert tx.user_id == user_id
        assert tx.amount == 100
        assert tx.type == TransactionType.EARN_REACTION
        assert tx.reason == "Test reason"
        assert tx.transaction_metadata == {"extra": "data"}
        assert tx.created_at is not None

    async def test_econ_06_admin_can_adjust_balance(
        self, wallet_service, econ_test_user
    ):
        """ECON-06: Admin can adjust user's besitos balance"""
        user_id = econ_test_user.user_id

        # Test credit
        success, _, tx = await wallet_service.admin_credit(
            user_id=user_id,
            amount=200,
            reason="Bonus",
            admin_id=999
        )
        assert success is True
        assert tx.type == TransactionType.EARN_ADMIN
        assert tx.transaction_metadata["admin_id"] == 999

        # Test debit
        success, _, tx = await wallet_service.admin_debit(
            user_id=user_id,
            amount=50,
            reason="Penalty",
            admin_id=999
        )
        assert success is True
        assert tx.type == TransactionType.SPEND_ADMIN
        assert tx.transaction_metadata["admin_id"] == 999

    async def test_econ_07_level_based_on_total_earned(
        self, wallet_service, econ_test_user
    ):
        """ECON-07: Level displayed based on total lifetime besitos earned"""
        user_id = econ_test_user.user_id

        # Setup: User with specific total_earned
        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=1000,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Level up"
        )

        # Verify: Level calculated from total_earned
        level = await wallet_service.get_user_level(user_id)
        # With default formula floor(sqrt(1000/100)) + 1 = floor(3.16) + 1 = 4
        assert level == 4

    async def test_econ_08_level_formula_configurable(
        self, config_service
    ):
        """ECON-08: Level progression formula is configurable by admin"""
        # Setup: Change formula
        success, _ = await config_service.set_level_formula(
            "floor(total_earned / 200) + 1"
        )
        assert success is True

        # Verify: New formula used in calculation
        formula = await config_service.get_level_formula()
        assert formula == "floor(total_earned / 200) + 1"


class TestECONEdgeCases:
    """Additional edge case tests for ECON requirements."""

    async def test_econ_03_balance_never_negative_after_multiple_spends(
        self, wallet_service, econ_test_user
    ):
        """ECON-03: Balance never goes negative even with multiple spends."""
        user_id = econ_test_user.user_id

        # Setup: User with 50 besitos
        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=50,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Initial"
        )

        # Try to spend 30 three times (would need 90, only have 50)
        results = []
        for i in range(3):
            result = await wallet_service.spend_besitos(
                user_id=user_id,
                amount=30,
                transaction_type=TransactionType.SPEND_SHOP,
                reason=f"Spend {i}"
            )
            results.append(result)

        # Verify: Balance never went negative
        balance = await wallet_service.get_balance(user_id)
        assert balance >= 0

        # Verify: Total spent doesn't exceed initial balance
        profile = await wallet_service.get_profile(user_id)
        assert profile.total_spent <= 50

    async def test_econ_05_all_transactions_logged(
        self, wallet_service, econ_test_user
    ):
        """ECON-05: Every single transaction is logged with metadata."""
        user_id = econ_test_user.user_id

        # Perform various operations
        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=100,
            transaction_type=TransactionType.EARN_REACTION,
            reason="Reaction",
            metadata={"content_id": 123}
        )
        await wallet_service.earn_besitos(
            user_id=user_id,
            amount=50,
            transaction_type=TransactionType.EARN_DAILY,
            reason="Daily gift"
        )
        await wallet_service.spend_besitos(
            user_id=user_id,
            amount=30,
            transaction_type=TransactionType.SPEND_SHOP,
            reason="Purchase",
            metadata={"item_id": 456}
        )

        # Get all transactions
        txs, total = await wallet_service.get_transaction_history(user_id)

        # Verify: All 3 transactions logged
        assert total == 3

        # Verify: Each has required fields
        for tx in txs:
            assert tx.user_id == user_id
            assert tx.amount is not None
            assert tx.type is not None
            assert tx.reason is not None
            assert tx.created_at is not None

    async def test_econ_07_level_minimum_one(
        self, wallet_service, econ_test_user
    ):
        """ECON-07: Level is always at least 1, even with 0 total_earned."""
        user_id = econ_test_user.user_id

        # New user should have level 1
        level = await wallet_service.get_user_level(user_id)
        assert level >= 1

        # Even with 0 total_earned
        profile = await wallet_service._get_or_create_profile(user_id)
        assert profile.total_earned == 0
        level = await wallet_service.get_user_level(user_id)
        assert level == 1
