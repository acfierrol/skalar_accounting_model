"""Waterfall decomposition: collections -> R -> S -> S~ -> GC/Skalar split."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from skalar_viz import (
    build_waterfall_steps,
    decompose_cohort,
    demo_deal_parameters,
    synthetic_collections,
)
from skalar_viz.models import StepKind, WaterfallCell

JUNE_2026 = date(2026, 6, 1)
# The scenarios_sandbox worked vintage (kUSD): collections that yield S~ summing to the 177.28 cap.
COLLECTIONS = [Decimal(v) for v in ("120", "90", "70", "55", "45", "40", "35", "30", "25")]
EXPECTED_STILDE = [Decimal(v) for v in
                   ("43.20", "32.40", "25.20", "19.80", "16.20", "14.40", "12.60", "10.80", "2.68")]
NO_CAP = Decimal("1000000000")


def _cells(gc_cap: Decimal = NO_CAP) -> list[WaterfallCell]:
    matrix = synthetic_collections({JUNE_2026: COLLECTIONS})
    params = demo_deal_parameters()  # funding/sharing 0.80, margin 0.45, leverage 0.95
    return decompose_cohort(
        matrix, JUNE_2026, params, effective_funding=Decimal("160"), gc_cap=gc_cap
    )


def test_effective_share_matches_worked_vintage() -> None:
    cells = _cells()
    assert [c.collected_sharing for c in cells] == EXPECTED_STILDE
    assert next(c.reference_income for c in cells) == Decimal("54.00")  # 120 x 0.45


def test_uncapped_gc_split_is_leverage_share() -> None:
    cells = _cells()
    first = cells[0]
    assert first.gc_share == Decimal("41.04")  # 0.95 x 43.20
    assert first.skalar_retained == Decimal("2.16")  # 0.05 x 43.20
    assert first.company_retained == Decimal("76.80")  # 120 - 43.20
    # Every dollar of collections is accounted for: company + gc + skalar.
    for c in cells:
        assert c.company_retained + c.gc_share + c.skalar_retained == c.collections


def test_gc_cap_stops_remittance_and_skalar_keeps_rest() -> None:
    cells = _cells(gc_cap=Decimal("50"))
    assert sum(c.gc_share for c in cells) == Decimal("50")  # cumulative remittance hits the cap
    # Once GC is fully repaid, Skalar keeps 100% of the effective share.
    assert cells[-1].gc_share == Decimal("0")
    assert cells[-1].skalar_retained == cells[-1].collected_sharing


def test_waterfall_steps_reconcile() -> None:
    steps = build_waterfall_steps(_cells())
    by_label = {s.label: s for s in steps}
    assert by_label["Collections"].value == Decimal("510")  # sum of collections
    assert by_label["Reference income"].value == Decimal("229.50")  # 510 x 0.45
    assert by_label["Effective Skalar share (S~)"].value == Decimal("177.28")
    assert by_label["Skalar retained"].value == Decimal("8.8640")  # 0.05 x 177.28

    # Totals are absolute; deltas are signed reductions that chain to the final retained level.
    running = 0.0
    for step in steps:
        if step.kind is StepKind.TOTAL:
            running = float(step.value)
        else:
            running += float(step.value)
    assert abs(running - float(by_label["Skalar retained"].value)) < 1e-9
