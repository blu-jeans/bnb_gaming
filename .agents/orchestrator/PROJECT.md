# Project: BnB Family Match Score Betting System

## Architecture
- Standalone PyQt6 desktop application with SQLite local database.
- Layers:
  - Data Layer: SQLite database (`bnb_betting.db`), Repository for transactional CRUD.
  - Logic/Engine Layer: Match & Betting engine (limits, validation, 1:1 score conservation settlement).
  - UI Layer: PyQt6 Main Window, drag-and-drop team/bettor binding, score input, history table, leaderboard.
  - Utils Layer: Excel exporter.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| 1 | DB Schema & Core Models | DB initialization, connection manager, tables (members, tournaments, rounds, bets, match_history), transactional database operations | None | DONE |
| 2 | Betting & Team Binding Logic Engine | Blind betting flow, team binding validation, score conservation settlement algorithm, best-of-seven match outcome | M1 | IN_PROGRESS (6d9e7429-d6bf-4b6c-840f-d20575093dc3) |
| 3 | PyQt6 UI Layout & Drag-and-Drop | MainWindow split layout, drag-and-drop mechanics (from pool to Red/Green camps with blind-bet auto-bind), Chinese localization | M2 | PLANNED |
| 4 | App Integration & Features | Integrate engine & UI, One-Click Settlement, Start/End Tournament triggers + popup, ladder board toggles, Excel export | M3 | PLANNED |
| 5 | E2E Testing Validation & Packaging | Run full E2E test suite (100% pass), adversarial coverage hardening, PyInstaller packaging | M4 | PLANNED |

## Interface Contracts
### Data Layer ↔ Logic Layer
- `db_manager.get_connection()`: Returns a SQLite connection context manager.
- `repository.initialize_db()`: Initializes tables.
- `repository.start_tournament() -> int`: Creates a new tournament and returns its ID.
- `repository.end_tournament(tournament_id: int) -> dict`: Archives matches and returns summary statistics.
- `repository.save_round_settlement(tournament_id: int, round_data: dict, settlements: list) -> bool`: Transactional settlement save.

### Logic Layer ↔ UI Layer
- `betting_engine.validate_bet(amount: int, max_limit: int) -> bool`: Validates bet multiple of 5 and <= limit.
- `betting_engine.calculate_settlement(bets: list, winner: str) -> dict`: Core score conservation algorithm.

## Code Layout
- `src/main.py`: Entry point.
- `src/config.py`: Global configuration, StrEnums.
- `src/database/db_manager.py`: SQLite connection.
- `src/database/models.py`: Data classes.
- `src/database/repository.py`: CRUD operations.
- `src/engine/betting_engine.py`: Logic engine.
- `src/gui/main_window.py`: PyQt6 MainWindow.
- `src/gui/dialogs.py`: PyQt6 popups.
- `src/gui/components/`: Sub-components.
- `src/utils/excel_exporter.py`: openpyxl Excel export.
