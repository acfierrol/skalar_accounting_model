"""Reference Income projection: R = collections x margin, age alignment, cohort filtering."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pytest

from skalar_capital_mechanics import (
    CollectionsCell,
    CollectionsMatrix,
    CollectionsMeta,
    DealParameters,
    SettlementWindows,
    reference_income,
)

JUNE_2026 = date(2026, 6, 1)


def _matrix(*cells: CollectionsCell, company_id: str = "SK011") -> CollectionsMatrix:
    return CollectionsMatrix(
        company_id=company_id,
        cells=cells,
        meta=CollectionsMeta(source="cache", from_cache=True, scanned_bytes=0),
    )


def _cell(period_month: date, amount: str, *, cohort: date = JUNE_2026) -> CollectionsCell:
    return CollectionsCell(
        company_id="SK011", cohort_month=cohort, period_month=period_month,
        collections=Decimal(amount),
    )


def test_margin_applied_and_sorted_by_age(
    make_params: Callable[..., DealParameters],
    make_matrix: Callable[..., CollectionsMatrix],
) -> None:
    matrix = make_matrix([Decimal("100"), Decimal("80")])
    ri = reference_income(matrix, JUNE_2026, make_params())
    assert [c.age for c in ri.cells] == [0, 1]
    assert ri.cells[0].reference_income == Decimal("45.00")  # 100 x 0.45
    assert ri.cells[1].reference_income == Decimal("36.00")  # 80 x 0.45
    assert ri.total() == Decimal("81.00")
    assert ri.cumulative_at(0) == Decimal("45.00")


def test_negative_collections_propagate_as_refunds(
    make_params: Callable[..., DealParameters],
    make_matrix: Callable[..., CollectionsMatrix],
) -> None:
    ri = reference_income(make_matrix([Decimal("100"), Decimal("-20")]), JUNE_2026, make_params())
    assert ri.cells[1].reference_income == Decimal("-9.00")


def test_only_the_named_cohort_is_projected(
    make_params: Callable[..., DealParameters],
) -> None:
    other = date(2026, 7, 1)
    matrix = _matrix(
        _cell(JUNE_2026, "100"),
        _cell(other, "999", cohort=other),
    )
    ri = reference_income(matrix, JUNE_2026, make_params())
    assert len(ri.cells) == 1
    assert ri.cells[0].cohort_month == JUNE_2026


def test_quarterly_cadence_aggregates_calendar_months(
    make_params: Callable[..., DealParameters],
) -> None:
    # L_op = 3: Jun/Jul/Aug collapse into S&M period 0, Sep into period 1 (KB §2, def:period).
    params = make_params().model_copy(
        update={"windows": SettlementWindows(l_op_months=3, lambda_=2)}
    )
    matrix = _matrix(
        _cell(date(2026, 6, 1), "100"),
        _cell(date(2026, 7, 1), "50"),
        _cell(date(2026, 8, 1), "25"),
        _cell(date(2026, 9, 1), "80"),
    )
    ri = reference_income(matrix, JUNE_2026, params)
    assert [c.age for c in ri.cells] == [0, 1]
    assert ri.cells[0].collections == Decimal("175")  # 100 + 50 + 25
    assert ri.cells[0].reference_income == Decimal("78.75")  # 175 x 0.45
    assert ri.cells[0].period_month == JUNE_2026
    assert ri.cells[1].collections == Decimal("80")
    assert ri.cells[1].period_month == date(2026, 9, 1)


def test_period_before_cohort_raises(make_params: Callable[..., DealParameters]) -> None:
    matrix = _matrix(_cell(date(2026, 5, 1), "100"))
    with pytest.raises(ValueError, match="precedes cohort"):
        reference_income(matrix, JUNE_2026, make_params())


def test_mismatched_company_raises(make_params: Callable[..., DealParameters]) -> None:
    matrix = _matrix(_cell(JUNE_2026, "100"), company_id="SK999")
    with pytest.raises(ValueError, match="SK999"):
        reference_income(matrix, JUNE_2026, make_params())
