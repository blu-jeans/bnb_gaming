# BnB 家族比赛积分竞猜系统 - 数据库与 Repository 设计分析报告

本报告针对 **BnB 家族比赛积分竞猜系统** 的第一里程碑（Milestone 1）进行数据库 Schema、Python 3.11 数据模型、SQLite 连接管理以及 Repository 数据访问层设计的深度分析与详细方案设计。

---

## 1. 数据库 Schema 设计 (Database Schema)

本系统使用轻量级本地数据库 **SQLite**。为保证在高频查询、排序（如积分排行榜、锦标赛历史）以及表连接（如计算竞猜盈亏）时的极致性能，设计遵循如下规范：
1. **外键约束与级联**：强制启用 SQLite 外键检查，利用级联删除确保数据完整性。
2. **字段级约束 (Check Constraints)**：定义状态和胜负的合法值范围，确保数据脏值无法入库。
3. **高效索引覆盖**：根据 WHERE、JOIN 和 ORDER BY 涉及的列，定义专属复合/单列索引。

### 1.1 数据库表结构 DDL 定义

```sql
-- 1. 家庭成员/玩家表
CREATE TABLE IF NOT EXISTS members (
    member_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,                          -- 姓名唯一，用于双击添加和防重
    historical_score INTEGER NOT NULL DEFAULT 0,       -- 累计历史总积分（持久化字段，跨锦标赛）
    created_at TEXT NOT NULL                           -- 记录创建时间（ISO8601 本地时间格式）
);

-- 2. 锦标赛表
CREATE TABLE IF NOT EXISTS tournaments (
    tournament_id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL CHECK(status IN ('active', 'completed')), -- 进行中或已结束
    start_time TEXT NOT NULL,                          -- 锦标赛开始时间
    end_time TEXT,                                     -- 结束时间，未结束时为 NULL
    banker_profit INTEGER NOT NULL DEFAULT 0           -- 庄家本届锦标赛的累计最终盈亏（结束时更新）
);

-- 3. 轮次/比赛记录表
CREATE TABLE IF NOT EXISTS rounds (
    round_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL,                     -- 所属锦标赛 ID
    round_number INTEGER NOT NULL,                     -- 本次锦标赛的轮次序号（1, 2, 3...）
    red_score INTEGER NOT NULL,                        -- 红队局内得分（先到4胜，即 0~4）
    green_score INTEGER NOT NULL,                      -- 绿队局内得分（0~4）
    winner TEXT NOT NULL CHECK(winner IN ('RED', 'GREEN')), -- 获胜 camp
    banker_profit INTEGER NOT NULL,                    -- 庄家本轮净盈亏（可正可负）
    created_at TEXT NOT NULL,                          -- 结算时间
    FOREIGN KEY(tournament_id) REFERENCES tournaments(tournament_id) ON DELETE CASCADE,
    UNIQUE(tournament_id, round_number)                -- 保证单届锦标赛内轮次序号不重复
);

-- 4. 投注与结算明细表
CREATE TABLE IF NOT EXISTS bets (
    bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id INTEGER NOT NULL,                         -- 关联轮次 ID
    member_id INTEGER NOT NULL,                        -- 投注人 ID
    bet_amount INTEGER NOT NULL CHECK(bet_amount > 0 AND bet_amount % 5 == 0), -- 投注额必须是5的倍数且大于0
    predicted_team TEXT NOT NULL CHECK(predicted_team IN ('RED', 'GREEN')), -- 押红/押绿
    net_profit INTEGER NOT NULL,                       -- 本轮该玩家的竞猜盈亏（赢则为 +bet_amount，输则为 -bet_amount）
    FOREIGN KEY(round_id) REFERENCES rounds(round_id) ON DELETE CASCADE,
    FOREIGN KEY(member_id) REFERENCES members(member_id) ON DELETE RESTRICT -- 限制删除：已有投注的成员不允许直接删除
);

-- 5. 归档比赛历史表
-- 用于锦标赛结束时一键归档所有轮次，做扁平化持久存储以防关联查询开销
CREATE TABLE IF NOT EXISTS match_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL,
    round_number INTEGER NOT NULL,
    red_score INTEGER NOT NULL,
    green_score INTEGER NOT NULL,
    winner TEXT NOT NULL CHECK(winner IN ('RED', 'GREEN')),
    banker_profit INTEGER NOT NULL,
    archived_at TEXT NOT NULL
);
```

