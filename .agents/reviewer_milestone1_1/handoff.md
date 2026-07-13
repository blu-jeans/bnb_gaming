# Handoff Report - Milestone 1 Database & Repository Review

## 1. 观察 (Observation)

在对数据库模型、连接管理器、仓储服务层及其测试代码进行独立评审的过程中，观察到以下内容：

1. **核心文件分析**：
   - `src/database/models.py` (共 89 行)：定义了数据实体类（`Member`, `Tournament`, `Round`, `Bet`, `MatchHistory`）以及枚举类（`TournamentStatus`, `TeamColor`）。
   - `src/database/db_manager.py` (共 69 行)：封装了 `DBManager` 连接管理器，包含 `connection` 上下文管理器及自定义的 `dict_like_row_factory`。
   - `src/database/repository.py` (共 347 行)：定义了 `Repository` 类，实现了基础的数据库初始化和 CRUD/事务操作（如 `save_round_settlement` 等）。
   - `tests/database/test_repository.py` (共 300 行)：包含了 9 个单元测试用例，覆盖了表结构验证、成员添加、锦标赛生命周期控制、结算事务性（包括回滚）及积分排行榜等。

2. **基本规范校验**：
   - 所有的代码注释、Docstring 均使用**简体中文**编写。
   - 所有的文件均包含作者署名注释（`@author hyq`）以及日期（`@version 2026-07-13`）。
   - 连接管理器 `DBManager` 的连接上下文中包含 `conn.execute("PRAGMA foreign_keys = ON;")` 以强制启用 SQLite 外键约束。

3. **测试运行状态**：
   - 运行针对仓储层的单元测试命令：
     ```powershell
     $env:PYTHONPATH="." ; pytest tests/database/test_repository.py
     ```
     测试输出如下：
     ```
     collected 9 items
     tests\database\test_repository.py .........                              [100%]
     ============================== 9 passed in 0.57s ==============================
     ```
     **仓储层自身的所有单元测试全部通过。**
   
   - 运行项目全量测试套件时，GUI 部分测试（如 `tests/test_tier1_features.py`）出现大量失败（如 `sqlite3.ProgrammingError: Incorrect number of bindings supplied`）。

4. **架构与代码耦合度观察**：
   - 检查 GUI 主窗口实现 `tests/test_helper.py` 中的 `BnbMainWindow` 类发现，它通过 `sqlite3.connect` **直接进行了本地数据库表的创建和增删改查操作**，并没有导入或使用 `DBManager` 以及 `Repository`。
   - **两套 Schema 存在严重的定义冲突**：
     - **状态值和颜色的大小写不一致**：`Repository` 在表约束中强制使用大写字符（`status IN ('ONGOING', 'ENDED')`，`winner IN ('RED', 'GREEN')`）；而 `BnbMainWindow` 的初始化数据库中使用了小写或驼峰（`status DEFAULT 'ongoing'`，`winner` 存入 `'Red'`/`'Green'`）。
     - **初始积分定义不一致**：`Repository` 默认 `historical_score` 为 `1000`；而 `BnbMainWindow` 默认 `historical_score` 为 `0`。
     - **关系设计不一致**：`Repository` 使用了外键关联 `round_id` 与 `member_id`；而 `BnbMainWindow` 的 `bets` 表字段则是 `tournament_id`, `round_number` 以及 `member_name`，且缺乏物理外键关联。
   
5. **测试辅助函数 Bug**：
   - `tests/test_helper.py` 中的 `assert_db_state` 函数定义如下：
     ```python
     def assert_db_state(db_path, query, expected_results):
         conn = sqlite3.connect(db_path)
         cursor = conn.cursor()
         cursor.execute(query) # 缺少对 query 的参数绑定传参
         ...
     ```
     当测试用例传入包含 `?` 占位符的 SQL 语句时（例如 `SELECT status FROM tournaments WHERE id = ?`），由于未向 `cursor.execute` 传入相应的绑定元组，将直接导致 `sqlite3.ProgrammingError: Incorrect number of bindings supplied. The current statement uses 1, and there are 0 supplied.` 错误。

