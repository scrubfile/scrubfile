"""Tests for utility functions."""

from __future__ import annotations

from pathlib import Path

import pytest

from redactor.utils import (
    expand_term_variants,
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
    def test_default_output_name_has_timestamp(self, tmp_path: Path):
        input_path = tmp_path / "report.pdf"
        result = resolve_output_path(input_path)
        assert result.parent == tmp_path
        assert result.name.startswith("report_redacted_")
        assert result.suffix == ".pdf"
        # Verify timestamp portion is 15 chars (YYYYMMDD_HHMMSS)
        ts_part = result.stem.replace("report_redacted_", "")
        assert len(ts_part) == 15

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


class TestExpandTermVariants:
    def test_ssn_dashed_expands(self):
        result = expand_term_variants(["123-45-6789"])
        assert "123-45-6789" in result
        assert "123456789" in result
        assert "123 45 6789" in result

    def test_ssn_plain_expands(self):
        result = expand_term_variants(["123456789"])
        assert "123456789" in result
        assert "123-45-6789" in result
        assert "123 45 6789" in result

    def test_ssn_spaced_expands(self):
        result = expand_term_variants(["123 45 6789"])
        assert "123 45 6789" in result
        assert "123-45-6789" in result
        assert "123456789" in result

    def test_non_ssn_not_expanded(self):
        result = expand_term_variants(["John Doe"])
        assert result == ["John Doe"]

    def test_mixed_terms(self):
        result = expand_term_variants(["John Doe", "123-45-6789"])
        assert "John Doe" in result
        assert "123-45-6789" in result
        assert "123456789" in result

    def test_no_duplicates(self):
        result = expand_term_variants(["123-45-6789", "123456789"])
        # Both originals and their variants, but no dupes
        assert len(result) == len(set(result))

    def test_empty_list(self):
        assert expand_term_variants([]) == []

    def test_phone_dashed_expands(self):
        result = expand_term_variants(["555-123-4567"])
        assert "555-123-4567" in result
        assert "5551234567" in result
        assert "555.123.4567" in result
        assert "555 123 4567" in result
        assert "(555) 123-4567" in result
        assert "(555)123-4567" in result

    def test_phone_plain_expands(self):
        result = expand_term_variants(["5551234567"])
        assert "5551234567" in result
        assert "555-123-4567" in result
        assert "555.123.4567" in result

    def test_phone_dotted_expands(self):
        result = expand_term_variants(["555.123.4567"])
        assert "555.123.4567" in result
        assert "555-123-4567" in result
        assert "5551234567" in result

    def test_phone_parens_expands(self):
        result = expand_term_variants(["(555) 123-4567"])
        assert "(555) 123-4567" in result
        assert "555-123-4567" in result
        assert "5551234567" in result

    def test_phone_no_duplicates(self):
        result = expand_term_variants(["555-123-4567", "5551234567"])
        assert len(result) == len(set(result))

    def test_non_phone_not_expanded(self):
        result = expand_term_variants(["Hello World"])
        assert result == ["Hello World"]
