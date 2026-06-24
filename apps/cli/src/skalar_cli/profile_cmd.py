"""``skalar-profile`` — read-only profiling of the Skalar BigQuery tables."""

from __future__ import annotations

from typing import Annotated

import typer

from skalar_data_access import (
    BigQueryClient,
    Settings,
    list_tables,
    null_profile,
    table_profile,
)
from skalar_data_docs import render_table_doc

app = typer.Typer(add_completion=False, help="Profile Skalar BigQuery tables (read-only).")


def _client() -> BigQueryClient:
    return BigQueryClient(Settings())


@app.command("tables")
def tables_cmd() -> None:
    """List every table in the configured dataset."""
    for name in list_tables(_client()):
        typer.echo(name)


@app.command("show")
def show_cmd(
    table: str,
    nulls: Annotated[bool, typer.Option(help="Include per-column NULL fractions.")] = False,
) -> None:
    """Print schema + size for TABLE (optionally NULL fractions)."""
    client = _client()
    profile = table_profile(client, table)
    typer.echo(f"{profile.table_id}: {profile.num_rows:,} rows / {profile.num_bytes:,} bytes")
    for col in profile.columns:
        flag = "NULLABLE" if col.is_nullable else "REQUIRED"
        typer.echo(f"  {col.name:<34} {col.field_type:<12} {flag}")
    if nulls:
        typer.echo("null fractions:")
        for name, frac in null_profile(client, table).items():
            typer.echo(f"  {name:<34} {frac * 100:6.2f}%")


@app.command("doc")
def doc_cmd(
    table: str,
    grain: Annotated[str, typer.Option(help="One-line grain description.")] = "",
    role: Annotated[str, typer.Option(help="Role in the pipeline.")] = "",
) -> None:
    """Emit a markdown dataset doc for TABLE to stdout."""
    client = _client()
    profile = table_profile(client, table)
    fractions = null_profile(client, table)
    typer.echo(render_table_doc(profile, null_fractions=fractions, grain=grain, role=role))


if __name__ == "__main__":
    app()
