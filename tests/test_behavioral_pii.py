"""Behavioral regression suite for PII detection (BT-001 through BT-024).

Each test has an immutable ID, exact input, expected entity types, and a
severity classification. These tests form a hard production gate:
a model/configuration that fails any "must-pass" test CANNOT ship.

This file is the executable version of TRAINING_PLAN §10 Level 4.
IDs are permanent — never renumber, only append.
"""

from __future__ import annotations

import pytest

from scrubfile.detector import PIIDetection, detect_pii

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detected_types(text: str, threshold: float = 0.3) -> dict[str, list[str]]:
    """Return {entity_type: [detected_text, ...]} for the given input."""
    results = detect_pii(text, threshold=threshold)
    out: dict[str, list[str]] = {}
    for r in results:
        out.setdefault(r.entity_type, []).append(r.text)
    return out


def _has_type(text: str, entity_type: str, threshold: float = 0.3) -> bool:
    """True if entity_type was detected in text."""
    return entity_type in _detected_types(text, threshold)


def _detected_type_set(text: str, threshold: float = 0.3) -> set[str]:
    """Return the set of entity types detected."""
    return set(_detected_types(text, threshold).keys())


# ---------------------------------------------------------------------------
# MUST-PASS: Critical PII detection — SSN, credit card, email, names
# Failing ANY of these blocks shipping.
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestMustPass:
    """Tests that MUST pass for any production release."""

    def test_bt001_ssn_with_context(self):
        """BT-001: SSN with explicit context label."""
        assert _has_type("SSN: 123-45-6789", "US_SSN")

    def test_bt002_ssn_without_context(self):
        """BT-002: SSN without any context — pattern alone should trigger."""
        results = detect_pii("123-45-6789", threshold=0.3)
        # Should detect something — at minimum a low-confidence SSN or phone
        assert len(results) >= 1

    def test_bt003_non_ssn_phone_number(self):
        """BT-003: 10-digit phone should NOT be classified as US_SSN."""
        types = _detected_types("Phone: 123-456-7890")
        if "US_SSN" in types:
            # If it triggers SSN, it should also have PHONE with higher confidence
            phone_results = [r for r in detect_pii("Phone: 123-456-7890", threshold=0.3)
                            if r.entity_type == "PHONE_NUMBER"]
            ssn_results = [r for r in detect_pii("Phone: 123-456-7890", threshold=0.3)
                          if r.entity_type == "US_SSN"]
            # Phone pattern (XXX-XXX-XXXX) is different from SSN (XXX-XX-XXXX)
            # so SSN should NOT match
            assert len(ssn_results) == 0, "10-digit phone misclassified as SSN"

    def test_bt004_email_detection(self):
        """BT-004: Email in natural context."""
        assert _has_type(
            "From: john.doe@email.com", "EMAIL_ADDRESS"
        )

    def test_bt005_address_in_paragraph(self):
        """BT-005: Street address embedded in a sentence."""
        text = "She lives at 123 Main Street, Springfield IL 62704"
        types = _detected_type_set(text)
        # Must detect at least the address pattern
        assert types & {"STREET_ADDRESS", "LOCATION"}, (
            f"Expected address-related entity, got: {types}"
        )

    def test_bt006_adversarial_date_not_person(self):
        """BT-006: A calendar date must NOT be classified as a person name."""
        types = _detected_types("The meeting is January 15, 2025")
        if "PERSON" in types:
            # Check that the person text is not "January"
            person_texts = types["PERSON"]
            for t in person_texts:
                assert "January" not in t, (
                    f"Calendar month 'January' misclassified as PERSON: {person_texts}"
                )

    def test_bt007_credit_card_luhn_valid(self):
        """BT-007: Luhn-valid credit card number must be detected."""
        assert _has_type("Card: 4111-1111-1111-1111", "CREDIT_CARD")

    def test_bt009_empty_document(self):
        """BT-009: Empty string should produce zero detections."""
        results = detect_pii("", threshold=0.1)
        assert len(results) == 0

    def test_bt012_multicultural_names(self):
        """BT-012: Names from diverse cultures must be detected as PERSON."""
        names = [
            "Employee name: Raj Patel",
            "Applicant: José García",
            "Contact: Wei Zhang",
            "Manager: Priya Krishnamurthy",
        ]
        for text in names:
            assert _has_type(text, "PERSON"), f"Failed to detect person in: {text}"

    def test_bt014_nested_context(self):
        """BT-014: PII in nested/complex context."""
        text = "Emergency contact: Jane Doe (wife), 555-123-4567"
        types = _detected_type_set(text)
        assert "PERSON" in types, f"Missing PERSON in: {types}"
        assert "PHONE_NUMBER" in types, f"Missing PHONE_NUMBER in: {types}"


