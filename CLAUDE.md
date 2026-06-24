# CLAUDE.md — Skalar Capital Mechanics & Accounting Model

Persistent context for any agent/developer working in this repo. Read this first, then
`prompts/00_foundation_and_architecture.md`, then the current phase prompt.

## Mission

One monorepo, two deliverables with a strict one-way dependency:

1. **Capital-mechanics engine** — read Skalar's BigQuery operational data and construct the
   operational concepts of the cash model: cohorts, attribution, collections, reference
   income, sharing, return caps (MOIC / payback), threshold tests & breaches, compliance
   with per-deal spend/commitment caps, wind-down, and the per-vintage **cash events**
   (signed, dated inflows/outflows).
2. **Accounting model** — consume those cash events and produce Skalar's **cash-basis**
   accounting report (the `docs/Accounting Model.xlsx` equivalent) via the
   **effective-interest (EIR / amortized-cost) method**: per-vintage *debt given* (downstream)
   and *debt taken* (upstream) books, consolidation, and a summary (Revenue, Cost of Capital,
   outstanding principal, period cash impact).

The engine is the source of truth for *what happened*; accounting is the source of truth for
*how it is booked*. **Accounting imports the engine; the engine never imports accounting.**

## Domain references (authoritative — read before coding)

- Methodology: `capital_mechanics_documentation/skalar_cash_model_kb.md` (engineering KB) and
  `skalar_cash_events_vintages.(tex|pdf)` (Capital Mechanics spec, v4.0). Every term,
  parameter, formula, and invariant is defined there.
- Concrete cases / fixtures: `capital_mechanics_documentation/scenarios_sandbox.md`
  (Scenario A & B parameter sets + the June-2026 worked vintage with expected numbers).
- BigQuery data: `docs/datasets/skalar/` (schema, grains, coverage, data-quality flags) and
  `docs/access.md` (read-only access).
- Accounting target: `docs/Accounting Model.xlsx` — the workbook this software reproduces and
  replaces. Study it; it is the acceptance oracle.

## Data sources (BigQuery `skalar-data.Skalar`, location US, READ-ONLY)

| Table | Grain | Notes |
|---|---|---|
| `company` | one row / deal | `company_id` (SK0NN) → name. 22 rows, 13 active. |
| `payments` | one row / payment | **~13.5 GB / 160.8M rows** — Collections source. `usd_amount` (signed), `customer_id`, `payment_date`, `cohort_month`, `company_id`. |
| `spend` | (company, cohort_month) | `actual_spend`; `estimated_*` + GC/Skalar split populated **only for SK011/Kindroid**. |
| `origination_collection_percent` | (company, cohort_month) | funding% / sharing% / `delay_months`. **1 row** (Kindroid). |
| `investment_ledger`, `payment_ledger`, `monthly_payments` | — | **undocumented** — profile in Phase 0/1 (likely the transacted-ledger source). |

SK011 (Kindroid) is the only fully-parameterized live deal today and the end-to-end golden case.

## Stack & tooling

- **Python 3.13**, **uv** workspace (locked). `mypy --strict`, `ruff` (lint+format),
  `pytest` (+ coverage). One CI for the whole workspace.
- Domain types: **Pydantic v2** (frozen models); **`decimal.Decimal`** for money;
  `datetime.date` for dates. Round only at presentation.
- Data: `google-cloud-bigquery`; SQL is **parameterized + Jinja-templated**, behind a
  **read-only guard** (SELECT/WITH only); `estimate_bytes()` dry-run before heavy reads.
- **Auth — keyless (ADC).** Workload identity is the service account
  `accounting-model-sa@skalar-data.iam.gserviceaccount.com`, read-only (`roles/bigquery.jobUser`
  + dataset `roles/bigquery.dataViewer`). On GCP, **attach** the SA to the runtime (ADC resolves
  it, no config); locally, ADC with `--impersonate-service-account` (the human principal holds
  `roles/iam.serviceAccountTokenCreator` on the SA). **No JSON key files.** Quota project `skalar-data`.
- Excel: **openpyxl**, **values-only** output (no Excel-formula dependency — the EIR logic
  lives in typed Python).
- Minimal dependencies; pure functions where possible.

## Engineering principles (non-negotiable)

- SOLID, DRY, single-purpose functions, small modules, explicit package boundaries.
- Fully typed; `mypy --strict` clean; no `Any` at boundaries; validate at IO edges.
- **Parametrized, not hard-coded.** Deal parameters (funding/sharing bands, per-cohort margin,
  pricing strategy, EIR rates, settlement windows `L_op/L_c/L_s/λ/δ`, per-period & commitment
  caps, threshold mechanic, wind-down) are *data*, resolved per cohort. New deal = new params;
  new strategy = new class implementing a `Protocol` (mirror the KB's "parametrized engine with
  default strategies"). No company names, dates, or magic numbers in code — they are inputs.
- **BigQuery cost discipline.** Never `SELECT *` on `payments`; aggregate and filter by
  `company_id`/date in SQL; dry-run `estimate_bytes()` first; push work down to BQ.
- Determinism & auditability: every formula has a unit test; intermediate results are
  inspectable typed objects, not opaque dataframes.

## Definition of done (whole system)

From BigQuery inputs for SK011, the pipeline reproduces the current `Accounting Model.xlsx`
numbers — June + July 2026 loans, both books, consolidation, and summary — within tolerance.
This **golden reconciliation test** is the acceptance oracle. Per package: `mypy --strict`
clean, `ruff` clean, tests green.

## Commands

```bash
uv sync --all-groups
uv run pytest
uv run mypy
uv run ruff check
gcloud auth application-default login   # read-only ADC; project skalar-data, dataset Skalar (case-sensitive)
```
