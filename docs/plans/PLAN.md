# PII Scrubfile — Implementation Plan

## Context

Build a local-only PII redaction tool that processes documents (PDF, images, DOCX) and removes personally identifiable information. The tool must run entirely on a MacBook with zero cloud dependencies. No single existing tool fills this gap — open-source PII detectors (Presidio, scrubadub) operate on plain text only and can't produce redacted documents, while desktop PDF editors (Adobe, Foxit) lack ML-based auto-detection and only handle PDFs.

---

## Existing Tools & Software Landscape

### Open-Source (Free, Local)

| Tool | What it does | Pros | Cons |
|------|-------------|------|------|
| **Microsoft Presidio** | NLP+regex PII detection on text & images | Extensible, 50+ entity types, active community (7.4k stars), multi-language | Text-only core — can't parse/output PDFs or DOCX; no metadata scrubbing |
| **scrubadub** | Regex-based PII scrubbing for text | Simple API, production-ready, plugin architecture | Text-only, advanced NER requires add-ons |
| **spaCy / Stanza** | General NER (PERSON, ORG, LOC) | Fast, high-quality models, local | Not PII-specific (no SSN, email, phone detection) |
| **Apache Tika** | Text extraction from 1000+ file types | Unmatched format breadth | Java dependency, extraction only — no redaction output |
| **PyMuPDF (fitz)** | PDF read/write with built-in redaction API | Native redaction support, fast, Python | PDF-only |
| **Tesseract OCR** | OCR engine for images | 100+ languages, mature | OCR only — no redaction |
| **ExifTool** | Metadata read/write for 300+ file types | Never connects to internet, thorough | Metadata only — no content redaction |

### Commercial / SaaS (Cloud-Dependent — DON'T meet local requirement)

| Tool | Why it fails local requirement |
|------|-------------------------------|
| **Google Cloud DLP** | Cloud-only API, $1-3/GB |
| **AWS Comprehend / Macie** | Cloud-only, data leaves machine |
| **Azure AI PII** | Cloud-only, requires Azure subscription |
| **Nightfall AI / Spirion / Ground Labs** | Enterprise SaaS/cloud, opaque pricing |

### Desktop Software (Local, but limited)

| Tool | Pros | Cons |
|------|------|------|
| **Adobe Acrobat Pro** ($23/mo) | Gold standard PDF redaction, metadata scrub | PDF-only, manual/keyword — no ML auto-detect |
| **Foxit PDF Editor** (~$130) | Has "Smart Redact" AI feature | PDF-only, AI may need cloud, accuracy unclear |
| **PDF Expert** (~$80) | Native macOS, simple | Manual-only, no auto-detect, PDF-only |

### The Gap Our Tool Fills

No existing local tool combines:
1. **Multi-format input** (PDF + images + DOCX)
2. **ML-powered auto-detection** of PII entities
3. **Format-preserving redacted output** (not just text replacement)
4. **Metadata scrubbing**
5. **100% offline** — no cloud APIs or telemetry at runtime. First-time setup downloads OCR models (~200MB) and spaCy models (~560MB) which are cached locally; after that, fully air-gapped operation
6. **Phased approach** — works with explicit PII first, then auto-detects
7. **LLM-friendly interfaces** — CLI, Python API, and MCP server

---

## Design for LLM Discoverability

The tool should be trivially usable by code LLMs (Claude Code, Cursor, Copilot, etc.). Three interfaces:

### 1. CLI with JSON Output (for subprocess calls)
```bash
# Human-readable (default)
scrubfile file.pdf --redact "John Doe"

# Machine-readable JSON output (for LLM parsing)
scrubfile file.pdf --redact "John Doe" --json
# → {"status": "success", "input": "file.pdf", "output": "file_redacted.pdf", "redactions": 3}

# Preview in JSON (LLMs can inspect before committing)
scrubfile file.pdf --auto --preview --json
# → {"detections": [{"type": "PERSON", "text": "John Doe", "score": 0.95, "page": 1}, ...]}
```

- Predictable exit codes: 0 = success, 1 = error, 2 = no redactions found
- Comprehensive `--help` text (LLMs read this to learn usage)
- Stdin support: `cat file.pdf | scrubfile --redact "term"` for piping

