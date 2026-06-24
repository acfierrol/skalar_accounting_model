"""Table profiling via guarded ``INFORMATION_SCHEMA`` / ``__TABLES__`` SELECTs.

Everything goes through :class:`BigQueryClient`, so the read-only guard, cost
estimate, and fake-runner injection apply uniformly. Identifiers (dataset, table,
column names) are validated and embedded; *values* still flow through ``@params``.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

from .client import BigQueryClient
from .errors import DataAccessError
from .params import ScalarParam

# \Z (not $) so a trailing newline cannot sneak through identifier validation.
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\Z")


def _safe_identifier(name: str) -> str:
    if not _IDENTIFIER.match(name):
        raise DataAccessError(f"unsafe SQL identifier: {name!r}")
    return name


class ColumnSpec(BaseModel):
    """One column's name, BigQuery type, and nullability."""

    model_config = ConfigDict(frozen=True)

    name: str
    field_type: str
    is_nullable: bool
    description: str = ""


class TableProfile(BaseModel):
    """Schema + size for a single table."""

    model_config = ConfigDict(frozen=True)

    table_id: str
    num_rows: int
    num_bytes: int
    columns: tuple[ColumnSpec, ...]


def list_tables(client: BigQueryClient) -> tuple[str, ...]:
    """Return every table name in the configured dataset (sorted)."""
    dataset = _safe_identifier(client.settings.dataset)
    project = client.settings.project
    sql = (
        f"SELECT table_name FROM `{project}.{dataset}`.INFORMATION_SCHEMA.TABLES "
        "ORDER BY table_name"
    )
    outcome = client.query(sql)
    return tuple(str(row["table_name"]) for row in outcome.rows)


def table_schema(client: BigQueryClient, table: str) -> tuple[ColumnSpec, ...]:
    """Return the ordered column specs for ``table`` (replaces ``schema_frame``)."""
    dataset = _safe_identifier(client.settings.dataset)
    project = client.settings.project
    _safe_identifier(table)
    sql = (
        "SELECT column_name, data_type, is_nullable "
        f"FROM `{project}.{dataset}`.INFORMATION_SCHEMA.COLUMNS "
        "WHERE table_name = @table ORDER BY ordinal_position"
    )
    outcome = client.query(sql, (ScalarParam.string("table", table),))
    return tuple(
        ColumnSpec(
            name=str(row["column_name"]),
            field_type=str(row["data_type"]),
            is_nullable=str(row["is_nullable"]).upper() == "YES",
        )
        for row in outcome.rows
    )


def table_size(client: BigQueryClient, table: str) -> tuple[int, int]:
    """Return ``(num_rows, num_bytes)`` for ``table`` from ``__TABLES__`` (free)."""
    dataset = _safe_identifier(client.settings.dataset)
    project = client.settings.project
    sql = (
        f"SELECT row_count, size_bytes FROM `{project}.{dataset}.__TABLES__` "
        "WHERE table_id = @table"
    )
    outcome = client.query(sql, (ScalarParam.string("table", table),))
    if not outcome.rows:
        raise DataAccessError(f"table not found: {table!r}")
    row = outcome.rows[0]
    return int(row["row_count"]), int(row["size_bytes"])


def table_profile(client: BigQueryClient, table: str) -> TableProfile:
    """Combined schema + size profile for ``table``."""
    columns = table_schema(client, table)
    num_rows, num_bytes = table_size(client, table)
    return TableProfile(table_id=table, num_rows=num_rows, num_bytes=num_bytes, columns=columns)


def null_profile(
    client: BigQueryClient, table: str, columns: tuple[str, ...] | None = None
) -> dict[str, float]:
    """Return the fraction of NULL values per column (one aggregate query).

    For large tables this scans only the referenced columns. ``columns`` defaults to
    every column in the table's schema.
    """
    names = tuple(c.name for c in table_schema(client, table)) if columns is None else columns
    if not names:
        return {}
    safe = [_safe_identifier(n) for n in names]
    selects = ", ".join(f"SAFE_DIVIDE(COUNTIF({c} IS NULL), COUNT(*)) AS {c}" for c in safe)
    sql = f"SELECT {selects} FROM `{client.fq_table(table)}`"  # identifiers validated above
    outcome = client.query(sql)
    if not outcome.rows:
        return dict.fromkeys(safe, 0.0)
    row = outcome.rows[0]
    return {c: float(row[c]) if row[c] is not None else 0.0 for c in safe}
