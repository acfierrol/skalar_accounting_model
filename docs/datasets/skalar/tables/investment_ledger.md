# `investment_ledger`

**Grain.** One row per investment / funding event (downstream Investment Amount, and its
GC/Skalar split). 1 row at profiling time (SK011, cohort 2026-06).

**Role in the pipeline.** The downstream **funding outflow** ("debt given") side of the
transacted ledger: Investment Amounts disbursed to the Company, plus their leverage split
and any Funding Adjustments. Feeds the cash events in Phase 4; the GC split + `trade_date`
seed the upstream debt-taken derivation.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `company_id` | STRING | yes | Deal id. |
| `cohort_month` | DATE | yes | Cohort / S&M period the funding is for (1st of month). |
| `amount` | FLOAT | yes | Signed Investment Amount. **Negative for accounting** (outflow); positive only for positive adjustments. 2 dp. |
| `gc_amount` | FLOAT | yes | GC (senior) portion = `φ · amount` (φ = 0.95). 2 dp. |
| `skalar_amount` | FLOAT | yes | Skalar (junior) portion = `(1−φ) · amount`. 2 dp. |
| `due_date` | DATE | yes | Month the amount is due (1st of month). |
| `trade_date` | DATE | yes | Date GC ("CVF" — Customer Value Financing) interacts with Skalar — the **GC transaction date** used to date debt-taken (Phase 4). |
| `is_adjustment` | BOOLEAN | yes | True if this row is a Funding Adjustment (spend reconciliation), not an original IR. |

**Live golden row (SK011, 2026-06):** `amount=-160000.0`, `gc_amount=-152000.0`,
`skalar_amount=-8000.0`, `due_date=2026-06-01`, `trade_date=2026-06-05`,
`is_adjustment=false`. F = $160k = 0.80 × $200k expected spend; 0.95/0.05 split.

**Notes.** `amount = gc_amount + skalar_amount` (leverage invariant). Sign convention here
is ledger-local (negative = outflow); the engine's `CashEvent` layer re-expresses signs
from Skalar's perspective (inflow > 0).
