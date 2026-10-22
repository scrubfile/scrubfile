"""XLSX redaction engine using openpyxl."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl
from openpyxl.cell.cell import MergedCell


@dataclass
class XlsxRedactionResult:
    """Result of an XLSX redaction operation."""

    input_path: str
    output_path: str
    total_redactions: int
    terms_found: dict[str, int] = field(default_factory=dict)
    metadata_cleared: bool = False


# Unicode full block character for redaction
_REDACT_CHAR = "█"


def redact_xlsx(
    input_path: Path,
    output_path: Path,
    terms: list[str],
) -> XlsxRedactionResult:
    """Redact PII terms from an XLSX workbook.

    Iterates every worksheet and every cell, replacing matched text in
    string cell values with block characters. Clears workbook properties.
    """
    wb = openpyxl.load_workbook(str(input_path))

    total_redactions = 0
    terms_found: dict[str, int] = {}

    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell, MergedCell):
                    continue
                value = cell.value
                if not isinstance(value, str):
                    continue

                text = value
                cell_counts: dict[str, int] = {}
                for term in terms:
                    pattern = re.compile(re.escape(term), re.IGNORECASE)
                    occurrences = pattern.findall(text)
                    if occurrences:
                        cell_counts[term] = cell_counts.get(term, 0) + len(occurrences)
                        text = pattern.sub(
                            lambda m: _REDACT_CHAR * len(m.group(0)), text
                        )

                if text != value:
                    cell.value = text
                    for term, count in cell_counts.items():
                        terms_found[term] = terms_found.get(term, 0) + count
                        total_redactions += count

    _clear_properties(wb)

    wb.save(str(output_path))
    os.chmod(str(output_path), 0o600)

    return XlsxRedactionResult(
        input_path=str(input_path),
        output_path=str(output_path),
        total_redactions=total_redactions,
        terms_found=terms_found,
        metadata_cleared=True,
    )


def _clear_properties(wb: openpyxl.Workbook) -> None:
    """Clear workbook core (and custom) properties."""
    props = wb.properties
    for attr in (
        "title",
        "subject",
        "creator",
        "description",
        "keywords",
        "category",
        "contentStatus",
        "lastModifiedBy",
        "lastPrinted",
        "identifier",
        "language",
        "revision",
        "version",
    ):
        try:
            setattr(props, attr, "")
        except Exception:
            pass
    # created/modified are typed datetime fields; leave them untouched to
    # avoid serialisation errors, but clear identity-ish string fields above.

    # Clear any custom document properties.
    try:
        wb.custom_doc_props = type(wb.custom_doc_props)()
    except Exception:
        try:
            for cp in list(wb.custom_doc_props):
                wb.custom_doc_props.remove(cp)
        except Exception:
            pass
