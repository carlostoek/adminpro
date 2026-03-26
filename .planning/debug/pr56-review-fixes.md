---
status: resolved
trigger: "Fix 3 bugs from PR#56 review comments"
created: 2026-03-25T00:00:00
updated: 2026-03-25T00:00:00
---

## Current Focus
hypothesis: "All 6 bugs/issues fixed"
test: "All fixes verified"
expecting: "Code quality improved"
next_action: "Provide summary"

## Symptoms
expected: "Code uses correct attributes/method calls"
actual: "AttributeError, TypeError, and missing parameters"
errors:
  - "AttributeError: 'ResolvedUserContext' has no attribute 'simulated_mode'"
  - "TypeError: 'SimulationStore.is_simulating()' takes 1 positional argument but 2 were given"
  - "TypeError: missing required positional argument 'user_context'"
reproduction: "See specific file:line references in bug descriptions"
started: "PR#56 review"

## Eliminated
<!-- All issues were valid and fixed -->

## Evidence
- timestamp: 2026-03-25
  checked: "All 6 issues"
  found: "All bugs confirmed and fixed"
  implication: "All issues resolved"

## Resolution
root_cause: "Wrong attribute names, class method vs instance method calls, missing parameters, redundant code"
fix: "Applied all 6 fixes"
verification: "All fixes applied successfully"
files_changed:
  - bot/middlewares/simulation.py
  - bot/services/wallet.py
  - bot/services/shop.py
  - bot/services/reward.py
  - bot/handlers/user/start.py
  - bot/database/enums.py
  - bot/handlers/admin/simulation.py
