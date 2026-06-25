"""Spend builder + funding resolution (offline, faked runner)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest

from skalar_capital_mechanics import (
    DealParameters,
    ResolutionError,
    SpendCell,
    build_spend,
    resolve_funding,
    resolve_funding_series,
)
from skalar_data_access import BigQueryClient, ScalarParam, Settings
from skalar_data_access.client import RunResult

JUNE_2026 = date(2026, 6, 1)
JULY_2026 = date(2026, 7, 1)


@dataclass
class FakeRunner:
    rows: tuple[dict[str, object], ...] = ()

    def run(self, sql: str, params: object, *, dry_run: bool) -> RunResult:
        return RunResult(total_bytes_processed=0, rows=() if dry_run else self.rows)


def _row(cohort: date, **over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "company_id": "SK011", "cohort_month": cohort,
        "estimated_spend": None, "actual_spend": None,
        "estimated_gc_spend": None, "estimated_skalar_spend": None,
        "actual_gc_spend": None, "actual_skalar_spend": None,
    }
    base.update(over)
    return base


def _cell(cohort: date, **over: object) -> SpendCell:
    return SpendCell(**_row(cohort, **over))  # type: ignore[arg-type]


def test_build_spend_preserves_nulls_and_basis_fallback() -> None:
    runner = FakeRunner(
        rows=(_row(JUNE_2026, estimated_spend=200000.0, estimated_gc_spend=152000.0,
                   estimated_skalar_spend=8000.0),)
    )
    table = build_spend(BigQueryClient(Settings(), runner=runner), "SK011")
    cell = table.cell(JUNE_2026)
    assert cell is not None
    assert cell.estimated_spend == Decimal("200000.0")
    assert cell.actual_spend is None
    # Threshold denominator falls back to estimated while actual is unavailable (KB §3.3).
    assert cell.basis_spend == Decimal("200000.0")
    assert table.cell(JULY_2026) is None


def test_resolve_funding_uses_recorded_gc_split(
    make_params: Callable[..., DealParameters],
) -> None:
    # SK011 June 2026: the split is recorded -> F = gc + pool directly (workbook 152000 + 8000).
    cell = _cell(JUNE_2026, estimated_spend=Decimal("200000"),
                 estimated_gc_spend=Decimal("152000"), estimated_skalar_spend=Decimal("8000"))
    funding = resolve_funding(cell, make_params())
    assert funding.funding == Decimal("160000")
    assert funding.gc_advance == Decimal("152000")
    assert funding.skalar_pool == Decimal("8000")
    assert funding.basis_spend == Decimal("200000")


def test_resolve_funding_without_split_uses_funding_pct_and_leverage(
    make_params: Callable[..., DealParameters],
) -> None:
    # No split recorded: F = funding_pct x spend; GC/pool from the deal's leverage (0.95).
    cell = _cell(JUNE_2026, estimated_spend=Decimal("100000"), actual_spend=Decimal("100000"))
    funding = resolve_funding(cell, make_params())
    assert funding.funding == Decimal("80000")  # 0.80 x 100000
    assert funding.gc_advance == Decimal("76000")  # 0.95 x 80000
    assert funding.skalar_pool == Decimal("4000")  # 80000 - 76000
    assert funding.basis_spend == Decimal("100000")  # actual present


def test_resolve_funding_raises_without_any_spend(
    make_params: Callable[..., DealParameters],
) -> None:
    with pytest.raises(ResolutionError, match="no estimated or actual spend"):
        resolve_funding(_cell(JUNE_2026), make_params())


def test_resolve_funding_series_skips_cohorts_without_spend(
    make_params: Callable[..., DealParameters],
) -> None:
    runner = FakeRunner(rows=(_row(JUNE_2026, estimated_spend=100000.0, actual_spend=100000.0),))
    table = build_spend(BigQueryClient(Settings(), runner=runner), "SK011")
    fundings = resolve_funding_series(
        table, [(JUNE_2026, make_params()), (JULY_2026, make_params())]
    )
    assert [f.cohort_month for f in fundings] == [JUNE_2026]  # July has no spend row


def test_build_spend_with_date_range_renders() -> None:
    # Smoke: the date_range branch renders + runs without error.
    runner = FakeRunner(rows=(_row(JUNE_2026, actual_spend=123.0),))
    table = build_spend(
        BigQueryClient(Settings(), runner=runner), "SK011", date_range=(JUNE_2026, JULY_2026)
    )
    assert table.cell(JUNE_2026) is not None


def test_scalar_param_date_available() -> None:
    # Guards that the builder's date params construct (used in the date_range branch).
    assert ScalarParam.date("date_from", JUNE_2026) is not None
