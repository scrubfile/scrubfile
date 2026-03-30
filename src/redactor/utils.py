"""Shared utilities for file validation and output naming."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

MAX_FILE_SIZE_MB = 100

SUPPORTED_EXTENSIONS = {".pdf"}


def validate_input_file(path: str | Path) -> Path:
    """Validate that the input file exists, is supported, and within size limits."""
    p = Path(path).resolve()

    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")

    if not p.is_file():
        raise ValueError(f"Not a file: {p}")

    if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported file type '{p.suffix}'. Supported: {supported}")

    size_mb = p.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(
            f"File too large ({size_mb:.1f}MB). Maximum: {MAX_FILE_SIZE_MB}MB"
        )

    return p


def resolve_output_path(input_path: Path, output: str | Path | None = None) -> Path:
    """Determine the output file path, with safety checks."""
    if output is None:
        stem = input_path.stem
        suffix = input_path.suffix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return input_path.parent / f"{stem}_redacted_{timestamp}{suffix}"

    out = Path(output)

    # Prevent writing outside the current working tree via symlink tricks
    # Check before resolve() so the symlink itself is tested
    if out.is_symlink():
        raise ValueError(f"Output path is a symlink, refusing to write: {out}")

    out = out.resolve()

    # Ensure parent directory exists
    if not out.parent.exists():
        raise ValueError(f"Output directory does not exist: {out.parent}")

    return out


def load_terms_from_file(path: str | Path) -> list[str]:
    """Load redaction terms from a text file, one per line."""
    p = Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Terms file not found: {p}")

    terms = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line)

    if not terms:
        raise ValueError(f"No terms found in file: {p}")

    return terms


# Regex for SSN in various formats
_SSN_DASHED = re.compile(r"^\d{3}-\d{2}-\d{4}$")
_SSN_PLAIN = re.compile(r"^\d{9}$")
_SSN_SPACED = re.compile(r"^\d{3} \d{2} \d{4}$")


def expand_term_variants(terms: list[str]) -> list[str]:
    """Expand terms to include common format variants.

    For SSN-like terms, generates dashed, plain, and spaced versions.
    Deduplicates while preserving order.
    """
    seen: set[str] = set()
    expanded: list[str] = []

    for term in terms:
        if term in seen:
            continue
        seen.add(term)
        expanded.append(term)

        # Generate SSN variants
        variants = _ssn_variants(term)
        for v in variants:
            if v not in seen:
                seen.add(v)
                expanded.append(v)

    return expanded


def _ssn_variants(term: str) -> list[str]:
    """If term looks like an SSN, return all format variants."""
    stripped = term.strip()

    if _SSN_DASHED.match(stripped):
        # "123-45-6789" → also search "123456789" and "123 45 6789"
        digits = stripped.replace("-", "")
        return [digits, f"{digits[:3]} {digits[3:5]} {digits[5:]}"]

    if _SSN_PLAIN.match(stripped):
        # "123456789" → also search "123-45-6789" and "123 45 6789"
        d = stripped
        return [f"{d[:3]}-{d[3:5]}-{d[5:]}", f"{d[:3]} {d[3:5]} {d[5:]}"]

    if _SSN_SPACED.match(stripped):
        # "123 45 6789" → also search "123-45-6789" and "123456789"
        digits = stripped.replace(" ", "")
        return [f"{digits[:3]}-{digits[3:5]}-{digits[5:]}", digits]

    return []
