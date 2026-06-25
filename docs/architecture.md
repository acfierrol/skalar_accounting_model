# Architecture

This mirrors `prompts/00_foundation_and_architecture.md` (the binding architecture).

## The pipeline

```
BigQuery (read-only)
   │  payments, spend, origination_collection_percent, company, *_ledger
   ▼
[engine] per-company / per-cohort cash events  (downstream inflows = sharing, outflows = funding)
   ▼
[engine] debt-taken (upstream) derivation       (= downstream x leverage 0.95, capped, + GC dates)
   ▼
[accounting] EIR amortization per book          (principal / interest split, outstanding, XIRR)
   ▼
[accounting] consolidation + summary            (Revenue, Cost of Capital, outstanding, cash impact)
   ▼
[accounting] Excel writer (values-only)  +  [engine] netting "payments to-do" per counterparty
```

The engine stops at **cash events** (inflows, outflows, dates per vintage). Accounting takes it
from there; the only data-driven inputs to the accounting layer are those series — the EIR method
is pure logic.

## Packages & dependency rule

| Package | Role |
|---|---|
| `skalar_data_access` | BigQuery client (read-only guard), Jinja SQL runner, cost guard, settings |
| `skalar_capital_mechanics` | engine: domain models + concept builders + cash events. Depends on data_access only |
| `skalar_accounting` | EIR, consolidation, summary, Excel writer. Depends on capital_mechanics |
| `skalar_data_docs` | dataset-doc tooling (leaf) |
| `apps/cli` | orchestration; depends on all packages |

Allowed import direction: `data_access → capital_mechanics → accounting → cli`. Never reversed —
enforced by an import-linter contract in CI.

## EIR / amortized-cost method (matched to the workbook)

Per book with effective annual rate `r` (debt given `r = 0.25`, debt taken `r = 0.16`; both are
per-book inputs). Periods are dated; `outstanding₀ = 0`. With prior balance `O` and day-count
fraction `f`, `accrued = O · ((1+r)^f − 1)` (**signed**: with `O ≤ 0` for debt given, `accrued`
is negative — so `+ accrued` below is the signed form of foundation §4's magnitude expression,
and the workbook is the oracle the code matches).

- **Debt given** (asset, `O ≤ 0`): `principal = MIN(inflow + accrued, −O)`;
  `interest = inflow − principal` (Revenue); `outstanding = O + principal + outflow`.
- **Debt taken** (liability, `O ≥ 0`): `outflow = MAX(remittance_basis, −O − accrued)` (the payoff
  cap); `principal = outflow + accrued`; `interest = outflow − principal` (Cost of Capital);
  `outstanding = O + principal + inflow`.

Day-count is per book: debt given uses **calendar days in the period's month / 365**; debt taken
uses **actual days between consecutive dates / 365**. `XIRR` is spreadsheet semantics
(Actual/365); non-converging single-signed loans return `None` (the workbook's `#NUM!`).

## Strategy seams

Encoded as `typing.Protocol`s resolved from a registry, so adding a strategy never touches call
sites: `PricingStrategy` (default payback MOIC ladder), `ThresholdMechanicStrategy` (Mechanic I
linear ladder, Mechanic II incremental), and the day-count conventions.
