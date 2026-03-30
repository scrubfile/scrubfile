"""Tests for thorough redaction mode (residual inference prevention)."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from scrubfile import redact, RedactionResult
from scrubfile.pdf import extract_text


@pytest.fixture
def inference_pdf(tmp_path: Path) -> Path:
    """Create a PDF where name fragments appear separately from the full name.

    This simulates the residual inference scenario: the full name
    "Xeus Yrdfghe" appears once, but fragments "X" and "Yrd" also
    appear elsewhere in the document.
    """
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Patient: Xeus Yrdfghe", fontsize=12, fontname="helv")
    page.insert_text((72, 140), "Referred by Dr. Yrdfghe at City Hospital", fontsize=12, fontname="helv")
    page.insert_text((72, 180), "Contact Xeus directly at ext 4500", fontsize=12, fontname="helv")
    page.insert_text((72, 220), "Notes: Xeus is doing well. Follow up with Yrdfghe.", fontsize=12, fontname="helv")
    doc.save(str(tmp_path / "inference.pdf"))
    doc.close()
    return tmp_path / "inference.pdf"


class TestThoroughRedaction:
    def test_normal_mode_leaves_fragments(self, inference_pdf: Path, tmp_path: Path):
        """Without --thorough, individual name parts survive."""
        output = tmp_path / "normal.pdf"
        redact(inference_pdf, terms=["Xeus Yrdfghe"], output=output)

        text = extract_text(output)
        # Full name is redacted
        assert "Xeus Yrdfghe" not in text
        # But fragments still appear (standalone "Xeus" and "Yrdfghe")
        assert "Xeus" in text or "Yrdfghe" in text

    def test_thorough_mode_catches_fragments(self, inference_pdf: Path, tmp_path: Path):
        """With --thorough, individual name components are also redacted."""
        output = tmp_path / "thorough.pdf"
        redact(inference_pdf, terms=["Xeus Yrdfghe"], output=output, thorough=True)

        text = extract_text(output)
        assert "Xeus Yrdfghe" not in text
        assert "Xeus" not in text
        assert "Yrdfghe" not in text

    def test_thorough_catches_initial_patterns(self, tmp_path: Path):
        """Thorough mode catches 'J. Doe' when 'John Doe' is the term."""
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 100), "Employee: John Doe", fontsize=12, fontname="helv")
        page.insert_text((72, 140), "Approved by J. Doe on March 1", fontsize=12, fontname="helv")
        page.insert_text((72, 180), "Signature: Doe, John", fontsize=12, fontname="helv")
        doc.save(str(tmp_path / "initials.pdf"))
        doc.close()

        output = tmp_path / "out.pdf"
        redact(tmp_path / "initials.pdf", terms=["John Doe"], output=output, thorough=True)

        text = extract_text(output)
        assert "John Doe" not in text
        assert "J. Doe" not in text
        assert "Doe" not in text
        assert "John" not in text

    def test_thorough_more_redactions_than_normal(self, inference_pdf: Path, tmp_path: Path):
        """Thorough mode produces more redactions than normal mode."""
        out_normal = tmp_path / "normal.pdf"
        out_thorough = tmp_path / "thorough.pdf"

        r_normal = redact(inference_pdf, terms=["Xeus Yrdfghe"], output=out_normal)
        r_thorough = redact(inference_pdf, terms=["Xeus Yrdfghe"], output=out_thorough, thorough=True)

        assert r_thorough.total_redactions > r_normal.total_redactions

    def test_thorough_with_auto_detect(self, inference_pdf: Path, tmp_path: Path):
        """Thorough mode works combined with --auto."""
        output = tmp_path / "auto_thorough.pdf"
        result = redact(inference_pdf, auto=True, thorough=True, threshold=0.3, output=output)

        assert isinstance(result, RedactionResult)
        assert output.exists()
