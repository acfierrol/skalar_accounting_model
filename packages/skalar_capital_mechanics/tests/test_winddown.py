"""Downstream wind-down: trigger threshold and proportional payment (KB §9.2)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from skalar_capital_mechanics import WindDownSpec, winddown_payment

JUNE_2026 = date(2026, 6, 1)
SPEC = WindDownSpec(trailing_months=3, threshold_pct=Decimal("0.05"))


def test_triggered_payment_is_exposure_times_proportion() -> None:
    result = winddown_payment(
        SPEC,
        cohort_month=JUNE_2026,
        return_cap=Decimal("100"),
        cumulative_collected=Decimal("40"),
        ref_income_cancelled_3m=Decimal("10"),
        ref_income_total_3m=Decimal("100"),
    )
    assert result.triggered  # 10% affected > 5% threshold
    assert result.affected_proportion == Decimal("0.10")
    assert result.outstanding_exposure == Decimal("60")  # cap 100 - collected 40
    assert result.payment == Decimal("6.00")  # 60 x 0.10


def test_below_threshold_is_not_triggered() -> None:
    result = winddown_payment(
        SPEC,
        cohort_month=JUNE_2026,
        return_cap=Decimal("100"),
        cumulative_collected=Decimal("40"),
        ref_income_cancelled_3m=Decimal("3"),
        ref_income_total_3m=Decimal("100"),
    )
    assert not result.triggered  # 3% affected <= 5% threshold
    assert result.payment == Decimal(0)


def test_zero_trailing_income_is_safe() -> None:
    result = winddown_payment(
        SPEC,
        cohort_month=JUNE_2026,
        return_cap=Decimal("100"),
        cumulative_collected=Decimal("40"),
        ref_income_cancelled_3m=Decimal("0"),
        ref_income_total_3m=Decimal("0"),
    )
    assert result.affected_proportion == Decimal(0)
    assert not result.triggered
    assert result.payment == Decimal(0)
