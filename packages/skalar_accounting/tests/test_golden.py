"""GOLDEN reconciliation against docs/Accounting Model.xlsx — the system's definition of done.

From the workbook's exact cash-event inputs (Kindroid June + July 2026), the EIR engine,
consolidation, and summary must reproduce the workbook's principal / interest / outstanding /
summary / XIRR to the cent, with Check rows ~ 0 and non-converging XIRRs returning None.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

import golden_data as gold  # type: ignore[import-not-found]  # test-local fixture module
import pytest

from skalar_accounting import (
    AmortizationSchedule,
    amortize,
    build_summary,
    consolidate,
)

ABS_TOL = 1e-6  # sub-micro-dollar: Decimal is more precise than the workbook's float


def _close(actual: Sequence[Decimal], expected: Sequence[float]) -> None:
    got = [float(a) for a in actual]
    assert got == pytest.approx(list(expected), abs=ABS_TOL)


def test_june_debt_given_matches_workbook() -> None:
    s = amortize(gold.june_debt_given())
    _close([r.principal for r in s.rows], gold.JUNE_GIVEN_PRINCIPAL)
    _close([r.interest for r in s.rows], gold.JUNE_GIVEN_INTEREST)
    _close([r.outstanding for r in s.rows], gold.JUNE_GIVEN_OUTSTANDING)
    assert s.xirr == pytest.approx(gold.JUNE_GIVEN_XIRR, abs=1e-6)


def test_june_debt_taken_matches_workbook_including_remittance_cap() -> None:
    s = amortize(gold.june_debt_taken())
    _close([r.principal for r in s.rows], gold.JUNE_TAKEN_PRINCIPAL)
    _close([r.interest for r in s.rows], gold.JUNE_TAKEN_INTEREST)
    _close([r.outstanding for r in s.rows], gold.JUNE_TAKEN_OUTSTANDING)
    # The remittance cap binds at Sep-28 (-28157.97 vs the -28500 basis) and zeroes once repaid.
    _close([r.outflow for r in s.rows], gold.JUNE_TAKEN_OUTFLOW)
    assert s.xirr == pytest.approx(gold.JUNE_TAKEN_XIRR, abs=1e-6)


def test_pure_accrual_loans_have_no_xirr() -> None:
    # July loans have single-signed flows → XIRR is #NUM! in the workbook → None here.
    assert amortize(gold.july_debt_given()).xirr is None
    assert amortize(gold.july_debt_taken()).xirr is None


def test_consolidated_books_match_workbook() -> None:
    given = consolidate([amortize(gold.june_debt_given()), amortize(gold.july_debt_given())])
    taken = consolidate([amortize(gold.june_debt_taken()), amortize(gold.july_debt_taken())])

    _close([r.principal for r in given.rows], gold.GIVEN_CONS_PRINCIPAL)
    _close([r.interest for r in given.rows], gold.GIVEN_CONS_INTEREST)
    _close([r.outstanding for r in given.rows], gold.GIVEN_CONS_OUTSTANDING)
    _close([r.interest for r in taken.rows], gold.TAKEN_CONS_INTEREST)
    _close([r.outstanding for r in taken.rows], gold.TAKEN_CONS_OUTSTANDING)
    assert taken.xirr == pytest.approx(gold.TAKEN_CONS_XIRR, abs=1e-6)


def test_summary_matches_workbook_and_checks_reconcile() -> None:
    given = consolidate([amortize(gold.june_debt_given()), amortize(gold.july_debt_given())])
    taken = consolidate([amortize(gold.june_debt_taken()), amortize(gold.july_debt_taken())])
    summary = build_summary(given, taken)

    _close([c.revenue for c in summary.columns], gold.SUMMARY_REVENUE)
    _close([c.cost_of_capital for c in summary.columns], gold.SUMMARY_COGS)
    _close([c.cash_impact for c in summary.columns], gold.SUMMARY_CASH_IMPACT)
    # Every reconciliation Check row is ~ 0.
    assert float(summary.max_abs_check) == pytest.approx(0.0, abs=1e-6)


def _per_row_check(schedule: AmortizationSchedule) -> Decimal:
    """Per-row Check residual |driver - principal - interest|; driver = inflow/outflow by book."""
    worst = Decimal(0)
    for r in schedule.rows:
        driver = r.inflow if schedule.kind.value == "debt_given" else r.outflow
        worst = max(worst, abs(driver - r.principal - r.interest))
    return worst


def test_book_level_check_rows_are_zero() -> None:
    for book in (gold.june_debt_given(), gold.june_debt_taken(),
                 gold.july_debt_given(), gold.july_debt_taken()):
        assert float(_per_row_check(amortize(book))) == pytest.approx(0.0, abs=1e-9)
