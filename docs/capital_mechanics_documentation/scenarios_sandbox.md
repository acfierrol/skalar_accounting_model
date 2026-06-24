# Skalar — Scenarios & Sandbox (testing)

Concrete, dated cases for exercising the methodology. The two reference documents
— `skalar_cash_model_kb.md` (engineering KB) and `skalar_cash_events_vintages`
(Capital Mechanics) — are deliberately abstract: every live-deal value, party,
date, and dollar figure lives **here**, not there. Use this file to seed tests,
build fixtures, and sanity-check the formulas against worked numbers.

All money in USD unless noted. All formulas reference definitions in the KB / Capital Mechanics.

---

## 0. Vintage clock

- **Vintages (upstream Reference Cohorts) commence June 1, 2026** — Skalar's first
  disbursement. Monthly thereafter (`L_op = 1`).
- Calendar months before June 2026 exist only as **legacy / historical cohorts**
  for threshold testing (6 upstream, 12 downstream), never funded.

## 1. Leverage structure (current regime)

| Tranche | Provider | Rate | Note |
|---|---|---|---|
| Senior advance | GC (single senior actor, first draft) | `φ = 0.95` | discretionary; treated as debt for tax/accounting |
| Junior co-investment | Skalar pool | `1 − φ = 0.05` | fungible pool |

Ratio `0.95 : 0.05 ≈ 19:1`. **Temporary** — `φ` is the aggregate senior advance
rate and may be revised; the senior side may later be syndicated across several
actors, in which case `φ(τ)` aggregates their advances.

Upstream cap legs (current facility): `min(2.0× PFA, 16% XIRR amount)`;
default rate 16%/yr (360/30); acceleration 3 business days; graduation triggers
$2.5M single-period spend **and** $20M aggregate outstanding; 10-year extinguishment.

---

## 2. Deal scenarios (resolved parameter sets)

### Scenario A — consumer subscription app (executed)

| Dimension | Value |
|---|---|
| Operation cadence `L_op` | monthly, from closing |
| Funding `f` | fixed `0.80` |
| Sharing `s` | `0.80` (elects `s = f`) |
| Income scope | single product line (subscriptions) |
| Margin `g(d,i)` | `0.45`, fixed across cohorts |
| Return-pricing strategy | MOIC ladder `(b, a_b, step, M) = (1.08, 4 mo, 0.014/mo, 1.60)` |
| Commitment | `$6.0M` over 12 months; "12-6-12" extension review |
| Per-period funding cap | `min($500k, 20% spend growth)` |
| Windows | "Net-60" `L_c + L_s ≈ 30 + 30 d` ⇒ `λ = 2`, `δ = 3` |
| Threshold checkpoints | ages `{0,1,2,3} = 16 / 25 / 31 / 37%` |
| Threshold Δ | `5%` from age 4 |
| Threshold mechanic / timing / exit | **II (incremental Δ)** / any-day / breakeven |
| Wind-down | `5%` trailing-3M; carve-outs: safety/content/AUP enforcement; app-store-removal variant |
| FX | none (USD-only) |
| Legacy cohorts | 12 pre-closing monthly |

### Scenario B — B2B SaaS + payments, multi-currency (term sheet)

| Dimension | Value |
|---|---|
| Operation cadence `L_op` | monthly, from closing |
| Funding `f` | band `[0.40, 0.70]`, company-elected per period |
| Sharing `s` | `= f` elected for the cohort's period |
| Income scope | all revenue streams, net of discounts |
| Margin `g(d,i)` | `0.80` |
| Return-pricing strategy | MOIC ladder `(1.09, 5 mo, 0.0125/mo, 1.70)` |
| Commitment | `$10.0M` over 12 months; "12-6-12" |
| Per-period funding cap | `min($835k, 10% spend growth)` |
| Windows | "Net-30" `L_c + L_s = 14 + 14 d` ⇒ `λ = 1`, `δ = 2` |
| Threshold checkpoints | ages `{0,3,6,9,12} = 7 / 24 / 40 / 56 / 73%` |
| Threshold Δ | `5%` from age 13 |
| Threshold mechanic / timing / exit | per election (TS Δ reads incremental) / period-end (TS) / breakeven |
| Wind-down | `2.5%` trailing-3M; no carve-out |
| FX | inception rate `e0` per cohort; `κ = 1.20`; company bears depreciation beyond 20% |
| Legacy cohorts | 12 pre-closing monthly; pre-deal customer IDs excluded |

