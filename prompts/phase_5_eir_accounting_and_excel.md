# Phase 5 — EIR amortization, consolidation, summary, Excel (+ golden reconciliation)

**Objective.** The `skalar_accounting` package: EIR principal/interest split per book, consolidation,
summary, a **values-only** Excel writer, and the **golden reconciliation** against
`docs/Accounting Model.xlsx`. This phase is the system's definition of done.

**Inputs / context.** `00_foundation` §4 (exact EIR spec) and §8 (testing); the workbook (Debt Given
`r = 0.25`, Debt Taken `r = 0.16`; per-book day-counts; XIRR; summary rows; Check rows). Depends on
`skalar_capital_mechanics` (consumes its `CashEvent`s).

**Build.**
- **EIR engine**: `AmortizationSchedule` from a book's cash events + rate `r` + `day_count`, per §4 —
  asset form (debt given, `outstanding < 0`) and liability form (debt taken, `outstanding > 0`);
  `accrued = O_{t-1}·((1+r)^{f} − 1)`; `principal`, `interest`, `outstanding`; reconciliation Check ≈ 0.
- **DayCount**: month-days/365 (debt given) and actual-days/365 (debt taken); both unit-tested to the
  workbook.
- **XIRR**: tested Newton + bisection fallback; per-loan and consolidated; handle the workbook's
  `#NUM!` (non-converging) cases gracefully.
- **Consolidation**: sum per-vintage schedules onto the union of dates → `ConsolidatedBook`.
- **Summary**: Revenue = Σ debt-given interest; Cost of Capital = Σ debt-taken interest; outstanding
  lended/borrowed; **Skalar Period Cash Impact** per the workbook; Check rows.
- **Excel writer** (openpyxl, **values-only**): emit Summary + Debt Given + Debt Taken + the
  Structure-style ledger + the netting to-do, matching the workbook's layout — **no Excel formulas**
  (all values computed in Python).

**Public API.** `amortize(book, rate, day_count) -> AmortizationSchedule`; `consolidate(...)`;
`build_summary(...)`; `write_workbook(path, summary, books, ledger, netting)`.

**Acceptance & tests.** **GOLDEN**: from fixture inputs for Kindroid (June + July 2026 loans), the
computed Debt Given / Debt Taken / consolidated / summary equal the cached workbook numbers within
tolerance (principal, interest, outstanding, and finite XIRRs); Check rows ≈ 0; re-read the generated
`.xlsx` and assert the written values. `mypy`/`ruff`/tests green.

**Constraints.** `Decimal` throughout; round only at presentation; EIR logic pure and fully unit-tested;
values-only output (no Excel-formula dependency).

**Out of scope.** CLI/orchestration (Phase 6).
