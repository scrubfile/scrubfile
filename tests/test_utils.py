"""Tests for utility functions."""

from __future__ import annotations

from pathlib import Path

import pytest

from scrubfile.utils import (
    expand_term_variants,
    expand_thorough_variants,
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
        import scrubfile.utils as utils_mod
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

    def test_rejects_symlink_terms_file(self, tmp_path: Path):
        target = tmp_path / "real_terms.txt"
        target.write_text("John Doe\n")
        link = tmp_path / "link_terms.txt"
        link.symlink_to(target)
        with pytest.raises(ValueError, match="symlink"):
            load_terms_from_file(link)


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


class TestExpandThoroughVariants:
    def test_splits_multi_word_name(self):
        result = expand_thorough_variants(["John Doe"])
        assert "John Doe" in result
        assert "John" in result
        assert "Doe" in result

    def test_adds_initial_variants(self):
        result = expand_thorough_variants(["John Doe"])
        assert "J. Doe" in result
        assert "J Doe" in result

    def test_skips_short_fragments(self):
        result = expand_thorough_variants(["Al Bo"])
        # "Al" and "Bo" are only 2 chars, below min_length=3
        assert "Al" not in result
        assert "Bo" not in result

    def test_custom_min_length(self):
        result = expand_thorough_variants(["Al Bo"], min_length=2)
        assert "Al" in result
        assert "Bo" in result

    def test_single_word_not_split(self):
        result = expand_thorough_variants(["Aniket"])
        # Single word — nothing to split
        assert result == expand_term_variants(["Aniket"])

    def test_three_word_name(self):
        result = expand_thorough_variants(["Maria Sofia Garcia"])
        assert "Maria" in result
        assert "Sofia" in result
        assert "Garcia" in result
        assert "M. Garcia" in result

    def test_includes_ssn_phone_variants(self):
        # Thorough should still include SSN/phone expansion
        result = expand_thorough_variants(["123-45-6789"])
        assert "123456789" in result

    def test_no_duplicates(self):
        result = expand_thorough_variants(["John Doe", "John Smith"])
        assert len(result) == len(set(result))

    def test_deduplicates_across_terms(self):
        result = expand_thorough_variants(["John Doe", "John Smith"])
        # "John" should appear only once
        assert result.count("John") == 1


class TestExpandDateVariants:
    """Tests for date format expansion."""

    def test_date_slash_mdy_expands(self):
        result = expand_term_variants(["12/12/2023"])
        assert "12/12/2023" in result
        assert "12-12-2023" in result
        assert "12.12.2023" in result
        assert "2023-12-12" in result
        assert "December 12, 2023" in result
        assert "Dec 12, 2023" in result
        assert "Dec. 12, 2023" in result
        assert "12 December 2023" in result
        assert "12 Dec 2023" in result
        assert "12/12/23" in result

    def test_date_iso_expands(self):
        result = expand_term_variants(["2023-12-12"])
        assert "2023-12-12" in result
        assert "12/12/2023" in result
        assert "December 12, 2023" in result
        assert "12 Dec 2023" in result

    def test_date_dotted_expands(self):
        result = expand_term_variants(["12.12.2023"])
        assert "12.12.2023" in result
        assert "12/12/2023" in result
        assert "2023-12-12" in result

    def test_date_month_name_first_expands(self):
        result = expand_term_variants(["December 12, 2023"])
        assert "December 12, 2023" in result
        assert "12/12/2023" in result
        assert "2023-12-12" in result
        assert "Dec 12, 2023" in result

    def test_date_abbr_month_first_expands(self):
        result = expand_term_variants(["Dec 12, 2023"])
        assert "Dec 12, 2023" in result
        assert "12/12/2023" in result
        assert "December 12, 2023" in result

    def test_date_abbr_dot_month_expands(self):
        result = expand_term_variants(["Dec. 12, 2023"])
        assert "Dec. 12, 2023" in result
        assert "12/12/2023" in result
        assert "2023-12-12" in result

    def test_date_day_first_expands(self):
        result = expand_term_variants(["12 December 2023"])
        assert "12 December 2023" in result
        assert "12/12/2023" in result
        assert "2023-12-12" in result

    def test_date_ordinal_day_first_expands(self):
        result = expand_term_variants(["12th Dec 2023"])
        assert "12th Dec 2023" in result
        assert "12/12/2023" in result
        assert "2023-12-12" in result
        assert "December 12, 2023" in result

    def test_date_ordinal_variants(self):
        """1st, 2nd, 3rd ordinals are recognized."""
        for term in ["1st January 2023", "2nd February 2023", "3rd March 2023"]:
            result = expand_term_variants([term])
            assert len(result) > 1, f"No expansion for {term}"

    def test_date_short_year_expands(self):
        result = expand_term_variants(["12/12/23"])
        assert "12/12/23" in result
        assert "12/12/2023" in result
        assert "2023-12-12" in result
        assert "December 12, 2023" in result

    def test_date_short_year_dash_expands(self):
        result = expand_term_variants(["12-12-23"])
        assert "12-12-23" in result
        assert "12/12/2023" in result
        assert "2023-12-12" in result

    def test_date_plain_digits_mmddyyyy(self):
        result = expand_term_variants(["12122023"])
        assert "12122023" in result
        assert "12/12/2023" in result
        assert "2023-12-12" in result

    def test_date_plain_digits_yyyymmdd(self):
        result = expand_term_variants(["20230112"])
        assert "20230112" in result
        assert "01/12/2023" in result
        assert "2023-01-12" in result

    def test_date_no_leading_zero_variant(self):
        result = expand_term_variants(["01/05/2023"])
        assert "1/5/2023" in result
        assert "January 5, 2023" in result

    def test_date_same_leading_zero_deduped(self):
        """When month/day are >=10 the no-leading-zero form is identical."""
        result = expand_term_variants(["12/12/2023"])
        assert len(result) == len(set(result))

    def test_invalid_date_not_expanded(self):
        result = expand_term_variants(["99/99/9999"])
        assert result == ["99/99/9999"]

    def test_date_no_duplicates(self):
        result = expand_term_variants(["12/12/2023"])
        assert len(result) == len(set(result))

    def test_date_mixed_with_ssn(self):
        result = expand_term_variants(["12/12/2023", "123-45-6789"])
        assert "December 12, 2023" in result
        assert "123456789" in result

    def test_bogus_month_name_not_expanded(self):
        result = expand_term_variants(["Foobar 12, 2023"])
        assert result == ["Foobar 12, 2023"]


class TestExpandCreditCardVariants:
    """Tests for credit card format expansion."""

    def test_cc_16_plain_expands(self):
        result = expand_term_variants(["4111111111111111"])
        assert "4111111111111111" in result
        assert "4111-1111-1111-1111" in result
        assert "4111 1111 1111 1111" in result

    def test_cc_16_dashed_expands(self):
        result = expand_term_variants(["4111-1111-1111-1111"])
        assert "4111-1111-1111-1111" in result
        assert "4111111111111111" in result
        assert "4111 1111 1111 1111" in result

    def test_cc_16_spaced_expands(self):
        result = expand_term_variants(["4111 1111 1111 1111"])
        assert "4111 1111 1111 1111" in result
        assert "4111111111111111" in result
        assert "4111-1111-1111-1111" in result

    def test_cc_amex_15_plain_expands(self):
        result = expand_term_variants(["371449635398431"])
        assert "371449635398431" in result
        assert "3714-496353-98431" in result
        assert "3714 496353 98431" in result

    def test_cc_amex_15_dashed_expands(self):
        result = expand_term_variants(["3714-496353-98431"])
        assert "3714-496353-98431" in result
        assert "371449635398431" in result
        assert "3714 496353 98431" in result

    def test_cc_amex_15_spaced_expands(self):
        result = expand_term_variants(["3714 496353 98431"])
        assert "3714 496353 98431" in result
        assert "371449635398431" in result
        assert "3714-496353-98431" in result

    def test_cc_13_digit_expands(self):
        result = expand_term_variants(["4222222222222"])
        assert "4222222222222" in result
        assert len(result) > 1

    def test_cc_no_duplicates(self):
        result = expand_term_variants(["4111-1111-1111-1111", "4111111111111111"])
        assert len(result) == len(set(result))

    def test_non_cc_12_digits_not_expanded(self):
        """12 digits is too short for a credit card."""
        result = expand_term_variants(["123456789012"])
        # 12 digits — doesn't match CC (min 13) or any other pattern
        assert result == ["123456789012"]

    def test_cc_not_confused_with_ssn(self):
        """9-digit SSN should not get CC variants."""
        result = expand_term_variants(["123456789"])
        # Should get SSN variants, not CC variants
        assert "123-45-6789" in result
        assert "1234-5678-9" not in result


class TestExpandEINVariants:
    """Tests for EIN format expansion."""

    def test_ein_dashed_expands(self):
        result = expand_term_variants(["12-3456789"])
        assert "12-3456789" in result
        assert "123456789" in result

    def test_ein_dashed_no_duplicates(self):
        result = expand_term_variants(["12-3456789"])
        assert len(result) == len(set(result))

    def test_ein_plain_gets_ssn_variants_not_ein(self):
        """Plain 9-digit EINs are handled by SSN expansion (same format)."""
        result = expand_term_variants(["123456789"])
        assert "123-45-6789" in result  # SSN grouping
        # EIN dashed form (2-7) is NOT generated from plain 9 digits
        # because that would conflict with SSN handling
        assert "12-3456789" not in result

    def test_ein_not_confused_with_phone(self):
        result = expand_term_variants(["12-3456789"])
        # Should not produce phone-like variants
        assert "(123) 456-789" not in result
