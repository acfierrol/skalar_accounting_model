"""Value objects for income, sharing, return caps, thresholds, and compliance (KB §3, §7, §9).

All amounts are exact ``Decimal``; ratios that may exceed 1 (cumulative threshold ratio,
MOIC) are plain ``Decimal``, ratios bounded to ``[0, 1]`` are ``Pct``. Nothing is rounded —
rounding is a presentation concern (CLAUDE.md). Models are frozen, strict, extra-forbidding.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from ..models.base import FrozenModel, Money, Pct
from ..models.enums import (
    ThresholdBasis,
    ThresholdExit,
    ThresholdMechanic,
    ThresholdTiming,
)

# ---------------------------------------------------------------------------
# Reference income (KB §8: collections x gross_margin -> R)
# ---------------------------------------------------------------------------


class ReferenceIncomeCell(FrozenModel):
    """Reference Income for one ``(cohort, period)`` cell: ``R = collections x margin``."""

    company_id: str
    cohort_month: date
    period_month: date
    age: int  # cohort age in S&M periods = (period - cohort) / L_op
    collections: Money
    reference_income: Money


class ReferenceIncomeSeries(FrozenModel):
    """A cohort's Reference Income across its periods, ordered by age (KB §2)."""

    company_id: str
    cohort_month: date
    margin: Pct
    cells: tuple[ReferenceIncomeCell, ...]

    def total(self) -> Decimal:
        return sum((c.reference_income for c in self.cells), Decimal(0))

    def cumulative_at(self, age: int) -> Decimal:
        """Cumulative Reference Income through ``age`` (inclusive)."""
        return sum((c.reference_income for c in self.cells if c.age <= age), Decimal(0))


# ---------------------------------------------------------------------------
# Sharing + return cap (KB §7: S = R x s, truncated recursively at the cap)
# ---------------------------------------------------------------------------


class SharingCell(FrozenModel):
    """Sharing for one period: theoretical ``S`` and cap-truncated collected ``S~`` (KB §7.4)."""

    age: int
    period_month: date
    reference_income: Money
    sharing_pct: Pct  # effective rate for this age (100% from a breach onward)
    theoretical_sharing: Money  # S = R x sharing_pct
    collected_sharing: Money  # S~ (truncated at the cap)
    cumulative_collected: Money  # sum of S~ through this age


class SharingSchedule(FrozenModel):
    """A cohort's full sharing ledger: payback, MOIC, return cap, closure, per-period S~."""

    company_id: str
    cohort_month: date
    effective_funding: Money  # F_eff = F - A
    payback_age: int | None  # first age (periods) where cum S~ >= F_eff
    payback_months: int | None  # payback_age x L_op (the MOIC input)
    moic: Decimal | None  # mu (None until payback fixes it)
    return_cap: Money | None  # mu x F_eff (None until payback fixes it)
    closure_age: int | None  # first age where cum S~ >= return_cap
    cells: tuple[SharingCell, ...]

    def total_collected(self) -> Decimal:
        return sum((c.collected_sharing for c in self.cells), Decimal(0))

    @property
    def is_closed(self) -> bool:
        return self.closure_age is not None


# ---------------------------------------------------------------------------
# Threshold tests (KB §3.3 / def:basis, mech:one, mech:two, def:breach)
# ---------------------------------------------------------------------------


class ThresholdRequirementResult(FrozenModel):
    """One requirement evaluated against a cohort's ratios at a given age."""

    basis: ThresholdBasis
    required: Decimal
    actual: Decimal
    passed: bool


class ThresholdCheck(FrozenModel):
    """A cohort's threshold evaluation for one tested age."""

    age: int
    period_month: date
    cumulative_ratio: Decimal  # cum(m) = sum_{x<=m} R / origin_spend
    incremental_ratio: Decimal  # inc(m) = R(m) / origin_spend
    requirements: tuple[ThresholdRequirementResult, ...]
    passed: bool  # all requirements satisfied (vacuously true if none)


class ThresholdResult(FrozenModel):
    """The threshold outcome for one cohort (KB §3.3); ``breach`` is irreversible."""

    company_id: str
    cohort_month: date
    mechanic: ThresholdMechanic
    timing: ThresholdTiming
    exit: ThresholdExit
    checks: tuple[ThresholdCheck, ...]
    breached: bool
    breach_age: int | None
    breach_month: date | None
    exited: bool  # left testing under the exit election (e.g. reached breakeven)
    exit_age: int | None


# ---------------------------------------------------------------------------
# Funding compliance (KB §3.2 / §9.3)
# ---------------------------------------------------------------------------


class ComplianceViolationKind(StrEnum):
    """Typed funding-compliance findings (KB §9.3)."""

    PER_PERIOD_CAP = "per_period_cap"  # F(d,n) > min(dollar cap, growth cap)
    COMMITMENT_CAP = "commitment_cap"  # cumulative F(d,n) > commitment_amount
    DEEMED_MINIMUM = "deemed_minimum"  # request below the deemed-minimum floor


class FundingRequest(FrozenModel):
    """One period's Investment Request, with the period's actual S&M spend (KB §4)."""

    period_month: date
    requested_funding: Money  # F(d,n) the company requests
    actual_spend: Money  # Actual S&M Spend for the period


class ComplianceViolation(FrozenModel):
    """A single typed compliance finding; reported, never raised."""

    kind: ComplianceViolationKind
    period_month: date
    requested: Money  # the amount under test (period F, cumulative F, or request)
    limit: Money  # the binding cap / floor
    detail: str


class ComplianceReport(FrozenModel):
    """All compliance findings for a deal's funding history (KB §9.3)."""

    company_id: str
    violations: tuple[ComplianceViolation, ...]

    @property
    def ok(self) -> bool:
        """True iff no cap was breached (deemed-minimum findings are informational)."""
        return not any(
            v.kind is not ComplianceViolationKind.DEEMED_MINIMUM for v in self.violations
        )

    def of_kind(self, kind: ComplianceViolationKind) -> tuple[ComplianceViolation, ...]:
        return tuple(v for v in self.violations if v.kind is kind)


# ---------------------------------------------------------------------------
# Wind-down (KB §9.2 / def:winddown)
# ---------------------------------------------------------------------------


class WindDownAssessment(FrozenModel):
    """Downstream wind-down test for one open cohort (KB §9.2)."""

    cohort_month: date
    affected_proportion: Pct  # cancelled / total trailing-3M Reference Income
    outstanding_exposure: Money  # return_cap - cumulative S~
    triggered: bool  # affected_proportion > winddown threshold
    payment: Money  # exposure x affected_proportion when triggered, else 0
