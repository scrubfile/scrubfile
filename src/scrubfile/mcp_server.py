"""MCP server exposing scrubfile tools for AI agents."""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("scrubfile")


@mcp.tool()
def redact_file(
    file_path: str,
    terms: list[str] | None = None,
    auto: bool = False,
    threshold: float = 0.7,
    thorough: bool = False,
) -> dict:
    """Redact PII from a PDF, image, or DOCX file.

    Provide explicit terms via `terms`, or set `auto=True` for NLP-based
    PII detection. Returns a summary with masked labels — raw PII is never
    included in the response.

    Args:
        file_path: Path to the file to redact.
        terms: PII strings to redact (e.g., ["John Doe", "123-45-6789"]).
        auto: Auto-detect PII using Presidio + spaCy.
        threshold: Confidence threshold for auto-detection (0.0-1.0).
        thorough: Also redact name fragments and initials.
    """
    from scrubfile import redact

    try:
        result = redact(
            file_path=file_path,
            terms=terms,
            auto=auto,
            threshold=threshold,
            thorough=thorough,
        )
    except (FileNotFoundError, ValueError) as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": f"Redaction failed: {type(e).__name__}"}

    # Mask term labels — never expose raw PII in MCP responses
    masked_counts = {
        f"[TERM-{i+1}]": count
        for i, (_, count) in enumerate(result.terms_found.items())
    }

    return {
        "status": "success",
        "input_file": Path(result.input_path).name,
        "output_file": Path(result.output_path).name,
        "redactions": result.total_redactions,
        "pages_affected": result.pages_affected,
        "terms_matched": len(result.terms_found),
        "term_counts": masked_counts,
        "metadata_cleared": result.metadata_cleared,
    }


@mcp.tool()
def detect_pii(
    file_path: str,
    threshold: float = 0.7,
    entity_types: list[str] | None = None,
) -> dict:
    """Detect PII in a document without modifying it.

    Returns masked labels and entity types — raw PII text is never
    included in the response. No start/end indices are provided to
    prevent span reconstruction.

    Args:
        file_path: Path to the file to scan.
        threshold: Confidence threshold (0.0-1.0).
        entity_types: Entity types to detect (e.g., ["PERSON", "US_SSN"]).
    """
    from scrubfile import _extract_text, _IMAGE_EXTENSIONS
    from scrubfile.detector import detect_pii as _detect_pii
    from scrubfile.utils import validate_input_file

    try:
        input_path = validate_input_file(file_path)
    except (FileNotFoundError, ValueError) as e:
        return {"status": "error", "message": str(e)}

    suffix = input_path.suffix.lower()

    try:
        text = _extract_text(input_path, suffix, "easyocr")
    except Exception as e:
        return {"status": "error", "message": f"Text extraction failed: {type(e).__name__}"}

    try:
        detections = _detect_pii(
            text=text,
            threshold=threshold,
            entity_types=entity_types,
        )
    except Exception as e:
        return {"status": "error", "message": f"Detection failed: {type(e).__name__}"}

    # Mask detected values — only return type and confidence, never raw text
    masked_detections = [
        {
            "entity_type": d.entity_type,
            "masked_label": f"[DETECTED-{i+1}]",
            "confidence": round(d.score, 3),
        }
        for i, d in enumerate(detections)
    ]

    return {
        "status": "success",
        "input_file": input_path.name,
        "detections": masked_detections,
        "total": len(detections),
    }


@mcp.tool()
def preview_redactions(
    file_path: str,
    terms: list[str] | None = None,
    auto: bool = False,
    threshold: float = 0.7,
) -> dict:
    """Preview what would be redacted without modifying the file.

    No files are created, modified, or persisted. Returns a count and
    masked labels only.

    Args:
        file_path: Path to the file to preview.
        terms: PII strings to look for.
        auto: Auto-detect PII using NLP.
        threshold: Confidence threshold for auto-detection.
    """
    from scrubfile import redact

    try:
        result = redact(
            file_path=file_path,
            terms=terms,
            auto=auto,
            threshold=threshold,
            preview=True,
        )
    except (FileNotFoundError, ValueError) as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": f"Preview failed: {type(e).__name__}"}

    masked_entities = [
        {"type": "AUTO" if auto else "EXPLICIT", "masked_label": f"[DETECTED-{i+1}]"}
        for i in range(len(result.terms_found))
    ]

    return {
        "status": "preview",
        "input_file": Path(result.input_path).name,
        "would_redact": len(result.terms_found),
        "entities": masked_entities,
    }


if __name__ == "__main__":
    mcp.run()
