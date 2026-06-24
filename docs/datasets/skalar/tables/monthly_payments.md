# `monthly_payments`

**Grain.** One row per `(company_id, cohort_month, payment_month)`. 9,629 rows.

**Role in the pipeline.** Pre-aggregated `collections(d, k, i)` — the same quantity the
Phase-2 builder computes from `payments`, already grouped by cohort × payment month.
**Used as the Phase-2 reconciliation oracle, not the source of truth** (it has no
`customer_id`, so it cannot reproduce cohort assignment or the backdated/pre-closing
exclusion). The builder aggregates `payments` and asserts agreement with this table.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `amount` | FLOAT | no | Collections for the cell = `SUM(usd_amount)` over that (cohort, payment_month). |
| `cohort_month` | DATE | no | Cohort birth month (1st of month). |
| `payment_month` | DATE | no | Month collections were received (1st of month). |
| `company_id` | STRING | no | Deal id. |

**Coverage (per company, from live profiling).** 13 companies present:

| company | cells | cohorts | first cohort | last payment | total amount |
|---|---:|---:|---|---|---:|
| SK001 | 253 | 22 | 2024-01 | 2025-10 | 32,272,073 |
| SK002 | 558 | 36 | 2022-12 | 2025-11 | 14,571,208 |
| SK003 | 526 | 36 | 2015-01 | 2026-06 | 18,583,496 |
| SK004 | 1667 | 58 | 2021-03 | 2025-12 | 26,402,134 |
| SK009 | 300 | 24 | 2024-01 | 2025-12 | 45,054,280 |
| SK011 | 666 | 36 | 2023-07 | 2026-06 | 6,828,157 |
| SK012 | 503 | 31 | 2023-02 | 2026-01 | 15,310,350 |
| SK013 | 630 | 35 | 2023-05 | 2026-03 | 95,584,151 |
| SK014 | 1227 | 77 | 2012-06 | 2026-03 | 15,648,694 |
| SK015 | 1325 | 51 | 2022-01 | 2026-03 | 12,651,682 |
| SK018 | 332 | 26 | 2024-04 | 2026-05 | 10,883,942 |
| SK021 | 696 | 38 | 2023-04 | 2026-05 | 28,165,977 |
| SK022 | 946 | 43 | 2022-12 | 2026-06 | 5,309,754 |

SK014's cohorts reach back to **2012-06** — far before any plausible deal closing; these
are the backdated cohorts the Phase-2 integrity check must surface (cohort assignment that
predates closing → `first_period < 0`).
