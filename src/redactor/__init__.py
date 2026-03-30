"""Redactor — Local PII redaction tool for documents."""

from __future__ import annotations

from pathlib import Path

from redactor.pdf import RedactionResult, redact_pdf
from redactor.utils import expand_term_variants, resolve_output_path, validate_input_file


def redact(
    file_path: str | Path,
    terms: list[str],
    output: str | Path | None = None,
) -> RedactionResult:
    """Redact PII terms from a document.

    This is the primary public API. It auto-detects the file type and
    routes to the appropriate handler.

    Args:
        file_path: Path to the document to redact.
        terms: List of PII strings to search for and redact.
        output: Optional output path. Defaults to <input>_redacted.<ext>.

    Returns:
        RedactionResult with details about what was redacted.

    Raises:
        FileNotFoundError: If the input file doesn't exist.
        ValueError: If the file type is unsupported or file is too large.
    """
    input_path = validate_input_file(file_path)
    output_path = resolve_output_path(input_path, output)

    # Expand SSN variants (dashed, plain, spaced)
    terms = expand_term_variants(terms)

    # Route by file type — Phase 1 supports PDF only
    suffix = input_path.suffix.lower()
    if suffix == ".pdf":
        return redact_pdf(input_path, output_path, terms)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")
