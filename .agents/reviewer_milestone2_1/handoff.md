# Handoff Report - Milestone 2 Betting Engine Review

## 1. 观察 (Observation)

通过对核心业务逻辑验证与结算引擎 `src/engine/betting_engine.py` 以及单元测试 `tests/engine/test_betting_engine.py` 进行静态代码走读，观察到以下具体内容：

1. **核心文件及结构**：
   - `src/engine/betting_engine.py` (共 241 行)：
     - 定义了自定义异常类：`BetValidationError`, `InvalidMultipleOfFiveError`, `ExceedMaxLimitError`, `NegativeBetAmountError`, `MatchResultValidationError`, `TeamBindingValidationError`。
     - 实现了验证函数：`validate_bet` (投注限额与5倍数验证)、`validate_match_score` (七局四胜比分验证)、`validate_team_bindings` (战队及投注人绑定交叉校验)。
     - 实现了结算函数：`calculate_settlement` (1:1 结算分值守恒算法，支持字典列表及 dataclass 实例列表)。
   - `tests/engine/test_betting_engine.py` (共 262 行)：
     - 针对上述业务函数，编写了 12 个测试用例，覆盖了合法投注、负数投注、超额投注、非5倍数投注、合法及非法比分判定、合规及违规绑定校验，以及字典和 `Bet` 实例的 1:1 分值守恒和只读不变性。

2. **规范及约束校验**：
   - 所有的代码注释、Docstring 均使用**简体中文**编写。
   - 所有类、方法和函数均包含作者署名 `@author hyq` 以及日期 `@version 2026-07-13`。
   - 没有发现硬编码测试结果等作弊行为。

3. **具体代码实现片段**：
   - 在 `src/engine/betting_engine.py` 第 163-166 行中，清除和提取姓名的逻辑为：
     ```python
     clean_red_players = [p.strip() for p in red_players if p]
     clean_green_players = [p.strip() for p in green_players if p]
     clean_red_bettors = [_extract_name(b) for b in red_bettors if b]
     clean_green_bettors = [_extract_name(b) for b in green_bettors if b]
     ```
   - 在 `src/engine/betting_engine.py` 第 122-135 行中，提取纯姓名的逻辑为：
     ```python
     def _extract_name(name_str: str) -> str:
         name = name_str
         if '(' in name:
             name = name.split('(')[0]
         if '（' in name:
             name = name.split('（')[0]
         return name.strip()
     ```
   - 在 `src/engine/betting_engine.py` 第 137-187 行的 `validate_team_bindings` 仅包含 4 项重叠/交叉校验，没有进行单队内部投注去重校验。
   - 在 `src/engine/betting_engine.py` 第 188-240 行的 `calculate_settlement` 通过 `total_profit_loss` 累加玩家的 `profit_loss`，并最终定义 `banker_round_profit = -total_profit_loss`。

---

## 2. 逻辑链 (Logic Chain)

根据上述观察，推导出以下逻辑链：

1. **仅含空格的姓名过滤漏洞**：
   - 在 `validate_team_bindings` 中，列表推导式使用 `if p` 来过滤非空值。
   - 如果列表中包含只含空格的字符串（如 `"   "`），在 Python 中其布尔值为 `True`，因此能绕过 `if p` 过滤。
   - 随后调用的 `p.strip()` 会将其转换为空字符串 `""` 并存入 `clean_red_players` 中。
   - 如果绿队也以同样的方式过滤到了仅含空格的字符串，则 `clean_red_players` 和 `clean_green_players` 的交集 `duplicate_players = set(clean_red_players) & set(clean_green_players)` 中将包含空字符串 `""`，从而抛出不合逻辑的 `TeamBindingValidationError("成员不能同时是红队和绿队队员: {''}")`。
   - 如果仅单边包含空格字符串，它将被作为空字串 `""` 存储，绕过校验，进入底层，增加了存储空字符串数据的风险。

2. **单队内部重复下注校验缺失**：
   - `validate_team_bindings` 分别校验了：(a) 队员重叠；(b) 投注人重叠；(c) 红队队员投绿队；(d) 绿队队员投红队。
   - 但是，如果 `red_bettors` 内部传入了重复的投注人（例如 `["张三 (10)", "张三 (20)"]`），该方法由于没有同队去重验证而直接认为其合法。
   - 然而，数据库 `bets` 表中存在联合唯一约束 `UNIQUE (round_id, member_id)`。当保存该结算结果时，底层将触发 `sqlite3.IntegrityError` 导致事务崩溃回滚，未能通过引擎层的验证异常给出友好的错误提示。

