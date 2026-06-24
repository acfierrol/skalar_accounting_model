"""Consolidation: element-wise sum of per-loan schedules onto the shared date grid (foundation §4).

Each loan is amortized over the deal's full column grid (zero flows where it is inactive — e.g.
a later loan accrues over earlier columns), so every schedule already spans the same dates and
the "union of dates" of foundation §4 *is* that shared grid. Consolidation therefore sums
column-by-column; outstanding consolidates as the sum of per-loan outstandings and the
consolidated XIRR is computed from the summed net flows. An identical grid is required (rather
than carry-forward-padding a ragged one) precisely because the engine guarantees pre-padded
schedules; a mismatch signals a construction bug, not a case to silently paper over.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from .models import AmortizationRow, AmortizationSchedule, ConsolidatedBook
from .xirr import xirr


def consolidate(schedules: Sequence[AmortizationSchedule]) -> ConsolidatedBook:
    """Sum per-loan schedules (same kind, same date grid) into one consolidated book."""
    if not schedules:
        raise ValueError("cannot consolidate an empty set of schedules")
    kinds = {s.kind for s in schedules}
    if len(kinds) != 1:
        raise ValueError(f"cannot consolidate mixed book kinds: {kinds}")
    kind = kinds.pop()

    grids = {s.dates for s in schedules}
    if len(grids) != 1:
        raise ValueError("schedules must share an identical date grid to consolidate")
    dates = grids.pop()

    rows: list[AmortizationRow] = []
    for position, when in enumerate(dates):
        cells = [s.rows[position] for s in schedules]
        rows.append(
            AmortizationRow(
                date=when,
                inflow=sum((c.inflow for c in cells), Decimal(0)),
                outflow=sum((c.outflow for c in cells), Decimal(0)),
                accrued_interest=sum((c.accrued_interest for c in cells), Decimal(0)),
                principal=sum((c.principal for c in cells), Decimal(0)),
                interest=sum((c.interest for c in cells), Decimal(0)),
                outstanding=sum((c.outstanding for c in cells), Decimal(0)),
            )
        )

    net = [(r.date, r.net) for r in rows]
    return ConsolidatedBook(kind=kind, rows=tuple(rows), xirr=xirr(net))
