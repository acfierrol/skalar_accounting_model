"""Runtime configuration for the data-access layer (env-driven, frozen)."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 50 GiB: a deliberately generous default. Cost is not a constraint for this project,
# so the cap is a visibility/safety rail (a full `payments` scan is ~14 GB), never the
# normal blocker. Lower it via SKALAR_MAX_SCAN_BYTES to enforce stricter discipline.
_DEFAULT_MAX_SCAN_BYTES = 50 * 1024**3


class Settings(BaseSettings):
    """Connection + cost settings, overridable via ``SKALAR_*`` environment variables.

    Auth is keyless (ADC). ``impersonate_service_account`` toggles *in-code*
    impersonation; leave it ``None`` when ADC already resolves the target identity
    (e.g. ``gcloud auth application-default login --impersonate-service-account=...``),
    otherwise double-impersonation fails with a token-creator error.
    """

    model_config = SettingsConfigDict(env_prefix="SKALAR_", frozen=True, extra="ignore")

    project: str = "skalar-data"
    dataset: str = "Skalar"  # case-sensitive in BigQuery
    location: str = "US"
    quota_project: str = "skalar-data"
    max_scan_bytes: int = Field(default=_DEFAULT_MAX_SCAN_BYTES, ge=0)
    impersonate_service_account: str | None = None
    cache_dir: Path | None = None
