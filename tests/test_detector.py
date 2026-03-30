"""Tests for PII auto-detection engine."""

from __future__ import annotations

import pytest

from scrubfile.detector import PIIDetection, detect_pii, SUPPORTED_ENTITY_TYPES


class TestDetectPii:
    def test_detects_person_name(self):
        text = "The employee John Smith works in accounting."
        results = detect_pii(text, threshold=0.5)

        person_results = [r for r in results if r.entity_type == "PERSON"]
        assert len(person_results) >= 1
        assert any("John Smith" in r.text for r in person_results)

    def test_detects_email(self):
        text = "Contact us at john.doe@example.com for more info."
        results = detect_pii(text, threshold=0.5)

        email_results = [r for r in results if r.entity_type == "EMAIL_ADDRESS"]
        assert len(email_results) >= 1
        assert any("john.doe@example.com" in r.text for r in email_results)

    def test_detects_ssn(self):
        text = "SSN: 123-45-6789 is on file."
        results = detect_pii(text, threshold=0.3)

        ssn_results = [r for r in results if r.entity_type == "US_SSN"]
        assert len(ssn_results) >= 1

    def test_detects_phone(self):
        text = "Call us at 555-123-4567 for support."
        results = detect_pii(text, threshold=0.3)

        phone_results = [r for r in results if r.entity_type == "PHONE_NUMBER"]
        assert len(phone_results) >= 1

    def test_no_pii_returns_empty(self):
        text = "The sky is blue and the grass is green."
        results = detect_pii(text, threshold=0.7)

        assert len(results) == 0

    def test_threshold_filters_low_confidence(self):
        text = "SSN: 123-45-6789"
        low = detect_pii(text, threshold=0.1)
        high = detect_pii(text, threshold=0.99)

        assert len(low) >= len(high)

    def test_entity_type_filter(self):
        text = "John Smith's email is john@example.com and SSN is 123-45-6789."
        results = detect_pii(text, threshold=0.3, entity_types=["EMAIL_ADDRESS"])

        # Should only find email, not person or SSN
        for r in results:
            assert r.entity_type == "EMAIL_ADDRESS"

    def test_returns_pii_detection_objects(self):
        text = "Contact john@example.com"
        results = detect_pii(text, threshold=0.3)

        for r in results:
            assert isinstance(r, PIIDetection)
            assert isinstance(r.entity_type, str)
            assert isinstance(r.text, str)
            assert isinstance(r.start, int)
            assert isinstance(r.end, int)
            assert isinstance(r.score, float)
            assert 0.0 <= r.score <= 1.0

    def test_results_sorted_by_position(self):
        text = "John Smith lives at john@example.com in New York."
        results = detect_pii(text, threshold=0.3)

        positions = [r.start for r in results]
        assert positions == sorted(positions)

    def test_multiple_pii_in_text(self):
        text = (
            "Employee: John Smith\n"
            "Email: john.smith@corp.com\n"
            "Phone: 555-123-4567\n"
            "SSN: 123-45-6789"
        )
        results = detect_pii(text, threshold=0.3)

        entity_types = {r.entity_type for r in results}
        # Should detect at least 2 different types
        assert len(entity_types) >= 2


class TestSupportedEntityTypes:
    def test_common_types_listed(self):
        assert "PERSON" in SUPPORTED_ENTITY_TYPES
        assert "EMAIL_ADDRESS" in SUPPORTED_ENTITY_TYPES
        assert "PHONE_NUMBER" in SUPPORTED_ENTITY_TYPES
        assert "US_SSN" in SUPPORTED_ENTITY_TYPES
        assert "CREDIT_CARD" in SUPPORTED_ENTITY_TYPES
        assert "LOCATION" in SUPPORTED_ENTITY_TYPES
