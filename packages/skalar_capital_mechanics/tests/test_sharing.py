"""Sharing schedule: payback detection, cap truncation, no-payback, breach → 100% sharing."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal

from skalar_capital_mechanics import (
    CollectionsMatrix,
    DealParameters,
    payback_age,
    reference_income,
    sharing_schedule,
)

JUNE_2026 = date(2026, 6, 1)


def test_payback_age_first_age_reaching_funding() -> None:
    series = [(0, Decimal("60")), (1, Decimal("60")), (2, Decimal("60"))]
    assert payback_age(series, Decimal("100")) == 1
    assert payback_age(series, Decimal("180")) == 2
    assert payback_age(series, Decimal("181")) is None


def test_no_payback_leaves_cap_unset_and_collects_all(
    make_params: Callable[..., DealParameters],
    make_matrix: Callable[..., CollectionsMatrix],
) -> None:
    # Tiny cohort: cumulative sharing never reaches F_eff, so no cap is fixed.
    ri = reference_income(make_matrix([Decimal("10"), Decimal("10")]), JUNE_2026, make_params())
    schedule = sharing_schedule(ri, make_params(), effective_funding=Decimal("160.0"))
    assert schedule.payback_age is None
    assert schedule.return_cap is None
    assert schedule.moic is None
    assert schedule.closure_age is None
    # S~ = S (each 10 x 0.45 x 0.80 = 3.60), nothing truncated.
    assert [c.collected_sharing for c in schedule.cells] == [Decimal("3.60"), Decimal("3.60")]


def test_breach_lifts_sharing_to_full_rate(
    make_params: Callable[..., DealParameters],
    make_matrix: Callable[..., CollectionsMatrix],
) -> None:
    # F_eff large enough that the cap never binds — isolate the breach effect on the rate.
    ri = reference_income(
        make_matrix([Decimal("100"), Decimal("100"), Decimal("100")]), JUNE_2026, make_params()
    )
    schedule = sharing_schedule(
        ri, make_params(), effective_funding=Decimal("1000.0"), breach_age=1
    )
    pcts = [c.sharing_pct for c in schedule.cells]
    assert pcts == [Decimal("0.80"), Decimal("1"), Decimal("1")]
    # Age 0 shares at 0.80 (R=45 → 36); from the breach age, sharing is 100% (R=45 → 45).
    assert schedule.cells[0].collected_sharing == Decimal("36.00")
    assert schedule.cells[1].collected_sharing == Decimal("45.00")
    assert schedule.cells[2].collected_sharing == Decimal("45.00")


def test_cap_truncates_and_closes(
    make_params: Callable[..., DealParameters],
    make_matrix: Callable[..., CollectionsMatrix],
) -> None:
    # Flat 100/period: R=45, S=36. F_eff=100 → payback at age 2 (cum S 36/72/108).
    ri = reference_income(make_matrix([Decimal("100")] * 6), JUNE_2026, make_params())
    schedule = sharing_schedule(ri, make_params(), effective_funding=Decimal("100"))
    assert schedule.payback_age == 2
    # μ(2 months) = base 1.08 (below base age 4) ⇒ cap = 1.08 x 100 = 108.
    assert schedule.return_cap == Decimal("108.00")
    assert schedule.total_collected() == Decimal("108.00")
    assert schedule.closure_age == 2
    # Once closed, later periods collect nothing and the cumulative holds at the cap.
    assert schedule.cells[-1].collected_sharing == Decimal(0)
    assert schedule.cells[-1].cumulative_collected == Decimal("108.00")
