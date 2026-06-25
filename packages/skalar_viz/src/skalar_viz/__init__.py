"""Skalar visualization layer.

Decomposes collections into the Skalar/GC sharing waterfall and lays the per-cohort flows out on a
time x cohort run-off triangle, with matplotlib renderers for notebook display. Depends only on
``skalar_capital_mechanics`` (a presentation leaf — nothing in the engine imports it).
"""

from __future__ import annotations

from .decompose import (
    build_waterfall_steps,
    decompose_cohort,
    decompose_portfolio,
)
from .matrix import build_cohort_period_matrix
from .models import (
    CohortPeriodMatrix,
    StepKind,
    WaterfallCell,
    WaterfallStep,
)
from .plot import plot_cohort_matrix, plot_waterfall
from .scenario import (
    demo_deal_parameters,
    geometric_series,
    synthetic_collections,
)

__version__ = "0.1.0"

__all__ = [
    "CohortPeriodMatrix",
    "StepKind",
    "WaterfallCell",
    "WaterfallStep",
    "build_cohort_period_matrix",
    "build_waterfall_steps",
    "decompose_cohort",
    "decompose_portfolio",
    "demo_deal_parameters",
    "geometric_series",
    "plot_cohort_matrix",
    "plot_waterfall",
    "synthetic_collections",
]
