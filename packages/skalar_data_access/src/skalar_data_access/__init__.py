"""Read-only BigQuery access layer for the Skalar model.

Public API (see ``docs/access.md`` for the small, documented deviations from the
Phase-0 prompt: ``schema_frame`` -> :func:`table_schema`; ``run_template`` /
``estimate_bytes`` are :class:`BigQueryClient` methods, with module-level shims
kept here for the literal API surface).
"""

from __future__ import annotations

from .client import BigQueryClient, QueryOutcome, QueryRunner, RunResult
from .errors import DataAccessError, ScanBudgetExceededError, WriteAttemptError
from .guard import assert_read_only
from .params import ScalarParam
from .profiling import (
    ColumnSpec,
    TableProfile,
    list_tables,
    null_profile,
    table_profile,
    table_schema,
    table_size,
)
from .settings import Settings
from .templates import list_templates, render_template


def estimate_bytes(client: BigQueryClient, sql: str, params: tuple[ScalarParam, ...] = ()) -> int:
    """Module-level shim for :meth:`BigQueryClient.estimate_bytes`."""
    return client.estimate_bytes(sql, params)


def run_template(
    client: BigQueryClient,
    name: str,
    params: tuple[ScalarParam, ...] = (),
    *,
    context: dict[str, object] | None = None,
) -> QueryOutcome:
    """Module-level shim for :meth:`BigQueryClient.run_template`."""
    return client.run_template(name, params, context=context)


__all__ = [
    "BigQueryClient",
    "ColumnSpec",
    "DataAccessError",
    "QueryOutcome",
    "QueryRunner",
    "RunResult",
    "ScalarParam",
    "ScanBudgetExceededError",
    "Settings",
    "TableProfile",
    "WriteAttemptError",
    "assert_read_only",
    "estimate_bytes",
    "list_tables",
    "list_templates",
    "null_profile",
    "render_template",
    "run_template",
    "table_profile",
    "table_schema",
    "table_size",
]
