"""Accounting value objects: books, amortization rows/schedules, consolidation, summary.

Money is exact ``Decimal``; nothing is rounded until presentation (CLAUDE.md). Models reuse the
engine's frozen/strict base so a ``float`` where a ``Decimal`` is expected is rejected.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from skalar_capital_mechanics import DayCount
from skalar_capital_mechanics.models import FrozenModel, Money, Pct


class BookKind(StrEnum):
    """Which EIR form a book takes (foundation §4)."""

    DEBT_GIVEN = "debt_given"  # asset; outstanding <= 0 (Skalar is owed)
    DEBT_TAKEN = "debt_taken"  # liability; outstanding >= 0 (Skalar owes)


class BookFlow(FrozenModel):
    """One dated period of a book's cash flows over the (consolidated) date grid.

    ``inflow >= 0`` (sharing for debt given; PFA/FA for debt taken). ``outflow <= 0`` (funding +
    signed adjustments for debt given; the *uncapped* remittance basis for debt taken — the EIR
    applies the contractual cap). A pure-accrual period carries zero flows.
    """

    date: date
    inflow: Money
    outflow: Money


class Book(FrozenModel):
    """One loan/vintage's inputs for the EIR engine."""

    name: str
    kind: BookKind
    rate: Pct  # effective annual EIR rate (debt given 0.25, debt taken 0.16)
    day_count: DayCount
    flows: tuple[BookFlow, ...]


class AmortizationRow(FrozenModel):
    """One amortized period: cash flows, accrued interest, principal/interest split, balance."""

    date: date
    inflow: Money
    outflow: Money  # the realised (capped, for debt taken) outflow
    accrued_interest: Money
    principal: Money
    interest: Money  # Revenue (debt given, >= 0) / Cost of Capital (debt taken, <= 0)
    outstanding: Money

    @property
    def net(self) -> Decimal:
        return self.inflow + self.outflow


class AmortizationSchedule(FrozenModel):
    """A single book's amortization plus its XIRR (``None`` when XIRR does not converge)."""

    name: str
    kind: BookKind
    rows: tuple[AmortizationRow, ...]
    xirr: float | None

    @property
    def dates(self) -> tuple[date, ...]:
        return tuple(r.date for r in self.rows)


class ConsolidatedBook(FrozenModel):
    """Element-wise sum of per-loan schedules onto their shared date grid (foundation §4)."""

    kind: BookKind
    rows: tuple[AmortizationRow, ...]
    xirr: float | None

    @property
    def dates(self) -> tuple[date, ...]:
        return tuple(r.date for r in self.rows)


class BookReport(FrozenModel):
    """A book's per-loan schedules plus their consolidation, for reporting/Excel output."""

    kind: BookKind
    title: str  # sheet title, e.g. "Debt Given By Skalar Cohort Led"
    rate: Pct
    loans: tuple[AmortizationSchedule, ...]
    consolidated: ConsolidatedBook


class SummaryColumn(FrozenModel):
    """One period of the Summary sheet (foundation §4)."""

    date_given: date
    date_taken: date
    revenue: Money  # Sigma debt-given interest
    cost_of_capital: Money  # Sigma debt-taken interest (<= 0)
    outstanding_lended: Money  # debt-given outstanding (<= 0)
    outstanding_borrowed: Money  # debt-taken outstanding (>= 0)
    cash_impact: Money  # Skalar Period Cash Impact
    check: Money  # net_given + net_taken - cash_impact ~ 0


class AccountingSummary(FrozenModel):
    """The Summary sheet: one :class:`SummaryColumn` per period."""

    columns: tuple[SummaryColumn, ...]

    @property
    def revenue_total(self) -> Decimal:
        return sum((c.revenue for c in self.columns), Decimal(0))

    @property
    def cost_of_capital_total(self) -> Decimal:
        return sum((c.cost_of_capital for c in self.columns), Decimal(0))

    @property
    def max_abs_check(self) -> Decimal:
        return max((abs(c.check) for c in self.columns), default=Decimal(0))


__all__ = [
    "AccountingSummary",
    "AmortizationRow",
    "AmortizationSchedule",
    "Book",
    "BookFlow",
    "BookKind",
    "BookReport",
    "ConsolidatedBook",
    "DayCount",
    "Money",
    "SummaryColumn",
]
