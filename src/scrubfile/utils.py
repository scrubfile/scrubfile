"""Shared utilities for file validation and output naming."""

from __future__ import annotations

import calendar
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

# Month name lookup tables for date parsing
_FULL_MONTHS = {name.lower(): num for num, name in enumerate(calendar.month_name) if name}
_ABBR_MONTHS = {abbr.lower(): num for num, abbr in enumerate(calendar.month_abbr) if abbr}

# Regex for dates in various formats
_DATE_SLASH = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_DATE_DASH_MDY = re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{4})$")
_DATE_DOT = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$")
_DATE_ISO = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
_DATE_MONTH_FIRST = re.compile(
    r"^([A-Za-z]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})$"
)
_DATE_DAY_FIRST = re.compile(
    r"^(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(\d{4})$"
)
_DATE_SLASH_SHORT = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2})$")
_DATE_DASH_SHORT = re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{2})$")
_DATE_PLAIN8 = re.compile(r"^\d{8}$")

# Regex for credit card numbers (13-19 digits)
_CC_PLAIN = re.compile(r"^\d{13,19}$")
_CC_DASHED4 = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{1,7}$")
_CC_SPACED4 = re.compile(r"^\d{4} \d{4} \d{4} \d{1,7}$")
_CC_AMEX_DASH = re.compile(r"^\d{4}-\d{6}-\d{5}$")
_CC_AMEX_SPACE = re.compile(r"^\d{4} \d{6} \d{5}$")

# Regex for EIN (Employer Identification Number): XX-XXXXXXX or 9 digits
_EIN_DASHED = re.compile(r"^\d{2}-\d{7}$")
_EIN_PLAIN = re.compile(r"^\d{9}$")


def expand_term_variants(terms: list[str]) -> list[str]:
    """Expand terms to include common format variants.

    For SSN-like, phone-like, date-like, credit-card-like, and EIN-like
    terms, generates all common format variants.
    Deduplicates while preserving order.
    """
    seen: set[str] = set()
    expanded: list[str] = []

    for term in terms:
        if term in seen:
            continue
        seen.add(term)
        expanded.append(term)

        variants = (
            _ssn_variants(term)
            + _phone_variants(term)
            + _date_variants(term)
            + _cc_variants(term)
            + _ein_variants(term)
        )
        for v in variants:
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


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def _safe_date(year: int, month: int, day: int) -> datetime | None:
    """Construct a datetime, returning None for invalid dates."""
    try:
        return datetime(year, month, day)
    except (ValueError, OverflowError):
        return None


def _resolve_month(name: str) -> int | None:
    """Resolve a full or abbreviated month name to its number (1-12)."""
    lower = name.lower()
    return _FULL_MONTHS.get(lower) or _ABBR_MONTHS.get(lower)


def _parse_date_term(term: str) -> datetime | None:
    """Try to parse a term as a date in any common format."""
    s = term.strip()

    # ISO: YYYY-MM-DD (check before dash-MDY to avoid ambiguity)
    m = _DATE_ISO.match(s)
    if m:
        return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # MM/DD/YYYY
    m = _DATE_SLASH.match(s)
    if m:
        return _safe_date(int(m.group(3)), int(m.group(1)), int(m.group(2)))

    # MM-DD-YYYY
    m = _DATE_DASH_MDY.match(s)
    if m:
        return _safe_date(int(m.group(3)), int(m.group(1)), int(m.group(2)))

    # MM.DD.YYYY
    m = _DATE_DOT.match(s)
    if m:
        return _safe_date(int(m.group(3)), int(m.group(1)), int(m.group(2)))

    # Month DD, YYYY  /  Mon DD, YYYY  /  Dec. 12th, 2023
    m = _DATE_MONTH_FIRST.match(s)
    if m:
        mo = _resolve_month(m.group(1))
        if mo is not None:
            return _safe_date(int(m.group(3)), mo, int(m.group(2)))

    # DD Month YYYY  /  12th Dec 2023
    m = _DATE_DAY_FIRST.match(s)
    if m:
        mo = _resolve_month(m.group(2))
        if mo is not None:
            return _safe_date(int(m.group(3)), mo, int(m.group(1)))

    # MM/DD/YY
    m = _DATE_SLASH_SHORT.match(s)
    if m:
        yy = int(m.group(3))
        year = 2000 + yy if yy < 69 else 1900 + yy
        return _safe_date(year, int(m.group(1)), int(m.group(2)))

    # MM-DD-YY
    m = _DATE_DASH_SHORT.match(s)
    if m:
        yy = int(m.group(3))
        year = 2000 + yy if yy < 69 else 1900 + yy
        return _safe_date(year, int(m.group(1)), int(m.group(2)))

    # 8 plain digits: try MMDDYYYY first, then YYYYMMDD
    if _DATE_PLAIN8.match(s):
        dt = _safe_date(int(s[4:]), int(s[:2]), int(s[2:4]))
        if dt:
            return dt
        return _safe_date(int(s[:4]), int(s[4:6]), int(s[6:]))

    return None


