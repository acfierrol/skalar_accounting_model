"""Resolver (live BigQuery): SK011 parameters. Marked ``bq``; skipped by default."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from skalar_capital_mechanics import load_company, resolve_deal_parameters
from skalar_data_access import BigQueryClient, Settings

pytestmark = pytest.mark.bq


def test_resolve_sk011_live() -> None:
    deal = resolve_deal_parameters(BigQueryClient(Settings()), "SK011", date(2026, 6, 1))
    assert deal.funding_pct == Decimal("0.80")
    assert deal.sharing_pct == Decimal("0.80")
    assert deal.windows.lambda_ == 2
    assert deal.windows.delta == 3


def test_load_company_live() -> None:
    assert load_company(BigQueryClient(Settings()), "SK011").name == "Kindroid"
