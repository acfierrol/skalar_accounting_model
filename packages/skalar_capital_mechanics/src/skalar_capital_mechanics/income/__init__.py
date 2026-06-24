"""Income, sharing, return caps, thresholds, and compliance (KB §3, §7, §9; Phase 3).

Importing this package registers the default pricing (MOIC ladder, flat multiple) and
threshold (Mechanic I, Mechanic II) strategies into the shared registries.
"""

from __future__ import annotations

from .compliance import check_compliance
from .models import (
    ComplianceReport,
    ComplianceViolation,
    ComplianceViolationKind,
    FundingRequest,
    ReferenceIncomeCell,
    ReferenceIncomeSeries,
    SharingCell,
    SharingSchedule,
    ThresholdCheck,
    ThresholdRequirementResult,
    ThresholdResult,
    WindDownAssessment,
)
from .pricing import FlatMultiplePricing, MoicLadderPricing, moic_from_ladder, return_cap
from .reference_income import reference_income
from .sharing import payback_age, sharing_schedule
from .thresholds import (
    IncrementalMechanic,
    LinearLadderMechanic,
    evaluate_threshold,
)
from .winddown import winddown_payment

__all__ = [
    "ComplianceReport",
    "ComplianceViolation",
    "ComplianceViolationKind",
    "FlatMultiplePricing",
    "FundingRequest",
    "IncrementalMechanic",
    "LinearLadderMechanic",
    "MoicLadderPricing",
    "ReferenceIncomeCell",
    "ReferenceIncomeSeries",
    "SharingCell",
    "SharingSchedule",
    "ThresholdCheck",
    "ThresholdRequirementResult",
    "ThresholdResult",
    "WindDownAssessment",
    "check_compliance",
    "evaluate_threshold",
    "moic_from_ladder",
    "payback_age",
    "reference_income",
    "return_cap",
    "sharing_schedule",
    "winddown_payment",
]
