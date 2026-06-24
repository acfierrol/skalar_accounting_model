"""Read-only BigQuery client with a guard, dry-run cost estimation, and a budget.

The client depends only on a :class:`QueryRunner` protocol, so unit tests inject a
fake runner and never touch the network. The real runner builds the
``google.cloud.bigquery`` client lazily (only when first used), so importing this
module and constructing a client with a fake runner resolves no credentials.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .credentials import resolve_credentials
from .errors import ScanBudgetExceededError
from .guard import assert_read_only
from .params import ScalarParam
from .settings import Settings
from .templates import render_template

Row = dict[str, Any]


@dataclass(frozen=True, slots=True)
class RunResult:
    """Low-level result returned by a :class:`QueryRunner`."""

    total_bytes_processed: int
    rows: tuple[Row, ...]


@runtime_checkable
class QueryRunner(Protocol):
    """Executes SQL against a backend. The only seam the client needs to run."""

    def run(self, sql: str, params: tuple[ScalarParam, ...], *, dry_run: bool) -> RunResult: ...


@dataclass(frozen=True, slots=True)
class QueryOutcome:
    """Rows plus the actual bytes scanned (surfaced for cost reporting)."""

    rows: tuple[Row, ...]
    scanned_bytes: int


class BigQueryClient:
    """Guarded, cost-disciplined entry point for all reads."""

    def __init__(self, settings: Settings, *, runner: QueryRunner | None = None) -> None:
        self._settings = settings
        self._runner: QueryRunner = runner if runner is not None else _BigQueryRunner(settings)

    @property
    def settings(self) -> Settings:
        return self._settings

    def estimate_bytes(self, sql: str, params: tuple[ScalarParam, ...] = ()) -> int:
        """Dry-run byte estimate for ``sql`` (free; no data scanned)."""
        assert_read_only(sql)
        return self._runner.run(sql, params, dry_run=True).total_bytes_processed

    def query(
        self,
        sql: str,
        params: tuple[ScalarParam, ...] = (),
        *,
        max_scan_bytes: int | None = None,
    ) -> QueryOutcome:
        """Guard, estimate, enforce the scan budget, then execute ``sql``."""
        assert_read_only(sql)
        budget = self._settings.max_scan_bytes if max_scan_bytes is None else max_scan_bytes
        estimate = self._runner.run(sql, params, dry_run=True).total_bytes_processed
        if estimate > budget:
            raise ScanBudgetExceededError(estimate, budget)
        result = self._runner.run(sql, params, dry_run=False)
        return QueryOutcome(rows=result.rows, scanned_bytes=result.total_bytes_processed)

    def run_template(
        self,
        name: str,
        params: tuple[ScalarParam, ...] = (),
        *,
        context: dict[str, object] | None = None,
        max_scan_bytes: int | None = None,
    ) -> QueryOutcome:
        """Render ``sql/<name>.sql.jinja`` with ``context`` and run it.

        ``project`` and ``dataset`` are injected from settings automatically (every
        template needs them); ``context`` supplies any additional structure.
        """
        ctx: dict[str, object] = {
            "project": self._settings.project,
            "dataset": self._settings.dataset,
        }
        if context:
            ctx.update(context)
        sql = render_template(name, **ctx)
        return self.query(sql, params, max_scan_bytes=max_scan_bytes)

    def fq_table(self, table: str) -> str:
        """Fully-qualified ``project.dataset.table`` reference."""
        return f"{self._settings.project}.{self._settings.dataset}.{table}"


class _BigQueryRunner:
    """Real runner backed by ``google.cloud.bigquery`` (built lazily)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Any = None

    def _client_or_build(self) -> Any:
        if self._client is None:
            from google.cloud import bigquery

            credentials, project = resolve_credentials(self._settings)
            self._client = bigquery.Client(
                project=project,
                credentials=credentials,
                location=self._settings.location,
            )
        return self._client

    def run(self, sql: str, params: tuple[ScalarParam, ...], *, dry_run: bool) -> RunResult:
        from google.cloud import bigquery

        client = self._client_or_build()
        job_config = bigquery.QueryJobConfig(
            dry_run=dry_run,
            use_query_cache=not dry_run,
            query_parameters=[
                bigquery.ScalarQueryParameter(p.name, p.type_, p.value) for p in params
            ],
        )
        job = client.query(sql, job_config=job_config)
        scanned = int(job.total_bytes_processed or 0)
        if dry_run:
            return RunResult(total_bytes_processed=scanned, rows=())
        rows: tuple[Row, ...] = tuple(dict(row.items()) for row in job.result())
        return RunResult(total_bytes_processed=int(job.total_bytes_processed or 0), rows=rows)
