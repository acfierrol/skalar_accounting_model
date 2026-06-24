"""Netting builder (KB §5.2 / def:netprinciple).

On any date, for a counterparty, sum every component that falls due that date — inflows ``> 0``,
outflows ``< 0`` — and emit one :class:`NettingInstruction`; the sign of the total sets the
direction. Only components that **actually share a date** are aggregated (the workbook's
per-period nets are the ideal matched case, not routine operation), so this groups by the exact
``(counterparty, date)`` and never coalesces across dates.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from .models import CashEvent, NettingInstruction


def build_netting(events: Sequence[CashEvent]) -> list[NettingInstruction]:
    """Collapse same-date, same-counterparty events into one signed wire each."""
    nets: dict[tuple[str, date], Decimal] = {}
    counts: dict[tuple[str, date], int] = {}
    for e in events:
        key = (e.counterparty, e.date)
        nets[key] = nets.get(key, Decimal(0)) + e.amount
        counts[key] = counts.get(key, 0) + 1
    instructions = [
        NettingInstruction(
            counterparty=counterparty,
            date=when,
            net_amount=nets[(counterparty, when)],
            event_count=counts[(counterparty, when)],
        )
        for counterparty, when in nets
    ]
    instructions.sort(key=lambda i: (i.date, i.counterparty))
    return instructions
