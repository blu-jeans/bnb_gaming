# 数据库架构、数据模型与仓储层设计分析报告

**文档属性**：
- **作者**：hyq
- **创建日期**：2026年07月13日
- **版本**：v1.0.0
- **工作目录**：`d:\workspace\bnb_guessing\.agents\explorer_milestone1_3`

---

## 1. 摘要 (Summary)
本报告详细阐述了 BnB 家庭比赛积分投注系统（BnB Family Match Score Betting System）第一阶段（Milestone 1）的数据层设计方案。基于 SQLite 数据库，设计了包含家庭成员、锦标赛、轮次、投注记录以及归档历史的五张核心数据表，并提供了完整的 SQL DDL 定义及索引覆盖策略。同时，使用 Python 3.11 的 `dataclass` 与 `StrEnum` 规范了数据模型，设计了支持事务自动控制与外键约束启用的连接管理器，并实现了核心仓储层（Repository）的 CRUD 接口逻辑与对应的单元测试验证方案。

---

## 2. 数据库 Schema 设计 (Database Schema Design)

本系统采用本地 SQLite 数据库文件 `bnb_betting.db`。为确保数据的完整性与高性能查询，设计了以下 5 张物理表，并结合查询特征建立了索引覆盖。

### 2.1 实体关系图说明 (ERD Description)
- **members** (1) ↔ (N) **bets**: 一个成员可以有多条投注记录。
- **tournaments** (1) ↔ (N) **rounds**: 一个锦标赛包含多个比赛轮次。
- **tournaments** (1) ↔ (N) **bets**: 一个锦标赛包含多个投注记录。
- **rounds** (1) ↔ (N) **bets**: 一个轮次关联该轮次下所有成员的投注（通过 `tournament_id` 和 `round_number` 联合关联）。
- **match_history** (1) ↔ (0/1): 当锦标赛结束时，将 `rounds` 表的数据复制归档到 `match_history`。

### 2.2 SQL 建表语句 (DDL)

根据用户全局规范的 SQL 编写规范，所有涉及 `WHERE`, `JOIN`, `ORDER BY` 的列均配置了索引。

