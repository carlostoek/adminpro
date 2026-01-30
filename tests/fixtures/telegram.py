"""
Telegram fixtures for testing.

Provides mocked Message and CallbackQuery objects for testing handlers.
"""
import pytest
from datetime import datetime, timezone
from aiogram.types import Message, CallbackQuery, User, Chat
from unittest.mock import AsyncMock, MagicMock, create_autospec


@pytest.fixture
def admin_user():
    """Create admin user for testing."""
    return User(id=123456789, is_bot=False, first_name="Admin", username="admin_user")


@pytest.fixture
def vip_user():
    """Create VIP user for testing."""
    return User(id=987654321, is_bot=False, first_name="VIP", username="vip_user")


@pytest.fixture
def free_user():
    """Create free user for testing."""
    return User(id=111222333, is_bot=False, first_name="Free", username="free_user")


@pytest.fixture
def regular_user():
    """Create regular user for testing."""
    return User(id=444555666, is_bot=False, first_name="Regular", username="regular_user")


def _create_mock_message(user, text="/start"):
    """Helper to create a mock Message with all required attributes."""
    message = MagicMock(spec=Message)
    message.message_id = 1
    message.date = datetime.now(timezone.utc)
    message.chat = Chat(id=user.id, type="private")
    message.from_user = user
    message.content_type = "text"
    message.text = text
    message.bot = AsyncMock()
    message.answer = AsyncMock()
    message.edit_text = AsyncMock()
    message.edit_reply_markup = AsyncMock()
    return message


def _create_mock_callback(user, data):
    """Helper to create a mock CallbackQuery with all required attributes."""
    callback = MagicMock(spec=CallbackQuery)
    callback.id = f"test_callback_{user.id}"
    callback.from_user = user
    callback.chat_instance = "test"
    callback.data = data
    callback.bot = AsyncMock()
    callback.answer = AsyncMock()

    # Create mock message
    mock_message = MagicMock()
    mock_message.edit_text = AsyncMock()
    mock_message.edit_reply_markup = AsyncMock()
    callback.message = mock_message

    return callback


@pytest.fixture
def admin_message(admin_user):
    """Create admin message."""
    return _create_mock_message(admin_user, text="/admin")


@pytest.fixture
def vip_message(vip_user):
    """Create VIP user message."""
    return _create_mock_message(vip_user, text="/start")


@pytest.fixture
def free_message(free_user):
    """Create free user message."""
    return _create_mock_message(free_user, text="/start")


@pytest.fixture
def user_message(regular_user):
    """Create regular user message."""
    return _create_mock_message(regular_user, text="/start")


@pytest.fixture
def admin_callback(admin_user):
    """Create admin callback query."""
    return _create_mock_callback(admin_user, data="admin:main")


@pytest.fixture
def vip_callback(vip_user):
    """Create VIP user callback."""
    return _create_mock_callback(vip_user, data="menu:vip")


@pytest.fixture
def free_callback(free_user):
    """Create free user callback."""
    return _create_mock_callback(free_user, data="menu:free")


@pytest.fixture
def generic_callback(regular_user):
    """Create generic callback query for general testing."""
    return _create_mock_callback(regular_user, data="menu:main")
