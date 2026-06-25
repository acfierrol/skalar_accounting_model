"""Cohort/period run-off triangle + matplotlib renderers (headless Agg backend)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import matplotlib

from skalar_viz import (
    build_cohort_period_matrix,
    build_waterfall_steps,
    decompose_portfolio,
    demo_deal_parameters,
    plot_cohort_matrix,
    plot_waterfall,
    synthetic_collections,
)
from skalar_viz.models import WaterfallCell

# Headless backend. Safe to set after imports: plot.py imports pyplot lazily, inside the
# rendering functions, so the backend only needs to be fixed before a plot call.
matplotlib.use("Agg")

JUNE = date(2026, 6, 1)
JULY = date(2026, 7, 1)


def _portfolio_cells() -> list[WaterfallCell]:
    matrix = synthetic_collections({
        JUNE: [Decimal("120"), Decimal("90"), Decimal("70")],
        JULY: [Decimal("100"), Decimal("80")],
    })
    params = demo_deal_parameters()
    return decompose_portfolio(
        matrix, params,
        {JUNE: (Decimal("160"), Decimal("1000000")), JULY: (Decimal("200"), Decimal("1000000"))},
    )


def test_matrix_is_a_triangle_with_empty_corner() -> None:
    grid = build_cohort_period_matrix(_portfolio_cells(), field="collected_sharing")
    assert grid.cohorts == (JUNE, JULY)
    # Three calendar periods: 2026-06, 2026-07, 2026-08.
    assert grid.periods == (JUNE, JULY, date(2026, 8, 1))
    assert grid.shape == (2, 3)
    # July cohort has no flow in the June column -> empty corner.
    july_row = grid.values[1]
    assert july_row[0] is None
    assert july_row[1] is not None
    # Age runs along the diagonals: cohort July at period July is age 0.
    assert grid.age_at(1, 1) == 0
    assert grid.age_at(0, 1) == 1  # June cohort, July period


def test_plot_waterfall_returns_figure_with_a_bar_per_step() -> None:
    steps = build_waterfall_steps(_portfolio_cells())
    fig = plot_waterfall(steps)
    ax = fig.axes[0]
    assert len(ax.patches) == len(steps)  # one bar per waterfall step
    assert ax.get_ylabel() == "USD"


def test_plot_cohort_matrix_returns_heatmap() -> None:
    grid = build_cohort_period_matrix(_portfolio_cells(), field="skalar_retained")
    fig = plot_cohort_matrix(grid)
    ax = fig.axes[0]
    assert ax.images  # an imshow heatmap was drawn
    assert len(ax.get_xticks()) == grid.shape[1]
    assert len(ax.get_yticks()) == grid.shape[0]
