# Original User Request

## 2026-07-13T16:15:43Z

Your identity is teamwork_preview_orchestrator (spawning as self).
Your working directory is d:\workspace\bnb_guessing\.agents\e2e_testing_orchestrator.
You are the E2E Testing Track Orchestrator for the BnB Family Match Score Betting System.

Objective:
Design and implement a comprehensive opaque-box E2E test suite derived from the user requirements in ORIGINAL_REQUEST.md. The test suite must be fully independent of the implementation design, and verify the app's functionality as an end-user.

Scope boundaries:
- Do NOT write or modify the product source code (under src/). Only write tests, test helpers, test runner scripts, and your own metadata.
- Do NOT run tests against a mock UI if possible; use a real PyQt6 GUI test approach (such as using pytest-qt to interact with elements or programmatic widget access) or whatever appropriate testing harness you build.
- Do NOT place test files inside the .agents/ folder. Only coordinate metadata goes there.

Input information:
- Verbatim user request is at d:\workspace\bnb_guessing\.agents\orchestrator\ORIGINAL_REQUEST.md.
- Global project plan is at d:\workspace\bnb_guessing\.agents\orchestrator\PROJECT.md.

Output requirements:
- Create TEST_INFRA.md inside d:\workspace\bnb_guessing\.agents\e2e_testing_orchestrator/ detailing the test architecture, features, and methodology.
- Create the test files (e.g. under a tests/ or e2e_tests/ directory).
- Once the test suite is fully designed and all test cases are written (even if some fail initially due to lack of implementation), publish TEST_READY.md inside d:\workspace\bnb_guessing\.agents\e2e_testing_orchestrator/.

Completion criteria:
- Minimum test thresholds met:
  - Tier 1: Feature Coverage (>= 5 per feature)
  - Tier 2: Boundary & Corner Cases (>= 5 per feature)
  - Tier 3: Cross-Feature Combinations (pairwise coverage of major feature interactions)
  - Tier 4: Real-World Application Scenarios (>= 5 scenarios)
  - Total minimum test cases: ~11 * N + max(5, N/2).
- TEST_READY.md and TEST_INFRA.md are published and accurate.
- When done, report back to me (ccdc47c8-7e28-456f-b602-58e742b90af2) with a handoff report (handoff.md).
