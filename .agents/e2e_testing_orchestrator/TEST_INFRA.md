# E2E Test Infra: BnB Family Match Score Betting System

## Test Philosophy
- **Opaque-box, requirement-driven**: All E2E tests interact with the application through its GUI interface or public CLI boundaries, without dependency on specific internal code paths, modules, or design patterns.
- **Methodology**: We apply Category-Partition (for equivalence classes), Boundary Value Analysis (BVA), Pairwise Combinatorial Testing (for cross-feature interactions), and Real-World Workload Testing (for complete tournaments).

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 (Coverage) | Tier 2 (Boundary) | Tier 3 (Cross-Feature) | Tier 4 (Scenario) |
|---|---|---|:---:|:---:|:---:|:---:|
| 1 | Tournament Lifecycle Management | ORIGINAL_REQUEST R1 | 5 | 5 | Yes | Yes |
| 2 | Drag & Drop Team/Bet Binding Flow | ORIGINAL_REQUEST R2 | 5 | 5 | Yes | Yes |
| 3 | Bet Validation & Score Settlement | ORIGINAL_REQUEST R3 | 5 | 5 | Yes | Yes |
| 4 | UI/UX Layout, Ladder & Export | ORIGINAL_REQUEST R4 | 5 | 5 | Yes | Yes |

## Test Architecture
- **Test Runner**: We use `pytest` along with `pytest-qt` to run tests.
- **PyQt6 GUI Test Integration**: The tests launch the application UI programmatically, use `qtbot` for simulated mouse clicks, double clicks, dragging, text entry, and verify UI widget state (labels, tables, lists, popups).
- **SQLite DB State Verification**: E2E tests verify database state changes and transactional integrity directly on the SQLite database, confirming score conservation.
- **Excel Export Verification**: Tests invoke the export button and verify that the output `.xlsx` file is valid and contains correct historical match data using `openpyxl`.
- **Directory Layout**:
  - `tests/` at the project root:
    - `tests/conftest.py`: pytest fixtures, including application instantiation, database setup/teardown.
    - `tests/test_tier1_features.py`: Tier 1 feature coverage tests.
    - `tests/test_tier2_boundaries.py`: Tier 2 boundary and corner cases.
    - `tests/test_tier3_combinations.py`: Tier 3 cross-feature combinations.
    - `tests/test_tier4_scenarios.py`: Tier 4 real-world application scenarios.
    - `tests/test_helper.py`: Helper functions for GUI automation and db assertions.

## Coverage Thresholds
- **Tier 1 (Feature Coverage)**: >= 20 test cases (5 per feature).
- **Tier 2 (Boundary & Corner Cases)**: >= 20 test cases (5 per feature).
- **Tier 3 (Cross-Feature Combinations)**: >= 4 test cases covering major interactions.
- **Tier 4 (Real-World Application Scenarios)**: >= 5 scenarios.
- **Total Minimum**: 49 test cases.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Standard Tournament with 3 Rounds | F1, F2, F3, F4 | Medium |
| 2 | High Bet Limits and Extreme Scores | F1, F3, F4 | Medium |
| 3 | Large Member Pool and Alternating Teams | F2, F3, F4 | High |
| 4 | Empty/New DB to End-to-End Tournament | F1, F2, F3, F4 | High |
| 5 | Excel Export Validation on Closed Tournament | F1, F4 | Medium |
