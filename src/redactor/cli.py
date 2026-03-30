"""CLI entrypoint for the redactor tool."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from redactor.pdf import redact_pdf
from redactor.utils import (
    expand_term_variants,
    load_terms_from_file,
    resolve_output_path,
    validate_input_file,
)

app = typer.Typer(
    name="redactor",
    help="Local PII redaction tool. Redact sensitive information from PDFs.",
    no_args_is_help=True,
)
console = Console(stderr=True)


@app.command()
def redact(
    file: Annotated[
        Path,
        typer.Argument(help="Path to the file to redact"),
    ],
    terms: Annotated[
        Optional[list[str]],
        typer.Option(
            "--redact",
            "-r",
            help="PII term to redact (can be specified multiple times)",
        ),
    ] = None,
    redact_file: Annotated[
        Optional[Path],
        typer.Option(
            "--redact-file",
            "-f",
            help="Path to a file containing PII terms, one per line",
        ),
    ] = None,
    output: Annotated[
        Optional[Path],
        typer.Option(
            "--output",
            "-o",
            help="Output file path (default: <input>_redacted.<ext>)",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output results as JSON (machine-readable)",
        ),
    ] = False,
) -> None:
    """Redact PII from a document.

    Provide terms to redact via --redact flags or a --redact-file.
    The redacted file is saved alongside the original (or to --output).
    """
    # Collect all terms
    all_terms: list[str] = []
    if terms:
        all_terms.extend(terms)
    if redact_file:
        all_terms.extend(load_terms_from_file(redact_file))

    if not all_terms:
        _error("No redaction terms provided. Use --redact or --redact-file.", json_output)
        raise typer.Exit(code=1)

    # Expand SSN variants (dashed, plain, spaced)
    all_terms = expand_term_variants(all_terms)

    # Validate input
    try:
        input_path = validate_input_file(file)
    except (FileNotFoundError, ValueError) as e:
        _error(str(e), json_output)
        raise typer.Exit(code=1)

    # Resolve output
    try:
        output_path = resolve_output_path(input_path, output)
    except ValueError as e:
        _error(str(e), json_output)
        raise typer.Exit(code=1)

    # Perform redaction
    try:
        result = redact_pdf(input_path, output_path, all_terms)
    except Exception as e:
        _error(f"Redaction failed: {e}", json_output)
        raise typer.Exit(code=1)

    # Output results
    if result.total_redactions == 0:
        if json_output:
            print(json.dumps({
                "status": "no_redactions",
                "input": str(result.input_path),
                "output": str(result.output_path),
                "redactions": 0,
            }))
        else:
            console.print("[yellow]No matches found for the given terms.[/yellow]")
        raise typer.Exit(code=2)

    # Mask PII terms in output — the tool should not echo sensitive data
    masked_terms = {
        f"[TERM-{i+1}]": count
        for i, (term, count) in enumerate(result.terms_found.items())
    }

    if json_output:
        print(json.dumps({
            "status": "success",
            "input": str(result.input_path),
            "output": str(result.output_path),
            "redactions": result.total_redactions,
            "pages_affected": result.pages_affected,
            "terms_matched": len(result.terms_found),
            "term_counts": masked_terms,
            "metadata_cleared": result.metadata_cleared,
        }))
    else:
        console.print(f"[green]Redacted {result.total_redactions} occurrence(s) "
                      f"across {result.pages_affected} page(s).[/green]")
        if masked_terms:
            table = Table(title="Redaction Summary")
            table.add_column("Term", style="bold")
            table.add_column("Occurrences", justify="right")
            for label, count in masked_terms.items():
                table.add_row(label, str(count))
            console.print(table)
        console.print(f"Output: {result.output_path}")
        console.print("[dim]Metadata cleared.[/dim]")


def _error(message: str, json_output: bool) -> None:
    """Print an error message in the appropriate format."""
    if json_output:
        print(json.dumps({"status": "error", "message": message}))
    else:
        console.print(f"[red]Error:[/red] {message}")
