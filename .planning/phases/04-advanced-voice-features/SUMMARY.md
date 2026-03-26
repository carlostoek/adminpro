# Phase 04: Advanced Voice Features - Summary

**Phase:** 04 - Advanced Voice Features
**Status:** PLANNING COMPLETE ✅
**Plans:** 3 (04-01, 04-02, 04-03)
**Confidence:** HIGH

---

## Phase Goal

Add context-aware variation selection and voice consistency enforcement tools to LucienVoiceService. Build on completed foundation (Phase 1), admin migration (Phase 2), and user migration (Phase 3) to prevent message repetition fatigue and automate voice validation.

---

## Plans Overview

### Plan 04-01: Session Message History Service
**Wave:** 1 (Foundation)
**Status:** READY FOR EXECUTION

**Goal:** Track recent messages per user session and exclude recently-seen variants from selection pool.

**Key Deliverables:**
- `SessionMessageHistory` service with in-memory storage (dict + deque)
- Enhanced `BaseMessageProvider._choose_variant()` with session context
- ~200 bytes per active user, 5-minute TTL, no database dependency
- Prevents "Buenos días" appearing 3 times in a row

**Files:**
- `bot/services/message/session_history.py` (NEW)
- `bot/services/message/base.py` (MODIFY)
- `tests/test_session_history.py` (NEW)

**Success Metrics:**
- Memory overhead: <50KB for 100 active users
- Performance impact: <1ms per message generation
- Repetition reduction: <5% of users report repetitive messages (vs ~15% baseline)

---

### Plan 04-02: Voice Linting Pre-Commit Hook
**Wave:** 2 (Tooling - parallel with 04-03)
**Status:** READY FOR EXECUTION

**Goal:** Catch 80% of voice violations before code is committed using AST parsing.

**Key Deliverables:**
- `VoiceViolationChecker` AST visitor (stdlib ast module)
- Pre-commit hook for staged message provider files
- Detects: tutear, technical jargon, missing emoji, missing HTML
- Performance: <100ms per file, no external dependencies

**Files:**
- `bot/utils/voice_linter.py` (NEW)
- `.hooks/pre-commit` (NEW)
- `.hooks/install.sh` (NEW)
- `tests/test_voice_linter.py` (NEW)

**Success Metrics:**
- Violation detection rate: 80% of voice violations caught
- False positive rate: <10%
- Hook adoption: 100% of developers
- Performance: <500ms for typical commit

---

### Plan 04-03: Message Preview CLI Tool
**Wave:** 2 (Tooling - parallel with 04-02)
**Status:** READY FOR EXECUTION

**Goal:** Enable rapid message testing without full bot restart.

**Key Deliverables:**
- CLI tool with argparse interface
- Commands: greeting, deep-link-success, variations, list
- Display text + keyboard markup
- ~500ms execution vs ~10s bot startup

**Files:**
- `tools/preview_messages.py` (NEW)
- `README.md` (UPDATE)
- `tests/test_preview_cli.py` (NEW)

**Success Metrics:**
- Execution time: <500ms single message, <2s for 30 variations
- Usage frequency: >50% of message-related PRs
- Developer preference: >80% prefer CLI over bot restart

---

## Execution Strategy

### Wave 1: Foundation (04-01)
**Sequential execution required** - base.py modification enables session tracking for all providers.

**Tasks:**
1. Create SessionHistoryEntry dataclass
2. Implement SessionMessageHistory class
3. Enhance BaseMessageProvider._choose_variant
4. Write tests for SessionMessageHistory
5. Integration test with BaseMessageProvider

**Estimated Time:** 3-4 hours

---

### Wave 2: Tooling (04-02, 04-03)
**Parallel execution** - independent tools, can run simultaneously.

**Plan 04-02 Tasks:**
1. Create VoiceViolationChecker AST visitor
2. Create check_file() function
3. Create pre-commit hook script
4. Create git hook installation
5. Write tests for voice linter
6. Integration test with pre-commit hook

**Plan 04-03 Tasks:**
1. Create CLI entry point
2. Implement greeting preview command
3. Implement deep link success preview command
4. Implement variations preview command
5. Implement list command
6. Update README with CLI usage
7. Write tests for CLI tool

**Estimated Time:** 2-3 hours per plan (4-6 hours total parallel)

---

## Dependencies

```
04-01 (Foundation)
  ↓
04-02 (Tooling) ⟷ 04-03 (Tooling)
  (parallel execution)
```

**No dependencies between 04-02 and 04-03** - both can be executed simultaneously by different agents or in sequence.

---

## Integration Points

### With Phase 1 (Foundation)
- Extends `BaseMessageProvider._choose_variant()` method
- Uses semantic test fixtures from `conftest.py`
- Follows stateless service pattern established in Phase 1

### With Phase 2 (Admin Migration)
- Voice linter validates admin message providers (admin_vip.py, admin_free.py, admin_main.py)
- CLI tool can preview admin messages (future enhancement)

### With Phase 3 (User Migration)
- Session tracking used by user message providers (user_start.py, user_flows.py)
- CLI tool previews user messages (greeting, deep-link-success)

---

## Technical Decisions

### 1. In-Memory Session Storage (Not Database)
**Decision:** Use dict + deque with TTL, no database persistence.

**Rationale:**
- Session loss is acceptable for convenience feature
- Avoids query latency and schema changes
- ~200 bytes per user is negligible memory
- Lazy cleanup prevents background task complexity