### 2. Python API (for LLMs writing scripts)
```python
from scrubfile import redact

# One-liner — LLMs love simple APIs
result = redact("input.pdf", terms=["John Doe", "123-45-6789"])

# Auto-detect
result = redact("input.pdf", auto=True, threshold=0.7)

# Preview without modifying
detections = redact("input.pdf", auto=True, preview=True)
```

The `redact()` function is the single entry point — it auto-detects file type and routes to the correct handler. Returns a result object with metadata.

### 3. MCP Server (Phase 3+ — for direct LLM tool use)
```python
# Expose as MCP tools that Claude Code / other LLMs can call natively
@mcp.tool()
def redact_file(file_path: str, terms: list[str]) -> dict: ...

@mcp.tool()
def detect_pii(file_path: str, threshold: float = 0.7) -> list[dict]: ...

@mcp.tool()
def preview_redactions(file_path: str, auto: bool = True) -> list[dict]: ...
```

This is the killer feature for LLM adoption — an LLM can directly call `redact_file` as a tool without writing any code. We'll add this after the core is stable.

### Package Discoverability
- **Package name:** Check PyPI availability before committing. `scrubfile` may be taken — fallback candidates: `pii-redactor`, `docredact`, `redact-pii`
- `pip install <name>` makes both the CLI and Python API available
- `pyproject.toml` `[project.scripts]` entry: `scrubfile = "scrubfile.cli:app"`
- Clear package description and keywords for PyPI search

---

## Tech Stack

- **Language:** Python 3.10+
- **CLI framework:** Typer (modern, type-hinted CLI with auto-generated `--help`)
- **PDF:** PyMuPDF (fitz) `>=1.24.0` (pinned — `scrub()`, `set_metadata()`, and redaction APIs vary across versions)
- **Images (Phase 2):** Pillow + EasyOCR (pure Python, no system install needed, better accuracy than Tesseract on varied fonts/styles, native bounding box support)
- **DOCX (Phase 2):** python-docx for Word document manipulation
- **PII auto-detection (Phase 3):** Microsoft Presidio (presidio-analyzer) with spaCy `en_core_web_lg` model + custom regex recognizers for SSN, phone, etc. **English-only initially** — Presidio supports other languages but requires separate spaCy models per language. Non-English support is a future extension, not Phase 3.
- **Metadata:** PyMuPDF's built-in metadata clearing (PDFs), Pillow for EXIF stripping (images)
- **Testing:** pytest
- **Packaging:** pyproject.toml with optional dependency groups per phase

### OCR Engine Choice: EasyOCR over Tesseract

| | EasyOCR | Tesseract |
|--|---------|-----------|
| **Install** | `pip install easyocr` (pure Python) | Requires `brew install tesseract` (system dep) |
| **Accuracy** | Better on varied fonts, styles, noise | Good on clean documents |
| **Bounding boxes** | Native `readtext()` returns boxes | Via `image_to_data()` |
| **Model size** | ~200MB (downloaded once) | ~15MB + language packs |
| **Speed** | Slower (PyTorch-based, CPU ok) | Faster |
| **GPU** | Optional (CUDA), works fine on CPU | CPU only |

EasyOCR is the better default because: no system dependency (easier install for users and LLMs), better accuracy on real-world documents, and pure Python. Speed difference is acceptable for document-level redaction.

### Pluggable OCR Provider

The OCR engine is abstracted behind a simple protocol so users can swap engines:

```python
# src/scrubfile/ocr.py

class OCRResult:
    text: str
    bbox: tuple[int, int, int, int]  # (x, y, w, h)
    confidence: float

class OCRProvider(Protocol):
    def extract(self, image: Image) -> list[OCRResult]: ...

class EasyOCRProvider:     # Default — pure Python, good accuracy
    ...

class TesseractProvider:   # Lightweight alternative
    ...

class PaddleOCRProvider:   # Best accuracy, heavier install
    ...
```

Usage via CLI: `scrubfile image.png --redact "John" --ocr-engine tesseract`
Usage via API: `redact("image.png", terms=[...], ocr_engine="paddleocr")`
Default: `easyocr`. Only the selected provider's dependency needs to be installed.

