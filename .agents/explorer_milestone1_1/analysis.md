# 里程碑 1 分析报告：数据库 Schema 与核心模型设计

本报告由 **Milestone 1 Explorer 1**（作者：`hyq`）编写，旨在详细分析与设计 **BnB 家庭比赛积分投注系统** 的数据存储层。包含 SQLite 数据库 Schema、Python 3.11 数据模型、数据库连接管理器、Repository CRUD 接口设计及完整的单元测试验证策略。

---

## 1. 设计概述与核心原则

为了满足项目的高质量、低耦合和强健性要求，数据访问层遵循以下核心设计原则：
1. **单一职责原则 (SRP)**：
   - `db_manager.py` 专门负责 SQLite 连接的创建、关闭以及事务包裹，提供一致的上下文管理器。
   - `models.py` 仅定义实体对象，使用 Python 3.11 的只读数据类（frozen dataclass）与强类型枚举（StrEnum）确保数据不可变性与类型安全。
   - `repository.py` 负责核心数据读写逻辑，屏蔽底层 SQL 细节。
2. **事务原子性**：
   - 任何涉及多表修改（如保存单轮比赛结算、更新玩家历史积分与累加庄家盈亏）的操作，必须在**单一数据库事务**内执行，一旦中途出错，全部回滚，保证积分守恒定律不被破坏。
3. **数据完整性约束**：
   - 利用 SQLite 关系约束（如 `FOREIGN KEY`、`UNIQUE` 索引和 `CHECK` 约束），在数据库层面对业务规则进行第二道安全网拦截（如：防止对同一个锦标赛在同一轮次插入两个结算记录，或同一个玩家在同一轮次下两次注）。
4. **归档与审计分离**：
   - 进行中的锦标赛数据保留在 `rounds` 表中，以便于实时查询和计算当前锦标赛的盈亏与排行榜。
   - 当锦标赛结束时，本届所有轮次的数据将通过事务安全地归档至 `match_history`。源数据在 `rounds` 和 `bets` 中仍予保留，以便未来追溯及统计。

---

## 2. SQLite 数据库 Schema 设计

本系统设计了 5 个核心表。由于 SQLite 默认关闭外键约束，因此在连接管理器中必须在获取连接时显式执行 `PRAGMA foreign_keys = ON;`。

### 2.1 建表 SQL (DDL) 语句

```sql
-- 1. 家庭成员表：存储家庭成员基本信息及历史累计总积分
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    historical_score INTEGER NOT NULL DEFAULT 1000,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. 锦标赛生命周期表：管理锦标赛状态及庄家盈亏
CREATE TABLE IF NOT EXISTS tournaments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT CHECK(status IN ('ONGOING', 'ENDED')) NOT NULL DEFAULT 'ONGOING',
    banker_profit INTEGER NOT NULL DEFAULT 0,
    start_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP
);

-- 3. 轮次结算表：存储每个锦标赛下各个单轮的比赛得分及获胜方
CREATE TABLE IF NOT EXISTS rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL,
    round_number INTEGER NOT NULL,
    red_score INTEGER NOT NULL,
    green_score INTEGER NOT NULL,
    winner TEXT CHECK(winner IN ('RED', 'GREEN')) NOT NULL,
    banker_round_profit INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
    UNIQUE (tournament_id, round_number)
);

-- 4. 投注与盈亏明细表：记录每轮比赛中各玩家的投注金额、预测方及单轮盈亏
CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    bet_amount INTEGER NOT NULL CHECK(bet_amount >= 0),
    prediction TEXT CHECK(prediction IN ('RED', 'GREEN')) NOT NULL,
    profit_loss INTEGER NOT NULL,
    is_player INTEGER CHECK(is_player IN (0, 1)) NOT NULL DEFAULT 0,
    FOREIGN KEY (round_id) REFERENCES rounds(id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
    UNIQUE (round_id, member_id)
);

-- 5. 归档比赛历史表：存储已结束锦标赛的历史归档记录
CREATE TABLE IF NOT EXISTS match_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL,
    round_number INTEGER NOT NULL,
    red_score INTEGER NOT NULL,
    green_score INTEGER NOT NULL,
    winner TEXT CHECK(winner IN ('RED', 'GREEN')) NOT NULL,
    banker_round_profit INTEGER NOT NULL,
    archived_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
    UNIQUE (tournament_id, round_number)
);
```

