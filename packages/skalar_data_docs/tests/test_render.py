"""Markdown renderer (pure function, no BigQuery)."""

from __future__ import annotations

from skalar_data_access import ColumnSpec, TableProfile
from skalar_data_docs import render_table_doc


def _profile() -> TableProfile:
    return TableProfile(
        table_id="payments",
        num_rows=10,
        num_bytes=2048,
        columns=(
            ColumnSpec(name="usd_amount", field_type="FLOAT64", is_nullable=True),
            ColumnSpec(name="company_id", field_type="STRING", is_nullable=False),
        ),
    )


def test_render_full() -> None:
    out = render_table_doc(
        _profile(),
        null_fractions={"usd_amount": 0.2},
        grain="one row per payment",
        role="collections source",
    )
    assert "# `payments`" in out
    assert "one row per payment" in out
    assert "collections source" in out
    assert "20.00%" in out  # usd_amount null fraction rendered as percent
    # company_id has no null fraction (em-dash) and is not nullable
    assert "| `company_id` | STRING | no | — |" in out
    assert "| `usd_amount` | FLOAT64 | yes | 20.00% |" in out


def test_render_omits_optional_sections() -> None:
    out = render_table_doc(_profile())
    assert "**Grain.**" not in out
    assert "**Role in the pipeline.**" not in out
    # null fractions absent -> all columns show the em-dash
    assert "| `usd_amount` | FLOAT64 | yes | — |" in out
