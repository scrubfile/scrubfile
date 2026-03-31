"""Shared test fixtures for scrubfile tests."""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF
import pytest


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: requires ML model downloads (spaCy, EasyOCR)")


def create_golden_pdf(path: Path) -> Path:
    """Create a test PDF with known PII at known positions."""
    doc = fitz.open()

    # Page 1: names and SSN
    page1 = doc.new_page()
    page1.insert_text(
        (72, 100),
        "Confidential Employee Record",
        fontsize=16,
        fontname="helv",
    )
    page1.insert_text(
        (72, 140),
        "Name: John Doe",
        fontsize=12,
        fontname="helv",
    )
    page1.insert_text(
        (72, 170),
        "SSN: 123-45-6789",
        fontsize=12,
        fontname="helv",
    )
    page1.insert_text(
        (72, 200),
        "Email: john@example.com",
        fontsize=12,
        fontname="helv",
    )
    page1.insert_text(
        (72, 230),
        "Address: 123 Main Street, Springfield, IL 62701",
        fontsize=12,
        fontname="helv",
    )
    page1.insert_text(
        (72, 280),
        "This document contains sensitive information about John Doe.",
        fontsize=11,
        fontname="helv",
    )

    # Page 2: more occurrences to test multi-page
    page2 = doc.new_page()
    page2.insert_text(
        (72, 100),
        "Performance Review for John Doe",
        fontsize=14,
        fontname="helv",
    )
    page2.insert_text(
        (72, 140),
        "Employee SSN: 123-45-6789",
        fontsize=12,
        fontname="helv",
    )
    page2.insert_text(
        (72, 170),
        "Reviewer: Jane Smith",
        fontsize=12,
        fontname="helv",
    )
    page2.insert_text(
        (72, 200),
        "No issues found. John Doe meets expectations.",
        fontsize=11,
        fontname="helv",
    )

    # Set metadata to verify clearing
    doc.set_metadata({
        "author": "HR Department",
        "title": "Employee Record",
        "creator": "Internal HR System",
        "producer": "Test Generator",
    })

    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def golden_pdf(tmp_path: Path) -> Path:
    """Create a fresh golden test PDF in a temp directory."""
    return create_golden_pdf(tmp_path / "golden.pdf")


@pytest.fixture
def simple_pdf(tmp_path: Path) -> Path:
    """Create a minimal single-page PDF."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Hello World. This is a test document.", fontsize=12)
    doc.save(str(tmp_path / "simple.pdf"))
    doc.close()
    return tmp_path / "simple.pdf"


@pytest.fixture
def empty_pdf(tmp_path: Path) -> Path:
    """Create a PDF with no text content."""
    doc = fitz.open()
    doc.new_page()
    doc.save(str(tmp_path / "empty.pdf"))
    doc.close()
    return tmp_path / "empty.pdf"


@pytest.fixture
def terms_file(tmp_path: Path) -> Path:
    """Create a terms file with one term per line."""
    p = tmp_path / "terms.txt"
    p.write_text("John Doe\n123-45-6789\n# this is a comment\njohn@example.com\n")
    return p