### 1.2 索引设计 DDL (满足 JOIN/WHERE/ORDER BY 性能要求)

```sql
-- 成员历史总分排行榜优化索引
CREATE INDEX IF NOT EXISTS idx_members_historical_score ON members(historical_score DESC);

-- 快速过滤锦标赛状态索引
CREATE INDEX IF NOT EXISTS idx_tournaments_status ON tournaments(status);

-- 关联查询特定锦标赛所有轮次索引
CREATE INDEX IF NOT EXISTS idx_rounds_tournament_id ON rounds(tournament_id);

-- 关联查询特定轮次投注明细索引
CREATE INDEX IF NOT EXISTS idx_bets_round_id ON bets(round_id);

-- 关联查询特定玩家所有投注历史索引（计算排行榜及报表）
CREATE INDEX IF NOT EXISTS idx_bets_member_id ON bets(member_id);

-- 归档历史表按锦标赛 ID 过滤与排序索引
CREATE INDEX IF NOT EXISTS idx_match_history_tournament_id ON match_history(tournament_id);
```

---

## 2. Python 3.11 核心数据模型设计 (Data Models)

在 `src/database/models.py` 中利用 Python 3.11 的 `dataclasses` 及现代类型提示定义实体模型，保持和数据库表的一一对应关系，易于类型检查和 IDE 补全。

```python
# -*- coding: utf-8 -*-
"""
@author hyq
@version 2026-07-13
系统核心数据模型定义。
"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class Member:
    """
    家庭成员/玩家实体类。
    """
    member_id: Optional[int]          # 自增 ID，新建未持久化时为 None
    name: str                         # 姓名，唯一
    historical_score: int             # 历史总积分
    created_at: str                   # 记录创建时间

@dataclass
class Tournament:
    """
    锦标赛实体类。
    """
    tournament_id: Optional[int]
    status: str                       # 'active' (进行中) 或 'completed' (已结束)
    start_time: str
    end_time: Optional[str]
    banker_profit: int                # 庄家本届盈亏累计值

@dataclass
class Round:
    """
    单轮比赛记录实体类。
    """
    round_id: Optional[int]
    tournament_id: int
    round_number: int                 # 第几轮
    red_score: int                    # 红队胜局数 (0~4)
    green_score: int                  # 绿队胜局数 (0~4)
    winner: str                       # 'RED' 或 'GREEN'
    banker_profit: int                # 庄家本轮盈亏
    created_at: str

@dataclass
class Bet:
    """
    玩家单轮投注与结算明细实体类。
    """
    bet_id: Optional[int]
    round_id: int
    member_id: int
    bet_amount: int                   # 投注额（5, 10, 15, 20...）
    predicted_team: str               # 投注队伍
    net_profit: int                   # 该玩家本轮净损益

@dataclass
class MatchHistory:
    """
    已结束锦标赛的归档比赛历史实体类。
    """
    history_id: Optional[int]
    tournament_id: int
    round_number: int
    red_score: int
    green_score: int
    winner: str
    banker_profit: int
    archived_at: str
```

---

## 3. SQLite 连接与事务管理器设计 (Connection Management)

为应对打包成单文件 `.exe` 时对数据库路径的特殊解析要求，以及 SQLite 外键约束默认关闭的问题，我们在 `src/database/db_manager.py` 中实现自动化管理：
1. 使用 `sys.frozen` 检测 PyInstaller 环境，确保 `bnb_betting.db` 始终在 `.exe` 所在同级目录下创建或读取。
2. 上下文管理器在 `yield` 出连接前，无条件执行 `PRAGMA foreign_keys = ON;`。
3. 捕获 yield 块内所有异常，若出错则执行 `rollback`，成功则执行 `commit`，最后强制在 `finally` 中关闭连接。
4. 提供运行时动态修改默认 DB 路径的钩子，极大便利了内存数据库 (`:memory:`) 单元测试的开展。

