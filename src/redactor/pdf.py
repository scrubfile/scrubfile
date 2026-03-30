"""PDF redaction engine using PyMuPDF."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class RedactionResult:
    """Result of a PDF redaction operation."""

    input_path: str
    output_path: str
    total_redactions: int
    pages_affected: int
    terms_found: dict[str, int] = field(default_factory=dict)
    metadata_cleared: bool = False


def redact_pdf(
    input_path: Path,
    output_path: Path,
    terms: list[str],
) -> RedactionResult:
    """Search for PII terms in a PDF and redact all occurrences.

    Redaction is permanent: text under black boxes is removed from the
    content stream, not just visually hidden. Metadata is also cleared.
    """
    doc = fitz.open(str(input_path))

    total_redactions = 0
    pages_affected: set[int] = set()
    terms_found: dict[str, int] = {}

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_had_redactions = False

        for term in terms:
            # Search is case-insensitive by default in PyMuPDF
            hits = page.search_for(term)
            if hits:
                terms_found[term] = terms_found.get(term, 0) + len(hits)
                total_redactions += len(hits)
                page_had_redactions = True

                for rect in hits:
                    page.add_redact_annot(rect, fill=(0, 0, 0))

        if page_had_redactions:
            page.apply_redactions()
            pages_affected.add(page_num)

    # Clear metadata
    doc.set_metadata({})
    doc.scrub()

    # Save with garbage collection to remove orphaned objects
    doc.save(str(output_path), garbage=3, deflate=True)
    doc.close()

    # Restrict output to owner-only (rw-------) to protect sensitive content
    os.chmod(str(output_path), 0o600)

    return RedactionResult(
        input_path=str(input_path),
        output_path=str(output_path),
        total_redactions=total_redactions,
        pages_affected=len(pages_affected),
        terms_found=terms_found,
        metadata_cleared=True,
    )


def extract_text(path: Path) -> str:
    """Extract all text from a PDF, for inspection/testing."""
    doc = fitz.open(str(path))
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def get_metadata(path: Path) -> dict:
    """Get PDF metadata, for inspection/testing."""
    doc = fitz.open(str(path))
    meta = doc.metadata
    doc.close()
    return meta
