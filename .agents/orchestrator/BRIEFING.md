# BRIEFING — 2026-07-13T16:14:58+08:00

## Mission
Decompose the BnB Family Match Score Betting System project, plan milestones, coordinate subagents to implement, verify, and complete all requirements.

## 🔒 My Identity
- Archetype: teamwork_preview_orchestrator
- Roles: orchestrator, user_liaison, human_reporter, successor
- Working directory: d:\workspace\bnb_guessing\.agents\orchestrator
- Original parent: top-level
- Original parent conversation ID: ccdc47c8-7e28-456f-b602-58e742b90af2

## 🔒 My Workflow
- **Pattern**: Project
- **Scope document**: d:\workspace\bnb_guessing\PROJECT.md
1. **Decompose**: Decompose the project into milestones (3-7 milestones) and document in PROJECT.md.
2. **Dispatch & Execute**:
   - **Delegate (sub-orchestrator)**: Spawn a sub-orchestrator for each milestone.
3. **On failure** (in this order):
   - Retry: nudge stuck agent or re-send task
   - Replace: spawn fresh agent with partial progress
   - Skip: proceed without (only if non-critical)
   - Redistribute: split stuck agent's remaining work
   - Redesign: re-partition decomposition
   - Escalate: report to parent (sub-orchestrators only, last resort)
4. **Succession**: Self-succeed at 16 spawns, write handoff.md, spawn successor.
- **Work items**:
  1. Analyze requirements & plan milestones [in-progress]
  2. Implement backend & frontend modules [pending]
  3. Validate using E2E testing [pending]
  4. Final victory claim [pending]
- **Current phase**: 1
- **Current focus**: Analyze requirements & plan milestones

## 🔒 Key Constraints
- NEVER write, modify, or create source code files directly.
- NEVER run build/test commands yourself — require workers to do so.
- Keep the language Simplified Chinese (简体中文).
- Do not reuse a subagent after it has delivered its handoff.
- DO NOT automatically run any tests, do not execute python, pytest, or any test/launch commands. The user will handle all testing and launching manually.
- ABSOLUTE BAN: NO python commands, NO pytest commands, NO pyinstaller commands, NO launching any .py files, NO running the application. The only terminal commands allowed are: mkdir, file creation/editing, and pip checking.



## Current Parent
- Conversation ID: ccdc47c8-7e28-456f-b602-58e742b90af2
- Updated: not yet

## Key Decisions Made
- Use Project pattern with Dual Track (Implementation & E2E Testing).

## Team Roster
| Agent | Type | Work Item | Status | Conv ID |
|-------|------|-----------|--------|---------|
| E2E Testing Track | self | Test suite creation | completed | 963326f8-f392-49f0-8fba-0ad62e7c6da6 |
| Milestone 1 Sub-orch | self | DB Schema & Core Models | completed | e5e5310c-2a17-40ec-a6ca-65b0d189446c |
| Milestone 2 Sub-orch | self | Betting & Team Binding Logic | in-progress | 6d9e7429-d6bf-4b6c-840f-d20575093dc3 |
| DB Preset Worker | teamwork_preview_worker | DB Schema & 34 Members Preset | completed | ede89cd1-34b2-4720-8ff2-72eaedc4144c |

## Succession Status
- Succession required: no
- Spawn count: 4 / 16
- Pending subagents: 6d9e7429-d6bf-4b6c-840f-d20575093dc3
- Predecessor: none
- Successor: not yet spawned

## Active Timers
- Heartbeat cron: task-13
- Safety timer: none
- On succession: kill all timers before spawning successor
- On context truncation: run manage_task(Action="list") — re-create if missing

## Artifact Index
- d:\workspace\bnb_guessing\.agents\orchestrator\ORIGINAL_REQUEST.md — Original User Request
- d:\workspace\bnb_guessing\.agents\orchestrator\progress.md — Heartbeat & Liveness Progress
- d:\workspace\bnb_guessing\PROJECT.md — Global Project Index (Milestones, Architecture, Interfaces)
