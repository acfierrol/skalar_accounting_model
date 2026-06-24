"""Day-count conventions for EIR accrual (foundation §4), matched to the workbook.

* ``MONTH_DAYS_365`` (debt given): calendar days in the *current* period's month / 365 —
  the workbook's ``DAY(EOMONTH(date,0))/365``.
* ``ACTUAL_365`` (debt taken): actual days between consecutive dates / 365.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal

from skalar_capital_mechanics import DayCount

_DAYS_PER_YEAR = Decimal(365)


def year_fraction(day_count: DayCount, prev: date, cur: date) -> Decimal:
    """Year fraction ``f`` for the accrual ``(1+r)^f - 1`` over the period ending ``cur``."""
    if day_count is DayCount.MONTH_DAYS_365:
        return Decimal(monthrange(cur.year, cur.month)[1]) / _DAYS_PER_YEAR
    if day_count is DayCount.ACTUAL_365:
        return Decimal((cur - prev).days) / _DAYS_PER_YEAR
    raise ValueError(f"unsupported day count: {day_count!r}")