```sql
-- 开启外键支持（SQLite 默认不开启，连接时需显式调用 PRAGMA foreign_keys = ON;）
PRAGMA foreign_keys = ON;

-- 1. 家庭成员表
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,                       -- 成员姓名，唯一约束
    initial_score INTEGER NOT NULL DEFAULT 1000,     -- 初始积分
    accumulated_score INTEGER NOT NULL DEFAULT 1000, -- 历史累计总积分（包含所有比赛结算后的实时积分）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP   -- 创建时间
);

-- 2. 锦标赛表
CREATE TABLE IF NOT EXISTS tournaments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL CHECK(status IN ('ACTIVE', 'COMPLETED')), -- 锦标赛状态
    banker_net_profit INTEGER NOT NULL DEFAULT 0,    -- 庄家在当前锦标赛的净盈亏
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 开启时间
    ended_at TIMESTAMP                               -- 结束时间
);

-- 3. 比赛轮次表
CREATE TABLE IF NOT EXISTS rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL,                  -- 关联锦标赛 ID
    round_number INTEGER NOT NULL,                   -- 轮次序号（从 1 开始递增）
    red_score INTEGER NOT NULL,                      -- 红队得分（抢4赛制，0-4）
    green_score INTEGER NOT NULL,                    -- 绿队得分（抢4赛制，0-4）
    winner TEXT NOT NULL CHECK(winner IN ('RED', 'GREEN')), -- 获胜队伍
    banker_round_profit INTEGER NOT NULL,            -- 庄家本轮盈亏
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 结算时间
    FOREIGN KEY (tournament_id) REFERENCES tournaments (id) ON DELETE CASCADE,
    UNIQUE (tournament_id, round_number)             -- 联合唯一索引：同届锦标赛下轮次号唯一
);

-- 4. 投注表
CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL,                  -- 关联锦标赛 ID
    round_number INTEGER NOT NULL,                   -- 关联轮次号
    member_id INTEGER NOT NULL,                      -- 关联成员 ID
    bet_amount INTEGER NOT NULL CHECK(bet_amount >= 0 AND bet_amount % 5 = 0), -- 投注金额，必须是 5 的倍数
    predicted_team TEXT CHECK(predicted_team IN ('RED', 'GREEN')),             -- 预测队伍（盲注阶段可为 NULL）
    is_player INTEGER NOT NULL CHECK(is_player IN (0, 1)),                     -- 是否为上场队员
    net_profit INTEGER DEFAULT 0,                    -- 投注净盈亏（结算前为 0，结算后为 +bet_amount 或 -bet_amount）
    FOREIGN KEY (tournament_id) REFERENCES tournaments (id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES members (id) ON DELETE CASCADE,
    UNIQUE (tournament_id, round_number, member_id)  -- 联合唯一：同届锦标赛同轮下每个成员只能投注一次
);

-- 5. 归档历史表
CREATE TABLE IF NOT EXISTS match_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL,                  -- 归档的锦标赛 ID
    round_number INTEGER NOT NULL,                   -- 归档的轮次号
    red_score INTEGER NOT NULL,
    green_score INTEGER NOT NULL,
    winner TEXT NOT NULL CHECK(winner IN ('RED', 'GREEN')),
    banker_round_profit INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP   -- 归档时间
);

-- 6. 高性能索引创建 (Index Optimization)
-- 锦标赛状态查询过滤索引
CREATE INDEX IF NOT EXISTS idx_tournaments_status ON tournaments(status);

-- 轮次关联查询优化索引
CREATE INDEX IF NOT EXISTS idx_rounds_tournament_id ON rounds(tournament_id);

-- 投注关联与排行榜统计优化索引
CREATE INDEX IF NOT EXISTS idx_bets_tournament_id ON bets(tournament_id);
CREATE INDEX IF NOT EXISTS idx_bets_member_id ON bets(member_id);

-- 归档历史表根据锦标赛过滤索引
CREATE INDEX IF NOT EXISTS idx_match_history_tournament ON match_history(tournament_id);
```

---

## 3. Python 3.11 数据模型设计 (Python Models Design)

文件路径建议：`src/database/models.py`

采用现代 Python 3.11 语言特性，包含强类型标注（Type Hints）、可空表示（`Optional`）、新增的 `StrEnum` 作为强类型枚举，以及简洁的 `dataclass` 定义。

```python
# -*- coding: utf-8 -*-
"""
@author: hyq
@date: 2026-07-13
@version: v1.0.0
@description: 数据库核心实体 Python 3.11 强类型数据模型定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import StrEnum

class TournamentStatus(StrEnum):
    """
    锦标赛状态枚举
    """
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"

class TeamColor(StrEnum):
    """
    队伍颜色枚举
    """
    RED = "RED"
    GREEN = "GREEN"

@dataclass
class Member:
    """
    家庭成员数据模型
    """
    id: Optional[int]
    name: str
    initial_score: int = 1000
    accumulated_score: int = 1000
    created_at: Optional[datetime] = None

@dataclass
class Tournament:
    """
    锦标赛数据模型
    """
    id: Optional[int]
    status: TournamentStatus
    banker_net_profit: int = 0
    created_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

@dataclass
class Round:
    """
    比赛轮次数据模型
    """
    id: Optional[int]
    tournament_id: int
    round_number: int
    red_score: int
    green_score: int
    winner: TeamColor
    banker_round_profit: int
    created_at: Optional[datetime] = None

@dataclass
class Bet:
    """
    投注记录数据模型
    """
    id: Optional[int]
    tournament_id: int
    round_number: int
    member_id: int
    bet_amount: int
    predicted_team: Optional[TeamColor] = None  # 盲注阶段为 None
    is_player: bool = False
    net_profit: int = 0

@dataclass
class MatchHistory:
    """
    历史归档数据模型
    """
    id: Optional[int]
    tournament_id: int
    round_number: int
    red_score: int
    green_score: int
    winner: TeamColor
    banker_round_profit: int
    created_at: Optional[datetime] = None
```

---

## 4. 数据库连接与事务管理器设计 (Connection & Transaction Manager)