**Packaging rule:** EasyOCR is a **required dependency** when installing Phase 2+ (i.e., `pip install scrubfile` includes EasyOCR out of the box). Alternative OCR engines are optional extras:
```toml
[project.dependencies]
easyocr = ">=1.7"              # default OCR — included automatically

[project.optional-dependencies]
tesseract = ["pytesseract"]     # pip install scrubfile[tesseract]
paddleocr = ["paddlepaddle", "paddleocr"]  # pip install scrubfile[paddleocr]
```
Phase 1 (PDF-only) does not require any OCR engine. The `easyocr` dependency is added when Phase 2 lands.

---

## Phase 1: PDF Redaction with Explicit PII Input

**Scope:** User provides a PDF + a list of PII strings to redact. Tool finds all occurrences and produces a redacted PDF.

**Feasibility:** Easy — PyMuPDF has first-class redaction support.

### Architecture

```
CLI Input                    Core Engine                    Output
─────────                    ───────────                    ──────
--input file.pdf    →   PDFRedactor                   →   file_redacted.pdf
--redact "John Doe"     ├─ search_text(term)               (black boxes over PII,
--redact "123-45-6789"  ├─ add_redact_annotations()         text layer removed,
                        ├─ apply_redactions()                metadata cleared)
                        └─ clear_metadata()
```

### Files to Create

```
scrubfile/
├── pyproject.toml              # Project config, dependencies, [project.scripts] entry
├── src/
│   └── scrubfile/
│       ├── __init__.py         # Public API: exports redact() function
│       ├── cli.py              # Typer CLI entrypoint (--json flag for machine output)
│       ├── pdf.py              # PDF redaction using PyMuPDF
│       └── utils.py            # Shared utilities (file validation, output naming)
└── tests/
    ├── conftest.py
    ├── test_pdf.py             # Unit tests for PDF redaction
    ├── test_cli.py             # CLI integration tests (including JSON output)
    └── fixtures/               # Sample test PDFs
        └── sample.pdf
```

### License Note: PyMuPDF is AGPL-3.0

PyMuPDF (fitz) is licensed under **AGPL-3.0**. AGPL obligations trigger on **distribution** — publishing this tool on PyPI, shipping binaries, or exposing it as a network service all count. Private use on your own machine does not.

Concretely:
- **Publishing on PyPI or GitHub under MIT/Apache:** NOT compatible. The combined work must be AGPL-3.0, or you need a commercial license from Artifex.
- **Publishing under AGPL-3.0:** Compatible — but all downstream users must also comply with AGPL (source availability, same license for derivative works).
- **Commercial license from Artifex:** Removes AGPL constraints. Pricing not public — contact Artifex.
- **If AGPL is unacceptable and no commercial license:** The fallback is `pdfplumber` (text extraction with coordinates) + `pikepdf` (PDF content stream manipulation). This is significantly harder — you'd reimplement redaction by surgically editing PDF content stream operators, which is brittle across different PDF producers. PyMuPDF is the only Python library with a built-in redaction API.

**Decision needed before publishing:** Choose AGPL-3.0 for the project, buy a commercial Artifex license, or invest in the pdfplumber+pikepdf alternative.

### Key Implementation Details

1. **Text search:** PyMuPDF's `page.search_for(term)` returns `Rect` objects with exact coordinates
2. **Redaction:** `page.add_redact_annot(rect, fill=(0,0,0))` + `page.apply_redactions()` permanently removes text under the black box
3. **Metadata clearing:** `doc.set_metadata({})` + `doc.scrub()` removes author, creator, timestamps, XMP data
4. **Case-insensitive matching:** Search both original and case-folded variants
5. **Output:** Save as `<filename>_redacted.pdf` in same directory (or user-specified output path)

### CLI Interface

```bash
# Basic usage
scrubfile file.pdf --redact "John Doe" --redact "123-45-6789"

# With output path
scrubfile file.pdf --redact "Jane Smith" -o redacted_output.pdf

# From a file containing PII terms (one per line)
scrubfile file.pdf --redact-file pii_terms.txt
```

### Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| PII in images/scanned pages (not in text layer) | Phase 1 only handles text-layer PDFs; Phase 2 adds OCR |
| Partial matches (e.g., "John" inside "Johnson") | Match whole terms; add `--exact` flag for word-boundary matching |
| PII split across lines/text blocks | PyMuPDF handles multi-block search; add cross-line search fallback |

---

## Phase 2: Extend to Images & DOCX

**Scope:** Add support for PNG, JPEG, TIFF (via OCR) and DOCX files. Still requires explicit PII input.

