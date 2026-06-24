# 00 — Foundation & Architecture

This is the architecture the build phases implement. It is binding: phases must not invent a
different structure. Read `CLAUDE.md` first. Terms (cohort, vintage, reference income, sharing,
cap, threshold, leverage structure, `L_op/L_c/L_s/λ/δ`) are defined in
`capital_mechanics_documentation/skalar_cash_model_kb.md` — use them exactly.

## 1. The pipeline (from the workbook's `Structure` sheet)

```
BigQuery (read-only)
   │  payments, spend, origination_collection_percent, company, *_ledger
   ▼
[engine] transacted ledger per company        (signed USD, loan-cohort, counterparty, date, type)
   ▼
[engine] per-company / per-cohort cash events  (downstream inflows = sharing, outflows = funding, dates)
   ▼
[engine] cross-cohort consolidation per company → portfolio
   ▼
[engine] debt-taken (upstream) derivation       (= downstream × leverage 0.95, capped, + GC dates)
   ▼
[accounting] EIR amortization per book          (principal / interest split, outstanding, XIRR)
   ▼
[accounting] consolidation + summary            (Revenue, Cost of Capital, outstanding, cash impact)
   ▼
[accounting] Excel writer (values-only)  +  [engine] netting "payments to-do" per company / GC
```

The engine stops at **cash events** (inflows, outflows, dates per vintage). Accounting takes it
from there. The only data-driven inputs to the accounting layer are those three series; the EIR
method is pure logic.

## 2. Packages & dependency rule

```
packages/
  skalar_data_access/        # BQ client wrapper (read-only guard), Jinja SQL runner, cost guard, Settings
  skalar_capital_mechanics/  # engine: domain models + concept builders. Depends on data_access only.
  skalar_accounting/         # EIR, consolidation, summary, Excel writer. Depends on capital_mechanics.
  skalar_data_docs/          # existing dataset-doc tooling (migrate the package in from the data repo)
apps/cli/                    # orchestration; depends on all packages
```

Allowed import direction: `data_access → capital_mechanics → accounting → cli`. Never reverse.
Enforce with an import-linter contract in CI.

## 3. Domain model (Pydantic v2, frozen; money = `Decimal`, dates = `date`)

Define in `skalar_capital_mechanics.models`. Illustrative — phases refine:

- `Company(company_id: str, name: str)`.
- `DealParameters` — resolved per cohort: `funding_band`, `sharing_band` (independent),
  `margin` (per-cohort), `pricing_strategy` (see §5), EIR rates `eir_given`, `eir_taken`,
  settlement `L_op, L_c, L_s` (→ derived `lambda_`, `delta`), `leverage` (senior advance φ,
  default 0.95), per-period cap `min(dollar_cap, growth_cap)`, `commitment_amount`,
  `threshold` (mechanic + checkpoints + delta + timing + exit), `winddown`. No defaults baked
  into code paths — defaults live in a `defaults` config object and are overridable per deal.
- `Cohort` / `Vintage` — `(company_id, cohort_month)`; vintage = upstream cohort by join month.
- `CollectionsCell(company_id, cohort_month, period_month, collections: Decimal)`.
- `ReferenceIncome` = `collections × margin`. `Sharing` = `reference_income × sharing_pct`,
  truncated at the return cap.
- `CashEvent(company_id, cohort_month, date, amount: Decimal, kind: CashEventKind, counterparty)`
  — `kind ∈ {FUND_DOWN, SHARE_UP, ADJUST, PFA, REMIT, FA_UP, WIND_DOWN}`; sign convention:
  **inflow to Skalar > 0, outflow < 0** (engine-wide, both layers — see netting §6).
- `AmortizationRow` / `AmortizationSchedule` (accounting): per period `date, cash_flow,
  accrued_interest, principal, interest, outstanding`.
- `Book` (debt-given | debt-taken) → `ConsolidatedBook` → `AccountingSummary`.
- `NettingInstruction(counterparty, date, net_amount, direction)`.

## 4. EIR / amortized-cost method — exact spec (replicate the workbook)

Per book with effective annual rate `r` (debt-given `r = 0.25`, debt-taken `r = 0.16`;
both are **per-book inputs**, not constants). Periods are dated; `outstanding₀ = 0`.

For period *t* with prior outstanding `O_{t-1}`, day-count fraction `f_t` (see day-count below),
and the period's signed cash flows:

```
accrued_interest_t = O_{t-1} · ((1 + r)^(f_t) − 1)
```

**Debt given (asset; outstanding is negative = Skalar is owed):**
- inputs: `outflow_t` (funding, ≤ 0), `inflow_t` (sharing, ≥ 0)
- `principal_t   = MIN( inflow_t − accrued_interest_t , −O_{t-1} )`   (cannot exceed balance)
- `interest_t    = inflow_t − principal_t`   (Revenue)
- `outstanding_t = O_{t-1} + principal_t + outflow_t`

**Debt taken (liability; outstanding is positive = Skalar owes):**
- inputs: `inflow_t` (GC funding, ≥ 0), `outflow_t` (remittance, ≤ 0, capped — see §6)
- `principal_t   = outflow_t + accrued_interest_t`     (accrued uses `O_{t-1} · ((1+r)^{f_t} − 1)`)
- `interest_t    = outflow_t − principal_t`   (Cost of Capital, COGS)
- `outstanding_t = O_{t-1} + principal_t + inflow_t`

