# Dataset: `skalar-data.Skalar`

BigQuery dataset (location **US**; dataset id is case-sensitive). Read-only — see
[`../../access.md`](../../access.md). Seven tables; sizes/grains below. The three ledgers
(`investment_ledger`, `payment_ledger`, `monthly_payments`) were undocumented at project
start and are profiled here.

| Table | Grain | Rows | Role |
|---|---|---:|---|
| [`company`](tables/company.md) | one row / deal | 22 | `company_id` (SK0NN) → name. |
| [`payments`](tables/payments.md) | one row / payment | 160.8M | Collections source (signed `usd_amount`). |
| [`monthly_payments`](tables/monthly_payments.md) | (company, cohort_month, payment_month) | 9,629 | Pre-aggregated collections; Phase-2 reconciliation oracle. |
| [`spend`](tables/spend.md) | (company, cohort_month) | 477 | Expected/actual S&M spend (+ GC/Skalar split). |
| [`origination_collection_percent`](tables/origination_collection_percent.md) | (company, cohort_month) | 1 | funding% / sharing% / `delay_months` (Kindroid). |
| [`investment_ledger`](tables/investment_ledger.md) | one row / investment event | 1 | Downstream funding / Investment Amounts (signed; GC/Skalar split). |
| [`payment_ledger`](tables/payment_ledger.md) | one row / payment-due event | 0 | Sharing remittances / payments due (typed). |

## Pipeline mapping (`Structure` sheet → tables)

- **Transacted ledger / cash events.** `investment_ledger` carries funding outflows
  (Investment Amounts, signed negative for accounting) with the `gc_amount`/`skalar_amount`
  leverage split and `is_adjustment` (Funding Adjustment) flag; its `trade_date` is the GC
  ("CVF" — Customer Value Financing) interaction date, i.e. the GC transaction date used to
  date debt-taken upstream (Phase 4). `payment_ledger` carries sharing remittances /
  payments-due (positive amounts, `type`-labelled, GC/Skalar split).
- **Collections.** `payments` (raw, per-payment, has `customer_id`) is the source of truth;
  `monthly_payments` is the pre-aggregated mirror used to reconcile the Phase-2 builder.

## Golden case

**SK011 / Kindroid** is the only fully-parameterized live deal and the end-to-end golden
case: funding 80% / sharing 80% / `delay_months` 2, cohort 2026-06, F = $160,000
(PFA = $152,000 GC + $8,000 Skalar). This is the worked vintage in
`docs/capital_mechanics_documentation/scenarios_sandbox.md` (×1000 vs its kUSD figures).
