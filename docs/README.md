# Scrubfile

A local-only PII redaction tool for documents. Finds and permanently removes sensitive information from PDFs, with image and DOCX support planned.

**Everything runs on your machine. No cloud APIs, no telemetry, no network calls at runtime.**

---

## Quick Start

```bash
# Install
pip install -e .

# Redact terms from a PDF
scrubfile report.pdf --redact "John Doe" --redact "123-45-6789"

# Use a terms file (one term per line)
scrubfile report.pdf --redact-file terms.txt

# Machine-readable output
scrubfile report.pdf --redact "Jane Smith" --json
```

## Installation

**Requirements:** Python 3.10+

```bash
git clone https://github.com/scrubfile/scrubfile.git
cd scrubfile
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

This installs the `scrubfile` CLI command and the `scrubfile` Python package.

---

## Usage

### CLI

```bash
scrubfile <file> [OPTIONS]
```

| Flag | Short | Type | Description |
|------|-------|------|-------------|
| `--redact` | `-r` | text (repeatable) | PII term to redact. Can be specified multiple times. |
| `--redact-file` | `-f` | path | File containing PII terms, one per line. Lines starting with `#` are comments. |
| `--output` | `-o` | path | Output file path. Default: `<input>_redacted_<timestamp>.pdf` |
| `--json` | | flag | Output results as JSON to stdout (machine-readable). |

**Exit codes:**

| Code | Meaning |
|------|---------|
| 0 | Success -- redactions applied and file saved |
| 1 | Error -- invalid input, missing terms, or processing failure |
| 2 | No matches -- terms were provided but none found in the document |

**Examples:**

```bash
# Redact multiple terms
scrubfile employee_record.pdf -r "John Doe" -r "123-45-6789" -r "john@example.com"

# Use a terms file
scrubfile employee_record.pdf -f pii_terms.txt

# Combine both
scrubfile employee_record.pdf -f pii_terms.txt -r "extra term"

# Custom output path
scrubfile employee_record.pdf -r "John Doe" -o cleaned.pdf

# JSON output for scripting
scrubfile employee_record.pdf -r "John Doe" --json
```

### Python API

```python
from scrubfile import redact

# Basic usage
result = redact("report.pdf", terms=["John Doe", "123-45-6789"])
print(result.total_redactions)   # 5
print(result.pages_affected)     # 2
print(result.output_path)        # report_redacted_20260329_153045.pdf

# Custom output path
result = redact("report.pdf", terms=["Jane Smith"], output="clean.pdf")

# String paths work too
result = redact("/path/to/file.pdf", terms=["SSN: 123-45-6789"])
```

**Return type: `RedactionResult`**

| Field | Type | Description |
|-------|------|-------------|
| `input_path` | `str` | Absolute path to the input file |
| `output_path` | `str` | Absolute path to the redacted output file |
| `total_redactions` | `int` | Total number of matched occurrences redacted |
| `pages_affected` | `int` | Number of pages with at least one redaction |
| `terms_found` | `dict[str, int]` | Map of each matched term to its occurrence count |
| `metadata_cleared` | `bool` | Whether PDF metadata was scrubbed |

### Terms File Format

Plain text, one term per line. Comments (lines starting with `#`) and blank lines are ignored.

```text
# Employee PII
John Doe
Jane Doe

# Identifiers
123-45-6789
555-123-4567
john@example.com

# Address
123 Main Street, Springfield, IL 62701
```

### JSON Output Format

When `--json` is used, output goes to stdout as a single JSON object.

**Success:**
```json
{
  "status": "success",
  "input": "/path/to/input.pdf",
  "output": "/path/to/input_redacted_20260329_153045.pdf",
  "redactions": 5,
  "pages_affected": 2,
  "terms_matched": 2,
  "term_counts": {
    "[TERM-1]": 3,
    "[TERM-2]": 2
  },
  "metadata_cleared": true
}
```

**No matches (exit code 2):**
```json
{
  "status": "no_redactions",
  "input": "/path/to/input.pdf",
  "output": "/path/to/input_redacted_20260329_153045.pdf",
  "redactions": 0
}
```

**Error (exit code 1):**
```json
{
  "status": "error",
  "message": "File not found: /path/to/missing.pdf"
}
```

Note: PII terms are never included in the output. `term_counts` uses masked labels (`[TERM-1]`, `[TERM-2]`) to prevent the tool from echoing sensitive data into logs or terminal history.

---

## How Redaction Works

### What happens to the PDF

1. **Search:** PyMuPDF's `page.search_for(term)` locates every occurrence of each term, returning exact bounding box coordinates. Search is case-insensitive.

2. **Annotate:** A redaction annotation is placed over each match: `page.add_redact_annot(rect, fill=(0,0,0))` -- a black filled rectangle.