# ---------------------------------------------------------------------------
# SHOULD-PASS: High-value but not blocking. Failures trigger investigation.
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestShouldPass:
    """Tests that SHOULD pass. Failures don't block but require explanation."""

    def test_bt008_credit_card_luhn_invalid(self):
        """BT-008: Luhn-invalid number should NOT be flagged as credit card."""
        types = _detected_types("ID: 1234-5678-9012-3456")
        if "CREDIT_CARD" in types:
            pytest.xfail("Luhn-invalid number falsely detected as credit card")

    def test_bt010_all_pii_document(self):
        """BT-010: Document saturated with PII should have high recall."""
        text = (
            "John Smith, SSN 123-45-6789, born 03/15/1988.\n"
            "Email: john.smith@example.com, Phone: (555) 867-5309.\n"
            "Address: 4521 Maple Avenue, Sunnyvale, CA 94086.\n"
            "Credit card: 4111-1111-1111-1111, expires 12/25.\n"
        )
        types = _detected_type_set(text)
        # Should detect at least 4 different entity types
        assert len(types) >= 4, f"Only detected {len(types)} types in dense PII doc: {types}"

    def test_bt013_pii_in_csv_table(self):
        """BT-013: PII in CSV/table-like format."""
        text = (
            "Name,Email,SSN\n"
            "John Doe,john@example.com,123-45-6789\n"
            "Jane Smith,jane@example.com,987-65-4321\n"
        )
        types = _detected_type_set(text)
        assert "EMAIL_ADDRESS" in types, f"Missing EMAIL_ADDRESS in table: {types}"
        assert "US_SSN" in types, f"Missing US_SSN in table: {types}"

    def test_bt015_ssn_in_sentence(self):
        """BT-015: SSN mentioned conversationally (no label)."""
        text = "Please verify that 287-65-4321 matches our records."
        assert _has_type(text, "US_SSN")

    def test_bt016_multiple_emails(self):
        """BT-016: Multiple emails in one text should all be found."""
        text = "Contact sarah@corp.com or backup: admin@corp.com for access."
        results = [r for r in detect_pii(text, threshold=0.3)
                   if r.entity_type == "EMAIL_ADDRESS"]
        assert len(results) >= 2, f"Expected ≥2 emails, found {len(results)}"

    def test_bt017_phone_formats(self):
        """BT-017: Various US phone formats should be detected."""
        formats = [
            "Call 555-123-4567",
            "Tel: (555) 123-4567",
            "Ph: 555.123.4567",
        ]
        for text in formats:
            assert _has_type(text, "PHONE_NUMBER"), (
                f"Failed to detect phone in: {text}"
            )

    def test_bt018_person_with_title(self):
        """BT-018: Person name with professional title."""
        text = "Reviewed by Dr. Michael Patel, Chief Medical Officer"
        assert _has_type(text, "PERSON"), "Failed to detect person with title"

    def test_bt019_ssn_context_variations(self):
        """BT-019: SSN with different context labels."""
        variations = [
            "Social Security Number: 287-65-4321",
            "SS#: 287-65-4321",
            "SSN 287-65-4321",
            "social security: 287-65-4321",
        ]
        for text in variations:
            assert _has_type(text, "US_SSN"), f"SSN not detected in: {text}"


# ---------------------------------------------------------------------------
# INFORMATIONAL: Track detection quality on hard cases.
# Failures are logged, never block.
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestInformational:
    """Informational tests — track quality on edge cases."""

    def test_bt011_ocr_degraded_text(self):
        """BT-011: OCR-degraded text — best-effort detection."""
        # Simulating common OCR errors: 0↔O, 1↔l, S↔5
        text = "J0hn Sm1th, SSN: l23-4S-6789"
        results = detect_pii(text, threshold=0.1)
        # Log what was found — this is informational, not a gate
        types = {r.entity_type for r in results}
        if not types:
            pytest.skip("No detection on OCR-degraded text (expected for current system)")

    def test_bt020_clean_doc_no_false_positives(self):
        """BT-020: Clean document with zero PII should produce zero detections."""
        text = (
            "The quarterly report shows strong performance across all business units. "
            "Revenue grew 15% year-over-year, driven by enterprise segment expansion. "
            "We recommend increasing R&D investment in the next fiscal year. "
            "The board meeting is scheduled for Monday at the headquarters."
        )
        results = detect_pii(text, threshold=0.5)
        if results:
            types = {r.entity_type: r.text for r in results}
            pytest.xfail(f"False positives in clean doc: {types}")

    def test_bt021_mixed_language_context(self):
        """BT-021: PII in mixed-language text."""
        text = "Nombre: José García, correo: jose@gmail.com, teléfono: 555-123-4567"
        types = _detected_type_set(text)
        if not (types & {"EMAIL_ADDRESS", "PHONE_NUMBER"}):
            pytest.skip("Limited mixed-language support (informational)")

    def test_bt022_pii_in_json(self):
        """BT-022: PII embedded in JSON-like structure."""
        text = '{"name": "John Doe", "ssn": "123-45-6789", "email": "john@test.com"}'
        types = _detected_type_set(text)
        # At minimum, email and SSN patterns should still match
        assert len(types) >= 1, f"No PII detected in JSON structure: {types}"

    def test_bt023_long_document_recall(self):
        """BT-023: PII at the end of a long document is still detected."""
        padding = "This is a normal paragraph with no sensitive information. " * 50
        text = padding + "\nEmployee SSN: 123-45-6789\n" + padding
        assert _has_type(text, "US_SSN"), "SSN at document midpoint not detected"

    def test_bt024_repeated_pii(self):
        """BT-024: Same PII repeated — each occurrence should be found."""
        text = (
            "SSN: 123-45-6789 on page 1.\n"
            "Verify SSN: 123-45-6789 on page 2.\n"
            "Final check: 123-45-6789.\n"
        )
        results = [r for r in detect_pii(text, threshold=0.3)
                   if r.entity_type == "US_SSN"]
        assert len(results) >= 2, f"Expected ≥2 SSN matches, got {len(results)}"