### 2.2 约束设计与合理性说明
1. **`members.name` 唯一约束 (`UNIQUE`)**：界面交互采用拖拽形式，因此名称是家庭成员的唯一主键展示，在数据库层面限制重名，能有效防止逻辑混淆。
2. **`rounds` 复合唯一约束 (`UNIQUE(tournament_id, round_number)`)**：保证在同一个锦标赛内，轮次编码（如第 1 轮、第 2 轮）是唯一的，防止重复录入。
3. **`bets` 复合唯一约束 (`UNIQUE(round_id, member_id)`)**：确保每个家庭成员在同一轮比赛中只允许进行一次有效投注，防止因并发或界面重复提交导致的多次投注漏洞。
4. **关于积分守恒的计算方案**：
   - 玩家当前锦标赛净盈亏不存储在专门的列中，而是采用**动态 SQL 聚合**：
     ```sql
     SELECT m.id, m.name, COALESCE(SUM(b.profit_loss), 0) AS tournament_profit
     FROM members m
     LEFT JOIN bets b ON b.member_id = m.id
     LEFT JOIN rounds r ON b.round_id = r.id AND r.tournament_id = ?
     GROUP BY m.id;
     ```
     这避免了冗余字段同步失败的风险，符合数据库第三范式 (3NF)。

---

## 3. Python 3.11 数据模型设计 (`src/database/models.py`)

利用 Python 3.11 现代特性，将状态枚举定义为 `StrEnum`，并将模型定义为 `dataclass(frozen=True)`。只读模型能够防止底层数据在流转到业务层或 UI 层时被无意篡改。

### 3.1 模型代码实现

```python
# @author hyq
# @version 2026-07-13
# models.py: 定义项目核心实体的 Python 3.11 数据模型及枚举类。

from dataclasses import dataclass
from enum import StrEnum
from typing import Optional

class TournamentStatus(StrEnum):
    ONGOING = "ONGOING"
    ENDED = "ENDED"

class TeamColor(StrEnum):
    RED = "RED"
    GREEN = "GREEN"

@dataclass(frozen=True)
class Member:
    id: Optional[int]
    name: str
    historical_score: int
    created_at: str

@dataclass(frozen=True)
class Tournament:
    id: Optional[int]
    status: TournamentStatus
    banker_profit: int
    start_time: str
    end_time: Optional[str]

@dataclass(frozen=True)
class Round:
    id: Optional[int]
    tournament_id: int
    round_number: int
    red_score: int
    green_score: int
    winner: TeamColor
    banker_round_profit: int
    created_at: str

@dataclass(frozen=True)
class Bet:
    id: Optional[int]
    round_id: int
    member_id: int
    bet_amount: int
    prediction: TeamColor
    profit_loss: int
    is_player: bool

@dataclass(frozen=True)
class MatchHistory:
    id: Optional[int]
    tournament_id: int
    round_number: int
    red_score: int
    green_score: int
    winner: TeamColor
    banker_round_profit: int
    archived_at: str
```

---

## 4. SQLite 连接管理器设计 (`src/database/db_manager.py`)

连接管理器负责连接生命周期的治理。SQLite 在多线程或桌面客户端中可能会产生锁竞争，我们必须保证每个连接能被正确释放。

```python
# @author hyq
# @version 2026-07-13
# db_manager.py: SQLite 数据库连接管理器，提供连接上下文管理并启用外键约束。

import os
import sqlite3
from contextlib import contextmanager

class DatabaseManager:
    """
    SQLite 数据库连接管理器，支持上下文管理。
    """
    def __init__(self, db_path: str = "bnb_betting.db"):
        self.db_path = os.path.abspath(db_path)
        
    @contextmanager
    def get_connection(self):
        """
        获取数据库连接的上下文管理器。
        在 with 块正常结束时自动 commit 事务，发生异常时 rollback 事务。
        无论何种情况下，最终都会 close 连接，防止句柄泄露。
        """
        conn = sqlite3.connect(self.db_path)
        
        # 核心：显式启用外键约束，默认 SQLite 是关闭外键的
        conn.execute("PRAGMA foreign_keys = ON;")
        # 启用 Row Factory，使返回的记录行可以通过字典形式键值对访问
        conn.row_factory = sqlite3.Row
        
        try:
            # 配合 Python context manager 机制：with conn 用于管理事务
            with conn:
                yield conn
        finally:
            conn.close()
```

---

## 5. Repository CRUD 接口设计 (`src/database/repository.py`)

Repository 实现类负责底层 SQL 操作的封装，重点对关键接口进行事务安全设计。

