"""Reference Income: ``R(d, k, i) = collections(d, k, i) x gross_margin(d)`` (KB §8, def:ridown).

Projects a cohort out of the Phase-2 collections matrix and applies the cohort's margin.
Margin is resolved per cohort (KB §3.2 param 3); a within-life schedule is a future seam.

The collections matrix buckets ``period_month`` by calendar month, while a cohort's age is
counted in S&M periods of ``L_op`` calendar months (KB §2, def:period). For ``L_op > 1`` every
calendar month inside an S&M period maps to the same age and its collections are aggregated
into that period's cell (``age = floor(months / L_op)``); for the monthly deals (``L_op = 1``)
this is one cell per calendar month.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ..collections import CollectionsMatrix
from ..models.parameters import DealParameters
from .models import ReferenceIncomeCell, ReferenceIncomeSeries


def _months_between(cohort_month: date, period_month: date) -> int:
    return (period_month.year - cohort_month.year) * 12 + (period_month.month - cohort_month.month)


def _month_plus(base: date, n: int) -> date:
    index = base.month - 1 + n
    return date(base.year + index // 12, index % 12 + 1, 1)


def reference_income(
    collections: CollectionsMatrix,
    cohort_month: date,
    params: DealParameters,
) -> ReferenceIncomeSeries:
    """Build the Reference Income series for one cohort from a collections matrix.

    Cells of other cohorts are ignored. Calendar months are bucketed into S&M periods (one
    cell per age, ordered by age); margin is applied to each period's aggregated collections.
    """
    if collections.company_id != params.company_id:
        raise ValueError(
            f"collections matrix is for {collections.company_id!r}, "
            f"params for {params.company_id!r}"
        )
    l_op = params.windows.l_op_months

    by_age: dict[int, Decimal] = {}
    for c in collections.cells:
        if c.cohort_month != cohort_month:
            continue
        months = _months_between(cohort_month, c.period_month)
        if months < 0:
            raise ValueError(
                f"period {c.period_month} precedes cohort {cohort_month} — not a member period"
            )
        age = months // l_op
        by_age[age] = by_age.get(age, Decimal(0)) + c.collections

    cells = tuple(
        ReferenceIncomeCell(
            company_id=params.company_id,
            cohort_month=cohort_month,
            period_month=_month_plus(cohort_month, age * l_op),
            age=age,
            collections=collected,
            reference_income=collected * params.margin,
        )
        for age, collected in sorted(by_age.items())
    )
    return ReferenceIncomeSeries(
        company_id=params.company_id,
        cohort_month=cohort_month,
        margin=params.margin,
        cells=cells,
    )
