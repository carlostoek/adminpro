"""
Tests for ConfigService economy configuration settings.

Validates:
- Level formula configuration and validation
- Economy value getters/setters (besitos per reaction, daily gift, etc.)
- Formula security (code injection prevention)
"""
import pytest
import pytest_asyncio

from bot.services.config import ConfigService


@pytest_asyncio.fixture
async def config_service(test_session):
    """Fixture: Provides ConfigService with test session."""
    return ConfigService(test_session)


class TestLevelFormula:
    """Tests for level formula configuration."""

    async def test_get_level_formula_default(self, config_service):
        """Returns default formula."""
        formula = await config_service.get_level_formula()
        assert formula == "floor(sqrt(total_earned / 100)) + 1"

    async def test_set_level_formula_valid(self, config_service):
        """Updates formula with valid syntax."""
        success, msg = await config_service.set_level_formula(
            "floor(total_earned / 200) + 1"
        )
        assert success is True
        assert msg == "formula_updated"

        formula = await config_service.get_level_formula()
        assert formula == "floor(total_earned / 200) + 1"

    async def test_set_level_formula_invalid_syntax(self, config_service):
        """Rejects bad formulas."""
        success, msg = await config_service.set_level_formula(
            "invalid syntax here @#$"
        )
        assert success is False
        assert "invalid_syntax" in msg

    async def test_set_level_formula_dangerous(self, config_service):
        """Rejects code injection attempts."""
        # Test __import__
        success, msg = await config_service.set_level_formula(
            "__import__('os').system('rm -rf /')"
        )
        assert success is False
        assert "invalid_syntax" in msg

        # Test eval
        success, msg = await config_service.set_level_formula(
            "eval('1 + 1')"
        )
        assert success is False
        assert "invalid_syntax" in msg

        # Test exec
        success, msg = await config_service.set_level_formula(
            "exec('import os')"
        )
        assert success is False
        assert "invalid_syntax" in msg


class TestEconomyConfig:
    """Tests for economy configuration values."""

    async def test_get_besitos_per_reaction_default(self, config_service):
        """Returns default value."""
        value = await config_service.get_besitos_per_reaction()
        assert value == 5

    async def test_set_besitos_per_reaction(self, config_service):
        """Updates value."""
        success, msg = await config_service.set_besitos_per_reaction(10)
        assert success is True

        value = await config_service.get_besitos_per_reaction()
        assert value == 10

    async def test_set_besitos_per_reaction_invalid(self, config_service):
        """Rejects <= 0."""
        success, msg = await config_service.set_besitos_per_reaction(0)
        assert success is False
        assert msg == "value_must_be_positive"

        success, msg = await config_service.set_besitos_per_reaction(-5)
        assert success is False
        assert msg == "value_must_be_positive"

    async def test_get_besitos_daily_gift_default(self, config_service):
        """Returns default value."""
        value = await config_service.get_besitos_daily_gift()
        assert value == 50

    async def test_set_besitos_daily_gift(self, config_service):
        """Updates value."""
        success, msg = await config_service.set_besitos_daily_gift(100)
        assert success is True

        value = await config_service.get_besitos_daily_gift()
        assert value == 100

    async def test_get_besitos_daily_streak_bonus_default(self, config_service):
        """Returns default value."""
        value = await config_service.get_besitos_daily_streak_bonus()
        assert value == 10

    async def test_set_besitos_daily_streak_bonus(self, config_service):
        """Updates value."""
        success, msg = await config_service.set_besitos_daily_streak_bonus(25)
        assert success is True

        value = await config_service.get_besitos_daily_streak_bonus()
        assert value == 25

    async def test_get_max_reactions_per_day_default(self, config_service):
        """Returns default value."""
        value = await config_service.get_max_reactions_per_day()
        assert value == 20

    async def test_set_max_reactions_per_day(self, config_service):
        """Updates value."""
        success, msg = await config_service.set_max_reactions_per_day(50)
        assert success is True

        value = await config_service.get_max_reactions_per_day()
        assert value == 50


class TestFormulaValidation:
    """Tests for formula validation with various mathematical patterns."""

    async def test_formula_with_sqrt(self, config_service):
        """sqrt(total_earned / 100) pattern works."""
        success, msg = await config_service.set_level_formula(
            "floor(sqrt(total_earned / 100)) + 1"
        )
        assert success is True

    async def test_formula_with_floor(self, config_service):
        """floor(total_earned / 500) pattern works."""
        success, msg = await config_service.set_level_formula(
            "floor(total_earned / 500) + 1"
        )
        assert success is True

    async def test_formula_complex(self, config_service):
        """floor(sqrt(total_earned) / 10) + 1 pattern works."""
        success, msg = await config_service.set_level_formula(
            "floor(sqrt(total_earned) / 10) + 1"
        )
        assert success is True

    async def test_formula_rejects_arbitrary_code(self, config_service):
        """No __import__, eval, exec, etc. allowed."""
        dangerous_patterns = [
            "__import__('os').system('ls')",
            "eval('1+1')",
            "exec('pass')",
            "open('/etc/passwd').read()",
            "total_earned.__class__",
            "total_earned.__dict__",
            "import os",
            "from os import system",
        ]

        for pattern in dangerous_patterns:
            success, msg = await config_service.set_level_formula(pattern)
            assert success is False, f"Pattern should be rejected: {pattern}"
            assert "invalid_syntax" in msg

    async def test_formula_accepts_arithmetic(self, config_service):
        """Basic arithmetic operations are allowed."""
        valid_formulas = [
            "floor(total_earned / 100) + 1",
            "floor(total_earned * 0.01) + 1",
            "floor((total_earned + 50) / 100) + 1",  # +1 ensures level >= 1
            "floor(sqrt(total_earned)) + 1",
            "floor(total_earned / 100) - 1 + 2",  # Still produces >= 1
        ]

        for formula in valid_formulas:
            # Reset to default first
            await config_service.set_level_formula(
                "floor(sqrt(total_earned / 100)) + 1"
            )

            success, msg = await config_service.set_level_formula(formula)
            assert success is True, f"Formula should be accepted: {formula}"