```python
# -*- coding: utf-8 -*-
"""
@author hyq
@version 2026-07-13
数据库连接管理器，提供 SQLite 连接的上下文管理、路径自动解析及全局事务边界。
"""
import os
import sys
import sqlite3
from contextlib import contextmanager

DB_NAME = "bnb_betting.db"
_DB_PATH_OVERRIDE = None  # 用于单元测试注入的路径覆盖（如 ":memory:"）

def get_db_path() -> str:
    """
    获取 SQLite 数据库文件的绝对路径。
    支持 PyInstaller 打包环境与开发脚本运行环境。
    """
    global _DB_PATH_OVERRIDE
    if _DB_PATH_OVERRIDE is not None:
        return _DB_PATH_OVERRIDE
        
    if getattr(sys, 'frozen', False):
        # 处于 PyInstaller 打包运行状态下，返回 exe 文件所在目录
        base_dir = os.path.dirname(sys.executable)
    else:
        # 开发环境下，返回项目根目录 (即 src/database/../../)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
    return os.path.join(base_dir, DB_NAME)

def set_db_path(path: str) -> None:
    """
    注入覆盖默认的 DB 路径。主要供 unittest 使用以指定内存数据库 ":memory:"。
    """
    global _DB_PATH_OVERRIDE
    _DB_PATH_OVERRIDE = path

@contextmanager
def get_connection(db_path: str = None):
    """
    SQLite 连接上下文管理器。
    - 自动管理连接关闭。
    - 启用 SQLite 外键检查机制。
    - 统一将 row_factory 配置为 sqlite3.Row（允许键名检索列值）。
    - 发生未捕获异常时自动 rollback，全部成功时自动 commit。
    """
    if db_path is None:
        db_path = get_db_path()
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # 核心步骤：SQLite 默认不开启外键检查，必须在每条连接建立时手动启用
    conn.execute("PRAGMA foreign_keys = ON;")
    
    try:
        yield conn
        conn.commit()  # 正常退出 block，提交事务
    except Exception as e:
        conn.rollback()  # 异常抛出，回滚事务，确保积分/投注保存的数据一致性
        raise e
    finally:
        conn.close()  # 最终关闭物理连接
```

---

## 4. Repository 数据访问接口设计 (Repository API)

Repository 是系统的唯一持久层抽象。在 `src/database/repository.py` 中，所有写操作均运行在单一的物理事务内，拒绝逻辑层的手工事务拼接，防止出现异常时出现脏数据。

