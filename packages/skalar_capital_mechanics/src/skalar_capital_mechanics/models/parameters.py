"""Per-cohort deal parameters (KB §3) and their component value objects.

Money is ``Decimal``; ratios are ``Pct`` (fraction in [0, 1]); all models frozen +
strict. ``DealParameters`` is resolved per ``(company_id, cohort_month)``.
"""

from __future__ import annotations

import math
from datetime import date
from decimal import Decimal
from typing import Self

from pydantic import Field, model_validator

from .base import FrozenModel, Money, Pct
from .enums import PricingStrategyKind, ThresholdExit, ThresholdMechanic, ThresholdTiming

_ZERO = Decimal(0)
_ONE = Decimal(1)
_DAYS_PER_MONTH = 30  # 30/360 calendar convention for the income-due-lag derivation (KB §5.3)


class FundingBand(FrozenModel):
    """Negotiated funding-rate interval ``[f_min, f_max]`` (KB §3.2). Fixed => f_min == f_max."""

    f_min: Pct
    f_max: Pct

    @model_validator(mode="after")
    def _check(self) -> Self:
        if not (_ZERO < self.f_min <= self.f_max < _ONE):
            raise ValueError(f"funding band must satisfy 0 < f_min <= f_max < 1; got {self}")
        return self

    @classmethod
    def fixed(cls, rate: Decimal) -> FundingBand:
        return cls(f_min=rate, f_max=rate)


class SharingBand(FrozenModel):
    """Negotiated sharing-rate interval ``[s_min, s_max]``, independent of funding (KB §3.2)."""

    s_min: Pct
    s_max: Pct

    @model_validator(mode="after")
    def _check(self) -> Self:
        if not (_ZERO < self.s_min <= self.s_max <= _ONE):
            raise ValueError(f"sharing band must satisfy 0 < s_min <= s_max <= 1; got {self}")
        return self

    @classmethod
    def fixed(cls, rate: Decimal) -> SharingBand:
        return cls(s_min=rate, s_max=rate)


class MoicLadder(FrozenModel):
    """Payback MOIC ladder ``(base_multiple b, base_payback_months a_b, step, max M)`` (KB §7.2)."""

    base_multiple: Decimal = Field(gt=0)
    base_payback_months: int = Field(ge=0)
    multiple_step: Decimal = Field(ge=0)
    max_multiple: Decimal = Field(gt=0)

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.base_multiple > self.max_multiple:
            raise ValueError("base_multiple must not exceed max_multiple")
        # A return multiple is a MOIC: it can never cap collections below funded principal.
        # mu >= 1 is what lets payback (cum sharing >= F_eff) be detected before the cap binds
        # (cap = mu x F_eff >= F_eff); the sharing engine relies on it (see income/sharing.py).
        if self.base_multiple < _ONE:
            raise ValueError("base_multiple is a MOIC and must be >= 1")
        return self


class SettlementWindows(FrozenModel):
    """Cash-calendar windows (KB §5). ``lambda_`` is the income-due lag in periods.

    Build from explicit day windows via :meth:`from_day_windows`, or directly from a
    period lag (e.g. BigQuery ``delay_months``). ``delta = lambda_ + 1`` (funding is
    staged one period ahead).
    """

    l_op_months: int = Field(default=1, ge=1)
    lambda_: int = Field(ge=0)
    l_c_days: int | None = Field(default=None, ge=0)
    l_s_days: int | None = Field(default=None, ge=0)

    @property
    def delta(self) -> int:
        return self.lambda_ + 1

    @classmethod
    def from_day_windows(
        cls,
        *,
        l_op_months: int,
        l_c_days: int,
        l_s_days: int,
        days_per_month: int = _DAYS_PER_MONTH,
    ) -> SettlementWindows:
        lam = math.ceil((l_c_days + l_s_days) / (days_per_month * l_op_months))
        return cls(l_op_months=l_op_months, lambda_=lam, l_c_days=l_c_days, l_s_days=l_s_days)


class PerPeriodCap(FrozenModel):
    """Per-period funding cap = ``min(dollar_cap, growth_cap)`` (KB §3.2 / §9.3)."""

    dollar_cap: Money = Field(gt=0)
    growth_cap_pct: Pct


class LeverageStructure(FrozenModel):
    """Senior/junior split + upstream cap legs (KB §11). Default regime: 0.95 : 0.05."""

    gc_funding_pct: Pct = Decimal("0.95")
    gc_moic_cap: Decimal = Field(default=Decimal("2.0"), gt=0)
    gc_irr_target: Pct = Decimal("0.16")


class ThresholdSpec(FrozenModel):
    """Threshold-test election + grid (KB §3.3)."""

    mechanic: ThresholdMechanic
    timing: ThresholdTiming
    exit: ThresholdExit
    checkpoints: tuple[tuple[int, Pct], ...]  # (age_in_periods, required cumulative ratio)
    delta_pct: Pct
    delta_from_age: int = Field(ge=0)

    @model_validator(mode="after")
    def _check(self) -> Self:
        ages = [age for age, _ in self.checkpoints]
        if ages != sorted(ages):
            raise ValueError("threshold checkpoints must be in non-decreasing age order")
        return self


class WindDownSpec(FrozenModel):
    """Wind-down trigger (KB §9.2): fraction of trailing-N-month Reference Income."""

    trailing_months: int = Field(default=3, ge=1)
    threshold_pct: Pct


class DealParameters(FrozenModel):
    """Fully-resolved parameters for one ``(company_id, cohort_month)`` (KB §3).

    ``funding_pct`` / ``sharing_pct`` are the rates elected for *this* cohort; the bands
    record the negotiated intervals they must fall within (fixed deals: degenerate bands).
    """

    company_id: str
    cohort_month: date
    funding_band: FundingBand
    sharing_band: SharingBand
    funding_pct: Pct
    sharing_pct: Pct
    margin: Pct
    pricing_strategy: PricingStrategyKind
    moic_ladder: MoicLadder | None
    eir_given: Pct
    eir_taken: Pct
    windows: SettlementWindows
    leverage: LeverageStructure
    per_period_cap: PerPeriodCap
    commitment_amount: Money = Field(gt=0)
    threshold: ThresholdSpec
    winddown: WindDownSpec
    income_scope: str | None = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        if not (self.funding_band.f_min <= self.funding_pct <= self.funding_band.f_max):
            raise ValueError("funding_pct lies outside funding_band")
        if not (self.sharing_band.s_min <= self.sharing_pct <= self.sharing_band.s_max):
            raise ValueError("sharing_pct lies outside sharing_band")
        if self.pricing_strategy is PricingStrategyKind.MOIC_LADDER and self.moic_ladder is None:
            raise ValueError("MOIC_LADDER pricing requires moic_ladder parameters")
        return self
