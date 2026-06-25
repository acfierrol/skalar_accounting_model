"""``skalar-accounting`` — run the full pipeline and write the accounting workbook.

The CLI only wires packages (``data_access -> capital_mechanics -> accounting``); all business
logic lives in those packages. The engine output is loaded from a cached fixture (``--cache``)
for deterministic, offline runs; a live BigQuery build is a documented future path that needs
the per-deal spend / adjustment / GC-date inputs that are not all carried in BigQuery — so the
``--from/--to/--asof/--gc-dates`` options below describe that live surface and are inert until it
is wired (a run today requires ``--cache``).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer

from .pipeline import EngineOutput, format_report, load_engine_output, run_pipeline

app = typer.Typer(add_completion=False, help="Run the Skalar accounting pipeline.")
logger = logging.getLogger("skalar_cli")


@app.callback()
def _main(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Emit INFO logs.")] = False,
) -> None:
    """Skalar accounting pipeline (wires data_access -> capital_mechanics -> accounting)."""
    # A callback keeps ``run`` an explicit subcommand and configures structured logging.
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _load_engine(company: str, cache: Path | None) -> EngineOutput:
    """Resolve the engine output for a run (overridable in tests).

    With ``--cache`` it loads a cached engine output (the deterministic, offline path). A live
    BigQuery build is not yet wired end-to-end, so a run must supply ``--cache``.
    """
    if cache is None:
        raise typer.BadParameter(
            "live BigQuery runs are not yet wired; pass --cache <engine-output.json>"
        )
    engine = load_engine_output(cache)
    if engine.company_id != company:
        raise typer.BadParameter(f"cache is for {engine.company_id!r}, not {company!r}")
    return engine


@app.command("run")
def run_cmd(
    company: Annotated[str, typer.Option("--company", help="Deal id, e.g. SK011.")],
    out: Annotated[Path, typer.Option("--out", help="Output .xlsx path.")],
    cache: Annotated[
        Path | None, typer.Option("--cache", help="Cached engine output (JSON); offline path.")
    ] = None,
    date_from: Annotated[
        str, typer.Option("--from", help="[live, not yet wired] First cohort month.")
    ] = "",
    date_to: Annotated[
        str, typer.Option("--to", help="[live, not yet wired] Last cohort month.")
    ] = "",
    asof: Annotated[
        str, typer.Option("--asof", help="[live, not yet wired] Reporting as-of date.")
    ] = "",
    gc_dates: Annotated[
        Path | None, typer.Option("--gc-dates", help="[live, not yet wired] GC dates (JSON).")
    ] = None,
) -> None:
    """Build the books for COMPANY and write the accounting workbook + print a run report."""
    if cache is not None and any((date_from, date_to, asof, gc_dates)):
        logger.warning("--from/--to/--asof/--gc-dates are ignored in cached (--cache) runs")
    engine = _load_engine(company, cache)
    report = run_pipeline(engine, out)
    typer.echo(format_report(report))


if __name__ == "__main__":
    app()
