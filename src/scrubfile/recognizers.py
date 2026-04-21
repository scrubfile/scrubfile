"""Custom Presidio recognizers for additional PII patterns."""

from __future__ import annotations

from presidio_analyzer import Pattern, PatternRecognizer


def get_custom_recognizers() -> list[PatternRecognizer]:
    """Return custom recognizers to supplement Presidio's built-in ones."""
    return [
        _us_ssn_recognizer(),
        _us_phone_recognizer(),
        _street_address_recognizer(),
        _date_of_birth_recognizer(),
    ]


def _us_ssn_recognizer() -> PatternRecognizer:
    """Recognizer for US SSNs in various formats."""
    patterns = [
        Pattern("SSN_DASHED", r"\b\d{3}-\d{2}-\d{4}\b", 0.85),
        Pattern("SSN_SPACED", r"\b\d{3}\s\d{2}\s\d{4}\b", 0.75),
        Pattern("SSN_PLAIN", r"\b\d{9}\b", 0.3),  # low score — many 9-digit numbers aren't SSNs
    ]
    return PatternRecognizer(
        supported_entity="US_SSN",
        patterns=patterns,
        context=["ssn", "social security", "social sec", "ss#", "ss #"],
        supported_language="en",
    )


def _us_phone_recognizer() -> PatternRecognizer:
    """Recognizer for US phone numbers in various formats."""
    patterns = [
        Pattern("PHONE_DASHED", r"\b\d{3}-\d{3}-\d{4}\b", 0.7),
        Pattern("PHONE_DOTTED", r"\b\d{3}\.\d{3}\.\d{4}\b", 0.7),
        Pattern("PHONE_PARENS", r"\(\d{3}\)\s?\d{3}-\d{4}", 0.8),
        Pattern("PHONE_SPACED", r"\b\d{3}\s\d{3}\s\d{4}\b", 0.5),
    ]
    return PatternRecognizer(
        supported_entity="PHONE_NUMBER",
        patterns=patterns,
        context=["phone", "tel", "telephone", "mobile", "cell", "call", "fax"],
        supported_language="en",
    )


def _street_address_recognizer() -> PatternRecognizer:
    """Recognizer for US street addresses."""
    patterns = [
        Pattern(
            "STREET_ADDRESS",
            r"\b\d{1,5}\s+(?:[A-Z][a-z]+\s*){1,3}"
            r"(?:Street|St|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Road|Rd|Lane|Ln|"
            r"Court|Ct|Place|Pl|Way|Circle|Cir|Trail|Trl)\b",
            0.6,
        ),
    ]
    return PatternRecognizer(
        supported_entity="STREET_ADDRESS",
        patterns=patterns,
        context=["address", "addr", "street", "home", "residence", "mailing"],
        supported_language="en",
    )


def _date_of_birth_recognizer() -> PatternRecognizer:
    """Recognizer for dates of birth.

    Plain date patterns are ambiguous with generic DATE_TIME values, so we
    lean on two strategies:
      1. High-confidence patterns that include an explicit DOB label.
      2. Lower-confidence bare date patterns that get boosted by nearby
         context words ("dob", "date of birth", "born", etc.).
    """
    # Numeric dates: MM/DD/YYYY, MM-DD-YYYY, MM.DD.YYYY, YYYY-MM-DD (and 2-digit year variants)
    numeric_date = (
        r"(?:\d{1,2}[/\-.]\d{1,2}[/\-.](?:\d{2}|\d{4})"
        r"|\d{4}-\d{1,2}-\d{1,2})"
    )
    # Written dates: "January 5, 1990", "5 January 1990", "Jan 5 1990"
    month = (
        r"(?:January|February|March|April|May|June|July|August|September|"
        r"October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
    )
    written_date = (
        rf"(?:{month}\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{2,4}}"
        rf"|\d{{1,2}}(?:st|nd|rd|th)?\s+{month}\s+\d{{2,4}})"
    )

    label = r"(?:DOB|D\.O\.B\.?|Date\s+of\s+Birth|Birth\s*Date|Birthday|Born)"

    patterns = [
        Pattern(
            "DOB_LABELED_NUMERIC",
            rf"\b{label}\s*[:\-]?\s*{numeric_date}\b",
            0.9,
        ),
        Pattern(
            "DOB_LABELED_WRITTEN",
            rf"\b{label}\s*[:\-]?\s*{written_date}\b",
            0.9,
        ),
        Pattern("DOB_BARE_NUMERIC", rf"\b{numeric_date}\b", 0.3),
        Pattern("DOB_BARE_WRITTEN", rf"\b{written_date}\b", 0.3),
    ]
    return PatternRecognizer(
        supported_entity="DATE_OF_BIRTH",
        patterns=patterns,
        # Context is matched per-token (lemma-based), so list single words.
        context=["dob", "birth", "birthday", "birthdate", "born"],
        supported_language="en",
    )
