"""Pipeline orchestration: engine cash events -> accounting books -> workbook + run report.

Wires ``data_access -> capital_mechanics -> accounting``; holds no business logic itself. The
engine's output (per-loan cash-flow books for each accounting book, plus the ledger/netting and
compliance/threshold counts) is consumed by :func:`run_pipeline`, which amortizes, consolidates,
summarizes, writes the values-only workbook, and produces a :class:`RunReport`.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from skalar_accounting import (
    Book,
    BookFlow,
    BookKind,
    BookReport,
    amortize,
    build_summary,
    consolidate,
    write_workbook,
)
from skalar_accounting.models import DayCount
from skalar_capital_mechanics import (
    CashEvent,
    CashEventKind,
    NettingInstruction,
    TransactedLedgerRow,
)

logger = logging.getLogger("skalar_cli.pipeline")

GIVEN_TITLE = "Debt Given By Skalar Cohort Led"
TAKEN_TITLE = "Debt Taken by Skalar Cohort Led"

# Which downstream/upstream event kinds feed the inflow vs outflow leg of each book.
_GIVEN_INFLOW = {CashEventKind.SHARE_UP}
_GIVEN_OUTFLOW = {CashEventKind.FUND_DOWN, CashEventKind.ADJUST}
_TAKEN_INFLOW = {CashEventKind.PFA, CashEventKind.FA_UP}
_TAKEN_OUTFLOW = {CashEventKind.REMIT}


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class EngineOutput(_Frozen):
    """Everything the engine layer hands to accounting for one deal run."""

    company_id: str
    scanned_bytes: int
    given_loans: tuple[Book, ...]
    taken_loans: tuple[Book, ...]
    ledger: tuple[TransactedLedgerRow, ...] = ()
    netting: tuple[NettingInstruction, ...] = ()
    compliance_violations: int = 0
    threshold_breaches: int = 0


class RunReport(_Frozen):
    """A run's headline figures and health checks (foundation §4, §6)."""

    company_id: str
    scanned_bytes: int
    revenue: Decimal
    cost_of_capital: Decimal
    outstanding_lended: Decimal
    outstanding_borrowed: Decimal
    max_check: Decimal
    compliance_violations: int
    threshold_breaches: int
    netting_wires: int
    output_path: str


def books_from_cash_events(
    events: Sequence[CashEvent],
    *,
    kind: BookKind,
    rate: Decimal,
    day_count: DayCount,
    grid: Sequence[date],
) -> list[Book]:
    """Group cash events into per-loan :class:`Book`s over a shared reporting date ``grid``.

    Events are bucketed by ``(cohort_month, date)`` into the inflow/outflow legs appropriate to
    ``kind``; every loan is laid out over the full ``grid`` (zero flows on pure-accrual periods)
    so consolidation aligns column-by-column. ``grid`` carries the accrual tail beyond the last
    event (e.g. a later loan accruing over earlier columns).
    """
    inflow_kinds = _GIVEN_INFLOW if kind is BookKind.DEBT_GIVEN else _TAKEN_INFLOW
    outflow_kinds = _GIVEN_OUTFLOW if kind is BookKind.DEBT_GIVEN else _TAKEN_OUTFLOW
    # Kinds outside these sets (e.g. WIND_DOWN) belong to the transacted ledger, not an EIR book.

    inflow: dict[date, dict[date, Decimal]] = {}
    outflow: dict[date, dict[date, Decimal]] = {}
    for e in events:
        if e.kind in inflow_kinds:
            leg = inflow
        elif e.kind in outflow_kinds:
            leg = outflow
        else:
            continue
        bucket = leg.setdefault(e.cohort_month, {})
        bucket[e.date] = bucket.get(e.date, Decimal(0)) + e.amount

    cohorts = sorted(set(inflow) | set(outflow))
    grid_dates = sorted(grid)
    books: list[Book] = []
    for cohort in cohorts:
        flows = tuple(
            BookFlow(
                date=when,
                inflow=inflow[cohort].get(when, Decimal(0)),
                outflow=outflow[cohort].get(when, Decimal(0)),
            )
            for when in grid_dates
        )
        books.append(
            Book(name=_loan_name(cohort), kind=kind, rate=rate, day_count=day_count, flows=flows)
        )
    return books


def _loan_name(cohort: date) -> str:
    return f"{cohort:%B %Y} Loan"


