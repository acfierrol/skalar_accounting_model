"""Debt-taken (upstream) derivation from downstream events (foundation §6, KB §11).

GC funds a leverage fraction (default 0.95) of every downstream movement and is remitted the
same fraction of sharing. The legs (matching the workbook ``Debt Taken`` sheet):

* **PFA** (``PFA``) — GC's advance establishing the vintage = ``-leverage x funding`` (a
  downstream funding outflow becomes a positive GC inflow).
* **FA-up** (``FA_UP``) — GC's ratable share of a spend adjustment = ``leverage x adjustment``
  (signed passthrough; the workbook does *not* negate these, unlike the establishing PFA).
* **Remittance basis** (``REMIT``) — ``-leverage x downstream_sharing`` (<= 0). This is the
  *uncapped* intent; the contractual cap ``MAX(basis, -outstanding - accrued)`` depends on the
  EIR outstanding and the per-book rate, so it is applied during debt-taken amortization
  (Phase 5), not here. Documented deviation from the phase-4 prompt's literal wording.

Dates come from :class:`GCDates` (an input): the PFA settles on GC's funding date; remittances
and adjustment shares settle on their downstream dates in the current facility.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from ..models.enums import CashEventKind
from .models import CashEvent, GCDates

DEFAULT_LEVERAGE = Decimal("0.95")


def derive_debt_taken(
    events: Sequence[CashEvent],
    gc_dates: GCDates,
    leverage: Decimal = DEFAULT_LEVERAGE,
) -> list[CashEvent]:
    """Derive a vintage's debt-taken (upstream) cash events from its downstream events."""
    counterparty = "GC"
    derived: list[CashEvent] = []
    for e in events:
        if e.kind is CashEventKind.FUND_DOWN:
            kind, amount, when = CashEventKind.PFA, -leverage * e.amount, gc_dates.funding_date
        elif e.kind is CashEventKind.ADJUST:
            kind, amount, when = CashEventKind.FA_UP, leverage * e.amount, e.date
        elif e.kind is CashEventKind.SHARE_UP:
            kind, amount, when = CashEventKind.REMIT, -leverage * e.amount, e.date
        else:
            continue  # other downstream kinds have no upstream leg
        derived.append(
            CashEvent(
                company_id=e.company_id,
                cohort_month=e.cohort_month,
                date=when,
                amount=amount,
                kind=kind,
                counterparty=counterparty,
            )
        )
    derived.sort(key=lambda x: (x.date, x.kind.value))
    return derived
