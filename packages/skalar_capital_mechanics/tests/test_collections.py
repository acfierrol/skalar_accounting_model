"""Collections builder + cache (offline, fake runner)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from skalar_capital_mechanics import (
    CollectionsCell,
    CollectionsMatrix,
    CollectionsMeta,
    build_collections,
    cohort_index,
)
from skalar_capital_mechanics.collections import cache
from skalar_data_access import BigQueryClient, ScalarParam, ScanBudgetExceededError, Settings
from skalar_data_access.client import RunResult

ROWS: tuple[dict[str, object], ...] = (
    {
        "company_id": "SK011",
        "cohort_month": date(2026, 6, 1),
        "payment_month": date(2026, 6, 1),
        "collections": 120000.0,
    },
    {
        "company_id": "SK011",
        "cohort_month": date(2026, 6, 1),
        "payment_month": date(2026, 7, 1),
        "collections": 90000.0,
    },
    {
        "company_id": "SK011",
        "cohort_month": date(2026, 6, 1),
        "payment_month": date(2026, 8, 1),
        "collections": -500.0,  # net-refund month
    },
    {
        "company_id": "SK011",
        "cohort_month": date(2026, 7, 1),
        "payment_month": date(2026, 7, 1),
        "collections": 0.0,  # zero kept
    },
)

RANGE = (date(2026, 1, 1), date(2027, 1, 1))


@dataclass
class FakeRunner:
    rows: tuple[dict[str, object], ...] = ()
    dry_run_bytes: int = 100
    calls: list[tuple[str, tuple[ScalarParam, ...], bool]] = field(default_factory=list)

    def run(self, sql: str, params: tuple[ScalarParam, ...], *, dry_run: bool) -> RunResult:
        self.calls.append((sql, params, dry_run))
        return RunResult(self.dry_run_bytes, () if dry_run else self.rows)


def _client(runner: FakeRunner, *, max_scan_bytes: int | None = None) -> BigQueryClient:
    settings = Settings() if max_scan_bytes is None else Settings(max_scan_bytes=max_scan_bytes)
    return BigQueryClient(settings, runner=runner)


def test_build_maps_rows_to_cells() -> None:
    matrix = build_collections(_client(FakeRunner(rows=ROWS)), "SK011", RANGE, use_cache=False)
    assert len(matrix.cells) == 4
    assert matrix.cell(date(2026, 6, 1), date(2026, 6, 1)) == Decimal("120000.0")
    assert matrix.cell(date(2026, 6, 1), date(2026, 8, 1)) == Decimal("-500.0")  # refund nets
    assert matrix.cell(date(2026, 7, 1), date(2026, 7, 1)) == Decimal("0.0")  # zero kept
    assert matrix.cohort_totals()[date(2026, 6, 1)] == Decimal("209500.0")
    assert matrix.meta.source == "payments"
    assert not matrix.meta.from_cache
    assert matrix.meta.scanned_bytes == 100


def test_decimal_conversion_is_exact() -> None:
    rows = (
        {
            "company_id": "SK011",
            "cohort_month": date(2026, 6, 1),
            "payment_month": date(2026, 6, 1),
            "collections": 0.1,
        },
    )
    matrix = build_collections(_client(FakeRunner(rows=rows)), "SK011", RANGE, use_cache=False)
    assert matrix.cells[0].collections == Decimal("0.1")  # Decimal(str(x)), not Decimal(float)


def test_null_collections_becomes_zero() -> None:
    rows = (
        {
            "company_id": "SK011",
            "cohort_month": date(2026, 6, 1),
            "payment_month": date(2026, 6, 1),
            "collections": None,
        },
    )
    matrix = build_collections(_client(FakeRunner(rows=rows)), "SK011", RANGE, use_cache=False)
    assert matrix.cells[0].collections == Decimal(0)


def test_cost_guard_trips() -> None:
    client = _client(FakeRunner(rows=ROWS, dry_run_bytes=10**12), max_scan_bytes=1000)
    with pytest.raises(ScanBudgetExceededError):
        build_collections(client, "SK011", RANGE, use_cache=False)


def test_exclude_backdated_requires_closing_month() -> None:
    with pytest.raises(ValueError, match="closing_month"):
        build_collections(
            _client(FakeRunner(rows=())), "SK011", RANGE, exclude_backdated=True, use_cache=False
        )


def test_exclude_backdated_binds_closing_month_param() -> None:
    runner = FakeRunner(rows=ROWS)
    build_collections(
        _client(runner),
        "SK011",
        RANGE,
        exclude_backdated=True,
        closing_month=date(2026, 6, 1),
        use_cache=False,
    )
    bound = {p.name for _, params, dry in runner.calls if not dry for p in params}
    assert "closing_month" in bound


def test_cache_roundtrip_preserves_decimal(tmp_path: Path) -> None:
    cells = (
        CollectionsCell(
            company_id="SK011",
            cohort_month=date(2026, 6, 1),
            period_month=date(2026, 6, 1),
            collections=Decimal("120000.123456"),
        ),
    )
    matrix = CollectionsMatrix(
        company_id="SK011",
        cells=cells,
        meta=CollectionsMeta(source="payments", from_cache=False, scanned_bytes=1),
    )
    key = cache.cache_key("SK011", RANGE[0], RANGE[1], exclude_backdated=False)
    cache.save(tmp_path, key, matrix)
    loaded = cache.load(tmp_path, key, "SK011")
    assert loaded is not None
    assert loaded.cells[0].collections == Decimal("120000.123456")  # decimal128 lossless at 6 dp
    assert loaded.meta.from_cache
    assert loaded.meta.source == "cache"


def test_build_uses_cache_on_second_call(tmp_path: Path) -> None:
    runner = FakeRunner(rows=ROWS)
    client = _client(runner)
    first = build_collections(client, "SK011", RANGE, cache_dir=tmp_path)
    assert not first.meta.from_cache
    n_calls_after_first = len(runner.calls)
    second = build_collections(client, "SK011", RANGE, cache_dir=tmp_path)
    assert second.meta.from_cache
    assert len(runner.calls) == n_calls_after_first  # no new backend calls
    assert second.cohort_totals() == first.cohort_totals()


def test_cache_key_includes_closing_month() -> None:
    a = cache.cache_key(
        "SK011", RANGE[0], RANGE[1], exclude_backdated=True, closing_month=date(2026, 6, 1)
    )
    b = cache.cache_key(
        "SK011", RANGE[0], RANGE[1], exclude_backdated=True, closing_month=date(2026, 7, 1)
    )
    assert a != b  # different closing_month must not collide on one extract


def test_cohort_index_maps_row() -> None:
    row: dict[str, object] = {
        "payment_rows": 4995,
        "customers": 813,
        "cohort_mismatch_rows": 2752,
        "backdated_customers": 751,
        "earliest_first_period": date(2024, 1, 1),
        "latest_first_period": date(2026, 3, 1),
    }
    index = cohort_index(_client(FakeRunner(rows=(row,))), "SK014", closing_month=date(2026, 1, 1))
    assert index.payment_rows == 4995
    assert index.customers == 813
    assert index.cohort_mismatch_rows == 2752
    assert index.backdated_customers == 751
    assert index.earliest_first_period == date(2024, 1, 1)
    assert index.latest_first_period == date(2026, 3, 1)


def test_cohort_index_empty_raises() -> None:
    with pytest.raises(ValueError, match="no payments"):
        cohort_index(_client(FakeRunner(rows=())), "SK014", closing_month=date(2026, 1, 1))
