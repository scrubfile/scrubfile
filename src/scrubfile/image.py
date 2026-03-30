"""Image redaction engine using OCR + Pillow."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw

from scrubfile.ocr import OCRProvider, OCRResult, get_ocr_provider


@dataclass
class ImageRedactionResult:
    """Result of an image redaction operation."""

    input_path: str
    output_path: str
    total_redactions: int
    terms_found: dict[str, int] = field(default_factory=dict)
    metadata_cleared: bool = False


def redact_image(
    input_path: Path,
    output_path: Path,
    terms: list[str],
    ocr_engine: str = "easyocr",
) -> ImageRedactionResult:
    """Redact PII terms from an image using OCR to find text locations.

    1. Run OCR to extract text with bounding boxes
    2. Match terms against OCR results (case-insensitive, multi-word aware)
    3. Draw black rectangles over matched regions
    4. Strip EXIF metadata
    5. Save redacted image with restricted permissions
    """
    image = Image.open(str(input_path))
    provider = get_ocr_provider(ocr_engine)
    ocr_results = provider.extract(image)

    # Build matches: find which OCR results contain each term
    matches = _find_term_matches(ocr_results, terms)

    total_redactions = 0
    terms_found: dict[str, int] = {}

    if matches:
        draw = ImageDraw.Draw(image)
        for term, bboxes in matches.items():
            terms_found[term] = len(bboxes)
            total_redactions += len(bboxes)
            for bbox in bboxes:
                x, y, w, h = bbox
                draw.rectangle([x, y, x + w, y + h], fill="black")

    # Strip EXIF metadata by creating a clean copy
    clean_image = _strip_metadata(image)

    # Save
    fmt = _get_save_format(output_path)
    clean_image.save(str(output_path), format=fmt)
    os.chmod(str(output_path), 0o600)

    return ImageRedactionResult(
        input_path=str(input_path),
        output_path=str(output_path),
        total_redactions=total_redactions,
        terms_found=terms_found,
        metadata_cleared=True,
    )


def _find_term_matches(
    ocr_results: list[OCRResult], terms: list[str]
) -> dict[str, list[tuple[int, int, int, int]]]:
    """Match terms against OCR results, handling multi-word terms.

    For multi-word terms (e.g. "John Doe"), checks if the term appears
    in the concatenated text of adjacent OCR blocks and merges their
    bounding boxes.
    """
    matches: dict[str, list[tuple[int, int, int, int]]] = {}

    for term in terms:
        term_lower = term.lower()

        # First: check each individual OCR result
        for r in ocr_results:
            if term_lower in r.text.lower():
                matches.setdefault(term, []).append(r.bbox)

        # Second: check consecutive OCR results for multi-word spans
        if " " in term and len(ocr_results) > 1:
            for i in range(len(ocr_results)):
                concat_text = ""
                concat_boxes = []
                for j in range(i, min(i + 10, len(ocr_results))):
                    if concat_text:
                        concat_text += " "
                    concat_text += ocr_results[j].text
                    concat_boxes.append(ocr_results[j].bbox)

                    if term_lower in concat_text.lower():
                        merged = _merge_bboxes(concat_boxes)
                        # Avoid duplicates from single-block matches
                        if merged not in matches.get(term, []):
                            matches.setdefault(term, []).append(merged)
                        break

    return matches


def _merge_bboxes(
    boxes: list[tuple[int, int, int, int]],
) -> tuple[int, int, int, int]:
    """Merge multiple bounding boxes into one encompassing box."""
    min_x = min(b[0] for b in boxes)
    min_y = min(b[1] for b in boxes)
    max_x = max(b[0] + b[2] for b in boxes)
    max_y = max(b[1] + b[3] for b in boxes)
    return (min_x, min_y, max_x - min_x, max_y - min_y)


def _strip_metadata(image: Image.Image) -> Image.Image:
    """Create a clean copy of the image without EXIF/metadata."""
    clean = Image.new(image.mode, image.size)
    clean.paste(image)
    return clean


def _get_save_format(path: Path) -> str:
    """Map file extension to Pillow save format."""
    ext = path.suffix.lower()
    formats = {
        ".png": "PNG",
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".tiff": "TIFF",
        ".tif": "TIFF",
        ".bmp": "BMP",
    }
    return formats.get(ext, "PNG")
