# `origination_collection_percent`

**Grain.** One row per `(company_id, cohort_month)`. 1 row at profiling time (SK011,
2026-06).

**Role in the pipeline.** Per-cohort election of the funding and sharing rates and the
settlement lag — the primary source the Phase-1 resolver reads to build `DealParameters`.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `company_id` | STRING | yes | Deal id. |
| `cohort_month` | DATE | yes | Cohort / S&M period (1st of month). |
| `origination_spend_percent` | INTEGER | yes | **Funding %** `f` as an integer percent (e.g. `80` → 0.80). |
| `origination_collection_percent` | INTEGER | yes | **Sharing %** `s` as an integer percent (e.g. `80` → 0.80). |
| `delay_months` | INTEGER | yes | Income-due settlement lag in months (the basis for `λ`). |

**Ambiguity (encoded in the resolver).** Despite the table name, the two percent columns
are the funding (`origination_spend_percent`) and sharing (`origination_collection_percent`)
elections, independent of each other (KB §3.2). Both are **integer percents** divided by
100 to produce a `Pct`. `delay_months` is the income-due lag; for SK011 = 2 ⇒ `λ = 2`,
`δ = 3` (Net-60, matching Scenario A).

**Live golden row (SK011, 2026-06):** funding 80, sharing 80, `delay_months` 2.