3. **分值守恒正确性**：
   - 在 `calculate_settlement` 中，庄家单轮盈亏被算作 `banker_round_profit = -total_profit_loss`。
   - 每一个玩家猜对时 `profit_loss = bet_amount`，猜错时 `profit_loss = -bet_amount`。
   - 这在数学上天然确保了：所有玩家的盈亏之和 + 庄家盈亏 = `total_profit_loss + (-total_profit_loss) = 0`，即分值完美守恒，完全符合 1:1 结算守恒算法的要求。

---

## 3. 局限性与假设 (Caveats)

1. **绝对终端禁令**：由于本任务中包含极其严格的终端指令禁令，无法在本地运行 Python 或 Pytest 进行物理边界场景的测试执行，所有分析和测试结论均建立在静态代码走读的推理基础之上。
2. **测试数据假设**：我们假设传入的投注记录中 `bet_amount` 均是能够被 `validate_bet` 正确验证的合法数值，即在传入 `calculate_settlement` 之前就已经完成了限额与5倍数的校验。

---

## 4. 结论 (Conclusion)

### 评审结论：REQUEST_CHANGES (要求整改)

---

### 核心质量评估报告 (Quality Review Report)

#### 1. 发现问题 (Findings)

##### 🟡 主要缺陷 (Major) 1: 仅含空格的成员姓名可绕过非空校验并导致错误拦截
- **具体表现**：`src/engine/betting_engine.py` 第 163-166 行过滤逻辑中使用 `if p` 和 `if b` 无法识别仅含空格的非空字符串（如 `"   "`），在转换为 `""` 放入清理集合后可能因为空字串重叠而导致不合逻辑地触发 `TeamBindingValidationError`。
- **潜在危害**：如果前端传参或接口调用时混入了空格，将导致正常的对局校验被错误地拦截，或者将无效的 `""` 成员数据绕过校验带入数据库。
- **改进建议**：修改过滤条件，在判断非空时一并过滤掉空白字符，例如：
  ```python
  clean_red_players = [p.strip() for p in red_players if p and p.strip()]
  clean_green_players = [p.strip() for p in green_players if p and p.strip()]
  clean_red_bettors = [_extract_name(b) for b in red_bettors if b and b.strip()]
  clean_green_bettors = [_extract_name(b) for b in green_bettors if b and b.strip()]
  ```

##### 🟡 主要缺陷 (Major) 2: 缺乏对单队内部重复下注人校验，容易触发 SQLite 唯一约束崩溃
- **具体表现**：`validate_team_bindings` 没有判断 `red_bettors` 和 `green_bettors` 各自内部是否包含重复的成员姓名。
- **潜在危害**：无法在业务层拦截“单人在同一队内下注多次”的违规行为，导致该错误数据传递到 Repository 事务层时触发底层 SQLite 抛出 `sqlite3.IntegrityError` 唯一性冲突，影响系统健壮性。
- **改进建议**：在 `validate_team_bindings` 中，增加对单队内部去重后长度一致性的校验：
  ```python
  if len(clean_red_bettors) != len(set(clean_red_bettors)):
      raise TeamBindingValidationError("红队投注人列表中存在重复成员")
  if len(clean_green_bettors) != len(set(clean_green_bettors)):
      raise TeamBindingValidationError("绿队投注人列表中存在重复成员")
  ```

##### 🟢 次要缺陷 (Minor) 3: 输入参数缺乏防御性 `None` 与类型校验
- **具体表现**：如果 `red_players` 等参数传入 `None`，方法会直接抛出 `TypeError: 'NoneType' object is not iterable`。
- **潜在危害**：抛出 Python 原生 TypeError 而不是业务异常，会增加上层组件的错误处理复杂度。
- **改进建议**：在校验方法最开始添加防空赋空防御，例如 `red_players = red_players or []`。

#### 2. 已验证声明 (Verified Claims)
- **1:1 结算分值守恒算法正确性** -> 通过静态公式代入验证 `banker_round_profit == -sum(profit_loss)` 确保双方盈亏之和严格为 0 -> **PASS**。
- **战队绑定交叉重叠与跨队投注逻辑** -> 静态分析集合求交 `set(clean_red_players) & set(clean_green_bettors)` 符合业务契约 -> **PASS**。
- **七局四胜比分胜负判定** -> 判定 `red_score == 4 and green_score < 4` 则红赢；`green_score == 4 and red_score < 4` 则绿赢；其余全部抛出 `MatchResultValidationError` -> 符合七局四胜制完备性定义 -> **PASS**。

