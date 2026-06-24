"""Default regime: documented values + per-field overridability."""

from __future__ import annotations

from decimal import Decimal

from skalar_capital_mechanics import PricingStrategyKind, ThresholdMechanic, load_defaults


def test_default_regime_values() -> None:
    d = load_defaults()
    assert d.leverage.gc_funding_pct == Decimal("0.95")
    assert d.leverage.gc_moic_cap == Decimal("2.0")
    assert d.eir_given == Decimal("0.25")
    assert d.eir_taken == Decimal("0.16")
    assert d.moic_ladder.base_multiple == Decimal("1.08")
    assert d.moic_ladder.max_multiple == Decimal("1.60")
    assert d.windows.lambda_ == 2
    assert d.windows.delta == 3
    assert d.pricing_strategy is PricingStrategyKind.MOIC_LADDER
    # Scenario A (the executed SK011 regime) elects Mechanic II (KB generic default is I).
    assert d.threshold.mechanic is ThresholdMechanic.INCREMENTAL


def test_override_leaves_others_intact() -> None:
    d = load_defaults()
    overridden = d.model_copy(update={"margin": Decimal("0.80")})
    assert overridden.margin == Decimal("0.80")
    assert overridden.eir_taken == d.eir_taken
    assert overridden.leverage == d.leverage
