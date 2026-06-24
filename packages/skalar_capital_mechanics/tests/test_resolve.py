"""Resolver (offline): reproduce SK011 parameters from a faked origination row."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest

from skalar_capital_mechanics import (
    PricingStrategyKind,
    ResolutionError,
    load_company,
    resolve_deal_parameters,
)
from skalar_data_access import BigQueryClient, Settings
from skalar_data_access.client import RunResult


@dataclass
class FakeRunner:
    """Returns canned rows on execution; empty on dry-run."""

    rows: tuple[dict[str, object], ...] = ()

    def run(self, sql: str, params: object, *, dry_run: bool) -> RunResult:
        return RunResult(total_bytes_processed=0, rows=() if dry_run else self.rows)


def test_resolve_sk011_parameters() -> None:
    runner = FakeRunner(
        rows=(
            {
                "origination_spend_percent": 80,
                "origination_collection_percent": 80,
                "delay_months": 2,
            },
        )
    )
    client = BigQueryClient(Settings(), runner=runner)
    deal = resolve_deal_parameters(client, "SK011", date(2026, 6, 1))

    assert deal.funding_pct == Decimal("0.80")
    assert deal.sharing_pct == Decimal("0.80")
    assert deal.funding_band.f_min == deal.funding_band.f_max == Decimal("0.80")
    assert deal.windows.lambda_ == 2
    assert deal.windows.delta == 3
    assert deal.leverage.gc_funding_pct == Decimal("0.95")
    assert deal.eir_taken == Decimal("0.16")
    assert deal.pricing_strategy is PricingStrategyKind.MOIC_LADDER


@pytest.mark.parametrize(("delay", "lam", "delta"), [(1, 1, 2), (3, 3, 4)])
def test_resolver_delay_months_drives_lambda(delay: int, lam: int, delta: int) -> None:
    # Proves lambda_ comes from the source row, not the default regime (whose delay is 2).
    runner = FakeRunner(
        rows=(
            {
                "origination_spend_percent": 80,
                "origination_collection_percent": 80,
                "delay_months": delay,
            },
        )
    )
    deal = resolve_deal_parameters(
        BigQueryClient(Settings(), runner=runner), "SK011", date(2026, 6, 1)
    )
    assert deal.windows.lambda_ == lam
    assert deal.windows.delta == delta
    assert deal.windows.l_op_months == 1  # l_op comes from the default regime


def test_resolve_missing_election_raises() -> None:
    client = BigQueryClient(Settings(), runner=FakeRunner(rows=()))
    with pytest.raises(ResolutionError):
        resolve_deal_parameters(client, "SK999", date(2026, 6, 1))


def test_load_company() -> None:
    runner = FakeRunner(rows=({"company_id": "SK011", "company_name": "Kindroid"},))
    client = BigQueryClient(Settings(), runner=runner)
    assert load_company(client, "SK011").name == "Kindroid"
