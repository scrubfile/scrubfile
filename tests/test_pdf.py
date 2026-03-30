"""Tests for PDF redaction engine."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from redactor.pdf import RedactionResult, extract_text, get_metadata, redact_pdf


class TestRedactPdf:
    """Core PDF redaction functionality."""

    def test_redacts_single_term(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        result = redact_pdf(golden_pdf, output, ["John Doe"])

        assert output.exists()
        assert result.total_redactions >= 3  # appears 3+ times across pages
        assert result.pages_affected == 2
        assert "John Doe" in result.terms_found

    def test_redacted_text_is_removed_from_content(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        redact_pdf(golden_pdf, output, ["John Doe"])

        text = extract_text(output)
        assert "John Doe" not in text

    def test_non_redacted_text_preserved(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        redact_pdf(golden_pdf, output, ["John Doe"])

        text = extract_text(output)
        assert "Performance Review" in text
        assert "Jane Smith" in text

    def test_redacts_multiple_terms(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        result = redact_pdf(golden_pdf, output, ["John Doe", "123-45-6789"])

        text = extract_text(output)
        assert "John Doe" not in text
        assert "123-45-6789" not in text
        assert result.total_redactions >= 4

    def test_redacts_ssn(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        redact_pdf(golden_pdf, output, ["123-45-6789"])

        text = extract_text(output)
        assert "123-45-6789" not in text

    def test_redacts_email(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        redact_pdf(golden_pdf, output, ["john@example.com"])

        text = extract_text(output)
        assert "john@example.com" not in text

    def test_redacts_address(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        redact_pdf(golden_pdf, output, ["123 Main Street"])

        text = extract_text(output)
        assert "123 Main Street" not in text

    def test_no_match_returns_zero_redactions(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        result = redact_pdf(golden_pdf, output, ["NONEXISTENT_TERM_XYZ"])

        assert result.total_redactions == 0
        assert result.pages_affected == 0
        assert output.exists()  # still produces output

    def test_empty_pdf(self, empty_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        result = redact_pdf(empty_pdf, output, ["anything"])

        assert result.total_redactions == 0
        assert output.exists()


class TestMetadataClearing:
    """Verify metadata is scrubbed from redacted PDFs."""

    def test_metadata_cleared(self, golden_pdf: Path, tmp_path: Path):
        # Verify source has metadata
        source_meta = get_metadata(golden_pdf)
        assert source_meta.get("author") == "HR Department"

        output = tmp_path / "out.pdf"
        result = redact_pdf(golden_pdf, output, ["John Doe"])

        assert result.metadata_cleared is True
        meta = get_metadata(output)
        assert meta.get("author", "") == ""
        assert meta.get("title", "") == ""
        assert meta.get("creator", "") == ""

    def test_metadata_cleared_even_with_no_redactions(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        redact_pdf(golden_pdf, output, ["NONEXISTENT"])

        meta = get_metadata(output)
        assert meta.get("author", "") == ""


class TestOutputValidity:
    """Verify the output PDF is valid and well-formed."""

    def test_output_is_valid_pdf(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        redact_pdf(golden_pdf, output, ["John Doe"])

        doc = fitz.open(str(output))
        assert len(doc) == 2  # same page count as input
        doc.close()

    def test_output_file_is_smaller_or_comparable(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        redact_pdf(golden_pdf, output, ["John Doe", "123-45-6789"])

        # Redacted + garbage-collected file should not be drastically larger
        input_size = golden_pdf.stat().st_size
        output_size = output.stat().st_size
        assert output_size < input_size * 3  # generous upper bound


class TestRedactionResult:
    """Verify the result dataclass is populated correctly."""

    def test_result_fields(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        result = redact_pdf(golden_pdf, output, ["John Doe", "Jane Smith"])

        assert isinstance(result, RedactionResult)
        assert result.input_path == str(golden_pdf)
        assert result.output_path == str(output)
        assert result.total_redactions > 0
        assert result.pages_affected > 0
        assert isinstance(result.terms_found, dict)
        assert result.metadata_cleared is True

    def test_terms_found_counts(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        result = redact_pdf(golden_pdf, output, ["Jane Smith"])

        assert "Jane Smith" in result.terms_found
        assert result.terms_found["Jane Smith"] >= 1