---

## 3. Worked vintage walkthrough — Scenario A, vintage τ = 2026-06

Rounded kUSD; monthly XIRR approximation at 16%/yr; expected = actual spend.
**Setup:** `espend = spend = 200.0`; `f = s = 0.80` ⇒ `F = 160.0`; `g = 0.45`;
ladder `(1.08, 4, 0.014, 1.60)`. Upstream: `F_sk = 160.0`, `φ = 0.95` ⇒
`PFA = 152.0`, pool draw `8.0`; `σ = 0.95`; cap legs `2.0×152.0 = 304.0` and 16% XIRR.
Scenario A elects **Mechanic II**, so M0–M3 are cumulative checkpoints and the Δ
rows test each period's own contribution.

### 3.1 Downstream cohort ledger

| Age | Collections | R (×0.45) | S̃ (×0.80) | cum S̃ | Test / event |
|---:|---:|---:|---:|---:|---|
| 0 | 120.00 | 54.00 | 43.20 | 43.20 | M0 27% ≥ 16% |
| 1 | 90.00 | 40.50 | 32.40 | 75.60 | M1 47.3% ≥ 25% |
| 2 | 70.00 | 31.50 | 25.20 | 100.80 | M2 63.0% ≥ 31% |
| 3 | 55.00 | 24.75 | 19.80 | 120.60 | M3 75.4% ≥ 37% |
| 4 | 45.00 | 20.25 | 16.20 | 136.80 | Δ 10.1% ≥ 5% |
| 5 | 40.00 | 18.00 | 14.40 | 151.20 | Δ 9.0% |
| 6 | 35.00 | 15.75 | 12.60 | 163.80 | payback (≥160); cum R = 102.4% ⇒ breakeven exit |
| 7 | 30.00 | 13.50 | 10.80 | 174.60 | — |
| 8 | 25.00 | 11.25 | 2.68 | 177.28 | cap reached; cohort closes |

Payback age `a* = 6` ⇒ `μ = 1.08 + 2×0.014 = 1.108`; `cap = 1.108 × 160.0 = 177.28`;
the age-8 flow truncates to `2.68`.

### 3.2 Upstream vintage ledger

Cohort income of age `k` falls due downstream at age `k + 2` (Net-60), remitted
upstream by day 17 of the following month. `rem = 0.95 × RI` until a cap leg binds.
PV discounts each remittance to the funding date at 16%/yr; closure when cum PV
reaches `PFA = 152.0`.

| k | Date | rem | cum rem | cum PV@16 | State |
|---:|---|---:|---:|---:|---|
| 0 | 2026-09-17 | 41.04 | 41.04 | 39.28 | repaying |
| 1 | 2026-10-17 | 30.78 | 71.82 | 68.37 | repaying |
| 2 | 2026-11-17 | 23.94 | 95.76 | 90.73 | repaying |
| 3 | 2026-12-17 | 18.81 | 114.57 | 108.07 | repaying |
| 4 | 2027-01-17 | 15.39 | 129.96 | 122.09 | repaying |
| 5 | 2027-02-17 | 13.68 | 143.64 | 134.40 | repaying |
| 6 | 2027-03-17 | 11.97 | 155.61 | 145.04 | repaying |
| 7 | 2027-04-17 | 7.93 | 163.54 | 152.00 | closed: XIRR leg met exactly; Skalar retains residual 2.33 |
| 8 | 2027-05-17 | 0.00 | 163.54 | — | post-cap: Skalar retains 100% (2.68) |

**Reading.** Binding leg: XIRR (163.54 ≪ 304.0); the 2.0× ceiling is immaterial for
fast vintages. Skalar's economics: entitlement 177.28, remitted 163.54, net 13.74
on a pool draw of 8.0 over ≈ 11 months — the velocity spread, which vanishes as
payback ages lengthen toward the ladder/IRR crossover.

### 3.3 One composite wire (ideal matched case)

September 2026 upstream settlement, assuming an October vintage of `F_sk = 400.0`
(`PFA = 380.0`):

```
Net_gc(Sep 2026) = 380.00 (PFA, τ=Oct) − 41.04 (remit, τ=Jun) = 338.96  → GC pays Skalar
```

The wire points at Skalar; the 41.04 remittance underneath is unconditional and
survives even if GC declines the PFA leg (solvency-without-GC). Per the netting
principle this closed form is the *ideal* case where both components share a date;
in operation only the components that actually coincide are aggregated.
