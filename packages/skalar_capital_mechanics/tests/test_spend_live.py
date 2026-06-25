"""Spend (live BigQuery): the consolidated table + SK011 funding decomposition.

Marked ``bq``; skipped by default. Asserts the real ``skalar-data.Skalar.spend`` values read for
SK011 (June/July 2026): F = funding_pct x estimated_spend = estimated_gc_spend + skalar_spend.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from skalar_capital_mechanics import build_spend, resolve_deal_parameters, resolve_funding
from skalar_data_access import BigQueryClient, Settings

pytestmark = pytest.mark.bq

JUNE_2026 = date(2026, 6, 1)
JULY_2026 = date(2026, 7, 1)


@pytest.fixture(scope="module")
def client() -> BigQueryClient:
    return BigQueryClient(Settings())


def test_consolidated_spend_spans_all_deals(client: BigQueryClient) -> None:
    # The table is the cross-deal consolidation, not a per-Kindroid slice.
    table = build_spend(client, "SK011")
    assert table.company_id == "SK011"
    assert len(table.cells) >= 30  # SK011 alone has 30 cohorts
    assert any(c.estimated_spend is not None for c in table.cells)
    assert any(c.actual_spend is not None for c in table.cells)


def test_sk011_funding_decomposition_matches_workbook(client: BigQueryClient) -> None:
    table = build_spend(client, "SK011", date_range=(JUNE_2026, JULY_2026))

    june = table.cell(JUNE_2026)
    assert june is not None
    assert june.estimated_spend == Decimal("200000")
    assert june.estimated_gc_spend == Decimal("152000")
    assert june.estimated_skalar_spend == Decimal("8000")

    params = resolve_deal_parameters(client, "SK011", JUNE_2026)
    funding = resolve_funding(june, params)
    assert funding.funding == Decimal("160000")  # F = 0.80 x 200000
    assert funding.gc_advance == Decimal("152000")  # PFA, the workbook debt-taken inflow
    assert funding.skalar_pool == Decimal("8000")
    assert funding.basis_spend == Decimal("200000")  # actual NULL -> estimated fallback

    july = table.cell(JULY_2026)
    assert july is not None
    # origination_collection_percent carries only the June election, so July has no resolvable
    # params — but its recorded GC split sizes the funding directly (funding_pct is moot here).
    july_funding = resolve_funding(july, params)
    assert july_funding.funding == Decimal("200000")  # 190000 + 10000 (recorded split)
    assert july_funding.gc_advance == Decimal("190000")
