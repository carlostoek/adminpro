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
    """Override event loop policy for the test session."""
    return asyncio.get_event_loop_policy()


@pytest.fixture
def assert_greeting_present():
    """Fixture: Returns assertion function that checks for Spanish greetings."""
    def _assert_greeting_present(text: str) -> None:
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
            raise AssertionError(f"Message must contain greeting, got: {first_100}")
    return _assert_greeting_present


@pytest.fixture
def assert_lucien_voice():
    """Fixture: Returns assertion function that validates Lucien's voice characteristics."""
    def _assert_lucien_voice(text: str) -> None:
        violations = []
        if "🎩" not in text:
            violations.append("Missing 🎩 emoji (Lucien's signature)")
        tutear_words = ["tienes", "tu ", "tu.", "haz", "puedes"]
        text_lower = text.lower()
        found_tutear = [word for word in tutear_words if word in text_lower]
        if found_tutear:
            violations.append(f"Uses tutear (informal): {', '.join(found_tutear)}")
        jargon_words = ["database", "api", "exception", "error code", "null"]
        found_jargon = [word for word in jargon_words if word in text_lower]
        if found_jargon:
            violations.append(f"Contains technical jargon: {', '.join(found_jargon)}")
        if len(text) > 400 and "<b>" not in text and "<i>" not in text:
            violations.append("Missing HTML formatting (<b> or <i>) for complex message")
        if violations:
            raise AssertionError(f"Voice violated: {'; '.join(violations)}")
    return _assert_lucien_voice


@pytest.fixture
def assert_time_aware():
    """Fixture: Returns assertion function that validates time-of-day awareness."""
    def _assert_time_aware(text: str, time_period: str) -> None:
        time_indicators = {
            "morning": ["buenos días", "buen día", "mañana"],
            "afternoon": ["buenas tardes", "buena tarde"],
            "evening": ["buenas noches", "buena noche", "noche"]
        }
        if time_period not in time_indicators:
            raise ValueError(f"Invalid time_period: {time_period}")
        indicators = time_indicators[time_period]
        text_lower = text.lower()
        has_indicator = any(indicator in text_lower for indicator in indicators)
        if not has_indicator:
            first_100 = text[:100] + "..." if len(text) > 100 else text
            raise AssertionError(f"Message must be {time_period}-aware, got: {first_100}")
    return _assert_time_aware