```python
# @author hyq
# @version 2026-07-13
# repository.py: 实现对数据库的操作类，封装了所有增删改查接口并支持事务处理。

import sqlite3
from typing import List, Dict, Any, Optional
from .db_manager import DatabaseManager
from .models import Member, Tournament, Round, Bet, MatchHistory, TournamentStatus, TeamColor

class Repository:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def initialize_db(self) -> None:
        """
        初始化数据库结构，如果表不存在则创建。
        """
        sql_statements = [
            """
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                historical_score INTEGER NOT NULL DEFAULT 1000,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT CHECK(status IN ('ONGOING', 'ENDED')) NOT NULL DEFAULT 'ONGOING',
                banker_profit INTEGER NOT NULL DEFAULT 0,
                start_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS rounds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                round_number INTEGER NOT NULL,
                red_score INTEGER NOT NULL,
                green_score INTEGER NOT NULL,
                winner TEXT CHECK(winner IN ('RED', 'GREEN')) NOT NULL,
                banker_round_profit INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
                UNIQUE (tournament_id, round_number)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                round_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL,
                bet_amount INTEGER NOT NULL CHECK(bet_amount >= 0),
                prediction TEXT CHECK(prediction IN ('RED', 'GREEN')) NOT NULL,
                profit_loss INTEGER NOT NULL,
                is_player INTEGER CHECK(is_player IN (0, 1)) NOT NULL DEFAULT 0,
                FOREIGN KEY (round_id) REFERENCES rounds(id) ON DELETE CASCADE,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
                UNIQUE (round_id, member_id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS match_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                round_number INTEGER NOT NULL,
                red_score INTEGER NOT NULL,
                green_score INTEGER NOT NULL,
                winner TEXT CHECK(winner IN ('RED', 'GREEN')) NOT NULL,
                banker_round_profit INTEGER NOT NULL,
                archived_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
                UNIQUE (tournament_id, round_number)
            );
            """
        ]
        
        with self.db_manager.get_connection() as conn:
            for sql in sql_statements:
                conn.execute(sql)

    def add_member(self, name: str, initial_score: int = 1000) -> int:
        """
        添加一个新的家庭成员。返回新插入的成员 ID。
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO members (name, historical_score) VALUES (?, ?);",
                (name, initial_score)
            )
            return cursor.lastrowid

    def get_all_members(self) -> List[Member]:
        """
        获取所有成员列表，按名字升序。
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, historical_score, created_at FROM members ORDER BY name ASC;")
            rows = cursor.fetchall()
            return [
                Member(
                    id=row["id"],
                    name=row["name"],
                    historical_score=row["historical_score"],
                    created_at=row["created_at"]
                )
                for row in rows
            ]

    def start_tournament(self) -> int:
        """
        开启新一届锦标赛。
        如果有未结束的锦标赛，限制不允许开启新锦标赛，必须显式抛出异常。
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM tournaments WHERE status = 'ONGOING';")
            active = cursor.fetchone()
            if active:
                raise ValueError(f"已经有一个进行中的锦标赛 (ID: {active['id']})，请先结束它。")
            
            cursor.execute(
                "INSERT INTO tournaments (status, banker_profit) VALUES ('ONGOING', 0);"
            )
            return cursor.lastrowid

    def end_tournament(self, tournament_id: int) -> Dict[str, Any]:
        """
        结束指定的锦标赛（归档至历史记录，并将状态标记为已结束），在一个事务中完成。
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. 验证锦标赛状态
            cursor.execute("SELECT status FROM tournaments WHERE id = ?;", (tournament_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"未找到 ID 为 {tournament_id} 的锦标赛。")
            if row["status"] == "ENDED":
                raise ValueError(f"该锦标赛 (ID: {tournament_id}) 已经结束。")
            
            # 2. 归档锦标赛的所有轮次到 match_history
            cursor.execute(
                """
                INSERT INTO match_history (tournament_id, round_number, red_score, green_score, winner, banker_round_profit)
                SELECT tournament_id, round_number, red_score, green_score, winner, banker_round_profit
                FROM rounds
                WHERE tournament_id = ?;
                """,
                (tournament_id,)
            )
            
            # 3. 将锦标赛状态变更为已结束
            cursor.execute(
                "UPDATE tournaments SET status = 'ENDED', end_time = CURRENT_TIMESTAMP WHERE id = ?;",
                (tournament_id,)
            )
            
            # 4. 统计返回数据 (庄家总净胜、本次锦标赛积分排行榜)
            cursor.execute("SELECT banker_profit FROM tournaments WHERE id = ?;", (tournament_id,))
            banker_profit = cursor.fetchone()["banker_profit"]
            
            cursor.execute(
                """
                SELECT m.id, m.name, COALESCE(SUM(b.profit_loss), 0) AS tournament_profit
                FROM members m
                JOIN bets b ON b.member_id = m.id
                JOIN rounds r ON b.round_id = r.id
                WHERE r.tournament_id = ?
                GROUP BY m.id
                ORDER BY tournament_profit DESC;
                """,
                (tournament_id,)
            )
            leaderboard = [dict(r) for r in cursor.fetchall()]
            
            return {
                "banker_total_profit": banker_profit,
                "leaderboard": leaderboard
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
        原子事务保存单轮比赛得分、所有投注、各投注人盈亏以及庄家最终盈亏，
        并更新各玩家的历史累计总积分及当前锦标赛的庄家总盈亏。
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. 安全检查：对应的锦标赛必须是进行中 (ONGOING)
            cursor.execute("SELECT status FROM tournaments WHERE id = ?;", (tournament_id,))
            t_row = cursor.fetchone()
            if not t_row:
                raise ValueError(f"锦标赛 (ID: {tournament_id}) 不存在。")
            if t_row["status"] != "ONGOING":
                raise ValueError(f"该锦标赛 (ID: {tournament_id}) 已经结束，无法保存新的轮次结算。")
                
            # 2. 插入 rounds 轮次主表
            cursor.execute(
                """
                INSERT INTO rounds (tournament_id, round_number, red_score, green_score, winner, banker_round_profit)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (tournament_id, round_number, red_score, green_score, winner, banker_round_profit)
            )
            round_id = cursor.lastrowid
            
            # 3. 批量插入 bets 表
            for bet in bets:
                cursor.execute(
                    """
                    INSERT INTO bets (round_id, member_id, bet_amount, prediction, profit_loss, is_player)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (
                        round_id,
                        bet["member_id"],
                        bet["bet_amount"],
                        bet["prediction"],
                        bet["profit_loss"],
                        1 if bet.get("is_player") else 0
                    )
                )
                
            # 4. 更新家庭成员历史累计积分 historical_score
            for sett in settlements:
                cursor.execute(
                    """
                    UPDATE members 
                    SET historical_score = historical_score + ?
                    WHERE id = ?;
                    """,
                    (sett["profit_loss"], sett["member_id"])
                )
                
            # 5. 累加并更新当前锦标赛的庄家净盈利
            cursor.execute(
                """
                UPDATE tournaments
                SET banker_profit = banker_profit + ?
                WHERE id = ?;
                """,
                (banker_round_profit, tournament_id)
            )
            
            return True

    def get_match_history(self) -> List[MatchHistory]:
        """
        从归档表 match_history 中获取所有已结束锦标赛的归档记录。
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, tournament_id, round_number, red_score, green_score, winner, banker_round_profit, archived_at
                FROM match_history
                ORDER BY tournament_id DESC, round_number ASC;
                """
            )
            rows = cursor.fetchall()
            return [
                MatchHistory(
                    id=row["id"],
                    tournament_id=row["tournament_id"],
                    round_number=row["round_number"],
                    red_score=row["red_score"],
                    green_score=row["green_score"],
                    winner=TeamColor(row["winner"]),
                    banker_round_profit=row["banker_round_profit"],
                    archived_at=row["archived_at"]
                )
                for row in rows
            ]

    def get_tournament_leaderboard(self, tournament_id: int) -> List[Dict[str, Any]]:
        """
        获取指定锦标赛的实时盈亏排行榜，包含所有注册的成员（未下注者显示为 0）。
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT m.id, m.name, COALESCE(SUM(b.profit_loss), 0) AS tournament_profit
                FROM members m
                LEFT JOIN bets b ON b.member_id = m.id
                LEFT JOIN rounds r ON b.round_id = r.id AND r.tournament_id = ?
                GROUP BY m.id
                ORDER BY tournament_profit DESC;
                """,
                (tournament_id,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
```

