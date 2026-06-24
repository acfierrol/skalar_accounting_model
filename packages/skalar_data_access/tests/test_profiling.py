"""Profiling logic (offline, scripted fake runner — no network)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from skalar_data_access import (
    BigQueryClient,
    DataAccessError,
    Settings,
    list_tables,
    null_profile,
    table_schema,
    table_size,
)
from skalar_data_access.client import RunResult
from skalar_data_access.params import ScalarParam
from skalar_data_access.profiling import _safe_identifier


@dataclass
class ScriptedRunner:
    """Returns canned rows for the first response key found in the SQL (longest key first)."""

    responses: dict[str, tuple[dict[str, object], ...]]

    def run(self, sql: str, params: tuple[ScalarParam, ...], *, dry_run: bool) -> RunResult:
        if dry_run:
            return RunResult(total_bytes_processed=0, rows=())
        for key in sorted(self.responses, key=len, reverse=True):
            if key in sql:
                return RunResult(total_bytes_processed=0, rows=self.responses[key])
        return RunResult(total_bytes_processed=0, rows=())


def _client(responses: dict[str, tuple[dict[str, object], ...]]) -> BigQueryClient:
    return BigQueryClient(Settings(), runner=ScriptedRunner(responses))


def test_safe_identifier_accepts_valid() -> None:
    assert _safe_identifier("payments") == "payments"
    assert _safe_identifier("usd_amount") == "usd_amount"
    assert _safe_identifier("_x9") == "_x9"


@pytest.mark.parametrize("bad", ["1bad", "a; DROP", "a-b", "a b", "payments\n", "", "a;"])
def test_safe_identifier_rejects_invalid(bad: str) -> None:
    with pytest.raises(DataAccessError):
        _safe_identifier(bad)


def test_list_tables() -> None:
    client = _client(
        {"INFORMATION_SCHEMA.TABLES": ({"table_name": "company"}, {"table_name": "payments"})}
    )
    assert list_tables(client) == ("company", "payments")


def test_table_schema_maps_nullability() -> None:
    client = _client(
        {
            "INFORMATION_SCHEMA.COLUMNS": (
                {"column_name": "usd_amount", "data_type": "FLOAT64", "is_nullable": "YES"},
                {"column_name": "company_id", "data_type": "STRING", "is_nullable": "NO"},
            )
        }
    )
    cols = table_schema(client, "payments")
    assert [(c.name, c.field_type, c.is_nullable) for c in cols] == [
        ("usd_amount", "FLOAT64", True),
        ("company_id", "STRING", False),
    ]


def test_table_size() -> None:
    client = _client({"__TABLES__": ({"row_count": 100, "size_bytes": 2048},)})
    assert table_size(client, "payments") == (100, 2048)


def test_table_size_not_found_raises() -> None:
    with pytest.raises(DataAccessError):
        table_size(_client({"__TABLES__": ()}), "missing")


def test_null_profile_coalesces_none_to_zero() -> None:
    client = _client(
        {
            "INFORMATION_SCHEMA.COLUMNS": (
                {"column_name": "a", "data_type": "STRING", "is_nullable": "YES"},
                {"column_name": "b", "data_type": "STRING", "is_nullable": "YES"},
            ),
            "SAFE_DIVIDE": ({"a": 0.5, "b": None},),
        }
    )
    assert null_profile(client, "t") == {"a": 0.5, "b": 0.0}


def test_null_profile_empty_table() -> None:
    assert null_profile(_client({"INFORMATION_SCHEMA.COLUMNS": ()}), "t") == {}