文件路径建议：`src/database/db_manager.py`

设计一个基于 `contextmanager` 的数据库连接管理器。它具有以下核心特性：
1. **自动建档**：如果数据库文件不存在，会自动创建连接。
2. **连接配置**：启用 SQLite 外键检查（`PRAGMA foreign_keys = ON;`），并将 `row_factory` 设置为 `sqlite3.Row` 以支持列名键值访问。
3. **事务自动化**：在上下文生命周期内，如果执行成功则自动 `commit`，若抛出异常则自动 `rollback`。

```python
# -*- coding: utf-8 -*-
"""
@author: hyq
@date: 2026-07-13
@version: v1.0.0
@description: SQLite 数据库连接与事务管理上下文管理器
"""

import sqlite3
import os
from contextlib import contextmanager
from typing import Generator

DB_FILE = "bnb_betting.db"

class DatabaseManager:
    """
    数据库连接管理器
    """
    def __init__(self, db_path: str = DB_FILE):
        # 默认生成在应用同级目录下
        self.db_path = os.path.abspath(db_path)

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        获取数据库连接上下文管理器，自动处理事务 Commit/Rollback 并开启外键约束
        """
        # 确保父级目录存在
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # 必须显式启用外键约束，以维持引用完整性
        conn.execute("PRAGMA foreign_keys = ON;")
        
        try:
            yield conn
            conn.commit()  # 正常退出时自动提交事务
        except Exception as e:
            conn.rollback()  # 发生任何异常时回滚当前事务
            raise e
        finally:
            conn.close()  # 确保连接最终被关闭
```

---

## 5. 仓储层 CRUD 操作设计 (Repository CRUD Design)

文件路径建议：`src/database/repository.py`

仓储层对外部模块屏蔽 SQL 细节，提供面向对象的方法签名。核心业务操作（如 `save_round_settlement` 和 `end_tournament`）在单个事务内运行以保证原子性。

