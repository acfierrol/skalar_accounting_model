# `company`

**Grain.** One row per deal (Company). 22 rows.

**Role.** Maps `company_id` (`SK0NN`) → `company_name`. Lookup for the deal register.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `company_name` | STRING | yes | Display name (e.g. `Kindroid`). |
| `company_id` | STRING | yes | `SK0NN` deal id (e.g. `SK011`). |

22 deals SK001–SK022. SK011 = Kindroid (the golden case). ~13 active deals have
collections in `monthly_payments`.
