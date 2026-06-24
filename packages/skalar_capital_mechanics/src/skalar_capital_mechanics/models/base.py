"""Base model + money/percent value types.

All domain models are frozen, forbid extra fields, and validate in **strict** mode —
so a ``float`` passed where a ``Decimal`` is expected is rejected. Convert at the IO
edge with ``Decimal(str(x))``; never ``Decimal(float)``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class FrozenModel(BaseModel):
    """Immutable, strict, extra-forbidding base for every domain model."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


# Money is an exact decimal amount (USD). Percent is a fraction in [0, 1].
Money = Decimal
Pct = Annotated[Decimal, Field(ge=0, le=1)]
