"""Decompose collections into the Skalar/GC waterfall, per cohort and per period.

Reuses the engine: ``reference_income`` (collections x margin) and ``sharing_schedule`` (theoretical
S, cap-truncated S~). The only viz-specific step is splitting the effective share S~ between the GC
remittance and what Skalar keeps, via the upstream waterfall (KB §11.5): each period GC takes
``leverage x S~`` until cumulative remittance reaches the vintage's GC cap; thereafter Skalar
retains 100%. The GC cap is a parameter (default the 2.0x-PFA ceiling leg).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal

from skalar_capital_mechanics import (
    CollectionsMatrix,
    DealParameters,
    reference_income,
    sharing_schedule,
)

from .models import StepKind, WaterfallCell, WaterfallStep

_ZERO = Decimal(0)


def decompose_cohort(
    collections: CollectionsMatrix,
    cohort_month: date,
    params: DealParameters,
    *,
    effective_funding: Decimal,
    gc_cap: Decimal,
    leverage: Decimal | None = None,
) -> list[WaterfallCell]:
    """Decompose one cohort's periods into the full waterfall (collections -> Skalar/GC split)."""
    lev = leverage if leverage is not None else params.leverage.gc_funding_pct
    ri = reference_income(collections, cohort_month, params)
    schedule = sharing_schedule(ri, params, effective_funding=effective_funding)
    collections_by_age = {c.age: c.collections for c in ri.cells}

    cells: list[WaterfallCell] = []
    cumulative_gc = _ZERO
    for cell in schedule.cells:
        s_tilde = cell.collected_sharing
        gc_take = lev * s_tilde
        # Cap cumulative GC remittance at the vintage's entitlement; never refund below zero.
        if cumulative_gc + gc_take > gc_cap:
            gc_take = gc_cap - cumulative_gc
        if cumulative_gc + gc_take < _ZERO:
            gc_take = -cumulative_gc
        cumulative_gc += gc_take
        coll = collections_by_age.get(cell.age, _ZERO)
        cells.append(
            WaterfallCell(
                cohort_month=cohort_month,
                period_month=cell.period_month,
                age=cell.age,
                collections=coll,
                reference_income=cell.reference_income,
                theoretical_sharing=cell.theoretical_sharing,
                collected_sharing=s_tilde,
                gc_share=gc_take,
                skalar_retained=s_tilde - gc_take,
                company_retained=coll - s_tilde,
            )
        )
    return cells


def decompose_portfolio(
    collections: CollectionsMatrix,
    params: DealParameters,
    fundings: Mapping[date, tuple[Decimal, Decimal]],
) -> list[WaterfallCell]:
    """Decompose several cohorts. ``fundings`` maps cohort_month -> (effective_funding, gc_cap)."""
    cells: list[WaterfallCell] = []
    for cohort_month in sorted(fundings):
        effective_funding, gc_cap = fundings[cohort_month]
        cells.extend(
            decompose_cohort(
                collections, cohort_month, params,
                effective_funding=effective_funding, gc_cap=gc_cap,
            )
        )
    return cells


def build_waterfall_steps(cells: Sequence[WaterfallCell]) -> list[WaterfallStep]:
    """Aggregate cells into the collections -> Skalar-retained waterfall (totals + reductions)."""
    collections = sum((c.collections for c in cells), _ZERO)
    reference = sum((c.reference_income for c in cells), _ZERO)
    theoretical = sum((c.theoretical_sharing for c in cells), _ZERO)
    effective = sum((c.collected_sharing for c in cells), _ZERO)
    gc = sum((c.gc_share for c in cells), _ZERO)
    retained = sum((c.skalar_retained for c in cells), _ZERO)

    delta = StepKind.DELTA
    total = StepKind.TOTAL
    return [
        WaterfallStep(label="Collections", value=collections, kind=total),
        WaterfallStep(label="Company keeps (margin)", value=reference - collections, kind=delta),
        WaterfallStep(label="Reference income", value=reference, kind=total),
        WaterfallStep(
            label="Company keeps (1 - sharing)", value=theoretical - reference, kind=delta
        ),
        WaterfallStep(label="Theoretical sharing", value=theoretical, kind=total),
        WaterfallStep(label="Above return cap", value=effective - theoretical, kind=delta),
        WaterfallStep(label="Effective Skalar share (S~)", value=effective, kind=total),
        WaterfallStep(label="Remitted to GC", value=-gc, kind=delta),
        WaterfallStep(label="Skalar retained", value=retained, kind=total),
    ]
