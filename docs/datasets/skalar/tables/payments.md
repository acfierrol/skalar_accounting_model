# `payments`

**Grain.** One row per customer payment. **160,857,022 rows / 14,223,183,136 bytes
(~13.25 GiB).** No partitioning or clustering — a `company_id` filter does **not** prune;
any query scans the full referenced columns (~3–5 GB). Always aggregate in SQL, never
`SELECT *`, and rely on the parquet cache (`estimate_bytes` gates each run).

**Role in the pipeline.** Source of truth for **Collections**. The Phase-2 builder
aggregates this to `collections(company_id, cohort_month, payment_month)` and reconciles
against the pre-aggregated [`monthly_payments`](monthly_payments.md). Only this table has
`customer_id`, so cohort-assignment integrity and the backdated/pre-closing exclusion
(KB §2) can only be computed here.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `usd_amount` | FLOAT64 | yes | Signed payment amount (USD). Negative = refund/reversal. |
| `customer_id` | STRING | yes | End-customer id (cohort-assignment key). |
| `payment_date` | DATE | yes | Payment date. **No `payment_month` column** — derive `DATE_TRUNC(payment_date, MONTH)`. |
| `cohort_month` | DATE | yes | Materialised cohort birth month (verify vs recomputed first-payment month). |
| `company_id` | STRING | yes | Deal id (13 active deals present). |

## Collections rule (KB §2)

`Collections = Success − Refunds = SUM(usd_amount)` — refunds are already negative amounts,
and NULL amounts are dropped by `SUM`. Zeros contribute nothing. No separate status column
exists; the sign of `usd_amount` carries the refund semantics.

## Data-quality profile (live, full-table scan 2026-06-24)

| Metric | Value | Share |
|---|---:|---:|
| Total rows | 160,857,022 | 100% |
| Distinct active companies | 13 | — |
| NULL `usd_amount` | 333,924 | 0.21% |
| Zero `usd_amount` | 33,027,822 | 20.53% |
| Negative `usd_amount` (refunds/reversals) | 677,117 | 0.42% |
| `SUM(usd_amount)` | 327,265,896.47 | — |
| `payment_date` range | 2015-01-24 → 2026-06-24 | — |

**Handling.** NULLs are dropped by `SUM` (and excluded from collections). Zeros are kept
but contribute 0. Negatives (refunds) net against positives per the Collections rule.

## Cohort-assignment integrity & backdated cohorts (KB §2)

`cohort_month` must equal each customer's first-payment month, computed over the
**complete, unfiltered** per-customer history; only then are customers with `first_period
< 0` (acquired before deal closing) excluded. Filtering payment rows by date *before*
computing `first_period` leaks pre-deal customers in as new — so the cohort-integrity query
(`cohort_integrity.sql.jinja`) computes first-payment month without a date filter.

**SK014** carries cohorts dating back to 2012-06 (and payments back to 2015), far earlier
than any plausible closing month — the backdated cohorts the Phase-2 integrity check must
surface and exclude (the prompt notes ~404 such backdated SK014 cohorts; the exact count is
recomputed against the elected closing month, not hard-coded).
