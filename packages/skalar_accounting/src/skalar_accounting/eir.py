"""Effective-interest (amortized-cost) engine (foundation §4), matched to the workbook.

Asset form (debt given, ``outstanding <= 0``) and liability form (debt taken,
``outstanding >= 0``). ``outstanding`` starts at 0; the first period's accrual is therefore 0.
Per period with prior balance ``O`` and day-count fraction ``f``:

    accrued = O * ((1+r)^f - 1)

Debt given:  principal = MIN(inflow + accrued, -O);  interest = inflow - principal;
             outstanding = O + principal + outflow.
Debt taken:  outflow  = MAX(remittance_basis, -O - accrued)  (the payoff-ceiling cap);
             principal = outflow + accrued;  interest = outflow - principal (= -accrued);
             outstanding = O + principal + inflow.
"""

from __future__ import annotations

from decimal import Decimal

from .daycount import year_fraction
from .models import AmortizationRow, AmortizationSchedule, Book, BookKind
from .xirr import xirr

_ONE = Decimal(1)
_ZERO = Decimal(0)


def amortize(book: Book) -> AmortizationSchedule:
    """Amortize one book's dated cash flows into principal/interest/outstanding + XIRR."""
    rate = book.rate
    rows: list[AmortizationRow] = []
    outstanding = _ZERO

    for index, flow in enumerate(book.flows):
        prev_date = book.flows[index - 1].date if index > 0 else flow.date
        fraction = year_fraction(book.day_count, prev_date, flow.date)
        accrued = outstanding * ((_ONE + rate) ** fraction - _ONE)

        if book.kind is BookKind.DEBT_GIVEN:
            principal = min(flow.inflow + accrued, -outstanding)
            interest = flow.inflow - principal
            outstanding = outstanding + principal + flow.outflow
            booked_outflow = flow.outflow
        else:  # DEBT_TAKEN
            payoff_cap = -outstanding - accrued  # = -(O * (1+r)^f); stops over-repayment
            booked_outflow = max(flow.outflow, payoff_cap)
            principal = booked_outflow + accrued
            interest = booked_outflow - principal
            outstanding = outstanding + principal + flow.inflow

        rows.append(
            AmortizationRow(
                date=flow.date,
                inflow=flow.inflow,
                outflow=booked_outflow,
                accrued_interest=accrued,
                principal=principal,
                interest=interest,
                outstanding=outstanding,
            )
        )

    net = [(r.date, r.net) for r in rows]
    return AmortizationSchedule(name=book.name, kind=book.kind, rows=tuple(rows), xirr=xirr(net))
