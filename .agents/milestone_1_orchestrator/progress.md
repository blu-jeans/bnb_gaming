## Current Status
Last visited: 2026-07-13T16:26:30+08:00

- [x] DB Schema & Tables Setup (db_manager.py, models.py)
- [x] Transactional CRUD Operations (repository.py)
- [x] Unit Test Implementation and Verification (tests/)

## Iteration Status
Current iteration: 2 / 32

## Retrospective Notes
### What Worked (成功经验)
- **多代理并发分析与评审**：通过 Explorer 和 Reviewer 对代码进行多轮交叉静态分析，高效拦截了 Row Factory 私有键污染、连接泄漏隐患和 SQL 注入等问题。
- **事务锁强化 (BEGIN IMMEDIATE)**：在 SQLite 并发读写环境下，采用 `BEGIN IMMEDIATE` 手动管理写事务，保证了排他性，避免了死锁的发生，并在测试中验证了事务原子性。

### What Didn't (不足之处)
- **测试框架和 GUI 实现在设计初期缺乏统一规范**：E2E 测试 track 的 mock GUI 对大小写、积分默认值（1000 vs 0）的初始定义与 Repository 存在不一致，导致首轮评审出现 Schema 不兼容的问题。第二轮迭代中，我们直接在 Repository 数据层对齐了 E2E 的大小写及默认分值规范。
- **行工厂动态声明开销**：在函数体内动态声明 Row 类会造成微小的重复编译开销，后续重构时建议将 Row 类提升到模块级作用域。

### Lessons Learned & Process Improvements (教训与流程建议)
- **前后端/数据逻辑接口应在 Milestone 0 阶段彻底对齐并锁死契约**，避免因为状态枚举值（ONGOING/ongoing）等细小差异导致中途重构。
- **测试环境数据隔离**：在进行单元测试时，通过 tempfile 动态生成并及时清理磁盘型 SQLite 测试文件，成功规避了内存连接隔离性丢失和物理脏文件污染的问题。
