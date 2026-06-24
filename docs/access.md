# BigQuery access — read-only, keyless (ADC)

How the model reads `skalar-data.Skalar` (location **US**, dataset name is
case-sensitive). All access is **read-only** and **keyless**; no JSON key files exist
or are supported.

## Identity & roles

Workload identity is the service account
`accounting-model-sa@skalar-data.iam.gserviceaccount.com`, which holds read-only roles
only: `roles/bigquery.jobUser` (run query jobs) + dataset `roles/bigquery.dataViewer`
(read data). It can never write — there is no write role to revoke.

## Credential resolution (`skalar_data_access.credentials.resolve_credentials`)

Credentials resolve via **Application Default Credentials (ADC)**. Two paths,
selected by `Settings.impersonate_service_account`:

- **Plain ADC / attached SA (default, `impersonate_service_account = None`).** Use the
  ambient ADC identity directly. On GCP, *attach* the SA to the runtime and ADC
  resolves it with no config. Locally, this also covers ADC that was created with
  `gcloud auth application-default login --impersonate-service-account=…` — in that
  case impersonation is already baked into the ADC file.
- **In-code impersonation (`impersonate_service_account` set).** Wrap the human ADC
  principal in `google.auth.impersonated_credentials` targeting the SA. The principal
  must hold `roles/iam.serviceAccountTokenCreator` on the SA.

> **Double-impersonation trap.** If ADC is *already* impersonated (the `--impersonate-…`
> login above), leave `impersonate_service_account = None`. Setting it as well wraps
> impersonated-on-impersonated credentials and fails with an opaque token-creator error.

Quota project is `skalar-data` (set via `with_quota_project`).

### Local setup

```bash
gcloud auth application-default login   # add --impersonate-service-account=<SA> if required
# Settings come from SKALAR_* env vars; defaults already target skalar-data / Skalar / US.
```

## Defense-in-depth: the read-only SQL guard

Every query passes `skalar_data_access.guard.assert_read_only` before execution. It uses
`sqlparse` (not regex) to: strip comments, require exactly one statement, require the
statement to begin with `SELECT`/`WITH`, and reject any DML/DDL keyword
(`INSERT/UPDATE/DELETE/MERGE/CREATE/DROP/ALTER/TRUNCATE/GRANT/CALL/EXPORT/…`, plus
`SELECT … INTO`). This is a fast, typed failure on top of the IAM restriction — not the
primary control (the SA simply cannot write).

## Cost discipline

`BigQueryClient.query` runs a dry-run `estimate_bytes` first and refuses to execute if
the estimate exceeds `Settings.max_scan_bytes` (`ScanBudgetExceededError`). Note
`payments` has **no partitioning/clustering**, so a `company_id` filter does not prune —
any `payments` query scans the full referenced columns (~5 GB). The default cap is
deliberately generous (cost is not a constraint here); it is a visibility/safety rail.
Actual scanned bytes are returned on every `QueryOutcome`.

## Public API & documented deviations from the Phase-0 prompt

`skalar_data_access` exports: `Settings`, `BigQueryClient`, `ScalarParam`,
`QueryOutcome`, `assert_read_only`, `WriteAttemptError`, `ScanBudgetExceededError`,
`list_tables`, `table_schema`, `table_size`, `table_profile`, `null_profile`,
`render_template`, and module-level `estimate_bytes`/`run_template` shims.

Two intentional, minor deviations from the literal prompt API:

- **`schema_frame` → `table_schema`** returning a typed `tuple[ColumnSpec, …]` rather
  than a DataFrame. The project avoids pandas (mypy-strict friction; money is `Decimal`,
  not a float column), so there is no DataFrame type to return.
- **`run_template` / `estimate_bytes` are `BigQueryClient` methods** (they need
  credentials/config). Module-level functions of the same name are kept as thin shims
  that take the client as the first argument, to preserve the literal API surface.

Profiling (`list_tables`, `table_schema`, `table_size`, `null_profile`) is implemented as
guarded `INFORMATION_SCHEMA` / `__TABLES__` `SELECT`s, so it flows through the same guard,
cost estimate, and fake-runner injection as every other read (no separate metadata path).
