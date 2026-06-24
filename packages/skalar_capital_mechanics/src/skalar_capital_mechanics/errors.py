"""Engine-level errors."""

from __future__ import annotations


class CapitalMechanicsError(Exception):
    """Base class for capital-mechanics engine errors."""


class ResolutionError(CapitalMechanicsError):
    """Raised when deal parameters cannot be resolved (e.g. no election on record)."""
