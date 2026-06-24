# `payment_ledger`

**Grain.** One row per payment-due / remittance event. **0 rows** at profiling time
(empty — populated as sharing remittances are booked).

**Role in the pipeline.** The **sharing remittance / "payments due"** side of the
transacted ledger: amounts the Company remits to Skalar (downstream sharing), with the
GC/Skalar split for the upstream remittance. The inflow ("share-up" / "remit") counterpart
to `investment_ledger`.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `company_id` | STRING | yes | Deal id. |
| `cohort_month` | DATE | yes | Cohort the remittance is attributed to (1st of month). |
| `amount` | FLOAT | yes | Payment-due amount. **Always positive.** 2 dp. |
| `gc_amount` | FLOAT | yes | GC portion of the remittance. 2 dp. |
| `skalar_amount` | FLOAT | yes | Skalar retained portion. 2 dp. |
| `due_date` | DATE | yes | When the amount is due. |
| `trade_date` | DATE | yes | Transaction date. |
| `type` | STRING | yes | Event type label (e.g. payment-due category). |

**Notes.** Mirror of `investment_ledger` for the inflow direction. Empty now; the engine
must tolerate an empty ledger (no remittances booked yet for the new June-2026 vintage).
`amount = gc_amount + skalar_amount` expected when populated.
