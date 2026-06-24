"""Funding compliance: per-period cap (dollar/growth legs), commitment cap, deemed minimum."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal

from skalar_capital_mechanics import (
    ComplianceViolationKind,
    DealParameters,
    FundingBand,
    FundingRequest,
    PerPeriodCap,
    SharingBand,
    check_compliance,
)

JAN = date(2026, 1, 1)
FEB = date(2026, 2, 1)


def _req(month: date, funding: str, spend: str, *, expected: str | None = None) -> FundingRequest:
    return FundingRequest(
        period_month=month,
        requested_funding=Decimal(funding),
        actual_spend=Decimal(spend),
        expected_sm_spend=Decimal(expected) if expected is not None else None,
    )


def _scenario_b_params(
    make_params: Callable[..., DealParameters], *, funding_pct: str
) -> DealParameters:
    """Scenario-B regime (scenarios_sandbox §2): funding band [0.40, 0.70] company-elected per
    period, per-period cap ``min($835k, 10% spend growth)``. ``funding_pct`` is the cohort's
    elected/default rate (the rate the *old* funding-dollar growth leg keyed off)."""
    rate = Decimal(funding_pct)
    return make_params().model_copy(
        update={
            "funding_band": FundingBand(f_min=Decimal("0.40"), f_max=Decimal("0.70")),
            "sharing_band": SharingBand(s_min=Decimal("0.40"), s_max=Decimal("0.70")),
            "funding_pct": rate,
            "sharing_pct": rate,
            "per_period_cap": PerPeriodCap(
                dollar_cap=Decimal("835000"), growth_cap_pct=Decimal("0.10")
            ),
        }
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
    # Prior spend 100k, 20% growth cap ⇒ spend ceiling 120k. Period-2 spend 150k (50% growth)
    # breaches the growth obligation. (Fixed-rate f=0.80: F = 0.80 x spend, so the spend test
    # coincides with the old funding-dollar leg — the deal stays flagged in FEB.)
    requests = [_req(JAN, "80000", "100000"), _req(FEB, "120000", "150000")]
    report = check_compliance(requests, make_params())
    caps = report.of_kind(ComplianceViolationKind.PER_PERIOD_CAP)
    assert len(caps) == 1
    assert caps[0].period_month == FEB
    assert caps[0].requested == Decimal("150000")  # expected S&M spend under test
    assert caps[0].limit == Decimal("120000")  # prior 100k x 1.20
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


# --- Scenario-B banded / company-elected-rate deals (the case the funding-dollar leg got wrong) ---


def test_banded_growth_no_false_positive(make_params: Callable[..., DealParameters]) -> None:
    # Band [0.40, 0.70] electing the TOP rate (0.70). Spend grows 100k -> 110k = exactly the 10%
    # cap, so there is no growth breach. The old funding-dollar leg (cohort default 0.40 x 100k
    # x 1.10 = 44k) would have wrongly flagged F = 0.70 x 110k = 77k. The spend test stays clean.
    params = _scenario_b_params(make_params, funding_pct="0.40")
    requests = [_req(JAN, "70000", "100000"), _req(FEB, "77000", "110000")]
    report = check_compliance(requests, params)
    assert report.of_kind(ComplianceViolationKind.PER_PERIOD_CAP) == ()
    assert report.ok


def test_banded_growth_no_false_negative(make_params: Callable[..., DealParameters]) -> None:
    # Band [0.40, 0.70] electing the BOTTOM rate (0.40). Spend jumps 100k -> 150k (50% > 10%
    # cap): a real breach. The old leg (cohort default 0.70 x 100k x 1.10 = 77k) would have
    # missed F = 0.40 x 150k = 60k. The spend test catches it. An explicit 0.40 floor keeps the
    # deliberately low request off the deemed-minimum leg.
    params = _scenario_b_params(make_params, funding_pct="0.70")
    requests = [_req(JAN, "40000", "100000"), _req(FEB, "60000", "150000")]
    report = check_compliance(requests, params, deemed_minimum_pct=Decimal("0.40"))
    caps = report.of_kind(ComplianceViolationKind.PER_PERIOD_CAP)
    assert len(caps) == 1
    assert caps[0].period_month == FEB
    assert caps[0].limit == Decimal("110000")  # prior 100k x 1.10
    assert "growth" in caps[0].detail


def test_banded_growth_keys_off_expected_spend(
    make_params: Callable[..., DealParameters],
) -> None:
    # F = f x EXPECTED spend (KB §4), so the growth obligation reads expected, not realised,
    # spend. The IR claims expected 150k (breaching the 110k ceiling) while actual lands at 105k
    # (within it): the funded obligation breaches, so a growth finding must fire on the expected.
    params = _scenario_b_params(make_params, funding_pct="0.40")
    requests = [_req(JAN, "40000", "100000"), _req(FEB, "60000", "105000", expected="150000")]
    report = check_compliance(requests, params)
    caps = report.of_kind(ComplianceViolationKind.PER_PERIOD_CAP)
    assert len(caps) == 1
    assert caps[0].period_month == FEB
    assert caps[0].requested == Decimal("150000")  # the expected spend, not the 105k actual
    assert caps[0].limit == Decimal("110000")
