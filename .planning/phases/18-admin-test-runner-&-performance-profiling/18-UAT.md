---
status: diagnosed
phase: 18-admin-test-runner-&-performance-profiling
source: [18-01-SUMMARY.md, 18-02-SUMMARY.md, 18-03-SUMMARY.md, 18-04-SUMMARY.md]
started: 2026-01-30T00:00:00Z
updated: 2026-01-30T01:00:00Z
---

## Current Test

[testing complete - blocker issue requires diagnosis]

## Tests

### 1. CLI Test Runner Script Execution
expected: Running `python scripts/run_tests.py` executes pytest and displays formatted results with pass/fail counts, duration, and emojis in console output
result: issue
reported: "Ejecutar ese comando directamente no hace nada. Se queda estático, sin hacer absolutamente nada. Al presionar ctrl+c muestra traceback de asyncio CancelledError en proc.communicate()"
severity: blocker

### 2. CLI Test Runner with Coverage Flag
expected: Running `python scripts/run_tests.py --coverage` shows coverage percentage at the end of the report
result: skipped
reason: Blocked by Test 1 blocker issue - CLI runner freezes

### 3. CLI Test Runner JSON Output
expected: Running `python scripts/run_tests.py --json` outputs valid JSON with test metrics (passed, failed, errors, duration)
result: skipped
reason: Blocked by Test 1 blocker issue - CLI runner freezes

### 4. Telegram /run_tests Command Execution
expected: Admin sends /run_tests in Telegram. Bot responds with "Ejecutando tests..." status, then shows HTML formatted results with pass/fail counts and emojis
result: skipped
reason: User requested stop due to blocker issue

### 5. Telegram /run_tests smoke
expected: Admin sends /run_tests smoke. Bot executes only smoke tests and reports results
result: skipped
reason: User requested stop due to blocker issue

### 6. Telegram /run_tests coverage
expected: Admin sends /run_tests coverage. Bot shows coverage percentage with trend indicator (+/- vs previous run)
result: skipped
reason: User requested stop due to blocker issue

### 7. Telegram /test_status Command
expected: Admin sends /test_status. Bot responds with test environment status and count of available tests
result: skipped
reason: User requested stop due to blocker issue

### 8. Telegram /smoke_test Command
expected: Admin sends /smoke_test. Bot executes quick smoke tests and shows results
result: skipped
reason: User requested stop due to blocker issue

### 9. Test Report History and Trends
expected: After running tests multiple times via Telegram, /run_tests trend shows historical statistics with duration delta and coverage comparison
result: skipped
reason: User requested stop due to blocker issue

### 10. HTML Report Generation via Telegram
expected: Admin sends /run_tests html. Bot generates and sends HTML report as document attachment
result: skipped
reason: User requested stop due to blocker issue

### 11. Failure Details with File:Line Information
expected: When tests fail, Telegram report shows failed test names with file path and line number. Clicking "Ver Detalles" shows formatted error excerpts
result: skipped
reason: User requested stop due to blocker issue

### 12. CLI Profile Handler List
expected: Running `python scripts/profile_handler.py --list` displays available handlers with full Python paths
result: skipped
reason: User requested stop due to blocker issue

### 13. CLI Profile Handler Execution
expected: Running `python scripts/profile_handler.py bot.handlers.user.start.cmd_start` shows profiling results with duration, query count, and top functions
result: skipped
reason: User requested stop due to blocker issue

### 14. CLI Profile Handler HTML Output
expected: Running `python scripts/profile_handler.py bot.handlers.admin.main.cmd_admin --format=html --output=report.html` creates HTML flame graph file
result: skipped
reason: User requested stop due to blocker issue

### 15. Telegram /profile Command List
expected: Admin sends /profile in Telegram. Bot lists available handlers that can be profiled
result: skipped
reason: User requested stop due to blocker issue

### 16. Telegram /profile with Iterations
expected: Admin sends /profile admin --iterations=3. Bot profiles the admin handler 3 times and shows aggregated results
result: skipped
reason: User requested stop due to blocker issue

### 17. Telegram /profile_stats Command
expected: With PROFILE_HANDLERS=1 enabled, admin sends /profile_stats. Bot shows accumulated profiling statistics
result: skipped
reason: User requested stop due to blocker issue

### 18. SQLite to PostgreSQL Migration Script Dry Run
expected: Running `python scripts/migrate_to_postgres.py --dry-run --source sqlite:///bot.db --target postgresql+asyncpg://...` shows what would be migrated without making changes
result: skipped
reason: User requested stop due to blocker issue

### 19. SQLite to PostgreSQL Migration Validation
expected: After migration, running with --validate-only verifies row counts match between source and target databases
result: skipped
reason: User requested stop due to blocker issue

### 20. Query Analyzer N+1 Detection
expected: Running code with @detect_n_plus_one_in_service decorator logs warning when N+1 pattern detected (5+ similar queries)
result: skipped
reason: User requested stop due to blocker issue

### 21. Telegram /analyzeQueries Command
expected: Admin sends /analyzeQueries. Bot runs test operations with QueryAnalyzer and reports N+1 issues and slow queries (>100ms)
result: skipped
reason: User requested stop due to blocker issue

### 22. Eager Loading Methods in Services
expected: Using SubscriptionService.get_vip_subscriber_with_relations() loads user, token, and plan in single query without N+1
result: skipped
reason: User requested stop due to blocker issue

### 23. Database Query Logging
expected: When debug_mode=True, SQL queries are logged to console for debugging
result: skipped
reason: User requested stop due to blocker issue

### 24. Concurrent Test Execution Prevention
expected: When tests are already running, second /run_tests command shows " Tests already running" message instead of starting parallel execution
result: skipped
reason: User requested stop due to blocker issue

## Summary

total: 24
passed: 0
issues: 1
pending: 0
skipped: 23

## Gaps

- truth: "Running `python scripts/run_tests.py` executes pytest and displays formatted results with pass/fail counts, duration, and emojis in console output"
  status: failed
  reason: "User reported: Ejecutar ese comando directamente no hace nada. Se queda estático, sin hacer absolutamente nada. Al presionar ctrl+c muestra traceback de asyncio CancelledError en proc.communicate()"
  severity: blocker
  test: 1
  root_cause: "Pytest is waiting for input from stdin because the subprocess inherits parent's stdin by default. When stdin is a TTY, pytest may wait for user input (for pdb debugging or interactive features), causing indefinite hang. The proc.communicate() waits for EOF that never comes."
  artifacts:
    - path: "scripts/run_tests.py"
      line: 108-113
      issue: "Subprocess created without stdin parameter - inherits parent's stdin"
    - path: "scripts/run_tests.py"
      line: 115
      issue: "proc.communicate() waits indefinitely for EOF"
  missing:
    - "Add stdin=asyncio.subprocess.DEVNULL to create_subprocess_exec() call"
  debug_session: "agent_a74dc4c"