---

## 2. 逻辑链 (Logic Chain)

根据上述观察，推导出以下逻辑链：

1. **功能未真正集成**：因为 `BnbMainWindow` (GUI 核心类) 内部仍然直接硬编码调用 SQLite 执行其自身的 SQL 语句，并未通过 `Repository` 与 `DBManager` 访问数据库，说明仓储层和 GUI 层处于**完全脱节**的状态。
2. **Schema 冲突无法兼容**：由于两套 Schema 的字段名称、数据类型规范、默认积分（`0` vs `1000`）、状态值大小写（`ongoing` vs `ONGOING`）存在显著冲突，导致 GUI 部分与 Repository 目前无法直接对接。
3. **GUI 单元测试代码编写缺陷**：`assert_db_state` 在设计时忽略了参数绑定的情况，使许多正常的测试场景（需要通过 ID 查询校验数据库状态）在执行到该断言时由于参数缺失而崩溃。
4. **仓储层及连接管理器本身的设计完备性**：
   - `@author` 署名及简体中文注释验证无误。
   - 上下文管理器通过 `try-except-finally` 机制对 `commit`、`rollback` 和 `close` 作了妥善处理，不会产生连接泄漏，且实现了事务回滚的原子性（在单元测试 `test_save_round_settlement_and_transaction` 中已通过外键触发 IntegrityError 验证回滚正常）。
   - 外键约束与索引（如 `idx_tournaments_status`、`idx_rounds_tournament_id`）已被正确创建并启用。

---

## 3. 局限性与假设 (Caveats)

1. **范围限制**：本次评审严格遵循“Review-only”的原则，仅进行代码的静态审查、运行测试并提出整改意见，未对任何有缺陷的业务代码（包括 `BnbMainWindow` 的集成与 `assert_db_state` 辅助函数 Bug）进行手动修复。
2. **并发评估限制**：未在真实高并发的多进程或多线程环境下测试 SQLite 的锁争用情况，仅通过代码分析了其潜在的死锁和锁等待超时风险。

---

## 4. 结论 (Conclusion)

### 评审结论：REQUEST_CHANGES (拒绝并要求整改)

### 核心质量评估报告 (Quality Review Report)

#### 1. 发现问题 (Findings)

##### 🔴 关键缺陷 (Critical) 1: 业务层 (GUI) 与仓储层 (Repository) 完全脱节
- **具体表现**：`tests/test_helper.py` 中的 `BnbMainWindow` 直接定义并使用了其自身的 `init_db` 方法及原生 `sqlite3` 连接进行所有的数据库存取。仓储服务层 `Repository` 和 `DBManager` 并未被 GUI 引用。
- **潜在危害**：导致新开发的仓储层成为了“摆设”，Milestone 1 中对数据库交互机制的重构和健壮性提升在实际应用中没有任何效果。
- **改进建议**：重构 `BnbMainWindow` 的初始化与交互逻辑，使用依赖注入或在初始化时实例化 `Repository`，所有的数据操作均通过仓储层接口进行。

##### 🟡 主要缺陷 (Major) 2: 数据库 Schema 严重冲突，不具备向下兼容性
- **具体表现**：
  1. `BnbMainWindow` 期待的锦标赛状态为小写 `'ongoing'`/`'ended'`，而 `Repository` 中硬编码了限制大写的 `CHECK(status IN ('ONGOING', 'ENDED'))`；
  2. `BnbMainWindow` 默认初始积分为 `0`，而 `Repository` 默认初始积分为 `1000`；
  3. 表关系未对齐（BnbMainWindow 倾向于直接使用 `member_name` 等非规范化冗余字段，Repository 实现了外键规范化）。
- **潜在危害**：直接导致两套机制在集成时抛出数据类型不一致或约束校验失败的异常。
- **改进建议**：对齐双方的 Schema 规范。如果是对老旧数据表的升级，应当提供一致的数据迁移路径；状态值和颜色建议统一为大写或保持良好的映射层进行转换。

