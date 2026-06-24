"""Cash events, debt-taken derivation, and netting (foundation §6; Phase 4).

The engine's final output: per-vintage downstream cash events, the derived debt-taken
(upstream) events, the transacted-ledger view, and netting instructions — the series the
accounting layer consumes.
"""

from __future__ import annotations

from .debt_taken import DEFAULT_LEVERAGE, derive_debt_taken
from .downstream import build_downstream_cash_events, sharing_events_from_schedule
from .ledger import build_transacted_ledger
from .models import CashEvent, GCDates, NettingInstruction, TransactedLedgerRow
from .netting import build_netting

__all__ = [
    "DEFAULT_LEVERAGE",
    "CashEvent",
    "GCDates",
    "NettingInstruction",
    "TransactedLedgerRow",
    "build_downstream_cash_events",
    "build_netting",
    "build_transacted_ledger",
    "derive_debt_taken",
    "sharing_events_from_schedule",
]
