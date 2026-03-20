# Agent Memory Index - Background Tasks Auditor

## Audit Reports
- [audit-report-2026-03-12.md](./audit-report-2026-03-12.md) - Auditoría de tasks.py y channel.py

## Code Patterns Documented
- Session factory patterns: Context manager usage in background tasks
- APScheduler configuration: max_instances, missing misfire_grace_time/coalesce
- Telegram API error handling: Specific in channel.py, generic in subscription.py
- Database transaction boundaries: Long-running transactions during API calls (anti-pattern)
- Datetime handling: datetime.utcnow() usage (legacy pattern)
- Idempotency mechanisms: Partial implementation in free queue processing

## Critical Issues Catalog
- CRITICAL-001: DB/Telegram inconsistency in VIP kicking - no tracking of failures
- CRITICAL-002: TOCTOU race condition in free request approval
