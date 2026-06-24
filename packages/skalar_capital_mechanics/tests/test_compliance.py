"""Funding compliance: per-period cap (dollar/growth legs), commitment cap, deemed minimum."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal

from skalar_capital_mechanics import (
    ComplianceViolationKind,
    DealParameters,
    FundingRequest,
    check_compliance,
)

JAN = date(2026, 1, 1)
FEB = date(2026, 2, 1)


def _req(month: date, funding: str, spend: str) -> FundingRequest:
    return FundingRequest(
        period_month=month,
        requested_funding=Decimal(funding),
        actual_spend=Decimal(spend),
    )


def test_clean_history_has_no_violations(make_params: Callable[..., DealParameters]) -> None:
    # 0.80 funding on 100k then 110k spend (10% growth, within the 20% cap); no deeming.
    requests = [_req(JAN, "80000", "100000"), _req(FEB, "88000", "110000")]
    report = check_compliance(requests, make_params())
    assert report.ok
    assert report.violations == ()


def test_dollar_cap_breached(make_params: Callable[..., DealParameters]) -> None:
    # per_period dollar cap is 500k; request 600k against matching spend (no deeming).
    report = check_compliance([_req(JAN, "600000", "750000")], make_params())
    caps = report.of_kind(ComplianceViolationKind.PER_PERIOD_CAP)
    assert len(caps) == 1
    assert caps[0].limit == Decimal("500000")
    assert "dollar" in caps[0].detail
    assert not report.ok


def test_growth_cap_breached(make_params: Callable[..., DealParameters]) -> None:
    # Prior spend 100k ⇒ growth leg = 0.80 x 100k x 1.20 = 96k. Period-2 funding 120k exceeds it.
    requests = [_req(JAN, "80000", "100000"), _req(FEB, "120000", "150000")]
    report = check_compliance(requests, make_params())
    caps = report.of_kind(ComplianceViolationKind.PER_PERIOD_CAP)
    assert len(caps) == 1
    assert caps[0].period_month == FEB
    assert caps[0].limit == Decimal("96000.00")
    assert "growth" in caps[0].detail


def test_commitment_cap_breached(make_params: Callable[..., DealParameters]) -> None:
    params = make_params().model_copy(update={"commitment_amount": Decimal("150000")})
    requests = [_req(JAN, "80000", "100000"), _req(FEB, "88000", "110000")]
    report = check_compliance(requests, params)
    commitments = report.of_kind(ComplianceViolationKind.COMMITMENT_CAP)
    assert len(commitments) == 1
    assert commitments[0].period_month == FEB
    assert commitments[0].requested == Decimal("168000")  # cumulative 80k + 88k
    assert commitments[0].limit == Decimal("150000")


def test_deemed_minimum_is_informational(make_params: Callable[..., DealParameters]) -> None:
    # Request 50k against 100k spend: floor = 0.80 x 100k = 80k. Deemed, but not a cap breach.
    report = check_compliance([_req(JAN, "50000", "100000")], make_params())
    deemed = report.of_kind(ComplianceViolationKind.DEEMED_MINIMUM)
    assert len(deemed) == 1
    assert deemed[0].limit == Decimal("80000.00")
    assert report.ok  # deeming attaches sharing; it is not a compliance breach


def test_deemed_minimum_pct_override(make_params: Callable[..., DealParameters]) -> None:
    # With a 0.50 floor, a 50k request against 100k spend clears (floor = 50k).
    report = check_compliance(
        [_req(JAN, "50000", "100000")], make_params(), deemed_minimum_pct=Decimal("0.50")
    )
    assert report.of_kind(ComplianceViolationKind.DEEMED_MINIMUM) == ()
