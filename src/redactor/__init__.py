"""Redactor — Local PII redaction tool for documents."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from redactor.utils import expand_term_variants, resolve_output_path, validate_input_file


@dataclass
class RedactionResult:
    """Unified result for any redaction operation."""

    input_path: str
    output_path: str
    total_redactions: int
    pages_affected: int = 0
    terms_found: dict[str, int] = field(default_factory=dict)
    metadata_cleared: bool = False


_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}


def redact(
    file_path: str | Path,
    terms: list[str],
    output: str | Path | None = None,
    ocr_engine: str = "easyocr",
) -> RedactionResult:
    """Redact PII terms from a document.

    This is the primary public API. It auto-detects the file type and
    routes to the appropriate handler.

    Args:
        file_path: Path to the document to redact.
        terms: List of PII strings to search for and redact.
        output: Optional output path. Defaults to <input>_redacted_<timestamp>.<ext>.
        ocr_engine: OCR engine for image files ("easyocr" or "tesseract").

    Returns:
        RedactionResult with details about what was redacted.

    Raises:
        FileNotFoundError: If the input file doesn't exist.
        ValueError: If the file type is unsupported or file is too large.
    """
    input_path = validate_input_file(file_path)
    output_path = resolve_output_path(input_path, output)

    # Expand SSN/phone variants
    terms = expand_term_variants(terms)

    suffix = input_path.suffix.lower()

    if suffix == ".pdf":
        from redactor.pdf import redact_pdf

        r = redact_pdf(input_path, output_path, terms)
        return RedactionResult(
            input_path=r.input_path,
            output_path=r.output_path,
            total_redactions=r.total_redactions,
            pages_affected=r.pages_affected,
            terms_found=r.terms_found,
            metadata_cleared=r.metadata_cleared,
        )

    elif suffix in _IMAGE_EXTENSIONS:
        from redactor.image import redact_image

        r = redact_image(input_path, output_path, terms, ocr_engine=ocr_engine)
        return RedactionResult(
            input_path=r.input_path,
            output_path=r.output_path,
            total_redactions=r.total_redactions,
            terms_found=r.terms_found,
            metadata_cleared=r.metadata_cleared,
        )

    elif suffix == ".docx":
        from redactor.docx_redactor import redact_docx

        r = redact_docx(input_path, output_path, terms)
        return RedactionResult(
            input_path=r.input_path,
            output_path=r.output_path,
            total_redactions=r.total_redactions,
            terms_found=r.terms_found,
            metadata_cleared=r.metadata_cleared,
        )

    else:
        raise ValueError(f"Unsupported file type: {suffix}")