```python
# -*- coding: utf-8 -*-
"""
@author: hyq
@date: 2026-07-13
@version: v1.0.0
@description: 数据库访问仓储层，提供核心业务接口的原子性 CRUD 实现
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from src.database.db_manager import DatabaseManager
from src.database.models import Member, Tournament, Round, Bet, TournamentStatus, TeamColor

class Repository:
    """
    数据访问仓储类
    """
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def initialize_db(self) -> None:
        """
        初始化数据库结构，创建表和对应索引
        """
        with self.db_manager.get_connection() as conn:
            # 1. 创建表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    initial_score INTEGER NOT NULL DEFAULT 1000,
                    accumulated_score INTEGER NOT NULL DEFAULT 1000,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tournaments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL CHECK(status IN ('ACTIVE', 'COMPLETED')),
                    banker_net_profit INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rounds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tournament_id INTEGER NOT NULL,
                    round_number INTEGER NOT NULL,
                    red_score INTEGER NOT NULL,
                    green_score INTEGER NOT NULL,
                    winner TEXT NOT NULL CHECK(winner IN ('RED', 'GREEN')),
                    banker_round_profit INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tournament_id) REFERENCES tournaments (id) ON DELETE CASCADE,
                    UNIQUE (tournament_id, round_number)
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tournament_id INTEGER NOT NULL,
                    round_number INTEGER NOT NULL,
                    member_id INTEGER NOT NULL,
                    bet_amount INTEGER NOT NULL CHECK(bet_amount >= 0 AND bet_amount % 5 = 0),
                    predicted_team TEXT CHECK(predicted_team IN ('RED', 'GREEN')),
                    is_player INTEGER NOT NULL CHECK(is_player IN (0, 1)),
                    net_profit INTEGER DEFAULT 0,
                    FOREIGN KEY (tournament_id) REFERENCES tournaments (id) ON DELETE CASCADE,
                    FOREIGN KEY (member_id) REFERENCES members (id) ON DELETE CASCADE,
                    UNIQUE (tournament_id, round_number, member_id)
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS match_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tournament_id INTEGER NOT NULL,
                    round_number INTEGER NOT NULL,
                    red_score INTEGER NOT NULL,
                    green_score INTEGER NOT NULL,
                    winner TEXT NOT NULL CHECK(winner IN ('RED', 'GREEN')),
                    banker_round_profit INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # 2. 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tournaments_status ON tournaments(status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rounds_tournament_id ON rounds(tournament_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_bets_tournament_id ON bets(tournament_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_bets_member_id ON bets(member_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_match_history_tournament ON match_history(tournament_id);")

    def add_member(self, name: str, initial_score: int = 1000) -> int:
        """
        添加家庭成员
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO members (name, initial_score, accumulated_score) VALUES (?, ?, ?)",
                (name, initial_score, initial_score)
            )
            return cursor.lastrowid

    def get_all_members(self) -> List[Member]:
        """
        获取所有成员列表及其历史积分
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, name, initial_score, accumulated_score, created_at FROM members ORDER BY id ASC"
            )
            rows = cursor.fetchall()
            return [
                Member(
                    id=row["id"],
                    name=row["name"],
                    initial_score=row["initial_score"],
                    accumulated_score=row["accumulated_score"],
                    created_at=datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S") if isinstance(row["created_at"], str) else row["created_at"]
                )
                for row in rows
            ]

    def start_tournament(self) -> int:
        """
        开启新一届锦标赛。若存在进行中的锦标赛则抛出异常，防止多重锦标赛混淆。
        """
        with self.db_manager.get_connection() as conn:
            # 检查是否有未结束的锦标赛
            cursor = conn.execute("SELECT id FROM tournaments WHERE status = 'ACTIVE'")
            active = cursor.fetchone()
            if active:
                raise ValueError("已存在正在进行中的锦标赛，无法启动新锦标赛！")
                
            cursor = conn.execute(
                "INSERT INTO tournaments (status, banker_net_profit) VALUES ('ACTIVE', 0)"
            )
            return cursor.lastrowid

    def end_tournament(self, tournament_id: int) -> Dict[str, Any]:
        """
        在一个事务内结束锦标赛：
        1. 更新状态为已完成；
        2. 将锦标赛下的所有轮次数据归档到 match_history 中；
        3. 计算并返回庄家总净盈亏和排行榜。
        """
        with self.db_manager.get_connection() as conn:
            # 验证锦标赛状态
            cursor = conn.execute("SELECT status, banker_net_profit FROM tournaments WHERE id = ?", (tournament_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"锦标赛 ID {tournament_id} 不存在。")
            if row["status"] == "COMPLETED":
                raise ValueError(f"锦标赛 ID {tournament_id} 已经结束，请勿重复操作。")

            # 1. 更新锦标赛状态
            conn.execute(
                "UPDATE tournaments SET status = 'COMPLETED', ended_at = CURRENT_TIMESTAMP WHERE id = ?",
                (tournament_id,)
            )

            # 2. 归档数据到 match_history 表
            conn.execute("""
                INSERT INTO match_history (tournament_id, round_number, red_score, green_score, winner, banker_round_profit, created_at)
                SELECT tournament_id, round_number, red_score, green_score, winner, banker_round_profit, created_at
                FROM rounds
                WHERE tournament_id = ?
            """, (tournament_id,))

            # 3. 统计该锦标赛的选手净盈亏（降序排列）
            cursor = conn.execute("""
                SELECT m.id, m.name, SUM(b.net_profit) as total_profit
                FROM members m
                JOIN bets b ON m.id = b.member_id
                WHERE b.tournament_id = ?
                GROUP BY m.id
                ORDER BY total_profit DESC
            """, (tournament_id,))
            leaderboard_rows = cursor.fetchall()
            
            leaderboard = [
                {"member_id": r["id"], "name": r["name"], "total_profit": r["total_profit"] if r["total_profit"] is not None else 0}
                for r in leaderboard_rows
            ]

            # 区分盈利王和背锅王
            top_winners = [p for p in leaderboard if p["total_profit"] > 0]
            top_losers = sorted([p for p in leaderboard if p["total_profit"] < 0], key=lambda x: x["total_profit"])

            return {
                "tournament_id": tournament_id,
                "banker_net_profit": row["banker_net_profit"],
                "leaderboard": leaderboard,
                "top_winners": top_winners,
                "top_losers": top_losers
            }

    def save_round_settlement(
        self,
        tournament_id: int,
        round_number: int,
        red_score: int,
        green_score: int,
        winner: str,
        banker_round_profit: int,
        bets: List[Dict[str, Any]],
        settlements: List[Dict[str, Any]]
    ) -> bool:
        """
        保存单轮比赛结算数据，以事务方式执行：
        1. 写入 rounds 比赛记录表；
        2. 写入或更新 bets 投注详情及个人盈亏；
        3. 增量更新 members 中的累计历史总积分；
        4. 增量更新 tournaments 中庄家的锦标赛总盈亏。
        """
        with self.db_manager.get_connection() as conn:
            # 1. 插入 rounds 数据
            conn.execute("""
                INSERT INTO rounds (tournament_id, round_number, red_score, green_score, winner, banker_round_profit)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (tournament_id, round_number, red_score, green_score, winner, banker_round_profit))

            # 建立盈亏映射字典 {member_id: net_profit}
            settlement_map = {s["member_id"]: s["net_profit"] for s in settlements}

            # 2. 插入或更新 bets 记录，并同步更新玩家累计积分
            for bet in bets:
                m_id = bet["member_id"]
                profit = settlement_map.get(m_id, 0)
                
                # 写入投注明细
                conn.execute("""
                    INSERT INTO bets (tournament_id, round_number, member_id, bet_amount, predicted_team, is_player, net_profit)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(tournament_id, round_number, member_id) DO UPDATE SET
                        bet_amount = excluded.bet_amount,
                        predicted_team = excluded.predicted_team,
                        is_player = excluded.is_player,
                        net_profit = excluded.net_profit
                """, (
                    tournament_id,
                    round_number,
                    m_id,
                    bet["bet_amount"],
                    bet["predicted_team"],
                    1 if bet["is_player"] else 0,
                    profit
                ))

                # 3. 更新家庭成员的累计历史总积分
                conn.execute("""
                    UPDATE members
                    SET accumulated_score = accumulated_score + ?
                    WHERE id = ?
                """, (profit, m_id))

            # 4. 更新庄家锦标赛累计盈亏
            conn.execute("""
                UPDATE tournaments
                SET banker_net_profit = banker_net_profit + ?
                WHERE id = ?
            """, (banker_round_profit, tournament_id))

        return True

    def get_match_history(self) -> List[Dict[str, Any]]:
        """
        从归档表中查询所有已结束锦标赛的归档记录
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, tournament_id, round_number, red_score, green_score, winner, banker_round_profit, created_at
                FROM match_history
                ORDER BY tournament_id DESC, round_number ASC
            """)
            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "tournament_id": r["tournament_id"],
                    "round_number": r["round_number"],
                    "red_score": r["red_score"],
                    "green_score": r["green_score"],
                    "winner": r["winner"],
                    "banker_round_profit": r["banker_round_profit"],
                    "created_at": r["created_at"]
                }
                for r in rows
            ]

    def get_tournament_leaderboard(self, tournament_id: int) -> List[Dict[str, Any]]:
        """
        获取当前锦标赛的盈亏排行榜。
        采用 LEFT JOIN 保证未在此锦标赛下投注的成员以 0 盈亏显示在榜单中。
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT m.id, m.name, COALESCE(SUM(b.net_profit), 0) as total_profit
                FROM members m
                LEFT JOIN bets b ON m.id = b.member_id AND b.tournament_id = ?
                GROUP BY m.id
                ORDER BY total_profit DESC
            """, (tournament_id,))
            rows = cursor.fetchall()
            return [
                {
                    "member_id": r["id"],
                    "name": r["name"],
                    "total_profit": r["total_profit"]
                }
                for r in rows
            ]
```

