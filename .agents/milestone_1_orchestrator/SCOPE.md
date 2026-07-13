# Scope: Milestone 1 — DB Schema & Core Models

## Architecture
- 数据库: 采用本地 SQLite 数据库文件 `bnb_betting.db`，在应用程序启动时自动在 exe 同级目录下创建或读取。
- 连接管理: 使用 `sqlite3` 提供连接上下文管理器（包含事务控制）。
- 数据模型: 在 `src/database/models.py` 中定义对应的数据类（Data Classes）或命名元组，用于表示 Member, Tournament, Round, Bet, MatchHistory 等核心实体。
- 数据访问层: 在 `src/database/repository.py` 中实现对数据库的增删改查（CRUD）操作，并保证涉及多表修改的操作全部在事务中执行。

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| 1 | DB Schema & Tables Setup | 数据库文件自动创建，初始化 members, tournaments, rounds, bets, match_history 数据表结构 | None | DONE |
| 2 | Transactional CRUD Operations | 实现事务性的 CRUD 接口（启动/结束比赛，保存单轮结算，更新成员积分，获取历史记录与排行榜） | M1 | DONE |
| 3 | Integrated Unit Testing | 编写完整的单元测试，验证所有核心模型、连接管理以及事务性 Repository APIs 的正确性 | M2 | DONE |

## Interface Contracts
### Data Layer ↔ Logic/UI Layer
- `db_manager.get_connection()`: 返回 SQLite 连接的上下文管理器。
- `repository.initialize_db()`: 自动创建表结构。
- `repository.add_member(name: str, initial_score: int) -> int`: 添加家庭成员。
- `repository.get_all_members() -> list`: 获取所有成员列表及历史积分。
- `repository.start_tournament() -> int`: 开启新一届锦标赛，返回其 ID。
- `repository.end_tournament(tournament_id: int) -> dict`: 结束锦标赛，计算庄家净盈亏，返回冠亚军或盈利排行榜，并将本届所有轮次归档到 `match_history`。
- `repository.save_round_settlement(tournament_id: int, round_number: int, red_score: int, green_score: int, winner: str, banker_round_profit: int, bets: list, settlements: list) -> bool`: 在一个事务内保存单轮比赛得分、所有投注、各投注人盈亏以及庄家该轮的最终盈亏，并更新各玩家的历史累计积分和当前锦标赛盈亏。
- `repository.get_match_history() -> list`: 从归档表 `match_history` 中获取所有已结束锦标赛的归档记录。
- `repository.get_tournament_leaderboard(tournament_id: int) -> list`: 获取当前锦标赛的盈亏排行榜。
