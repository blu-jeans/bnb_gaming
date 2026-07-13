# -*- coding: utf-8 -*-
"""
@author hyq
@version 2026-07-13
"""

from dataclasses import dataclass
from enum import StrEnum

class TournamentStatus(StrEnum):
    """
    锦标赛状态枚举
    ONGOING: 进行中
    ENDED: 已结束
    """
    ONGOING = "ongoing"
    ENDED = "ended"

class TeamColor(StrEnum):
    """
    下注/赢家颜色枚举
    RED: 红队
    GREEN: 绿队
    """
    RED = "Red"
    GREEN = "Green"

@dataclass(frozen=True)
class Member:
    """
    成员信息模型
    """
    name: str
    historical_score: int = 0
    is_banker: bool = False
    id: int | None = None
    created_at: str | None = None

# hyq: 2026-07-13 Add GameAccount model for match player game IDs
@dataclass(frozen=True)
class GameAccount:
    """
    参赛选手游戏账号模型
    """
    nickname: str
    id: int | None = None
    created_at: str | None = None

@dataclass(frozen=True)
class Tournament:
    """
    锦标赛模型
    """
    id: int | None = None
    status: TournamentStatus = TournamentStatus.ONGOING
    banker_profit: int = 0
    start_time: str | None = None
    end_time: str | None = None

@dataclass(frozen=True)
class Round:
    """
    轮次模型
    """
    tournament_id: int
    round_number: int
    red_score: int
    green_score: int
    winner: TeamColor
    banker_round_profit: int
    # hyq: 2026-07-13 Add red/green players fields for match history
    red_players: str = ""
    green_players: str = ""
    # hyq: 2026-07-13 Add bet details for match history
    bet_details: str = ""
    id: int | None = None
    created_at: str | None = None

@dataclass(frozen=True)
class Bet:
    """
    投注模型
    """
    round_id: int
    member_id: int
    bet_amount: int
    prediction: TeamColor
    profit_loss: int
    is_player: bool = False
    id: int | None = None

@dataclass(frozen=True)
class MatchHistory:
    """
    对战历史模型
    """
    tournament_id: int
    round_number: int
    red_score: int
    green_score: int
    winner: TeamColor
    banker_round_profit: int
    # hyq: 2026-07-13 Add red/green players fields for match history
    red_players: str = ""
    green_players: str = ""
    # hyq: 2026-07-13 Add bet details for match history
    bet_details: str = ""
    id: int | None = None
    archived_at: str | None = None
