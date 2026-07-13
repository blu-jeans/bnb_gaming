# BRIEFING — 2026-07-13T16:30:00+08:00

## Mission
实现 `src/engine/betting_engine.py` 核心业务逻辑引擎，包括投注限额校验、1:1 结算分值守恒算法、战队绑定校验以及七局四胜制胜负判定。

## 🔒 My Identity
- Archetype: teamwork_preview_orchestrator
- Roles: orchestrator, user_liaison, human_reporter, successor
- Working directory: d:\workspace\bnb_guessing\.agents\milestone_2_orchestrator
- Original parent: parent
- Original parent conversation ID: ccdc47c8-7e28-456f-b602-58e742b90af2

## 🔒 My Workflow
- **Pattern**: Project / Sub-orchestrator
- **Scope document**: d:\workspace\bnb_guessing\.agents\milestone_2_orchestrator\SCOPE.md
1. **Decompose**: 拆分为逻辑引擎实现与单元测试规格书写两步。
2. **Dispatch & Execute**:
   - **Delegate (sub-orchestrator)**: 不适用，我们已是子协调器。
   - **Direct (iteration loop)**: 派遣 Worker 进行编码，Reviewer 进行静态审计审查。
3. **On failure**: Retry -> Replace -> Skip -> Redistribute -> Redesign -> Escalate.
4. **Succession**: 当累计派生子智能体次数达到 16 时自我接替。
- **Work items**:
  1. 逻辑引擎 Betting Engine 实现 [pending]
  2. 单元测试实现 [pending]
- **Current phase**: 2
- **Current focus**: 派遣 Worker 编写代码

## 🔒 Key Constraints
- 绝对禁止运行任何 python、pytest、pyinstaller 或其他测试与启动命令。
- 所有代码注释及文档必须使用简体中文。
- 固定作者署名 @author hyq。
- 新增/修改的文件应直接就地修改写入。

## Current Parent
- Conversation ID: ccdc47c8-7e28-456f-b602-58e742b90af2
- Updated: not yet

## Key Decisions Made
- 将逻辑引擎 Betting Engine 与其对应的测试规范写在 `tests/engine/test_betting_engine.py` 目录下。

## Team Roster
| Agent | Type | Work Item | Status | Conv ID |
|-------|------|-----------|--------|---------|
| worker_1 | teamwork_preview_worker | Implement Betting Engine and unit tests | completed | a1828260-c8f1-4205-9430-26bd6fd20e6f |
| reviewer_1 | teamwork_preview_reviewer | Static code review of Betting Engine | completed | 584fa128-e68c-4090-bc42-4a659a13d93e |
| reviewer_2 | teamwork_preview_reviewer | Static code review of Betting Engine | completed | 9ad214c7-b0c3-48dd-b1e4-9e51b687f70c |
| worker_2 | teamwork_preview_worker | Fix review gaps in Betting Engine & tests | in-progress | 13dc8818-2b41-470f-a2fe-4a8147063f48 |

## Succession Status
- Succession required: no
- Spawn count: 4 / 16
- Pending subagents: [13dc8818-2b41-470f-a2fe-4a8147063f48]
- Predecessor: none
- Successor: not yet spawned

## Active Timers
- Heartbeat cron: task-45
- Safety timer: none

## Artifact Index
- d:\workspace\bnb_guessing\.agents\milestone_2_orchestrator\SCOPE.md — Milestone 2 范围定义
- d:\workspace\bnb_guessing\.agents\milestone_2_orchestrator\progress.md — 进度跟进文件
