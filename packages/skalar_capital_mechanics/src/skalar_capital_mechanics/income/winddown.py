"""Downstream wind-down (KB §9.2 / def:winddown).

If a company-initiated cancellation affects more than ``winddown_threshold`` of an open
cohort's trailing-3-month Reference Income, the company owes Skalar a payment proportional to
the cohort's remaining exposure:

```
affected_proportion = ref_income_cancelled_3m / ref_income_total_3m
outstanding_exposure = return_cap - cumulative S~
payment              = outstanding_exposure x affected_proportion   (only when triggered)
```

Applies only to **company-initiated** cancellations — not end-customer churn, not credit
deterioration, and **not** terminations from the company enforcing its published safety,
content, or acceptable-use policies in the ordinary course. The caller passes Reference Income
already net of those carve-outs.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ..models.parameters import WindDownSpec
from .models import WindDownAssessment

_ZERO = Decimal(0)


def winddown_payment(
    spec: WindDownSpec,
    *,
    cohort_month: date,
    return_cap: Decimal,
    cumulative_collected: Decimal,
    ref_income_cancelled_3m: Decimal,
    ref_income_total_3m: Decimal,
) -> WindDownAssessment:
    """Assess the wind-down trigger and payment for one open cohort (KB §9.2)."""
    affected = (
        _ZERO if ref_income_total_3m <= _ZERO else ref_income_cancelled_3m / ref_income_total_3m
    )
    outstanding_exposure = max(_ZERO, return_cap - cumulative_collected)
    triggered = affected > spec.threshold_pct
    payment = outstanding_exposure * affected if triggered else _ZERO
    return WindDownAssessment(
        cohort_month=cohort_month,
        affected_proportion=affected,
        outstanding_exposure=outstanding_exposure,
        triggered=triggered,
        payment=payment,
    )
