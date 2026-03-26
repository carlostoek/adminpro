# Phase 16: Testing Infrastructure

## Goal
Establish a robust testing infrastructure with pytest-asyncio, in-memory database fixtures, complete test isolation, and coverage reporting.

## Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| TESTINF-01 | pytest-asyncio configurado con async_mode=auto | High |
| TESTINF-02 | Fixtures creados (test_db, mock_bot, container) | High |
| TESTINF-03 | Base de datos en memoria para tests (sqlite+aiosqlite:///:memory:) | High |
| TESTINF-04 | Aislamiento de tests (cleanup entre tests) | High |
| TESTINF-05 | Configuración de coverage reporting | Medium |

## Success Criteria

1. pytest-asyncio configurado con async_mode=auto
2. Fixtures creados (test_db, mock_bot, container) para todos los tests
3. Base de datos en memoria se crea y limpia automáticamente entre tests
4. Tests están aislados (cleanup completo entre tests)
5. Coverage reporting configurado para medir cobertura de código

## Plans

| Task | Description | Wave | Depends On | File |
|------|-------------|------|------------|------|
| 16-01 | pytest-asyncio configuration | 1 | - | [16-01-PLAN.md](./16-01-PLAN.md) |
| 16-02 | Core test fixtures | 1 | 16-01 | [16-02-PLAN.md](./16-02-PLAN.md) |
| 16-03 | In-memory database | 2 | 16-02 | [16-03-PLAN.md](./16-03-PLAN.md) |
| 16-04 | Test isolation | 2 | 16-03 | [16-04-PLAN.md](./16-04-PLAN.md) |
| 16-05 | Coverage reporting | 1 | 16-01 | [16-05-PLAN.md](./16-05-PLAN.md) |

## Wave Execution

### Wave 1 (Parallel)
- 16-01: pytest-asyncio configuration
- 16-02: Core test fixtures
- 16-05: Coverage reporting

### Wave 2 (Sequential)
- 16-03: In-memory database (depends on 16-02)
- 16-04: Test isolation (depends on 16-03)

## Key Technical Decisions

1. **async_mode=auto**: Eliminates need for @pytest.mark.asyncio decorator
2. **In-memory SQLite**: Fast, isolated tests without file I/O
3. **Transaction rollback**: Ensures complete isolation between tests
4. **Fixture-based architecture**: Reusable, composable test dependencies
5. **pytest-cov**: Industry-standard coverage reporting

## Files to be Modified

```
/
├── pytest.ini                    # NEW: pytest configuration
├── .coveragerc                   # NEW: coverage configuration
├── requirements.txt              # MODIFY: add pytest-cov
├── tests/
│   ├── conftest.py              # MODIFY: modern pytest-asyncio
│   ├── fixtures/                # NEW: fixture modules
│   │   ├── __init__.py
│   │   ├── database.py          # test_db, test_session
│   │   └── services.py          # mock_bot, container
│   └── test_infrastructure/     # NEW: infrastructure tests
│       ├── test_database.py
│       ├── test_isolation.py
│       └── test_cleanup.py
└── scripts/
    └── coverage.py              # NEW: coverage helper
```

## Verification Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=bot --cov-report=term

# Run with HTML coverage report
pytest --cov=bot --cov-report=html

# Run infrastructure tests only
pytest tests/test_infrastructure/

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_integration.py -v
```
