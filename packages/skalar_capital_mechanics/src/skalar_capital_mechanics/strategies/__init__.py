"""Strategy protocols + registries (foundation §5)."""

from __future__ import annotations

from .protocols import (
    DayCountStrategy,
    PricingStrategy,
    ThresholdMechanicStrategy,
    ThresholdRequirement,
)
from .registry import (
    Registry,
    day_count_strategies,
    pricing_strategies,
    threshold_mechanics,
)

__all__ = [
    "DayCountStrategy",
    "PricingStrategy",
    "Registry",
    "ThresholdMechanicStrategy",
    "ThresholdRequirement",
    "day_count_strategies",
    "pricing_strategies",
    "threshold_mechanics",
]
