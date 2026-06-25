"""Parametrized inputs for the notebook: demo deal parameters + synthetic collections.

A presentation-layer convenience (not part of the engine): builds a ``DealParameters`` from a few
scalar knobs and lays out per-cohort collection series into a ``CollectionsMatrix`` so the notebook
can explore the waterfall without a live BigQuery pull.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal

from skalar_capital_mechanics import (
    CollectionsCell,
    CollectionsMatrix,
    CollectionsMeta,
    DealParameters,
    FundingBand,
    SettlementWindows,
    SharingBand,
    load_defaults,
)


def _month_plus(base: date, n: int) -> date:
    index = base.month - 1 + n
    return date(base.year + index // 12, index % 12 + 1, 1)


def demo_deal_parameters(
    *,
    company_id: str = "SK011",
    cohort_month: date = date(2026, 6, 1),
    funding_pct: Decimal = Decimal("0.80"),
    sharing_pct: Decimal = Decimal("0.80"),
    margin: Decimal = Decimal("0.45"),
    gc_funding_pct: Decimal = Decimal("0.95"),
) -> DealParameters:
    """Build deal parameters from scalar knobs; ladder/windows/threshold come from the defaults."""
    regime = load_defaults()
    return DealParameters(
        company_id=company_id,
        cohort_month=cohort_month,
        funding_band=FundingBand.fixed(funding_pct),
        sharing_band=SharingBand.fixed(sharing_pct),
        funding_pct=funding_pct,
        sharing_pct=sharing_pct,
        margin=margin,
        pricing_strategy=regime.pricing_strategy,
        moic_ladder=regime.moic_ladder,
        eir_given=regime.eir_given,
        eir_taken=regime.eir_taken,
        windows=SettlementWindows(l_op_months=1, lambda_=regime.windows.lambda_),
        leverage=regime.leverage.model_copy(update={"gc_funding_pct": gc_funding_pct}),
        per_period_cap=regime.per_period_cap,
        commitment_amount=regime.commitment_amount,
        threshold=regime.threshold,
        winddown=regime.winddown,
    )


def geometric_series(first: Decimal, decay: Decimal, periods: int) -> list[Decimal]:
    """A decaying collections curve: ``first``, ``first*decay``, ... (2 dp), ``periods`` long."""
    out: list[Decimal] = []
    value = first
    for _ in range(periods):
        out.append(value)
        value = (value * decay).quantize(Decimal("0.01"))
    return out


def synthetic_collections(
    cohorts: Mapping[date, Sequence[Decimal]],
    *,
    company_id: str = "SK011",
) -> CollectionsMatrix:
    """Build a collections matrix from per-cohort series (cohort i, age k -> month i+k)."""
    cells = tuple(
        CollectionsCell(
            company_id=company_id,
            cohort_month=cohort,
            period_month=_month_plus(cohort, age),
            collections=amount,
        )
        for cohort, series in cohorts.items()
        for age, amount in enumerate(series)
    )
    meta = CollectionsMeta(source="cache", from_cache=True, scanned_bytes=0)
    return CollectionsMatrix(company_id=company_id, cells=cells, meta=meta)