---

## 6. 测试策略与设计 (Testing Strategy)

为了验证本设计的正确性以及在多步操作、约束冲突等异常情况下的事务安全行为，使用 Python 标准库 `unittest`（或 `pytest`）进行针对性单元测试设计。

### 6.1 测试设置
利用 SQLite 的内存模式（使用 `:memory:` 作为连接字符串），在不产生垃圾文件的前提下，为每个独立的测试方法自动创建干净的运行上下文环境。

### 6.2 关键测试用例设计

#### 测试用例 1：数据库建表与外键启用检查
- **操作**：调用 `initialize_db()` 并验证表是否成功创建。
- **验证**：利用 `sqlite_master` 校验表名列表；尝试向子表 `rounds` 插入一个不存在的 `tournament_id`，预期必须抛出 `IntegrityError`（用以验证外键约束是否真正开启）。

#### 测试用例 2：唯一性约束与投注限额限制
- **操作**：添加相同姓名的玩家；同一轮次尝试多次保存同一玩家的投注记录。
- **验证**：姓名重复应拦截并报错；同一轮次同一玩家重复投注应当在 ON CONFLICT 事务中被合理处理，或者抛出 `IntegrityError`（若直接插入）。
- **校验**：投注额插入不合规数字（例如不能整除 5 或为负数）必须触发 DDL `CHECK` 约束。

