"""The Company (deal) identity model."""

from __future__ import annotations

from .base import FrozenModel


class Company(FrozenModel):
    """One deal under one CIA. ``company_id`` is the ``SK0NN`` id."""

    company_id: str
    name: str