```python
# -*- coding: utf-8 -*-
"""
@author hyq
@version 2026-07-13
数据访问层（Repository），集中实现所有核心 CRUD、业务操作事务和多表关联查询。
"""
from typing import Optional, List, Dict, Any
from .db_manager import get_connection
from .models import Member, Tournament, Round, Bet, MatchHistory

def initialize_db() -> None:
    """
    在数据库中初始化创建表和对应的优化索引。
    通常在主程序启动时被调用。
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. 成员表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS members (
            member_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            historical_score INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        """)
        
        # 2. 锦标赛表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournaments (
            tournament_id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL CHECK(status IN ('active', 'completed')),
            start_time TEXT NOT NULL,
            end_time TEXT,
            banker_profit INTEGER NOT NULL DEFAULT 0
        );
        """)
        
        # 3. 局轮次表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS rounds (
            round_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL,
            round_number INTEGER NOT NULL,
            red_score INTEGER NOT NULL,
            green_score INTEGER NOT NULL,
            winner TEXT NOT NULL CHECK(winner IN ('RED', 'GREEN')),
            banker_profit INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(tournament_id) REFERENCES tournaments(tournament_id) ON DELETE CASCADE,
            UNIQUE(tournament_id, round_number)
        );
        """)
        
        # 4. 投注与结算表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            bet_amount INTEGER NOT NULL CHECK(bet_amount > 0 AND bet_amount % 5 == 0),
            predicted_team TEXT NOT NULL CHECK(predicted_team IN ('RED', 'GREEN')),
            net_profit INTEGER NOT NULL,
            FOREIGN KEY(round_id) REFERENCES rounds(round_id) ON DELETE CASCADE,
            FOREIGN KEY(member_id) REFERENCES members(member_id) ON DELETE RESTRICT
        );
        """)
        
        # 5. 归档历史表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS match_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL,
            round_number INTEGER NOT NULL,
            red_score INTEGER NOT NULL,
            green_score INTEGER NOT NULL,
            winner TEXT NOT NULL CHECK(winner IN ('RED', 'GREEN')),
            banker_profit INTEGER NOT NULL,
            archived_at TEXT NOT NULL
        );
        """)
        
        # 6. 高效率优化索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_members_historical_score ON members(historical_score DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tournaments_status ON tournaments(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rounds_tournament_id ON rounds(tournament_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bets_round_id ON bets(round_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bets_member_id ON bets(member_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_match_history_tournament_id ON match_history(tournament_id);")

def add_member(name: str, initial_score: int = 0) -> int:
    """
    添加新家庭成员。
    - 约束：name 唯一。重复时抛出 sqlite3.IntegrityError。
    返回 member_id。
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO members (name, historical_score, created_at) VALUES (?, ?, datetime('now', 'localtime'))",
            (name, initial_score)
        )
        return cursor.lastrowid

def get_all_members() -> List[Member]:
    """
    获取系统内所有成员实体，结果按姓名升序排列。
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT member_id, name, historical_score, created_at FROM members ORDER BY name ASC")
        rows = cursor.fetchall()
        return [Member(row['member_id'], row['name'], row['historical_score'], row['created_at']) for row in rows]

def start_tournament() -> int:
    """
    开启一届新锦标赛。
    - 约束：系统同一时刻只能有一届 active 状态的锦标赛。若已存在活动比赛，则拒绝创建并抛出 ValueError。
    返回新建的 tournament_id。
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 判断当前是否有进行中的比赛
        cursor.execute("SELECT tournament_id FROM tournaments WHERE status = 'active'")
        active = cursor.fetchone()
        if active:
            raise ValueError(f"当前已有正在进行的锦标赛 (ID: {active['tournament_id']})。请先结束它再开新比赛。")
        
        cursor.execute(
            "INSERT INTO tournaments (status, start_time, banker_profit) VALUES ('active', datetime('now', 'localtime'), 0)"
        )
        return cursor.lastrowid

def get_active_tournament_id() -> Optional[int]:
    """
    查询当前活跃的锦标赛 ID。如果没有进行中的锦标赛则返回 None。
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT tournament_id FROM tournaments WHERE status = 'active'")
        row = cursor.fetchone()
        return row['tournament_id'] if row else None

def save_round_settlement(
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
    【事务一致性核心】保存单局比分、更新本局所有玩家的投注/收益以及家庭成员累积历史总分。
    
    1. 校验锦标赛活跃性约束。
    2. 向 rounds 插入一笔结算记录。
    3. 解析 settlements 建立 成员ID -> net_profit 快速查找表。
    4. 对每一笔投注 bet：
       a. 插入 bets 数据记录。
       b. 原子地更新该成员的历史总积分（`historical_score = historical_score + net_profit`）。
       
    上述流程全程在一个物理事务（`get_connection()` 内部）中自动提交，任何步骤（如非法成员ID、违反金额约束等）报错，都会整体回滚。
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. 验证锦标赛状态
        cursor.execute("SELECT status FROM tournaments WHERE tournament_id = ?", (tournament_id,))
        t_row = cursor.fetchone()
        if not t_row:
            raise ValueError(f"锦标赛 ID {tournament_id} 不存在。")
        if t_row['status'] != 'active':
            raise ValueError(f"锦标赛 ID {tournament_id} 不是进行中状态，无法进行结算保存。")
        
        # 2. 插入局轮次记录
        cursor.execute(
            """INSERT INTO rounds (tournament_id, round_number, red_score, green_score, winner, banker_profit, created_at)
               VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))""",
            (tournament_id, round_number, red_score, green_score, winner, banker_round_profit)
        )
        round_id = cursor.lastrowid
        
        # 3. 创建映射表，加速批量积分更新
        profit_map = {s['member_id']: s['net_profit'] for s in settlements}
        
        # 4. 录入明细并修改用户账户历史积分
        for bet in bets:
            member_id = bet['member_id']
            bet_amount = bet['bet_amount']
            predicted_team = bet['predicted_team']
            net_profit = profit_map.get(member_id, 0)
            
            # 保存投注
            cursor.execute(
                """INSERT INTO bets (round_id, member_id, bet_amount, predicted_team, net_profit)
                   VALUES (?, ?, ?, ?, ?)""",
                (round_id, member_id, bet_amount, predicted_team, net_profit)
            )
            
            # 原子更新玩家积分表
            cursor.execute(
                "UPDATE members SET historical_score = historical_score + ? WHERE member_id = ?",
                (net_profit, member_id)
            )
            
        return True

def end_tournament(tournament_id: int) -> Dict[str, Any]:
    """
    【事务一致性核心】结束本届锦标赛并执行历史数据扁平化归档。
    
    1. 验证待结束比赛的状态。
    2. 对 rounds 局轮表进行聚合：SUM(banker_profit) 计算本届庄家累计总盈亏。
    3. 更新 tournaments 表对应的 status='completed'，记录结束时间和总庄家盈利。
    4. 将本届锦标赛的所有局次，原子复制并插入到已归档的比赛历史表 `match_history` 中。
    5. 返回包含本届最终庄家总收益和玩家锦标赛利润排名等结算快照。
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. 确认锦标赛活跃性
        cursor.execute("SELECT status FROM tournaments WHERE tournament_id = ?", (tournament_id,))
        t_row = cursor.fetchone()
        if not t_row:
            raise ValueError(f"锦标赛 ID {tournament_id} 不存在。")
        if t_row['status'] == 'completed':
            raise ValueError(f"锦标赛 ID {tournament_id} 早已结束，请勿重复操作。")
        
        # 2. 统计庄家累积总盈亏
        cursor.execute("SELECT COALESCE(SUM(banker_profit), 0) AS total_profit FROM rounds WHERE tournament_id = ?", (tournament_id,))
        banker_total_profit = cursor.fetchone()['total_profit']
        
        # 3. 归并更新锦标赛记录状态
        cursor.execute(
            """UPDATE tournaments 
               SET status = 'completed', end_time = datetime('now', 'localtime'), banker_profit = ? 
               WHERE tournament_id = ?""",
            (banker_total_profit, tournament_id)
        )
        
        # 4. 数据归档至扁平表（match_history）
        cursor.execute(
            "SELECT round_number, red_score, green_score, winner, banker_profit FROM rounds WHERE tournament_id = ?",
            (tournament_id,)
        )
        rounds_to_archive = cursor.fetchall()
        for r in rounds_to_archive:
            cursor.execute(
                """INSERT INTO match_history (tournament_id, round_number, red_score, green_score, winner, banker_profit, archived_at)
                   VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))""",
                (tournament_id, r['round_number'], r['red_score'], r['green_score'], r['winner'], r['banker_profit'])
            )
            
        # 5. 生成玩家在该届锦标赛的最终积分排行榜
        leaderboard = get_tournament_leaderboard_conn(conn, tournament_id)
        
        return {
            'tournament_id': tournament_id,
            'banker_profit': banker_total_profit,
            'leaderboard': leaderboard
        }

def get_tournament_leaderboard_conn(conn, tournament_id: int) -> List[Dict[str, Any]]:
    """
    使用活动连接获取指定锦标赛的个人盈亏排行榜。
    不参与该届投注的玩家默认展示且收益为 0。
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT m.member_id, m.name, COALESCE(SUM(b.net_profit), 0) AS tournament_profit
        FROM members m
        LEFT JOIN bets b ON m.member_id = b.member_id AND b.round_id IN (
            SELECT round_id FROM rounds WHERE tournament_id = ?
        )
        GROUP BY m.member_id
        ORDER BY tournament_profit DESC, m.name ASC
        """,
        (tournament_id,)
    )
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

def get_tournament_leaderboard(tournament_id: int) -> List[Dict[str, Any]]:
    """
    获取指定锦标赛的成员盈亏排行榜（外部接口）。
    """
    with get_connection() as conn:
        return get_tournament_leaderboard_conn(conn, tournament_id)

def get_historical_leaderboard() -> List[Dict[str, Any]]:
    """
    获取所有玩家累积的跨锦标赛总积分排行榜。
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT member_id, name, historical_score FROM members ORDER BY historical_score DESC, name ASC"
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_match_history() -> List[Dict[str, Any]]:
    """
    从归档历史表查询所有已结束锦标赛的历史战局记录。
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT history_id, tournament_id, round_number, red_score, green_score, winner, banker_profit, archived_at
            FROM match_history
            ORDER BY tournament_id DESC, round_number DESC
            """
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
```

