# Phase 17: System Tests

**Goal:** Comprehensive test coverage for critical flows and message providers

**Status:** 🔄 In Progress (Planning Complete)

**Plans:** 4 plans

**Dependencies:** Phase 16 (Testing Infrastructure)

---

## Overview

Phase 17 builds on the testing infrastructure from Phase 16 to create comprehensive system tests. These tests verify the bot's critical user flows, menu systems, role detection, and message providers all work correctly.

## Plans

| Plan | Wave | Focus | Files Created |
|------|------|-------|---------------|
| 17-01 | 1 | System startup and configuration | `test_startup.py`, `test_configuration.py`, `test_health.py` |
| 17-02 | 2 | Menu system (Admin/VIP/Free) with FSM | `test_admin_menu.py`, `test_role_menu_routing.py`, `test_vip_free_menus.py`, `test_fsm_states.py` |
| 17-03 | 2 | Role detection and user management | `test_role_detection.py`, `test_user_management.py`, `test_role_change_audit.py` |
| 17-04 | 3 | VIP/Free flows and message providers | `test_vip_tokens.py`, `test_vip_ritual_flow.py`, `test_free_flow.py`, `test_message_providers.py` |

## Success Criteria

1. ✅ Test de arranque verifica que bot inicia, DB conecta, y servicios cargan
2. ✅ Tests de menú principal Admin cubren todos los comandos y callbacks
3. ✅ Tests de menú VIP y Free verifican navegación y rol routing
4. ✅ Test de detección de roles valida prioridad Admin > VIP > Free
5. ✅ Tests de flujos VIP/Free verifican tokens, entrada ritual, y aprobación Free

## Requirements Coverage

| Requirement | Status | Plan |
|-------------|--------|------|
| TESTSYS-01: System startup test | ✅ 17-01 | test_startup.py |
| TESTSYS-02: Admin menu handlers | ✅ 17-02 | test_admin_menu.py |
| TESTSYS-03: VIP menu handlers | ✅ 17-02 | test_vip_free_menus.py |
| TESTSYS-04: Free menu handlers | ✅ 17-02 | test_vip_free_menus.py |
| TESTSYS-05: Role detection priority | ✅ 17-03 | test_role_detection.py |
| TESTSYS-06: Free channel entry flow | ✅ 17-04 | test_free_flow.py |
| TESTSYS-07: VIP token generation | ✅ 17-04 | test_vip_tokens.py |
| TESTSYS-08: VIP ritualized entry (3 stages) | ✅ 17-04 | test_vip_ritual_flow.py |
| TESTSYS-09: Configuration management | ✅ 17-01 | test_configuration.py |
| TESTSYS-10: Message providers (13 providers) | ✅ 17-04 | test_message_providers.py |

## Test Files Created

### System Startup (17-01)
- `tests/test_system/test_startup.py` - Database init, ServiceContainer loading, BotConfig seeding, background tasks
- `tests/test_system/test_configuration.py` - Config validation, setters, summary, reset
- `tests/test_system/test_health.py` - Health check endpoint, database status

### Menu System (17-02)
- `tests/test_system/test_admin_menu.py` - Admin /admin command, callbacks, content submenu
- `tests/test_system/test_role_menu_routing.py` - VIP/Free menu routing based on role
- `tests/test_system/test_vip_free_menus.py` - VIP subscription info, Free social media, navigation
- `tests/test_system/test_fsm_states.py` - FSM state entry/exit, persistence, callback validation

### Role Detection (17-03)
- `tests/test_system/test_role_detection.py` - Priority rules, stateless detection, VIP channel vs subscription
- `tests/test_system/test_user_management.py` - User info, role changes, block/unblock, kick, pagination
- `tests/test_system/test_role_change_audit.py` - Audit log creation, history retrieval

### User Flows (17-04)
- `tests/test_system/test_vip_tokens.py` - Token generation, validation, expiry, redemption, double-redemption blocking
- `tests/test_system/test_vip_ritual_flow.py` - 3-stage ritual (confirmation → alignment → access), complete flow
- `tests/test_system/test_free_flow.py` - Free requests, queue processing, duplicate prevention, invite links
- `tests/test_system/test_message_providers.py` - All 13 providers, HTML validation, session-aware variations

### Fixtures (New)
- `tests/fixtures/telegram.py` - Telegram object fixtures (admin_user, vip_user, free_user, callbacks)

## Key Test Patterns

### Service Testing
```python
async def test_service_method(test_session, mock_bot):
    service = ServiceClass(test_session, mock_bot)
    result = await service.method()
    assert result is not None
```

### Handler Testing
```python
async def test_handler(message_or_callback, test_session, mock_bot):
    message_or_callback.answer = AsyncMock()
    await handler_function(message_or_callback, test_session)
    message_or_callback.answer.assert_called()
```

### Message Provider Testing
```python
async def test_provider(container):
    session_history = container.session_history
    text, keyboard = container.message.provider.method(
        param=value,
        session_history=session_history
    )
    assert text is not None
    assert keyboard is not None
```

### FSM Testing
```python
async def test_fsm_state(callback, test_session, mock_bot):
    fsm_state = FSMContext(storage=mock_bot.dispatcher.storage, key=callback.from_user.id)
    await handler(callback, test_session, mock_bot)
    current_state = await fsm_state.get_state()
    assert current_state == ExpectedState
```

## Anti-Patterns Avoided

1. ❌ Don't mock the database - Use test_db fixture for real DB operations
2. ❌ Don't test implementation details - Test observable behavior
3. ❌ Don't test exact message text - Test that providers return valid content
4. ❌ Don't skip keyboard validation - Verify buttons are present
5. ❌ Don't ignore error cases - Test both success and failure scenarios
6. ❌ Don't forget session refresh - Use session.refresh() after updates
7. ❌ Don't skip FSM state validation - Verify state changes

## Expected Outcomes

- **50+ new system tests** covering all critical flows
- **Coverage increase**: Target >75% for handlers, services, and message providers
- **Fast execution**: All tests complete in <60 seconds
- **Reliable**: No flaky tests, all use in-memory DB with proper isolation

## Next Steps

After Phase 17 completion:
1. Move to Phase 18 (Admin Test Runner & Performance Profiling)
2. Implement `/run_tests` script for CLI and Telegram
3. Integrate pyinstrument for profiling
4. Create SQLite → PostgreSQL migration script

---

**Phase Leader:** Claude (gsd-planner)
**Last Updated:** 2026-01-29
**Status:** ✅ Planning Complete
