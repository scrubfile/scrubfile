"""Pluggable OCR provider abstraction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from PIL import Image


@dataclass
class OCRResult:
    """A single text detection result with bounding box."""

    text: str
    bbox: tuple[int, int, int, int]  # (x, y, w, h) — top-left corner + dimensions
    confidence: float


class OCRProvider(Protocol):
    """Protocol for OCR engines. Implement this to add a new backend."""

    def extract(self, image: Image.Image) -> list[OCRResult]: ...


class EasyOCRProvider:
    """Default OCR provider using EasyOCR (pure Python, no system deps)."""

    def __init__(self, languages: list[str] | None = None):
        import easyocr

        self._reader = easyocr.Reader(
            languages or ["en"],
            gpu=False,
            verbose=False,
        )

    def extract(self, image: Image.Image) -> list[OCRResult]:
        import numpy as np

        img_array = np.array(image)
        raw = self._reader.readtext(img_array)

        results = []
        for bbox_points, text, confidence in raw:
            # EasyOCR returns [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
            # Convert to (x, y, w, h)
            xs = [p[0] for p in bbox_points]
            ys = [p[1] for p in bbox_points]
            x = int(min(xs))
            y = int(min(ys))
            w = int(max(xs) - x)
            h = int(max(ys) - y)
            results.append(OCRResult(text=text, bbox=(x, y, w, h), confidence=confidence))

        return results


class TesseractProvider:
    """Alternative OCR provider using Tesseract (requires system install)."""

    def extract(self, image: Image.Image) -> list[OCRResult]:
        import pytesseract

        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        results = []
        for i in range(len(data["text"])):
            text = data["text"][i].strip()
            conf = int(data["conf"][i])
            if text and conf > 0:
                x = data["left"][i]
                y = data["top"][i]
                w = data["width"][i]
                h = data["height"][i]
                results.append(OCRResult(
                    text=text,
                    bbox=(x, y, w, h),
                    confidence=conf / 100.0,
                ))

        return results


def get_ocr_provider(engine: str = "easyocr") -> OCRProvider:
    """Get an OCR provider by name."""
    if engine == "easyocr":
        return EasyOCRProvider()
    elif engine == "tesseract":
        return TesseractProvider()
    else:
        raise ValueError(f"Unknown OCR engine: {engine}. Available: easyocr, tesseract")
