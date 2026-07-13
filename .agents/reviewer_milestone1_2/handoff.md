# Handoff Report — 2026-07-13

## 1. 观察 (Observation)
- **源码文件及路径**：
  - `src/database/models.py`
  - `src/database/db_manager.py`
  - `src/database/repository.py`
  - `tests/database/test_repository.py`
- **注释和署名**：所有源码文件顶部均包含 `@author hyq` 和 `@version 2026-07-13`，且采用简体中文注释。符合项目规范。
- **单元测试执行结果**：运行 `python -m pytest tests/database/test_repository.py`，结果显示所有 9 个单元测试均通过：
  ```
  tests\database\test_repository.py .........                              [100%]
  ============================== 9 passed in 0.52s ==============================
  ```
- **发现的问题 1（Row 键污染）**：在 `src/database/db_manager.py` 的 `dict_like_row_factory` 中：
  ```python
  class Row(dict):
      def __init__(self, keys: list[str], values: tuple):
          super().__init__()
          self._keys = keys
          self._values = values
          for k, v in zip(keys, values):
              self[k] = v
      # ...
      def __setattr__(self, name: str, value):
          self[name] = value
  ```
  由于 `__setattr__` 被重写为将所有属性赋值都写入字典键中（`self[name] = value`），所以在构造函数中执行 `self._keys = keys` 和 `self._values = values` 时，会把 `_keys` 和 `_values` 存储为字典的键。这导致调用 `dict(row)` 或 `row.keys()` 时，会返回 `_keys` 和 `_values` 键。
  实际输出：
  `{'_keys': [...], '_values': (...), 'col1': val1, ...}`
- **发现的问题 2（缺少执行计划）**：在 `src/database/repository.py` 的 `get_tournament_leaderboard` 方法中，存在一个复杂的多表连接查询（连接了 `members`、`bets`、`rounds` 3张表，包含 `SUM` 聚合、`GROUP BY` 和 `ORDER BY` 多重排序），但没有在注释中附带 `EXPLAIN QUERY PLAN` 预期执行计划，这违反了项目全局规范的“数据库与 MyBatis 铁律”第4条：“新增复杂查询时，AI 必须在注释中附上 EXPLAIN ANALYZE 的预期执行计划”。
- **发现的问题 3（连接泄漏隐患）**：在 `src/database/db_manager.py` 中，`sqlite3.connect(self.db_path)` 打开连接后，先执行了 `PRAGMA foreign_keys = ON;` 和行工厂赋值，然后再进入 `try...finally` 块。如果在进入 `try` 块之前发生异常，连接将无法关闭，存在极小概率的连接泄露风险。
- **发现的问题 4（内存数据库局限性）**：使用 SQLite 的内存模式（如 `:memory:`）进行测试时，每次调用仓储方法（如 `add_member`）都会打开和关闭一个全新的内存数据库连接，导致数据被完全清空，抛出 `sqlite3.OperationalError: no such table: members`。

## 2. 逻辑链 (Logic Chain)
- 基于上述观察：
  - **问题 1 逻辑**：`Row` 继承自 `dict`。当使用 `self._keys = keys` 进行赋值时，Python 会调用重写的 `__setattr__`，进而执行 `self["_keys"] = keys`。这导致系统级变量污染了字典的键集，凡是使用 `dict(row)`、`list(row.keys())` 或对其进行 JSON 序列化的情况，均会出现额外的 `_keys` 和 `_values` 键，破坏了对外接口的数据干净度。
  - **问题 2 逻辑**：`get_tournament_leaderboard` 方法连接了三张表，并进行聚合分组与排序，属于中/高复杂度的 SQL 查询。根据项目规范，此复杂查询应该包含其相应的预期执行计划，以备后续进行慢 SQL 审计。目前注释中缺少此内容。
  - **问题 3 逻辑**：如果 `conn.execute("PRAGMA foreign_keys = ON;")` 因任何底层错误或 SQLite 运行时异常失败，控制流将在进入 `try:` 块前中断，导致 `conn.close()` 无法被调用，引发连接泄露。
  - **问题 4 逻辑**：SQLite `:memory:` 数据库在连接关闭时会自动销毁。目前的 `DBManager.connection()` 采用的是短连接模式（每次操作打开并提交后即关闭），导致内存数据库中的表和数据在方法结束时立刻丢失，无法在多次调用间保持。

