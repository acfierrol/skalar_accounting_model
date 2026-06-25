# Parameter reference

Deal parameters are **data, resolved per cohort** — never magic numbers in code. Defaults live in
`skalar_capital_mechanics.defaults` and are overridable per deal; `resolve_deal_parameters` reads
the funding/sharing election + settlement lag from BigQuery and fills the rest from the defaults.

## `DealParameters` (per `(company_id, cohort_month)`)

| Field | Meaning (KB ref) |
|---|---|
| `funding_band` / `funding_pct` | negotiated funding interval + the cohort's elected rate (§3.2 #1) |
| `sharing_band` / `sharing_pct` | sharing interval + elected rate, independent of funding (§3.2 #2) |
| `margin` | gross margin applied to collections → Reference Income (§3.2 #3) |
| `pricing_strategy` / `moic_ladder` | return-pricing family; default payback MOIC ladder `(b, a_b, step, M)` (§7) |
| `eir_given` / `eir_taken` | per-book EIR rates (0.25 / 0.16) — confirmed by the workbook |
| `windows` | settlement calendar `L_op`, `lambda_`, `delta` (§5) |
| `leverage` | senior/junior split (GC 0.95 : Skalar 0.05) and upstream cap legs (§11) |
| `per_period_cap` | per-period funding cap = `min(dollar_cap, growth_cap_pct)` (§9.3) |
| `commitment_amount` | cumulative funding ceiling (§9.3) |
| `threshold` | mechanic (I/II), timing, exit, checkpoint grid, delta (§3.3) |
| `winddown` | trailing-3M Reference-Income cancellation trigger (§9.2) |

## Strategy elections (the executed SK011 / Scenario-A regime)

- **Pricing**: payback MOIC ladder `(1.08, 4 months, 0.014/month, 1.60)`.
- **Threshold**: Mechanic II (incremental delta), `any_day` timing, `breakeven` exit; checkpoints
  `{0: 16%, 1: 25%, 2: 31%, 3: 37%}`, delta 5% from age 4.
- **Day-count**: debt given month-days/365; debt taken actual-days/365.

The full per-term definitions are in the [methodology KB](capital_mechanics_documentation/skalar_cash_model_kb.md)
and the resolved scenario values in the [scenarios sandbox](capital_mechanics_documentation/scenarios_sandbox.md).