**Tradeoff:** Users lose session context on bot restart (acceptable).

---

### 2. AST-Based Voice Linting (Not Regex or Flake8)
**Decision:** Use stdlib `ast` module for parsing.

**Rationale:**
- AST isolates string literals from comments (regex false positives)
- No external dependencies (flake8 requires install)
- Fast (<100ms per file)
- Handles edge cases (multiline strings, escaped characters)

**Tradeoff:** Only checks syntax, not semantics (acceptable for linting).

---

### 3. Pre-Commit Hook Blocks Commits (Not Warn-Only)
**Decision:** Hook returns exit code 1 to block commits with violations.

**Rationale:**
- Enforces voice rules consistently
- `--no-verify` available for edge cases
- Developer education (see violations immediately)

**Tradeoff:** May slow initial workflow (acceptable for quality gain).

---

### 4. CLI Tool Uses stdout (Not TUI or Web)
**Decision:** Simple argparse script printing to terminal.

**Rationale:**
- Fastest development time (<2 hours)
- Works in Termux environment
- No additional dependencies
- Easy to integrate with shell scripts

**Tradeoff:** Less polished than TUI (acceptable for developer tool).

---

## Risk Mitigation

### Risk 1: Session Tracking Memory Growth
**Mitigation:**
- Max 5 entries per user (deque maxlen)
- 5-minute TTL with lazy cleanup
- get_stats() method for monitoring
- Document acceptable memory overhead (<50KB for 100 users)

---

### Risk 2: Voice Linter False Positives
**Mitigation:**
- Skip short strings (<50 chars)
- Skip HTML-only strings (start with "<")
- Tutear word boundary checks ("tu " not "future")
- --no-verify bypass for edge cases
- Collect violation statistics for 30 days post-deployment

---

### Risk 3: Pre-Commit Hook Performance
**Mitigation:**
- Only check staged files (git diff --cached)
- Only check message provider files (bot/services/message/*.py)
- Target: <100ms per file
- Lazy evaluation (skip if no message files changed)

---

### Risk 4: CLI Tool Extensibility
**Mitigation:**
- Argparse subparsers for easy command addition
- Introspection for list command (automatic method discovery)
- Clear separation: command -> function -> provider method
- Document adding new commands in README

---

## Open Questions (Post-Deployment)

### User Perception Validation
**Question:** Does session context actually improve user perception?

**Plan:**
- Deploy Phase 4 with session tracking (exclude last 2 variants)
- Survey users after 2 weeks: "Have you noticed the bot repeating messages?"
- Compare to baseline from Phase 3
- If no improvement, increase exclusion to last 3 variants

---

### Voice Violation Patterns
**Question:** What voice violations actually occur in practice?

**Plan:**
- Collect pre-commit rejection statistics for 30 days
- Categorize violations by type (tutear, jargon, emoji, HTML)
- If 60%+ are "missing emoji", voice linting is working
- If top violations are unexpected, add new rules

---

### Session Persistence Need
**Question:** Should session history persist to database?

**Plan:**
- Start with in-memory only
- Monitor user feedback: "bot forgot we already talked about this"
- Only add database persistence if explicit user request
- Current design acceptable for convenience feature

---

## Success Criteria

### Phase-Level (Must Achieve All)

1. **Session Tracking Active:**
   - [ ] 100% of user-facing message methods opt-in to session context
   - [ ] Memory overhead <50KB for 100 active users
   - [ ] Performance impact <1ms per message generation

2. **Voice Linting Effective:**
   - [ ] 80% of voice violations caught before commit
   - [ ] False positive rate <10%
   - [ ] 100% of developers have hook installed

3. **CLI Tool Useful:**
   - [ ] Execution time <500ms for single message
   - [ ] Used in >50% of message-related PRs
   - [ ] >80% of developers prefer CLI over bot restart

4. **Quality Metrics:**
   - [ ] All tests passing (pytest)
   - [ ] Zero hardcoded strings in handlers (validated by grep)
   - [ ] Voice linting passes on all message providers

---

## Phase Handoff

### To Phase 5 (Future - Performance Optimization)
**Deliverables:**
- Session tracking performance metrics (get_stats())
- Voice linting performance data (timing per file)
- CLI tool execution time benchmarks

**Recommendations:**
- Profile message generation with session context
- Measure <5ms target validation
- Add session tracking to CLI preview tool

---

### To Operations (Deployment)
**Deliverables:**
- Pre-commit hook installation script (.hooks/install.sh)
- README updated with CLI usage
- Voice linter documentation (violation types, bypass)

**Recommendations:**
- Run install.sh in developer onboarding
- Monitor pre-commit rejection statistics
- Survey users 2 weeks post-deployment

---

## Metadata

**Planning Date:** 2026-01-24
**Planner:** GSD Phase Planner
**Research Complete:** Yes (04-RESEARCH.md)
**Plans Created:** 3 (04-01, 04-02, 04-03)
**Confidence:** HIGH (stdlib-only, proven patterns, no external dependencies)

**Plans Status:**
- [x] 04-01: Session Message History Service - READY
- [x] 04-02: Voice Linting Pre-Commit Hook - READY
- [x] 04-03: Message Preview CLI Tool - READY

**Next Step:** Execute Wave 1 (04-01) → Execute Wave 2 (04-02, 04-03 parallel)

---

*Phase 04 Planning Complete*
*Ready for /gsd:execute-phase*
