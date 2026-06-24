"""Strategy seams (foundation §5). Protocols + their value types.

Each is a :class:`typing.Protocol` resolved per deal from a registry, so adding a strategy
never touches existing call sites. Definitions land in Phase 1; default implementations in
Phase 3 (:mod:`skalar_capital_mechanics.income`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol, runtime_checkable

from ..models.enums import ThresholdBasis
from ..models.parameters import DealParameters, ThresholdSpec


@runtime_checkable
class PricingStrategy(Protocol):
    """Return-cap pricing: ``return_cap = MOIC(payback) * effective_funding`` (KB §7)."""

    def return_cap(
        self, params: DealParameters, effective_funding: Decimal, payback_months: int
    ) -> Decimal: ...


@runtime_checkable
class DayCountStrategy(Protocol):
    """Year fraction between consecutive dated periods for EIR accrual (foundation §4)."""

    def fraction(self, prev: date, cur: date) -> Decimal: ...


@dataclass(frozen=True)
class ThresholdRequirement:
    """One floor a mechanic imposes at a given age: ``actual(basis) >= required`` (KB §3.3).

    A mechanic may impose several at one age (e.g. a cumulative checkpoint *and* an
    incremental delta), or none (an untested age between non-consecutive checkpoints).
    """

    basis: ThresholdBasis
    required: Decimal


@runtime_checkable
class ThresholdMechanicStrategy(Protocol):
    """The floors a cohort must clear at ``age`` (KB §3.3).

    The mechanic owns *what* must hold; the evaluator owns *whether* the cohort's ratios
    clear it. Returning an empty tuple means the age carries no requirement.
    """

    def requirements(self, spec: ThresholdSpec, age: int) -> tuple[ThresholdRequirement, ...]: ...
