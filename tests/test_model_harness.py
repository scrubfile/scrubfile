"""Model swap-in harness — verify ANY model checkpoint works in the scrubfile pipeline.

This is the bridge between "model has good metrics" and "model works in production."
It tests that a trained model (DeBERTa, spaCy, or any future model) can be:
1. Loaded by Presidio/scrubfile
2. Used to detect PII on real text
3. Integrated into the full redaction pipeline

Usage:
    # Test current production model (spaCy):
    pytest tests/test_model_harness.py -m slow -v

    # Test a trained DeBERTa checkpoint:
    MODEL_PATH=/path/to/checkpoint pytest tests/test_model_harness.py -m slow -v

    # Test ONNX model:
    MODEL_PATH=/path/to/onnx_model MODEL_TYPE=onnx pytest tests/test_model_harness.py -m slow -v
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import fitz
import pytest

from scrubfile import RedactionResult, redact
from scrubfile.detector import PIIDetection, detect_pii

# ---------------------------------------------------------------------------
# Configuration — which model to test
# ---------------------------------------------------------------------------

MODEL_PATH = os.environ.get("MODEL_PATH", "")  # empty = current production
MODEL_TYPE = os.environ.get("MODEL_TYPE", "spacy")  # spacy | transformers | onnx

# Standard test inputs — same across ALL model checkpoints
STANDARD_TEXTS = {
    "ssn_basic": "SSN: 123-45-6789",
    "email_basic": "Contact: john.doe@example.com",
    "phone_basic": "Call us at 555-123-4567",
    "person_basic": "Employee John Smith works in accounting.",
    "multi_pii": (
        "Name: James Mitchell\n"
        "SSN: 287-65-4321\n"
        "Email: james@corp.com\n"
        "Phone: (555) 867-5309\n"
        "Address: 4521 Maple Avenue, Sunnyvale, CA 94086\n"
    ),
    "clean_text": (
        "The quarterly report shows strong performance across all units. "
        "Revenue grew 15% year-over-year in the enterprise segment."
    ),
}

# Minimum expected detections per standard text
EXPECTED_DETECTIONS = {
    "ssn_basic": {"must_include": ["US_SSN"], "min_count": 1},
    "email_basic": {"must_include": ["EMAIL_ADDRESS"], "min_count": 1},
    "phone_basic": {"must_include": ["PHONE_NUMBER"], "min_count": 1},
    "person_basic": {"must_include": ["PERSON"], "min_count": 1},
    "multi_pii": {"must_include": ["US_SSN", "EMAIL_ADDRESS"], "min_count": 3},
    "clean_text": {"must_include": [], "max_count": 2},  # few or no false positives
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def pii_pdf(tmp_path: Path) -> Path:
    """Create a standardized test PDF with known PII."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Employee Record", fontsize=16, fontname="helv")
    page.insert_text((72, 140), "Name: James Robert Mitchell", fontsize=12, fontname="helv")
    page.insert_text((72, 170), "SSN: 287-65-4321", fontsize=12, fontname="helv")
    page.insert_text((72, 200), "Email: james.mitchell@globalcorp.com", fontsize=12, fontname="helv")
    page.insert_text((72, 230), "Phone: (555) 867-5309", fontsize=12, fontname="helv")
    page.insert_text((72, 260), "Address: 4521 Maple Ave, Sunnyvale, CA 94086", fontsize=12, fontname="helv")
    doc.save(str(tmp_path / "test.pdf"))
    doc.close()
    return tmp_path / "test.pdf"


# ---------------------------------------------------------------------------
# GATE 1: Model loads and produces output
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestModelLoads:
    """Verify the model loads and returns valid PIIDetection objects."""

    def test_model_loads_without_error(self):
        """Model initialization should not raise."""
        results = detect_pii("test text", threshold=0.1)
        assert isinstance(results, list)

    def test_returns_pii_detection_objects(self):
        """All results must be PIIDetection with valid fields."""
        results = detect_pii(STANDARD_TEXTS["multi_pii"], threshold=0.3)
        for r in results:
            assert isinstance(r, PIIDetection), f"Expected PIIDetection, got {type(r)}"
            assert isinstance(r.entity_type, str) and len(r.entity_type) > 0
            assert isinstance(r.text, str) and len(r.text) > 0
            assert isinstance(r.start, int) and r.start >= 0
            assert isinstance(r.end, int) and r.end > r.start
            assert isinstance(r.score, float) and 0.0 <= r.score <= 1.0

    def test_results_sorted_by_position(self):
        """Results must be sorted by start position."""
        results = detect_pii(STANDARD_TEXTS["multi_pii"], threshold=0.3)
        starts = [r.start for r in results]
        assert starts == sorted(starts), "Results not sorted by position"

    def test_model_startup_time(self):
        """Model should initialize in reasonable time (<60s including download)."""
        # This measures warm start (model already loaded from prior tests)
        start = time.time()
        detect_pii("quick test", threshold=0.5)
        elapsed = time.time() - start
        assert elapsed < 10.0, f"Warm inference took {elapsed:.1f}s (expected <10s)"


