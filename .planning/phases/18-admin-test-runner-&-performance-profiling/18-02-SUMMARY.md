---
phase: "18"
plan: "18-02"
subsystem: "admin"
tags: ["testing", "coverage", "reporting", "telegram"]
dependencies:
  requires: ["18-01"]
  provides: ["test-reporting", "coverage-integration"]
  affects: []
tech-stack:
  added: []
  patterns: ["dataclasses", "async-file-ops", "html-generation"]
key-files:
  created:
    - bot/utils/test_report.py
  modified:
    - bot/services/test_runner.py
    - bot/handlers/admin/tests.py
decisions:
  - "Use async file operations for history to avoid blocking bot"
  - "Cache last test result in memory for failure detail retrieval"
  - "Generate HTML reports on-demand only (not by default)"
  - "Sanitize file paths to hide sensitive project structure"
  - "Store lightweight TestRunRecord in history (no full stdout)"
metrics:
  duration: "25 min"
  completed: "2026-01-30"
---

# Phase 18 Plan 02: Test Reporting with Coverage and Detailed Results

## Summary

Enhanced the test runner system with comprehensive reporting capabilities including coverage analysis, detailed failure reports with file:line information, historical tracking with trend comparison, and formatted output suitable for Telegram messages. The system now provides actionable intelligence for administrators through multiple output formats.

## One-Liner

Test reporting with coverage integration, trend analysis, and multi-format output (Telegram HTML, console, JSON, HTML reports).

## What Was Built

### 1. Enhanced TestResult Dataclass (bot/services/test_runner.py)

Extended the basic TestResult with comprehensive metadata:

- **FailedTestInfo**: New dataclass capturing test name, file path, line number, error type, and error message
- **Coverage by module**: Dictionary mapping module names to coverage percentages
- **Git tracking**: Automatic capture of commit hash and branch
- **Timestamp**: ISO format UTC timestamp for each test run
- **Warnings**: List of pytest warnings collected during execution

### 2. Test Report Utility Module (bot/utils/test_report.py)

Created a comprehensive reporting module with three main components:

**TestRunRecord**: Lightweight dataclass for historical persistence
- Captures essential metrics without full stdout (keeps history small)
- Conversion methods to/from TestResult and dict for JSON serialization

**TestReportHistory**: Async history management
- JSON file persistence with async I/O (non-blocking)
- Trend comparison against previous runs (duration delta, coverage delta)
- Statistics calculation (success rate, averages)
- Automatic history rotation (max 100 entries)

**TestReportFormatter**: Multi-format output generation
- `format_telegram()`: HTML formatted for Telegram with emojis and code blocks
- `format_console()`: Plain text for terminal output
- `format_json()`: Machine-readable JSON for integrations
- `generate_html_report()`: Full styled HTML report with CSS

### 3. Enhanced TestRunnerService (bot/services/test_runner.py)

Added sophisticated reporting integration:

- `run_tests_with_report()`: New method returning (TestResult, report_metadata)
  - Automatic history recording (non-blocking via create_task)
  - Optional HTML report generation
  - Trend comparison data included
- `get_test_statistics()`: Access to historical statistics
- Enhanced parsing: Extracts coverage by module, failed test details, warnings
- Git integration: Automatically captures version info

### 4. Enhanced Telegram Handler (bot/handlers/admin/tests.py)

Updated admin commands with new capabilities:

- `/run_tests trend`: Shows historical statistics and trends
- `/run_tests html`: Generates and sends HTML report as document
- `/run_tests coverage`: Now shows coverage trends vs previous runs
- Failure details: Cached in memory, accessible via callback button
- Smart message splitting: Preserves line boundaries when splitting long reports
- Enhanced formatting: Git branch/commit info, trend indicators (🟢🔴⚪)

## Key Features

### Coverage Integration
- Coverage percentage displayed with trend indicator (+/- vs previous run)
- Per-module coverage breakdown (stored in TestResult)
- Visual coverage bar in HTML reports (color-coded: red <50%, yellow <80%, green >=80%)

### Failure Details
- File:line information extracted from pytest output
- Error type classification (AssertionError, ValueError, etc.)
- Formatted excerpts in Telegram (no raw tracebacks)
- Cached in memory for post-run detail viewing

### Historical Tracking
- JSON persistence in `.test_history.json`
- Trend comparison (duration delta, coverage delta, failed count delta)
- Success rate calculation over time
- Non-blocking save operations (asyncio.create_task)

### Multi-Format Output
- **Telegram**: HTML with emojis, code blocks, bold text
- **Console**: Plain text for terminal viewing
- **JSON**: Machine-readable for external integrations
- **HTML**: Full styled report with CSS, suitable for sharing

## Anti-Patterns Avoided

1. **No full stdout in history**: TestRunRecord stores only metadata, keeping history file small
2. **No HTML by default**: HTML generation is opt-in via `generate_html=True`
3. **No raw tracebacks in Telegram**: Error messages are formatted and truncated appropriately
4. **Non-blocking history**: Uses `asyncio.create_task()` to avoid I/O blocking
5. **Path sanitization**: Removes project root from file paths in reports

## Commands Reference

| Command | Description |
|---------|-------------|
| `/run_tests` | Execute all tests with enhanced reporting |
| `/run_tests smoke` | Execute smoke tests only |
| `/run_tests system` | Execute system tests only |
| `/run_tests coverage` | Execute with coverage analysis |
| `/run_tests html` | Generate and send HTML report |
| `/run_tests trend` | Show historical statistics |
| `/smoke_test` | Quick smoke test alias |
| `/test_status` | Show test system status |

## Files Changed

```
bot/services/test_runner.py    (+137 lines)
  - Added FailedTestInfo dataclass
  - Extended TestResult with coverage, git, timestamp
  - Added _parse_failed_tests() for detailed extraction
  - Added _get_git_info() for version tracking
  - Added run_tests_with_report() with history integration
  - Added get_test_statistics()

bot/utils/test_report.py       (+606 lines, new file)
  - TestRunRecord dataclass
  - TestReportHistory class with async JSON persistence
  - TestReportFormatter with 4 output formats
  - Trend comparison and statistics calculation

bot/handlers/admin/tests.py    (+201 lines, -25 lines)
  - Added _last_test_result global cache
  - Updated cmd_run_tests() with enhanced reporting
  - Added _send_report_in_parts() helper
  - Added _show_test_trends() command handler
  - Updated callback_show_failures() with cache
  - Updated cmd_smoke_test() with trends
```

## Testing

The implementation was validated with:
- Syntax verification: `python -m py_compile` on all modified files
- Import verification: All modules import successfully
- Type consistency: Dataclass field types are consistent

## Integration Points

- **TestRunnerService** now depends on **TestReportFormatter** and **TestReportHistory**
- **Telegram handler** uses the enhanced service methods
- **History file** stored at project root: `.test_history.json`
- **HTML reports** stored with timestamp: `test_report_YYYYMMDD_HHMMSS.html`

## Next Steps

This plan completes the test reporting infrastructure. The system is ready for:
- Performance profiling integration (Plan 18-03)
- CI/CD integration for automated test reporting
- Alerting based on coverage thresholds or failure rates
