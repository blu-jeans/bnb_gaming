# Challenger Review Report - Milestone 1 Challenger 4

## 1. 观察到的现象 (Observation)
- **文件路径**: `src/database/db_manager.py` 和 `src/database/repository.py`。
- **并发控制**:
  - `src/database/db_manager.py` 第 29-31 行：
    ```python
    if write:
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
    ```
    写连接会强制将 `isolation_level` 设置为 `None`，并执行 `BEGIN IMMEDIATE` 以获取 `RESERVED` 锁，避免写写死锁。
  - `src/database/db_manager.py` 第 23 行：
    ```python
    conn = sqlite3.connect(self.db_path)
    ```
    未配置连接的 `timeout` 参数（默认使用 python sqlite3 的 5.0 秒），且未启用 WAL 模式（即未执行 `PRAGMA journal_mode = WAL;`）。
  - `src/database/db_manager.py` 第 41-74 行的 `Row` 类定义在 `dict_like_row_factory` 方法内部：
    ```python
    @staticmethod
    def dict_like_row_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
        class Row(dict):
            ...
        ...
        return Row(keys, row)
    ```
    这导致每次调用 `row_factory`（即查询结果中的每一行）时，都会在局部作用域内动态定义一个新的 `Row` 类。
- **参数绑定**:
  - 在 `src/database/repository.py` 中，所有写操作（如第 109, 153, 190, 218, 235, 252, 266, 276 行等）和读操作（如第 116, 156, 175, 183, 194, 290, 335 行等）均使用 `?` 占位符进行参数绑定。例如：
    ```python
    cursor.execute("INSERT INTO members (name, historical_score) VALUES (?, ?)", (name, historical_score))
    ```
- **数据完整性 (CHECK 约束)**:
  - `src/database/repository.py` 中的建表语句中只定义了以下 CHECK 约束：
    - `tournaments.status`: `CHECK(status IN ('ongoing', 'ended'))` (第 38 行)
    - `rounds.winner`: `CHECK(winner IN ('Red', 'Green'))` (第 53 行)
    - `bets.bet_amount`: `CHECK(bet_amount >= 0)` (第 67 行)
    - `bets.prediction`: `CHECK(prediction IN ('Red', 'Green'))` (第 68 行)
    - `bets.is_player`: `CHECK(is_player IN (0, 1))` (第 70 行)
    - `match_history.winner`: `CHECK(winner IN ('Red', 'Green'))` (第 85 行)
  - 缺失的 CHECK 约束包括：
    - 成员姓名非空检查（如限制 `name` 不能为 `""`）。
    - 锦标赛结束时间不早于开始时间检查（如限制 `end_time >= start_time`）。
    - 轮次号正数检查（如限制 `round_number > 0`）。
    - 轮次得分非负检查（如限制 `red_score >= 0` 和 `green_score >= 0`）。
    - 赢家与得分一致性检查（如限制如果赢家为 `'Red'` 则红队得分大于或等于绿队得分，反之亦然）。

## 2. 逻辑链条 (Logic Chain)
- **并发锁分析**:
  1. 基于观察，当 `write=True` 时，连接使用 `BEGIN IMMEDIATE`，它会立即获取 `RESERVED` 锁。这确保了在同一个数据库文件上，只有一个写事务可以进行，从而避免了两个 `DEFERRED` 事务同时尝试升级为写锁时造成的死锁 (SQLITE_BUSY)。
  2. 然而，当 `write=False`（默认读连接）时，`DBManager.connection` 不会修改 `isolation_level`，这允许开发者使用该连接执行写操作。如果开发者在默认的 `write=False` 连接中执行写操作，SQLite 会启动一个 `DEFERRED` 事务，破坏了 `BEGIN IMMEDIATE` 锁防范设计，再次引入并发写死锁的隐患。
  3. 此外，未启用 WAL（Write-Ahead Logging）模式。在传统的 Rollback Journal 模式下，写事务在写入数据时（升级到 `EXCLUSIVE` 锁）会完全阻塞所有读操作，反之亦然。这在高并发场景下会导致频繁的 `sqlite3.OperationalError: database is locked`。
