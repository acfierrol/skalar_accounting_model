"""Summary sheet (foundation §4): Revenue, Cost of Capital, outstanding, period cash impact.

The two consolidated books are aligned **by column position** (the workbook's debt-given and
debt-taken grids share a period count but differ on the first date — GC funds on its own trade
date). Per period:

    revenue              = consolidated debt-given interest      (Revenue)
    cost_of_capital      = consolidated debt-taken interest      (COGS, <= 0)
    outstanding_lended   = consolidated debt-given outstanding   (<= 0)
    outstanding_borrowed = consolidated debt-taken outstanding   (>= 0)
    cash_impact[0]       = sum(revenue, cogs, out_lended, out_borrowed)
    cash_impact[i>0]     = sum(revenue, cogs, out_lended, out_borrowed)
                           - (prior out_lended + prior out_borrowed)
    check                = net_given + net_taken - cash_impact   (~ 0)
"""

from __future__ import annotations

from decimal import Decimal

from .models import AccountingSummary, BookKind, ConsolidatedBook, SummaryColumn


def build_summary(debt_given: ConsolidatedBook, debt_taken: ConsolidatedBook) -> AccountingSummary:
    """Build the Summary from the two consolidated books, aligned by period position."""
    if debt_given.kind is not BookKind.DEBT_GIVEN:
        raise ValueError(f"first book must be debt given, got {debt_given.kind}")
    if debt_taken.kind is not BookKind.DEBT_TAKEN:
        raise ValueError(f"second book must be debt taken, got {debt_taken.kind}")
    if len(debt_given.rows) != len(debt_taken.rows):
        raise ValueError("debt-given and debt-taken books must have the same period count")

    columns: list[SummaryColumn] = []
    prior_outstanding = Decimal(0)
    for given, taken in zip(debt_given.rows, debt_taken.rows, strict=True):
        outstanding_total = given.outstanding + taken.outstanding
        period_total = given.interest + taken.interest + outstanding_total
        cash_impact = period_total if not columns else period_total - prior_outstanding
        check = given.net + taken.net - cash_impact
        columns.append(
            SummaryColumn(
                date_given=given.date,
                date_taken=taken.date,
                revenue=given.interest,
                cost_of_capital=taken.interest,
                outstanding_lended=given.outstanding,
                outstanding_borrowed=taken.outstanding,
                cash_impact=cash_impact,
                check=check,
            )
        )
        prior_outstanding = outstanding_total

    return AccountingSummary(columns=tuple(columns))
