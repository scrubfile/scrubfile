<!-- LLM-FRIENDLY
package: scrubfile
install: pip install scrubfile
import: from scrubfile import redact
cli: scrubfile <file> [OPTIONS]
formats: pdf, png, jpg, jpeg, tiff, bmp, docx
auto_detect: scrubfile file.pdf --auto (requires: python -m spacy download en_core_web_lg)
website: https://scrubfile.com
mcp_server: python -m scrubfile.mcp_server
license: AGPL-3.0-only
local_only: true — no network calls after initial model download
output_masking: tool never echoes detected PII in output
-->

# scrubfile

**Scrub PII from PDFs, images, and DOCX files. Local-only. One command.**

[![Tests](https://github.com/scrubfile/scrubfile/actions/workflows/ci.yml/badge.svg)](https://github.com/scrubfile/scrubfile/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/scrubfile)](https://pypi.org/project/scrubfile/)
[![Python](https://img.shields.io/pypi/pyversions/scrubfile)](https://pypi.org/project/scrubfile/)
[![License](https://img.shields.io/badge/license-AGPL--3.0-blue)](LICENSE)

## Install

```bash
pip install scrubfile
```

For auto-detection (`--auto`), also download the spaCy model (~560MB, one-time):

```bash
python -m spacy download en_core_web_lg
```

## Quick Start

![Before and after redaction](assets/before-after.png)

```bash
# Redact specific terms
scrubfile document.pdf -r "John Doe" -r "123-45-6789"

# Redact terms from a file (one per line)
scrubfile document.pdf -f redact.txt -o redacted_output.pdf

# Auto-detect all PII (names, SSNs, emails, phones, addresses, ...)
scrubfile document.pdf --auto

# Preview what would be redacted (no changes made)
scrubfile document.pdf --auto --preview

# Machine-readable output
scrubfile document.pdf --auto --json
```

## Python API

```python
from scrubfile import redact

result = redact("document.pdf", terms=["John Doe", "123-45-6789"])
print(result.total_redactions)  # 5
print(result.output_path)       # document_redacted_20260330_120000.pdf
```

## Features

| Feature | Details |
|---------|---------|
| Multi-format | PDF, PNG, JPG, TIFF, BMP, DOCX |
| Auto-detect PII | Names, SSNs, emails, phones, addresses, credit cards, IBANs, and 20+ entity types via Presidio + spaCy |
| Local-only | No cloud APIs. No data leaves your machine. Zero network calls after model download. |
| Permanent redaction | Text removed from PDF content stream, not just visual overlay |
| Metadata scrubbing | PDF metadata, XMP, EXIF, DOCX properties — all cleared |
| OCR support | Redact scanned documents and images via EasyOCR or Tesseract |
| Thorough mode | `--thorough` also redacts name fragments ("John", "J. Doe") to prevent inference |
| Term expansion | Provide one SSN/phone/date/credit-card format, all variants searched automatically |
| JSON output | Machine-readable output for pipelines and automation |
| MCP server | AI agents can call scrubfile directly (see below) |
| Privacy-safe output | Detected PII is never echoed in CLI, JSON, or MCP output |

## Comparison

| | scrubfile | Adobe Acrobat | Google Cloud DLP | Presidio (standalone) |
|---|:---:|:---:|:---:|:---:|
| Local-only | Yes | Yes | No (cloud) | Yes |
| Multi-format | PDF, images, DOCX | PDF only | Text/images | Text only |
| CLI | Yes | No | No | No |
| Auto-detect PII | Yes | No | Yes | Yes |
| Agent-ready (MCP) | Yes | No | No | No |
| Metadata scrubbing | Yes | Partial | No | No |
| Free | Yes | No ($240/yr) | No (pay per API call) | Yes |

## Supported Formats

| Format | Redaction method | Notes |
|--------|-----------------|-------|
| PDF (.pdf) | Text search + content stream removal | Permanent, not visual overlay |
| PNG, JPG, JPEG, TIFF, BMP | OCR + bounding box blackout | EXIF metadata stripped |
| DOCX (.docx) | Paragraph/table/header/footer search | Unicode block chars (████) |

## MCP Server (for AI Agents)

scrubfile includes an MCP server so AI agents (Claude Code, Cursor, etc.) can redact documents directly.

**Setup** — add to your MCP config:

```json
{
  "mcpServers": {
    "scrubfile": {
      "command": "python",
      "args": ["-m", "scrubfile.mcp_server"]
    }
  }
}
```

**Available tools:**

| Tool | Description |
|------|-------------|
| `redact_file` | Redact PII from a file (explicit terms or auto-detect) |
| `detect_pii` | Scan a file for PII without modifying it |
| `preview_redactions` | Preview what would be redacted (no file changes) |

All MCP tool responses use masked labels (`[TERM-1]`, `[DETECTED-1]`). Raw PII is never included in responses.

## CLI Reference

```
scrubfile <file> [OPTIONS]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--redact TEXT` | `-r` | PII term to redact (repeatable) |
| `--redact-file PATH` | `-f` | File with terms, one per line |
| `--output PATH` | `-o` | Output path (default: `<name>_redacted_<timestamp>.<ext>`) |
| `--auto` | | Auto-detect PII using NLP |
| `--threshold FLOAT` | | Confidence threshold for auto-detect (default: 0.7) |
| `--types TEXT` | | Comma-separated entity types (e.g., `PERSON,US_SSN`) |
| `--thorough` | | Also redact name fragments and initials |
| `--preview` | | Show detections without redacting |
| `--json` | | Machine-readable JSON output |
| `--ocr-engine TEXT` | | OCR engine: `easyocr` (default) or `tesseract` |

## Model Requirements

| Component | Size | When needed | How to install |
|-----------|------|-------------|----------------|
| Python packages | ~200MB | Always | `pip install scrubfile` |
| spaCy model | ~560MB | `--auto` mode | `python -m spacy download en_core_web_lg` |
| EasyOCR models | ~300MB | Image files | Auto-downloads on first use |
| PyTorch | ~1.5GB | Image files | Installed with `pip install scrubfile` |

If models are missing, scrubfile fails with a clear error message — it will not silently download during redaction.

## Best-Effort Redaction

scrubfile redacts PII from text content in supported formats. Some document elements cannot be reliably redacted:

- **Excel formulas** that reference cells containing PII
- **Embedded objects** (charts, SmartArt, OLE objects)
- **Non-text elements** (form fields, annotations, JavaScript)

These locations are flagged with warnings when detected. Always perform a manual review for highly sensitive documents.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and guidelines.

## License

[AGPL-3.0-only](LICENSE) — required by the PyMuPDF dependency.

## Links

- **Website:** [scrubfile.com](https://scrubfile.com)
- **PyPI:** [pypi.org/project/scrubfile](https://pypi.org/project/scrubfile/)
- **GitHub:** [github.com/scrubfile/scrubfile](https://github.com/scrubfile/scrubfile)
- **Issues:** [github.com/scrubfile/scrubfile/issues](https://github.com/scrubfile/scrubfile/issues)
