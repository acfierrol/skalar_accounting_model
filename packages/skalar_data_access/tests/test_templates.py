"""Templates render guard-passing SQL with bound params (no value interpolation)."""

from __future__ import annotations

import pytest
from jinja2 import UndefinedError

from skalar_data_access import assert_read_only, render_template


def test_collections_renders_parameterized_sql() -> None:
    sql = render_template(
        "collections", project="skalar-data", dataset="Skalar", exclude_backdated=False
    )
    assert_read_only(sql)  # is a valid read-only query
    # values arrive only as bound params, never interpolated
    assert "@company_id" in sql
    assert "@date_from" in sql
    assert "@date_to" in sql
    assert "DATE_TRUNC(p.payment_date, MONTH)" in sql
    assert "`skalar-data.Skalar.payments`" in sql
    # default path does not include the backdated-exclusion CTE
    assert "eligible" not in sql


def test_collections_exclude_backdated_adds_cte() -> None:
    sql = render_template(
        "collections", project="skalar-data", dataset="Skalar", exclude_backdated=True
    )
    assert_read_only(sql)
    assert "eligible" in sql
    assert "@closing_month" in sql
    assert "first_period_month >= @closing_month" in sql


def test_cohort_integrity_renders() -> None:
    sql = render_template("cohort_integrity", project="skalar-data", dataset="Skalar")
    assert_read_only(sql)
    assert "@company_id" in sql
    assert "@closing_month" in sql
    assert "backdated_customers" in sql


def test_strict_undefined_fails_loud() -> None:
    with pytest.raises(UndefinedError):
        render_template("collections")  # missing project/dataset/exclude_backdated
