# `spend`

**Grain.** One row per `(company_id, cohort_month)`. 477 rows.

**Role in the pipeline.** Expected and actual S&M spend per cohort, with the GC/Skalar
split. Drives the threshold-test **denominator** (KB §3.3 basis = origin-period **actual
total** S&M spend, `actual_spend` — never the funded amount) and the funding/adjustment
sizing in Phase 1/3/4.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `estimated_spend` | FLOAT | yes | Expected S&M spend (from the IR). |
| `actual_spend` | FLOAT | yes | Actual total S&M spend (threshold denominator). |
| `estimated_skalar_spend` | FLOAT | yes | Estimated Skalar-funded portion. |
| `estimated_gc_spend` | FLOAT | yes | Estimated GC-funded portion. |
| `actual_gc_spend` | FLOAT | yes | Actual GC-funded portion. |
| `actual_skalar_spend` | FLOAT | yes | Actual Skalar-funded portion. |
| `cohort_month` | DATE | yes | Cohort / S&M period (1st of month). |
| `company_id` | STRING | yes | Deal id. |

**Notes.** The GC/Skalar split columns are populated only where the leverage split is
tracked (notably SK011/Kindroid). `actual_spend` is the threshold-test denominator;
`estimated_spend` is the fallback while actuals are unavailable (KB §3.3). For SK011 the
June-2026 expected = actual = $200,000.
