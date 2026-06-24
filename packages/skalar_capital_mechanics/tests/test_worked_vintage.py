"""Golden: reproduce the scenarios_sandbox §3.1 downstream cohort ledger (Scenario A, June 2026).

The acceptance oracle for Phase 3 — every number is read straight from the worked walkthrough:
R (x0.45), S̃ (x0.80), cum S̃, payback a* = 6, μ = 1.108, cap = 177.28, age-8 flow truncates
to 2.68, breakeven exit at age 6 under Mechanic II.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal

from skalar_capital_mechanics import (
    CollectionsMatrix,
    DealParameters,
    ThresholdBasis,
    ThresholdMechanic,
    evaluate_threshold,
    reference_income,
    sharing_schedule,
)

JUNE_2026 = date(2026, 6, 1)
F_EFF = Decimal("160.0")  # 0.80 funding x 200.0 origin spend
ORIGIN_SPEND = Decimal("200.0")

COLLECTIONS = [Decimal(v) for v in ("120", "90", "70", "55", "45", "40", "35", "30", "25")]
EXPECTED_R = ["54.00", "40.50", "31.50", "24.75", "20.25", "18.00", "15.75", "13.50", "11.25"]
EXPECTED_STILDE = ["43.20", "32.40", "25.20", "19.80", "16.20", "14.40", "12.60", "10.80", "2.68"]
EXPECTED_CUM = [
    "43.20", "75.60", "100.80", "120.60", "136.80", "151.20", "163.80", "174.60", "177.28",
]


def test_reference_income_matches_walkthrough(
    make_params: Callable[..., DealParameters],
    make_matrix: Callable[..., CollectionsMatrix],
) -> None:
    ri = reference_income(make_matrix(COLLECTIONS), JUNE_2026, make_params())
    assert [c.age for c in ri.cells] == list(range(9))
    assert [c.reference_income for c in ri.cells] == [Decimal(v) for v in EXPECTED_R]


def test_sharing_schedule_payback_cap_and_truncation(
    make_params: Callable[..., DealParameters],
    make_matrix: Callable[..., CollectionsMatrix],
) -> None:
    ri = reference_income(make_matrix(COLLECTIONS), JUNE_2026, make_params())
    schedule = sharing_schedule(ri, make_params(), effective_funding=F_EFF)

    assert schedule.payback_age == 6
    assert schedule.payback_months == 6
    assert schedule.moic == Decimal("1.108")
    assert schedule.return_cap == Decimal("177.28")
    assert schedule.closure_age == 8
    assert schedule.is_closed

    assert [c.collected_sharing for c in schedule.cells] == [Decimal(v) for v in EXPECTED_STILDE]
    assert [c.cumulative_collected for c in schedule.cells] == [Decimal(v) for v in EXPECTED_CUM]
    # The cap binds exactly: the age-8 theoretical 9.00 truncates to the residual 2.68.
    assert schedule.cells[8].theoretical_sharing == Decimal("9.00")
    assert schedule.total_collected() == Decimal("177.28")


def test_threshold_mechanic_two_passes_to_breakeven(
    make_params: Callable[..., DealParameters],
    make_matrix: Callable[..., CollectionsMatrix],
) -> None:
    ri = reference_income(make_matrix(COLLECTIONS), JUNE_2026, make_params())
    result = evaluate_threshold(ri, make_params(), origin_spend=ORIGIN_SPEND)

    assert result.mechanic is ThresholdMechanic.INCREMENTAL
    assert not result.breached
    assert result.exited
    assert result.exit_age == 6  # cum R = 102.4% of origin spend ⇒ breakeven exit
    assert [c.age for c in result.checks] == [0, 1, 2, 3, 4, 5]
    assert all(c.passed for c in result.checks)

    # M0 is a cumulative checkpoint at 16%; cum(0) = 54/200 = 27%.
    m0 = result.checks[0]
    assert m0.cumulative_ratio == Decimal("0.27")
    assert m0.requirements[0].basis is ThresholdBasis.CUMULATIVE
    assert m0.requirements[0].required == Decimal("0.16")

    # Age 4 is the first incremental-delta test; inc(4) = 20.25/200 = 10.125% ≥ 5%.
    delta = result.checks[4]
    assert delta.incremental_ratio == Decimal("0.10125")
    assert delta.requirements[0].basis is ThresholdBasis.INCREMENTAL
    assert delta.requirements[0].required == Decimal("0.05")
