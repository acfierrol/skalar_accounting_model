"""Value objects for the collections->sharing waterfall and the cohort/time matrix.

Money is exact ``Decimal`` (the engine's convention); rounding is a plotting concern. Reuses the
engine's frozen/strict base so a ``float`` where a ``Decimal`` is expected is rejected.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from skalar_capital_mechanics.models import FrozenModel, Money


class WaterfallCell(FrozenModel):
    """One ``(cohort, period)`` cell decomposed end to end (KB §8 flow chain + §11 split).

    ``collections`` splits into ``company_retained`` (everything Skalar does not collect) plus the
    effective Skalar share ``collected_sharing`` (= S~); that share splits again into the GC
    remittance and what Skalar keeps. So ``collections = company_retained + gc_share +
    skalar_retained`` and ``collected_sharing = gc_share + skalar_retained``.
    """

    cohort_month: date
    period_month: date
    age: int  # period - cohort, in S&M periods
    collections: Money
    reference_income: Money  # collections x margin
    theoretical_sharing: Money  # R x sharing_pct (= S)
    collected_sharing: Money  # S~ (cap-truncated)
    gc_share: Money  # remitted to GC (<= leverage x S~, capped at the GC entitlement)
    skalar_retained: Money  # S~ - gc_share
    company_retained: Money  # collections - S~

    @property
    def above_cap(self) -> Decimal:
        """Theoretical sharing lost to the return cap (returns to the company)."""
        return self.theoretical_sharing - self.collected_sharing

    def field(self, name: str) -> Decimal:
        value = getattr(self, name)
        if not isinstance(value, Decimal):
            raise ValueError(f"{name!r} is not a numeric WaterfallCell field")
        return value


class StepKind(StrEnum):
    """A waterfall bar: an absolute milestone total, or a signed reduction between milestones."""

    TOTAL = "total"  # drawn from the baseline (Collections, Reference Income, S~, Skalar retained)
    DELTA = "delta"  # floating reduction connecting the prior level to the next


class WaterfallStep(FrozenModel):
    """One bar of the collections->retained waterfall."""

    label: str
    value: Money  # TOTAL: the absolute level; DELTA: the signed change (reductions are < 0)
    kind: StepKind


class CohortPeriodMatrix(FrozenModel):
    """A cohort (row) x calendar-period (col) grid of one decomposed field — a run-off triangle.

    ``values[r][c]`` is the field for cohort ``cohorts[r]`` in period ``periods[c]``, or ``None``
    where the period precedes the cohort (the empty corner). Constant cohort age runs along the
    diagonals; the populated region is a triangle.
    """

    field: str
    cohorts: tuple[date, ...]  # row labels, ascending
    periods: tuple[date, ...]  # column labels, ascending
    values: tuple[tuple[Money | None, ...], ...]

    @property
    def shape(self) -> tuple[int, int]:
        return (len(self.cohorts), len(self.periods))

    def age_at(self, row: int, col: int) -> int:
        cohort, period = self.cohorts[row], self.periods[col]
        return (period.year - cohort.year) * 12 + (period.month - cohort.month)
