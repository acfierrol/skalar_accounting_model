# Phase 2 — Cohorts & collections engine

**Objective.** From `payments`, build the cost-disciplined `collections(company_id, cohort_month,
period_month)` matrix and cohort assignment.

**Inputs / context.** `00_foundation` §7; `docs/datasets/skalar/tables/payments.md` (160.8M rows,
signed `usd_amount`, 20.5% zero rows, 0.21% null, refunds, **404 backdated SK014 cohorts**); KB §2
(Collections = Success − Refunds) and cohort-assignment integrity rule.

**Build.**
- `sql/collections.sql.jinja`: `GROUP BY (company_id, cohort_month, payment_month)`
  `SUM(usd_amount)`, applying the documented Collections rule; **filter by `company_id` and date range**
  (params); never `SELECT *`. Decide and **document** zero/null handling.
- Cohort assignment: `cohort_month` = customer's first-payment month; **exclude** backdated /
  pre-closing customers (`first_period < 0`) per KB; assert one-cohort-per-customer.
- Typed builder returning `CollectionsCell`s / a typed matrix; **local parquet cache** keyed by
  `(company_id, params)` for cost-free dev/test re-runs.
- `estimate_bytes()` guard before running; expose scanned-bytes in result metadata.

**Public API.** `build_collections(company_id, date_range) -> CollectionsMatrix`;
`cohort_index(company_id)`.

**Acceptance & tests.** Against a cached SK011 extract, per-company totals reconcile to the figures in
`payments.md`; refund/zero/null handling unit-tested; backdated SK014 cohorts excluded; cost guard trips
above cap. Live-BQ test marked. `mypy`/`ruff`/tests green.

**Constraints.** Aggregation pushed to SQL; `payments` never scanned without filters; deterministic
ordering; `Decimal` money.

**Out of scope.** Margin/sharing/caps (Phase 3); dating/accounting.