3. **Apply:** `page.apply_redactions()` permanently removes the text and graphics under each annotation from the PDF content stream. This is not a visual overlay -- the underlying data is deleted.

4. **Scrub metadata:** `doc.set_metadata({})` clears standard fields (author, title, creator, producer, dates). `doc.scrub()` removes XMP metadata and other embedded data.

5. **Save:** The file is saved with `garbage=3` (removes orphaned objects) and `deflate=True` (compression). Output file permissions are set to `0o600` (owner read/write only).

### What this means

- Redacted text **cannot be recovered** by selecting, copying, or extracting text from the PDF.
- The PDF's internal content stream no longer contains the redacted strings.
- Metadata (author, creator, timestamps) is cleared.
- The output is a valid, smaller PDF.

### What this does NOT cover (Phase 1 limitations)

- **Scanned PDFs / image-only PDFs:** If the PDF has no text layer (just images of text), the tool won't find any matches. Phase 2 adds OCR for this.
- **Text in embedded images:** Images within the PDF are not processed. Phase 2 addresses this.
- **Partial/fuzzy matching:** The tool searches for exact strings. "John" won't match "Johnson" and "123 Main St" won't match "123 Main Street" unless both are provided.
- **Non-English PII detection:** Phase 3's auto-detection uses English-only NLP models initially.

---

## Smart Term Expansion

The tool automatically expands SSNs and phone numbers to search all common format variants. You only need to provide one format.

### SSN Expansion

Provide any format -- the tool searches for all three:

| You provide | Also searched |
|-------------|---------------|
| `123-45-6789` | `123456789`, `123 45 6789` |
| `123456789` | `123-45-6789`, `123 45 6789` |
| `123 45 6789` | `123-45-6789`, `123456789` |

### Phone Number Expansion

Provide any US phone format -- the tool searches all six:

| You provide | Also searched |
|-------------|---------------|
| `555-123-4567` | `5551234567`, `555.123.4567`, `555 123 4567`, `(555) 123-4567`, `(555)123-4567` |
| `5551234567` | `555-123-4567`, `555.123.4567`, `555 123 4567`, `(555) 123-4567`, `(555)123-4567` |
| `(555) 123-4567` | `555-123-4567`, `5551234567`, `555.123.4567`, `555 123 4567`, `(555)123-4567` |

Other terms (names, emails, addresses) are searched as exact strings only.

---

## Design Decisions

### Why PyMuPDF?

PyMuPDF is the only Python library with a built-in redaction API (`add_redact_annot` + `apply_redactions`). Alternatives:

| Library | Can extract text? | Can redact? | Notes |
|---------|:-:|:-:|-------|
| **PyMuPDF** | Yes | Yes | Native redaction API. AGPL-3.0 license. |
| **pdfplumber** | Yes | No | Read-only. Good for extraction but can't modify PDFs. |
| **pikepdf** | No | Partially | Low-level PDF manipulation. No text extraction, no redaction API. Would require manual content stream surgery. |
| **reportlab** | No | No | PDF generation only. Cannot read existing PDFs. |

**License note:** PyMuPDF is AGPL-3.0. This means distributing the tool (PyPI, binaries, network service) requires the entire project to be AGPL-3.0, or a commercial license from Artifex. Private/local use is unrestricted. This must be resolved before public release.

### Why Typer?

- Type-hinted CLI arguments (no manual parser setup)
- Auto-generated `--help` with clear formatting
- Typed parameters catch errors before the code runs
- Built on Click, well-tested

### Why mask PII in output?

A PII redaction tool should not echo the PII it's removing. If the output showed `"John Doe": 3 occurrences`, that PII would end up in:
- Terminal scrollback
- Shell history files
- CI/CD logs
- Log aggregation systems

Instead, the output shows `[TERM-1]: 3` -- you already know what terms you provided.

### Why timestamp in output filenames?

Running the tool twice on the same file should not silently overwrite the previous output. Timestamped filenames (`report_redacted_20260329_153045.pdf`) prevent this and create a clear audit trail. You can always override with `--output`.

### Why restrict file permissions to 0o600?

Default file creation on Unix uses umask 0o022, making files readable by all local users (0o644). A redacted document still contains sensitive non-redacted content, so the output is restricted to owner-only access (0o600 = `rw-------`).

### Why expand SSN/phone variants automatically?

PII often appears in multiple formats within a single document (e.g., an SSN as `123-45-6789` in one place and `123456789` in another). Requiring the user to manually provide every variant is error-prone. The tool detects the pattern and generates all common variants automatically.

### Why a pluggable OCR provider? (Phase 2)

Different OCR engines have different trade-offs:

