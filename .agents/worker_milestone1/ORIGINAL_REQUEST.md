## 2026-07-13T08:18:16Z

Objective:
Implement database models, SQLite schema setup, connection management, repository transactional APIs, and unit tests for Milestone 1.

Key Constraints:
- DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
- Keep all code comments and documentation in Simplified Chinese (简体中文).
- Modify/add code only in the business package (e.g., src/database/).
- Follow the author and versioning annotation rules: include @author hyq and @version 2026-07-13 in all files.
- Use modern Python 3.11 features where appropriate (StrEnum, frozen dataclasses, etc.).
- Transactions must be used for database operations to ensure atomicity.
- Implement the exact files as required:
  - src/database/db_manager.py
  - src/database/models.py
  - src/database/repository.py
  - tests/database/test_repository.py

Technical Specifications:
1. Database Schema DDL:
   - members: id (INTEGER PRIMARY KEY AUTOINCREMENT), name (TEXT UNIQUE NOT NULL), historical_score (INTEGER NOT NULL DEFAULT 1000), created_at (TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)
   - tournaments: id (INTEGER PRIMARY KEY AUTOINCREMENT), status (TEXT CHECK(status IN ('ONGOING', 'ENDED')) NOT NULL DEFAULT 'ONGOING'), banker_profit (INTEGER NOT NULL DEFAULT 0), start_time (TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP), end_time (TIMESTAMP)
   - rounds: id (INTEGER PRIMARY KEY AUTOINCREMENT), tournament_id (INTEGER NOT NULL), round_number (INTEGER NOT NULL), red_score (INTEGER NOT NULL), green_score (INTEGER NOT NULL), winner (TEXT CHECK(winner IN ('RED', 'GREEN')) NOT NULL), banker_round_profit (INTEGER NOT NULL), created_at (TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP), FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE, UNIQUE (tournament_id, round_number)
   - bets: id (INTEGER PRIMARY KEY AUTOINCREMENT), round_id (INTEGER NOT NULL), member_id (INTEGER NOT NULL), bet_amount (INTEGER NOT NULL CHECK(bet_amount >= 0)), prediction (TEXT CHECK(prediction IN ('RED', 'GREEN')) NOT NULL), profit_loss (INTEGER NOT NULL), is_player (INTEGER CHECK(is_player IN (0, 1)) NOT NULL DEFAULT 0), FOREIGN KEY (round_id) REFERENCES rounds(id) ON DELETE CASCADE, FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE, UNIQUE (round_id, member_id)
   - match_history: id (INTEGER PRIMARY KEY AUTOINCREMENT), tournament_id (INTEGER NOT NULL), round_number (INTEGER NOT NULL), red_score (INTEGER NOT NULL), green_score (INTEGER NOT NULL), winner (TEXT CHECK(winner IN ('RED', 'GREEN')) NOT NULL), banker_round_profit (INTEGER NOT NULL), archived_at (TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP), FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE, UNIQUE (tournament_id, round_number)

2. SQLite connection management in db_manager.py:
   - Connection context manager.
   - Enforce PRAGMA foreign_keys = ON;
   - Row Factory mapping columns to dict-like attributes.

3. Models in models.py:
   - Frozen dataclasses for Member, Tournament, Round, Bet, MatchHistory.
   - StrEnum for TournamentStatus and TeamColor.

4. Repository in repository.py:
   - Methods: initialize_db(), add_member(), get_all_members(), start_tournament(), end_tournament(), save_round_settlement(), get_match_history(), get_tournament_leaderboard().
   - Raise ValueError if starting a tournament while one is already ONGOING.
   - Raise ValueError if ending a non-existent or already ENDED tournament.
   - save_round_settlement must perform all inserts/updates in a single transaction (rounds, bets, members, tournaments updates).

5. Verification:
   - Write pytest unit tests in tests/database/test_repository.py.
   - Run tests via pytest (use `run_command` in workspace).
   - Document the test execution command and result in your handoff report (handoff.md).

Please complete the task, write your handoff report to d:\workspace\bnb_guessing\.agents\worker_milestone1\handoff.md, and send a message when done.
