# Original User Request

## 2026-07-13T08:14:37Z

Build a desktop application called BnB Family Match Score Betting System using Python 3.11, PyQt6, and SQLite. It is a standalone local green app where the SQLite database file is auto-generated in the same directory as the executable. No server deployment needed. The target user is the host (banker) of a BnB game family, managing bets, settlements, and score tracking for internal family matches.

Working directory: d:\workspace\bnb_guessing
Integrity mode: development

Requirements:

R1. Tournament Lifecycle Management
The system introduces a Tournament concept. A tournament contains multiple rounds of matches.
- The database maintains each player's cumulative historical total score.
- When clicking Start New Tournament, a new tournament ID is created. All players start with 0 profit/loss for this tournament.
- After each round settlement, player gains/losses are recorded in both their cumulative historical total score and the current tournament profit/loss.
- The banker (host) has an independent account but only records the current tournament profit/loss (no historical accumulation, does not affect anyone's score account). Each new tournament resets banker profit/loss to 0.
- When clicking End Tournament:
  - A popup shows the tournament summary: banker's total net profit/loss, and a leaderboard ranking of bettors who earned the most and lost the most.
  - All rounds in this tournament are archived to the match history with a tournament label.

R2. Drag-and-Drop Team Assignment with Blind Bet to Binding Flow
Matches are two-team battles (Red Team vs Green Team), best-of-seven (first to 4 wins). Members are divided into round players and bettors (players can also be bettors). Interaction flow:
1. Pre-match Blind Betting Phase: All family members are in the left member pool. The host double-clicks a member name to input bet amount (all bettors are in betting-person status, players who bet are blind-betting on themselves, red/green color undetermined).
2. First Game Binding: The host drags players from the pool into the Red Player List or Green Player List. The system intelligently detects if the player has blind bet amounts and auto-binds them to the corresponding team's bet flow (strict validation: player can only bind to their own team).
3. Regular Bettor Binding: The host drags non-playing bettors from the pool into Red or Green bettor lists.
4. No Bet = Spectator: Anyone without a bet amount gets no score change regardless of outcome.

R3. Bet Limit Validation and 1:1 Exact Settlement Algorithm (Score Conservation)
- The UI provides a Max Bet per round input (default 20).
- All bet amounts must be less than or equal to the limit AND be a multiple of 5 (5, 10, 15, 20). Non-compliant inputs are rejected with an error popup.
- Settlement rules (pure bet-driven): If a player bets X points (X > 0):
  - Correct guess: personal total score +X (1:1 bet, principal returned plus net gain X)
  - Wrong guess: personal total score -X
  - Banker's round net profit/loss = sum of all wrong-guess bets - sum of all correct-guess bets
- Use database transactions to ensure atomicity of score settlement, preventing score conservation violations.

R4. Modern UI/UX Interface Layout
Interface is split into layers:
- Top half (fixed pinned area): Shows the current ongoing match.
  - Left: Family member pool (showing name and current total score)
  - Center columns: Red Team / Green Team camps, each camp clearly subdivided with headers for Players and Bettors
  - Right: Round score input and limit console, Start New Tournament and End Tournament buttons
- Bottom half (archive display area):
  - Left: Historical match table (Tournament ID, Round ID, Red/Green scores, Winner, Banker round profit/loss)
  - Right: Family ladder live scoreboard (toggle between: Historical Cumulative Leaderboard and Current Tournament Profit/Loss Leaderboard)
- Clicking One-Click Auto Settlement auto-completes calculations, updates database, clears the top area and archives to history below.
- Supports One-Click Export to local Excel (.xlsx) functionality.
- UI language is Simplified Chinese.

R5. Packagable Distribution and Modern Python 3.11 Code Quality
- Code should leverage Python 3.11 features (modern type hints, StrEnum, ExceptionGroup, etc.) for code quality and robustness.
- Provide complete packaging instructions (PyInstaller or similar) so end users can run via a single exe file.
- SQLite database file is auto-generated in the exe's directory, no user configuration needed.
- Provide requirements.txt with all dependencies (including openpyxl for Excel export).

Acceptance Criteria:

Functional Completeness:
- [ ] App starts and correctly creates/reads SQLite database, first launch auto-initializes table schema
- [ ] Can add/manage family members, each with name and cumulative historical total score
- [ ] Start New Tournament button works correctly, tournament profit/loss starts from 0
- [ ] Double-clicking pool member opens bet amount input, with strict validation (max limit, multiple of 5)
- [ ] Dragging members to Red/Green camps auto-detects and binds blind bet amounts
- [ ] Score input and best-of-seven (first to 4) determination logic is correct
- [ ] Post-settlement score conservation: all correct guessers +X, wrong guessers -X, banker profit/loss = total loser X - total winner X
- [ ] End Tournament shows summary popup with banker profit/loss and leaderboard
- [ ] After tournament ends, rounds archive to history table with tournament label
- [ ] Ladder board supports toggle between Historical Cumulative and Current Tournament views
- [ ] Excel (.xlsx) export works correctly

Interaction Experience:
- [ ] Drag-and-drop is smooth, supports dragging from pool to Red/Green camps
- [ ] UI is aesthetically pleasing, modern, with clear layout
- [ ] Invalid inputs trigger clear error popups

Technical Quality:
- [ ] Code uses Python 3.11 features (type hints, StrEnum, etc.)
- [ ] Database operations use transactions for atomicity
- [ ] Provides working PyInstaller packaging command
- [ ] Provides requirements.txt file

## 2026-07-13T08:22:10Z

IMPORTANT USER DIRECTIVE:
DO NOT automatically run any tests, do not execute `python`, `pytest`, or any test/launch commands. The user will handle all testing and launching manually.

Your job is ONLY to write complete, working source code files. Once all code files are written, provide the PyInstaller packaging command and requirements.txt — that's it. No test execution.

## 2026-07-13T08:23:57Z

🚨 URGENT — STOP ALL EXECUTION IMMEDIATELY 🚨
ABSOLUTE BAN on the following commands in ALL sub-agents:
- NO `python` commands of any kind
- NO `pytest` commands
- NO `pyinstaller` commands  
- NO launching any .py files
- NO running the application

The ONLY terminal commands allowed are: `mkdir`, file creation/editing, and `pip` if needed to check dependencies.
ALL AGENTS MUST ONLY WRITE CODE FILES. NOTHING ELSE.
Any agent that runs python or pytest after this message should be terminated.

## 2026-07-13T08:29:56Z

NEW USER REQUIREMENT — Pre-populated Family Members

The database must be pre-populated with the following 34 family members on first launch. Include them in the database initialization code:

棉花, P5, 斌, 滋味, F, 冰, 雀占, 小黑, 仁俊, 大宝, 爱恋, 恋, 蟋蟀, 君王, 月子, 老王, 螺丝, 千序, 兰兰, 燕子, 咬字, 欢, 娜娜, 托尼, 敏宝, 通, 飓风, 爱火花, 今天, 李硕, 觅魅, 车, 主持人, 大哥

Key notes:
1. "主持人" is the host/banker — this member should be flagged as the banker role in the database.
2. All members start with an initial cumulative score (likely 0 or a configurable default).
3. The system should also support dynamically adding new members later via the UI.
4. The user mentioned that actual match players have different "match IDs" each time — they will provide common match IDs later for preset. For now, just ensure the system supports dynamic addition of members.