**Feasibility:** Moderate — OCR bounding box accuracy is the main challenge.

### Image Redaction Flow

```
Image (PNG/JPEG)
  → EasyOCR reader.readtext(image) → get bounding boxes + text for every word
  → match PII terms against extracted text
  → draw filled black rectangles over matching regions using Pillow
  → strip EXIF metadata
  → save redacted image
```

### DOCX Redaction Flow

```
DOCX file
  → python-docx: iterate paragraphs + tables + headers/footers
  → find and replace PII terms with "█████" (redacted block chars)
  → clear document properties (author, company, etc.)
  → save redacted DOCX
```

### New/Modified Files

```
src/scrubfile/
├── ocr.py              # OCRProvider protocol + EasyOCR/Tesseract/PaddleOCR adapters
├── image.py            # Image redaction (uses OCRProvider for text detection, Pillow for drawing)
├── docx.py             # DOCX text search + redaction (python-docx)
├── metadata.py         # Metadata scrubbing (Pillow for images, python-docx for DOCX)
└── cli.py              # Updated: auto-detect file type, --ocr-engine flag, route to correct handler
```

### Dependencies Added
- `easyocr` (pure Python — no system install needed)
- `Pillow`
- `python-docx`

### Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| OCR accuracy on low-res images | Warn user; preprocess with contrast/DPI enhancement before OCR |
| EasyOCR first-run model download (~200MB) | Inform user on first run; models cached locally after that |
| PII in DOCX embedded images | Phase 2 handles text runs only; flag embedded images for manual review |
| DOCX complex formatting (tables, text boxes) | python-docx handles paragraphs and tables; log warning for unsupported elements |

---

## Phase 3: Auto-Detection of PII (No Manual Input Required)

**Scope:** Tool automatically detects PII using NLP + regex patterns. User doesn't need to specify what to redact.

**Feasibility:** Moderate-to-Hard — detection accuracy is never 100%; needs good defaults + user review workflow.

### Detection Engine (Presidio-based)

```
Document
  → Extract text (PyMuPDF / EasyOCR / python-docx)
  → Presidio AnalyzerEngine.analyze(text)
      ├─ spaCy NER: PERSON, ORG, GPE, DATE
      ├─ Built-in recognizers: EMAIL, PHONE, URL, IP_ADDRESS
      ├─ Custom recognizers:
      │   ├─ SSN (regex: \d{3}-\d{2}-\d{4})
      │   ├─ Credit card (Luhn check)
      │   ├─ US Address patterns
      │   └─ Custom names list (optional)
      └─ Returns: [(entity_type, start, end, score)]
  → Map detected spans back to document coordinates
  → Redact with appropriate handler (PDF/image/DOCX)
```

### CLI Additions

```bash
# Auto-detect all PII
scrubfile file.pdf --auto

# Auto-detect specific types only
scrubfile file.pdf --auto --types PERSON,SSN,EMAIL

# Preview mode — show what would be redacted without modifying
scrubfile file.pdf --auto --preview

# Set confidence threshold (default 0.7)
scrubfile file.pdf --auto --threshold 0.5

# Combine: auto-detect + explicit terms
scrubfile file.pdf --auto --redact "custom secret term"
```

### New/Modified Files

```
src/scrubfile/
├── detector.py         # PII detection engine wrapping Presidio
├── recognizers.py      # Custom Presidio recognizers (SSN, address, etc.)
└── cli.py              # Updated: --auto, --types, --preview, --threshold flags
```

### Dependencies Added
- `presidio-analyzer`
- `presidio-anonymizer`
- `spacy` + `en_core_web_lg` model (~560MB download, runs locally)

### Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| False positives (over-redaction) | `--preview` mode shows detections before applying; `--threshold` controls sensitivity |
| False negatives (missed PII) | Combine NLP + regex; allow `--redact` alongside `--auto` for manual additions |
| spaCy model is large (~560MB) | One-time download; document in setup instructions; consider `en_core_web_md` as lighter alternative |
| **Span-to-PDF coordinate alignment** (hardest problem) | Presidio returns character offsets in extracted text, but PDF text models have reading order quirks, hyphenation, and multi-column layouts. `search_for()` works when the detected span is an exact substring; for mismatches, implement: (1) per-page text block extraction so spans are page-scoped, (2) fuzzy substring matching as fallback, (3) user warning when a detected entity can't be located in the PDF layout. **This is an explicit design + test work item, not a hand-wave.** |
| OCR noise amplifies false positives/negatives | OCR errors (e.g., "Joh n Doe", "l23-45-6789") degrade both detection and coordinate mapping. Preprocess OCR text (merge fragments, normalize whitespace) before sending to Presidio. Add OCR confidence threshold to skip low-quality regions. |
| Performance on large documents | Process page-by-page; add progress bar (rich/tqdm) |
| English-only detection | Presidio + `en_core_web_lg` is English-centric. Non-English documents will have high false-negative rates. Document this limitation; future work can add `--language` flag with appropriate spaCy models. |

---

## Security & Input Hardening

This tool opens arbitrary user-supplied files. Basic safeguards (not full sandboxing):

- **File size limit:** Reject files above a configurable max (default 100MB) to prevent memory exhaustion
- **Output path validation:** Resolve output paths to absolute, reject symlinks pointing outside the working directory
- **No path traversal:** Sanitize `--output` to prevent writing to `/etc/`, `~/.ssh/`, etc.
- **Nested decompression:** DOCX files are ZIP archives — don't follow recursive decompression (zip bombs). python-docx handles this safely by default
- **No shell injection:** All file paths passed to PyMuPDF/Pillow/python-docx via Python APIs, never via shell commands

These are lightweight checks, not a security boundary. The tool is designed for trusted local use, not untrusted input from the internet.

---

## Verification Plan

### Phase 1 Testing
```bash
# Install
pip install -e .

# Create a test PDF with known PII, then:
scrubfile test.pdf --redact "John Doe" --redact "123-45-6789"

# Verify:
# 1. Output PDF exists and opens correctly
# 2. PII text is visually blacked out
# 3. Selecting/copying text where PII was returns nothing (text layer removed)
# 4. PDF metadata (author, creator) is cleared
# 5. pytest passes
```

### Golden Test Fixtures
Create purpose-built test files with **known PII at known positions** for automated assertions:
- `tests/fixtures/golden.pdf` — contains "John Doe", "123-45-6789", "john@example.com" at specific locations
- Tests assert: (1) redacted PDF text extraction returns no PII strings, (2) metadata fields are empty, (3) file is valid PDF
- Phase 2: `tests/fixtures/golden.png` — image with known text for OCR verification
- Phase 3: `tests/fixtures/golden_auto.pdf` — contains diverse PII types for auto-detection accuracy tests

### Phase 2 Testing
```bash
# Image: create a test image with text containing PII
scrubfile test_image.png --redact "Jane Smith"
# Verify: PII region is blacked out, EXIF data stripped

# DOCX: create a test document with PII
scrubfile test.docx --redact "555-12-3456"
# Verify: PII replaced with block characters, document properties cleared
```

### Phase 3 Testing
```bash
# Auto-detect on PDF
scrubfile test.pdf --auto --preview
# Verify: preview shows detected entities with types and confidence scores

scrubfile test.pdf --auto
# Verify: all detected PII is redacted in output

# Test with different thresholds
scrubfile test.pdf --auto --threshold 0.3  # more aggressive
scrubfile test.pdf --auto --threshold 0.9  # more conservative
```

---

## Implementation Order

1. **Phase 1** — PDF + explicit PII
   - Project setup (pyproject.toml, src layout)
   - `pdf.py` — core redaction engine
   - `__init__.py` — public `redact()` API function
   - `cli.py` — Typer CLI with `--json` output
   - `utils.py` — file validation
   - Tests (unit + CLI integration)

2. **Phase 2** — Images + DOCX
   - `ocr.py` — pluggable OCR provider abstraction
   - `image.py` — EasyOCR + Pillow redaction
   - `docx.py` — Word doc redaction
   - `metadata.py` — unified metadata scrubbing
   - Update CLI for multi-format routing + `--ocr-engine` flag
   - Update `redact()` API to handle all formats
   - Tests for each format

3. **Phase 3** — Auto-detection + MCP
   - `detector.py` — Presidio integration
   - `recognizers.py` — custom SSN/address recognizers
   - `--auto`, `--preview`, `--threshold` CLI flags
   - `mcp_server.py` — MCP tool server for direct LLM integration
   - Tests with known PII documents



