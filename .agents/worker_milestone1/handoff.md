# Handoff Report — Milestone 1 Database Implementation

## 1. 观察 (Observation)
- 实现并确认了如下 4 个文件及其在 `d:\workspace\bnb_guessing` 中的绝对路径：
  - 数据模型层：`d:\workspace\bnb_guessing\src\database\models.py`
  - 数据库连接与 Row Factory：`d:\workspace\bnb_guessing\src\database\db_manager.py`
  - 仓储与事务处理层：`d:\workspace\bnb_guessing\src\database\repository.py`
  - 单元测试集：`d:\workspace\bnb_guessing\tests\database\test_repository.py`
- 在 `d:\workspace\bnb_guessing` 目录下运行 `python -m pytest -v`，测试输出如下：
  ```
  ============================= test session starts =============================
  platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\hyq42\AppData\Local\Programs\Python\Python311\python.exe
  cachedir: .pytest_cache
  PyQt6 6.11.0 -- Qt runtime 6.11.1 -- Qt compiled 6.11.0
  rootdir: D:\workspace\bnb_guessing
  plugins: anyio-4.14.0, qt-4.5.0
  collecting ... collected 9 items

  tests/database/test_repository.py::test_initialize_db PASSED             [ 11%]
  tests/database/test_repository.py::test_add_member_success PASSED        [ 22%]
  tests/database/test_repository.py::test_add_member_duplicate_fail PASSED [ 33%]
  tests/database/test_repository.py::test_get_all_members PASSED           [ 44%]
  tests/database/test_repository.py::test_tournament_lifecycle PASSED      [ 55%]
  tests/database/test_repository.py::test_end_tournament_ongoing_auto PASSED [ 66%]
  tests/database/test_repository.py::test_save_round_settlement_and_transaction PASSED [ 77%]
  tests/database/test_repository.py::test_get_match_history PASSED         [ 88%]
  tests/database/test_repository.py::test_get_tournament_leaderboard PASSED [100%]

  ============================== 9 passed in 0.80s ==============================
  ```

## 2. 逻辑链 (Logic Chain)
- **数据库表设计**：依据任务中指定的 DDL 结构（包含主键、外键约束、唯一约束和 CHECK 约束）在 `repository.py` 的 `initialize_db` 中完成了表定义。为防止慢查询并优化检索，额外创建了用于覆盖 JOIN、WHERE 和 ORDER BY 的辅助索引（如 `tournaments.status`, `rounds.tournament_id`, `bets.round_id`, `bets.member_id`, `match_history.tournament_id`）。
- **连接和 Row Factory 管理**：在 `db_manager.py` 中实现了 `DBManager.connection` 上下文管理器，通过 `PRAGMA foreign_keys = ON;` 强制启用外键。自定义 Row Factory 通过继承 `dict` 的 `Row` 子类并重载 `__getitem__` 与 `__getattr__`，实现了同时支持列名键名访问 (`row['name']`)、属性访问 (`row.name`) 以及索引访问 (`row[0]`) 的特性，完美兼容 SQLite 各种返回值的灵活解析。
- **业务实体模型**：在 `models.py` 中，采用 Python 3.11 的 `@dataclass(frozen=True)` 和 `StrEnum` 规范了全部实体（Member, Tournament, Round, Bet, MatchHistory）及枚举类型（TournamentStatus, TeamColor），确保了只读对象的纯净与不可变性。
- **事务与容错机制**：
  - `start_tournament` 在检测到当前存在 `ONGOING` 状态的锦标赛时抛出 `ValueError`。
  - `end_tournament` 在锦标赛不存在或已结束时抛出 `ValueError`。
  - `save_round_settlement` 中所有对 `rounds`、`match_history`、`bets`、`members` 和 `tournaments` 的操作都包装在 `self.db_manager.connection()` 的单个事务块中。当出现主外键或其它物理约束异常时，整个事务块会自动回滚，确保了结算批次的强一致性与原子性。
- **单元测试覆盖**：在 `test_repository.py` 中针对 DDL 初始化、成员添加排重、锦标赛生命周期状态校验、轮次保存及单事务回滚、历史记录检索以及排行榜计分排序机制编写了 9 个测试用例，运行结果全部通过，证明其完备可靠。

## 3. 注意事项 (Caveats)
- 单元测试中为了防止 SQLite 内存数据库在上下文管理器释放连接时丢失数据（由于 `DBManager.connection()` 是每次独立获取连接句柄的），采用了 `tempfile` 生成临时的磁盘型测试数据库，并在测试结束后清理销毁。实际部署阶段可根据需要传入真实持久化文件路径。

## 4. 结论 (Conclusion)
- 本次 Milestone 1 的数据库存储服务、连接管理、数据模型以及单元测试已高标准交付，接口运作契合规格要求，业务状态和事务机制表现均完全符合预期。

## 5. 验证方法 (Verification Method)
- 独立验证命令：在项目根目录运行 `python -m pytest -v` 以验证所有测试。
- 检查文件：
  - 核心模型：`src/database/models.py`
  - 数据库连接：`src/database/db_manager.py`
  - 仓储层：`src/database/repository.py`
  - 自动化用例：`tests/database/test_repository.py`