---

## 5. 单元测试策略与验证方案 (Unit Testing Strategy)

为保障竞猜系统的金融级严谨性（特别是积分为 0 守恒不凭空流失/产生的特性），必须对以下关键机制开展严密的单元测试：
1. **外键约束与数据校验测试**：输入无效的 `member_id`、非法投注数额时，数据库抛出 IntegrityError 终止。
2. **多活跃锦标赛拒绝测试**：锦标赛开启阶段的互斥锁保护。
3. **单轮结算事务一致性与回滚机制测试**：通过破坏其内部分流程，检验是否触发 ROLLBACK 恢复现场历史积分，证明其具备“防大面积崩溃后数据混乱”的鲁棒性。

### 5.1 单元测试代码设计 (`tests/test_database.py`)

```python
# -*- coding: utf-8 -*-
"""
@author hyq
@version 2026-07-13
系统持久层单元测试用例，采用 SQLite 内存数据库确保不污染物理磁盘。
"""
import unittest
import sqlite3
from database.db_manager import set_db_path, get_connection
from database import repository

class TestBnBDatabase(unittest.TestCase):
    def setUp(self):
        # 1. 强制注入内存数据库
        self.db_path = ":memory:"
        set_db_path(self.db_path)
        
        # 2. 调用 repository 进行结构初始化
        repository.initialize_db()
        
        # 3. 预置基础玩家数据
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO members (name, historical_score, created_at) VALUES ('Alice', 100, '2026-07-13 12:00:00')")
            cursor.execute("INSERT INTO members (name, historical_score, created_at) VALUES ('Bob', 100, '2026-07-13 12:00:00')")
            cursor.execute("INSERT INTO members (name, historical_score, created_at) VALUES ('Charlie', 100, '2026-07-13 12:00:00')")

    def tearDown(self):
        # 还原默认物理文件路径，防止对其他模块测试产生交叉影响
        set_db_path(None)

    def test_add_member_integrity(self):
        """测试家庭成员添加和姓名唯一性强校验"""
        # 正常添加
        member_id = repository.add_member("David", 50)
        self.assertIsNotNone(member_id)
        
        # 重名添加应该抛出 IntegrityError
        with self.assertRaises(sqlite3.IntegrityError):
            repository.add_member("Alice", 0)

    def test_tournament_lifecycle_concurrency(self):
        """测试开启锦标赛生命周期的多活动状态互斥保护"""
        t_id_1 = repository.start_tournament()
        self.assertIsNotNone(t_id_1)
        
        # 已有活跃锦标赛，再次开启应抛 ValueError
        with self.assertRaises(ValueError):
            repository.start_tournament()
            
        # 验证能正确获取当前的活跃锦标赛 ID
        self.assertEqual(repository.get_active_tournament_id(), t_id_1)

    def test_save_round_settlement_success(self):
        """测试正常竞猜轮次的保存及账户历史积分的变动"""
        t_id = repository.start_tournament()
        
        # 构造竞猜条件：
        # Alice 投 20 点 RED (赢)
        # Bob 投 10 点 GREEN (输)
        # Charlie 不进行任何投注 (Spectator，无分数变动)
        # 庄家该轮收益 = 输家 10 - 赢家 20 = -10 点
        
        # 假设 Alice 的 ID 为 1，Bob 的 ID 为 2，Charlie 为 3
        bets = [
            {"member_id": 1, "bet_amount": 20, "predicted_team": "RED"},
            {"member_id": 2, "bet_amount": 10, "predicted_team": "GREEN"}
        ]
        settlements = [
            {"member_id": 1, "net_profit": 20},
            {"member_id": 2, "net_profit": -10}
        ]
        
        success = repository.save_round_settlement(
            tournament_id=t_id,
            round_number=1,
            red_score=4,
            green_score=1,
            winner="RED",
            banker_round_profit=-10,
            bets=bets,
            settlements=settlements
        )
        self.assertTrue(success)
        
        # 验证成员历史账户分数是否获得同步累计
        members = {m.name: m.historical_score for m in repository.get_all_members()}
        self.assertEqual(members["Alice"], 120)    # 100 + 20
        self.assertEqual(members["Bob"], 90)       # 100 - 10
        self.assertEqual(members["Charlie"], 100)  # 保持 100

    def test_save_round_settlement_rollback(self):
        """测试事务的回滚机制：当投注数据非法触发约束时，所有先前对积分的写操作应全面取消"""
        t_id = repository.start_tournament()
        
        # 非法投注列表：试图为不存在的成员 999 插入投注记录，这将由于 foreign_keys 约束校验失败
        bets = [
            {"member_id": 1, "bet_amount": 20, "predicted_team": "RED"},
            {"member_id": 999, "bet_amount": 15, "predicted_team": "RED"} # 非法 ID
        ]
        settlements = [
            {"member_id": 1, "net_profit": 20},
            {"member_id": 999, "net_profit": 15}
        ]
        
        # 保存轮次，此时因为外键约束失败，save_round_settlement 会抛出 IntegrityError 异常
        with self.assertRaises(sqlite3.IntegrityError):
            repository.save_round_settlement(
                tournament_id=t_id,
                round_number=1,
                red_score=4,
                green_score=2,
                winner="RED",
                banker_round_profit=-35,
                bets=bets,
                settlements=settlements
            )
            
        # 事务应该整体回滚，我们检查 Alice 的历史积分是否没有改变
        members = {m.name: m.historical_score for m in repository.get_all_members()}
        self.assertEqual(members["Alice"], 100) # 未受部分成功写入的 SQL 污染，数据完好如初

    def test_end_tournament_archiving_and_leaderboard(self):
        """测试结束锦标赛的归档流程和排行榜数据准确性"""
        t_id = repository.start_tournament()
        
        # 插入一轮有效局
        bets = [
            {"member_id": 1, "bet_amount": 20, "predicted_team": "RED"},
            {"member_id": 2, "bet_amount": 15, "predicted_team": "GREEN"}
        ]
        settlements = [
            {"member_id": 1, "net_profit": 20},
            {"member_id": 2, "net_profit": -15}
        ]
        repository.save_round_settlement(
            tournament_id=t_id,
            round_number=1,
            red_score=4,
            green_score=3,
            winner="RED",
            banker_round_profit=-5,
            bets=bets,
            settlements=settlements
        )
        
        # 结束锦标赛并执行一键归档
        summary = repository.end_tournament(tournament_id=t_id)
        self.assertEqual(summary["banker_profit"], -5)
        
        # 验证活跃锦标赛是否关闭为 None
        self.assertIsNone(repository.get_active_tournament_id())
        
        # 验证 match_history 归档表中是否存在此数据
        history = repository.get_match_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["tournament_id"], t_id)
        self.assertEqual(history[0]["banker_profit"], -5)
        
        # 验证单次锦标赛盈亏排行榜的正确性
        leaderboard = summary["leaderboard"]
        # Alice 排名第一 (+20)，Charlie 并列第二 (0，无投注)，Bob 垫底 (-15)
        self.assertEqual(leaderboard[0]["name"], "Alice")
        self.assertEqual(leaderboard[0]["tournament_profit"], 20)
        self.assertEqual(leaderboard[1]["name"], "Charlie")
        self.assertEqual(leaderboard[1]["tournament_profit"], 0)
        self.assertEqual(leaderboard[2]["name"], "Bob")
        self.assertEqual(leaderboard[2]["tournament_profit"], -15)

if __name__ == '__main__':
    unittest.main()
```

