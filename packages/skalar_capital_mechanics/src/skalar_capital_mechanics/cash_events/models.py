"""Cash-event value objects (foundation §3, §6): the engine's final output.

A :class:`CashEvent` is a typed, dated, signed entitlement/obligation (Capital Mechanics
def:component). Engine-wide sign convention: **inflow to Skalar > 0, outflow < 0**. These are
the three series the accounting layer consumes.
"""

from __future__ import annotations

from datetime import date

from ..models.base import FrozenModel, Money
from ..models.enums import CashEventKind


class CashEvent(FrozenModel):
    """One signed, dated cash movement for a vintage (foundation §3)."""

    company_id: str
    cohort_month: date
    date: date
    amount: Money  # inflow to Skalar > 0, outflow < 0
    kind: CashEventKind
    counterparty: str


class TransactedLedgerRow(FrozenModel):
    """A row of the workbook ``Structure`` ledger: signed amount + provenance."""

    amount: Money  # neg = from Skalar, pos = to Skalar
    loan_cohort: date
    counterparty: str
    date: date
    type: str  # "Investment Request" | "Under/Over" | "Payment Due"


class GCDates(FrozenModel):
    """Explicit GC (upstream) transaction dates for a vintage — an input, never derived.

    The senior partner funds the PFA on its own trade date (e.g. 2026-06-05, ahead of the
    downstream disbursement). In the current facility GC remittance dates coincide with the
    downstream settlement dates, so only the funding date is carried here; ``remittance_dates``
    overrides them when a future facility diverges.
    """

    cohort_month: date
    funding_date: date
    remittance_dates: tuple[date, ...] = ()


class NettingInstruction(FrozenModel):
    """One wire: the signed net of all components a counterparty settles on a date (KB §5.2)."""

    counterparty: str
    date: date
    net_amount: Money  # > 0 Skalar receives, < 0 Skalar pays
    event_count: int

    @property
    def direction(self) -> str:
        if self.net_amount > 0:
            return "receive"
        if self.net_amount < 0:
            return "pay"
        return "none"  # a fully-offsetting wire has no direction
