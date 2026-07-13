# 数据库并发安全性与输入边界审查报告 (Challenger Report)

## 1. 观察到的事实 (Observation)
本项目采用 Python 内置的 `sqlite3` 作为轻量级持久层引擎。通过对 `src/database/db_manager.py` 和 `src/database/repository.py` 进行静态代码审查，具体发现如下事实：

### 1.1 并发与锁机制的设计
在 `src/database/db_manager.py` 中的 `connection` 上下文管理器实现中（第 29-32 行）：
```python
29:             if write:
30:                 conn.isolation_level = None
31:                 conn.execute("BEGIN IMMEDIATE")
32:             yield conn
```
当 `write=True` 时，连接的 `isolation_level` 被设置为 `None`（禁用 Python `sqlite3` 的隐式事务管理器以开启自动提交/手动控制模式），并显式执行了 `BEGIN IMMEDIATE` 语句。

在 `src/database/repository.py` 中，所有写操作（DML）方法在获取连接时都传递了 `write=True` 参数：
* `initialize_db` (第 23 行): `with self.db_manager.connection(write=True) as conn:`
* `add_member` (第 105 行): `with self.db_manager.connection(write=True) as conn:`
* `start_tournament` (第 147 行): `with self.db_manager.connection(write=True) as conn:`
* `end_tournament` (第 172 行): `with self.db_manager.connection(write=True) as conn:`
* `save_round_settlement` (第 213 行): `with self.db_manager.connection(write=True) as conn:`

### 1.2 参数绑定（防 SQL 注入）
在 `src/database/repository.py` 中，所有动态 SQL 参数输入均使用 `?` 占位符进行绑定。例如：
* `add_member` (第 108-111 行):
```python
108:                 cursor.execute(
109:                     "INSERT INTO members (name, historical_score) VALUES (?, ?)",
110:                     (name, historical_score)
111:                 )
```
* `save_round_settlement` (第 216-229 行 等):
```python
216:             cursor.execute(
217:                 """
218:                 INSERT INTO rounds (tournament_id, round_number, red_score, green_score, winner, banker_round_profit)
219:                 VALUES (?, ?, ?, ?, ?, ?)
220:                 """,
...
```
整个文件中未发现使用 `f-string` 或 `+` 进行 SQL 字符串拼接的操作。

### 1.3 CHECK 约束和数据完整性
在 `src/database/repository.py` 中的 `initialize_db` 方法（第 19-91 行）定义了以下 CHECK 约束：
* `tournaments` 表 (第 38 行): `status TEXT CHECK(status IN ('ongoing', 'ended')) NOT NULL DEFAULT 'ongoing'`
* `rounds` 表 (第 53 行): `winner TEXT CHECK(winner IN ('Red', 'Green')) NOT NULL`
* `bets` 表 (第 67, 68, 70 行):
  * `bet_amount INTEGER NOT NULL CHECK(bet_amount >= 0)`
  * `prediction TEXT CHECK(prediction IN ('Red', 'Green')) NOT NULL`
  * `is_player INTEGER CHECK(is_player IN (0, 1)) NOT NULL DEFAULT 0`
* `match_history` 表 (第 85 行): `winner TEXT CHECK(winner IN ('Red', 'Green')) NOT NULL`

但是，发现以下列缺少数据库级 CHECK 约束保护：
* `rounds.red_score` 和 `rounds.green_score` 缺少 `CHECK(red_score >= 0 AND green_score >= 0)`。
* `rounds.round_number` 缺少 `CHECK(round_number > 0)`。
* `match_history.red_score` 和 `match_history.green_score` 缺少 `CHECK(red_score >= 0 AND green_score >= 0)`。
* `match_history.round_number` 缺少 `CHECK(round_number > 0)`。
* `members.name` 缺少 `CHECK(length(name) > 0)`（可能插入空字符串）。
* `tournaments.end_time` 和 `tournaments.status` 缺少业务状态互斥约束（例如，ongoing 时 `end_time` 应为 NULL，ended 时应非空且晚于 `start_time`）。

### 1.4 自定义 Row Factory 的性能开销
在 `src/database/db_manager.py` 的 `dict_like_row_factory` 方法（第 41-74 行）中：
```python
41:     @staticmethod
42:     def dict_like_row_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
...
45:         class Row(dict):
...
```
`Row` 类是在 `dict_like_row_factory` 函数内部动态声明的。每当数据库查询返回一行数据时，该工厂函数就会被调用，从而重复执行 `class Row(dict)` 声明，产生额外的 CPU 和内存开销。

---

## 2. 逻辑推导链 (Logic Chain)

### 2.1 BEGIN IMMEDIATE 预防死锁的有效性
1. SQLite 在默认的 `DEFERRED` 事务模式下，事务启动时不获取排他锁，而在第一次执行写入（DML）时才会尝试将 `SHARED` 锁升级为 `RESERVED` 锁。
2. 若两个并发线程同时通过 `write=False`（或默认模式）读取数据，各持有一个 `SHARED` 锁。随后两个线程同时尝试写入，均需要将 `SHARED` 锁升级，导致死锁（即 `SQLITE_BUSY: database is locked`）。
3. 本项目在 `write=True` 时设置 `isolation_level = None`，并执行 `BEGIN IMMEDIATE`。
4. `BEGIN IMMEDIATE` 在事务启动时就立即尝试获取 `RESERVED` 锁。由于在 SQLite 中同一时刻只能有一个连接持有 `RESERVED` 锁，因此第二个尝试写入的事务在执行 `BEGIN IMMEDIATE`时就会被阻塞，直至第一个事务提交或回滚释放锁（或者等待繁忙超时）。
5. 这一机制防止了并发事务在已经读取并修改完内存状态后由于锁升级而发生相互阻塞，从而彻底规避了 SQLite 并发写入死锁风险。
6. 结合 `repository.py` 的静态代码，所有的写入入口均正确地带上了 `write=True`，保证了该机制的完整覆盖。