#### 3. 覆盖范围与漏洞评估 (Coverage Gaps & Risk)
- **输入数据非整型边界风险**（低风险）：若投注金额 `amount` 或比分传入了浮点数（如 `amount = 5.0` 或 `red_score = 4.0`），在 Python 的弱类型比较下虽然可以判定等值，但可能导致下游数据库字段（设计为整型）类型不匹配风险。建议在引擎前置增加类型防错。

#### 4. 未验证项 (Unverified Items)
- **单元测试在本地执行的真实通过率**：受限于终端命令禁用约束，无法物理运行 `pytest`。

---

### 对抗性评估报告 (Adversarial Review Report)

#### 1. 假设压力测试挑战 (Challenges)

##### 🔴 关键挑战 (Critical) 1: 仅含空格的成员名导致防御性逻辑“自相残杀”并引起误拦截
- **被挑战假设**：只要不是 `None` 或空值，输入就能安全通过 `p.strip()` 洗净并不造成判定误伤。
- **攻击场景**：
  在初始化一局比赛时，前台可能误传入带有空格的参数 `red_players = ["   "]` 和 `green_players = ["   "]`。
  - 第一步，`if p` 判定为 True。
  - 第二步，`p.strip()` 使得 clean 后的两个列表皆为 `[""]`。
  - 第三步，判定互斥逻辑：`set([""]) & set([""])` 为 `set([""])`。
  - 第四步，判定不为空，抛出 `TeamBindingValidationError`，提示 `成员不能同时是红队和绿队队员`。
  本应被作为空数据过滤的空格数据，却因为清洗策略漏洞相互交织，导致合规的队伍绑定被拦截。
- **破坏范围**：游戏对局创建功能受阻，接口误报绑定异常。
- **缓解措施**：在列表推导中加入过滤掉 strip 之后长度为 0 的条件。

##### 🟡 主要挑战 (Major) 2: 单人多次投注同一队伍直接引起数据库写事务崩溃
- **被挑战假设**：上层或前端传入的 `red_bettors` 与 `green_bettors` 必然是一人一注干净的。
- **攻击场景**：
  若有人蓄意或者并发地发出两笔投注，例如对红队投注 `"棉花 (10)"` 和 `"棉花 (20)"`。
  - 绑定校验由于两队不交叉，判定为通过。
  - 进入 `calculate_settlement` 成功输出两个独立的 `Bet` 实例（分别对应同一 member_id 下注 10 和 20）。
  - 进入 Repository 中的保存轮次结算逻辑 `save_round_settlement`，在批量向 `bets` 表插入时，第二笔数据将因为触发 `UNIQUE (round_id, member_id)` 而抛出 `IntegrityError`。
- **破坏范围**：该轮次的所有投注结果均无法写入并发生回滚，系统产生 raw exception，缺少优雅提示。
- **缓解措施**：在引擎层对投注人本身的唯一性进行前置限制校验。

#### 2. 压力测试结果预测与场景 (Stress Test Results)
- 场景 A：传入 `red_players=["  "]`, `green_players=["  "]` -> 预测表现：误触发 `TeamBindingValidationError`。
- 场景 B：传入 `red_bettors=["A (10)", "A (20)"]` -> 预测表现：校验通过，但持久化到 Repository 时事务由于 `IntegrityError` 回滚崩溃。
- 场景 C：传入 `amount = 25`, `max_limit = 20` -> 预测表现：准确拦截，抛出 `ExceedMaxLimitError` (PASS)。
- 场景 D：传入 `red_score = 4`, `green_score = 4` -> 预测表现：准确拦截，抛出 `MatchResultValidationError` (PASS)。

#### 3. 未挑战的盲区 (Unchallenged Areas)
- 对字典结构数据中缺失 `prediction` 键的情形，目前依靠 `new_bet.get('prediction')` 获得 `None`，这在后续与 `winner` 比较时不相等，最终会计算为 `profit_loss = -bet_amount`。在未对 prediction 字段合法性进行验证的情况下，会导致漏判的投注直接算输，未做报错处理。

---

## 5. 验证方法 (Verification Method)

在放开终端禁令的测试环境下，可以使用以下命令独立验证：

1. **测试用例运行命令**：
   ```powershell
   $env:PYTHONPATH="." ; pytest tests/engine/test_betting_engine.py
   ```
2. **需人工审查的文件**：
   - `src/engine/betting_engine.py` (核对 `validate_team_bindings` 过滤与去重校验逻辑)
   - `tests/engine/test_betting_engine.py` (核对对应的去重测试及空格边界测试是否存在)
3. **失效条件 (Invalidation Conditions)**：
   - 运行上述 pytest 命令发现测试套件中未能全面检测空格边界以及去重绑定测试；
   - 在进行上述优化修改后，原有的 tests 无法通过。
