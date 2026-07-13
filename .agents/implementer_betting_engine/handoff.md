# Handoff Report — 2026-07-13T16:33:00Z

## 1. Observation
- 任务要求创建并实现核心业务逻辑验证与结算引擎 `src/engine/betting_engine.py` 及其单元测试 `tests/engine/test_betting_engine.py`。
- 项目数据库模型定义文件位于 `src/database/models.py`，其中包含 `TeamColor` 与 `Bet` 的定义：
  - Line 19: `class TeamColor(StrEnum): RED = "Red", GREEN = "Green"`
  - Line 65: `@dataclass(frozen=True) class Bet:`
- 约束条件中包含：
  - "绝对禁止运行任何 python、pytest、pyinstaller 或其他测试与启动命令。（必须严格遵守，绝对不要执行测试命令！）"
  - "在每个类/方法的 JavaDoc/注释中，固定作者署名 @author hyq，版本日期写 2026-07-13。"
  - "所有代码注释及文档必须使用简体中文。"

## 2. Logic Chain
- **异常定义**：按照要求定义了 6 个自定义异常类（`BetValidationError`, `InvalidMultipleOfFiveError`, `ExceedMaxLimitError`, `NegativeBetAmountError`, `MatchResultValidationError`, `TeamBindingValidationError`），它们均继承自 `ValueError`，且前三者属于投注验证的具体派生。
- **投注验证 (`validate_bet`)**：对 `amount` 进行多重条件检查：如果是负数抛出 `NegativeBetAmountError`；如果大于 `max_limit` 抛出 `ExceedMaxLimitError`；如果为0或非5的倍数抛出 `InvalidMultipleOfFiveError`；合规返回 `True`。
- **比分验证 (`validate_match_score`)**：根据七局四胜制（Best of Seven），红绿队得分必须非负，且一队为 4 另一队小于 4。判定并返回对应的 `TeamColor` 赢家，否则抛出 `MatchResultValidationError`。
- **绑定验证 (`validate_team_bindings`)**：
  - 使用辅助函数 `_extract_name` 剥离金额括号，例如将 `"姓名 (金额)"` 或 `"姓名（金额）"` 转换为 `"姓名"`。
  - 检查队员互斥（`red_players & green_players`）。
  - 检查投注人互斥（`red_bettors & green_bettors`）。
  - 严格限制队员不能买对手队伍：红队队员不能出现在绿队投注人里，绿队队员不能出现在红队投注人里。
  - 任何不合规关系触发 `TeamBindingValidationError`。
- **结算与分值守恒 (`calculate_settlement`)**：
  - 遍历所有下注（支持字典或 `Bet` 实例）。对于 `Bet` 实例（frozen dataclass），利用 `dataclasses.replace` 返回全新实例；
  - 个人盈亏计算：猜中为正，猜错为负。
  - 庄家单轮净盈亏计算为所有选手盈亏之和的相反数：`banker_round_profit = -sum(player_profit_loss)`，保证 `sum(profit_loss) + banker_round_profit == 0`，完美实现守恒。
- **单元测试**：编写了 `tests/engine/test_betting_engine.py`，完整覆盖上述所有边界条件。

## 3. Caveats
- 按照指令约束，**完全没有在终端中运行任何测试或执行脚本命令**。代码的正确性是通过严格的静态逻辑推理和对已有项目代码风格的模仿保障的。
- 假设输入的投注列表 `bets` 中的成员对象类型只为 `dict` 或具备 `prediction`/`bet_amount` 属性的类（如 `Bet`），若传入其他类型未定义此接口，将可能抛出 AttributeError。

## 4. Conclusion
- 完美完成了核心验证与结算逻辑文件 `src/engine/betting_engine.py` 的编写，并配备了高覆盖率 of 单元测试 `tests/engine/test_betting_engine.py`。
- 所有代码均配有符合规范的中文注释与作者署名（@author hyq, @version 2026-07-13）。

## 5. Verification Method
- 用户或审计员可在项目根目录下运行以下命令来进行测试验证：
  `pytest tests/engine/test_betting_engine.py`
- 可通过直接查看以下两个文件来确认其编码规范与逻辑正确性：
  - `src/engine/betting_engine.py`
  - `tests/engine/test_betting_engine.py`
