"""PII auto-detection engine wrapping Microsoft Presidio."""

from __future__ import annotations

from dataclasses import dataclass

from presidio_analyzer import AnalyzerEngine, RecognizerResult

from redactor.recognizers import get_custom_recognizers


@dataclass
class PIIDetection:
    """A single detected PII entity."""

    entity_type: str
    text: str
    start: int
    end: int
    score: float


_engine: AnalyzerEngine | None = None


def _get_engine() -> AnalyzerEngine:
    """Lazily initialize the Presidio analyzer with custom recognizers."""
    global _engine
    if _engine is None:
        _engine = AnalyzerEngine()
        for recognizer in get_custom_recognizers():
            _engine.registry.add_recognizer(recognizer)
    return _engine


def detect_pii(
    text: str,
    language: str = "en",
    threshold: float = 0.7,
    entity_types: list[str] | None = None,
) -> list[PIIDetection]:
    """Detect PII entities in text using Presidio + custom recognizers.

    Args:
        text: The text to analyze.
        language: Language code (default "en").
        threshold: Minimum confidence score (0.0-1.0). Default 0.7.
        entity_types: Optional list of entity types to detect.
            If None, detects all supported types.

    Returns:
        List of PIIDetection objects sorted by position.
    """
    engine = _get_engine()

    results: list[RecognizerResult] = engine.analyze(
        text=text,
        language=language,
        entities=entity_types,
        score_threshold=threshold,
    )

    detections = []
    for r in results:
        detections.append(PIIDetection(
            entity_type=r.entity_type,
            text=text[r.start:r.end],
            start=r.start,
            end=r.end,
            score=r.score,
        ))

    # Sort by position, then by score (highest first for overlapping)
    detections.sort(key=lambda d: (d.start, -d.score))

    # Remove overlapping detections (keep highest score)
    filtered: list[PIIDetection] = []
    last_end = -1
    for d in detections:
        if d.start >= last_end:
            filtered.append(d)
            last_end = d.end

    return filtered


# All entity types supported by default
SUPPORTED_ENTITY_TYPES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "US_SSN",
    "CREDIT_CARD",
    "IP_ADDRESS",
    "URL",
    "LOCATION",
    "DATE_TIME",
    "NRP",  # nationality, religion, political group
    "US_DRIVER_LICENSE",
    "US_PASSPORT",
    "US_BANK_NUMBER",
    "US_ITIN",
    "IBAN_CODE",
    "MEDICAL_LICENSE",
]
