# Scope: Milestone 2 — Betting & Team Binding Logic Engine

## Architecture
- Logic engine Layer (`src/engine/betting_engine.py`) containing the core business rules.
- Validations for betting: multiple of 5, <= max limit.
- 1:1 Exact Settlement Score Conservation Algorithm.
- Match results validator (best-of-seven, first to 4 wins).
- Team binding rules (a player can only bind to their own team, no duplicate member in Red and Green team).

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| 1 | Betting Engine Core | Implement `src/engine/betting_engine.py` with validation and settlement logic | None | PLANNED |
| 2 | Code Alignment and Documentation | Add unit tests/documentation for the logic engine without executing them | M1 | PLANNED |
