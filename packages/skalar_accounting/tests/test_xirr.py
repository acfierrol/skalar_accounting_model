"""XIRR: known rates, sign-change requirement, non-convergence → None."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from skalar_accounting import xirr

D = Decimal


def test_simple_annual_return() -> None:
    # 2020 is a leap year: Jan 1 -> Dec 31 is exactly 365 days, so t = 1 and r = 10%.
    flows = [(date(2020, 1, 1), D("-1000")), (date(2020, 12, 31), D("1100"))]
    result = xirr(flows)
    assert result is not None
    assert result == pytest.approx(0.10, abs=1e-9)


def test_recovers_workbook_june_debt_given_irr() -> None:
    flows = [
        (date(2026, 6, 8), D("-160000")),
        (date(2026, 6, 28), D("-12000")),
        (date(2026, 7, 28), D("90000")),
        (date(2026, 8, 28), D("45000")),
        (date(2026, 9, 28), D("30000")),
        (date(2026, 10, 28), D("22500")),
        (date(2026, 11, 28), D("0")),
    ]
    result = xirr(flows)
    assert result is not None
    assert result == pytest.approx(0.5099311411380766, abs=1e-6)


def test_negative_rate_near_minus_one_via_bisection() -> None:
    # Consolidated debt-taken in the workbook converges to ~ -0.99 (Newton from 0.1 misses it).
    flows = [
        (date(2026, 6, 5), D("152000")),
        (date(2026, 6, 28), D("178600")),
        (date(2026, 7, 28), D("-74100")),
        (date(2026, 8, 28), D("-42750")),
        (date(2026, 9, 28), D("-28157.97047160613")),
        (date(2026, 10, 28), D("0")),
        (date(2026, 11, 28), D("0")),
    ]
    result = xirr(flows)
    assert result is not None
    assert result == pytest.approx(-0.9903501344844701, abs=1e-6)


def test_no_sign_change_returns_none() -> None:
    assert xirr([(date(2026, 6, 1), D("-100")), (date(2026, 7, 1), D("-50"))]) is None
    assert xirr([(date(2026, 6, 1), D("100")), (date(2026, 7, 1), D("50"))]) is None


def test_too_few_flows_returns_none() -> None:
    assert xirr([(date(2026, 6, 1), D("-100"))]) is None
    assert xirr([]) is None
