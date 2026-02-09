"""
Tests for WalletService admin operations (Phase 19 - Wave 3).

Validates:
- admin_credit creates EARN_ADMIN transaction with audit metadata
- admin_debit creates SPEND_ADMIN transaction with audit metadata
- admin_debit respects insufficient_funds check
- Formula validation in ConfigService
"""
import pytest
import pytest_asyncio

from bot.services.wallet import WalletService
from bot.services.config import ConfigService
from bot.database.enums import TransactionType


@pytest_asyncio.fixture
async def wallet_service(test_session):
    """Fixture: Provides WalletService with test session."""
    return WalletService(test_session)


@pytest_asyncio.fixture
async def config_service(test_session):
    """Fixture: Provides ConfigService with test session."""
    return ConfigService(test_session)


class TestAdminCredit:
    """Tests for admin_credit method."""

    async def test_admin_credit_creates_earn_admin_transaction(
        self, wallet_service, test_user
    ):
        """admin_credit must create EARN_ADMIN transaction."""
        success, msg, tx = await wallet_service.admin_credit(
            user_id=test_user.user_id,
            amount=100,
            reason="Test credit",
            admin_id=999999
        )

        assert success is True
        assert msg == "credited"
        assert tx is not None
        assert tx.type == TransactionType.EARN_ADMIN
        assert tx.amount == 100

    async def test_admin_credit_includes_admin_id_in_metadata(
        self, wallet_service, test_user
    ):
        """admin_credit must include admin_id in transaction metadata."""
        success, msg, tx = await wallet_service.admin_credit(
            user_id=test_user.user_id,
            amount=50,
            reason="Bonus",
            admin_id=123456
        )

        assert success is True
        assert tx.transaction_metadata is not None
        assert tx.transaction_metadata["admin_id"] == 123456
        assert tx.transaction_metadata["action"] == "credit"

    async def test_admin_credit_validates_positive_amount(
        self, wallet_service, test_user
    ):
        """admin_credit must reject non-positive amounts."""
        success, msg, tx = await wallet_service.admin_credit(
            user_id=test_user.user_id,
            amount=0,
            reason="Invalid",
            admin_id=123456
        )

        assert success is False
        assert msg == "invalid_amount"
        assert tx is None

    async def test_admin_credit_rejects_negative_amount(
        self, wallet_service, test_user
    ):
        """admin_credit must reject negative amounts."""
        success, msg, tx = await wallet_service.admin_credit(
            user_id=test_user.user_id,
            amount=-10,
            reason="Invalid",
            admin_id=123456
        )

        assert success is False
        assert msg == "invalid_amount"


class TestAdminDebit:
    """Tests for admin_debit method."""

    async def test_admin_debit_creates_spend_admin_transaction(
        self, wallet_service, test_user
    ):
        """admin_debit must create SPEND_ADMIN transaction."""
        # First credit some besitos
        await wallet_service.admin_credit(
            user_id=test_user.user_id,
            amount=100,
            reason="Initial",
            admin_id=999999
        )

        # Then debit
        success, msg, tx = await wallet_service.admin_debit(
            user_id=test_user.user_id,
            amount=50,
            reason="Test debit",
            admin_id=999999
        )

        assert success is True
        assert msg == "debited"
        assert tx is not None
        assert tx.type == TransactionType.SPEND_ADMIN
        assert tx.amount == -50  # Negative for spend

    async def test_admin_debit_includes_admin_id_in_metadata(
        self, wallet_service, test_user
    ):
        """admin_debit must include admin_id in transaction metadata."""
        # First credit some besitos
        await wallet_service.admin_credit(
            user_id=test_user.user_id,
            amount=100,
            reason="Initial",
            admin_id=999999
        )

        success, msg, tx = await wallet_service.admin_debit(
            user_id=test_user.user_id,
            amount=30,
            reason="Penalty",
            admin_id=654321
        )

        assert success is True
        assert tx.transaction_metadata is not None
        assert tx.transaction_metadata["admin_id"] == 654321
        assert tx.transaction_metadata["action"] == "debit"

    async def test_admin_debit_respects_insufficient_funds(
        self, wallet_service, test_user
    ):
        """admin_debit must reject if user has insufficient balance."""
        # Credit small amount
        await wallet_service.admin_credit(
            user_id=test_user.user_id,
            amount=10,
            reason="Small credit",
            admin_id=999999
        )

        # Try to debit more than available
        success, msg, tx = await wallet_service.admin_debit(
            user_id=test_user.user_id,
            amount=100,
            reason="Too much",
            admin_id=999999
        )

        assert success is False
        assert msg == "insufficient_funds"
        assert tx is None

    async def test_admin_debit_validates_positive_amount(
        self, wallet_service, test_user
    ):
        """admin_debit must reject non-positive amounts."""
        success, msg, tx = await wallet_service.admin_debit(
            user_id=test_user.user_id,
            amount=0,
            reason="Invalid",
            admin_id=123456
        )

        assert success is False
        assert msg == "invalid_amount"
        assert tx is None

    async def test_admin_debit_returns_no_profile_for_new_user(
        self, wallet_service
    ):
        """admin_debit must return no_profile for users without profile."""
        success, msg, tx = await wallet_service.admin_debit(
            user_id=999999999,  # Non-existent user
            amount=10,
            reason="Test",
            admin_id=123456
        )

        assert success is False
        assert msg == "no_profile"
        assert tx is None