| Engine | Install | Accuracy | Speed |
|--------|---------|----------|-------|
| EasyOCR | `pip install` (pure Python) | Better on varied fonts | Slower |
| Tesseract | `brew install tesseract` (system dep) | Good on clean docs | Faster |
| PaddleOCR | Heavy (PaddlePaddle framework) | Best overall | Fast |

An `OCRProvider` protocol lets users pick the engine that fits their needs without changing tool code.

---

## Security Model

The tool is designed for **trusted local use** -- processing your own files on your own machine. It is not hardened for untrusted input from the internet.

### Protections

| Protection | Implementation |
|-----------|----------------|
| **File size limit** | 100MB max. Prevents memory exhaustion. |
| **File type validation** | Only `.pdf` accepted (Phase 1). Rejects unexpected types. |
| **Symlink rejection** | Output paths and terms files are checked for symlinks before use. Prevents path traversal. |
| **Output permissions** | Files created with `0o600` (owner-only). Prevents unauthorized reads. |
| **PII masking in output** | Terms shown as `[TERM-1]` etc. Never echoed in CLI/JSON output. |
| **No shell execution** | All file operations via Python APIs. No `subprocess`, `os.system`, or `exec`. |
| **No network calls** | Zero imports of `requests`, `urllib`, `socket`. Fully offline. |
| **Metadata scrubbing** | `set_metadata({})` + `scrub()` removes author, creator, timestamps, XMP. |
| **Content stream removal** | `apply_redactions()` deletes text from PDF internals, not just visual overlay. |
| **Path resolution** | All paths resolved to absolute via `Path.resolve()` before use. |

### Known Limitations

- **Metadata scrubbing may be incomplete:** `scrub()` handles standard and XMP metadata but may not remove all custom properties, embedded files, or form field data.
- **No PDF magic byte validation:** The tool trusts the `.pdf` extension and PyMuPDF's parser. A malformed file with a `.pdf` extension will be opened.
- **TOCTOU on symlinks:** There is a theoretical time-of-check-time-of-use gap between the symlink check and the file operation. Low risk for local use.
- **No term count limit:** A terms file with millions of lines could cause memory exhaustion. Practical limit is system memory.

---

## Architecture

```
src/scrubfile/
├── __init__.py         # Public API: redact() function
├── cli.py              # Typer CLI: argument parsing, output formatting
├── pdf.py              # PDF engine: search, annotate, apply, scrub, save
└── utils.py            # Validation: file checks, path safety, term loading, variant expansion
```

**Data flow:**

```
User Input (CLI or API)
  │
  ├─ Terms: --redact flags / --redact-file / API list
  │    └─ expand_term_variants() → SSN/phone variants added
  │
  ├─ Input file: validated (exists, type, size)
  │
  └─ Output path: resolved (default with timestamp, symlink check)
       │
       ▼
   redact_pdf(input, output, terms)
     ├─ For each page:
     │    ├─ For each term:
     │    │    ├─ page.search_for(term) → bounding boxes
     │    │    └─ page.add_redact_annot(rect, fill=black)
     │    └─ page.apply_redactions()
     ├─ doc.set_metadata({})
     ├─ doc.scrub()
     ├─ doc.save(garbage=3, deflate=True)
     └─ os.chmod(output, 0o600)
           │
           ▼
       RedactionResult → CLI output (masked) or API return
```

---

## Dependencies

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| PyMuPDF | >= 1.24.0 | PDF text search, redaction, metadata clearing | AGPL-3.0 |
| typer | >= 0.12.0 | CLI framework with type-hinted arguments | MIT |
| rich | >= 13.0.0 | Colored terminal output, tables | MIT |

**Dev dependencies:**

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >= 8.0 | Test framework |
| pytest-cov | >= 5.0 | Code coverage |

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=scrubfile --cov-report=term-missing
```

**Test coverage:**

| Test file | Tests | What it covers |
|-----------|:-----:|----------------|
| `test_pdf.py` | 17 | Redaction accuracy (names, SSN, email, address), metadata clearing, output validity, file permissions, edge cases |
| `test_cli.py` | 13 | All CLI flags, JSON output format, exit codes, combined term sources, PII masking verification |
| `test_api.py` | 7 | Public `redact()` API, string/Path inputs, default output paths, error handling |
| `test_utils.py` | 21 | Input validation, symlink rejection, terms file parsing, SSN expansion, phone expansion |
| **Total** | **63** | |

Tests use golden PDFs generated in `conftest.py` with known PII at known positions. Each test creates fresh fixtures in `tmp_path` -- no shared state between tests.

---

## Roadmap

| Phase | Scope | Status |
|-------|-------|--------|
| **1** | PDF redaction with explicit PII terms | Done |
| **2** | Image (PNG/JPEG via OCR) and DOCX support | Planned |
| **3** | Auto-detection of PII (no manual input), MCP server | Planned |

See [PLAN.md](../PLAN.md) for detailed phase specifications.
