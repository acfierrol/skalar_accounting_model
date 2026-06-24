# Build prompt pack — Skalar Capital Mechanics & Accounting Model

These are the **setup prompts** that drive development. They encode the agreed architecture so an
agent or developer can build the system phase by phase without re-deciding fundamentals.

## How to use

1. Read **`../CLAUDE.md`** (persistent context: mission, data, stack, principles, definition of done).
2. Read **`00_foundation_and_architecture.md`** (binding architecture: pipeline, packages, domain
   model, the exact EIR spec, strategy seams, netting, BQ patterns, testing).
3. Execute the phases **in order**. Do not start a phase until the prior phase's tests are green.
   Each phase prompt is self-contained (Objective · Inputs/Context · Build · Public API · Acceptance &
   tests · Constraints · Out of scope).

## Phases

| # | File | Outcome |
|---|---|---|
| 0 | `phase_0_monorepo_and_bq_access.md` | uv workspace, tooling/CI, read-only BQ layer; profile the 3 undocumented ledgers |
| 1 | `phase_1_domain_models_and_parameters.md` | typed domain models + per-cohort `DealParameters` + defaults |
| 2 | `phase_2_cohorts_and_collections.md` | `collections(d,k,i)` from `payments` (cost-disciplined) |
| 3 | `phase_3_income_caps_thresholds_compliance.md` | reference income, capped sharing, MOIC/payback, thresholds, compliance, breach |
| 4 | `phase_4_cash_events_and_netting.md` | downstream cash events + debt-taken derivation + netting |
| 5 | `phase_5_eir_accounting_and_excel.md` | EIR amortization + consolidation + summary + Excel + **golden reconciliation** |
| 6 | `phase_6_cli_orchestration_and_docs.md` | CLI/orchestration, run reporting, docs |

## Architecture decisions baked in (do not relitigate without updating these files)

- **Monorepo**, multiple uv packages: `data_access → capital_mechanics → accounting → cli` (one-way).
- **Typed Python + Jinja-templated, parameterized SQL** on a read-only BQ client (no ORM, no dbt).
- **Excel computed fully in Python** (values-only; the EIR logic is the Python source of truth, not the
  workbook formulas).
- **Definition of done**: reproduce `docs/Accounting Model.xlsx` (Kindroid June+July 2026, both books,
  consolidation, summary) from BigQuery inputs — the golden reconciliation test.
