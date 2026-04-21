"""Tests for custom Presidio recognizers."""

from __future__ import annotations

import pytest

from scrubfile.recognizers import (
    _date_of_birth_recognizer,
    _street_address_recognizer,
    _us_phone_recognizer,
    _us_ssn_recognizer,
    get_custom_recognizers,
)


def _match_texts(recognizer, text: str, entity: str) -> list[tuple[str, float]]:
    """Run a PatternRecognizer standalone (no NLP artifacts) and return matches."""
    results = recognizer.analyze(text, entities=[entity], nlp_artifacts=None)
    return [(text[r.start:r.end], r.score) for r in results]


class TestGetCustomRecognizers:
    def test_registers_date_of_birth(self):
        entities = {r.supported_entities[0] for r in get_custom_recognizers()}
        assert "DATE_OF_BIRTH" in entities

    def test_registers_expected_entities(self):
        entities = {r.supported_entities[0] for r in get_custom_recognizers()}
        assert entities == {
            "US_SSN",
            "PHONE_NUMBER",
            "STREET_ADDRESS",
            "DATE_OF_BIRTH",
        }


class TestDateOfBirthRecognizerLabeled:
    """Labeled DOBs should match with high confidence (>= 0.85)."""

    @pytest.mark.parametrize("text,expected", [
        ("DOB: 01/15/1990", "DOB: 01/15/1990"),
        ("DOB 01/15/1990", "DOB 01/15/1990"),
        ("DOB - 01-15-1990", "DOB - 01-15-1990"),
        ("D.O.B.: 1/5/90", "D.O.B.: 1/5/90"),
        ("D.O.B: 12.31.1985", "D.O.B: 12.31.1985"),
        ("Date of Birth: 1990-01-15", "Date of Birth: 1990-01-15"),
        ("Birth Date: 01/15/1990", "Birth Date: 01/15/1990"),
        ("BirthDate: 01/15/1990", "BirthDate: 01/15/1990"),
        ("Birthday: 7/4/1980", "Birthday: 7/4/1980"),
        ("Born: 12/25/1975", "Born: 12/25/1975"),
    ])
    def test_labeled_numeric_dates(self, text, expected):
        recognizer = _date_of_birth_recognizer()
        matches = _match_texts(recognizer, text, "DATE_OF_BIRTH")
        assert any(expected in m and score >= 0.85 for m, score in matches), matches

    @pytest.mark.parametrize("text,expected", [
        ("DOB: January 15, 1990", "DOB: January 15, 1990"),
        ("DOB January 15 1990", "DOB January 15 1990"),
        ("Date of Birth: Jan 5, 1990", "Date of Birth: Jan 5, 1990"),
        ("Date of Birth: 15 January 1990", "Date of Birth: 15 January 1990"),
        ("Born: 3rd April 1982", "Born: 3rd April 1982"),
        ("Birthday: Feb 29, 2000", "Birthday: Feb 29, 2000"),
    ])
    def test_labeled_written_dates(self, text, expected):
        recognizer = _date_of_birth_recognizer()
        matches = _match_texts(recognizer, text, "DATE_OF_BIRTH")
        assert any(expected in m and score >= 0.85 for m, score in matches), matches


class TestDateOfBirthRecognizerBare:
    """Bare dates match at low confidence and rely on context for boosting."""

    @pytest.mark.parametrize("text", [
        "01/15/1990",
        "1/5/90",
        "12-31-1985",
        "12.31.1985",
        "1990-01-15",
        "January 15, 1990",
        "15 Jan 1990",
        "3rd April 1982",
    ])
    def test_bare_dates_match_with_low_score(self, text):
        recognizer = _date_of_birth_recognizer()
        matches = _match_texts(recognizer, text, "DATE_OF_BIRTH")
        assert len(matches) >= 1, f"no match for {text!r}"
        # Bare matches should be low confidence (context-driven)
        assert any(score <= 0.5 for _, score in matches), matches


class TestDateOfBirthRecognizerSpans:
    """start/end indices must precisely locate the matched substring."""

    def test_labeled_numeric_span_exact(self):
        recognizer = _date_of_birth_recognizer()
        prefix = "Employee info — "
        date_str = "DOB: 01/15/1990"
        text = f"{prefix}{date_str} on file."
        results = recognizer.analyze(text, entities=["DATE_OF_BIRTH"], nlp_artifacts=None)

        labeled = [r for r in results if r.score >= 0.85]
        assert len(labeled) >= 1
        r = labeled[0]
        assert text[r.start:r.end] == date_str
        assert r.start == len(prefix)
        assert r.end == len(prefix) + len(date_str)

    def test_bare_written_span_exact(self):
        recognizer = _date_of_birth_recognizer()
        prefix = "The date was "
        date_str = "January 15, 1990"
        text = f"{prefix}{date_str} last year."
        results = recognizer.analyze(text, entities=["DATE_OF_BIRTH"], nlp_artifacts=None)

        assert len(results) >= 1
        bare = [r for r in results if text[r.start:r.end] == date_str]
        assert len(bare) >= 1, [(text[r.start:r.end], r.score) for r in results]