- **性能和内存瓶颈分析**:
  1. `dict_like_row_factory` 中在函数体内动态定义 `Row` 类。
  2. 因为 SQLite 的 `row_factory` 是针对查询结果的**每一行**分别调用的，这意味着如果一个查询返回 10,000 行，Python 将动态定义 `Row` 类 10,000 次，产生大量的垃圾回收 (GC) 和内存分配开销。
- **SQL 注入分析**:
  1. 静态审查 `repository.py` 中的所有 SQL 执行语句。
  2. 发现所有的 SQL 查询均为硬编码的静态字符串，并使用 `?` 占位符将参数传递给 `cursor.execute`。
  3. 因此，用户输入被严格限制为数据参数，无法篡改 SQL 语法树，防御 SQL 注入是完备的。
- **数据完整性分析**:
  1. 现有的 CHECK 约束限制了状态枚举、投注金额非负及布尔标志，但缺失了其他核心业务逻辑约束。
  2. 例如，如果数据库中插入了 `red_score = -5` 或者 `end_time` 早于 `start_time` 的数据，SQLite 不会报错，这破坏了数据的真实性。
  3. 同样，如果没有赢家与得分的一致性约束，可能出现 `red_score=3`, `green_score=1` 但 `winner='Green'` 的不一致垃圾数据。

## 3. 局限性与假设 (Caveats)
- 仅进行了静态代码审查，未实际运行测试脚本或在并发环境下执行压力测试（依据绝对终端命令禁令）。
- 假定 SQLite 数据库的引擎版本支持标准的 SQL-92 CHECK 约束（在 SQLite 3.3.0+ 中均已默认支持并启用）。
- 假定在 `write=False` 时，开发规范要求绝对不允许执行任何写操作，但该要求在代码层面未被强制约束。

## 4. 结论 (Conclusion)
- **安全性评估**:
  - **SQL 注入**: **极低风险**。参数绑定应用非常彻底，无注入漏洞。
  - **并发安全性**: **中等风险**。`BEGIN IMMEDIATE` 能够防止写写死锁，但由于未启用 WAL 模式，且读连接未在代码层面限制写入，高并发读写仍有较大的概率触发 `database is locked` 错误。
  - **数据完整性**: **中等风险**。关键字段缺乏 CHECK 约束保护（如得分非负、姓名非空、时间顺序、赢家得分一致性），可能导致逻辑异常的数据写入数据库。
  - **性能缺陷**: **高风险**。`Row` 类动态定义机制对大批量数据读取性能非常不利。
- **改进建议**:
  1. 将 `Row` 类的定义移出 `dict_like_row_factory` 方法，定义为模块级别的类，避免动态创建。
  2. 在 `DBManager.connection(write=False)` 时，通过执行 `PRAGMA query_only = ON;` 强制将连接限制为只读，或者使用 SQLite URI 只读模式，防止开发人员误用。
  3. 在初始化数据库时执行 `PRAGMA journal_mode = WAL;` 以启用 WAL 模式，提高并发读写性能。
  4. 补全缺失的 CHECK 约束：
     - `members.name`: `CHECK(length(name) > 0)`
     - `tournaments`: `CHECK(end_time IS NULL OR end_time >= start_time)`
     - `rounds` / `match_history`: `CHECK(round_number > 0)`, `CHECK(red_score >= 0)`, `CHECK(green_score >= 0)`
     - `rounds` / `match_history`: `CHECK((winner = 'Red' AND red_score >= green_score) OR (winner = 'Green' AND green_score >= red_score))`

## 5. 验证方法 (Verification Method)
- **静态验证**: 检查 `db_manager.py` 和 `repository.py` 的代码逻辑。
- **测试套件运行**: 使用项目自带的 pytest 测试用例（如运行 `pytest tests/database/test_repository_challenger.py`），验证当前的并发和边界测试是否通过。
- **检查失效条件**: 若在并发测试中频繁发生 `database is locked` 错误，或者在数据库中成功插入了负数得分、空名字或非逻辑一致的赢家数据，则说明验证失败。
