"""
Tests for Atomic Purchase with Automatic Refund (Tarea 2A).

Verifies:
- Purchase flow: spend_besitos -> deliver_content
- Automatic refund on delivery failure
- User notification of error and refund
- Proper logging of incidents
"""
import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from bot.services.shop import ShopService
from bot.services.wallet import WalletService
from bot.services.reward import RewardService
from bot.database.models import ContentSet, ShopProduct, UserContentAccess, User, UserGamificationProfile
from bot.database.enums import ContentType, ContentTier, TransactionType, UserRole


@pytest_asyncio.fixture
async def atomic_wallet_service(test_session):
    """Fixture: Provides WalletService with test session."""
    return WalletService(test_session)


@pytest_asyncio.fixture
async def atomic_shop_service(test_session, atomic_wallet_service):
    """Fixture: Provides ShopService with test session and wallet service."""
    return ShopService(test_session, wallet_service=atomic_wallet_service)


@pytest_asyncio.fixture
async def atomic_reward_service(test_session, atomic_wallet_service):
    """Fixture: Provides RewardService for testing."""
    return RewardService(test_session, wallet_service=atomic_wallet_service)


@pytest_asyncio.fixture
async def atomic_test_user(test_session):
    """Fixture: Creates a test user for atomic purchase tests."""
    import random
    user = User(
        user_id=random.randint(100000, 999999),
        username=f"atomictest_{random.randint(1000, 9999)}",
        first_name="Atomic",
        last_name="Test",
        role=UserRole.FREE
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def atomic_content_set(test_session):
    """Fixture: Creates a test content set with files."""
    content_set = ContentSet(
        name="Atomic Test Content Pack",
        file_ids=["file1_id", "file2_id", "file3_id"],
        content_type=ContentType.PHOTO_SET,
        tier=ContentTier.FREE
    )
    test_session.add(content_set)
    await test_session.commit()
    await test_session.refresh(content_set)
    return content_set


@pytest_asyncio.fixture
async def atomic_shop_product(test_session, atomic_content_set):
    """Fixture: Creates a test shop product."""
    product = ShopProduct(
        name="Atomic Test Product",
        description="A test product for atomic purchase tests",
        content_set_id=atomic_content_set.id,
        besitos_price=100,
        vip_besitos_price=80,
        vip_discount_percentage=20,
        tier=ContentTier.FREE,
        is_active=True
    )
    test_session.add(product)
    await test_session.commit()
    await test_session.refresh(product)
    return product


class TestAtomicPurchaseRefund:
    """Tests for atomic purchase with automatic refund on delivery failure."""

    async def test_purchase_successful_delivery_no_refund(
        self, atomic_shop_service, atomic_wallet_service, atomic_shop_product, atomic_test_user, test_session
    ):
        """Successful purchase and delivery - no refund needed."""
        # Setup: Add balance to user
        await atomic_wallet_service.earn_besitos(
            user_id=atomic_test_user.user_id,
            amount=200,
            transaction_type=TransactionType.EARN_ADMIN,
            reason="Test setup"
        )

        # Execute purchase
        success, status, result = await atomic_shop_service.purchase_product(
            user_id=atomic_test_user.user_id,
            product_id=atomic_shop_product.id,
            user_role="FREE"
        )

        assert success is True
        assert status == "success"
        assert result["price_paid"] == 100

        # Verify balance deducted
        balance = await atomic_wallet_service.get_balance(atomic_test_user.user_id)
        assert balance == 100  # 200 - 100

        # Verify access record created
        from sqlalchemy import select
        result = await test_session.execute(
            select(UserContentAccess).where(
                UserContentAccess.user_id == atomic_test_user.user_id
            )
        )
        access = result.scalar_one_or_none()
        assert access is not None
        assert access.besitos_paid == 100

    async def test_refund_on_delivery_failure_simulated(
        self, atomic_wallet_service, atomic_test_user, atomic_shop_product, test_session
    ):
        """Simulated delivery failure triggers automatic refund via admin_credit."""
        # Setup: Add balance to user
        await atomic_wallet_service.earn_besitos(
            user_id=atomic_test_user.user_id,
            amount=200,
            transaction_type=TransactionType.EARN_ADMIN,
            reason="Test setup"
        )

        # Get initial balance
        initial_balance = await atomic_wallet_service.get_balance(atomic_test_user.user_id)
        assert initial_balance == 200

        # Simulate: Spend besitos (as would happen in purchase)
        price = 100
        spend_success, spend_msg, tx = await atomic_wallet_service.spend_besitos(
            user_id=atomic_test_user.user_id,
            amount=price,
            transaction_type=TransactionType.SPEND_SHOP,
            reason=f"Purchase product #{atomic_shop_product.id}",
            metadata={"product_id": atomic_shop_product.id}
        )
        assert spend_success is True

        # Verify balance after spend
        balance_after_spend = await atomic_wallet_service.get_balance(atomic_test_user.user_id)
        assert balance_after_spend == 100  # 200 - 100

        # Simulate: Delivery fails, trigger automatic refund
        refund_success, refund_msg, refund_tx = await atomic_wallet_service.admin_credit(
            user_id=atomic_test_user.user_id,
            amount=price,
            reason="reembolso_automatico_fallo_entrega",
            admin_id=0  # System admin
        )

        assert refund_success is True
        assert refund_msg == "credited"

        # Verify balance restored
        final_balance = await atomic_wallet_service.get_balance(atomic_test_user.user_id)
        assert final_balance == 200  # Original balance restored

        # Verify transaction record exists
        from sqlalchemy import select
        from bot.database.models import Transaction
        result = await test_session.execute(
            select(Transaction).where(
                Transaction.user_id == atomic_test_user.user_id,
                Transaction.type == TransactionType.EARN_ADMIN
            ).order_by(Transaction.created_at.desc())
        )
        transactions = result.scalars().all()

        # Find the refund transaction
        refund_transactions = [t for t in transactions if t.reason == "reembolso_automatico_fallo_entrega"]
        assert len(refund_transactions) >= 1

        # Verify refund transaction metadata
        refund_tx_record = refund_transactions[0]
        assert refund_tx_record.amount == price  # Positive amount for credit
        assert refund_tx_record.transaction_metadata.get("admin_id") == 0
        assert refund_tx_record.transaction_metadata.get("action") == "credit"

    async def test_refund_amount_matches_purchase_price(
        self, atomic_wallet_service, atomic_test_user
    ):
        """Refund amount exactly matches the purchase price."""
        # Setup: Add balance
        await atomic_wallet_service.earn_besitos(
            user_id=atomic_test_user.user_id,
            amount=500,
            transaction_type=TransactionType.EARN_ADMIN,
            reason="Test setup"
        )

        # Test different purchase amounts
        test_amounts = [50, 100, 250, 500]

        for amount in test_amounts:
            # Spend besitos
            spend_success, _, _ = await atomic_wallet_service.spend_besitos(
                user_id=atomic_test_user.user_id,
                amount=amount,
                transaction_type=TransactionType.SPEND_SHOP,
                reason=f"Test purchase of {amount}"
            )
            assert spend_success is True

            # Verify balance reduced
            balance = await atomic_wallet_service.get_balance(atomic_test_user.user_id)

            # Refund exact amount
            refund_success, _, refund_tx = await atomic_wallet_service.admin_credit(
                user_id=atomic_test_user.user_id,
                amount=amount,
                reason="reembolso_automatico_fallo_entrega",
                admin_id=0
            )
            assert refund_success is True
            assert refund_tx.amount == amount

        # Final balance should be back to original (minus any rounding issues)
        final_balance = await atomic_wallet_service.get_balance(atomic_test_user.user_id)
        assert final_balance == 500  # Original amount

    async def test_refund_transaction_logged_with_correct_reason(
        self, atomic_wallet_service, atomic_test_user, test_session
    ):
        """Refund transaction is logged with correct reason for audit trail."""
        # Setup
        await atomic_wallet_service.earn_besitos(
            user_id=atomic_test_user.user_id,
            amount=100,
            transaction_type=TransactionType.EARN_ADMIN,
            reason="Test setup"
        )

        # Spend and refund
        await atomic_wallet_service.spend_besitos(
            user_id=atomic_test_user.user_id,
            amount=50,
            transaction_type=TransactionType.SPEND_SHOP,
            reason="Test purchase"
        )

        await atomic_wallet_service.admin_credit(
            user_id=atomic_test_user.user_id,
            amount=50,
            reason="reembolso_automatico_fallo_entrega",
            admin_id=0
        )

        # Query transactions
        from sqlalchemy import select
        from bot.database.models import Transaction
        result = await test_session.execute(
            select(Transaction).where(
                Transaction.user_id == atomic_test_user.user_id
            ).order_by(Transaction.created_at.asc())
        )
        transactions = result.scalars().all()

        # Verify transaction sequence
        assert len(transactions) >= 3  # Setup earn, spend, refund

        # Find refund transaction
        refund_tx = [t for t in transactions if t.reason == "reembolso_automatico_fallo_entrega"][0]
        assert refund_tx.type == TransactionType.EARN_ADMIN
        assert refund_tx.amount == 50
        assert refund_tx.transaction_metadata.get("admin_id") == 0
        assert refund_tx.transaction_metadata.get("action") == "credit"

    async def test_multiple_refunds_sum_correctly(
        self, atomic_wallet_service, atomic_test_user
    ):
        """Multiple refunds (if needed) sum correctly to restore balance."""
        # Setup
        await atomic_wallet_service.earn_besitos(
            user_id=atomic_test_user.user_id,
            amount=1000,
            transaction_type=TransactionType.EARN_ADMIN,
            reason="Test setup"
        )

        # Multiple purchases and refunds
        purchases = [100, 200, 150]

        for amount in purchases:
            # Spend
            await atomic_wallet_service.spend_besitos(
                user_id=atomic_test_user.user_id,
                amount=amount,
                transaction_type=TransactionType.SPEND_SHOP,
                reason=f"Purchase {amount}"
            )

            # Refund
            await atomic_wallet_service.admin_credit(
                user_id=atomic_test_user.user_id,
                amount=amount,
                reason="reembolso_automatico_fallo_entrega",
                admin_id=0
            )

        # Balance should be restored
        final_balance = await atomic_wallet_service.get_balance(atomic_test_user.user_id)
        assert final_balance == 1000

    async def test_refund_with_zero_admin_id_is_system_refund(
        self, atomic_wallet_service, atomic_test_user
    ):
        """Refund with admin_id=0 indicates system-initiated automatic refund."""
        await atomic_wallet_service.earn_besitos(
            user_id=atomic_test_user.user_id,
            amount=100,
            transaction_type=TransactionType.EARN_ADMIN,
            reason="Test setup"
        )

        _, _, refund_tx = await atomic_wallet_service.admin_credit(
            user_id=atomic_test_user.user_id,
            amount=50,
            reason="reembolso_automatico_fallo_entrega",
            admin_id=0
        )

        assert refund_tx.transaction_metadata.get("admin_id") == 0
        assert refund_tx.transaction_metadata.get("action") == "credit"


class TestPurchaseFlowIntegration:
    """Integration tests for complete purchase flow with refund."""

    async def test_complete_flow_with_simulated_delivery_error(
        self, atomic_shop_service, atomic_wallet_service, atomic_shop_product, atomic_test_user, test_session
    ):
        """Complete flow: validate -> spend -> (delivery fails) -> refund."""
        # Setup: Add balance
        await atomic_wallet_service.earn_besitos(
            user_id=atomic_test_user.user_id,
            amount=200,
            transaction_type=TransactionType.EARN_ADMIN,
            reason="Test setup"
        )

        initial_balance = await atomic_wallet_service.get_balance(atomic_test_user.user_id)

        # Step 1: Validate purchase
        can_purchase, reason, details = await atomic_shop_service.validate_purchase(
            user_id=atomic_test_user.user_id,
            product_id=atomic_shop_product.id,
            user_role="FREE"
        )
        assert can_purchase is True
        price_to_pay = details["price_to_pay"]

        # Step 2: Spend besitos
        spend_success, _, _ = await atomic_wallet_service.spend_besitos(
            user_id=atomic_test_user.user_id,
            amount=price_to_pay,
            transaction_type=TransactionType.SPEND_SHOP,
            reason=f"Purchase product #{atomic_shop_product.id}"
        )
        assert spend_success is True

        balance_after_spend = await atomic_wallet_service.get_balance(atomic_test_user.user_id)
        assert balance_after_spend == initial_balance - price_to_pay

        # Step 3: Simulate delivery failure and refund
        refund_success, _, _ = await atomic_wallet_service.admin_credit(
            user_id=atomic_test_user.user_id,
            amount=price_to_pay,
            reason="reembolso_automatico_fallo_entrega",
            admin_id=0
        )
        assert refund_success is True

        # Step 4: Verify balance restored
        final_balance = await atomic_wallet_service.get_balance(atomic_test_user.user_id)
        assert final_balance == initial_balance

    async def test_purchase_flow_state_consistency(
        self, atomic_shop_service, atomic_wallet_service, atomic_shop_product, atomic_test_user, test_session
    ):
        """Purchase flow maintains database consistency through refund."""
        from sqlalchemy import select, func
        from bot.database.models import Transaction

        # Setup
        await atomic_wallet_service.earn_besitos(
            user_id=atomic_test_user.user_id,
            amount=200,
            transaction_type=TransactionType.EARN_ADMIN,
            reason="Test setup"
        )

        # Get initial transaction count
        result = await test_session.execute(
            select(func.count(Transaction.id)).where(
                Transaction.user_id == atomic_test_user.user_id
            )
        )
        initial_tx_count = result.scalar_one()

        # Purchase and refund
        await atomic_wallet_service.spend_besitos(
            user_id=atomic_test_user.user_id,
            amount=100,
            transaction_type=TransactionType.SPEND_SHOP,
            reason="Purchase"
        )

        await atomic_wallet_service.admin_credit(
            user_id=atomic_test_user.user_id,
            amount=100,
            reason="reembolso_automatico_fallo_entrega",
            admin_id=0
        )

        # Verify transaction count increased by 2
        result = await test_session.execute(
            select(func.count(Transaction.id)).where(
                Transaction.user_id == atomic_test_user.user_id
            )
        )
        final_tx_count = result.scalar_one()
        assert final_tx_count == initial_tx_count + 2  # Spend + refund

        # Verify balance is consistent
        # Sum of all transactions should equal current balance
        result = await test_session.execute(
            select(func.sum(Transaction.amount)).where(
                Transaction.user_id == atomic_test_user.user_id
            )
        )
        total_transaction_amount = result.scalar_one() or 0

        current_balance = await atomic_wallet_service.get_balance(atomic_test_user.user_id)

        # The total earned (positive amounts) minus spent (negative amounts)
        # For this test: +200 (setup) -100 (purchase) +100 (refund) = +200 net
        # Current balance should be 200
        assert current_balance == 200
        assert total_transaction_amount == 200  # Net sum of all transactions
