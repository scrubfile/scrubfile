"""Shared utilities for file validation and output naming."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

MAX_FILE_SIZE_MB = 100

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".docx"}


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
    p = Path(path)
    if p.is_symlink():
        raise ValueError(f"Terms file is a symlink, refusing to read: {p}")
    p = p.resolve()
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

# Regex for US phone numbers in various formats (10 digits)
_PHONE_DASHED = re.compile(r"^\d{3}-\d{3}-\d{4}$")          # 555-123-4567
_PHONE_DOTTED = re.compile(r"^\d{3}\.\d{3}\.\d{4}$")        # 555.123.4567
_PHONE_SPACED = re.compile(r"^\d{3} \d{3} \d{4}$")          # 555 123 4567
_PHONE_PARENS = re.compile(r"^\(\d{3}\)\s?\d{3}-\d{4}$")    # (555)123-4567 or (555) 123-4567
_PHONE_PLAIN = re.compile(r"^\d{10}$")                       # 5551234567


def expand_term_variants(terms: list[str]) -> list[str]:
    """Expand terms to include common format variants.

    For SSN-like and phone-like terms, generates all common format variants.
    Deduplicates while preserving order.
    """
    seen: set[str] = set()
    expanded: list[str] = []

    for term in terms:
        if term in seen:
            continue
        seen.add(term)
        expanded.append(term)

        # Generate variants (SSN, phone)
        for v in _ssn_variants(term) + _phone_variants(term):
            if v not in seen:
                seen.add(v)
                expanded.append(v)

    return expanded


def expand_thorough_variants(terms: list[str], min_length: int = 3) -> list[str]:
    """Expand terms to include individual components for thorough redaction.

    For multi-word terms like "John Doe", also adds "John" and "Doe" as
    separate search terms. Also adds common name fragments: initials,
    first N characters (prefixes >= min_length).

    This catches residual inference attacks where partial fragments
    (e.g., "J. Doe", "Dr. Joh", first name alone) remain in the document
    and can be recombined to identify the person.

    Use with caution — increases false positives. "John" will match
    "Johnson", "St. John's", etc.

    Args:
        terms: Original list of terms.
        min_length: Minimum character length for a fragment to be included.
            Default 3 to avoid single-letter matches.
    """
    # Start with standard expansion
    expanded = expand_term_variants(terms)
    seen = set(expanded)

    for term in terms:
        words = term.strip().split()
        if len(words) < 2:
            continue

        for word in words:
            word = word.strip(".,;:!?()\"'")
            if len(word) >= min_length and word not in seen:
                seen.add(word)
                expanded.append(word)

        # Add initials pattern: "J. Doe", "J Doe"
        if len(words) >= 2:
            first_initial = words[0][0]
            last = words[-1]
            variants = [
                f"{first_initial}. {last}",    # "J. Doe"
                f"{first_initial} {last}",     # "J Doe"
                f"{first_initial}.{last}",     # "J.Doe"
            ]
            for v in variants:
                if len(v) >= min_length and v not in seen:
                    seen.add(v)
                    expanded.append(v)

    return expanded


def _ssn_variants(term: str) -> list[str]:
    """If term looks like an SSN, return all format variants."""
    stripped = term.strip()

    if _SSN_DASHED.match(stripped):
        digits = stripped.replace("-", "")
        return [digits, f"{digits[:3]} {digits[3:5]} {digits[5:]}"]

    if _SSN_PLAIN.match(stripped):
        d = stripped
        return [f"{d[:3]}-{d[3:5]}-{d[5:]}", f"{d[:3]} {d[3:5]} {d[5:]}"]

    if _SSN_SPACED.match(stripped):
        digits = stripped.replace(" ", "")
        return [f"{digits[:3]}-{digits[3:5]}-{digits[5:]}", digits]

    return []


def _phone_variants(term: str) -> list[str]:
    """If term looks like a US phone number, return all format variants."""
    stripped = term.strip()

    # Extract 10 digits from any recognized phone format
    digits: str | None = None

    if _PHONE_PLAIN.match(stripped):
        digits = stripped
    elif _PHONE_DASHED.match(stripped):
        digits = stripped.replace("-", "")
    elif _PHONE_DOTTED.match(stripped):
        digits = stripped.replace(".", "")
    elif _PHONE_SPACED.match(stripped):
        digits = stripped.replace(" ", "")
    elif _PHONE_PARENS.match(stripped):
        digits = re.sub(r"[^0-9]", "", stripped)

    if digits is None or len(digits) != 10:
        return []

    a, b, c = digits[:3], digits[3:6], digits[6:]
    variants = [
        digits,              # 5551234567
        f"{a}-{b}-{c}",     # 555-123-4567
        f"{a}.{b}.{c}",     # 555.123.4567
        f"{a} {b} {c}",     # 555 123 4567
        f"({a}) {b}-{c}",   # (555) 123-4567
        f"({a}){b}-{c}",    # (555)123-4567
    ]
    # Return only variants that aren't the original term
    return [v for v in variants if v != stripped]