# ---------------------------------------------------------------------------
# GATE 2: Standard PII detection accuracy
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestStandardDetections:
    """Verify detection on standard test inputs — same for every model."""

    @pytest.mark.parametrize("text_key", [
        "ssn_basic", "email_basic", "phone_basic", "person_basic", "multi_pii",
    ])
    def test_detects_expected_types(self, text_key: str):
        """Each standard text must produce the expected entity types."""
        text = STANDARD_TEXTS[text_key]
        expected = EXPECTED_DETECTIONS[text_key]
        results = detect_pii(text, threshold=0.3)
        detected_types = {r.entity_type for r in results}

        for required_type in expected["must_include"]:
            assert required_type in detected_types, (
                f"[{text_key}] Missing {required_type}. Detected: {detected_types}"
            )

    @pytest.mark.parametrize("text_key", [
        "ssn_basic", "email_basic", "phone_basic", "person_basic", "multi_pii",
    ])
    def test_meets_minimum_count(self, text_key: str):
        """Each standard text must produce at least the minimum detection count."""
        text = STANDARD_TEXTS[text_key]
        expected = EXPECTED_DETECTIONS[text_key]
        results = detect_pii(text, threshold=0.3)

        assert len(results) >= expected["min_count"], (
            f"[{text_key}] Expected ≥{expected['min_count']} detections, got {len(results)}"
        )

    def test_clean_text_low_false_positives(self):
        """Clean text should produce few or no false positives."""
        results = detect_pii(STANDARD_TEXTS["clean_text"], threshold=0.5)
        max_count = EXPECTED_DETECTIONS["clean_text"]["max_count"]
        assert len(results) <= max_count, (
            f"Clean text produced {len(results)} detections (max {max_count}): "
            f"{[(r.entity_type, r.text) for r in results]}"
        )


# ---------------------------------------------------------------------------
# GATE 3: Full pipeline integration (detection → redaction)
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestPipelineIntegration:
    """Verify the model works in the full scrubfile redaction pipeline."""

    def test_auto_redact_pdf(self, pii_pdf: Path, tmp_path: Path):
        """Full pipeline: PDF → extract → detect → redact."""
        output = tmp_path / "redacted.pdf"
        result = redact(pii_pdf, auto=True, threshold=0.3, output=output)

        assert isinstance(result, RedactionResult)
        assert result.total_redactions >= 3, (
            f"Expected ≥3 redactions, got {result.total_redactions}"
        )
        assert output.exists()

    def test_ssn_removed_from_output(self, pii_pdf: Path, tmp_path: Path):
        """SSN must not survive in the redacted PDF text."""
        output = tmp_path / "redacted.pdf"
        redact(pii_pdf, auto=True, threshold=0.3, output=output)

        from scrubfile.pdf import extract_text
        text = extract_text(output)
        assert "287-65-4321" not in text, "SSN survived redaction in pipeline"

    def test_email_removed_from_output(self, pii_pdf: Path, tmp_path: Path):
        """Email must not survive in the redacted PDF text."""
        output = tmp_path / "redacted.pdf"
        redact(pii_pdf, auto=True, threshold=0.3, output=output)

        from scrubfile.pdf import extract_text
        text = extract_text(output)
        assert "james.mitchell@globalcorp.com" not in text, (
            "Email survived redaction in pipeline"
        )

    def test_auto_plus_explicit_terms(self, pii_pdf: Path, tmp_path: Path):
        """Auto-detection combined with explicit terms should redact both."""
        output = tmp_path / "redacted.pdf"
        result = redact(
            pii_pdf,
            terms=["Employee Record"],
            auto=True,
            threshold=0.3,
            output=output,
        )
        from scrubfile.pdf import extract_text
        text = extract_text(output)
        assert "Employee Record" not in text, "Explicit term survived"
        assert result.total_redactions >= 4

    def test_pipeline_latency(self, pii_pdf: Path, tmp_path: Path):
        """Full pipeline should complete in reasonable time."""
        output = tmp_path / "redacted.pdf"
        start = time.time()
        redact(pii_pdf, auto=True, threshold=0.3, output=output)
        elapsed = time.time() - start

        # Single-page PDF should process in <10s (generous for first call)
        assert elapsed < 10.0, (
            f"Pipeline took {elapsed:.1f}s for single-page PDF (expected <10s)"
        )


# ---------------------------------------------------------------------------
# GATE 4: Consistency checks
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestConsistency:
    """Verify model produces consistent results across runs."""

    def test_deterministic_output(self):
        """Same input should produce same detections."""
        text = STANDARD_TEXTS["multi_pii"]
        r1 = [(r.entity_type, r.start, r.end) for r in detect_pii(text, threshold=0.3)]
        r2 = [(r.entity_type, r.start, r.end) for r in detect_pii(text, threshold=0.3)]
        assert r1 == r2, "Non-deterministic: two runs produced different results"

    def test_threshold_monotonicity(self):
        """Lower threshold should produce ≥ same number of detections."""
        text = STANDARD_TEXTS["multi_pii"]
        r_low = detect_pii(text, threshold=0.1)
        r_high = detect_pii(text, threshold=0.9)
        assert len(r_low) >= len(r_high), (
            f"Threshold monotonicity violated: {len(r_low)} detections at 0.1 "
            f"vs {len(r_high)} at 0.9"
        )

    def test_empty_input_safe(self):
        """Empty/whitespace inputs should not crash."""
        for text in ["", " ", "\n", "\t\n  "]:
            results = detect_pii(text, threshold=0.1)
            assert isinstance(results, list)

    def test_long_input_does_not_crash(self):
        """Very long input should not OOM or crash."""
        text = STANDARD_TEXTS["multi_pii"] * 100  # ~500 lines
        results = detect_pii(text, threshold=0.3)
        assert isinstance(results, list)
        assert len(results) >= 1
