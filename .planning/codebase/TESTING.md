# Testing Patterns

**Analysis Date:** 2026-01-23

## Test Framework

**Runner:**
- pytest 7.4.3
- Config: No pytest.ini (uses default discovery)
- pytest-asyncio 0.21.1 for async test support

**Assertion Library:**
- Python's built-in `assert` statements

**Run Commands:**
```bash
pytest tests/ -v                    # Run all tests with verbose output
pytest tests/ -v -k test_name       # Run specific test by name pattern
pytest -x tests/                    # Stop on first failure
pytest tests/ --tb=short            # Show shorter tracebacks
python -m pytest tests/             # Alternative invocation
bash scripts/run_tests.sh           # Helper script (if present)
```

## Test File Organization

**Location:**
- Tests co-located in `tests/` directory at project root
- Pattern: `tests/test_*.py` for test files
- Pattern: `tests/conftest.py` for shared fixtures
- Some test files at root for quick testing during development: `test_formatters.py`, `test_handlers.py`

**Naming:**
- Test files: `test_e2e_flows.py`, `test_pricing_service.py`, `test_a3_deep_links.py`
- Test functions: `test_vip_flow_complete()`, `test_create_plan()`, `test_generate_token_with_plan()`
- Fixture functions: `event_loop()`, `db_setup()`, `mock_bot()`

**Structure:**
```
tests/
├── conftest.py                     # Shared fixtures and config
├── test_e2e_flows.py              # End-to-end flow tests
├── test_integration.py            # Service integration tests
├── test_pricing_service.py        # PricingService unit tests
├── test_a3_deep_links.py          # Deep link feature tests
├── test_e2e_onda2.py              # ONDA 2 feature tests
├── test_sprint1_features.py       # Sprint 1 feature tests
├── test_user_service.py           # UserService tests
└── __init__.py
```

## Test Structure

**Suite Organization:**
```python
"""
Module-level docstring describing what tests do.

Tests that validate:
- Feature 1
- Feature 2
- Feature 3
"""
import pytest
from datetime import datetime, timedelta

from bot.database import get_session
from bot.database.models import VIPSubscriber
from bot.services.container import ServiceContainer


@pytest.mark.asyncio
async def test_specific_feature(mock_bot):
    """
    Test summary on one line.

    Detailed description of what the test validates:
    1. Step 1
    2. Step 2
    3. Step 3

    Expected:
    - Assertion 1
    - Assertion 2
    """
    # Setup phase
    admin_id = 111111
    user_id = 222222

    # Async context manager for session
    async with get_session() as session:
        container = ServiceContainer(session, mock_bot)

        # Action phase
        result = await container.subscription.method_name(...)

        # Assertion phase
        assert result is not None
        assert result.field == expected_value
```

**Patterns:**
- All async tests marked with `@pytest.mark.asyncio`
- Session obtained via `async with get_session() as session:`
- ServiceContainer created with `(session, mock_bot)`
- Three phases: Setup, Action, Assert

## Mocking

**Framework:** unittest.mock (Python standard library)

**Patterns:**
```python
from unittest.mock import AsyncMock, Mock, MagicMock

# Create mock bot
bot = Mock()
bot.id = 123456789

# Mock async methods
bot.get_chat = AsyncMock()
bot.send_message = AsyncMock()
bot.create_chat_invite_link = AsyncMock()
bot.ban_chat_member = AsyncMock()

# Setup return values
bot.get_chat.return_value = Chat(id="-100123456789", type="supergroup")
bot.send_message.return_value = Message(message_id=1, date=datetime.now(timezone.utc))

# Verify calls
bot.send_message.assert_called_with(chat_id=123, text="text")
bot.send_message.assert_called_once()
```

**What to Mock:**
- Telegram API methods (bot.get_chat, bot.send_message, etc.)
- External services (when testing service isolation)
- Never mock: database (tests use real async session), internal services

**What NOT to Mock:**
- Database layer - tests use real async SQLite via conftest setup
- ServiceContainer dependencies - tests use real services
- Internal service methods - test end-to-end flows

## Fixtures and Factories

**Test Data:**

Database auto-initialized by autouse fixture:
```python
@pytest.fixture(autouse=True)
def db_setup(event_loop):
    """Setup BD before each test."""
    event_loop.run_until_complete(init_db())
    yield
    event_loop.run_until_complete(close_db())
```

Mock bot fixture:
```python
@pytest.fixture
def mock_bot():
    """Fixture: Mock del bot de Telegram."""
    bot = Mock()
    bot.id = 123456789
    bot.get_chat = AsyncMock()
    bot.send_message = AsyncMock()
    # ... more mocks
    return bot
```

Test data created inline in tests:
```python
# Hardcoded IDs for consistency
admin_id = 111111
user_id = 222222
channel_id = "-100123456789"

# Create data via service methods
plan = await container.pricing.create_plan(
    name="Plan Test",
    duration_days=30,
    price=9.99,
    created_by=admin_id
)
```

**Location:**
- Fixtures in `tests/conftest.py` (shared across all tests)
- Test-specific data created in test function body
- No separate factory files - data creation done via service methods

## Coverage

**Requirements:** No specific target enforced

**View Coverage:**
```bash
# Install coverage
pip install pytest-cov

# Run with coverage
pytest tests/ --cov=bot --cov-report=html

# View report
open htmlcov/index.html
```

**Current State:** Not explicitly measured
- Focus on test completeness rather than percentage
- E2E and integration tests provide high practical coverage

