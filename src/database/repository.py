# -*- coding: utf-8 -*-
"""
@author hyq
@version 2026-07-13
"""

import sqlite3
from typing import Any
from src.database.db_manager import DBManager
from src.database.models import Member, GameAccount, Tournament, Round, Bet, MatchHistory, TournamentStatus, TeamColor

class Repository:
    """
    仓储服务层，执行具体的数据库操作，确保事务的原子性
    """
    def __init__(self, db_manager: DBManager):
        self.db_manager = db_manager

    def initialize_db(self) -> None:
        """
        初始化数据库架构，创建所有必要的表和索引
        """
        with self.db_manager.connection(write=True) as conn:
            # 1. 创建成员表
            # hyq: 2026-07-13 Modify to add is_banker column
            # conn.execute("""
            #     CREATE TABLE IF NOT EXISTS members (
            #         id INTEGER PRIMARY KEY AUTOINCREMENT,
            #         name TEXT UNIQUE NOT NULL,
            #         historical_score INTEGER NOT NULL DEFAULT 0,
            #         created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            #     );
            # """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    historical_score INTEGER NOT NULL DEFAULT 0,
                    is_banker INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # 2. 创建锦标赛表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tournaments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT CHECK(status IN ('ongoing', 'ended')) NOT NULL DEFAULT 'ongoing',
                    banker_profit INTEGER NOT NULL DEFAULT 0,
                    start_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP
                );
            """)

            # 3. 创建轮次表
            # hyq: 2026-07-13 Modify to add red_players, green_players and bet_details columns
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rounds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tournament_id INTEGER NOT NULL,
                    round_number INTEGER NOT NULL,
                    red_score INTEGER NOT NULL,
                    green_score INTEGER NOT NULL,
                    winner TEXT CHECK(winner IN ('Red', 'Green')) NOT NULL,
                    banker_round_profit INTEGER NOT NULL,
                    red_players TEXT NOT NULL DEFAULT '',
                    green_players TEXT NOT NULL DEFAULT '',
                    bet_details TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
                    UNIQUE (tournament_id, round_number)
                );
            """)

            # 4. 创建投注表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    round_id INTEGER NOT NULL,
                    member_id INTEGER NOT NULL,
                    bet_amount INTEGER NOT NULL CHECK(bet_amount >= 0),
                    prediction TEXT CHECK(prediction IN ('Red', 'Green')) NOT NULL,
                    profit_loss INTEGER NOT NULL,
                    is_player INTEGER CHECK(is_player IN (0, 1)) NOT NULL DEFAULT 0,
                    FOREIGN KEY (round_id) REFERENCES rounds(id) ON DELETE CASCADE,
                    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
                    UNIQUE (round_id, member_id)
                );
            """)

            # 5. 创建对战历史表
            # hyq: 2026-07-13 Modify to add red_players, green_players and bet_details columns
            conn.execute("""
                CREATE TABLE IF NOT EXISTS match_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tournament_id INTEGER NOT NULL,
                    round_number INTEGER NOT NULL,
                    red_score INTEGER NOT NULL,
                    green_score INTEGER NOT NULL,
                    winner TEXT CHECK(winner IN ('Red', 'Green')) NOT NULL,
                    banker_round_profit INTEGER NOT NULL,
                    red_players TEXT NOT NULL DEFAULT '',
                    green_players TEXT NOT NULL DEFAULT '',
                    bet_details TEXT NOT NULL DEFAULT '',
                    archived_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
                    UNIQUE (tournament_id, round_number)
                );
            """)

            # 数据库平滑升级 DDL
            try:
                conn.execute("ALTER TABLE rounds ADD COLUMN bet_details TEXT NOT NULL DEFAULT ''")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE match_history ADD COLUMN bet_details TEXT NOT NULL DEFAULT ''")
            except sqlite3.OperationalError:
                pass

            # 根据 SQL 开发规范创建辅助索引以防止慢查询并满足 JOIN / WHERE 查询索引覆盖要求
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tournaments_status ON tournaments(status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rounds_tournament_id ON rounds(tournament_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_bets_round_id ON bets(round_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_bets_member_id ON bets(member_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_match_history_tournament_id ON match_history(tournament_id);")

            # hyq: 2026-07-13 Add game_accounts table for match player game IDs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS game_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nickname TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # hyq: 2026-07-13 Add pre-population check for 34 family members and banker role
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM members")
            count = cursor.fetchone()[0]
            if count == 0:
                default_members = [
                    ("棉花", 0), ("P5", 0), ("斌", 0), ("滋味", 0), ("F", 0), ("冰", 0), ("雀占", 0),
                    ("小黑", 0), ("仁俊", 0), ("大宝", 0), ("爱恋", 0), ("恋", 0), ("蟋蟀", 0), ("君王", 0),
                    ("月子", 0), ("老王", 0), ("螺丝", 0), ("千序", 0), ("兰兰", 0), ("燕子", 0), ("咬字", 0),
                    ("欢", 0), ("娜娜", 0), ("托尼", 0), ("敏宝", 0), ("通", 0), ("飓风", 0), ("爱火花", 0),
                    ("今天", 0), ("李硕", 0), ("觅魅", 0), ("车", 0), ("主持人", 1), ("大哥", 0)
                ]
                conn.executemany(
                    "INSERT INTO members (name, historical_score, is_banker) VALUES (?, 0, ?)",
                    default_members
                )

            # hyq: 2026-07-13 Pre-populate game accounts
            cursor.execute("SELECT COUNT(*) FROM game_accounts")
            ga_count = cursor.fetchone()[0]
            if ga_count == 0:
                default_accounts = [
                    "别了七月", "淡若衣长", "倾城初遇",
                    "Mrˇ戀°", "君诺寒", "挨个弄死"
                ]
                conn.executemany(
                    "INSERT INTO game_accounts (nickname) VALUES (?)",
                    [(n,) for n in default_accounts]
                )

    # hyq: 2026-07-13 Modify to accept is_banker and support new field
    # def add_member(self, name: str, historical_score: int = 0) -> Member:
    #     """
    #     添加一名新成员
    #     如果成员姓名已存在，则抛出 ValueError
    #     """
    #     with self.db_manager.connection(write=True) as conn:
    #         cursor = conn.cursor()
    #         try:
    #             cursor.execute(
    #                 "INSERT INTO members (name, historical_score) VALUES (?, ?)",
    #                 (name, historical_score)
    #             )
    #             member_id = cursor.lastrowid
    #         except sqlite3.IntegrityError as e:
    #             raise ValueError(f"成员姓名 '{name}' 已存在") from e
    #
    #         cursor.execute("SELECT id, name, historical_score, created_at FROM members WHERE id = ?", (member_id,))
    #         row = cursor.fetchone()
    #         return Member(
    #             id=row.id,
    #             name=row.name,
    #             historical_score=row.historical_score,
    #             created_at=row.created_at
    #         )
    def add_member(self, name: str, historical_score: int = 0, is_banker: bool = False) -> Member:
        """
        添加一名新成员
        如果成员姓名已存在，则抛出 ValueError
        """
        with self.db_manager.connection(write=True) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO members (name, historical_score, is_banker) VALUES (?, ?, ?)",
                    (name, historical_score, 1 if is_banker else 0)
                )
                member_id = cursor.lastrowid
            except sqlite3.IntegrityError as e:
                raise ValueError(f"成员姓名 '{name}' 已存在") from e

            cursor.execute("SELECT id, name, historical_score, is_banker, created_at FROM members WHERE id = ?", (member_id,))
            row = cursor.fetchone()
            return Member(
                id=row.id,
                name=row.name,
                historical_score=row.historical_score,
                is_banker=bool(row.is_banker),
                created_at=row.created_at
            )

    # hyq: 2026-07-13 Modify to fetch and instantiate is_banker field
    # def get_all_members(self) -> list[Member]:
    #     """
    #     获取数据库中所有的成员列表，按名字字母排序
    #     """
    #     with self.db_manager.connection() as conn:
    #         cursor = conn.cursor()
    #         cursor.execute("SELECT id, name, historical_score, created_at FROM members ORDER BY name ASC")
    #         rows = cursor.fetchall()
    #         return [
    #             Member(
    #                 id=row.id,
    #                 name=row.name,
    #                 historical_score=row.historical_score,
    #                 created_at=row.created_at
    #             )
    #             for row in rows
    #         ]
    def get_all_members(self) -> list[Member]:
        """
        获取数据库中所有的成员列表，按名字字母排序
        """
        with self.db_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, historical_score, is_banker, created_at FROM members ORDER BY name ASC")
            rows = cursor.fetchall()
            return [
                Member(
                    id=row.id,
                    name=row.name,
                    historical_score=row.historical_score,
                    is_banker=bool(row.is_banker),
                    created_at=row.created_at
                )
                for row in rows
            ]

    def start_tournament(self) -> Tournament:
        """
        开始一轮新的锦标赛。若已有正在进行中的锦标赛则抛出 ValueError
        """
        with self.db_manager.connection(write=True) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM tournaments WHERE status = 'ongoing'")
            if cursor.fetchone():
                raise ValueError("无法开始新锦标赛，当前已存在正在进行中(ongoing)的锦标赛")

            cursor.execute("INSERT INTO tournaments (status, banker_profit) VALUES ('ongoing', 0)")
            tournament_id = cursor.lastrowid

            cursor.execute("SELECT id, status, banker_profit, start_time, end_time FROM tournaments WHERE id = ?", (tournament_id,))
            row = cursor.fetchone()
            return Tournament(
                id=row.id,
                status=TournamentStatus(row.status),
                banker_profit=row.banker_profit,
                start_time=row.start_time,
                end_time=row.end_time
            )

    def end_tournament(self, tournament_id: int | None = None) -> Tournament:
        """
        结束指定的或当前进行中的锦标赛
        若指定的锦标赛不存在或已结束，抛出 ValueError
        若无指定且当前没有进行中的锦标赛，抛出 ValueError
        """
        with self.db_manager.connection(write=True) as conn:
            cursor = conn.cursor()
            if tournament_id is not None:
                cursor.execute("SELECT id, status, banker_profit, start_time, end_time FROM tournaments WHERE id = ?", (tournament_id,))
                row = cursor.fetchone()
                if not row:
                    raise ValueError(f"未找到 ID 为 {tournament_id} 的锦标赛")
                if row.status == "ended":
                    raise ValueError(f"ID 为 {tournament_id} 的锦标赛已处于结束状态")
                target_id = tournament_id
            else:
                cursor.execute("SELECT id, status, banker_profit, start_time, end_time FROM tournaments WHERE status = 'ongoing'")
                row = cursor.fetchone()
                if not row:
                    raise ValueError("当前没有进行中(ongoing)的锦标赛")
                target_id = row.id

            cursor.execute(
                "UPDATE tournaments SET status = 'ended', end_time = CURRENT_TIMESTAMP WHERE id = ?",
                (target_id,)
            )

            cursor.execute("SELECT id, status, banker_profit, start_time, end_time FROM tournaments WHERE id = ?", (target_id,))
            updated_row = cursor.fetchone()
            return Tournament(
                id=updated_row.id,
                status=TournamentStatus(updated_row.status),
                banker_profit=updated_row.banker_profit,
                start_time=updated_row.start_time,
                end_time=updated_row.end_time
            )

    def save_round_settlement(self, round_data: Round, bets_data: list[Bet]) -> None:
        """
        保存轮次结算，必须在单一事务中执行：
        1. 插入轮次记录 (rounds)
        2. 归档到历史记录 (match_history)
        3. 批量插入投注记录 (bets)
        4. 更新成员的历史总分 (members.historical_score)
        5. 累加并更新锦标赛的庄家收益 (tournaments.banker_profit)
        """
        with self.db_manager.connection(write=True) as conn:
            cursor = conn.cursor()
            # 1. 插入 rounds 记录
            # hyq: 2026-07-13 Modify to include red_players, green_players and bet_details
            cursor.execute(
                """
                INSERT INTO rounds (tournament_id, round_number, red_score, green_score, winner, banker_round_profit, red_players, green_players, bet_details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    round_data.tournament_id,
                    round_data.round_number,
                    round_data.red_score,
                    round_data.green_score,
                    round_data.winner.value,
                    round_data.banker_round_profit,
                    round_data.red_players,
                    round_data.green_players,
                    round_data.bet_details
                )
            )
            round_id = cursor.lastrowid

            # 2. 插入 match_history 记录
            # hyq: 2026-07-13 Modify to include red_players, green_players and bet_details
            cursor.execute(
                """
                INSERT INTO match_history (tournament_id, round_number, red_score, green_score, winner, banker_round_profit, red_players, green_players, bet_details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    round_data.tournament_id,
                    round_data.round_number,
                    round_data.red_score,
                    round_data.green_score,
                    round_data.winner.value,
                    round_data.banker_round_profit,
                    round_data.red_players,
                    round_data.green_players,
                    round_data.bet_details
                )
            )

            # 3. 批量插入投注记录并更新成员的历史分数
            for bet in bets_data:
                cursor.execute(
                    """
                    INSERT INTO bets (round_id, member_id, bet_amount, prediction, profit_loss, is_player)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        round_id,
                        bet.member_id,
                        bet.bet_amount,
                        bet.prediction.value,
                        bet.profit_loss,
                        1 if bet.is_player else 0
                    )
                )
                cursor.execute(
                    """
                    UPDATE members
                    SET historical_score = historical_score + ?
                    WHERE id = ?
                    """,
                    (bet.profit_loss, bet.member_id)
                )

            # 4. 更新对应锦标赛的 banker_profit
            cursor.execute(
                """
                UPDATE tournaments
                SET banker_profit = banker_profit + ?
                WHERE id = ?
                """,
                (round_data.banker_round_profit, round_data.tournament_id)
            )

    def get_match_history(self, tournament_id: int | None = None) -> list[MatchHistory]:
        """
        获取对战历史。若指定锦标赛 ID，则获取该锦标赛的所有历史轮次，否则获取全部。
        """
        with self.db_manager.connection() as conn:
            cursor = conn.cursor()
            if tournament_id is not None:
                cursor.execute(
                    """
                    SELECT id, tournament_id, round_number, red_score, green_score, winner, banker_round_profit, red_players, green_players, bet_details, archived_at
                    FROM match_history
                    WHERE tournament_id = ?
                    ORDER BY round_number ASC
                    """,
                    (tournament_id,)
                )
            else:
                cursor.execute(
                    """
                    SELECT id, tournament_id, round_number, red_score, green_score, winner, banker_round_profit, red_players, green_players, bet_details, archived_at
                    FROM match_history
                    ORDER BY tournament_id ASC, round_number ASC
                    """
                )
            rows = cursor.fetchall()
            return [
                MatchHistory(
                    id=row.id,
                    tournament_id=row.tournament_id,
                    round_number=row.round_number,
                    red_score=row.red_score,
                    green_score=row.green_score,
                    winner=TeamColor(row.winner),
                    banker_round_profit=row.banker_round_profit,
                    red_players=row.red_players,
                    green_players=row.green_players,
                    bet_details=row.bet_details,
                    archived_at=row.archived_at
                )
                for row in rows
            ]

    # SQL 执行计划预期 (EXPLAIN QUERY PLAN):
    # 1. SEARCH r USING INDEX idx_rounds_tournament_id (tournament_id=?) - 使用索引过滤特定锦标赛的轮次
    # 2. SEARCH b USING INDEX idx_bets_round_id (round_id=?) - 使用索引关联投注信息
    # 3. SEARCH m USING INTEGER PRIMARY KEY (rowid=?) - 使用主键关联成员信息
    # 4. USE TEMP B-TREE FOR GROUP BY - 使用临时 B 树进行分组
    # 5. USE TEMP B-TREE FOR ORDER BY - 使用临时 B 树进行排序以输出排行榜
    def get_tournament_leaderboard(self, tournament_id: int) -> list[dict[str, Any]]:
        """
        获取指定锦标赛的积分排行榜
        依据锦标赛总收益（该锦标赛所有投注的 profit_loss 之和）进行降序排序，总收益相同则按历史积分降序、姓名升序排序
        """
        with self.db_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 
                    m.id AS member_id,
                    m.name,
                    m.historical_score,
                    COALESCE(SUM(b.profit_loss), 0) AS tournament_profit
                FROM members m
                JOIN bets b ON m.id = b.member_id
                JOIN rounds r ON b.round_id = r.id
                WHERE r.tournament_id = ?
                GROUP BY m.id, m.name, m.historical_score
                ORDER BY tournament_profit DESC, m.historical_score DESC, m.name ASC
                """,
                (tournament_id,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def add_game_account(self, nickname: str) -> GameAccount:
        """
        添加一名新的参赛选手游戏账号
        如果昵称已存在，则抛出 ValueError
        """
        with self.db_manager.connection(write=True) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO game_accounts (nickname) VALUES (?)",
                    (nickname,)
                )
                account_id = cursor.lastrowid
            except sqlite3.IntegrityError as e:
                raise ValueError(f"游戏账号 '{nickname}' 已存在") from e

            cursor.execute("SELECT id, nickname, created_at FROM game_accounts WHERE id = ?", (account_id,))
            row = cursor.fetchone()
            return GameAccount(
                id=row.id,
                nickname=row.nickname,
                created_at=row.created_at
            )

    def get_all_game_accounts(self) -> list[GameAccount]:
        """
        获取所有游戏账号
        """
        with self.db_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nickname, created_at FROM game_accounts ORDER BY nickname ASC")
            rows = cursor.fetchall()
            return [
                GameAccount(
                    id=row.id,
                    nickname=row.nickname,
                    created_at=row.created_at
                )
                for row in rows
            ]

