"""Collections matrix value objects (KB §2): collections(company, cohort, period)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from ..models.base import FrozenModel, Money

# Collections come from BigQuery FLOAT64 sums, whose decimal scale is unbounded float
# noise. Normalise to 6 dp (micro-dollar) at the IO edge: well beyond cent precision,
# below float noise, and a fixed scale the parquet cache can store losslessly.
MONEY_QUANTUM = Decimal("0.000001")


def quantize_money(value: Decimal) -> Decimal:
    """Round a money value to the canonical 6-dp scale."""
    return value.quantize(MONEY_QUANTUM)


class CollectionsCell(FrozenModel):
    """One ``(cohort_month, period_month)`` collections amount for a deal."""

    company_id: str
    cohort_month: date
    period_month: date
    collections: Money


class CollectionsMeta(FrozenModel):
    """Provenance + cost for a collections build."""

    source: Literal["payments", "cache"]
    from_cache: bool
    scanned_bytes: int
    exclude_backdated: bool = False


class CollectionsMatrix(FrozenModel):
    """The full collections matrix for one deal."""

    company_id: str
    cells: tuple[CollectionsCell, ...]
    meta: CollectionsMeta

    def cell(self, cohort_month: date, period_month: date) -> Decimal | None:
        """Collections for one ``(cohort, period)`` cell, or ``None`` if absent."""
        for c in self.cells:
            if c.cohort_month == cohort_month and c.period_month == period_month:
                return c.collections
        return None

    def cohort_totals(self) -> dict[date, Decimal]:
        """Total collections per cohort across all periods."""
        totals: dict[date, Decimal] = {}
        for c in self.cells:
            totals[c.cohort_month] = totals.get(c.cohort_month, Decimal(0)) + c.collections
        return totals

    def total(self) -> Decimal:
        """Grand total collections."""
        return sum((c.collections for c in self.cells), Decimal(0))


class CohortIndex(FrozenModel):
    """Cohort-assignment integrity summary for a deal (KB §2)."""

    company_id: str
    closing_month: date
    payment_rows: int
    customers: int
    cohort_mismatch_rows: int
    backdated_customers: int
    earliest_first_period: date | None
    latest_first_period: date | None
