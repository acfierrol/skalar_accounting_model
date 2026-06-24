# Phase 6 — CLI / orchestration, reporting, docs

**Objective.** Wire the full pipeline behind a CLI, add run reporting, and complete the docs.

**Inputs / context.** `00_foundation` §1 (pipeline); `apps/cli`; the mkdocs site under `docs/`.

**Build.**
- **CLI** (`typer`): `skalar-accounting run --company SK011 --from <m> --to <m> --asof <d>
  --gc-dates <file> --out <path.xlsx> [--use-cache]` orchestrating
  `data_access → capital_mechanics → accounting`. No business logic in the CLI — it only wires packages.
- **Run report**: scanned bytes (cost), compliance violations, threshold breaches, and the netting
  to-do summary; structured logging.
- **Docs**: mkdocs pages for the engine and accounting (architecture mirror, how-to-run, parameter
  reference); update `docs/datasets/skalar/index.md` to include the newly profiled ledger tables; add a
  `CHANGELOG`. Provide uv scripts / Make targets for the common commands.

**Public API.** CLI entrypoints (`apps/cli`).

**Acceptance & tests.** End-to-end run on cached SK011 fixtures deterministically produces the workbook
+ report; CLI smoke tests; `mkdocs build` clean; full-workspace `mypy --strict` / `ruff` / `pytest`
green.

**Constraints.** Deterministic, reproducible runs; the CLI delegates to packages; no network in default
test runs.

**Out of scope.** New financial features beyond the pipeline.
