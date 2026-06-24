"""Keyless credential resolution via Application Default Credentials (ADC).

Never loads a JSON key file. The service account
``accounting-model-sa@skalar-data.iam.gserviceaccount.com`` holds read-only roles
only. Two paths:

* **Plain ADC / attached SA** (``impersonate_service_account is None``): use the
  ambient ADC identity directly. This also covers the case where ADC was created
  with ``--impersonate-service-account`` (impersonation is already baked into the
  ADC file — do *not* set ``impersonate_service_account`` as well, or token minting
  double-impersonates and fails).
* **In-code impersonation** (``impersonate_service_account`` set): wrap the human
  ADC principal in :class:`google.auth.impersonated_credentials.Credentials`. The
  principal must hold ``roles/iam.serviceAccountTokenCreator`` on the target SA.
"""

from __future__ import annotations

from typing import Any

from .settings import Settings

_BIGQUERY_SCOPE = "https://www.googleapis.com/auth/bigquery"
_CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


def resolve_credentials(settings: Settings) -> tuple[Any, str]:
    """Return ``(credentials, project)`` for constructing a BigQuery client.

    The credentials object is intentionally typed ``Any``: ``google.auth`` ships no
    type information, and the object is opaque to this layer (passed straight to the
    client). This is the single external-untyped boundary.
    """
    import google.auth
    from google.auth import impersonated_credentials

    base, detected_project = google.auth.default(scopes=[_BIGQUERY_SCOPE, _CLOUD_PLATFORM_SCOPE])
    if settings.quota_project and hasattr(base, "with_quota_project"):
        base = base.with_quota_project(settings.quota_project)

    if settings.impersonate_service_account is None:
        return base, (detected_project or settings.project)

    impersonated = impersonated_credentials.Credentials(
        source_credentials=base,
        target_principal=settings.impersonate_service_account,
        target_scopes=[_BIGQUERY_SCOPE],
        lifetime=3600,
    )
    return impersonated, settings.project