## 3. 注意事项/局限性 (Caveats)
- 本次评审没有对多线程并发场景下的 SQLite 数据库锁（Database Locked）进行真实高并发压测，主要是基于代码静态分析做出的并发死锁/锁等待风险提示。由于本项目是 PyQt 桌面应用，大部分场景为单线程操作，但如果后续在多线程工作线程中并发写入数据库，需要注意 SQLite 写入排他锁带来的冲突。

## 4. 结论 (Conclusion)
- **最终评审结论**：**REQUEST_CHANGES** (需要修改)
- 总结：
  - **Models.py**：实现正确，契约完整，署名正确。
  - **Db_manager.py**：存在 Row 键污染 Bug 和小概率的连接泄漏隐患，无法支持内存数据库。
  - **Repository.py**：整体 SQL 索引覆盖完整，单条 SQL JOIN 未超 3 张表，无 `SELECT *` 模式；但复杂排行榜查询缺少 `EXPLAIN QUERY PLAN` 预期执行计划，违反了全局 SQL 编写规范。
  - **Test_repository.py**：测试用例编写规范，能够覆盖常规逻辑和事务回滚，但由于连接管理器设计局限，未包含 `:memory:` 模式测试。

## 5. 验证方法 (Verification Method)
1. **验证 Row 键污染 Bug**：
   运行以下命令：
   ```bash
   python -c "from src.database.db_manager import DBManager; import tempfile, os; fd, path = tempfile.mkstemp(); os.close(fd); db = DBManager(path); r = db.dict_like_row_factory(type('Cursor', (), {'description': [('a',), ('b',)]})(), (10, 20)); print(dict(r)); os.remove(path)"
   ```
   **预期输出**：`{'_keys': ['a', 'b'], '_values': (10, 20), 'a': 10, 'b': 20}`（包含多余的系统键，验证失败）。
   
2. **运行单元测试**：
   ```bash
   python -m pytest tests/database/test_repository.py
   ```
   **预期输出**：`9 passed in 0.52s`（验证全部基础功能通过）。

---

## 6. 评审与对抗性报告 (Review & Challenge Report)

### 评审概要 (Review Summary)
- **Verdict**: REQUEST_CHANGES
- **Rationale**: 尽管单元测试全部通过，但数据库行工厂（Row Factory）存在泄露内部属性 `_keys`/`_values` 到字典键集的 Bug。此外，复杂的排行榜查询 SQL 缺少全局规则所要求的 `EXPLAIN QUERY PLAN` 预期执行计划。

### 发现的问题 (Findings)

#### [Critical] 发现 1: 字典行工厂存在属性泄露 Bug (Leaky Row Factory)
- **What**: 继承自 `dict` 的自定义 `Row` 类通过重写 `__setattr__` 将 `self._keys` 和 `self._values` 写入了底层的 `dict` 键集中。
- **Where**: `src/database/db_manager.py` (Line 38-68)
- **Why**: 任何获取到的行数据在调用 `dict(row)` 转换或者在前端进行 JSON 序列化时，都会包含非业务键 `_keys` 和 `_values`，这极易引发前端解析或契约不匹配的问题。
- **Suggestion**: 
  在 `Row.__init__` 中使用 `object.__setattr__(self, '_keys', keys)` 和 `object.__setattr__(self, '_values', values)` 绕过被重写的 `__setattr__`：
  ```python
  class Row(dict):
      def __init__(self, keys: list[str], values: tuple):
          super().__init__()
          object.__setattr__(self, '_keys', keys)
          object.__setattr__(self, '_values', values)
          for k, v in zip(keys, values):
              self[k] = v
  ```