def _book_report(kind: BookKind, title: str, loans: Sequence[Book]) -> BookReport:
    if not loans:
        raise ValueError(f"{kind} book has no loans to amortize")
    schedules = tuple(amortize(b) for b in loans)
    consolidated = consolidate(list(schedules))
    return BookReport(
        kind=kind,
        title=title,
        rate=loans[0].rate,
        loans=schedules,
        consolidated=consolidated,
    )


def run_pipeline(engine: EngineOutput, out_path: str | Path) -> RunReport:
    """Amortize, consolidate, summarize, write the workbook, and return the run report."""
    logger.info(
        "amortizing %d debt-given + %d debt-taken loans for %s",
        len(engine.given_loans), len(engine.taken_loans), engine.company_id,
    )
    given = _book_report(BookKind.DEBT_GIVEN, GIVEN_TITLE, engine.given_loans)
    taken = _book_report(BookKind.DEBT_TAKEN, TAKEN_TITLE, engine.taken_loans)
    summary = build_summary(given.consolidated, taken.consolidated)

    written = write_workbook(
        out_path,
        summary=summary,
        books=[given, taken],
        ledger=engine.ledger,
        netting=engine.netting,
    )

    logger.info("wrote workbook %s (scanned %d bytes)", written, engine.scanned_bytes)
    last = summary.columns[-1]
    return RunReport(
        company_id=engine.company_id,
        scanned_bytes=engine.scanned_bytes,
        revenue=summary.revenue_total,
        cost_of_capital=summary.cost_of_capital_total,
        outstanding_lended=last.outstanding_lended,
        outstanding_borrowed=last.outstanding_borrowed,
        max_check=summary.max_abs_check,
        compliance_violations=engine.compliance_violations,
        threshold_breaches=engine.threshold_breaches,
        netting_wires=len(engine.netting),
        output_path=str(written),
    )


def format_report(report: RunReport) -> str:
    """Render a run report as a human-readable block for the CLI."""

    def money(d: Decimal) -> str:
        return f"{d:,.2f}"

    lines = [
        f"Run report — {report.company_id}",
        f"  BigQuery scanned bytes : {report.scanned_bytes:,}",
        f"  Revenue                : {money(report.revenue)}",
        f"  Cost of Capital        : {money(report.cost_of_capital)}",
        f"  Outstanding lended     : {money(report.outstanding_lended)}",
        f"  Outstanding borrowed   : {money(report.outstanding_borrowed)}",
        f"  Compliance violations  : {report.compliance_violations}",
        f"  Threshold breaches     : {report.threshold_breaches}",
        f"  Netting wires (to-do)  : {report.netting_wires}",
        f"  Reconciliation |Check| : {money(report.max_check)}",
        f"  Workbook               : {report.output_path}",
    ]
    return "\n".join(lines)


def load_engine_output(path: str | Path) -> EngineOutput:
    """Load a cached engine output (JSON) for a deterministic, offline run.

    Schema: ``company_id``, ``scanned_bytes``, ``debt_given``/``debt_taken`` each with ``rate``,
    ``day_count``, and ``loans`` (``name`` + ``flows`` of ``date``/``inflow``/``outflow``);
    optional ``compliance_violations``/``threshold_breaches`` counts. All money values are strings
    (parsed as ``Decimal``).
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    given = _loans_from_json(data["debt_given"], BookKind.DEBT_GIVEN)
    taken = _loans_from_json(data["debt_taken"], BookKind.DEBT_TAKEN)
    logger.info("loaded cached engine output for %s from %s", data.get("company_id"), path)
    return EngineOutput(
        company_id=str(data["company_id"]),
        scanned_bytes=int(data.get("scanned_bytes", 0)),
        given_loans=tuple(given),
        taken_loans=tuple(taken),
        compliance_violations=int(data.get("compliance_violations", 0)),
        threshold_breaches=int(data.get("threshold_breaches", 0)),
    )


def _loans_from_json(section: dict[str, object], kind: BookKind) -> list[Book]:
    rate = Decimal(str(section["rate"]))
    day_count = DayCount(str(section["day_count"]))
    loans_raw = section["loans"]
    assert isinstance(loans_raw, list)
    books: list[Book] = []
    for loan in loans_raw:
        assert isinstance(loan, dict)
        flows_raw = loan["flows"]
        assert isinstance(flows_raw, list)
        flows = tuple(
            BookFlow(
                date=date.fromisoformat(str(f["date"])),
                inflow=Decimal(str(f["inflow"])),
                outflow=Decimal(str(f["outflow"])),
            )
            for f in flows_raw
        )
        books.append(
            Book(name=str(loan["name"]), kind=kind, rate=rate, day_count=day_count, flows=flows)
        )
    return books
