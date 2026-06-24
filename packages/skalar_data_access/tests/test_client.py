"""BigQueryClient cost discipline + guard short-circuit (fake runner, no network)."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from skalar_data_access import (
    BigQueryClient,
    ScalarParam,
    ScanBudgetExceededError,
    Settings,
    WriteAttemptError,
)
from skalar_data_access.client import RunResult


@dataclass
class FakeRunner:
    """Records calls; returns canned results. Satisfies the QueryRunner protocol."""

    dry_run_bytes: int = 0
    rows: tuple[dict[str, object], ...] = ()
    calls: list[tuple[str, tuple[ScalarParam, ...], bool]] = field(default_factory=list)

    def run(self, sql: str, params: tuple[ScalarParam, ...], *, dry_run: bool) -> RunResult:
        self.calls.append((sql, params, dry_run))
        if dry_run:
            return RunResult(total_bytes_processed=self.dry_run_bytes, rows=())
        return RunResult(total_bytes_processed=self.dry_run_bytes, rows=self.rows)

    @property
    def non_dry_calls(self) -> list[tuple[str, tuple[ScalarParam, ...], bool]]:
        return [c for c in self.calls if c[2] is False]


def test_query_happy_path() -> None:
    runner = FakeRunner(dry_run_bytes=1000, rows=({"n": 1},))
    client = BigQueryClient(Settings(max_scan_bytes=10_000), runner=runner)
    outcome = client.query("SELECT 1 AS n")
    assert outcome.rows == ({"n": 1},)
    assert outcome.scanned_bytes == 1000
    assert [c[2] for c in runner.calls] == [True, False]  # estimate, then execute


def test_estimate_bytes() -> None:
    runner = FakeRunner(dry_run_bytes=4096)
    client = BigQueryClient(Settings(), runner=runner)
    assert client.estimate_bytes("SELECT 1") == 4096
    assert runner.non_dry_calls == []


def test_scan_budget_trips_before_execution() -> None:
    runner = FakeRunner(dry_run_bytes=5_000_000)
    client = BigQueryClient(Settings(max_scan_bytes=1000), runner=runner)
    with pytest.raises(ScanBudgetExceededError):
        client.query("SELECT 1")
    assert runner.non_dry_calls == []  # dry-run happened; actual scan did not


def test_guard_short_circuits_before_runner() -> None:
    runner = FakeRunner()
    client = BigQueryClient(Settings(), runner=runner)
    with pytest.raises(WriteAttemptError):
        client.query("DELETE FROM t")
    assert runner.calls == []  # rejected before any backend call


def test_params_passed_through() -> None:
    runner = FakeRunner(dry_run_bytes=10)
    client = BigQueryClient(Settings(), runner=runner)
    param = ScalarParam.string("company_id", "SK011")
    client.query("SELECT @company_id AS c", (param,))
    assert runner.calls[0][1] == (param,)
