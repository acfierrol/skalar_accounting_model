# Skalar Capital Mechanics & Accounting Model

One monorepo, two deliverables with a strict one-way dependency:

1. **Capital-mechanics engine** (`skalar_capital_mechanics`) — reads Skalar's BigQuery
   operational data and builds the cash model: cohorts, collections, reference income,
   sharing, return caps, thresholds, compliance, and per-vintage **cash events**.
2. **Accounting model** (`skalar_accounting`) — consumes those cash events and produces the
   cash-basis accounting report via the effective-interest (EIR / amortized-cost) method.

The engine is the source of truth for *what happened*; accounting for *how it is booked*.
Accounting imports the engine; the engine never imports accounting.

See [`CLAUDE.md`](CLAUDE.md) for the mission, [`prompts/00_foundation_and_architecture.md`](prompts/00_foundation_and_architecture.md)
for the binding architecture, and [`docs/access.md`](docs/access.md) for BigQuery access.

## Layout

```
packages/
  skalar_data_access/        # read-only BigQuery client: guard, Jinja SQL, cost discipline, profiling
  skalar_capital_mechanics/  # engine: domain models, deal parameters, collections, cash events
  skalar_accounting/         # EIR amortization, consolidation, summary, Excel writer
  skalar_data_docs/          # dataset-doc tooling (schema/profile -> markdown)
apps/cli/                    # orchestration CLI (skalar-profile, skalar)
docs/datasets/skalar/        # profiled dataset docs (the 7 tables)
```

Dependency rule (enforced by import-linter in CI): `data_access → capital_mechanics →
accounting → cli` (never reversed).

## Commands

```bash
uv sync --all-groups            # build the workspace (Python 3.13)
uv run ruff check               # lint
uv run ruff format --check      # format
uv run mypy                     # type-check (strict)
uv run lint-imports             # layer contracts
uv run pytest                   # offline tests (live BigQuery tests deselected)
uv run pytest -m bq             # live BigQuery acceptance (requires ADC)
uv run skalar-profile show payments   # profile a table (read-only)

gcloud auth application-default login  # read-only ADC; project skalar-data, dataset Skalar
```

## Status

- **Phase 0** — workspace, tooling/CI, read-only BigQuery access, dataset docs. ✅
- **Phase 1** — domain models + per-cohort deal parameters + defaults. ✅
- **Phase 2** — cohorts & collections engine (payments → matrix, cohort integrity, parquet cache). ✅
- Phases 3–6 — caps/thresholds, cash events, EIR/Excel, CLI. _planned_

Golden case: **SK011 / Kindroid** (the live worked vintage in
`docs/capital_mechanics_documentation/scenarios_sandbox.md`).
