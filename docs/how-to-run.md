# How to run

## Setup

```bash
uv sync --all-groups
gcloud auth application-default login   # read-only ADC; project skalar-data, dataset Skalar
```

## Quality gates

```bash
uv run ruff check        # lint + format
uv run mypy              # strict type-check (whole workspace)
uv run lint-imports      # layered-architecture contract
uv run pytest            # offline tests (live BigQuery tests are marked `bq` and deselected)
```

`make check` runs all four; `make docs` builds this site.

## Run the accounting pipeline

The `skalar-accounting` CLI wires `data_access → capital_mechanics → accounting`, writes the
values-only workbook, and prints a run report:

```bash
uv run skalar-accounting run \
    --company SK011 \
    --from 2026-06-01 --to 2026-07-01 --asof 2026-11-30 \
    --cache apps/cli/fixtures/sk011.json \
    --out build/sk011.xlsx
```

`--cache <engine-output.json>` runs deterministically offline from a cached engine output (the
SK011 fixture reproduces `docs/Accounting Model.xlsx`). The run report shows BigQuery scanned
bytes, Revenue, Cost of Capital, outstanding lended/borrowed, compliance violations, threshold
breaches, the netting "to-do" wire count, and the reconciliation `|Check|` (≈ 0).

> **Live BigQuery runs** (building cash events from scratch) are not yet wired end-to-end: the
> hand-set per-deal spend / funding-adjustment / GC-transaction-date inputs are not all carried
> in BigQuery. Until that is wired, supply `--cache`.

## Profile the BigQuery tables (read-only)

```bash
uv run skalar-profile tables
uv run skalar-profile show payments --nulls
uv run skalar-profile doc spend --grain "(company, cohort_month)"
```
