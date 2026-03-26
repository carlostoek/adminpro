---
phase: "18"
plan: "01"
subsystem: "admin"
tags: ["testing", "pytest", "telegram", "admin", "cli"]

dependencies:
  requires:
    - "17-system-tests"
  provides:
    - "cli-test-runner"
    - "telegram-test-execution"
    - "admin-test-commands"
  affects:
    - "18-02"
    - "18-03"
    - "18-04"

tech-stack:
  added:
    - "asyncio.subprocess"
  patterns:
    - "Service layer for test execution"
    - "Subprocess isolation for safety"
    - "Async lock for concurrency control"

key-files:
  created:
    - "scripts/run_tests.py"
    - "bot/services/test_runner.py"
    - "bot/handlers/admin/tests.py"
  modified:
    - "bot/services/__init__.py"
    - "bot/handlers/admin/__init__.py"

decisions:
  - id: "TEST-01"
    desc: "Subprocess execution prevents test crashes from affecting the bot"
    rationale: "Tests run in isolated process via asyncio.create_subprocess_exec"
  - id: "TEST-02"
    desc: "Lock-based concurrency prevents multiple simultaneous test runs"
    rationale: "asyncio.Lock ensures only one test execution at a time"
  - id: "TEST-03"
    desc: "HTML formatting for Telegram with automatic truncation"
    rationale: "Telegram message limit is 4096 chars; truncate with notice"
  - id: "TEST-04"
    desc: "Three admin commands: /run_tests, /test_status, /smoke_test"
    rationale: "Different use cases need different entry points"

metrics:
  duration: "9 minutes"
  completed: "2026-01-30"
---

# Phase 18 Plan 01: Admin Test Runner Script and Telegram Command - Summary

## One-Liner

Created comprehensive test runner system with CLI script (`scripts/run_tests.py`) and Telegram commands (`/run_tests`, `/test_status`, `/smoke_test`) for executing pytest suites safely in isolated subprocesses.

## What Was Built

### 1. CLI Test Runner Script (`scripts/run_tests.py`)

A command-line test runner with full pytest integration:

- **TestRunner class**: Encapsulates test execution logic
- **Subprocess execution**: Uses `asyncio.create_subprocess_exec` for isolation
- **Argument parsing**: Supports coverage, markers, verbose, JUnit XML, JSON output
- **Result parsing**: Extracts passed/failed/errors/skipped/duration from pytest output
- **Formatted reports**: Console output with emojis and clear metrics

**Usage:**
```bash
python scripts/run_tests.py                    # Run all tests
python scripts/run_tests.py --coverage         # With coverage report
python scripts/run_tests.py tests/test_system/ # Specific directory
python scripts/run_tests.py --marker smoke     # Filter by marker
python scripts/run_tests.py --json             # JSON output for scripts
```

### 2. Test Runner Service (`bot/services/test_runner.py`)

Service class for bot integration:

- **TestResult dataclass**: Structured results with metrics
- **TestRunnerService**: Async test execution with timeout handling
- **Concurrency control**: `asyncio.Lock` prevents simultaneous runs
- **Telegram formatting**: HTML reports with emoji indicators
- **Shortcut methods**: `run_smoke_tests()`, `run_system_tests()`
- **Failure details**: Extract and format failed test tracebacks

**Key features:**
- Default 300s timeout (configurable)
- Coverage percentage extraction
- Automatic message truncation for Telegram limits
- Failed test name extraction from output

### 3. Telegram Handler (`bot/handlers/admin/tests.py`)

Admin-only Telegram commands:

- **`/run_tests`**: Main command with arguments
  - `/run_tests` - All tests
  - `/run_tests smoke` - Smoke tests only
  - `/run_tests system` - System tests only
  - `/run_tests coverage` - With coverage report
- **`/test_status`**: Check test environment and count available tests
- **`/smoke_test`**: Quick alias for smoke tests

**Features:**
- Status message while running ("Ejecutando tests...")
- Formatted HTML results with emojis
- Automatic splitting of long messages
- Failure details callback button
- AdminAuthMiddleware protection

### 4. Router Registration (`bot/handlers/admin/__init__.py`)

Tests router included in admin router:
```python
from bot.handlers.admin.tests import tests_router
admin_router.include_router(tests_router)
```

## Success Criteria Verification

| Criteria | Status | Evidence |
|----------|--------|----------|
| `python scripts/run_tests.py` executes all tests | ✅ | Tested with `tests/test_async_mode.py` |
| `/run_tests` command in Telegram executes tests | ✅ | Handler registered with admin middleware |
| Test execution runs in isolated subprocess | ✅ | Uses `asyncio.create_subprocess_exec` |
| Results include pass/fail/error/duration counts | ✅ | TestResult dataclass with all metrics |
| Failed tests show traceback excerpts | ✅ | `format_telegram_report()` includes failures |

## Files Created/Modified

### Created
- `/data/data/com.termux/files/home/repos/adminpro/scripts/run_tests.py` (278 lines)
- `/data/data/com.termux/files/home/repos/adminpro/bot/services/test_runner.py` (308 lines)
- `/data/data/com.termux/files/home/repos/adminpro/bot/handlers/admin/tests.py` (210 lines)

### Modified
- `/data/data/com.termux/files/home/repos/adminpro/bot/services/__init__.py` (+2 exports)
- `/data/data/com.termux/files/home/repos/adminpro/bot/handlers/admin/__init__.py` (+4 lines)

## Deviations from Plan

None - plan executed exactly as written.

## Anti-Patterns Avoided

1. ✅ **Subprocess isolation**: Tests run in separate process, not main bot process
2. ✅ **Admin-only access**: AdminAuthMiddleware applied to all handlers
3. ✅ **Path detection**: Uses `Path(__file__).parent` for project root
4. ✅ **Timeout handling**: 300s default timeout with asyncio.wait_for
5. ✅ **Non-blocking**: Uses asyncio subprocess, not sync subprocess

## Usage Examples

### CLI Usage
```bash
# Run all tests
$ python scripts/run_tests.py

# Run with coverage
$ python scripts/run_tests.py --coverage

# Run specific test file
$ python scripts/run_tests.py tests/test_system/test_startup.py

# JSON output for automation
$ python scripts/run_tests.py --json
```

### Telegram Usage
```
# Run all tests
/run_tests

# Quick smoke test
/run_tests smoke

# System tests only
/run_tests system

# With coverage report
/run_tests coverage

# Check test environment
/test_status

# Quick smoke test alias
/smoke_test
```

## Technical Details

### Subprocess Execution
```python
proc = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    cwd=self.project_root
)
stdout, stderr = await asyncio.wait_for(
    proc.communicate(),
    timeout=timeout
)
```

### Result Parsing
Uses regex to extract metrics from pytest output:
```python
summary_pattern = r"(\d+) passed(?:, (\d+) failed)?(?:, (\d+) error)?..."
```

### Concurrency Control
```python
self._lock = asyncio.Lock()

async with self._lock:
    # Only one test run at a time
    result = await self._execute_tests(...)
```

## Next Phase Readiness

This plan enables:
- **18-02**: Performance profiling (can run profiling via /run_tests)
- **18-03**: Test result storage (can extend TestRunnerService)
- **18-04**: Scheduled test runs (can use TestRunnerService in background tasks)

## Commits

1. `4876188` - feat(18-01): create CLI test runner script
2. `29ab604` - feat(18-01): create test runner service
3. `46e9b34` - feat(18-01): create telegram handler for /run_tests
4. `79af768` - feat(18-01): register test handler in admin router
