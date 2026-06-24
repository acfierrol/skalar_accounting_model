"""Parquet cache for collections extracts (pyarrow; money as ``decimal128``).

Money round-trips losslessly as Arrow ``decimal128(38, 6)`` (the 6-dp money quantum) —
never as float. The cache key is a stable hash of every query input that changes the
result: ``(company_id, date range, exclude_backdated, closing_month, template version)``.
"""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .models import CollectionsCell, CollectionsMatrix, CollectionsMeta, quantize_money

# Bump when collections.sql.jinja semantics change, to invalidate stale caches.
TEMPLATE_VERSION = "v1"

# Matches the 6-dp money normalisation in models.quantize_money.
_MONEY_TYPE = pa.decimal128(38, 6)


def cache_key(
    company_id: str,
    date_from: date,
    date_to: date,
    *,
    exclude_backdated: bool,
    closing_month: date | None = None,
    template_version: str = TEMPLATE_VERSION,
) -> str:
    # closing_month changes the eligible-customer set when exclude_backdated is true, so it
    # is part of the key: omitting it would let two different queries collide on one extract.
    raw = (
        f"{company_id}|{date_from}|{date_to}|{exclude_backdated}"
        f"|{closing_month.isoformat() if closing_month else 'none'}|{template_version}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _path(cache_dir: Path, company_id: str, key: str) -> Path:
    return cache_dir / f"collections_{company_id}_{key}.parquet"


def save(cache_dir: Path, key: str, matrix: CollectionsMatrix) -> Path:
    """Write a collections matrix to parquet; return the file path."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    table = pa.table(
        {
            "company_id": pa.array([c.company_id for c in matrix.cells], pa.string()),
            "cohort_month": pa.array([c.cohort_month for c in matrix.cells], pa.date32()),
            "period_month": pa.array([c.period_month for c in matrix.cells], pa.date32()),
            "collections": pa.array(
                [quantize_money(c.collections) for c in matrix.cells], _MONEY_TYPE
            ),
        }
    )
    path = _path(cache_dir, matrix.company_id, key)
    pq.write_table(table, path)
    return path


def load(
    cache_dir: Path, key: str, company_id: str, *, exclude_backdated: bool = False
) -> CollectionsMatrix | None:
    """Read a cached collections matrix, or ``None`` if not present.

    ``exclude_backdated`` is the provenance flag for the cached extract (known from the
    cache-key inputs); it is restored onto the reconstructed meta so a cache hit reports
    the same provenance as a fresh build.
    """
    path = _path(cache_dir, company_id, key)
    if not path.exists():
        return None
    table = pq.read_table(path)
    records: list[dict[str, object]] = table.to_pylist()
    cells = tuple(
        CollectionsCell(
            company_id=str(r["company_id"]),
            cohort_month=_as_date(r["cohort_month"]),
            period_month=_as_date(r["period_month"]),
            collections=_as_decimal(r["collections"]),
        )
        for r in records
    )
    meta = CollectionsMeta(
        source="cache", from_cache=True, scanned_bytes=0, exclude_backdated=exclude_backdated
    )
    return CollectionsMatrix(company_id=company_id, cells=cells, meta=meta)


def _as_date(value: object) -> date:
    if isinstance(value, date):
        return value
    raise TypeError(f"expected date in cache, got {type(value)!r}")


def _as_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    raise TypeError(f"expected Decimal in cache, got {type(value)!r}")
