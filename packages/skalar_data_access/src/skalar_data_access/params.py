"""Typed scalar query parameters (the only channel for values into SQL)."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

# BigQuery standard-SQL scalar types we use. Values are always bound as
# @parameters; they are never string-interpolated into SQL.
ParamValue = str | int | float | bool | dt.date | dt.datetime | None


@dataclass(frozen=True, slots=True)
class ScalarParam:
    """A single named BigQuery scalar query parameter.

    ``type_`` is a BigQuery standard-SQL type name, e.g. ``"STRING"``, ``"DATE"``,
    ``"INT64"``, ``"FLOAT64"``, ``"BOOL"``, ``"TIMESTAMP"``.
    """

    name: str
    type_: str
    value: ParamValue

    @classmethod
    def string(cls, name: str, value: str | None) -> ScalarParam:
        return cls(name, "STRING", value)

    @classmethod
    def date(cls, name: str, value: dt.date | None) -> ScalarParam:
        return cls(name, "DATE", value)

    @classmethod
    def int64(cls, name: str, value: int | None) -> ScalarParam:
        return cls(name, "INT64", value)