## Test Types

**Unit Tests:**
- Scope: Individual service methods
- Approach: Test method in isolation with mocked dependencies
- Example: `test_create_plan()` tests PricingService.create_plan directly
- File: `tests/test_pricing_service.py` (19 tests covering PricingService)
- Setup: Single service instance, mocked bot
- Assertions: Return values, model state, database persistence

**Integration Tests:**
- Scope: Multiple services working together
- Approach: Test through ServiceContainer with real database
- Example: `test_service_container_lazy_loading()` verifies lazy loading works
- File: `tests/test_integration.py` (4 tests covering container, config, sessions, error handling)
- Setup: ServiceContainer with full session, mock bot
- Assertions: Service state after operations, data consistency across services

**E2E Tests:**
- Scope: Complete user flows from start to finish
- Approach: Simulate real user actions through service methods
- Example: `test_vip_flow_complete()` - generate token → redeem token → verify VIP active
- File: `tests/test_e2e_flows.py` (5 tests: VIP flow, Free flow, VIP expiration, token validation, prevent duplicates)
- Setup: ServiceContainer, create users/tokens, simulate background tasks
- Assertions: Final state after complete flow, side effects (email sent, user created, etc.)

**Feature Tests:**
- Scope: New feature validation
- Example: `test_generate_token_with_plan()` validates A3 deep link feature
- File: `tests/test_a3_deep_links.py` (7 tests for deep link feature)
- Setup: Similar to E2E - create plans, tokens, users
- Assertions: Feature-specific behavior (plan linking, automatic activation)

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
async def test_async_operation(mock_bot):
    """Test async database operations."""
    async with get_session() as session:
        container = ServiceContainer(session, mock_bot)

        # Await async calls
        result = await container.subscription.get_vip_subscriber(user_id)

        # Assertions work normally
        assert result is not None
```

**Error Testing:**
```python
@pytest.mark.asyncio
async def test_validation_error():
    """Test that validation raises correct error."""
    async with get_session() as session:
        service = PricingService(session)

        # Use pytest.raises for exception testing
        with pytest.raises(ValueError, match="duration must be"):
            await service.create_plan(
                name="Test",
                duration_days=-1,  # Invalid
                price=9.99,
                created_by=123456
            )
```

**Database Transaction Testing:**
```python
@pytest.mark.asyncio
async def test_persistence(mock_bot):
    """Test that changes persist in database."""
    async with get_session() as session:
        container = ServiceContainer(session, mock_bot)

        # Create data
        token = await container.subscription.generate_vip_token(
            generated_by=111111,
            duration_hours=24
        )
        token_id = token.id

    # Open new session to verify persistence
    async with get_session() as session:
        result = await session.execute(
            select(InvitationToken).where(InvitationToken.id == token_id)
        )
        persisted_token = result.scalar_one()
        assert persisted_token.id == token_id
```

**Mocking Telegram API Calls:**
```python
@pytest.mark.asyncio
async def test_channel_setup(mock_bot):
    """Test channel setup with mocked Telegram API."""
    # Setup mock return value
    mock_bot.get_chat.return_value = Mock(
        id=-100123456789,
        type="supergroup"
    )

    async with get_session() as session:
        container = ServiceContainer(session, mock_bot)

        success, msg = await container.channel.setup_vip_channel("-100123456789")

        # Verify mock was called
        mock_bot.get_chat.assert_called_once()
        assert success is True
```

**Multi-step Flow Testing:**
```python
@pytest.mark.asyncio
async def test_complete_vip_flow(mock_bot):
    """Test complete VIP flow: generate → redeem → verify."""
    async with get_session() as session:
        container = ServiceContainer(session, mock_bot)

        # Step 1: Generate token
        print("1. Generating token...")
        token = await container.subscription.generate_vip_token(
            generated_by=111111,
            duration_hours=24
        )
        assert token.used == False

        # Step 2: Redeem token
        print("2. Redeeming token...")
        success, msg, subscriber = await container.subscription.redeem_vip_token(
            token_str=token.token,
            user_id=222222
        )
        assert success == True
        assert subscriber is not None

        # Step 3: Verify VIP status
        print("3. Verifying VIP status...")
        is_vip = await container.subscription.is_vip_active(222222)
        assert is_vip == True

        print("[PASSED] Complete VIP flow")
```

## Test Execution

**Running Tests:**
```bash
# Install dependencies
pip install pytest==7.4.3 pytest-asyncio==0.21.1

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_e2e_flows.py -v

# Run specific test
pytest tests/test_e2e_flows.py::test_vip_flow_complete -v

# Run with output capture disabled (see print statements)
pytest tests/ -v -s

# Stop on first failure
pytest tests/ -x
```

**Expected Output:**
```
======================== 30 passed in 12.45s ========================
```

**Test Organization:**
- Tests are independent and can run in any order
- Autouse `db_setup` fixture ensures clean database before each test
- No shared state between tests
- Each test creates its own test data

## Pytest Configuration

**Markers:**
- `@pytest.mark.asyncio` - marks test as async (required for all async tests)

**Fixtures Available:**
- `event_loop` - pytest-asyncio event loop for async operations
- `db_setup` (autouse) - automatically initializes and cleans database before/after each test
- `mock_bot` - pre-configured mock Telegram bot with AsyncMock methods

**Auto-use Fixtures:**
- `db_setup` runs before every test automatically
- Initializes database tables
- Cleans up after test
- Ensures isolation between tests

---

*Testing analysis: 2026-01-23*
