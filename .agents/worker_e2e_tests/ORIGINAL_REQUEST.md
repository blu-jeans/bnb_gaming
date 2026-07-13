## 2026-07-13T08:16:28Z
You are a worker with role E2E Test Writer. Your working directory is d:\workspace\bnb_guessing\.agents\worker_e2e_tests.
Your task is to design, write, and verify the complete E2E test suite for the BnB Family Match Score Betting System.
The test files must be placed in a `tests/` directory at the project root (`d:\workspace\bnb_guessing\tests/`).
Do NOT write or modify files under `src/`.
Please read:
1. Requirements in `d:\workspace\bnb_guessing\.agents\ORIGINAL_REQUEST.md`.
2. Global project plan in `d:\workspace\bnb_guessing\.agents\orchestrator\PROJECT.md`.
3. E2E Test Infra in `d:\workspace\bnb_guessing\.agents\e2e_testing_orchestrator\TEST_INFRA.md`.

You must implement the E2E test suite using `pytest` and `pytest-qt`. Since the GUI is not yet implemented, you will define the contract for the GUI widgets in a helper or directly in the tests, using standard widget names:
- `start_new_tournament_btn`: QPushButton for starting a tournament.
- `end_tournament_btn`: QPushButton for ending a tournament.
- `member_pool_list`: QListWidget showing family members in the pool.
- `red_player_list`: QListWidget for Red Team players.
- `green_player_list`: QListWidget for Green Team players.
- `red_bettor_list`: QListWidget for Red Team bettors.
- `green_bettor_list`: QListWidget for Green Team bettors.
- `max_bet_input`: QSpinBox or QLineEdit for max bet limit.
- `score_input_red`: QSpinBox or QLineEdit for Red Team match score (e.g. number of games won, best-of-seven, first to 4).
- `score_input_green`: QSpinBox or QLineEdit for Green Team match score.
- `one_click_settlement_btn`: QPushButton to settle the round.
- `export_excel_btn`: QPushButton to export to Excel.
- `historical_match_table`: QTableWidget or QTableView for match history.
- `ladder_board_table`: QTableWidget or QTableView for ladder ranking.
- `ladder_view_toggle`: QComboBox or QPushButton to toggle between Historical Cumulative and Current Tournament leaderboards.

Create:
- `tests/conftest.py`: pytest fixtures, PyQt6 app launch helper, database test setup.
- `tests/test_helper.py`: Helper functions to interact with the UI, input bets, drag members, and assert DB state.
- `tests/test_tier1_features.py`: Feature coverage (at least 5 tests per feature, total >= 20 tests).
- `tests/test_tier2_boundaries.py`: Boundary and corner cases (at least 5 tests per feature, total >= 20 tests).
- `tests/test_tier3_combinations.py`: Cross-feature combinations (at least 4 tests).
- `tests/test_tier4_scenarios.py`: Real-world application scenarios (at least 5 tests).

MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Make sure all requirements (Simplified Chinese, multiples of 5, max bet validation, 1:1 score conservation, transaction atomicity, db file auto-generation in the executable folder, and Excel export verification) are thoroughly tested.
Write clean Python 3.11 code, following the project style and using Chinese comments.
Provide a summary of the implemented tests and how to run them in your handoff report.
