"""A tiny name -> implementation registry, one per strategy seam.

Empty in Phase 1; default implementations register in Phase 3. Adding a strategy is a
registration, not a call-site change.
"""

from __future__ import annotations

from .protocols import DayCountStrategy, PricingStrategy, ThresholdMechanicStrategy


class Registry[T]:
    """Maps a strategy name to its implementation."""

    def __init__(self, kind: str) -> None:
        self._kind = kind
        self._items: dict[str, T] = {}

    def register(self, name: str, impl: T) -> None:
        if name in self._items:
            raise ValueError(f"{self._kind} strategy already registered: {name!r}")
        self._items[name] = impl

    def get(self, name: str) -> T:
        try:
            return self._items[name]
        except KeyError:
            raise KeyError(f"unknown {self._kind} strategy: {name!r}") from None

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._items))


pricing_strategies: Registry[PricingStrategy] = Registry("pricing")
day_count_strategies: Registry[DayCountStrategy] = Registry("day_count")
threshold_mechanics: Registry[ThresholdMechanicStrategy] = Registry("threshold")
