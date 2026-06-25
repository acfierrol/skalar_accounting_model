# Changelog

All notable changes to this project. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); this project is pre-1.0 and unversioned.

## [Unreleased]

### Added — Visualization (`skalar_viz`)
- `skalar_viz`: decomposes collections into the Skalar/GC sharing waterfall
  (`collections → R → S → S~ → GC remittance / Skalar retained`, reusing the engine's
  `reference_income`/`sharing_schedule`) and lays the per-cohort flows on a cohort × calendar-period
  run-off triangle. `decompose_portfolio`, `build_waterfall_steps`, `build_cohort_period_matrix`,
  and matplotlib renderers `plot_waterfall` / `plot_cohort_matrix`; `scenario` helpers for
  parametrized synthetic inputs. A presentation leaf (import-linter forbids the engine/accounting
  from importing it).
- Parametrized notebook `notebooks/collections_waterfall.ipynb` (+ `make notebook`).

### Added — Spend access (`skalar_capital_mechanics.spend`)
- `build_spend` reads the consolidated `skalar-data.Skalar.spend` table; `resolve_funding` sizes
  each cohort's funding (`F`, GC PFA, Skalar pool) and the threshold basis.

### Added — Phase 6 (CLI / orchestration, reporting, docs)
- `skalar-accounting run` CLI (typer) wiring `data_access → capital_mechanics → accounting`:
  loads a cached engine output, writes the values-only workbook, prints a run report
  (scanned bytes, Revenue, Cost of Capital, outstanding, compliance/threshold counts, netting
  wires, reconciliation `|Check|`).
- `skalar_cli.pipeline`: `books_from_cash_events`, `run_pipeline`, `load_engine_output`,
  `RunReport`. Cached SK011 fixture (`apps/cli/fixtures/sk011.json`) reproducing the workbook.
- mkdocs site (`mkdocs.yml`, Home / Architecture / How-to-run / Parameter reference), `Makefile`,
  and this changelog.

### Added — Phase 5 (EIR accounting + golden reconciliation)
- `skalar_accounting`: EIR engine (`amortize`, asset + liability forms), day-counts, `xirr`
  (Newton + bisection, `#NUM!` → `None`), `consolidate`, `build_summary`, values-only Excel
  writer. **Golden reconciliation** against `docs/Accounting Model.xlsx` passes to
  sub-micro-dollar — the system's definition of done.

### Added — Phase 4 (cash events, debt-taken, netting)
- `skalar_capital_mechanics.cash_events`: `build_downstream_cash_events`, `derive_debt_taken`,
  `build_netting`, `build_transacted_ledger`.

### Added — Phases 0–3
- Monorepo + tooling (uv, mypy --strict, ruff, import-linter, pytest); read-only BigQuery access
  layer; domain models + per-cohort deal-parameter resolution; collections engine; reference
  income, sharing, return caps, thresholds (Mechanic I/II), compliance, wind-down.