def _date_variants(term: str) -> list[str]:
    """If term looks like a date, return all format variants."""
    dt = _parse_date_term(term)
    if dt is None:
        return []

    mo, d, y = dt.month, dt.day, dt.year
    month_full = calendar.month_name[mo]
    month_abbr = calendar.month_abbr[mo]
    yy = y % 100

    candidates = [
        f"{mo:02d}/{d:02d}/{y}",
        f"{mo}/{d}/{y}",
        f"{mo:02d}-{d:02d}-{y}",
        f"{mo:02d}.{d:02d}.{y}",
        f"{y}-{mo:02d}-{d:02d}",
        f"{month_full} {d}, {y}",
        f"{month_abbr} {d}, {y}",
        f"{month_abbr}. {d}, {y}",
        f"{d} {month_full} {y}",
        f"{d} {month_abbr} {y}",
        f"{mo:02d}/{d:02d}/{yy:02d}",
        f"{mo:02d}-{d:02d}-{yy:02d}",
        f"{mo:02d}{d:02d}{y}",
        f"{y}{mo:02d}{d:02d}",
    ]

    seen: set[str] = set()
    unique: list[str] = []
    original = term.strip()
    for c in candidates:
        if c not in seen and c != original:
            seen.add(c)
            unique.append(c)
    return unique


# ---------------------------------------------------------------------------
# Credit-card helpers
# ---------------------------------------------------------------------------

def _extract_cc_digits(term: str) -> str | None:
    """Extract digits from a credit-card-like term, or return None."""
    stripped = term.strip()

    if _CC_PLAIN.match(stripped):
        return stripped
    if _CC_DASHED4.match(stripped) or _CC_AMEX_DASH.match(stripped):
        return stripped.replace("-", "")
    if _CC_SPACED4.match(stripped) or _CC_AMEX_SPACE.match(stripped):
        return stripped.replace(" ", "")
    return None


def _cc_variants(term: str) -> list[str]:
    """If term looks like a credit card number, return all format variants."""
    digits = _extract_cc_digits(term)
    if digits is None:
        return []

    n = len(digits)
    stripped = term.strip()
    candidates: list[str] = [digits]

    if n == 15:
        # Amex: 4-6-5 grouping
        candidates += [
            f"{digits[:4]}-{digits[4:10]}-{digits[10:]}",
            f"{digits[:4]} {digits[4:10]} {digits[10:]}",
        ]
    if n == 16:
        # Standard: 4-4-4-4 grouping
        g = [digits[i:i + 4] for i in range(0, 16, 4)]
        candidates += [
            "-".join(g),
            " ".join(g),
        ]
    if n not in (15, 16):
        # Generic: 4-4-4-rest grouping for other lengths
        g = [digits[i:i + 4] for i in range(0, n, 4)]
        candidates += [
            "-".join(g),
            " ".join(g),
        ]

    return [v for v in candidates if v != stripped]


# ---------------------------------------------------------------------------
# EIN helpers
# ---------------------------------------------------------------------------

def _ein_variants(term: str) -> list[str]:
    """If term looks like an EIN, return the other format variant.

    EINs are 9 digits in XX-XXXXXXX format.  Because plain 9-digit strings
    are also handled by ``_ssn_variants``, this function only activates on
    the *dashed* EIN form (2-7 grouping) so it doesn't conflict.
    """
    stripped = term.strip()

    if _EIN_DASHED.match(stripped):
        return [stripped.replace("-", "")]

    return []
