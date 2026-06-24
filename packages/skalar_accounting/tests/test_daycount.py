"""Day-count conventions matched to the workbook."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from skalar_accounting import DayCount, year_fraction

_365 = Decimal(365)


@pytest.mark.parametrize(
    ("cur", "days"),
    [(date(2026, 6, 28), 30), (date(2026, 7, 28), 31), (date(2026, 2, 15), 28)],
)
def test_month_days_365_uses_current_month(cur: date, days: int) -> None:
    # Independent of prev; uses calendar days in cur's month (DAY(EOMONTH)).
    assert year_fraction(DayCount.MONTH_DAYS_365, date(2000, 1, 1), cur) == Decimal(days) / _365


@pytest.mark.parametrize(
    ("prev", "cur", "days"),
    [(date(2026, 6, 5), date(2026, 6, 28), 23), (date(2026, 6, 28), date(2026, 7, 28), 30)],
)
def test_actual_365_uses_days_between(prev: date, cur: date, days: int) -> None:
    assert year_fraction(DayCount.ACTUAL_365, prev, cur) == Decimal(days) / _365