#### 测试用例 3：锦标赛生命周期与单重性验证
- **操作**：调用 `start_tournament()`。
- **验证**：再次调用 `start_tournament()`，预期应捕获 `ValueError`；调用 `end_tournament()` 归档后，可重新成功调用 `start_tournament()`。

#### 测试用例 4：结算事务原子性与积分守恒校验
- **操作**：执行一轮带有 3 名投注人的比分结算，故意使第 3 名投注人的 `member_id` 变成无效 ID（不存在的玩家）。
- **验证**：执行 `save_round_settlement`，由于外键约束，写入第三人投注时将崩溃报错。
- **校验**：查询第一、第二名玩家的 `accumulated_score` 积分，验证其没有任何改变。证明由于任何一步失败，前两步的积分修改及 rounds 写入均被完全 Rollback。

### 6.3 单元测试代码草案

```python
# -*- coding: utf-8 -*-
"""
@author: hyq
@date: 2026-07-13
@version: v1.0.0
@description: 单元测试用例，校验数据一致性、原子性与外键约束行为
"""

import unittest
import sqlite3
from src.database.db_manager import DatabaseManager
from src.database.repository import Repository

class TestDatabaseLayer(unittest.TestCase):
    def setUp(self):
        # 使用内存数据库，避免文件干扰，速度极快
        self.db_manager = DatabaseManager(db_path=":memory:")
        self.repo = Repository(self.db_manager)
        self.repo.initialize_db()
        
        # 预制初始家庭成员
        self.alice_id = self.repo.add_member("Alice", initial_score=1000)
        self.bob_id = self.repo.add_member("Bob", initial_score=1000)
        self.charlie_id = self.repo.add_member("Charlie", initial_score=1000)

    def test_add_member_unique_constraint(self):
        """测试成员姓名唯一性约束"""
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.add_member("Alice")  # 重名写入应报错

    def test_bet_limit_check_constraint(self):
        """测试投注额度合法性约束（5的倍数且非负）"""
        t_id = self.repo.start_tournament()
        with self.assertRaises(sqlite3.IntegrityError):
            # 12 积分不满足 5 的倍数约束，应当触发 Check 报错
            with self.db_manager.get_connection() as conn:
                conn.execute(
                    "INSERT INTO bets (tournament_id, round_number, member_id, bet_amount, is_player) VALUES (?, ?, ?, ?, ?)",
                    (t_id, 1, self.alice_id, 12, 0)
                )

    def test_single_active_tournament_constraint(self):
        """测试同时仅允许存在一个活动锦标赛的逻辑约束"""
        t_id = self.repo.start_tournament()
        self.assertIsNotNone(t_id)
        
        with self.assertRaises(ValueError):
            self.repo.start_tournament()  # 重复开启报错

    def test_settlement_transaction_atomicity(self):
        """测试单轮结算的整体事务原子性"""
        t_id = self.repo.start_tournament()
        
        bets = [
            {"member_id": self.alice_id, "bet_amount": 10, "predicted_team": "RED", "is_player": False},
            {"member_id": self.bob_id, "bet_amount": 20, "predicted_team": "RED", "is_player": False},
            {"member_id": 9999, "bet_amount": 15, "predicted_team": "GREEN", "is_player": True}  # 故意传入非法 member_id
        ]
        
        settlements = [
            {"member_id": self.alice_id, "net_profit": 10},
            {"member_id": self.bob_id, "net_profit": 20},
            {"member_id": 9999, "net_profit": -15}
        ]
        
        # 此时执行预期崩溃
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.save_round_settlement(
                tournament_id=t_id,
                round_number=1,
                red_score=4,
                green_score=2,
                winner="RED",
                banker_round_profit=-15,
                bets=bets,
                settlements=settlements
            )
            
        # 校验：检查 Alice 和 Bob 的积分是否仍然保持 1000（确认被 Rollback，无部分写入）
        members = self.repo.get_all_members()
        for m in members:
            self.assertEqual(m.accumulated_score, 1000)

    def test_successful_flow(self):
        """测试完整正常的开启-结算-结束流程"""
        # 1. 开启比赛
        t_id = self.repo.start_tournament()
        
        # 2. 投注与结算
        bets = [
            {"member_id": self.alice_id, "bet_amount": 15, "predicted_team": "RED", "is_player": False},
            {"member_id": self.bob_id, "bet_amount": 20, "predicted_team": "GREEN", "is_player": False}
        ]
        settlements = [
            {"member_id": self.alice_id, "net_profit": 15},   -- 猜对赢15
            {"member_id": self.bob_id, "net_profit": -20}    -- 猜错输20
        ]
        
        # 庄家盈利 = 20 (Bob输的) - 15 (Alice赢的) = 5
        self.repo.save_round_settlement(
            tournament_id=t_id,
            round_number=1,
            red_score=4,
            green_score=1,
            winner="RED",
            banker_round_profit=5,
            bets=bets,
            settlements=settlements
        )
        
        # 验证积分更新
        m_map = {m.id: m.accumulated_score for m in self.repo.get_all_members()}
        self.assertEqual(m_map[self.alice_id], 1015)
        self.assertEqual(m_map[self.bob_id], 980)
        self.assertEqual(m_map[self.charlie_id], 1000) # Charlie没投注不受影响
        
        # 3. 结束锦标赛，验证归档与统计
        summary = self.repo.end_tournament(t_id)
        self.assertEqual(summary["banker_net_profit"], 5)
        self.assertEqual(len(summary["leaderboard"]), 2) # 有投注的两人
        
        # 验证归档记录
        history = self.repo.get_match_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["tournament_id"], t_id)
        self.assertEqual(history[0]["banker_round_profit"], 5)

if __name__ == "__main__":
    unittest.main()
```

