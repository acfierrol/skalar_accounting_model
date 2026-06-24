"""Collections (live BigQuery): SK011 reconciles to monthly_payments; SK014 backdated.

Marked ``bq``; skipped by default. These scan ``payments`` (several GB).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from skalar_capital_mechanics import build_collections, cohort_index
from skalar_data_access import BigQueryClient, ScalarParam, Settings

pytestmark = pytest.mark.bq

FULL_RANGE = (date(2015, 1, 1), date(2026, 7, 1))
TOLERANCE = Decimal("0.05")


def _monthly_payments(client: BigQueryClient, company_id: str) -> dict[tuple[date, date], Decimal]:
    sql = (
        "SELECT cohort_month, payment_month, SUM(amount) AS amount "
        f"FROM `{client.fq_table('monthly_payments')}` "
        "WHERE company_id = @company_id GROUP BY cohort_month, payment_month"
    )
    outcome = client.query(sql, (ScalarParam.string("company_id", company_id),))
    return {
        (row["cohort_month"], row["payment_month"]): Decimal(str(row["amount"]))
        for row in outcome.rows
    }


@pytest.fixture(scope="module")
def client() -> BigQueryClient:
    return BigQueryClient(Settings())


def test_sk011_reconciles_to_monthly_payments(client: BigQueryClient) -> None:
    expected = _monthly_payments(client, "SK011")
    matrix = build_collections(client, "SK011", FULL_RANGE, use_cache=False)
    actual = {(c.cohort_month, c.period_month): c.collections for c in matrix.cells}

    assert set(actual) == set(expected)
    for key, want in expected.items():
        assert abs(actual[key] - want) <= TOLERANCE, f"{key}: {actual[key]} vs {want}"


def test_sk011_cache_roundtrip_live(client: BigQueryClient, tmp_path: object) -> None:
    from pathlib import Path

    cache_dir = Path(str(tmp_path))
    fresh = build_collections(client, "SK011", FULL_RANGE, cache_dir=cache_dir)
    assert not fresh.meta.from_cache
    cached = build_collections(client, "SK011", FULL_RANGE, cache_dir=cache_dir)
    assert cached.meta.from_cache
    assert cached.total() == fresh.total()


def test_sk014_has_backdated_cohorts(client: BigQueryClient) -> None:
    index = cohort_index(client, "SK014", closing_month=date(2026, 1, 1))
    assert index.payment_rows > 0
    # Materialised cohort_month disagrees with the recomputed first-payment month for
    # many rows: the backdated cohort_month assignments (KB §2 integrity violation).
    assert index.cohort_mismatch_rows > 0
    # Customers whose first payment precedes the closing month -> excluded from funded cohorts.
    assert index.backdated_customers > 0
