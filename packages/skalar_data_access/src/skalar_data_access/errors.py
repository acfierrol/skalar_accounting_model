"""Typed errors for the read-only BigQuery access layer."""

from __future__ import annotations


class DataAccessError(Exception):
    """Base class for all data-access errors."""


class WriteAttemptError(DataAccessError):
    """Raised when SQL is not a single read-only ``SELECT``/``WITH`` statement.

    Defense-in-depth on top of the read-only IAM grant: a write can never reach
    BigQuery because the service account holds only ``dataViewer`` + ``jobUser``,
    but this guard fails fast with a typed error before a job slot is spent.
    """


class ScanBudgetExceededError(DataAccessError):
    """Raised when a query's dry-run byte estimate exceeds the configured budget."""

    def __init__(self, estimated_bytes: int, budget_bytes: int) -> None:
        self.estimated_bytes = estimated_bytes
        self.budget_bytes = budget_bytes
        super().__init__(
            f"query would scan {estimated_bytes:,} bytes, "
            f"exceeding the budget of {budget_bytes:,} bytes"
        )
