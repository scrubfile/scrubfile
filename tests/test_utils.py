"""Tests for utility functions."""

from __future__ import annotations

from pathlib import Path

import pytest

from redactor.utils import (
    load_terms_from_file,
    resolve_output_path,
    validate_input_file,
)


class TestValidateInputFile:
    def test_valid_pdf(self, golden_pdf: Path):
        result = validate_input_file(golden_pdf)
        assert result == golden_pdf.resolve()

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="File not found"):
            validate_input_file("/nonexistent/file.pdf")

    def test_not_a_file(self, tmp_path: Path):
        with pytest.raises(ValueError, match="Not a file"):
            validate_input_file(tmp_path)

    def test_unsupported_extension(self, tmp_path: Path):
        txt = tmp_path / "test.txt"
        txt.write_text("hello")
        with pytest.raises(ValueError, match="Unsupported file type"):
            validate_input_file(txt)

    def test_file_too_large(self, tmp_path: Path, monkeypatch):
        import redactor.utils as utils_mod
        monkeypatch.setattr(utils_mod, "MAX_FILE_SIZE_MB", 0.0001)

        pdf = tmp_path / "big.pdf"
        pdf.write_bytes(b"x" * 1024)
        with pytest.raises(ValueError, match="File too large"):
            validate_input_file(pdf)


class TestResolveOutputPath:
    def test_default_output_name(self, tmp_path: Path):
        input_path = tmp_path / "report.pdf"
        result = resolve_output_path(input_path)
        assert result == tmp_path / "report_redacted.pdf"

    def test_custom_output(self, tmp_path: Path):
        input_path = tmp_path / "report.pdf"
        output = tmp_path / "clean.pdf"
        result = resolve_output_path(input_path, output)
        assert result == output.resolve()

    def test_rejects_symlink_output(self, tmp_path: Path):
        input_path = tmp_path / "report.pdf"
        target = tmp_path / "real.pdf"
        target.touch()
        link = tmp_path / "link.pdf"
        link.symlink_to(target)

        with pytest.raises(ValueError, match="symlink"):
            resolve_output_path(input_path, link)

    def test_rejects_nonexistent_parent(self, tmp_path: Path):
        input_path = tmp_path / "report.pdf"
        with pytest.raises(ValueError, match="does not exist"):
            resolve_output_path(input_path, tmp_path / "no_such_dir" / "out.pdf")


class TestLoadTermsFromFile:
    def test_loads_terms(self, terms_file: Path):
        terms = load_terms_from_file(terms_file)
        assert "John Doe" in terms
        assert "123-45-6789" in terms
        assert "john@example.com" in terms

    def test_skips_comments_and_blanks(self, terms_file: Path):
        terms = load_terms_from_file(terms_file)
        for term in terms:
            assert not term.startswith("#")
            assert term.strip() != ""

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_terms_from_file("/nonexistent/terms.txt")

    def test_empty_file(self, tmp_path: Path):
        empty = tmp_path / "empty.txt"
        empty.write_text("# only comments\n\n")
        with pytest.raises(ValueError, match="No terms found"):
            load_terms_from_file(empty)
