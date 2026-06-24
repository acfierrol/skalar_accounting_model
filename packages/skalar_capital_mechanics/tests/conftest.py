"""Shared builders for the income (Phase 3) tests: Scenario-A params + a collections matrix.

Exposed as factory fixtures so tests can vary the cohort month and override fields via
``model_copy``. Values mirror scenarios_sandbox §2 (Scenario A, the executed SK011 regime).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date
from decimal import Decimal

import pytest

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

JUNE_2026 = date(2026, 6, 1)


def month_plus(base: date, n: int) -> date:
    """The first of the month ``n`` months after ``base`` (always day 1)."""
    index = base.month - 1 + n
    return date(base.year + index // 12, index % 12 + 1, 1)


def make_scenario_a_params(cohort_month: date = JUNE_2026) -> DealParameters:
    """Fully-resolved Scenario-A parameters for one cohort (funding/sharing 0.80, margin 0.45)."""
    reg = load_defaults()
    return DealParameters(
        company_id="SK011",
        cohort_month=cohort_month,
        funding_band=FundingBand.fixed(Decimal("0.80")),
        sharing_band=SharingBand.fixed(Decimal("0.80")),
        funding_pct=Decimal("0.80"),
        sharing_pct=Decimal("0.80"),
        margin=reg.margin,
        pricing_strategy=reg.pricing_strategy,
        moic_ladder=reg.moic_ladder,
        eir_given=reg.eir_given,
        eir_taken=reg.eir_taken,
        windows=SettlementWindows(l_op_months=1, lambda_=2),
        leverage=reg.leverage,
        per_period_cap=reg.per_period_cap,
        commitment_amount=reg.commitment_amount,
        threshold=reg.threshold,
        winddown=reg.winddown,
    )


def make_collections(
    values: Sequence[Decimal],
    cohort_month: date = JUNE_2026,
    *,
    company_id: str = "SK011",
) -> CollectionsMatrix:
    """A collections matrix for one cohort: ``values[k]`` is collected at age ``k``."""
    cells = tuple(
        CollectionsCell(
            company_id=company_id,
            cohort_month=cohort_month,
            period_month=month_plus(cohort_month, age),
            collections=value,
        )
        for age, value in enumerate(values)
    )
    meta = CollectionsMeta(source="cache", from_cache=True, scanned_bytes=0)
    return CollectionsMatrix(company_id=company_id, cells=cells, meta=meta)


@pytest.fixture
def make_params() -> Callable[..., DealParameters]:
    return make_scenario_a_params


@pytest.fixture
def make_matrix() -> Callable[..., CollectionsMatrix]:
    return make_collections
