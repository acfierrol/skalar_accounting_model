"""Sharing schedule: theoretical ``S``, recursive cap truncation to ``S~``, payback, closure.

Implements KB §7 (def:capdn): ``S = R x s``; ``S~`` is truncated recursively at
``return_cap = mu(payback) x F_eff``. A threshold breach raises the effective sharing rate
to 100% from the breach age on (KB §3.3, irreversible) — passed in by the caller, since the
threshold basis is Reference Income, never sharing.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from ..models.base import Pct
from ..models.parameters import DealParameters
from .models import ReferenceIncomeSeries, SharingCell, SharingSchedule
from .pricing import return_cap

_ZERO = Decimal(0)
_ONE = Decimal(1)
_HUNDRED_PCT: Pct = _ONE


def _effective_sharing_pct(base: Pct, age: int, breach_age: int | None) -> Pct:
    """Sharing rate for ``age`` — 100% from a breach on, otherwise the negotiated rate."""
    if breach_age is not None and age >= breach_age:
        return _HUNDRED_PCT
    return base


def payback_age(
    theoretical_sharing: Sequence[tuple[int, Decimal]], effective_funding: Decimal
) -> int | None:
    """First age (periods) at which cumulative theoretical sharing reaches ``F_eff`` (KB §7.1).

    Theoretical ``S`` equals collected ``S~`` until the cap binds, and the cap (``mu x F_eff``)
    is never below ``F_eff`` because ``mu >= 1`` is an enforced invariant of the pricing
    parameters (``MoicLadder`` rejects ``base_multiple < 1``). Payback is therefore always
    reached on or before the cap, so computing it from ``S`` matches the contractual ``S~``
    definition without the circular dependency of needing the cap to size the cap.
    """
    cumulative = _ZERO
    for age, sharing in sorted(theoretical_sharing):
        cumulative += sharing
        if cumulative >= effective_funding:
            return age
    return None


def sharing_schedule(
    ri: ReferenceIncomeSeries,
    params: DealParameters,
    *,
    effective_funding: Decimal,
    breach_age: int | None = None,
) -> SharingSchedule:
    """Build a cohort's sharing ledger from its Reference Income and effective funding.

    ``effective_funding`` is ``F_eff = F - A``; the caller sizes it (Phase 4 supplies the
    funding/adjustment). ``breach_age`` lifts the sharing rate to 100% from that age on.
    """
    ordered = sorted(ri.cells, key=lambda c: c.age)

    # Theoretical sharing S, with the breach-adjusted effective rate per age.
    theoretical: list[tuple[int, Decimal, Pct]] = []
    for cell in ordered:
        pct = _effective_sharing_pct(params.sharing_pct, cell.age, breach_age)
        theoretical.append((cell.age, cell.reference_income * pct, pct))

    paid_age = payback_age([(age, s) for age, s, _ in theoretical], effective_funding)
    l_op = params.windows.l_op_months
    paid_months = paid_age * l_op if paid_age is not None else None

    cap: Decimal | None = None
    moic: Decimal | None = None
    if paid_months is not None:
        cap = return_cap(params, effective_funding, paid_months)
        moic = cap / effective_funding if effective_funding > _ZERO else None

    cells: list[SharingCell] = []
    cumulative = _ZERO
    closure_age: int | None = None
    for (age, theoretical_s, pct), cell in zip(theoretical, ordered, strict=True):
        if cap is None:
            collected = theoretical_s
        else:
            remaining = max(_ZERO, cap - cumulative)
            collected = min(theoretical_s, remaining)
        cumulative += collected
        if cap is not None and closure_age is None and cumulative >= cap:
            closure_age = age
        cells.append(
            SharingCell(
                age=age,
                period_month=cell.period_month,
                reference_income=cell.reference_income,
                sharing_pct=pct,
                theoretical_sharing=theoretical_s,
                collected_sharing=collected,
                cumulative_collected=cumulative,
            )
        )

    return SharingSchedule(
        company_id=ri.company_id,
        cohort_month=ri.cohort_month,
        effective_funding=effective_funding,
        payback_age=paid_age,
        payback_months=paid_months,
        moic=moic,
        return_cap=cap,
        closure_age=closure_age,
        cells=tuple(cells),
    )
