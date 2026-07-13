# -*- coding: utf-8 -*-
"""
@author hyq
@version 2026-07-13
核心业务逻辑验证与结算引擎
"""

# hyq: 2026-07-13 Add re module import
import re
from dataclasses import replace
from src.database.models import TeamColor

class BetValidationError(ValueError):
    """
    投注验证异常基类
    
    @author hyq
    @version 2026-07-13
    """
    pass

class InvalidMultipleOfFiveError(BetValidationError):
    """
    投注金额不是5的倍数（或为0）异常
    
    @author hyq
    @version 2026-07-13
    """
    pass

class ExceedMaxLimitError(BetValidationError):
    """
    投注金额超过单轮上限异常
    
    @author hyq
    @version 2026-07-13
    """
    pass

class NegativeBetAmountError(BetValidationError):
    """
    投注金额为负数异常
    
    @author hyq
    @version 2026-07-13
    """
    pass

class MatchResultValidationError(ValueError):
    """
    比赛比分结果验证异常
    
    @author hyq
    @version 2026-07-13
    """
    pass

class TeamBindingValidationError(ValueError):
    """
    队伍绑定关系验证异常
    
    @author hyq
    @version 2026-07-13
    """
    pass

def validate_bet(amount: int, max_limit: int) -> bool:
    """
    验证投注金额是否合法。
    投注金额不能为负数，不能超过单轮上限 max_limit，且必须是 5 的倍数且不能为 0。
    
    @author hyq
    @version 2026-07-13
    
    Args:
        amount (int): 投注金额
        max_limit (int): 单轮最大上限
        
    Returns:
        bool: 合法则返回 True
        
    Raises:
        NegativeBetAmountError: 如果金额为负数
        ExceedMaxLimitError: 如果金额超过 max_limit
        InvalidMultipleOfFiveError: 如果金额不是5的倍数（或为0）
    """
    # hyq: 2026-07-13 Add defensive check for bet amount type
    if not (isinstance(amount, int) and not isinstance(amount, bool)):
        raise BetValidationError("投注金额必须为整型且不能为布尔型")
    if amount < 0:
        raise NegativeBetAmountError("投注金额不能为负数")
    if amount > max_limit:
        raise ExceedMaxLimitError(f"投注金额 {amount} 超过单轮上限 {max_limit}")
    if amount == 0 or amount % 5 != 0:
        raise InvalidMultipleOfFiveError("投注金额必须是 5 的倍数且不能为 0")
    return True

def validate_match_score(red_score: int, green_score: int) -> TeamColor:
    """
    验证比分是否符合七局四胜制。
    七局四胜制要求一方分数恰好是 4，且另一方分数小于 4 且不能为负数。
    
    @author hyq
    @version 2026-07-13
    
    Args:
        red_score (int): 红队得分
        green_score (int): 绿队得分
        
    Returns:
        TeamColor: 赢家队伍颜色 (TeamColor.RED 或 TeamColor.GREEN)
        
    Raises:
        MatchResultValidationError: 如果比分不符合规则
    """
    if red_score < 0 or green_score < 0:
        raise MatchResultValidationError("比分不能为负数")
    if red_score == 4 and green_score < 4:
        return TeamColor.RED
    elif green_score == 4 and red_score < 4:
        return TeamColor.GREEN
    else:
        raise MatchResultValidationError(
            f"比分不符合七局四胜制规则（一方须恰好为 4，另一方须小于 4）。当前比分：红队 {red_score} - 绿队 {green_score}"
        )

def _extract_name(name_str: str) -> str:
    """
    剥离投注人字符串中的金额，提取纯姓名。
    支持格式如 "张三 (10)" 或 "张三"
    
    @author hyq
    @version 2026-07-13
    """
    # hyq: 2026-07-13 Modify for name extraction using regex
    # name = name_str
    # if '(' in name:
    #     name = name.split('(')[0]
    # if '（' in name:
    #     name = name.split('（')[0]
    # return name.strip()
    return re.sub(r'\s*[\(（]\d+[\)）]\s*$', '', name_str).strip()