---

## 7. 决策考量与架构优劣分析 (Design Analysis & Caveats)

1. **SQLite 写入锁限制 (Write Lock Limit)**
   SQLite 作为进程内数据库，支持极高的并发读，但在写入时采用库级排他锁（Write Lock）。针对桌面 PyQt6 单用户场景，这已完全足够，不会产生性能瓶颈。在设计连接管理器时，我们使用事务回滚保证多步写入的完整性。

2. **排行榜的 LEFT JOIN 选择**
   计算锦标赛排行榜时，由于可能存在某些玩家在某一锦标赛中全程观战（没有下注记录），如果使用 `INNER JOIN`，这些玩家将不会出现在排行榜中。在 `get_tournament_leaderboard` 方法中，我们采用 `LEFT JOIN` 与 `COALESCE` 方式，能够将所有参赛玩家（哪怕净盈亏为 0）均排列在实时榜单内，更佳地保障了 UI 层面拉取排行榜的展示体验。

3. **数据归档冗余策略 (Archive Redundancy Strategy)**
   在 `end_tournament` 中，我们将 `rounds` 数据拷贝至 `match_history`。为避免 `rounds` 和 `bets` 在锦标赛多次进行后膨胀导致的查询慢问题，归档表作为静态数据查询的最佳拍档，可以将已经完成的赛事记录进行一次性聚合，满足历史轮次表展示的要求；而当前进行中的活动数据始终可以保持精简高效。
