## 2026-07-13T08:23:09Z
You are Milestone 1 Worker Gen 2. Your working directory is d:\workspace\bnb_guessing\.agents\worker_milestone1_gen2.

Objective:
Refactor and fix the database models, connection management, repository, and tests for Milestone 1 based on Reviewer feedback.

Key Constraints:
- YOU MUST NOT run any tests (pytest, python, etc.) or execution commands. Your role is restricted to ONLY writing complete, working source code files. The user will run all tests manually.
- DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
- Keep all code comments and documentation in Simplified Chinese (简体中文).
- Modify/add code only in the business package (e.g., src/database/) and the unit tests you wrote in tests/database/test_repository.py.
- Follow the author and versioning annotation rules: include @author hyq and @version 2026-07-13 in all files.
- Use modern Python 3.11 features where appropriate.
- Transactions must be used for database operations to ensure atomicity.

Issues to Fix:
1. Schema & Case Mismatch:
   - Change enums/constants in models.py and check constraints in repository.py to use lowercase status values ('ongoing', 'ended') and title case colors ('Red', 'Green').
   - Change the default historical_score of members to 0 in both models.py (Member.historical_score: int = 0) and repository.py (table members historical_score INTEGER DEFAULT 0).
2. Row Factory Key Pollution Bug:
   - In db_manager.py, fix the dict_like_row_factory. Bypassing key assignment for private properties starting with '_'. Use object.__setattr__(self, '_keys', keys) and object.__setattr__(self, '_values', values). In __setattr__, if the name starts with '_', route to super().__setattr__(name, value), otherwise route to self[name] = value.
3. Connection Initialization Leak:
   - In db_manager.py, move the PRAGMA execution and row_factory configuration inside the try block of the connection context manager so that connections are always closed even if initialization fails.
4. Concurrency write-lock BEGIN IMMEDIATE:
   - Modify the connection context manager in db_manager.py to accept a `write: bool = False` argument. If write is True, execute conn.execute("BEGIN IMMEDIATE") and set conn.isolation_level = None to handle transactions manually.
   - Update repository.py methods that perform writes (initialize_db, add_member, start_tournament, end_tournament, save_round_settlement) to request write=True connection context: self.db_manager.connection(write=True).
5. SQL Query Plan Comment:
   - Add an EXPLAIN QUERY PLAN comment above the get_tournament_leaderboard method in repository.py.
6. Unit Tests Update:
   - Update tests/database/test_repository.py to match the new schema and default score of 0. Ensure no tests try to run commands.

Apply the changes to the source files, write a handoff report summarizing the modifications in d:\workspace\bnb_guessing\.agents\worker_milestone1_gen2\handoff.md, and notify me when complete.
