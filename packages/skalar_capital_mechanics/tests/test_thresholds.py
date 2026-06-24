"""Threshold mechanics I & II: requirement grids, exit, breach, stringency, legacy cohorts."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date
from decimal import Decimal

import pytest

from skalar_capital_mechanics import (
    DealParameters,
    IncrementalMechanic,
    LinearLadderMechanic,
    ReferenceIncomeCell,
    ReferenceIncomeSeries,
    ThresholdBasis,
    ThresholdExit,
    ThresholdMechanic,
    ThresholdSpec,
    ThresholdTiming,
    evaluate_threshold,
)
from skalar_capital_mechanics.strategies import ThresholdRequirement

JUNE_2026 = date(2026, 6, 1)
MARGIN = Decimal("0.45")


def _month_plus(base: date, n: int) -> date:
    index = base.month - 1 + n
    return date(base.year + index // 12, index % 12 + 1, 1)


def _ri(r_values: Sequence[Decimal], cohort: date = JUNE_2026) -> ReferenceIncomeSeries:
    """Build a Reference Income series directly from R values (collections back-derived)."""
    cells = tuple(
        ReferenceIncomeCell(
            company_id="SK011",
            cohort_month=cohort,
            period_month=_month_plus(cohort, age),
            age=age,
            collections=r / MARGIN,
            reference_income=r,
        )
        for age, r in enumerate(r_values)
    )
    return ReferenceIncomeSeries(
        company_id="SK011", cohort_month=cohort, margin=MARGIN, cells=cells
    )


def _spec(
    mechanic: ThresholdMechanic, exit_: ThresholdExit = ThresholdExit.BREAKEVEN
) -> ThresholdSpec:
    return ThresholdSpec(
        mechanic=mechanic,
        timing=ThresholdTiming.ANY_DAY,
        exit=exit_,
        checkpoints=(
            (0, Decimal("0.16")),
            (1, Decimal("0.25")),
            (2, Decimal("0.31")),
            (3, Decimal("0.37")),
        ),
        delta_pct=Decimal("0.05"),
        delta_from_age=4,
    )


def test_mechanic_one_requirement_grid() -> None:
    spec = _spec(ThresholdMechanic.LINEAR_LADDER)
    mech = LinearLadderMechanic()
    assert mech.requirements(spec, 0) == (
        ThresholdRequirement(ThresholdBasis.CUMULATIVE, Decimal("0.16")),
    )
    assert mech.requirements(spec, 3)[0].required == Decimal("0.37")
    # Beyond the last checkpoint: linear at slope 0.05.
    assert mech.requirements(spec, 4)[0].basis is ThresholdBasis.CUMULATIVE
    assert mech.requirements(spec, 4)[0].required == Decimal("0.42")
    assert mech.requirements(spec, 5)[0].required == Decimal("0.47")


def test_mechanic_one_gap_grid_has_no_floor_between_checkpoints() -> None:
    spec = ThresholdSpec(
        mechanic=ThresholdMechanic.LINEAR_LADDER,
        timing=ThresholdTiming.ANY_DAY,
        exit=ThresholdExit.BREAKEVEN,
        checkpoints=((0, Decimal("0.07")), (3, Decimal("0.24")), (6, Decimal("0.40"))),
        delta_pct=Decimal("0.05"),
        delta_from_age=7,
    )
    mech = LinearLadderMechanic()
    assert mech.requirements(spec, 1) == ()
    assert mech.requirements(spec, 2) == ()
    assert mech.requirements(spec, 3)[0].required == Decimal("0.24")
    assert mech.requirements(spec, 7)[0].required == Decimal("0.45")  # 0.40 + 1 x 0.05


def test_mechanic_two_requirement_grid() -> None:
    spec = _spec(ThresholdMechanic.INCREMENTAL)
    mech = IncrementalMechanic()
    # Checkpoint age: cumulative only (below delta_from_age).
    assert [r.basis for r in mech.requirements(spec, 0)] == [ThresholdBasis.CUMULATIVE]
    # From delta_from_age: an incremental floor.
    inc = mech.requirements(spec, 4)
    assert [r.basis for r in inc] == [ThresholdBasis.INCREMENTAL]
    assert inc[0].required == Decimal("0.05")


def test_mechanic_two_overlapping_checkpoint_and_delta(
    make_params: Callable[..., DealParameters],
) -> None:
    # An age that is BOTH a checkpoint and >= delta_from_age emits both floors, ANDed together.
    spec = ThresholdSpec(
        mechanic=ThresholdMechanic.INCREMENTAL,
        timing=ThresholdTiming.ANY_DAY,
        exit=ThresholdExit.RETURN_CAP,
        checkpoints=((0, Decimal("0.10")), (2, Decimal("0.30"))),
        delta_pct=Decimal("0.05"),
        delta_from_age=2,
    )
    bases = [r.basis for r in IncrementalMechanic().requirements(spec, 2)]
    assert sorted(bases) == sorted([ThresholdBasis.CUMULATIVE, ThresholdBasis.INCREMENTAL])

    # cum(2) = 0.52 clears the 0.30 checkpoint, but inc(2) = 0.02 fails the 0.05 delta → breach.
    ri = _ri([Decimal("20"), Decimal("30"), Decimal("2")])
    params = make_params().model_copy(update={"threshold": spec})
    result = evaluate_threshold(ri, params, origin_spend=Decimal("100"), exit_age=5)
    assert result.breached
    assert result.breach_age == 2
    passed_by_basis = {r.basis: r.passed for r in result.checks[-1].requirements}
    assert passed_by_basis[ThresholdBasis.CUMULATIVE] is True
    assert passed_by_basis[ThresholdBasis.INCREMENTAL] is False


# R values whose cumulative is exactly on the Mechanic-I schedule but whose age-4 increment
# (0.02) is below the 0.05 delta. origin_spend = 100 ⇒ ratios are R/100.
STRINGENCY_R = [Decimal("20"), Decimal("10"), Decimal("5"), Decimal("5"), Decimal("2")]


def test_mechanic_two_breaches_where_one_passes(
    make_params: Callable[..., DealParameters],
) -> None:
    ri = _ri(STRINGENCY_R)
    params_two = make_params().model_copy(
        update={"threshold": _spec(ThresholdMechanic.INCREMENTAL)}
    )
    result_two = evaluate_threshold(ri, params_two, origin_spend=Decimal("100"))
    assert result_two.breached
    assert result_two.breach_age == 4  # incremental dip
    assert result_two.checks[-1].requirements[0].basis is ThresholdBasis.INCREMENTAL
    assert not result_two.checks[-1].passed

    params_one = make_params().model_copy(
        update={"threshold": _spec(ThresholdMechanic.LINEAR_LADDER)}
    )
    result_one = evaluate_threshold(ri, params_one, origin_spend=Decimal("100"))
    assert not result_one.breached  # cumulative 0.42 meets the ladder's 0.42 floor at age 4
    assert [c.age for c in result_one.checks] == [0, 1, 2, 3, 4]


def test_legacy_cohort_evaluated_and_can_breach(
    make_params: Callable[..., DealParameters],
) -> None:
    # A pre-closing (legacy) cohort, tested as if the deal had been in effect (def:breach).
    legacy_cohort = date(2026, 3, 1)
    ri = _ri([Decimal("10"), Decimal("20")], cohort=legacy_cohort)  # cum(0) = 0.10 < 0.16
    params = make_params(legacy_cohort).model_copy(
        update={"threshold": _spec(ThresholdMechanic.INCREMENTAL)}
    )
    result = evaluate_threshold(ri, params, origin_spend=Decimal("100"))
    assert result.breached
    assert result.breach_age == 0
    assert result.breach_month == legacy_cohort


def test_return_cap_exit_stops_at_exit_age(
    make_params: Callable[..., DealParameters],
) -> None:
    ri = _ri([Decimal("20"), Decimal("10"), Decimal("5"), Decimal("5"), Decimal("5")])
    params = make_params().model_copy(
        update={"threshold": _spec(ThresholdMechanic.INCREMENTAL, ThresholdExit.RETURN_CAP)}
    )
    result = evaluate_threshold(ri, params, origin_spend=Decimal("100"), exit_age=2)
    assert [c.age for c in result.checks] == [0, 1, 2]
    assert result.exited
    assert result.exit_age == 2
    assert not result.breached


def test_zero_origin_spend_rejected(make_params: Callable[..., DealParameters]) -> None:
    with pytest.raises(ValueError, match="positive origin"):
        evaluate_threshold(_ri([Decimal("10")]), make_params(), origin_spend=Decimal("0"))
