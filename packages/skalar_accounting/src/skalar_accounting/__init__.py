"""Skalar cash-basis accounting model (EIR / amortized-cost).

Consumes the capital-mechanics engine's cash events and produces the workbook's books,
consolidation, summary, and a values-only Excel rendering (Phase 5).
"""

from __future__ import annotations

from .consolidate import consolidate
from .daycount import year_fraction
from .eir import amortize
from .excel import write_workbook
from .models import (
    AccountingSummary,
    AmortizationRow,
    AmortizationSchedule,
    Book,
    BookFlow,
    BookKind,
    BookReport,
    ConsolidatedBook,
    DayCount,
    SummaryColumn,
)
from .summary import build_summary
from .xirr import xirr

__version__ = "0.1.0"

__all__ = [
    "AccountingSummary",
    "AmortizationRow",
    "AmortizationSchedule",
    "Book",
    "BookFlow",
    "BookKind",
    "BookReport",
    "ConsolidatedBook",
    "DayCount",
    "SummaryColumn",
    "amortize",
    "build_summary",
    "consolidate",
    "write_workbook",
    "xirr",
    "year_fraction",
]
