"""Build the collections matrix from ``payments`` (cost-disciplined) + cohort integrity.

`payments` is the source of truth (only it has ``customer_id``); the result optionally
caches to parquet. Money is converted ``Decimal(str(float))`` at the BigQuery edge.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from skalar_data_access import BigQueryClient, ScalarParam

from . import cache
from .models import (
    CohortIndex,
    CollectionsCell,
    CollectionsMatrix,
    CollectionsMeta,
    quantize_money,
)


def _to_decimal(value: object) -> Decimal:
    if value is None:
        return quantize_money(Decimal(0))
    return quantize_money(Decimal(str(value)))


def build_collections(
    client: BigQueryClient,
    company_id: str,
    date_range: tuple[date, date],
    *,
    cache_dir: Path | None = None,
    use_cache: bool = True,
    exclude_backdated: bool = False,
    closing_month: date | None = None,
) -> CollectionsMatrix:
    """Aggregate ``payments`` into ``collections(company, cohort, period)`` for one deal.

    With ``exclude_backdated=True`` (requires ``closing_month``), customers whose first
    payment precedes closing are dropped (KB §2). Caching is keyed on the parameters, so a
    cached extract is only reused for an identical query.
    """
    date_from, date_to = date_range
    if exclude_backdated and closing_month is None:
        raise ValueError("closing_month is required when exclude_backdated=True")

    key = cache.cache_key(
        company_id,
        date_from,
        date_to,
        exclude_backdated=exclude_backdated,
        closing_month=closing_month,
    )

    if use_cache and cache_dir is not None:
        cached = cache.load(cache_dir, key, company_id, exclude_backdated=exclude_backdated)
        if cached is not None:
            return cached

    params: list[ScalarParam] = [
        ScalarParam.string("company_id", company_id),
        ScalarParam.date("date_from", date_from),
        ScalarParam.date("date_to", date_to),
    ]
    context: dict[str, object] = {"exclude_backdated": exclude_backdated}
    if exclude_backdated:
        params.append(ScalarParam.date("closing_month", closing_month))

    outcome = client.run_template("collections", tuple(params), context=context)
    cells = tuple(
        CollectionsCell(
            company_id=str(row["company_id"]),
            cohort_month=row["cohort_month"],
            period_month=row["payment_month"],
            collections=_to_decimal(row["collections"]),
        )
        for row in outcome.rows
    )
    meta = CollectionsMeta(
        source="payments",
        from_cache=False,
        scanned_bytes=outcome.scanned_bytes,
        exclude_backdated=exclude_backdated,
    )
    matrix = CollectionsMatrix(company_id=company_id, cells=cells, meta=meta)

    if use_cache and cache_dir is not None:
        cache.save(cache_dir, key, matrix)
    return matrix


def cohort_index(client: BigQueryClient, company_id: str, *, closing_month: date) -> CohortIndex:
    """Cohort-assignment integrity for a deal: mismatches + backdated customers (KB §2)."""
    outcome = client.run_template(
        "cohort_integrity",
        (
            ScalarParam.string("company_id", company_id),
            ScalarParam.date("closing_month", closing_month),
        ),
    )
    if not outcome.rows:
        raise ValueError(f"no payments for {company_id!r}")
    row = outcome.rows[0]
    return CohortIndex(
        company_id=company_id,
        closing_month=closing_month,
        payment_rows=int(row["payment_rows"]),
        customers=int(row["customers"]),
        cohort_mismatch_rows=int(row["cohort_mismatch_rows"]),
        backdated_customers=int(row["backdated_customers"]),
        earliest_first_period=row["earliest_first_period"],
        latest_first_period=row["latest_first_period"],
    )
