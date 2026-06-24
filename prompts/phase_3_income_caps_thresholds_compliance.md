# Phase 3 — Reference income, sharing, caps, thresholds, compliance

**Objective.** Turn collections + parameters into reference income, capped sharing, return caps,
threshold results, and compliance/breach checks.

**Inputs / context.** `00_foundation` §3, §5; KB §3.3 (threshold mechanics I/II; basis = cohort
Reference Income / **origin-period Actual S&M Spend**), §7 (payback / MOIC / return cap), §3.2 (per-period
& commitment caps, deemed minimum), §9 (wind-down, breach); Capital Mechanics `def:capdn`, `def:basis`,
`def:netprinciple`. Fixtures from `scenarios_sandbox.md`.

**Build.**
- `reference_income = collections × margin` (per-cohort margin); `sharing = RI × sharing_pct`,
  **recursively truncated** at `return_cap` (Decimal-exact).
- `PricingStrategy` protocol + default **payback MOIC ladder** `(b, a_b, step, M)`: payback age
  (un-lagged, rounded up to whole months), MOIC freeze at payback, `return_cap = MOIC × F_eff`.
- `ThresholdMechanic` protocol + **Mechanic I** (linear ladder, default) and **Mechanic II**
  (per-period incremental); basis exactly per KB; `timing` (any-day/period-end) and `exit`
  (breakeven/return-cap) elections; **breach** flag (sharing → 100%, irreversible) including legacy
  cohorts. Carry the agreement-language caution as a docstring.
- `compliance`: per-period cap `min(dollar, growth)`, cumulative commitment cap, deemed-minimum floor;
  emit typed violations (don't raise — report).

**Public API.** `reference_income(...)`, `sharing_schedule(...)`, `return_cap(...)`,
`evaluate_threshold(...)`, `check_compliance(...)`.

**Acceptance & tests.** Reproduce the scenario-sandbox **worked-vintage downstream ledger** (R, S̃,
cum S̃, payback `a*=6`, `μ=1.108`, `cap=177.28`) within tolerance; Mechanic I vs II table-driven tests;
compliance violations fire on constructed cap-busting cases. `mypy`/`ruff`/tests green.

**Constraints.** Strategies swappable via the registry; basis never uses received-sharing numerator or
funded-amount denominator; `Decimal` throughout.

**Out of scope.** Cash-event dating, debt-taken, accounting.
