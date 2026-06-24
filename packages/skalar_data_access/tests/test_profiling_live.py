"""Live BigQuery profiling acceptance (requires ADC). Marked ``bq``; skipped by default."""

from __future__ import annotations

import pytest

from skalar_data_access import (
    BigQueryClient,
    Settings,
    list_tables,
    table_profile,
    table_schema,
)

pytestmark = pytest.mark.bq

EXPECTED_TABLES = {
    "company",
    "investment_ledger",
    "monthly_payments",
    "origination_collection_percent",
    "payment_ledger",
    "payments",
    "spend",
}

# Documented schema for the three previously-undocumented ledgers + payments.
DOCUMENTED_SCHEMA: dict[str, set[str]] = {
    "payments": {"usd_amount", "customer_id", "payment_date", "cohort_month", "company_id"},
    "monthly_payments": {"amount", "cohort_month", "payment_month", "company_id"},
    "investment_ledger": {
        "company_id",
        "cohort_month",
        "amount",
        "gc_amount",
        "skalar_amount",
        "due_date",
        "trade_date",
        "is_adjustment",
    },
    "payment_ledger": {
        "company_id",
        "cohort_month",
        "amount",
        "gc_amount",
        "skalar_amount",
        "due_date",
        "trade_date",
        "type",
    },
}


@pytest.fixture(scope="module")
def client() -> BigQueryClient:
    return BigQueryClient(Settings())


def test_list_tables(client: BigQueryClient) -> None:
    assert EXPECTED_TABLES.issubset(set(list_tables(client)))


@pytest.mark.parametrize("table", sorted(DOCUMENTED_SCHEMA))
def test_documented_schema_matches_live(client: BigQueryClient, table: str) -> None:
    live = {col.name for col in table_schema(client, table)}
    assert live == DOCUMENTED_SCHEMA[table]


def test_payments_size(client: BigQueryClient) -> None:
    profile = table_profile(client, "payments")
    assert profile.num_rows > 100_000_000  # ~160.8M
