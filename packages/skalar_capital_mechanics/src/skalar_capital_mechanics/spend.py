"""Per-cohort S&M spend from the consolidated ``spend`` table (KB §3.3 basis; §4 funding).

The ``spend`` table holds, per ``(company, cohort_month)``, the expected (``estimated_spend``,
the IR figure) and realized (``actual_spend``) total S&M spend, plus the GC/Skalar leverage
split where tracked. It is the source for two things:

* the **threshold-test denominator** — origin-period *actual* total S&M spend, with expected as
  the fallback while actuals are unavailable (KB §3.3 / def:basis); and
* the **funding sizing** — ``F = funding_pct x expected_spend`` (KB §4), equivalently the
  recorded ``estimated_gc_spend + estimated_skalar_spend`` (the GC advance / PFA plus the Skalar
  pool draw) where the split is present.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from skalar_data_access import BigQueryClient, ScalarParam

from .errors import ResolutionError
from .models.base import FrozenModel, Money
from .models.parameters import DealParameters


def _opt_decimal(value: object) -> Money | None:
    """Convert a BigQuery FLOAT64 to ``Decimal`` at the IO edge; preserve ``NULL`` as ``None``."""
    if value is None:
        return None
    return Decimal(str(value))


class SpendCell(FrozenModel):
    """One ``(company, cohort_month)`` spend row (NULLs preserved)."""

    company_id: str
    cohort_month: date
    estimated_spend: Money | None
    actual_spend: Money | None
    estimated_gc_spend: Money | None
    estimated_skalar_spend: Money | None
    actual_gc_spend: Money | None
    actual_skalar_spend: Money | None

    @property
    def basis_spend(self) -> Money | None:
        """Threshold-test denominator: actual total S&M spend, expected as fallback (KB §3.3)."""
        return self.actual_spend if self.actual_spend is not None else self.estimated_spend


class SpendTable(FrozenModel):
    """A deal's spend rows, ordered by cohort."""

    company_id: str
    cells: tuple[SpendCell, ...]
    scanned_bytes: int

    def cell(self, cohort_month: date) -> SpendCell | None:
        for c in self.cells:
            if c.cohort_month == cohort_month:
                return c
        return None


class CohortFunding(FrozenModel):
    """A cohort's funding decomposition (KB §4, §11): ``funding = gc_advance + skalar_pool``."""

    cohort_month: date
    funding: Money  # F — Skalar's Investment Amount (positive magnitude)
    gc_advance: Money  # PFA — GC's senior advance
    skalar_pool: Money  # Skalar's junior co-investment
    basis_spend: Money  # threshold-test denominator


def build_spend(
    client: BigQueryClient,
    company_id: str,
    *,
    date_range: tuple[date, date] | None = None,
) -> SpendTable:
    """Read the consolidated ``spend`` table for one deal (optionally bounded by cohort month)."""
    params: list[ScalarParam] = [ScalarParam.string("company_id", company_id)]
    context: dict[str, object] = {"date_range": date_range is not None}
    if date_range is not None:
        date_from, date_to = date_range
        params.append(ScalarParam.date("date_from", date_from))
        params.append(ScalarParam.date("date_to", date_to))

    outcome = client.run_template("spend", tuple(params), context=context)
    cells = tuple(
        SpendCell(
            company_id=str(row["company_id"]),
            cohort_month=row["cohort_month"],
            estimated_spend=_opt_decimal(row["estimated_spend"]),
            actual_spend=_opt_decimal(row["actual_spend"]),
            estimated_gc_spend=_opt_decimal(row["estimated_gc_spend"]),
            estimated_skalar_spend=_opt_decimal(row["estimated_skalar_spend"]),
            actual_gc_spend=_opt_decimal(row["actual_gc_spend"]),
            actual_skalar_spend=_opt_decimal(row["actual_skalar_spend"]),
        )
        for row in outcome.rows
    )
    return SpendTable(company_id=company_id, cells=cells, scanned_bytes=outcome.scanned_bytes)


def resolve_funding(
    spend: SpendCell,
    params: DealParameters,
) -> CohortFunding:
    """Size a cohort's funding from its spend row (KB §4, §11).

    Funding ``F`` prefers the recorded GC/Skalar split (``estimated_gc_spend +
    estimated_skalar_spend``); absent the split it is ``funding_pct x expected_spend`` (expected
    falls back to actual). The GC advance / Skalar pool come from the split when present, else
    from the deal's leverage. ``basis_spend`` is the threshold denominator.
    """
    leverage = params.leverage.gc_funding_pct
    gc = spend.estimated_gc_spend
    pool = spend.estimated_skalar_spend
    if gc is not None and pool is not None:
        funding = gc + pool
    else:
        base = spend.estimated_spend if spend.estimated_spend is not None else spend.actual_spend
        if base is None:
            raise ResolutionError(
                f"cannot size funding for {spend.company_id} {spend.cohort_month}: "
                "no estimated or actual spend"
            )
        funding = params.funding_pct * base
        gc = leverage * funding
        pool = funding - gc

    basis = spend.basis_spend
    if basis is None:
        raise ResolutionError(
            f"no spend basis for {spend.company_id} {spend.cohort_month} (threshold denominator)"
        )
    return CohortFunding(
        cohort_month=spend.cohort_month,
        funding=funding,
        gc_advance=gc,
        skalar_pool=pool,
        basis_spend=basis,
    )


def resolve_funding_series(
    spend: SpendTable,
    params_by_cohort: Sequence[tuple[date, DealParameters]],
) -> list[CohortFunding]:
    """Resolve funding for each cohort that has both a spend row and resolved parameters."""
    fundings: list[CohortFunding] = []
    for cohort_month, params in params_by_cohort:
        cell = spend.cell(cohort_month)
        if cell is None:
            continue
        fundings.append(resolve_funding(cell, params))
    return fundings
