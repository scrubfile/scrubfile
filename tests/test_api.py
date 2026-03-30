"""Tests for the public Python API."""

from __future__ import annotations

from pathlib import Path

import pytest

from redactor import RedactionResult, redact
from redactor.pdf import extract_text


class TestPublicApi:
    def test_redact_pdf_basic(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        result = redact(golden_pdf, terms=["John Doe"], output=output)

        assert isinstance(result, RedactionResult)
        assert result.total_redactions >= 3
        assert output.exists()

    def test_redact_removes_text(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        redact(golden_pdf, terms=["123-45-6789"], output=output)

        text = extract_text(output)
        assert "123-45-6789" not in text

    def test_redact_default_output_path(self, golden_pdf: Path):
        result = redact(golden_pdf, terms=["John Doe"])

        # Output has timestamp: golden_redacted_YYYYMMDD_HHMMSS.pdf
        outputs = list(golden_pdf.parent.glob("golden_redacted_*.pdf"))
        assert len(outputs) >= 1
        assert Path(result.output_path).exists()

    def test_redact_str_path(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        result = redact(str(golden_pdf), terms=["John Doe"], output=str(output))

        assert result.total_redactions >= 3

    def test_redact_unsupported_type(self, tmp_path: Path):
        txt = tmp_path / "test.txt"
        txt.write_text("hello")
        with pytest.raises(ValueError, match="Unsupported file type"):
            redact(txt, terms=["hello"])

    def test_redact_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            redact("/nonexistent.pdf", terms=["test"])

    def test_redact_multiple_terms(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        result = redact(
            golden_pdf,
            terms=["John Doe", "123-45-6789", "john@example.com"],
            output=output,
        )
        text = extract_text(output)
        assert "John Doe" not in text
        assert "123-45-6789" not in text
        assert "john@example.com" not in text
        assert result.total_redactions >= 5
