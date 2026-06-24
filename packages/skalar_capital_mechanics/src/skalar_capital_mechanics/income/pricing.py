"""Return-pricing strategies: ``return_cap = MOIC x F_eff`` (KB §7, def:capdn).

The default is the payback MOIC ladder. Pricing is a strategy *family* (KB §7.3 /
def:capdn): a flat multiple drops into the same slot, a performance-indexed schedule could
follow, none touching the call sites that resolve a deal's elected strategy from the registry.
"""

from __future__ import annotations

from decimal import Decimal

from ..models.enums import PricingStrategyKind
from ..models.parameters import DealParameters, MoicLadder
from ..strategies.registry import pricing_strategies

_ZERO = Decimal(0)


def moic_from_ladder(ladder: MoicLadder, payback_months: int) -> Decimal:
    """``mu = min(b + step x max(0, a* - a_b), M)`` (KB §7.2). Monotone, capped at ``M``."""
    excess = max(0, payback_months - ladder.base_payback_months)
    raw = ladder.base_multiple + ladder.multiple_step * Decimal(excess)
    return min(raw, ladder.max_multiple)


class MoicLadderPricing:
    """Default strategy: MOIC rises with payback age and freezes at payback (KB §7.2)."""

    def return_cap(
        self, params: DealParameters, effective_funding: Decimal, payback_months: int
    ) -> Decimal:
        if params.moic_ladder is None:
            raise ValueError("MOIC-ladder pricing requires moic_ladder parameters")
        return moic_from_ladder(params.moic_ladder, payback_months) * effective_funding


class FlatMultiplePricing:
    """Alternative: a fixed multiple regardless of payback age (``mu = base_multiple``)."""

    def return_cap(
        self, params: DealParameters, effective_funding: Decimal, payback_months: int
    ) -> Decimal:
        if params.moic_ladder is None:
            raise ValueError("flat-multiple pricing reads the multiple from moic_ladder")
        return params.moic_ladder.base_multiple * effective_funding


def return_cap(
    params: DealParameters, effective_funding: Decimal, payback_months: int
) -> Decimal:
    """Resolve the deal's elected pricing strategy and return ``mu x F_eff`` (KB §7.3).

    Forced to 0 once ``F_eff <= 0`` (an empty cohort has no cap to track).
    """
    if effective_funding <= _ZERO:
        return _ZERO
    strategy = pricing_strategies.get(params.pricing_strategy.value)
    return strategy.return_cap(params, effective_funding, payback_months)


def _register_defaults() -> None:
    if PricingStrategyKind.MOIC_LADDER.value not in pricing_strategies.names():
        pricing_strategies.register(PricingStrategyKind.MOIC_LADDER.value, MoicLadderPricing())
    if PricingStrategyKind.FLAT_MULTIPLE.value not in pricing_strategies.names():
        pricing_strategies.register(PricingStrategyKind.FLAT_MULTIPLE.value, FlatMultiplePricing())


_register_defaults()
