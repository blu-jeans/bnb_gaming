# BRIEFING — 2026-07-13T16:15:43+08:00

## Mission
Design and implement a comprehensive opaque-box E2E test suite for the BnB Family Match Score Betting System.

## 🔒 My Identity
- Archetype: teamwork_preview_orchestrator
- Roles: orchestrator, user_liaison, human_reporter, successor
- Working directory: d:\workspace\bnb_guessing\.agents\e2e_testing_orchestrator
- Original parent: Project Orchestrator
- Original parent conversation ID: ccdc47c8-7e28-456f-b602-58e742b90af2

## 🔒 My Workflow
- **Pattern**: Project Pattern (E2E Testing Track)
- **Scope document**: d:\workspace\bnb_guessing\.agents\e2e_testing_orchestrator\TEST_INFRA.md
1. **Decompose**: Decompose the E2E testing requirements into feature blocks and map them to the 4-tier test architecture.
2. **Dispatch & Execute** (pick ONE):
   - **Delegate (sub-orchestrator)**: Spawn a subagent to research/explore and implement the E2E tests.
3. **On failure** (in this order):
   - Retry: nudge stuck agent or re-send task
   - Replace: spawn fresh agent with partial progress
   - Skip: proceed without (only if non-critical)
   - Redistribute: split stuck agent's remaining work
   - Redesign: re-partition decomposition
   - Escalate: report to parent (sub-orchestrators only, last resort)
4. **Succession**: Self-succeed at 16 spawns. Write handoff.md, spawn successor, exit.
- **Work items**:
  1. Initialize TEST_INFRA.md [done]
  2. Implement E2E test suite [done]
  3. Verify test files statically (no executions allowed) [done]
  4. Publish TEST_READY.md [done]
- **Current phase**: 4
- **Current focus**: Complete

## 🔒 Key Constraints
- Do NOT write or modify product source code under `src/`.
- Do NOT place test files inside the `.agents/` folder.
- Use a real PyQt6 GUI test approach (e.g., pytest-qt or programmatic widget access) rather than mock UI where possible.
- Minimum test thresholds must be met (Tier 1: Feature Coverage >= 5 per feature, Tier 2: Boundary & Corner >= 5 per feature, Tier 3: Cross-Feature Combinations pairwise, Tier 4: Real-world scenarios >= 5).
- Simplify Chinese as standard language.
- Key-naming, SQL and DB transactions checks.
- **NO TEST EXECUTION**: Do NOT run tests, do NOT execute `python`, `pytest`, or any test/launch commands. All verification must be done statically.

## Current Parent
- Conversation ID: ccdc47c8-7e28-456f-b602-58e742b90af2
- Updated: not yet

## Key Decisions Made
- Use pytest with pytest-qt for E2E GUI testing.

## Team Roster
| Agent | Type | Work Item | Status | Conv ID |
|-------|------|-----------|--------|---------|
| worker | teamwork_preview_worker | Write E2E test suite | completed | b0348028-0072-4825-82cc-3d1173aaccde |

## Succession Status
- Succession required: no
- Spawn count: 1 / 16
- Pending subagents: none
- Predecessor: none
- Successor: not yet spawned

## Active Timers
- Heartbeat cron: 963326f8-f392-49f0-8fba-0ad62e7c6da6/task-17
- Safety timer: 963326f8-f392-49f0-8fba-0ad62e7c6da6/task-37

## Artifact Index
- d:\workspace\bnb_guessing\.agents\e2e_testing_orchestrator\TEST_INFRA.md — E2E test infra design, features and methodology
- d:\workspace\bnb_guessing\.agents\e2e_testing_orchestrator\TEST_READY.md — Signal file indicating that tests are ready
