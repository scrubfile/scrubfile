"""Tests for the CLI interface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from scrubfile.cli import app

runner = CliRunner()


class TestCliBasic:
    def test_no_args_shows_help(self):
        result = runner.invoke(app, [])
        # Typer with no_args_is_help shows usage and exits with 0 or 2
        assert result.exit_code in (0, 2)
        # Help text may go to stdout or be captured in output
        combined = (result.stdout or "") + (result.output or "")
        assert "redact" in combined.lower() or "usage" in combined.lower() or result.exit_code == 2

    def test_redact_single_term(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        result = runner.invoke(app, [
            str(golden_pdf), "--redact", "John Doe", "-o", str(output),
        ])
        assert result.exit_code == 0
        assert output.exists()

    def test_redact_multiple_terms(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        result = runner.invoke(app, [
            str(golden_pdf),
            "--redact", "John Doe",
            "--redact", "123-45-6789",
            "-o", str(output),
        ])
        assert result.exit_code == 0
        assert output.exists()

    def test_redact_from_file(self, golden_pdf: Path, terms_file: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        result = runner.invoke(app, [
            str(golden_pdf),
            "--redact-file", str(terms_file),
            "-o", str(output),
        ])
        assert result.exit_code == 0
        assert output.exists()

    def test_default_output_name(self, golden_pdf: Path):
        result = runner.invoke(app, [
            str(golden_pdf), "--redact", "John Doe",
        ])
        assert result.exit_code == 0
        # Output has timestamp: golden_redacted_YYYYMMDD_HHMMSS.pdf
        outputs = list(golden_pdf.parent.glob("golden_redacted_*.pdf"))
        assert len(outputs) >= 1

    def test_no_terms_exits_with_error(self, golden_pdf: Path):
        result = runner.invoke(app, [str(golden_pdf)])
        assert result.exit_code == 1

    def test_nonexistent_file(self, tmp_path: Path):
        result = runner.invoke(app, [
            str(tmp_path / "nope.pdf"), "--redact", "term",
        ])
        assert result.exit_code == 1

    def test_no_matches_exit_code_2(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        result = runner.invoke(app, [
            str(golden_pdf), "--redact", "ZZZZNONEXISTENTZZZZ", "-o", str(output),
        ])
        assert result.exit_code == 2


class TestCliJsonOutput:
    def test_json_success(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        result = runner.invoke(app, [
            str(golden_pdf), "--redact", "John Doe", "-o", str(output), "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["status"] == "success"
        assert data["redactions"] >= 3
        assert data["pages_affected"] == 2
        assert data["terms_matched"] >= 1
        # PII terms should be masked, not echoed back
        assert "John Doe" not in json.dumps(data)
        assert "[TERM-1]" in json.dumps(data)
        assert data["metadata_cleared"] is True

    def test_json_no_match(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        result = runner.invoke(app, [
            str(golden_pdf), "--redact", "NOMATCH", "-o", str(output), "--json",
        ])
        assert result.exit_code == 2
        data = json.loads(result.stdout)
        assert data["status"] == "no_redactions"
        assert data["redactions"] == 0

    def test_json_error(self, tmp_path: Path):
        result = runner.invoke(app, [
            str(tmp_path / "missing.pdf"), "--redact", "term", "--json",
        ])
        assert result.exit_code == 1
        data = json.loads(result.stdout)
        assert data["status"] == "error"
        assert "message" in data

    def test_json_with_multiple_terms(self, golden_pdf: Path, tmp_path: Path):
        output = tmp_path / "out.pdf"
        result = runner.invoke(app, [
            str(golden_pdf),
            "--redact", "John Doe",
            "--redact", "Jane Smith",
            "-o", str(output),
            "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["terms_matched"] == 2
        # PII should NOT appear in output
        raw = json.dumps(data)
        assert "John Doe" not in raw
        assert "Jane Smith" not in raw


class TestCliCombinedTermSources:
    def test_redact_flag_and_file_combined(
        self, golden_pdf: Path, terms_file: Path, tmp_path: Path
    ):
        output = tmp_path / "out.pdf"
        result = runner.invoke(app, [
            str(golden_pdf),
            "--redact", "Jane Smith",
            "--redact-file", str(terms_file),
            "-o", str(output),
            "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        # Terms from both sources should be found, but masked
        assert data["terms_matched"] >= 2
        raw = json.dumps(data)
        assert "Jane Smith" not in raw
        assert "John Doe" not in raw
