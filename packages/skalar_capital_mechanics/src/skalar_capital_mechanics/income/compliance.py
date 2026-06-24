"""Funding compliance: per-period cap, commitment cap, deemed-minimum floor (KB §3.2 / §9.3).

Findings are *reported*, never raised — a deal can be out of compliance and still need its
numbers booked. Three checks per the KB:

* **Per-period cap** ``F(d,n) <= min(dollar_cap, growth_cap)`` (KB §9.3). The growth leg caps
  the funding Skalar is *obligated* to advance at the elected rate against spend that grew at
  most ``growth_cap_pct`` over the prior period; a larger jump needs consent.
* **Commitment cap** cumulative ``F(d,n) <= commitment_amount`` (KB §9.3, def:fdown).
* **Deemed minimum** if a request falls below ``deemed_minimum_pct x actual_sm_spend`` the
  company is *deemed* to have received that floor and sharing attaches accordingly
  (def:deemedmin); the default floor rate is the negotiated funding rate (KB §3.2 param 15).
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from ..models.base import Pct
from ..models.parameters import DealParameters
from .models import (
    ComplianceReport,
    ComplianceViolation,
    ComplianceViolationKind,
    FundingRequest,
)

_ONE = Decimal(1)


def check_compliance(
    requests: Sequence[FundingRequest],
    params: DealParameters,
    *,
    deemed_minimum_pct: Pct | None = None,
) -> ComplianceReport:
    """Audit a deal's funding history against its caps and floor (KB §9.3).

    ``deemed_minimum_pct`` defaults to the negotiated ``funding_pct`` (def:deemedmin). Periods
    are processed in calendar order so the growth leg and cumulative commitment are exact.
    """
    floor_pct = deemed_minimum_pct if deemed_minimum_pct is not None else params.funding_pct
    dollar_cap = params.per_period_cap.dollar_cap
    growth_pct = params.per_period_cap.growth_cap_pct
    commitment = params.commitment_amount

    violations: list[ComplianceViolation] = []
    cumulative_funding = Decimal(0)
    prior_spend: Decimal | None = None

    for req in sorted(requests, key=lambda r: r.period_month):
        # Per-period cap = min(dollar leg, growth leg). The growth leg needs a prior period.
        if prior_spend is None:
            cap = dollar_cap
            leg = "dollar"
        else:
            growth_leg = params.funding_pct * prior_spend * (_ONE + growth_pct)
            cap = min(dollar_cap, growth_leg)
            leg = "dollar" if dollar_cap <= growth_leg else "growth"
        if req.requested_funding > cap:
            violations.append(
                ComplianceViolation(
                    kind=ComplianceViolationKind.PER_PERIOD_CAP,
                    period_month=req.period_month,
                    requested=req.requested_funding,
                    limit=cap,
                    detail=f"funding exceeds the {leg} cap",
                )
            )

        cumulative_funding += req.requested_funding
        if cumulative_funding > commitment:
            violations.append(
                ComplianceViolation(
                    kind=ComplianceViolationKind.COMMITMENT_CAP,
                    period_month=req.period_month,
                    requested=cumulative_funding,
                    limit=commitment,
                    detail="cumulative funding exceeds the commitment amount",
                )
            )

        deemed_floor = floor_pct * req.actual_spend
        if req.requested_funding < deemed_floor:
            violations.append(
                ComplianceViolation(
                    kind=ComplianceViolationKind.DEEMED_MINIMUM,
                    period_month=req.period_month,
                    requested=req.requested_funding,
                    limit=deemed_floor,
                    detail="request below deemed minimum; sharing attaches at the floor",
                )
            )

        prior_spend = req.actual_spend

    return ComplianceReport(company_id=params.company_id, violations=tuple(violations))
