# Phase 4 — Cash events, debt-taken derivation, netting

**Objective.** Assemble per-vintage **downstream** cash events (inflows/outflows/dates), **derive**
debt-taken (upstream) via the leverage structure + GC dates + remittance cap, and build netting
instructions. This is where the engine produces its final output: the three series the accounting
layer consumes.

**Inputs / context.** `00_foundation` §1 (pipeline), §6 (cash events, leverage, netting); KB §5
(settlement timing, netting principle), §11 (leverage structure, remittance cap, greater-of accrual);
the workbook's `Structure` sheet (ledger → consolidation → debt-taken from GC dates → netting to-do)
and its formulas: debt-taken inflow `= −downstream_outflow × 0.95`; debt-taken outflow
`= MAX(−downstream_inflow × 0.95, −outstanding + interest)`.

**Build.**
- **Downstream cash events** from Phase 1–3 outputs: `FUND_DOWN` outflows (sized `funding_pct × spend`,
  dated at the IR/disbursement date), `SHARE_UP` inflows (the capped sharing schedule, dated by the
  settlement calendar `delay_months` / `δ`), `ADJUST` events (under/over-spend, settled standalone).
  Sign convention engine-wide: inflow to Skalar `> 0`, outflow `< 0`.
- **Transacted ledger** model matching the `Structure` sheet: `amount` (signed), `loan_cohort`,
  `counterparty`, `date`, `type ∈ {Investment Request, Under/Over, Payment Due}`.
- **Debt-taken derivation**: inflow `= leverage × downstream funding`; remittance outflow
  `= leverage × downstream sharing`, **capped** at `−outstanding + interest`; dated by **GC transaction
  dates** (an explicit input model `GCDates`, not derived). `leverage` is a parameter (default 0.95).
- **Netting builder** (`def:netprinciple`): per counterparty, per date, sum signed events → one
  `NettingInstruction`. Aggregate only events that **actually share a date** (the workbook's per-period
  nets are the ideal matched case).

**Public API.** `build_downstream_cash_events(...) -> list[CashEvent]`;
`derive_debt_taken(events, gc_dates, leverage) -> list[CashEvent]`;
`build_netting(events) -> list[NettingInstruction]`.

**Acceptance & tests.** Downstream events reproduce the workbook's June/July Kindroid outflow + inflow
series; debt-taken inflows `= 0.95 × downstream` and the remittance cap matches the workbook `MAX`;
netting collapses same-date events correctly. `mypy`/`ruff`/tests green.

**Constraints.** The engine stops at cash events (no EIR here); signs consistent; leverage and GC dates
are parameters/inputs, never hard-coded.

**Out of scope.** EIR, accounting, Excel.
