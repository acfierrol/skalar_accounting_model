"""Enumerations for strategy elections and cash-event kinds (KB §3, §5, §8)."""

from __future__ import annotations

from enum import StrEnum


class PricingStrategyKind(StrEnum):
    """Return-pricing strategy family (KB §7; foundation §5)."""

    MOIC_LADDER = "moic_ladder"  # default: payback MOIC ladder (b, a_b, step, M)
    FLAT_MULTIPLE = "flat_multiple"
    PERFORMANCE_INDEXED = "performance_indexed"


class ThresholdMechanic(StrEnum):
    """Threshold-test mechanic (KB §3.3)."""

    LINEAR_LADDER = "I"  # Mechanic I — company default
    INCREMENTAL = "II"  # Mechanic II — per-period incremental delta


class ThresholdTiming(StrEnum):
    """When a breach is recognised (KB §3.3)."""

    ANY_DAY = "any_day"  # canonical default
    PERIOD_END = "period_end"  # term-sheet style


class ThresholdExit(StrEnum):
    """When a cohort exits testing (KB §3.3)."""

    BREAKEVEN = "breakeven"  # canonical default (cum >= 100% of origin spend)
    RETURN_CAP = "return_cap"  # term-sheet style (tested while outstanding)


class ThresholdBasis(StrEnum):
    """Which ratio a single threshold requirement tests (KB §3.3 / def:basis)."""

    CUMULATIVE = "cumulative"  # cum(m) = sum_{x<=m} R / origin_spend
    INCREMENTAL = "incremental"  # inc(m) = R(m) / origin_spend


class DayCount(StrEnum):
    """Day-count convention per accounting book (foundation §4)."""

    MONTH_DAYS_365 = "month_days_365"  # debt given: calendar days in the month / 365
    ACTUAL_365 = "actual_365"  # debt taken: actual days between dates / 365


class CashEventKind(StrEnum):
    """Signed cash-event kinds; inflow to Skalar > 0, outflow < 0 (foundation §3)."""

    FUND_DOWN = "FUND_DOWN"  # downstream funding outflow
    SHARE_UP = "SHARE_UP"  # downstream sharing inflow
    ADJUST = "ADJUST"  # funding adjustment (standalone)
    PFA = "PFA"  # upstream periodic funding amount (GC inflow)
    REMIT = "REMIT"  # upstream remittance outflow
    FA_UP = "FA_UP"  # upstream funding adjustment
    WIND_DOWN = "WIND_DOWN"  # wind-down payment
