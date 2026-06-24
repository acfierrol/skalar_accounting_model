"""skalar-profile CLI (offline, monkeypatched client)."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from skalar_cli import profile_cmd
from skalar_data_access import ColumnSpec, TableProfile

runner = CliRunner()


def test_tables_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(profile_cmd, "_client", lambda: object())
    monkeypatch.setattr(profile_cmd, "list_tables", lambda _client: ("company", "payments"))
    result = runner.invoke(profile_cmd.app, ["tables"])
    assert result.exit_code == 0
    assert "company" in result.stdout
    assert "payments" in result.stdout


def test_show_command_with_nulls(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = TableProfile(
        table_id="payments",
        num_rows=160_857_022,
        num_bytes=14_223_183_136,
        columns=(ColumnSpec(name="usd_amount", field_type="FLOAT64", is_nullable=True),),
    )
    monkeypatch.setattr(profile_cmd, "_client", lambda: object())
    monkeypatch.setattr(profile_cmd, "table_profile", lambda _client, _table: profile)
    monkeypatch.setattr(profile_cmd, "null_profile", lambda _client, _table: {"usd_amount": 0.21})
    result = runner.invoke(profile_cmd.app, ["show", "payments", "--nulls"])
    assert result.exit_code == 0
    assert "160,857,022" in result.stdout
    assert "usd_amount" in result.stdout
    assert "21.00%" in result.stdout
