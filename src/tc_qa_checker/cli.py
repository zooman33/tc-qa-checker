"""Command-line interface for tc-qa-checker."""

import logging
from pathlib import Path

import typer

from .alignment import DEFAULT_SKIP_COST
from .engine import analyze_files
from .report import render_json, render_text

app = typer.Typer(
    add_completion=False,
    help="Track-changes verification for bilingual DOCX translation files.",
)


@app.command()
def run(
    source: Path = typer.Option(
        ...,
        "--source",
        "-s",
        exists=True,
        dir_okay=False,
        readable=True,
        help="Path to the source .docx (with tracked changes).",
    ),
    target: Path = typer.Option(
        ...,
        "--target",
        "-t",
        exists=True,
        dir_okay=False,
        readable=True,
        help="Path to the target .docx (with tracked changes).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit findings as JSON."),
    skip_cost: int = typer.Option(
        DEFAULT_SKIP_COST, "--skip-cost", help="Needleman-Wunsch skip cost for unit alignment."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Log pipeline progress to stderr."),
) -> None:
    """Verify that tracked changes were carried correctly from source to target."""
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    findings = analyze_files(source, target, skip_cost=skip_cost)
    output = render_json(findings) if json_output else render_text(findings)
    typer.echo(output)


if __name__ == "__main__":  # pragma: no cover
    app()
