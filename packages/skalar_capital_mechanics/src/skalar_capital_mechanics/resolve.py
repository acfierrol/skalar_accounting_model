"""Resolve per-cohort :class:`DealParameters` from BigQuery + the default regime.

Reads the funding/sharing election + settlement lag from
``origination_collection_percent`` (the deal's authority for elected rates) and fills
everything the source is silent on from :func:`load_defaults`.

The Phase-1 Build spec also lists ``company`` and ``spend`` as inputs. The deal display
name is a separate concern exposed via :func:`load_company` (not needed to resolve
parameters), and per-cohort ``spend`` is not a resolution-time input — the per-period cap
is a policy percentage (``PerPeriodCap.growth_cap_pct``) applied against spend downstream
(Phase 3+). Neither is queried here; both are read where they are actually consumed.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from skalar_data_access import BigQueryClient, ScalarParam

from .defaults import DefaultRegime, load_defaults
from .errors import ResolutionError
from .models.company import Company
from .models.parameters import DealParameters, FundingBand, SettlementWindows, SharingBand

_PERCENT = Decimal(100)


def load_company(client: BigQueryClient, company_id: str) -> Company:
    """Look up a deal's display name."""
    outcome = client.run_template("company", (ScalarParam.string("company_id", company_id),))
    if not outcome.rows:
        raise ResolutionError(f"no company row for {company_id!r}")
    row = outcome.rows[0]
    return Company(company_id=str(row["company_id"]), name=str(row["company_name"]))


def resolve_deal_parameters(
    client: BigQueryClient,
    company_id: str,
    cohort_month: date,
    *,
    defaults: DefaultRegime | None = None,
) -> DealParameters:
    """Resolve the parameters governing ``(company_id, cohort_month)``."""
    regime = defaults if defaults is not None else load_defaults()

    outcome = client.run_template(
        "origination",
        (
            ScalarParam.string("company_id", company_id),
            ScalarParam.date("cohort_month", cohort_month),
        ),
    )
    if not outcome.rows:
        raise ResolutionError(
            f"no funding/sharing election on record for {company_id!r} cohort {cohort_month}"
        )
    row = outcome.rows[0]

    funding_pct = Decimal(int(row["origination_spend_percent"])) / _PERCENT
    sharing_pct = Decimal(int(row["origination_collection_percent"])) / _PERCENT
    delay_months = int(row["delay_months"])

    windows = SettlementWindows(l_op_months=regime.windows.l_op_months, lambda_=delay_months)

    return DealParameters(
        company_id=company_id,
        cohort_month=cohort_month,
        funding_band=FundingBand.fixed(funding_pct),
        sharing_band=SharingBand.fixed(sharing_pct),
        funding_pct=funding_pct,
        sharing_pct=sharing_pct,
        margin=regime.margin,
        pricing_strategy=regime.pricing_strategy,
        moic_ladder=regime.moic_ladder,
        eir_given=regime.eir_given,
        eir_taken=regime.eir_taken,
        windows=windows,
        leverage=regime.leverage,
        per_period_cap=regime.per_period_cap,
        commitment_amount=regime.commitment_amount,
        threshold=regime.threshold,
        winddown=regime.winddown,
    )