---

## 6. 积分守恒数学与逻辑证明 (Score Conservation Verification)

BnB 竞猜系统作为闭环的“庄闲博弈模型”，其结算和资金流动必须严格遵循 **积分守恒定律**。以下提供其零和属性的逻辑证明。

### 6.1 定义符号
设参与本轮竞猜的玩家集合为 $M$。
- 将竞猜正确的玩家集合记为 $M_{correct} \subseteq M$；
- 将竞猜错误的玩家集合记为 $M_{wrong} \subseteq M$；
- 将没有任何投注的旁观者玩家集合记为 $M_{spectator}$。
显然，$M_{correct} \cap M_{wrong} = \emptyset$，$M_{correct} \cup M_{wrong}$ 等于所有进行投注的玩家集合。

每个投注玩家 $i \in M$ 投注的积分为 $X_i$（由系统校验为正数且 $X_i \pmod 5 = 0$）。

### 6.2 积分账户变动计算
1. **竞猜正确者账户变动** ($\Delta S_i$)：
   $$\forall i \in M_{correct}, \quad \Delta S_i = +X_i$$
   竞猜正确者全体积分变动总量：
   $$\Delta S_{correct} = \sum_{i \in M_{correct}} X_i$$

2. **竞猜错误者账户变动** ($\Delta S_j$)：
   $$\forall j \in M_{wrong}, \quad \Delta S_j = -X_j$$
   竞猜错误者全体积分变动总量：
   $$\Delta S_{wrong} = \sum_{j \in M_{wrong}} (-X_j) = -\sum_{j \in M_{wrong}} X_j$$