### 2.2 SQL 注入防护验证
1. SQL 注入是通过恶意拼接 SQL 语法结构改变原有查询语义的攻击手段。
2. 本项目所有的 SQL 语句均采用参数占位符（`?`），将 SQL 模板编译与动态参数传递解耦。
3. 数据库驱动（`sqlite3`）在接收到参数后，只会将其作为纯字面量（Literal Value）在运行时填入，即使输入中包含 `'; DROP TABLE...`，也只会被视作字符串或数值，无法被 SQLite 解析为可执行指令。
4. 静态审查确认 `Repository` 没有遗漏任何参数的绑定。SQL 注入防护达到 100% 的安全性。

### 2.3 边界完整性漏洞分析
1. 数据一致性依赖于数据库级强约束（CHECK/UNIQUE/FOREIGN KEY），以防止应用层逻辑漏洞漏掉非法边界值。
2. 目前 `rounds` 和 `match_history` 中均允许 `red_score`、`green_score` 为负数，或者 `round_number` 为负数/0。如果应用层异常传入了非法边界值，数据库将无法拦截。
3. `members.name` 允许为空字符串（`""`），这通常不符合业务直觉。
4. 虽然应用层（例如测试用例中）会有部分校验，但没有数据库级的 CHECK 约束作为最后一道防线，难以保证极端情况下的数据绝对完整性。

### 2.4 行工厂类重复创建分析
1. Python 中的 `class` 语句是动态执行的，每次执行 `dict_like_row_factory` 时都会重新创建 `Row` 类的元类和类型实例。
2. 在海量查询结果返回时，这种函数内定义类的写法会对 CPU 执行开销和垃圾回收（GC）产生不必要的额外压力，降低数据吞吐率。

---

## 3. 局限性与前提假设 (Caveats)
1. **未进行动态负载压测**：受制于绝对禁用终端命令的红线（🔒 ABSOLUTE TERMINAL COMMAND BAN），我们无法编写或运行高并发压力测试脚本（如多线程写入争抢）来测量高负载下 `OperationalError`（Busy Timeout）的实际发生率。
2. **Busy Timeout 依赖系统默认**：我们假设运行环境使用的是 SQLite 的默认繁忙超时设置（Python `sqlite3.connect` 默认为 5.0 秒）。如果高并发写事务单次耗时超过 5 秒，依然会导致部分并发写操作抛出 `database is locked` 异常。

---

## 4. 结论与建议 (Conclusion)
本项目当前的数据库并发设计（`BEGIN IMMEDIATE`）和 SQL 注入防护（参数绑定）整体上**非常安全且规范**，能够满足 Milestone 1 的基本安全要求。然而，在**数据完整性边界**和**性能优化**方面存在进一步优提升的空间。

### 建议采取的改进方案：

#### 方案一：强化数据库 CHECK 约束（防脏数据边界溢出）
修改 `repository.py` 的 `initialize_db` 逻辑，在创建表时为相应字段增加 CHECK 约束：
1. `members` 表的 `name` 字段：
   `CHECK(length(name) > 0)`
2. `rounds` 和 `match_history` 表的 `red_score`、`green_score`、`round_number` 字段：
   `CHECK(red_score >= 0 AND green_score >= 0 AND round_number > 0)`
3. `tournaments` 表的状态时间相关性：
   `CHECK((status = 'ongoing' AND end_time IS NULL) OR (status = 'ended' AND end_time IS NOT NULL))`
   `CHECK(end_time IS NULL OR end_time >= start_time)`

#### 方案二：优化 Row Factory 声明位置（提升性能）
将 `Row` 类的定义提升至 `db_manager.py` 的模块作用域（Module Level），避免在 `dict_like_row_factory` 内部进行高频动态定义。

---

## 5. 验证方法 (Verification Method)
由于无法运行命令，以下验证需由后续 Worker 或用户执行：

1. **运行现有测试套件**：
   ```bash
   pytest tests/database/test_repository.py
   pytest tests/database/test_repository_challenger.py
   ```
   验证在现有状态下，并发测试 `test_concurrency_locking_and_timeout` 以及边界测试 `test_integer_boundary_and_check_constraints` 均能正常通过。

2. **验证 CHECK 约束失效（在未优化前）**：
   可在测试文件中临时加入以下测试用例：
   ```python
   def test_missing_check_constraints(repo):
       # 应该抛出 IntegrityError，但目前由于缺少数据库约束，以下非负校验在 DB 层不会拦截
       with repo.db_manager.connection(write=True) as conn:
           conn.execute(
               "INSERT INTO rounds (tournament_id, round_number, red_score, green_score, winner, banker_round_profit) VALUES (1, -1, -5, -10, 'Red', 0)"
           )
   ```
   若此插入未报错，则证实数据完整性在数据库层存在缺口。

3. **静态代码核对**：
   使用文本工具或 IDE 全文检索 `execute(`，确认是否存在除 `?` 以外的字符串拼接（如 `execute(f"...{var}...")`）。审查确认无任何拼接注入点。
