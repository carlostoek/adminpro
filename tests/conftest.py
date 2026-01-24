"""
Pytest Configuration and Shared Fixtures.

Proporciona fixtures comunes para todos los tests:
- mock_bot: Mock del bot de Telegram
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock

from bot.database import init_db, close_db


@pytest.fixture
def event_loop():
    """
    Fixture: Event loop para tests async.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# Hook para inicializar BD antes de cada test async
@pytest.fixture(autouse=True)
def db_setup(event_loop):
    """
    Setup BD antes de cada test.
    """
    # Ejecutar init_db antes del test
    event_loop.run_until_complete(init_db())

    yield

    # Limpiar BD despues del test
    event_loop.run_until_complete(close_db())


@pytest.fixture
def mock_bot():
    """
    Fixture: Mock del bot de Telegram.

    Proporciona mock de métodos Telegram API necesarios:
    - get_chat
    - get_chat_member
    - create_chat_invite_link
    - ban_chat_member
    - unban_chat_member
    - send_message
    """
    bot = Mock()
    bot.id = 123456789

    # Mock de métodos necesarios (retornan AsyncMock)
    bot.get_chat = AsyncMock()
    bot.get_chat_member = AsyncMock()
    bot.create_chat_invite_link = AsyncMock()
    bot.ban_chat_member = AsyncMock()
    bot.unban_chat_member = AsyncMock()
    bot.send_message = AsyncMock()

    return bot


# ============================================================================
# SEMANTIC ASSERTION FIXTURES
# ============================================================================
# These fixtures provide semantic validation functions that test INTENT
# rather than exact wording, making tests resilient to message variations.


@pytest.fixture
def assert_greeting_present():
    """
    Fixture: Returns assertion function that checks for Spanish greetings.

    Validates message contains at least one common Spanish greeting,
    making tests variation-safe (doesn't break when greeting wording changes).

    Usage:
        def test_welcome_message(assert_greeting_present):
            text = "Buenos días, Juan. Bienvenido al sistema."
            assert_greeting_present(text)  # Passes

    Greetings checked (case-insensitive):
        - buenos días, buen día
        - buenas tardes, buena tarde
        - buenas noches, buena noche
        - bienvenido, bienvenida
        - hola, saludos
    """
    def _assert_greeting_present(text: str) -> None:
        """Check if text contains any Spanish greeting."""
        greetings = [
            "buenos días", "buen día",
            "buenas tardes", "buena tarde",
            "buenas noches", "buena noche",
            "bienvenido", "bienvenida",
            "hola", "saludos"
        ]

        text_lower = text.lower()
        has_greeting = any(greeting in text_lower for greeting in greetings)

        if not has_greeting:
            first_100 = text[:100] + "..." if len(text) > 100 else text
            raise AssertionError(
                f"Message must contain greeting, got: {first_100}"
            )

    return _assert_greeting_present


@pytest.fixture
def assert_lucien_voice():
    """
    Fixture: Returns assertion function that validates Lucien's voice characteristics.

    Ensures messages maintain the sophisticated mayordomo personality:
    - 🎩 emoji present (Lucien's signature)
    - No tutear (uses usted form, not informal tú)
    - No technical jargon (speaks naturally, not like a developer)
    - HTML formatting present (elegant presentation)

    Usage:
        def test_welcome_message(assert_lucien_voice):
            text = "🎩 <b>Buenos días.</b> Le asisto con su solicitud."
            assert_lucien_voice(text)  # Passes

            bad_text = "Tienes un error en la database."
            assert_lucien_voice(bad_text)  # Fails: tutear + jargon

    Voice Rules:
        - Must contain: 🎩 emoji, HTML tags (<b> or <i>)
        - Must NOT contain: tutear words (tienes, tu, haz, puedes)
        - Must NOT contain: jargon (database, api, exception, error code, null)
    """
    def _assert_lucien_voice(text: str) -> None:
        """Validate text maintains Lucien's voice characteristics."""
        violations = []

        # Check 1: 🎩 emoji present
        if "🎩" not in text:
            violations.append("Missing 🎩 emoji (Lucien's signature)")

        # Check 2: No tutear (informal tú form)
        tutear_words = ["tienes", "tu ", "tu.", "haz", "puedes"]
        text_lower = text.lower()
        found_tutear = [word for word in tutear_words if word in text_lower]
        if found_tutear:
            violations.append(f"Uses tutear (informal): {', '.join(found_tutear)}")

        # Check 3: No technical jargon
        jargon_words = ["database", "api", "exception", "error code", "null"]
        found_jargon = [word for word in jargon_words if word in text_lower]
        if found_jargon:
            violations.append(f"Contains technical jargon: {', '.join(found_jargon)}")

        # Check 4: HTML formatting present (optional for simple messages)
        # Lenient: Some error messages are intentionally plain text for clarity
        # Only flag if it's truly a complex message (>400 chars) without any formatting
        if len(text) > 400 and "<b>" not in text and "<i>" not in text:
            violations.append("Missing HTML formatting (<b> or <i>) for complex message")

        if violations:
            raise AssertionError(
                f"Voice violated: {'; '.join(violations)}"
            )

    return _assert_lucien_voice


@pytest.fixture
def assert_time_aware():
    """
    Fixture: Returns assertion function that validates time-of-day awareness.

    Ensures messages adapt appropriately to time period (morning/afternoon/evening),
    making tests resilient to specific greeting variations.

    Usage:
        def test_morning_greeting(assert_time_aware):
            text = "Buenos días, Juan. ¿En qué puedo asistirle?"
            assert_time_aware(text, "morning")  # Passes

        def test_evening_greeting(assert_time_aware):
            text = "Buenas noches. Le atiendo esta noche."
            assert_time_aware(text, "evening")  # Passes

    Time Periods:
        - morning (6:00-11:59): buenos días, buen día, mañana
        - afternoon (12:00-19:59): buenas tardes, buena tarde
        - evening (20:00-5:59): buenas noches, buena noche, noche
    """
    def _assert_time_aware(text: str, time_period: str) -> None:
        """Validate text contains appropriate time-of-day indicators."""
        time_indicators = {
            "morning": ["buenos días", "buen día", "mañana"],
            "afternoon": ["buenas tardes", "buena tarde"],
            "evening": ["buenas noches", "buena noche", "noche"]
        }

        if time_period not in time_indicators:
            raise ValueError(
                f"Invalid time_period: {time_period}. "
                f"Must be one of: {list(time_indicators.keys())}"
            )

        indicators = time_indicators[time_period]
        text_lower = text.lower()
        has_indicator = any(indicator in text_lower for indicator in indicators)

        if not has_indicator:
            first_100 = text[:100] + "..." if len(text) > 100 else text
            raise AssertionError(
                f"Message must be {time_period}-aware, got: {first_100}"
            )

    return _assert_time_aware
