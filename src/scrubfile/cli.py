"""CLI entrypoint for scrubfile."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from scrubfile import redact as redact_api
from scrubfile.utils import (
    expand_term_variants,
    load_terms_from_file,
)

app = typer.Typer(
    name="scrubfile",
    help="Scrub PII from PDFs, images, and DOCX files. Local-only. One command.",
    no_args_is_help=True,
)
console = Console(stderr=True)


@app.command()
def redact(
    file: Annotated[
        Path,
        typer.Argument(help="Path to the file to redact (PDF, PNG, JPEG, DOCX)"),
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
            help="Output file path (default: <input>_redacted_<timestamp>.<ext>)",
        ),
    ] = None,
    ocr_engine: Annotated[
        str,
        typer.Option(
            "--ocr-engine",
            help="OCR engine for image files (easyocr or tesseract)",
        ),
    ] = "easyocr",
    auto: Annotated[
        bool,
        typer.Option(
            "--auto",
            help="Auto-detect PII using NLP (no manual terms needed)",
        ),
    ] = False,
    threshold: Annotated[
        float,
        typer.Option(
            "--threshold",
            help="Confidence threshold for auto-detection (0.0-1.0)",
        ),
    ] = 0.7,
    entity_types: Annotated[
        Optional[str],
        typer.Option(
            "--types",
            help="Comma-separated entity types for auto mode (e.g. PERSON,US_SSN,EMAIL_ADDRESS)",
        ),
    ] = None,
    thorough: Annotated[
        bool,
        typer.Option(
            "--thorough",
            help="Also redact name fragments and initials (e.g. 'John Doe' also redacts 'John', 'Doe', 'J. Doe'). More aggressive, may increase false positives.",
        ),
    ] = False,
    preview: Annotated[
        bool,
        typer.Option(
            "--preview",
            help="Preview auto-detected PII without redacting",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output results as JSON (machine-readable)",
        ),
    ] = False,
) -> None:
    """Redact PII from a document.

    Supports PDF, PNG, JPEG, TIFF, BMP, and DOCX files.
    Provide terms via --redact / --redact-file, or use --auto for NLP-based detection.
    """
    # Collect all terms
    all_terms: list[str] = []
    if terms:
        all_terms.extend(terms)
    if redact_file:
        try:
            all_terms.extend(load_terms_from_file(redact_file))
        except (FileNotFoundError, ValueError) as e:
            _error(str(e), json_output)
            raise typer.Exit(code=1)

    if not all_terms and not auto:
        _error("No redaction terms provided. Use --redact, --redact-file, or --auto.", json_output)
        raise typer.Exit(code=1)

    # Parse entity types if provided
    types_list = [t.strip() for t in entity_types.split(",")] if entity_types else None

    # Perform redaction via the public API
    try:
        result = redact_api(
            file,
            terms=all_terms if all_terms else None,
            output=output,
            ocr_engine=ocr_engine,
            auto=auto,
            threshold=threshold,
            entity_types=types_list,
            preview=preview,
            thorough=thorough,
        )
    except (FileNotFoundError, ValueError) as e:
        _error(str(e), json_output)
        raise typer.Exit(code=1)
    except Exception as e:
        _error(f"Redaction failed: {e}", json_output)
        raise typer.Exit(code=1)

    # Preview mode — show detections without redacting
    if preview and auto:
        if json_output:
            print(json.dumps({
                "status": "preview",
                "input": str(result.input_path),
                "detections": len(result.terms_found),
                "entities": [
                    {"type": "AUTO", "text": f"[DETECTED-{i+1}]"}
                    for i in range(len(result.terms_found))
                ],
            }))
        else:
            console.print(f"[cyan]Preview: {len(result.terms_found)} PII entities detected.[/cyan]")
            if result.terms_found:
                table = Table(title="Detected PII (Preview)")
                table.add_column("#", style="dim")
                table.add_column("Type", style="bold")
                for i, term in enumerate(result.terms_found.keys()):
                    table.add_row(str(i + 1), f"[DETECTED-{i+1}]")
                console.print(table)
            console.print("[dim]No changes made. Remove --preview to redact.[/dim]")
        raise typer.Exit(code=0)

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
        affected = result.pages_affected
        scope = f"across {affected} page(s)" if affected > 0 else "in file"
        console.print(f"[green]Redacted {result.total_redactions} occurrence(s) "
                      f"{scope}.[/green]")
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
