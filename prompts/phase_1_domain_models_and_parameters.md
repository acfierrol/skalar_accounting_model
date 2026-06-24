# Phase 1 — Domain models & deal-parameter resolution

**Objective.** Typed domain model + a resolver producing **per-cohort** `DealParameters` from BigQuery,
backed by an overridable defaults config.

**Inputs / context.** `00_foundation` §3 (models), §5 (strategy seams); KB §3 (parameters), §11
(leverage structure); `scenarios_sandbox.md` (Scenario A/B values → fixtures).

**Build.**
- `skalar_capital_mechanics.models`: frozen Pydantic v2 models from §3 — `Company`, `DealParameters`
  (with **independent** `funding_band` and `sharing_band`; **per-cohort** `margin`; `pricing_strategy`
  reference; `eir_given`/`eir_taken`; `L_op,L_c,L_s` with derived `lambda_`, `delta`; `leverage`;
  per-period cap `min(dollar_cap, growth_cap)`; `commitment_amount`; `threshold` spec; `winddown`).
  Money = `Decimal`, dates = `date`; validators (`0 < f_min ≤ f_max < 1`, etc.).
- `defaults` config (the "current default regime"): margin fixed-per-cohort, pricing = MOIC ladder,
  `leverage = 0.95`, `eir_taken = 0.16`, default settlement windows, `s = f` as the default election —
  **all overridable per deal**, never hard-coded at call sites.
- `resolve_deal_parameters(company_id, cohort_month)`: read `company`, `origination_collection_percent`,
  `spend`; resolve parameters per cohort; apply defaults where the source is silent. Encode the
  documented ambiguities (meaning of `origination_collection_percent`; integer percents) as explicit,
  typed, commented fields.

**Public API.** `models` module; `resolve_deal_parameters(...) -> DealParameters`; `load_defaults()`.

**Acceptance & tests.** Models reject invalid parameter sets; the resolver reproduces Kindroid's known
parameters (funding 0.80, sharing 0.80, `delay_months` 2, leverage 0.95, `eir_taken` 0.16) from fixtures;
`mypy --strict`/`ruff`/tests green.

**Constraints.** Resolution is per cohort; no `Any`; validation at IO edges; defaults are data, not code.

**Out of scope.** Collections, cash events, accounting.