class TestDateOfBirthRecognizerCaseInsensitivity:
    """DOB labels must match regardless of case — Presidio PatternRecognizer
    applies re.IGNORECASE by default, and we rely on that behavior.
    """

    @pytest.mark.parametrize("text", [
        "DOB: 01/15/1990",
        "dob: 01/15/1990",
        "Dob: 01/15/1990",
        "dOb: 01/15/1990",
        "d.o.b.: 01/15/1990",
        "date of birth: 01/15/1990",
        "DATE OF BIRTH: 01/15/1990",
        "Date Of Birth: January 15, 1990",
        "birthday: 01/15/1990",
        "BORN: 01/15/1990",
    ])
    def test_labels_match_regardless_of_case(self, text):
        recognizer = _date_of_birth_recognizer()
        matches = _match_texts(recognizer, text, "DATE_OF_BIRTH")
        assert any(score >= 0.85 for _, score in matches), (
            f"case-insensitive label did not produce high-confidence match: {matches}"
        )


class TestDateOfBirthRecognizerNonMatches:
    @pytest.mark.parametrize("text", [
        "",
        "Hello world",
        "The meeting is tomorrow.",
        "Version 1.2.3 was released.",
        "Call 555-123-4567 for info.",
    ])
    def test_non_dates_do_not_match(self, text):
        recognizer = _date_of_birth_recognizer()
        matches = _match_texts(recognizer, text, "DATE_OF_BIRTH")
        assert matches == []


class TestOtherRecognizersUnaffected:
    """Sanity check that the three pre-existing recognizers still work."""

    def test_ssn(self):
        matches = _match_texts(_us_ssn_recognizer(), "SSN: 123-45-6789", "US_SSN")
        assert any("123-45-6789" in m for m, _ in matches)

    def test_phone(self):
        matches = _match_texts(_us_phone_recognizer(), "Call 555-123-4567", "PHONE_NUMBER")
        assert any("555-123-4567" in m for m, _ in matches)

    def test_street_address(self):
        matches = _match_texts(
            _street_address_recognizer(),
            "Ship to 123 Main Street",
            "STREET_ADDRESS",
        )
        assert any("123 Main Street" in m for m, _ in matches)


@pytest.mark.slow
class TestDateOfBirthIntegration:
    """End-to-end tests through the Presidio analyzer (loads spaCy)."""

    def test_detects_labeled_dob(self):
        from scrubfile.detector import detect_pii

        text = "Employee DOB: 01/15/1990 on file."
        results = detect_pii(text, threshold=0.7, entity_types=["DATE_OF_BIRTH"])

        assert len(results) >= 1
        assert any("01/15/1990" in r.text for r in results)
        assert all(r.entity_type == "DATE_OF_BIRTH" for r in results)

    def test_detects_written_dob(self):
        from scrubfile.detector import detect_pii

        text = "Date of Birth: January 15, 1990"
        results = detect_pii(text, threshold=0.7, entity_types=["DATE_OF_BIRTH"])

        assert len(results) >= 1
        assert any("January 15, 1990" in r.text for r in results)

    def test_bare_date_boosted_by_context(self):
        from scrubfile.detector import detect_pii

        text = "His date of birth is 01/15/1990 according to records."
        results = detect_pii(text, threshold=0.5, entity_types=["DATE_OF_BIRTH"])

        assert any("01/15/1990" in r.text for r in results), results

    def test_non_dob_text_produces_no_dob(self):
        from scrubfile.detector import detect_pii

        text = "The sky is blue and the grass is green."
        results = detect_pii(text, threshold=0.5, entity_types=["DATE_OF_BIRTH"])

        assert results == []

    def test_bare_date_without_context_stays_below_threshold(self):
        """Without birth-related context, a bare date must not produce DATE_OF_BIRTH."""
        from scrubfile.detector import detect_pii

        text = "The project kickoff happened on 01/15/1990."
        results = detect_pii(text, threshold=0.5, entity_types=["DATE_OF_BIRTH"])

        assert results == [], (
            f"bare date without birth context should not hit threshold 0.5, got: {results}"
        )

    def test_labeled_dob_beats_date_time_on_overlap(self):
        """With no entity filter, the labeled span should surface as DATE_OF_BIRTH.

        Presidio's built-in DATE_TIME recognizer will match '01/15/1990' inside
        'DOB: 01/15/1990'. Our overlap filter picks the earlier-starting, then
        higher-scoring entity. The labeled DOB span starts earlier (covers
        'DOB:') and wins, so the reported entity type must be DATE_OF_BIRTH.
        """
        from scrubfile.detector import detect_pii

        text = "Employee DOB: 01/15/1990 on file."
        results = detect_pii(text, threshold=0.7)  # no entity_types filter

        dob_hits = [r for r in results if r.entity_type == "DATE_OF_BIRTH"]
        assert dob_hits, f"expected DATE_OF_BIRTH in {results}"
        # And the winning span should include the label
        assert any("DOB" in r.text and "01/15/1990" in r.text for r in dob_hits), dob_hits
        # No DATE_TIME should have survived for the same date span
        date_time_overlap = [
            r for r in results
            if r.entity_type == "DATE_TIME" and "01/15/1990" in r.text
        ]
        assert date_time_overlap == [], (
            f"DATE_TIME should have lost to DATE_OF_BIRTH on overlap, got: {date_time_overlap}"
        )
