"""Arrange decomposed cells into a cohort x calendar-period run-off triangle."""

from __future__ import annotations

from collections.abc import Sequence

from skalar_capital_mechanics.models import Money

from .models import CohortPeriodMatrix, WaterfallCell


def build_cohort_period_matrix(
    cells: Sequence[WaterfallCell], field: str = "collected_sharing"
) -> CohortPeriodMatrix:
    """Lay ``field`` as a cohort (row) x period (col) grid; ``None`` in the empty corner."""
    cohorts = sorted({c.cohort_month for c in cells})
    periods = sorted({c.period_month for c in cells})
    by_key = {(c.cohort_month, c.period_month): c.field(field) for c in cells}
    values: tuple[tuple[Money | None, ...], ...] = tuple(
        tuple(by_key.get((cohort, period)) for period in periods) for cohort in cohorts
    )
    return CohortPeriodMatrix(
        field=field, cohorts=tuple(cohorts), periods=tuple(periods), values=values
    )
