# Phase 0 — Monorepo, tooling, read-only BigQuery access

**Objective.** Stand up the uv workspace + package skeleton with lint/type/test/CI, and a tested
**read-only** BigQuery access layer. Profile the three undocumented ledger tables and write their docs.

**Inputs / context.** `CLAUDE.md`; `00_foundation_and_architecture.md` §2 (layout, dependency rule),
§7 (BQ patterns); `docs/access.md` (read-only ADC + guard); existing `bq.py` / `scripts/bq.ps1` in the
data repo (port the guard semantics).

**Build.**
- uv **workspace** at repo root with `packages/` and `apps/` exactly per §2; each package has its own
  `pyproject.toml`, `py.typed`, `__init__`.
- Tooling: `ruff` (lint+format), `mypy --strict`, `pytest`+coverage, **import-linter** contract
  enforcing `data_access → capital_mechanics → accounting → cli` (no reverse imports), `pre-commit`,
  and one CI workflow (`uv sync`, lint, type, test).
- `skalar_data_access`:
  - `Settings` (pydantic-settings): project `skalar-data`, dataset `Skalar`, location `US`,
    `quota_project` (`skalar-data`), `max_scan_bytes` cap, and
    `impersonate_service_account: str | None` — from env.
  - **Credentials provider (keyless):** resolve via ADC; if `impersonate_service_account` is set,
    wrap ADC in `google.auth.impersonated_credentials` targeting the SA
    (`accounting-model-sa@skalar-data.iam.gserviceaccount.com`, scope `bigquery`); unset = plain ADC
    (the attached-SA path on GCP). **Never load a JSON key file.** The SA holds read-only roles only
    (`roles/bigquery.jobUser` + dataset `roles/bigquery.dataViewer`).
  - `BigQueryClient` wrapping `google-cloud-bigquery` with a **read-only guard** that refuses anything
    but `SELECT`/`WITH` (`WriteAttemptError`); `query()`, `estimate_bytes()` (dry-run), and
    `run_template(name, params)` that renders `sql/*.sql.jinja` with **parameterized** query params.
    Construct the client with the resolved credentials and `quota_project_id`.
- Profiling: a command (`skalar-profile`) to list tables / schema / null profile; use it to **profile
  `investment_ledger`, `payment_ledger`, `monthly_payments`** and write
  `docs/datasets/skalar/tables/{investment_ledger,payment_ledger,monthly_payments}.md` (grain, columns,
  FKs, coverage, and their role vs. the `Structure`-sheet transacted ledger).

**Public API.** `skalar_data_access.{Settings, BigQueryClient, run_template, estimate_bytes,
WriteAttemptError, list_tables, schema_frame}`.

**Acceptance & tests.** `uv sync` clean; `mypy --strict` + `ruff` clean; guard unit tests
(DELETE/UPDATE/DDL refused, SELECT/WITH allowed) against a **faked** client (no network); import-linter
passes; the three ledger docs exist and match live schema (a **live-BQ** test, marked `@pytest.mark.bq`).

**Constraints.** Read-only only; no value interpolation into SQL; `estimate_bytes()` before any
`payments` query; never `SELECT *` on `payments`.

**Out of scope.** Domain logic, accounting, Excel.
