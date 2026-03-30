"""Custom Presidio recognizers for additional PII patterns."""

from __future__ import annotations

from presidio_analyzer import Pattern, PatternRecognizer


def get_custom_recognizers() -> list[PatternRecognizer]:
    """Return custom recognizers to supplement Presidio's built-in ones."""
    return [
        _us_ssn_recognizer(),
        _us_phone_recognizer(),
        _street_address_recognizer(),
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
        supported_entity="LOCATION",
        patterns=patterns,
        context=["address", "addr", "street", "home", "residence", "mailing"],
        supported_language="en",
    )