#### [Major] 发现 2: 复杂 SQL 连接查询缺少预期执行计划 (Missing EXPLAIN PLAN)
- **What**: `get_tournament_leaderboard` 涉及 3 张表连接及分组、聚合、排序，但未提供 `EXPLAIN QUERY PLAN` 的预期分析。
- **Where**: `src/database/repository.py` (Line 322-346)
- **Why**: 违反了项目全局规范 `RULE[user_global]` 第 4 条中关于“新增复杂查询时，AI 必须在注释中附上 EXPLAIN ANALYZE 的预期执行计划”的红线要求。
- **Suggestion**: 
  在 `get_tournament_leaderboard` 的注释中附上以下预期执行计划：
  ```sql
  -- EXPLAIN QUERY PLAN 预期执行计划:
  -- SEARCH m USING INTEGER PRIMARY KEY (rowid=?)
  -- SEARCH b USING INDEX idx_bets_member_id (member_id=?)
  -- SEARCH r USING INTEGER PRIMARY KEY (rowid=?)
  -- USE TEMP B-TREE FOR GROUP BY
  -- USE TEMP B-TREE FOR ORDER BY
  ```

#### [Minor] 发现 3: 连接管理器初始化异常下的连接泄漏隐患
- **What**: 连接创建后在进入 `try...finally` 块前执行了 PRAGMA 命令，若该步骤抛出异常，连接将无法关闭。
- **Where**: `src/database/db_manager.py` (Line 23-35)
- **Why**: 在 `PRAGMA foreign_keys = ON;` 执行出错时，程序无法调用 `conn.close()`，导致连接或文件句柄泄漏。
- **Suggestion**: 将 `try:` 块移动到 `sqlite3.connect` 之后，将所有的配置指令包裹在内。

---

### 已验证声明 (Verified Claims)
- **声明 1**: 数据库事务回滚功能正常工作。
  - 验证方法: 在 `test_save_round_settlement_and_transaction` 中使用不存在的成员 ID 触发外键约束失败，成功验证 `rounds` 表未插入无效数据且成员积分与锦标赛收益全部回滚。 -> **PASS**
- **声明 2**: SQLite 外键约束默认开启并正常级联删除。
  - 验证方法: 在 `test_initialize_db` 中执行 `PRAGMA foreign_keys;` 确认返回值为 `1`。 -> **PASS**
- **声明 3**: SQL 查询均使用了索引覆盖。
  - 验证方法: 检查 DDL 及索引创建代码，确认在 `status`、`tournament_id`、`round_id`、`member_id` 等常用于 WHERE 和 JOIN 的列上均正确创建了辅助索引。 -> **PASS**

---

### 对抗性挑战点 (Challenges)

#### [High] 挑战 1: 内存模式 (:memory:) 导致仓储完全不可用
- **假设前提**: 系统可能在单元测试或内存模式下部署。
- **攻击场景**: 使用 `DBManager(":memory:")` 初始化仓储。
- **失效表现**: 由于每次操作均会使用全新的连接并销毁前一次的数据库，导致在 `initialize_db` 之后调用 `add_member` 会直接报表不存在的错误。
- **破坏半径**: 仓储类在内存数据库下完全失效，极大地阻碍了轻量级单元测试的编写。
- **防守建议**: 在 `DBManager` 中识别 `:memory:` 路径，若是内存模式，则持久化连接对象并不在 context manager 结束时关闭它，或者提供长连接共享机制。

#### [Medium] 挑战 2: 极端并发写操作下的 Database Locked 异常
- **假设前提**: 应用程序在后台工作线程中并发调用 `save_round_settlement` 或 `start_tournament`。
- **攻击场景**: 两个线程同时开启事务进行写入操作。
- **失效表现**: SQLite 在写入时会加排他锁。如果一个事务长时间占用（例如网络等待或大批量写），另一个事务在默认的 5 秒超时后会直接抛出 `sqlite3.OperationalError: database is locked`。
- **破坏半径**: 导致事务失败，业务操作报错。
- **防守建议**: 
  1. 保证所有的数据库写入在极短时间内完成。
  2. 显式在连接时配置 busy timeout，如 `sqlite3.connect(self.db_path, timeout=30.0)`。
  3. 对于写操作事务，使用 `BEGIN IMMEDIATE` 显式声明，防止在事务升级时发生死锁。
