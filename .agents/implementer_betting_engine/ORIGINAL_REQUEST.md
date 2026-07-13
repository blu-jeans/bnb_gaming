## 2026-07-13T16:30:00Z

你是 Betting Engine Implementer。你的任务是实现核心业务逻辑引擎 src/engine/betting_engine.py，并编写单元测试 tests/engine/test_betting_engine.py。

### 代码要求
1. 在 `src/engine/betting_engine.py` 中：
   - 编写以下自定义异常类（继承自 ValueError 或更具体的类）：
     - `BetValidationError`
     - `InvalidMultipleOfFiveError`
     - `ExceedMaxLimitError`
     - `NegativeBetAmountError`
     - `MatchResultValidationError`
     - `TeamBindingValidationError`
   - 实现以下验证与计算函数：
     - `validate_bet(amount: int, max_limit: int) -> bool`:
       - 验证投注金额：不能为负数，不能超过单轮上限 max_limit，且必须是 5 的倍数。
       - 合法则返回 True；非法则抛出对应的异常（例如 NegativeBetAmountError, ExceedMaxLimitError, InvalidMultipleOfFiveError）。
     - `validate_match_score(red_score: int, green_score: int) -> TeamColor`:
       - 验证是否符合七局四胜制（一方必须恰好是 4，且另一方必须小于 4 且不能为负数）。
       - 合法则返回赢家颜色 TeamColor.RED 或 TeamColor.GREEN（在 src.database.models 中导入 TeamColor）。
       - 非法则抛出 MatchResultValidationError 异常。
     - `validate_team_bindings(red_players: list[str], green_players: list[str], red_bettors: list[str], green_bettors: list[str]) -> None`:
       - 校验队伍绑定关系：任何成员不能同时在红队队员和绿队队员列表中（互斥关系验证）。若重复，抛出 TeamBindingValidationError。
       - 严格约束验证：队员只能投注自己所在的队伍。红队队员不能出现在 green_bettors 中，绿队队员不能出现在 red_bettors 中。若违反，抛出 TeamBindingValidationError。
       - 说明：投注人列表中成员可以表示为纯姓名字符串（如 "张三"），若传入 "张三 (10)" 这种带金额的形式，请在校验时剥离金额提取姓名再进行比对。
     - `calculate_settlement(bets: list, winner: TeamColor) -> dict`:
       - 核心 1:1 结算分值守恒算法。
       - 支持传入 Bet 实例列表，也支持传入字典列表。如果是 Bet 实例列表，由于 Bet 是 frozen dataclass，应使用 dataclasses.replace 返回全新的 Bet 列表。
       - 计算每个投注的盈亏（猜对 profit_loss = bet_amount；猜错 profit_loss = -bet_amount）。
       - 计算庄家单轮净盈亏（banker_round_profit = 输家投注额之和 - 赢家投注额之和 = 所有人盈亏取反之和）。
       - 返回格式：{"settlements": list, "banker_round_profit": int}，保证所有投注 of profit_loss 之和加上庄家盈亏绝对为 0。

2. 在 `tests/engine/test_betting_engine.py` 中编写对应的 pytest 单元测试用例，覆盖：
   - 投注金额各种有效/无效边界情况。
   - 各种比分边界情况（4-0 至 4-3, 3-3, 5-2, 4-4, 负数比分等）。
   - 队伍互斥与队员不能投注对方队伍的规则校验。
   - 结算在不同输入类型（Bet 模型、字典形式）下的正确性及分值严格守恒。

### 约束与规范
- 绝对禁止运行任何 python、pytest、pyinstaller 或其他测试与启动命令。（必须严格遵守，绝对不要执行测试命令！）
- 所有代码注释及文档必须使用简体中文。
- 在每个类/方法的 JavaDoc/注释中，固定作者署名 @author hyq，版本日期写 2026-07-13。
- 不要引入 Java 8 Stream 等不合时宜的高级炫技写法（此处为 Python 代码，遵循 Pythonic 的简洁写法即可，避免过度复杂的设计）。
- 就地编写修改文件，不要输出代码片段让用户手动拷贝。

## 2026-07-13T16:35:57Z

你是 Betting Engine Repair Worker。你的任务是根据代码审查意见对 `src/engine/betting_engine.py` 和 `tests/engine/test_betting_engine.py` 进行重构和修复。

### 修改项要求
1. 在 `src/engine/betting_engine.py` 中：
   - **导入模块**：导入 `re` 用于正则匹配。
   - **投注限额防御性类型校验**：在 `validate_bet` 开头增加校验：金额必须为整型且不能为布尔型（例如 `isinstance(amount, int) and not isinstance(amount, bool)`），否则抛出 `BetValidationError`。
   - **正则姓名提取优化**：在 `_extract_name` 中，使用 `re.sub(r'\s*[\(（]\d+[\)）]\s*$', '', name_str).strip()` 清除末尾的投注金额信息，这样能避免当姓名本身带有括号（如 `"张三(小张) (10)"`）时造成误截断。
   - **防空拦截**：在 `validate_team_bindings` 开头，对传入的 4 个列表参数做默认空值防空处理（若为 `None` 则赋予空列表 `[]`）。
   - **空格姓名拦截**：过滤姓名逻辑应修改为过滤掉 strip 之后长度为 0 的无效姓名（如使用 `if p and p.strip()`），防止仅含空格的成员名绕过非空校验并导致后续集合误伤。
   - **单队内重复校验**：在 `validate_team_bindings` 中校验单队内是否存在重复姓名，若存在重复则抛出 `TeamBindingValidationError`。具体需要检查：
     - `clean_red_players` 内有无重复
     - `clean_green_players` 内有无重复
     - `clean_red_bettors` 内有无重复（剥离金额后）
     - `clean_green_bettors` 内有无重复（剥离金额后）
   - **大小写敏感校验强化**：在校验队员和投注人重叠、交叉购买对手战队时，进行大小写归一化判定（如使用 `.lower()` 进行求交集判定，防止大小写差异绕过安全校验限制），但抛出异常的提示中可以展示原始成员姓名。

2. 在 `tests/engine/test_betting_engine.py` 中，新增以下边界与对抗性测试用例：
   - **浮点数及布尔值校验**：测试传入 `5.0` 或 `True` 等非法类型。
   - **姓名提取测试**：测试 `"张三(小张) (10)"` 是否能够正确提取为 `"张三(小张)"`；测试中英文混用括号清洗。
   - **空格名过滤测试**：测试仅含空格的名字 `"   "` 是否被成功过滤且不造成队伍互斥校验的误报。
   - **单队内部去重校验**：测试红队或绿队内部有重复姓名、下注人有重复姓名时（如 `["棉花 (10)", "棉花 (20)"]`）抛出 `TeamBindingValidationError`。
   - **大小写不敏感匹配验证**：测试红队队员 `"Alice"` 与绿队投注人 `"alice (10)"` 是否能被大小写归一化拦截。

### 约束与规范
- 绝对禁止运行任何 python、pytest、pyinstaller 或其他测试与启动命令。（必须严格遵守，绝对不要执行测试命令！）
- 所有代码注释及文档必须使用简体中文。
- 在每个类/方法的 JavaDoc/注释中，固定作者署名 @author hyq，版本日期写 2026-07-13。
- 就地编写修改文件，直接覆盖原文件，不要输出代码片段让用户手动拷贝。

⚠️ MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

请立即开始修改并覆盖对应的代码文件。完成后，向我发送 handoff 报告，列出修改的代码与通过的静态校验点。
