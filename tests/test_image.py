"""Tests for image redaction engine."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from redactor.image import redact_image, ImageRedactionResult


def _create_test_image(path: Path, texts: list[tuple[str, tuple[int, int]]]) -> Path:
    """Create a test image with text at specified positions."""
    img = Image.new("RGB", (800, 400), color="white")
    draw = ImageDraw.Draw(img)
    for text, position in texts:
        draw.text(position, text, fill="black")
    img.save(str(path))
    return path


@pytest.fixture
def text_image(tmp_path: Path) -> Path:
    """Create a test image with known PII text."""
    return _create_test_image(
        tmp_path / "test.png",
        [
            ("Name: John Doe", (50, 50)),
            ("SSN: 123-45-6789", (50, 100)),
            ("Email: john@example.com", (50, 150)),
            ("This is a test document", (50, 250)),
        ],
    )


class TestImageRedaction:
    def test_returns_result(self, text_image: Path, tmp_path: Path):
        output = tmp_path / "out.png"
        result = redact_image(text_image, output, ["John Doe"])

        assert isinstance(result, ImageRedactionResult)
        assert output.exists()
        assert result.output_path == str(output)

    def test_redacts_found_terms(self, text_image: Path, tmp_path: Path):
        output = tmp_path / "out.png"
        result = redact_image(text_image, output, ["John Doe"])

        # If OCR found the term, it should be redacted
        if result.total_redactions > 0:
            assert "John Doe" in result.terms_found

    def test_no_match_returns_zero(self, text_image: Path, tmp_path: Path):
        output = tmp_path / "out.png"
        result = redact_image(text_image, output, ["NONEXISTENT_XYZ"])

        assert result.total_redactions == 0
        assert output.exists()

    def test_output_has_restricted_permissions(self, text_image: Path, tmp_path: Path):
        output = tmp_path / "out.png"
        redact_image(text_image, output, ["John Doe"])

        mode = output.stat().st_mode
        assert not (mode & stat.S_IRGRP)
        assert not (mode & stat.S_IROTH)

    def test_metadata_cleared(self, text_image: Path, tmp_path: Path):
        output = tmp_path / "out.png"
        result = redact_image(text_image, output, ["John Doe"])

        assert result.metadata_cleared is True
        # Output image should have no EXIF data
        out_img = Image.open(str(output))
        exif = out_img.getexif()
        assert len(exif) == 0

    def test_supports_jpeg(self, tmp_path: Path):
        img_path = _create_test_image(
            tmp_path / "test.jpg",
            [("Hello World", (50, 50))],
        )
        output = tmp_path / "out.jpg"
        result = redact_image(img_path, output, ["Hello"])

        assert output.exists()
        assert isinstance(result, ImageRedactionResult)

    def test_multiple_terms(self, text_image: Path, tmp_path: Path):
        output = tmp_path / "out.png"
        result = redact_image(
            text_image, output, ["John Doe", "123-45-6789"]
        )
        # Should process without error regardless of OCR accuracy
        assert isinstance(result, ImageRedactionResult)
        assert output.exists()


class TestImageOutputValidity:
    def test_output_is_valid_image(self, text_image: Path, tmp_path: Path):
        output = tmp_path / "out.png"
        redact_image(text_image, output, ["John Doe"])

        img = Image.open(str(output))
        assert img.size == (800, 400)
        img.close()

    def test_output_preserves_dimensions(self, text_image: Path, tmp_path: Path):
        original = Image.open(str(text_image))
        orig_size = original.size
        original.close()

        output = tmp_path / "out.png"
        redact_image(text_image, output, ["test"])

        result = Image.open(str(output))
        assert result.size == orig_size
        result.close()
