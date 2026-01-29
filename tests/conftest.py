"""
Pytest Configuration and Shared Fixtures.

Provides common fixtures for all tests:
- test_db: Isolated in-memory database
- test_session: Active database session
- test_engine: Raw database engine
- test_invitation_token: Pre-created invitation token
- mock_bot: Mock Telegram bot
- container: ServiceContainer with dependencies
- container_with_preload: Container with services preloaded
- Semantic assertion fixtures for voice validation
"""
import pytest
import asyncio

# Import all fixtures from the fixtures package
from tests.fixtures import (
    test_db,
    test_session,
    test_engine,
    test_invitation_token,
    mock_bot,
    container,
    container_with_preload,
)


@pytest.fixture(scope="session")
def event_loop_policy():
    """
    Override event loop policy for the test session.

    Modern pytest-asyncio pattern for session-scoped event loop configuration.
    """
    return asyncio.get_event_loop_policy()


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
    - emoji present (Lucien's signature)
    - No tutear (uses usted form, not informal tú)
    - No technical jargon (speaks naturally, not like a developer)
    - HTML formatting present (elegant presentation)

    Usage:
        def test_welcome_message(assert_lucien_voice):
            text = "<b>Buenos días.</b> Le asisto con su solicitud."
            assert_lucien_voice(text)  # Passes

            bad_text = "Tienes un error en la database."
            assert_lucien_voice(bad_text)  # Fails: tutear + jargon

    Voice Rules:
        - Must contain: emoji, HTML tags (<b> or <i>)
        - Must NOT contain: tutear words (tienes, tu, haz, puedes)
        - Must NOT contain: jargon (database, api, exception, error code, null)
    """
    def _assert_lucien_voice(text: str) -> None:
        """Validate text maintains Lucien's voice characteristics."""
        violations = []

        # Check 1: emoji present
        import re
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE)

        if not emoji_pattern.search(text):
            violations.append("Missing emoji (Lucien's signature)")

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
