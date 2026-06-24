"""Threshold mechanics I & II and the per-cohort evaluator (KB §3.3 / def:basis, mech:*).

The test basis is fixed and non-electable (def:basis): numerator is the Reference Income the
cohort is *entitled* to (``collections x margin``), denominator is the origin period's Actual
S&M Spend. Received sharing as numerator and the funded amount as denominator are both
invalid and never used here.

Two mechanics ship as defaults; both read their grid from the deal's ``ThresholdSpec``:

* **I — linear ladder (KB company default).** Cumulative floors at the checkpoint ages, then
  a linear continuation at slope ``delta_pct`` beyond the last checkpoint. Surplus carries
  forward.
* **II — per-period incremental delta (electable; the executed SK011 election).** Cumulative
  floors at the checkpoints *plus* a floor on each period's own incremental ratio from
  ``delta_from_age`` on. No surplus credit.

CAUTION (def:elections / KB §3.3): where an executed agreement's incremental-delta wording
("incremental Reference Income … in any one of such S&M Periods", tested "on any date") reads
as Mechanic II while the company default is Mechanic I, the elected mechanic must be reconciled
with the agreement's words before execution; where they diverge, amend or record the deviation.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ..models.enums import ThresholdBasis, ThresholdExit, ThresholdMechanic
from ..models.parameters import DealParameters, ThresholdSpec
from ..strategies.protocols import ThresholdRequirement
from ..strategies.registry import threshold_mechanics
from .models import (
    ReferenceIncomeSeries,
    ThresholdCheck,
    ThresholdRequirementResult,
    ThresholdResult,
)

_ONE = Decimal(1)


class LinearLadderMechanic:
    """Mechanic I (mech:one): cumulative ladder, linear beyond the last checkpoint."""

    def requirements(self, spec: ThresholdSpec, age: int) -> tuple[ThresholdRequirement, ...]:
        grid = dict(spec.checkpoints)
        if age in grid:
            return (ThresholdRequirement(ThresholdBasis.CUMULATIVE, grid[age]),)
        last_age, last_p = spec.checkpoints[-1]
        if age > last_age:
            required = last_p + Decimal(age - last_age) * spec.delta_pct
            return (ThresholdRequirement(ThresholdBasis.CUMULATIVE, required),)
        return ()  # an age below the last checkpoint but not on the grid carries no floor


class IncrementalMechanic:
    """Mechanic II (mech:two): checkpoints plus a per-period incremental floor."""

    def requirements(self, spec: ThresholdSpec, age: int) -> tuple[ThresholdRequirement, ...]:
        grid = dict(spec.checkpoints)
        reqs: list[ThresholdRequirement] = []
        if age in grid:
            reqs.append(ThresholdRequirement(ThresholdBasis.CUMULATIVE, grid[age]))
        if age >= spec.delta_from_age:
            reqs.append(ThresholdRequirement(ThresholdBasis.INCREMENTAL, spec.delta_pct))
        return tuple(reqs)


def evaluate_threshold(
    ri: ReferenceIncomeSeries,
    params: DealParameters,
    *,
    origin_spend: Decimal,
    exit_age: int | None = None,
) -> ThresholdResult:
    """Evaluate a cohort's threshold tests in age order (KB §3.3).

    ``origin_spend`` is the cohort's origin-period Actual S&M Spend (def:basis denominator).
    Legacy (pre-closing) cohorts are evaluated identically — pass their reconstructed series.

    Exit (def:elections): under ``BREAKEVEN`` the cohort leaves testing the first period its
    cumulative ratio reaches 100% (that period is not tested). Under ``RETURN_CAP`` it is tested
    while outstanding: pass the closure age ``k*`` as ``exit_age``; ages ``0..exit_age``
    (inclusive — ``k*`` is still outstanding at the start of its period) are tested and
    ``exit_age + 1`` on are not. Testing stops at the first failing period: a breach is
    irreversible.
    """
    if origin_spend <= 0:
        raise ValueError("threshold basis requires a positive origin S&M spend")

    spec = params.threshold
    mechanic = threshold_mechanics.get(spec.mechanic.value)

    checks: list[ThresholdCheck] = []
    cumulative = Decimal(0)
    breached = False
    breach_age: int | None = None
    breach_month: date | None = None
    exited = False
    exit_age_out: int | None = None

    for cell in sorted(ri.cells, key=lambda c: c.age):
        age = cell.age
        cumulative += cell.reference_income
        cum_ratio = cumulative / origin_spend
        inc_ratio = cell.reference_income / origin_spend

        if spec.exit is ThresholdExit.BREAKEVEN and cum_ratio >= _ONE:
            exited, exit_age_out = True, age
            break
        if spec.exit is ThresholdExit.RETURN_CAP and exit_age is not None and age > exit_age:
            exited, exit_age_out = True, exit_age
            break

        req_results: list[ThresholdRequirementResult] = []
        for req in mechanic.requirements(spec, age):
            actual = cum_ratio if req.basis is ThresholdBasis.CUMULATIVE else inc_ratio
            req_results.append(
                ThresholdRequirementResult(
                    basis=req.basis,
                    required=req.required,
                    actual=actual,
                    passed=actual >= req.required,
                )
            )
        age_passed = all(r.passed for r in req_results)
        checks.append(
            ThresholdCheck(
                age=age,
                period_month=cell.period_month,
                cumulative_ratio=cum_ratio,
                incremental_ratio=inc_ratio,
                requirements=tuple(req_results),
                passed=age_passed,
            )
        )
        if not age_passed:
            breached, breach_age, breach_month = True, age, cell.period_month
            break

    return ThresholdResult(
        company_id=ri.company_id,
        cohort_month=ri.cohort_month,
        mechanic=spec.mechanic,
        timing=spec.timing,
        exit=spec.exit,
        checks=tuple(checks),
        breached=breached,
        breach_age=breach_age,
        breach_month=breach_month,
        exited=exited,
        exit_age=exit_age_out,
    )


def _register_defaults() -> None:
    if ThresholdMechanic.LINEAR_LADDER.value not in threshold_mechanics.names():
        threshold_mechanics.register(ThresholdMechanic.LINEAR_LADDER.value, LinearLadderMechanic())
    if ThresholdMechanic.INCREMENTAL.value not in threshold_mechanics.names():
        threshold_mechanics.register(ThresholdMechanic.INCREMENTAL.value, IncrementalMechanic())


_register_defaults()
