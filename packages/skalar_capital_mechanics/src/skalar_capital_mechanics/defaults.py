"""The current default regime (KB §3 / scenarios sandbox Scenario A).

Defaults are **data**, not magic numbers at call sites: the resolver pulls from here
wherever the BigQuery source is silent, and any field is overridable per deal. The values
mirror the executed Scenario-A regime; deals with different terms override them.
"""

from __future__ import annotations

from decimal import Decimal

from .models.base import FrozenModel, Money, Pct
from .models.enums import (
    PricingStrategyKind,
    ThresholdExit,
    ThresholdMechanic,
    ThresholdTiming,
)
from .models.parameters import (
    LeverageStructure,
    MoicLadder,
    PerPeriodCap,
    SettlementWindows,
    ThresholdSpec,
    WindDownSpec,
)


class DefaultRegime(FrozenModel):
    """Default values applied where a deal's source data is silent."""

    margin: Pct
    eir_given: Pct
    eir_taken: Pct
    leverage: LeverageStructure
    pricing_strategy: PricingStrategyKind
    moic_ladder: MoicLadder
    windows: SettlementWindows
    per_period_cap: PerPeriodCap
    threshold: ThresholdSpec
    winddown: WindDownSpec
    commitment_amount: Money


def load_defaults() -> DefaultRegime:
    """Return the current default regime (overridable per deal)."""
    return DefaultRegime(
        # Margin is deal-specific and not carried in BigQuery; this is the Scenario-A
        # current-regime default (override per deal once a margin source exists).
        margin=Decimal("0.45"),
        # Per-book EIR rates from foundation §4 ("debt-given r = 0.25, debt-taken r = 0.16").
        # eir_taken also matches the KB upstream 16% XIRR target; eir_given (0.25) must be
        # reconciled against docs/Accounting Model.xlsx in the Phase-5 golden reconciliation.
        eir_given=Decimal("0.25"),
        eir_taken=Decimal("0.16"),
        leverage=LeverageStructure(),  # 0.95 : 0.05, 2.0x ceiling, 16% XIRR
        pricing_strategy=PricingStrategyKind.MOIC_LADDER,
        moic_ladder=MoicLadder(
            base_multiple=Decimal("1.08"),
            base_payback_months=4,
            multiple_step=Decimal("0.014"),
            max_multiple=Decimal("1.60"),
        ),
        # Net-60 monthly => lambda = 2, delta = 3 (matches Kindroid delay_months = 2).
        windows=SettlementWindows.from_day_windows(l_op_months=1, l_c_days=30, l_s_days=30),
        per_period_cap=PerPeriodCap(dollar_cap=Decimal("500000"), growth_cap_pct=Decimal("0.20")),
        # Scenario A (the executed regime, = SK011/Kindroid) elects Mechanic II with this
        # checkpoint grid (scenarios_sandbox §2/§3). Note the KB *generic* company default is
        # Mechanic I (KB §3.3 / §13 inv.18); the mechanic is properly a per-deal election and
        # should move to a per-deal source once one exists — this regime carries the live
        # deal's election so the golden case resolves correctly.
        threshold=ThresholdSpec(
            mechanic=ThresholdMechanic.INCREMENTAL,
            timing=ThresholdTiming.ANY_DAY,
            exit=ThresholdExit.BREAKEVEN,
            checkpoints=(
                (0, Decimal("0.16")),
                (1, Decimal("0.25")),
                (2, Decimal("0.31")),
                (3, Decimal("0.37")),
            ),
            delta_pct=Decimal("0.05"),
            delta_from_age=4,
        ),
        winddown=WindDownSpec(trailing_months=3, threshold_pct=Decimal("0.05")),
        commitment_amount=Decimal("6000000"),
    )
