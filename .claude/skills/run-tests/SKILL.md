---
name: run-tests
description: Run appropriate pytest tests based on modified files. Use this skill when the user asks to run tests, check if tests pass, or run specific test categories. Auto-detects which tests to run based on changed files (handlers → handler tests + e2e, services → service tests + integration, database → infrastructure tests). Supports unit, integration, e2e, and file-specific test scopes.
---

# run-tests

Smart test runner that selects appropriate tests based on context.

## When to use

- User asks to "run tests" or "test this"
- User mentions "pytest" or "run the tests"
- User wants to verify changes don't break tests
- User needs to run specific test categories
- User modified files and wants to run relevant tests

## Arguments

- `scope`: Test scope to run
  - `auto` (default): Detect based on modified files
  - `unit`: Run unit tests only
  - `integration`: Run integration tests
  - `e2e`: Run end-to-end tests
  - `file`: Run specific test file
- `file`: Specific test file path (required when scope=file)
- `verbose`: Show detailed output - `true` (default) or `false`
- `coverage`: Generate coverage report - `true` or `false`

## Auto-detection logic

When `scope=auto`, the skill detects modified files and runs:

| Modified files | Tests triggered |
|---------------|-----------------|
| `bot/handlers/*` | `tests/handlers/` + `tests/test_e2e_*.py` |
| `bot/services/*` | `tests/services/` + `tests/test_integration*.py` |
| `bot/database/*` | `tests/test_infrastructure/` |
| `bot/middlewares/*` | `tests/test_middlewares.py` |
| `bot/utils/*` | `tests/unit/` |
| `config.py`, `main.py` | All tests |

## Test commands

### Default (auto-detect)
```bash
pytest -v --tb=short
```

### Unit tests only
```bash
pytest tests/ -v --tb=short -m unit
```

### Integration tests
```bash
pytest tests/ -v --tb=short -m integration
```

### E2E tests
```bash
pytest tests/ -v --tb=short -m e2e
```

### Specific file
```bash
pytest tests/test_wallet.py -v --tb=short
```

### With coverage
```bash
pytest tests/ -v --tb=short --cov=bot --cov-report=term-missing
```

## Test markers

The project uses pytest markers defined in `pytest.ini`:

- `@pytest.mark.unit`: Fast, isolated tests (no DB, no external APIs)
- `@pytest.mark.integration`: Tests with database and service integration
- `@pytest.mark.e2e`: End-to-end flow tests
- `@pytest.mark.slow`: Tests that take >5 seconds (can skip with `-m "not slow"`)

## Output interpretation

### Success
```
============================= test session starts ==============================
collected 42 items

tests/test_handler.py::test_success PASSED                               [100%]

============================== 42 passed in 3.21s ==============================
```

### Failure
```
=========================== short test summary info ============================
FAILED tests/test_handler.py::test_failure - AssertionError: expected 200
============================== 1 failed, 41 passed =============================
```

### Coverage report
```
----------- coverage: platform linux, python 3.11 -----------
Name                           Stmts   Miss  Cover
--------------------------------------------------
bot/__init__.py                    0      0   100%
bot/handlers/admin/vip.py         45      5    89%
--------------------------------------------------
TOTAL                            523     48    91%
```

## Usage examples

```
/run-tests
/run-tests scope=auto
/run-tests scope=unit
/run-tests scope=integration
/run-tests scope=file file=tests/test_wallet.py
/run-tests scope=e2e verbose=true
/run-tests scope=unit coverage=true
```

Or just ask: "run the tests" or "test my changes"