class TestConfigLevelFormula:
    """Tests for ConfigService level formula methods."""

    async def test_get_level_formula_returns_default(self, config_service):
        """get_level_formula must return default formula."""
        formula = await config_service.get_level_formula()
        assert formula == "floor(sqrt(total_earned / 100)) + 1"

    async def test_set_level_formula_validates_syntax(self, config_service):
        """set_level_formula must validate formula syntax."""
        success, msg = await config_service.set_level_formula(
            "floor(sqrt(total_earned / 100)) + 1"
        )
        assert success is True
        assert msg == "formula_updated"

    async def test_set_level_formula_rejects_unknown_identifiers(
        self, config_service
    ):
        """set_level_formula must reject formulas with unknown identifiers."""
        success, msg = await config_service.set_level_formula(
            "malicious_function(total_earned)"
        )
        assert success is False
        assert "invalid_syntax" in msg
        assert "Unknown identifier" in msg

    async def test_set_level_formula_rejects_invalid_characters(
        self, config_service
    ):
        """set_level_formula must reject formulas with invalid characters."""
        success, msg = await config_service.set_level_formula(
            "total_earned + __import__('os').system('rm -rf /')"
        )
        assert success is False
        assert "invalid_syntax" in msg

    async def test_set_level_formula_tests_evaluation(self, config_service):
        """set_level_formula must test formula produces valid results."""
        # This formula would produce 0 for total_earned=0
        success, msg = await config_service.set_level_formula(
            "floor(total_earned / 100)"  # Produces 0 when total_earned < 100
        )
        assert success is False
        assert "invalid_syntax" in msg
        assert "level >= 1" in msg

    async def test_formula_validation_accepts_valid_formula(self, config_service):
        """_validate_formula_syntax must accept valid formulas."""
        is_valid, error = config_service._validate_formula_syntax(
            "floor(sqrt(total_earned / 50)) + 1"
        )
        assert is_valid is True
        assert error == ""

    async def test_formula_validation_rejects_invalid_syntax(self, config_service):
        """_validate_formula_syntax must reject invalid syntax."""
        is_valid, error = config_service._validate_formula_syntax(
            "invalid_func(total_earned)"
        )
        assert is_valid is False
        assert "Unknown identifier" in error


class TestConfigEconomyGettersSetters:
    """Tests for ConfigService economy configuration getters/setters."""

    async def test_get_besitos_per_reaction_returns_default(
        self, config_service
    ):
        """get_besitos_per_reaction must return default value."""
        value = await config_service.get_besitos_per_reaction()
        assert value == 5

    async def test_set_besitos_per_reaction_updates_value(self, config_service):
        """set_besitos_per_reaction must update the value."""
        success, msg = await config_service.set_besitos_per_reaction(10)
        assert success is True

        value = await config_service.get_besitos_per_reaction()
        assert value == 10

    async def test_set_besitos_per_reaction_rejects_zero(self, config_service):
        """set_besitos_per_reaction must reject zero."""
        success, msg = await config_service.set_besitos_per_reaction(0)
        assert success is False
        assert msg == "value_must_be_positive"

    async def test_set_besitos_per_reaction_rejects_negative(
        self, config_service
    ):
        """set_besitos_per_reaction must reject negative values."""
        success, msg = await config_service.set_besitos_per_reaction(-5)
        assert success is False
        assert msg == "value_must_be_positive"

    async def test_get_besitos_daily_gift_returns_default(self, config_service):
        """get_besitos_daily_gift must return default value."""
        value = await config_service.get_besitos_daily_gift()
        assert value == 50

    async def test_set_besitos_daily_gift_updates_value(self, config_service):
        """set_besitos_daily_gift must update the value."""
        success, msg = await config_service.set_besitos_daily_gift(100)
        assert success is True

        value = await config_service.get_besitos_daily_gift()
        assert value == 100

    async def test_get_besitos_daily_streak_bonus_returns_default(
        self, config_service
    ):
        """get_besitos_daily_streak_bonus must return default value."""
        value = await config_service.get_besitos_daily_streak_bonus()
        assert value == 10

    async def test_set_besitos_daily_streak_bonus_updates_value(
        self, config_service
    ):
        """set_besitos_daily_streak_bonus must update the value."""
        success, msg = await config_service.set_besitos_daily_streak_bonus(25)
        assert success is True

        value = await config_service.get_besitos_daily_streak_bonus()
        assert value == 25

    async def test_get_max_reactions_per_day_returns_default(self, config_service):
        """get_max_reactions_per_day must return default value."""
        value = await config_service.get_max_reactions_per_day()
        assert value == 20

    async def test_set_max_reactions_per_day_updates_value(self, config_service):
        """set_max_reactions_per_day must update the value."""
        success, msg = await config_service.set_max_reactions_per_day(50)
        assert success is True

        value = await config_service.get_max_reactions_per_day()
        assert value == 50
