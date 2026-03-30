"""Shared utilities for file validation and output naming."""

from __future__ import annotations

import os
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
        return input_path.parent / f"{stem}_redacted{suffix}"

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
