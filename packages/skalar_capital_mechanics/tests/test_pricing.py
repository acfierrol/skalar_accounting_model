"""Pricing strategies: MOIC ladder (KB §7.2), flat multiple, registry resolution."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

import pytest
from pydantic import ValidationError

from skalar_capital_mechanics import (
    DealParameters,
    FlatMultiplePricing,
    MoicLadder,
    MoicLadderPricing,
    PricingStrategyKind,
    moic_from_ladder,
    return_cap,
)
from skalar_capital_mechanics.strategies import pricing_strategies

LADDER = MoicLadder(
    base_multiple=Decimal("1.08"),
    base_payback_months=4,
    multiple_step=Decimal("0.014"),
    max_multiple=Decimal("1.60"),
)


@pytest.mark.parametrize(
    ("payback_months", "expected"),
    [
        (0, "1.08"),  # below base age: floored at base multiple
        (4, "1.08"),  # exactly base age
        (6, "1.108"),  # +2 months x 0.014 (the worked-vintage value)
        (10, "1.164"),  # +6 months x 0.014
        (50, "1.60"),  # capped at max_multiple
    ],
)
def test_moic_ladder_curve(payback_months: int, expected: str) -> None:
    assert moic_from_ladder(LADDER, payback_months) == Decimal(expected)


def test_moic_is_monotone_nondecreasing() -> None:
    values = [moic_from_ladder(LADDER, m) for m in range(0, 60)]
    assert values == sorted(values)
    assert max(values) == Decimal("1.60")


def test_return_cap_resolves_default_strategy(
    make_params: Callable[..., DealParameters],
) -> None:
    params = make_params()
    assert params.pricing_strategy is PricingStrategyKind.MOIC_LADDER
    assert return_cap(params, Decimal("160.0"), 6) == Decimal("177.28")


def test_return_cap_zero_when_no_effective_funding(
    make_params: Callable[..., DealParameters],
) -> None:
    assert return_cap(make_params(), Decimal("0"), 6) == Decimal(0)


def test_flat_multiple_ignores_payback(make_params: Callable[..., DealParameters]) -> None:
    pricing = FlatMultiplePricing()
    params = make_params()
    assert pricing.return_cap(params, Decimal("160.0"), 6) == Decimal("172.80")  # 1.08 x 160
    assert pricing.return_cap(params, Decimal("160.0"), 20) == Decimal("172.80")


def test_moic_ladder_rejects_sub_unity_multiple() -> None:
    # mu is a MOIC: a return cap below funded principal is nonsensical and would break the
    # payback-from-theoretical-sharing reasoning in income/sharing.py.
    with pytest.raises(ValidationError, match="must be >= 1"):
        MoicLadder(
            base_multiple=Decimal("0.9"),
            base_payback_months=4,
            multiple_step=Decimal("0.014"),
            max_multiple=Decimal("1.60"),
        )


def test_default_strategies_registered() -> None:
    assert PricingStrategyKind.MOIC_LADDER.value in pricing_strategies.names()
    assert PricingStrategyKind.FLAT_MULTIPLE.value in pricing_strategies.names()
    assert isinstance(
        pricing_strategies.get(PricingStrategyKind.MOIC_LADDER.value), MoicLadderPricing
    )