---

## 6. 测试与验证策略

为确保底层系统的健壮性，应使用 `pytest` 编写高覆盖率的单元测试，并在内存数据库中完成测试以防产生磁盘脏数据。

### 6.1 单元测试代码设计 (`tests/database/test_repository.py`)

```python
# @author hyq
# @version 2026-07-13
# test_repository.py: 针对数据库初始化、生命周期、事务回滚等进行自动化验证。

import pytest
import sqlite3
from src.database.db_manager import DatabaseManager
from src.database.repository import Repository
from src.database.models import TeamColor

@pytest.fixture
def repo():
    # 使用 :memory: 确保测试的高效与隔离
    db = DatabaseManager(":memory:")
    r = Repository(db)
    r.initialize_db()
    return r

def test_db_initialization(repo):
    """验证表初始化是否成功"""
    with repo.db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row["name"] for row in cursor.fetchall()]
        for expected in ["members", "tournaments", "rounds", "bets", "match_history"]:
            assert expected in tables

def test_member_constraints(repo):
    """验证成员表唯一键约束"""
    mid = repo.add_member("張三", 1000)
    assert mid > 0
    
    with pytest.raises(sqlite3.IntegrityError):
        repo.add_member("張三")  # 重名应报错

def test_tournament_lifecycle(repo):
    """验证锦标赛生命周期，防止重复开启"""
    t_id = repo.start_tournament()
    assert t_id > 0
    
    # 进行中时，禁止启动新的
    with pytest.raises(ValueError, match="已经有一个进行中的锦标赛"):
        repo.start_tournament()
        
    res = repo.end_tournament(t_id)
    assert res["banker_total_profit"] == 0
    assert len(res["leaderboard"]) == 0
    
    # 结束后可以开启新的锦标赛
    t_id_new = repo.start_tournament()
    assert t_id_new > t_id

def test_save_round_settlement_success(repo):
    """测试单轮比赛结算在正常流下的更新逻辑"""
    m1_id = repo.add_member("张三", 1000)
    m2_id = repo.add_member("李四", 1000)
    t_id = repo.start_tournament()
    
    bets = [
        {"member_id": m1_id, "bet_amount": 20, "prediction": "RED", "profit_loss": 20, "is_player": True},
        {"member_id": m2_id, "bet_amount": 10, "prediction": "GREEN", "profit_loss": -10, "is_player": False}
    ]
    settlements = [
        {"member_id": m1_id, "profit_loss": 20},
        {"member_id": m2_id, "profit_loss": -10}
    ]
    
    # 庄家本轮盈亏：李四输了 10，张三赢了 20，庄家净盈亏为 -10。
    success = repo.save_round_settlement(
        tournament_id=t_id,
        round_number=1,
        red_score=4,
        green_score=2,
        winner="RED",
        banker_round_profit=-10,
        bets=bets,
        settlements=settlements
    )
    assert success
    
    # 验证玩家积分被持久化更改
    members = repo.get_all_members()
    member_map = {m.name: m.historical_score for m in members}
    assert member_map["张三"] == 1020
    assert member_map["李四"] == 990
    
    # 验证当前锦标赛实时排行榜
    leaderboard = repo.get_tournament_leaderboard(t_id)
    lead_map = {item["name"]: item["tournament_profit"] for item in leaderboard}
    assert lead_map["张三"] == 20
    assert lead_map["李四"] == -10

def test_save_round_transactional_rollback(repo):
    """测试事务回滚：若结算中途违反 UNIQUE 约束，所有更改必须完全回滚"""
    m1_id = repo.add_member("张三", 1000)
    t_id = repo.start_tournament()
    
    # 成功写入第 1 轮
    repo.save_round_settlement(
        tournament_id=t_id,
        round_number=1,
        red_score=4,
        green_score=1,
        winner="RED",
        banker_round_profit=0,
        bets=[],
        settlements=[]
    )
    
    # 尝试写入同为第 1 轮的记录，这应当因为 rounds 的 (tournament_id, round_number) 唯一键而报错
    # 我们故意在 settlements 中修改积分，如果回滚失败，张三积分会变，回滚成功则积分依然是 1000
    with pytest.raises(sqlite3.IntegrityError):
        repo.save_round_settlement(
            tournament_id=t_id,
            round_number=1, # 冲突轮次
            red_score=4,
            green_score=3,
            winner="RED",
            banker_round_profit=-10,
            bets=[],
            settlements=[{"member_id": m1_id, "profit_loss": 500}]
        )
        
    # 验证张三积分未被污染，依旧为 1000，证明事务已回滚
    members = repo.get_all_members()
    assert members[0].historical_score == 1000
```

### 6.2 事务隔离性与异常自愈建议
- **锁状态 (`OperationalError: database is locked`)**：
  SQLite 在大并发写入或 GUI 触发频繁读取时，容易发生死锁。针对本 PyQt6 桌面应用，建议使用 `sqlite3.connect(..., timeout=5.0)` 设置合理超时时间，并保证**连接生命周期极短**（借助 `db_manager` 中的 Python 上下文管理器），即用即关，将冲突几率降到最低。