##### 🟡 主要缺陷 (Major) 3: 测试辅助函数 `assert_db_state` 设计缺陷导致 GUI 测试崩溃
- **具体表现**：`tests/test_helper.py` 第 785 行的 `assert_db_state` 方法，在执行带有 SQL 参数占位符 `?` 的 `query` 时，未能在 `cursor.execute` 中传入任何绑定值。
- **潜在危害**：导致依赖该断言的所有 GUI 测试用例全部崩溃失败。
- **改进建议**：修改 `assert_db_state` 的签名，使其支持传入 `params: tuple = ()`，并在执行时调用 `cursor.execute(query, params)`。

#### 2. 已验证声明 (Verified Claims)
- **仓储层单元测试全部通过**：`tests/database/test_repository.py` 中的 9 个用例均成功运行并断言通过。验证方式为 `pytest`。
- **外键约束与事务一致性已生效**：通过在测试中传入无效外键，已验证外键约束会抛出 `IntegrityError`，且仓储层正确回滚了事务，未对数据库残留脏数据。
- **基本规范符合要求**：所有代码类头部均正确标注了 `@author hyq` 并且使用了简体中文注释。

---

### 对抗性安全与健壮性报告 (Adversarial Challenge Report)

#### 1. 发现的问题与挑战 (Challenges)

##### 🟡 中度风险 (Medium) Challenge 1: 缺少全局连接锁，高并发写操作时可能产生 `database is locked` 异常
- **挑战假设**：SQLite 自身仅支持单一写连接。在目前 `DBManager.connection()` 默认的事务隔离级别下，若有多个业务线程并发调用 Repository 的写入接口（例如多名成员同时投注），可能会同时开启事务进行读，随后尝试升级为写锁，从而产生死锁，或在锁等待超时后抛出 `sqlite3.OperationalError: database is locked`。
- **攻击场景**：并发性能压测，模拟多名家庭成员同时调用结算或投注接口。
- **影响范围**：业务接口直接报错失败，事务异常。
- **防护建议**：在 `DBManager.connection()` 的事务开始时，如果包含写操作，应当显式执行 `conn.execute("BEGIN IMMEDIATE");` 或者是使用互斥锁对写入逻辑进行串行化控制。

##### 🟡 中度风险 (Medium) Challenge 2: 缺乏跨仓储方法的长事务支撑
- **挑战假设**：目前的 `Repository` 中的每一个 CRUD 方法（如 `add_member`, `start_tournament` 等）内部都独立通过 `with self.db_manager.connection()` 获取连接并提交。这就意味着每个仓储方法都是一个独立的物理事务。
- **攻击场景**：在更高级的业务场景中，如果我们需要在同一个业务流程里“先开启锦标赛，再添加初始成员”，且这两个操作必须保持原子性（其中一个失败则全部回融）。目前的架构由于连接在每个方法内部独立申请并提交，无法共享同一个事务连接，从而无法保证跨方法的长事务一致性。
- **影响范围**：当业务逻辑变得复杂时，无法保证跨 Repository 方法的一致性。
- **防护建议**：引入事务管理器，或允许仓储方法接收一个可选的 `connection` 参数，或者将连接生命周期管理（Units of Work）提升到业务/服务层。

---

## 5. 独立验证方法 (Verification Method)

1. **验证仓储层基础功能**：
   在控制台运行以下命令，确保仓储层本身测试通过：
   ```powershell
   $env:PYTHONPATH="." ; pytest tests/database/test_repository.py
   ```
2. **重现 GUI 测试崩溃**：
   在控制台运行以下命令，可以重现由于 `assert_db_state` 没有进行参数绑定传参而导致的测试失败：
   ```powershell
   $env:PYTHONPATH="." ; pytest tests/test_tier1_features.py -k test_f1_start_new_tournament
   ```
3. **审查代码耦合与 Schema 冲突**：
   - 打开 `tests/test_helper.py` 检索 `def init_db(self)`，对比其创建的 `members`, `tournaments` 表结构与 `src/database/repository.py` 中的 `initialize_db` 表结构设计。
