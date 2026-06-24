"""Transacted-ledger view (workbook ``Structure`` sheet).

Flattens cash events into the ledger rows the workbook keeps per company: signed amount, loan
cohort, counterparty, date, and a coarse transaction ``type``.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..models.enums import CashEventKind
from .models import CashEvent, TransactedLedgerRow

_TYPE_BY_KIND: dict[CashEventKind, str] = {
    CashEventKind.FUND_DOWN: "Investment Request",
    CashEventKind.PFA: "Investment Request",
    CashEventKind.ADJUST: "Under/Over",
    CashEventKind.FA_UP: "Under/Over",
    CashEventKind.SHARE_UP: "Payment Due",
    CashEventKind.REMIT: "Payment Due",
    CashEventKind.WIND_DOWN: "Payment Due",
}


def build_transacted_ledger(events: Sequence[CashEvent]) -> list[TransactedLedgerRow]:
    """Render cash events as ``Structure``-sheet ledger rows, ordered by date."""
    rows = [
        TransactedLedgerRow(
            amount=e.amount,
            loan_cohort=e.cohort_month,
            counterparty=e.counterparty,
            date=e.date,
            type=_TYPE_BY_KIND[e.kind],
        )
        for e in events
    ]
    rows.sort(key=lambda r: (r.date, r.counterparty))
    return rows
