"""Matplotlib renderers: the collections->retained waterfall, and the cohort/time triangle.

``pyplot`` is imported lazily inside each function so the backend (e.g. ``Agg`` in tests, the
inline backend in a notebook) is whatever the caller has configured. Returns the ``Figure`` for
notebook display.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .models import CohortPeriodMatrix, StepKind, WaterfallStep

# Palette: milestone totals, company reductions, the GC remittance, and Skalar's retained total.
_TOTAL = "#3b5b92"
_RETAINED = "#4a9d6f"
_COMPANY = "#d9a441"
_GC = "#5aa9b5"
_GC_LABEL = "Remitted to GC"
_RETAINED_LABEL = "Skalar retained"


def plot_waterfall(steps: list[WaterfallStep], *, title: str = "Collections waterfall") -> Any:
    """Draw the waterfall: milestone totals from the baseline, reductions floating between them."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 5.5))
    running = 0.0
    prev_level = 0.0
    for i, step in enumerate(steps):
        value = float(step.value)
        if step.kind is StepKind.TOTAL:
            bottom, height, running = 0.0, value, value
            color = _RETAINED if step.label == _RETAINED_LABEL else _TOTAL
        else:
            bottom = running + value if value < 0 else running
            height = abs(value)
            running += value
            color = _GC if step.label == _GC_LABEL else _COMPANY
        ax.bar(i, height, bottom=bottom, width=0.6, color=color, edgecolor="white")
        ax.text(i, bottom + height, f"{value:,.0f}", ha="center", va="bottom", fontsize=8)
        if i > 0:
            ax.plot([i - 0.7, i - 0.3], [prev_level, prev_level],
                    color="#999999", linewidth=0.7, linestyle="--")
        prev_level = running

    ax.set_xticks(range(len(steps)))
    ax.set_xticklabels([s.label for s in steps], rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("USD")
    ax.set_title(title)
    ax.margins(y=0.15)
    fig.tight_layout()
    return fig


def plot_cohort_matrix(
    matrix: CohortPeriodMatrix, *, cmap: str = "viridis", title: str | None = None
) -> Any:
    """Heatmap the run-off triangle: cohorts (rows) x calendar periods (cols), empties masked."""
    import matplotlib.pyplot as plt

    rows, cols = matrix.shape
    grid = np.full((rows, cols), np.nan)
    for r, row in enumerate(matrix.values):
        for c, value in enumerate(row):
            if value is not None:
                grid[r, c] = float(value)
    masked = np.ma.masked_invalid(grid)

    fig, ax = plt.subplots(figsize=(max(6, cols * 0.6), max(4, rows * 0.5)))
    palette = plt.get_cmap(cmap).with_extremes(bad="#f2f2f2")  # mask the empty triangle corner
    image = ax.imshow(masked, aspect="auto", cmap=palette)

    ax.set_xticks(range(cols))
    ax.set_xticklabels([p.strftime("%Y-%m") for p in matrix.periods], rotation=90, fontsize=7)
    ax.set_yticks(range(rows))
    ax.set_yticklabels([c.strftime("%Y-%m") for c in matrix.cohorts], fontsize=7)
    ax.set_xlabel("Calendar period")
    ax.set_ylabel("Cohort (origin month)")
    ax.set_title(title or f"{matrix.field} — cohort x period")
    fig.colorbar(image, ax=ax, label=matrix.field, fraction=0.046, pad=0.04)
    fig.tight_layout()
    return fig
