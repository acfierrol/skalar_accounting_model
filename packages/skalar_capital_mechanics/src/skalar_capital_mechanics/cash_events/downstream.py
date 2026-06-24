"""Downstream cash-event construction (foundation §6).

Assembles a vintage's downstream events from Phase 1-3 outputs: the funding outflow
(``FUND_DOWN``), the capped sharing inflows (``SHARE_UP``, from the Phase-3 sharing schedule),
and any spend-reconciliation ``ADJUST`` events. Sign convention: inflow > 0, outflow < 0.

Dating is supplied by the caller (the settlement calendar / IR dates resolved upstream); this
function is the pure assembly step, so the golden reconciliation can feed the workbook's exact
dates without re-deriving them here.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from ..income.models import SharingSchedule
from ..models.enums import CashEventKind
from .models import CashEvent

_ZERO = Decimal(0)


def build_downstream_cash_events(
    *,
    company_id: str,
    cohort_month: date,
    counterparty: str,
    funding_amount: Decimal,
    funding_date: date,
    sharing: Sequence[tuple[date, Decimal]],
    adjustments: Sequence[tuple[date, Decimal]] = (),
) -> list[CashEvent]:
    """Build one vintage's downstream cash events, ordered by date.

    ``funding_amount`` is the disbursed Investment Amount (passed as a positive magnitude or a
    signed outflow; recorded as an outflow ``< 0``). ``sharing`` are ``(date, collected S~)``
    inflows (the Phase-3 schedule, already cap-truncated). ``adjustments`` are signed
    ``(date, A)`` spend reconciliations settled standalone (under-spend refund ``> 0`` inflow,
    over-spend top-up ``< 0`` outflow).
    """
    outflow = -abs(funding_amount)
    events = [
        CashEvent(
            company_id=company_id,
            cohort_month=cohort_month,
            date=funding_date,
            amount=outflow,
            kind=CashEventKind.FUND_DOWN,
            counterparty=counterparty,
        )
    ]
    events.extend(
        CashEvent(
            company_id=company_id,
            cohort_month=cohort_month,
            date=when,
            amount=amount,
            kind=CashEventKind.SHARE_UP,
            counterparty=counterparty,
        )
        for when, amount in sharing
        if amount != _ZERO
    )
    events.extend(
        CashEvent(
            company_id=company_id,
            cohort_month=cohort_month,
            date=when,
            amount=amount,
            kind=CashEventKind.ADJUST,
            counterparty=counterparty,
        )
        for when, amount in adjustments
        if amount != _ZERO
    )
    events.sort(key=lambda e: (e.date, e.kind.value))
    return events


def sharing_events_from_schedule(
    schedule: SharingSchedule, dates: Sequence[date]
) -> list[tuple[date, Decimal]]:
    """Pair a sharing schedule's collected ``S~`` (by age) with settlement dates for the cells.

    ``dates[k]`` dates the cell at index ``k`` (the settlement calendar maps cohort age to a
    settlement date upstream). Lengths must match.
    """
    if len(dates) != len(schedule.cells):
        raise ValueError(
            f"need one date per sharing cell: {len(dates)} dates, {len(schedule.cells)} cells"
        )
    return [
        (when, cell.collected_sharing)
        for when, cell in zip(dates, schedule.cells, strict=True)
    ]
