---
phase: 27-security-audit-fixes
plan: 02
type: execute
subsystem: security
wave: 1
tags: [security, race-condition, sqlite, atomic-updates]
dependency_graph:
  requires: ["27-01"]
  provides: ["27-03", "27-04"]
  affects: ["bot/services/subscription.py", "bot/database/models.py", "bot/background/tasks.py"]
tech_stack:
  added: []
  patterns: ["UPDATE with rowcount check", "SQLite-compatible atomic operations", "Batch processing with LIMIT"]
key_files:
  created: []
  modified:
    - bot/database/models.py
    - bot/services/subscription.py
    - bot/background/tasks.py
decisions:
  - "Use UPDATE with rowcount check instead of SELECT FOR UPDATE (SQLite-compatible)"
  - "Use timestamp (kicked_from_channel_at) instead of boolean for tracking"
  - "Batch processing with LIMIT 100 to prevent memory issues"
  - "Mark as processed BEFORE calling Telegram API to prevent double-processing"
metrics:
  duration_seconds: 414
  completed_date: "2026-03-17T07:29:32Z"
  tasks_completed: 4
  commits: 4
  files_modified: 3
  lines_added: 148
  lines_removed: 61
---

# Phase 27 Plan 02: Race Condition Fixes Summary

## Overview

Fixed critical race conditions C-003 and C-004 in subscription.py that caused double-processing of Free requests and inconsistent DB/Telegram state for VIP expirations.

## Critical Issues Fixed

### C-003: Inconsistencia DB/Telegram en kick_expired_vip_from_channel

**Problem:** Users expired but not banned become orphaned - in DB as expired but still in channel.

**Solution:**
- Added `kicked_from_channel_at` timestamp field to VIPSubscriber model
- Changed return type from `int` to `Tuple[int, int, int]` for detailed monitoring
- Process only VIPs not yet kicked (`kicked_from_channel_at IS NULL`)
- Handle "user not found" as success (already not in channel)
- Failed kicks remain in queue for retry

### C-004: Race Condition en approve_ready_free_requests

**Problem:** Same request can be processed by multiple concurrent workers.

**Solution:**
- Replaced SELECT-then-process pattern with atomic UPDATE
- Use `UPDATE ... WHERE processed = False` with rowcount check
- SQLite-compatible (no SKIP LOCKED needed)
- Mark as processed BEFORE calling Telegram API
- Batch processing with LIMIT 100

## Changes Made

### Task 1: Add kicked_from_channel_at Field
**Files:** `bot/database/models.py`
- Added `kicked_from_channel_at` column (DateTime, nullable)
- Added `idx_vip_expired_not_kicked` index for efficient retry queries

### Task 2: Fix approve_ready_free_requests Race Condition
**Files:** `bot/services/subscription.py`
- Replaced vulnerable SELECT-then-process pattern
- Added atomic UPDATE with rowcount check
- Added race condition detection logging
- Separated DB operations from Telegram API calls

### Task 3: Fix kick_expired_vip_from_channel Inconsistency
**Files:** `bot/services/subscription.py`
- Changed return type to Tuple[int, int, int]
- Added kicked_from_channel_at tracking
- Added batch processing with LIMIT 100
- Handle partial failures for retry logic

### Task 4: Update Background Tasks
**Files:** `bot/background/tasks.py`
- Updated expire_and_kick_vip_subscribers for new return signature
- Added detailed logging for kick results

## Verification

- [x] C-003 fixed: kick_expired_vip_from_channel tracks kicked_from_channel_at
- [x] C-004 fixed: approve_ready_free_requests uses UPDATE with rowcount check
- [x] No PostgreSQL-specific features used (no SKIP LOCKED)
- [x] kicked_from_channel_at field exists in VIPSubscriber model
- [x] Batch processing with LIMIT 100 implemented
- [x] Background tasks updated for new signatures
- [x] No infinite retry loops on Telegram API failures

## Commits

| Commit | Description |
|--------|-------------|
| 011d256 | feat(27-02): add kicked_from_channel_at tracking field to VIPSubscriber |
| f2e418a | fix(27-02): fix race condition in approve_ready_free_requests (C-004) |
| 24b7de5 | fix(27-02): fix kick_expired_vip_from_channel inconsistency (C-003) |
| 33e94bc | chore(27-02): update background tasks for new return signatures |

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- [x] All modified files exist and contain expected changes
- [x] All commits exist in git history
- [x] No syntax errors in modified Python files
- [x] SQLite-compatible patterns used throughout
