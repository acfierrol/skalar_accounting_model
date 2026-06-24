"""Domain-model validation: bands, percents, strict floats, frozen, settlement windows."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from skalar_capital_mechanics import (
    DealParameters,
    FundingBand,
    LeverageStructure,
    MoicLadder,
    PerPeriodCap,
    PricingStrategyKind,
    SettlementWindows,
    SharingBand,
    ThresholdExit,
    ThresholdMechanic,
    ThresholdSpec,
    ThresholdTiming,
    WindDownSpec,
)


def _moic() -> MoicLadder:
    return MoicLadder(
        base_multiple=Decimal("1.08"),
        base_payback_months=4,
        multiple_step=Decimal("0.014"),
        max_multiple=Decimal("1.60"),
    )


def _threshold() -> ThresholdSpec:
    return ThresholdSpec(
        mechanic=ThresholdMechanic.INCREMENTAL,
        timing=ThresholdTiming.ANY_DAY,
        exit=ThresholdExit.BREAKEVEN,
        checkpoints=((0, Decimal("0.16")), (1, Decimal("0.25")), (2, Decimal("0.31"))),
        delta_pct=Decimal("0.05"),
        delta_from_age=4,
    )


def _deal(**overrides: object) -> DealParameters:
    base: dict[str, object] = {
        "company_id": "SK011",
        "cohort_month": date(2026, 6, 1),
        "funding_band": FundingBand.fixed(Decimal("0.80")),
        "sharing_band": SharingBand.fixed(Decimal("0.80")),
        "funding_pct": Decimal("0.80"),
        "sharing_pct": Decimal("0.80"),
        "margin": Decimal("0.45"),
        "pricing_strategy": PricingStrategyKind.MOIC_LADDER,
        "moic_ladder": _moic(),
        "eir_given": Decimal("0.25"),
        "eir_taken": Decimal("0.16"),
        "windows": SettlementWindows.from_day_windows(l_op_months=1, l_c_days=30, l_s_days=30),
        "leverage": LeverageStructure(),
        "per_period_cap": PerPeriodCap(
            dollar_cap=Decimal("500000"), growth_cap_pct=Decimal("0.20")
        ),
        "commitment_amount": Decimal("6000000"),
        "threshold": _threshold(),
        "winddown": WindDownSpec(trailing_months=3, threshold_pct=Decimal("0.05")),
    }
    base.update(overrides)
    return DealParameters(**base)  # type: ignore[arg-type]


# --- funding / sharing bands -------------------------------------------------


@pytest.mark.parametrize(
    ("f_min", "f_max"),
    [("0", "0.8"), ("0.9", "0.8"), ("0.8", "1.0"), ("1.2", "1.5")],
)
def test_funding_band_invalid(f_min: str, f_max: str) -> None:
    with pytest.raises(ValidationError):
        FundingBand(f_min=Decimal(f_min), f_max=Decimal(f_max))


def test_funding_band_rejects_float() -> None:
    with pytest.raises(ValidationError):
        FundingBand(f_min=0.8, f_max=0.8)  # type: ignore[arg-type]


def test_pct_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        SharingBand(s_min=Decimal("0.5"), s_max=Decimal("1.5"))


# --- settlement windows (KB §5.3) -------------------------------------------


def test_windows_net60_monthly() -> None:
    w = SettlementWindows.from_day_windows(l_op_months=1, l_c_days=30, l_s_days=30)
    assert w.lambda_ == 2
    assert w.delta == 3


def test_windows_net30_monthly() -> None:
    w = SettlementWindows.from_day_windows(l_op_months=1, l_c_days=14, l_s_days=14)
    assert w.lambda_ == 1
    assert w.delta == 2


def test_windows_net90_quarterly() -> None:
    w = SettlementWindows.from_day_windows(l_op_months=3, l_c_days=45, l_s_days=45)
    assert w.lambda_ == 1
    assert w.delta == 2


# --- MoicLadder --------------------------------------------------------------


def test_moic_ladder_base_exceeds_max() -> None:
    with pytest.raises(ValidationError):
        MoicLadder(
            base_multiple=Decimal("2.0"),
            base_payback_months=4,
            multiple_step=Decimal("0.014"),
            max_multiple=Decimal("1.60"),
        )


# --- DealParameters ----------------------------------------------------------


def test_valid_deal_scenario_a() -> None:
    deal = _deal()
    assert deal.funding_pct == Decimal("0.80")
    assert deal.windows.delta == 3
    assert deal.leverage.gc_funding_pct == Decimal("0.95")


def test_deal_frozen() -> None:
    deal = _deal()
    with pytest.raises(ValidationError):
        deal.funding_pct = Decimal("0.5")  # type: ignore[misc]


def test_deal_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        _deal(unexpected_field=1)


def test_deal_funding_pct_outside_band() -> None:
    with pytest.raises(ValidationError):
        _deal(funding_pct=Decimal("0.40"))  # band is fixed at 0.80


def test_deal_moic_required_for_ladder() -> None:
    with pytest.raises(ValidationError):
        _deal(moic_ladder=None)


def test_scenario_b_band_deal() -> None:
    deal = _deal(
        funding_band=FundingBand(f_min=Decimal("0.40"), f_max=Decimal("0.70")),
        sharing_band=SharingBand(s_min=Decimal("0.40"), s_max=Decimal("0.70")),
        funding_pct=Decimal("0.55"),
        sharing_pct=Decimal("0.55"),
        margin=Decimal("0.80"),
        windows=SettlementWindows.from_day_windows(l_op_months=1, l_c_days=14, l_s_days=14),
    )
    assert deal.windows.delta == 2
    assert deal.funding_band.f_min == Decimal("0.40")