**Day-count (configurable per book; match the workbook exactly):**
- debt given uses **calendar days in the period's month** (`DAY(EOMONTH)`) over 365;
- debt taken uses **actual days between consecutive dates** (`(dateₜ − dateₜ₋₁)/365`).
Expose `day_count: DayCount` on the book; provide both; unit-test each against the workbook.

`XIRR` per loan and consolidated = `XIRR(net_flows, dates)` (spreadsheet semantics:
outflows negative, inflows positive; Actual/365). Implement a tested Newton/bisection XIRR.

**Consolidation** = element-wise sum of per-vintage schedules onto the union of dates.
**Summary**: Revenue = Σ debt-given interest; Cost of Capital = Σ debt-taken interest;
Outstanding Lended/Borrowed = consolidated outstanding; Period Cash Impact per the workbook's
`SUM(revenue, COGS, outstanding) − prior outstanding`; include the reconciliation **Check** rows
(must be ~0 to floating tolerance).

## 5. Strategy seams (extensibility)

Encode as `typing.Protocol`s with a default implementation, resolved from `DealParameters`:
- `PricingStrategy.return_cap(cohort, funding) -> Decimal` — default: payback MOIC ladder
  `(b, a_b, step, M)`; alternatives (flat multiple, performance-indexed) drop in.
- `ThresholdMechanic.evaluate(...) -> ThresholdResult` — default: Mechanic I linear ladder;
  Mechanic II incremental as alternative (see KB §3.3; mind the agreement-language caution).
- `DayCount.fraction(prev, cur) -> Decimal`.
A registry maps a deal's elected strategy name → implementation. Adding a strategy must not
touch existing call sites.

## 6. Cash events, leverage & netting

- **Downstream cash events** come from BQ: funding outflows (per cohort, sized by
  `funding_pct × spend`, dated at the disbursement/IR date) and sharing inflows
  (`Σ collections × margin × sharing_pct` per period, dated by the settlement calendar
  `delay_months`/`δ`), truncated at the return cap.
- **Debt-taken (upstream)** is *derived*: inflow = `leverage × downstream funding` (default
  0.95); remittance outflow = `leverage × downstream sharing`, **capped** at outstanding+interest
  (`MAX(−share×0.95, −outstanding+interest)` in the workbook); dated by **GC transaction dates**
  (a separate input). Implement the leverage structure as a parameter (§KB leverage structure).
- **Netting principle** (KB §5.2 / Capital Mechanics `def:netprinciple`): on any date, per
  counterparty, sum signed events; the sign of the total sets direction; emit one
  `NettingInstruction`. The workbook's per-period nets are the *ideal matched case*; the netting
  builder must aggregate only events that actually share a date. This produces the Phase
  "payments to-do."

## 7. BigQuery access patterns

- **Auth (keyless).** Credentials resolve via ADC. Workload SA
  `accounting-model-sa@skalar-data.iam.gserviceaccount.com`: on GCP **attach** it to the runtime
  (no config); locally use ADC impersonation (`gcloud auth application-default login
  --impersonate-service-account=…`; principal holds `roles/iam.serviceAccountTokenCreator` on the SA).
  `Settings.impersonate_service_account: str | None` toggles in-code impersonation
  (`google.auth.impersonated_credentials`); unset = plain ADC (the attached-SA path). Quota project
  `skalar-data`. SA roles are read-only only (`roles/bigquery.jobUser` + dataset
  `roles/bigquery.dataViewer`); **never a downloaded key**. The `SELECT`/`WITH` guard remains as
  defense-in-depth on top of the IAM restriction.
- All SQL under `skalar_data_access/sql/*.sql.jinja`, parameterized (`@company_id`, `@from`, …),
  rendered + run through the read-only guard. No string interpolation of values.
- Mandatory aggregates for `payments`: build `collections(company, cohort_month, period_month)`
  with `GROUP BY` in SQL; filter by `company_id` and date; treat zero/negative/null `usd_amount`
  per the documented Collections rule (Success − Refunds); handle backdated cohorts (exclude
  `first_period < 0`) explicitly.
- `estimate_bytes()` dry-run guard with a configurable cap; fail loud above it.
- Cache cohort-collection extracts locally (parquet) for fast, cost-free re-runs in tests/dev.

## 8. Testing strategy

- **Unit**: every EIR formula, day-count, XIRR, pricing/threshold strategy — table-driven.
- **Golden**: `tests/golden/` holds the expected numbers extracted from `Accounting Model.xlsx`
  (June + July 2026 Kindroid loans, both books, consolidated, summary). A test runs the pipeline
  from fixture inputs (the scenario-sandbox values / cached BQ extracts) and asserts equality
  within tolerance. This is the definition of done.
- **Data contracts**: schema/grain assertions against BQ docs; referential-integrity checks.
- No network in unit/golden tests — use cached fixtures; mark live-BQ tests separately.

## 9. Build phases (sequenced — see `prompts/phase_*.md`)

0. Monorepo + tooling + read-only BQ access layer; profile undocumented ledgers.
1. Domain models + per-cohort deal-parameter resolution (+ defaults config).
2. Cohorts & collections engine (payments → `collections(d,k,i)`, cost-disciplined).
3. Reference income, sharing, return caps (MOIC/payback), thresholds, compliance, wind-down/breach.
4. Cash-event construction (downstream) + debt-taken derivation + netting.
5. EIR amortization + consolidation + summary + Excel writer + **golden reconciliation**.
6. CLI/orchestration + reporting + docs.

Each phase prompt states: Objective · Inputs/Context · Build · Public API · Acceptance & tests ·
Constraints · Out of scope. Do not start a phase until the prior phase's tests are green.