def validate_team_bindings(
    red_players: list[str],
    green_players: list[str],
    red_bettors: list[str],
    green_bettors: list[str]
) -> None:
    """
    校验队伍绑定关系是否合法。
    
    1. 任何成员不能同时在红队队员和绿队队员列表中（互斥关系验证）。
    2. 任何成员不能同时在红队投注人和绿队投注人列表中。
    3. 严格约束：队员只能投注自己所在的队伍。红队队员不能出现在 green_bettors 中，绿队队员不能出现在 red_bettors 中。
    
    @author hyq
    @version 2026-07-13
    
    Args:
        red_players (list[str]): 红队队员列表
        green_players (list[str]): 绿队队员列表
        red_bettors (list[str]): 红队投注人列表
        green_bettors (list[str]): 绿队投注人列表
        
    Raises:
        TeamBindingValidationError: 校验不通过时抛出
    """
    # hyq: 2026-07-13 Modify for team bindings validation (null checks, empty names, duplicates, and case-insensitivity)
    # clean_red_players = [p.strip() for p in red_players if p]
    # clean_green_players = [p.strip() for p in green_players if p]
    # clean_red_bettors = [_extract_name(b) for b in red_bettors if b]
    # clean_green_bettors = [_extract_name(b) for b in green_bettors if b]
    # 
    # # 1. 红绿队员互斥
    # duplicate_players = set(clean_red_players) & set(clean_green_players)
    # if duplicate_players:
    #     raise TeamBindingValidationError(f"成员不能同时是红队和绿队队员: {duplicate_players}")
    #     
    # # 2. 红绿投注人互斥
    # duplicate_bettors = set(clean_red_bettors) & set(clean_green_bettors)
    # if duplicate_bettors:
    #     raise TeamBindingValidationError(f"成员不能同时对红队和绿队进行投注: {duplicate_bettors}")
    #     
    # # 3. 红队队员不能投绿队
    # red_player_betting_green = set(clean_red_players) & set(clean_green_bettors)
    # if red_player_betting_green:
    #     raise TeamBindingValidationError(f"红队队员不能投注绿队: {red_player_betting_green}")
    #     
    # # 4. 绿队队员不能投红队
    # green_player_betting_red = set(clean_green_players) & set(clean_red_bettors)
    # if green_player_betting_red:
    #     raise TeamBindingValidationError(f"绿队队员不能投注红队: {green_player_betting_red}")

    # 4个列表参数防空处理
    if red_players is None:
        red_players = []
    if green_players is None:
        green_players = []
    if red_bettors is None:
        red_bettors = []
    if green_bettors is None:
        green_bettors = []

    # 过滤掉strip后长度为0的无效姓名
    clean_red_players = [p.strip() for p in red_players if p and p.strip()]
    clean_green_players = [p.strip() for p in green_players if p and p.strip()]
    
    clean_red_bettors = []
    for b in red_bettors:
        if b and b.strip():
            extracted = _extract_name(b)
            if extracted:
                clean_red_bettors.append(extracted)

    clean_green_bettors = []
    for b in green_bettors:
        if b and b.strip():
            extracted = _extract_name(b)
            if extracted:
                clean_green_bettors.append(extracted)

    # 单队内重复校验（大小写不敏感）
    def check_duplicates(lst: list[str], name_type: str):
        seen = set()
        duplicates = []
        for x in lst:
            xl = x.lower()
            if xl in seen:
                duplicates.append(x)
            seen.add(xl)
        if duplicates:
            raise TeamBindingValidationError(f"{name_type}中存在重复姓名: {duplicates}")

    check_duplicates(clean_red_players, "红队队员")
    check_duplicates(clean_green_players, "绿队队员")
    check_duplicates(clean_red_bettors, "红队投注人")
    check_duplicates(clean_green_bettors, "绿队投注人")

    # 1. 红绿队员互斥（大小写不敏感）
    dup_players_lower = set(p.lower() for p in clean_red_players) & set(p.lower() for p in clean_green_players)
    if dup_players_lower:
        orig = {p for p in clean_red_players if p.lower() in dup_players_lower} | {p for p in clean_green_players if p.lower() in dup_players_lower}
        raise TeamBindingValidationError(f"成员不能同时是红队和绿队队员: {orig}")
        
    # 2. 红绿投注人互斥（大小写不敏感）
    dup_bettors_lower = set(b.lower() for b in clean_red_bettors) & set(b.lower() for b in clean_green_bettors)
    if dup_bettors_lower:
        orig = {b for b in clean_red_bettors if b.lower() in dup_bettors_lower} | {b for b in clean_green_bettors if b.lower() in dup_bettors_lower}
        raise TeamBindingValidationError(f"成员不能同时对红队和绿队进行投注: {orig}")
        
    # 3. 红队队员不能投绿队（大小写不敏感）
    red_player_betting_green_lower = set(p.lower() for p in clean_red_players) & set(b.lower() for b in clean_green_bettors)
    if red_player_betting_green_lower:
        orig = {p for p in clean_red_players if p.lower() in red_player_betting_green_lower} | {b for b in clean_green_bettors if b.lower() in red_player_betting_green_lower}
        raise TeamBindingValidationError(f"红队队员不能投注绿队: {orig}")
        
    # 4. 绿队队员不能投红队（大小写不敏感）
    green_player_betting_red_lower = set(p.lower() for p in clean_green_players) & set(b.lower() for b in clean_red_bettors)
    if green_player_betting_red_lower:
        orig = {p for p in clean_green_players if p.lower() in green_player_betting_red_lower} | {b for b in clean_red_bettors if b.lower() in green_player_betting_red_lower}
        raise TeamBindingValidationError(f"绿队队员不能投注红队: {orig}")

def calculate_settlement(bets: list, winner: TeamColor) -> dict:
    """
    核心 1:1 结算分值守恒算法。
    
    猜对 profit_loss = bet_amount；猜错 profit_loss = -bet_amount。
    庄家单轮净盈亏 = 输家投注额之和 - 赢家投注额之和 = 所有人盈亏取反之和。
    
    @author hyq
    @version 2026-07-13
    
    Args:
        bets (list): Bet 实例列表，或字典列表
        winner (TeamColor): 赢家队伍颜色
        
    Returns:
        dict: {"settlements": list, "banker_round_profit": int}
    """
    settlements = []
    total_profit_loss = 0
    
    for bet in bets:
        if isinstance(bet, dict):
            new_bet = bet.copy()
            prediction = new_bet.get('prediction')
            bet_amount = new_bet.get('bet_amount', 0)
            
            if prediction == winner:
                profit_loss = bet_amount
            else:
                profit_loss = -bet_amount
                
            new_bet['profit_loss'] = profit_loss
            settlements.append(new_bet)
            total_profit_loss += profit_loss
        else:
            prediction = getattr(bet, 'prediction')
            bet_amount = getattr(bet, 'bet_amount', 0)
            
            if prediction == winner:
                profit_loss = bet_amount
            else:
                profit_loss = -bet_amount
                
            new_bet = replace(bet, profit_loss=profit_loss)
            settlements.append(new_bet)
            total_profit_loss += profit_loss
            
    banker_round_profit = -total_profit_loss
    
    return {
        "settlements": settlements,
        "banker_round_profit": banker_round_profit
    }