3. **旁观者账户变动** ($\Delta S_k$)：
   $$\forall k \in M_{spectator}, \quad \Delta S_k = 0$$

4. **庄家账户盈亏变动** ($P_{banker}$)：
   根据需求，庄家单轮盈亏规则为“输家投注总额减去赢家收益总额”：
   $$P_{banker} = \sum_{j \in M_{wrong}} X_j - \sum_{i \in M_{correct}} X_i$$

### 6.3 守恒验证
将本轮所有实体（全体玩家账户和庄家临时账户）的积分变化累加：
$$\sum_{m \in M} \Delta S_m + P_{banker} = \Delta S_{correct} + \Delta S_{wrong} + \Delta S_{spectator} + P_{banker}$$

代入各分项计算值：
$$\sum_{m \in M} \Delta S_m + P_{banker} = \sum_{i \in M_{correct}} X_i - \sum_{j \in M_{wrong}} X_j + 0 + \left( \sum_{j \in M_{wrong}} X_j - \sum_{i \in M_{correct}} X_i \right)$$

消除相反项：
$$\sum_{m \in M} \Delta S_m + P_{banker} = \left( \sum_{i \in M_{correct}} X_i - \sum_{i \in M_{correct}} X_i \right) + \left( \sum_{j \in M_{wrong}} X_j - \sum_{j \in M_{wrong}} X_j \right) = 0$$

### 6.4 结论
在物理事务隔离保护下，数据库每次调用 `save_round_settlement` 写入后，**所有玩家的历史积分变动之和与庄家的收益变动之和互为相反数，净值严格为 0**。积分既没有在数据库中凭空逃逸，也绝无重复累计，系统设计逻辑数学上守恒。
