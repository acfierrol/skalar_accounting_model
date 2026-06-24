"""Cohorts & collections engine (Phase 2)."""

from __future__ import annotations

from .builder import build_collections, cohort_index
from .models import (
    CohortIndex,
    CollectionsCell,
    CollectionsMatrix,
    CollectionsMeta,
)

__all__ = [
    "CohortIndex",
    "CollectionsCell",
    "CollectionsMatrix",
    "CollectionsMeta",
    "build_collections",
    "cohort_index",
]
