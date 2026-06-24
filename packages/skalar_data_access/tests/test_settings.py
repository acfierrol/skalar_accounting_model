"""Settings: defaults, env overrides, frozen."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from skalar_data_access import Settings


def test_defaults() -> None:
    settings = Settings()
    assert settings.project == "skalar-data"
    assert settings.dataset == "Skalar"  # case-sensitive
    assert settings.location == "US"
    assert settings.quota_project == "skalar-data"
    assert settings.impersonate_service_account is None
    assert settings.max_scan_bytes > 0


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKALAR_PROJECT", "other-proj")
    monkeypatch.setenv("SKALAR_MAX_SCAN_BYTES", "12345")
    monkeypatch.setenv("SKALAR_IMPERSONATE_SERVICE_ACCOUNT", "sa@x.iam.gserviceaccount.com")
    settings = Settings()
    assert settings.project == "other-proj"
    assert settings.max_scan_bytes == 12345
    assert settings.impersonate_service_account == "sa@x.iam.gserviceaccount.com"


def test_frozen() -> None:
    settings = Settings()
    with pytest.raises(ValidationError):
        settings.project = "mutated"  # type: ignore[misc]
