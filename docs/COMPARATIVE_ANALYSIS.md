# Comparative Analysis: PII Redaction Tools (2025-2026)

How does Scrubfile compare to existing tools for removing personally identifiable information from documents? This page covers every major option — open-source, cloud, desktop, and developer tools — with honest trade-offs.

---

## The Short Version

No other single tool does what Scrubfile does: **multi-format document redaction (PDF + images + DOCX) with ML auto-detection, running 100% locally, with CLI + Python API interfaces.**

- Open-source detectors (Presidio, scrubadub) find PII in text strings but can't produce redacted PDFs or DOCX files.
- Cloud APIs (Google DLP, AWS Comprehend) are powerful but your data leaves your machine.
- Desktop editors (Adobe Acrobat, Foxit) do true PDF redaction but are GUI-only, PDF-only, and subscription-priced.
- No existing tool combines detection + redaction + multi-format + local + scriptable in one package.

---

## Detailed Comparison

### Feature Matrix

| Capability | Scrubfile | Presidio | scrubadub | Google DLP | AWS Comprehend | Adobe Acrobat | Foxit Editor |
|:-----------|:--------:|:--------:|:---------:|:----------:|:--------------:|:------------:|:------------:|
| **PDF redaction** | Yes | No | No | No | No | Yes | Yes |
| **Image redaction** | Yes (OCR) | Partial | No | Yes | No | No | No |
| **DOCX redaction** | Yes | No | No | No | No | No | No |
| **All formats in one tool** | Yes | No | No | No | No | No | No |
| **NLP auto-detection** | Yes | Yes | Partial | Yes | Yes | No | No |
| **Runs 100% local** | Yes | Yes | Yes | No | No | Yes | Yes |
| **CLI interface** | Yes | No | No | No | No | No | No |
| **Python API** | Yes | Yes | Yes | Client lib | Client lib | No | No |
| **JSON machine output** | Yes | No | No | Yes | Yes | No | No |
| **Metadata scrubbing** | Yes | No | No | No | No | Yes | Yes |
| **Free / open-source** | Yes | Yes | Yes | No | No | No | No |
| **Term variant expansion** | Yes | No | No | No | No | No | No |
| **PII masked in output** | Yes | N/A | N/A | N/A | N/A | N/A | N/A |
| **File permission hardening** | Yes | N/A | N/A | N/A | N/A | No | No |

---

## Open-Source Tools

### Microsoft Presidio

**What it is:** The most popular open-source PII detection library. Built by Microsoft. Uses spaCy/transformers for NER + regex recognizers for structured PII (SSN, credit card, etc.). 7,400+ GitHub stars.

**License:** MIT (free)

| Strength | Limitation |
|----------|-----------|
| 50+ entity types with extensible recognizer architecture | **Text-only core** — operates on strings, not documents |
| Multi-language support | Cannot open, search, or produce redacted PDFs |
| Active community and Microsoft backing | Cannot handle DOCX files |
| `presidio-image-redactor` sub-package for images | Image redaction requires Tesseract system install |
| Runs fully local | No metadata scrubbing |
| | No CLI — library only, requires Python code |
| | Span-to-document-coordinate mapping is your problem |

**How Scrubfile relates:** Scrubfile uses Presidio as its detection engine (Phase 3 `--auto` mode). It adds everything Presidio doesn't have: document parsing, format-preserving redaction output, metadata scrubbing, CLI, and multi-format routing.

### scrubadub

**What it is:** A Python library for removing PII from text strings. Simpler than Presidio, regex-heavy.

**License:** MIT (free)

| Strength | Limitation |
|----------|-----------|
| Simple API: `scrubadub.clean(text)` | Text-only — no file I/O whatsoever |
| Plugin architecture for custom detectors | Advanced NER requires add-on packages |
| Production-stable | Less actively maintained than Presidio |
| | Returns scrubbed text, not documents |
| | No bounding box / coordinate information |
| | English-centric |

### spaCy NER

**What it is:** A general-purpose NLP library with named entity recognition. Not PII-specific.

**License:** MIT (free)

Detects PERSON, ORG, GPE, DATE, MONEY — but **not** SSN, email, phone, credit card, or other structured PII. Requires building an entire detection + regex + redaction pipeline around it. Scrubfile uses spaCy indirectly through Presidio.

---

## Cloud APIs

### Google Cloud DLP

**What it is:** Google's data loss prevention API. The most comprehensive PII detector available (150+ built-in infoTypes across many countries).

**Pricing:** Inspection: $1.00/GB (first 1 GB/month free). De-identification: $2.00/GB.

| Strength | Limitation |
|----------|-----------|
| 150+ infoTypes — broadest coverage anywhere | **Cloud-only** — data must be sent to Google servers |
| Multi-language, multi-country | Cannot handle PDFs or DOCX natively |
| Image redaction via `image.redact` | Requires GCP account + API key management |
| Powerful anonymization (masking, hashing, crypto, bucketing) | Cost scales with volume |
| | Not suitable for air-gapped or privacy-sensitive environments |
| | No local/offline mode |

### AWS Comprehend

**What it is:** AWS's NLP service with PII detection and redaction for text.

**Pricing:** $0.0001 per unit (100 characters). ~$1.00 per 1M characters.

| Strength | Limitation |
|----------|-----------|
| Good PII detection for text | **Cloud-only** — data leaves your machine |
| Returns redacted text with entity labels | Text-only — no document format support |
| Integrates with AWS ecosystem | Requires AWS account |
| | No PDF/DOCX/image handling |

**AWS Macie** is a related S3-focused service that **discovers** PII in S3 buckets ($1.00/GB) but does NOT redact. Discovery only.

### Azure AI Language PII

**What it is:** Azure's text analytics PII detection API.

**Pricing:** Free tier: 5,000 records/month. Standard: $1.00 per 1,000 text records (each up to 5,120 chars).

| Strength | Limitation |
|----------|-----------|
| 50+ entity types, multi-language | **Cloud-only API** |
| Returns masked text | Text-only — no PDF/DOCX/image handling |
| | Requires Azure subscription |

### Private AI

**What it is:** Commercial PII detection platform. Claims 99.5% accuracy, 50+ entity types, 50+ languages.

**Pricing:** Enterprise (contact sales). Not publicly listed.

| Strength | Limitation |
|----------|-----------|
| On-premise Docker deployment option | Proprietary, opaque pricing |
| Multi-modal (text, images, audio) | Enterprise-focused — not a simple CLI tool |
| High reported accuracy | Docker dependency for on-prem |

---

## Desktop / Commercial Software

### Adobe Acrobat Pro

**What it is:** The industry standard for PDF editing and redaction. Gold standard for redaction quality.

**Pricing:** ~$23/month (annual plan) or ~$30/month (monthly).

| Strength | Limitation |
|----------|-----------|
| **Gold standard** PDF redaction — true content stream removal | **PDF-only** — no images, DOCX, or other formats |
| "Remove Hidden Information" tool scrubs metadata | **No NLP auto-detection** — keyword/regex search only |
| Legally defensible redaction (used by law firms, government) | GUI-only — no CLI, no API, not scriptable |
| Pattern search (SSN, phone, email regex) | $276/year subscription |
| Trusted by enterprises and regulators | Cannot detect a person's name unless you tell it what to search |

### Foxit PDF Editor

**What it is:** PDF editor with a "Smart Redact" feature that searches for PII patterns.

**Pricing:** ~$160/year (Pro). One-time purchase options may exist.

| Strength | Limitation |
|----------|-----------|
| "Smart Redact" for pattern-based PII search | **PDF-only** |
| Cheaper than Adobe | Pattern-based, not NLP — similar to Adobe's approach |
| Available on macOS and Windows | GUI-only, no CLI/API |
| | "AI" features may require cloud connectivity (unverified) |

### PDF Expert (macOS)

**What it is:** macOS-native PDF editor by Readdle. ~$80/year.

Manual redaction only. No auto-detection, no pattern search. PDF-only. Produces true redaction in recent versions.

### macOS Preview.app

**WARNING:** Preview.app can draw black rectangles over content but **does NOT perform true redaction**. The text remains in the PDF content stream and can be selected, copied, and extracted. It is NOT a redaction tool despite widespread misconception. Do not use it for PII redaction.

---

## Developer / CLI Tools

### The gap

**There is no widely-adopted CLI tool that combines PII detection + multi-format document redaction locally.** The landscape consists of:

- **Libraries** (Presidio, scrubadub, spaCy) that detect PII in text strings but produce no document output
- **Cloud APIs** (Google DLP, AWS, Azure) that require sending data to third-party servers
- **GUI applications** (Adobe, Foxit) that are not scriptable
- **Numerous GitHub proof-of-concepts** that combine Presidio + PyMuPDF but are abandoned after initial commits and lack tests, CLI, or multi-format support

Scrubfile fills this gap.

---

## Pricing Comparison

| Tool | Annual Cost | Notes |
|------|:----------:|-------|
| **Scrubfile** | **$0** | Free, open-source (AGPL-3.0 due to PyMuPDF dependency) |
| Microsoft Presidio | $0 | Free library, but no document redaction |
| scrubadub | $0 | Free library, text-only |
| Google Cloud DLP | ~$3/GB | Inspection + de-identification combined |
| AWS Comprehend | ~$1/1M chars | Text-only, no documents |
| Azure AI PII | ~$1/1K records | Text-only |
| Adobe Acrobat Pro | ~$276/year | PDF-only, GUI-only |
| Foxit PDF Editor | ~$160/year | PDF-only, GUI-only |
| Private AI | Unknown | Enterprise sales only |

---

## What Scrubfile Uniquely Provides

### 1. Multi-format pipeline in one tool

No other tool takes PDF, PNG, JPEG, TIFF, BMP, and DOCX as input and produces redacted versions of those files. Everyone else either handles text strings only (Presidio, scrubadub, cloud APIs) or handles PDFs only (Adobe, Foxit).

```bash
# One tool, any format
scrubfile report.pdf --auto
scrubfile photo.png -r "John Doe"
scrubfile contract.docx -f terms.txt
```

### 2. Detection + redaction in one command

Cloud APIs detect PII and return annotations. Desktop apps require manual search. Scrubfile's `--auto` flag runs ML detection and applies redaction in a single command.

```bash
scrubfile document.pdf --auto --threshold 0.5
```

### 3. Designed for LLM and automation use

No existing tool provides all of: structured JSON output, predictable exit codes, a single-function Python API, and PII-masked output. Adobe and Foxit are GUI-only. Presidio and scrubadub are libraries without CLIs.

```bash
# JSON for scripts/LLMs
scrubfile file.pdf --auto --json

# Python API
from scrubfile import redact
result = redact("file.pdf", auto=True)
```

### 4. Privacy-preserving output

Scrubfile masks PII terms in its own output (`[TERM-1]`, `[TERM-2]`). Other tools either echo detected PII in logs/responses or don't consider this concern. Output files are set to owner-only permissions (0o600).

### 5. Smart term expansion

When you provide an SSN or phone number in any format, Scrubfile automatically searches for all common variants. No other tool does this.

```bash
# Provide one format, all 6 are searched
scrubfile file.pdf -r "555-123-4567"
# Also finds: 5551234567, 555.123.4567, 555 123 4567, (555) 123-4567, (555)123-4567
```

### 6. True redaction with metadata scrubbing

Like Adobe Acrobat, Scrubfile performs true PDF redaction (content stream removal, not visual overlay) and scrubs metadata (author, creator, timestamps, XMP). Unlike Adobe, it also handles images and DOCX.

---

## Honest Limitations

Scrubfile is not the best choice for every scenario:

| Scenario | Better tool |
|----------|-------------|
| Legal/regulatory PDF redaction with audit trail | **Adobe Acrobat Pro** — legally established, industry-trusted |
| Scanning 150+ country-specific PII patterns | **Google Cloud DLP** — broadest infoType coverage |
| Processing petabytes of structured data | **Cloud APIs** — designed for scale |
| GUI workflow for non-technical users | **Adobe Acrobat / Foxit** — visual, point-and-click |
| Multi-language PII detection (non-English) | **Google Cloud DLP** or **Presidio with multilingual models** |
| Audio/video PII redaction | **Private AI** — supports audio natively |

Scrubfile is best when you need: **local, scriptable, multi-format, automated PII redaction** — and you don't want to stitch together 5 different tools or send your data to the cloud.

---

## Summary

| Category | Best-in-class | Scrubfile's position |
|----------|:-------------|:--------------------|
| PDF redaction quality | Adobe Acrobat Pro | Equivalent (uses PyMuPDF's native redaction) |
| PII detection breadth | Google Cloud DLP (150+ types) | Good (Presidio + custom recognizers, English-only) |
| Multi-format support | None (no tool covers all) | **Only tool with PDF + image + DOCX** |
| Local/offline operation | Presidio (detection only) | **Only tool with local detection + redaction** |
| Developer ergonomics | None adequate | **CLI + Python API + JSON output** |
| Cost | Presidio (free, detection only) | **Free, detection + redaction** |
| Enterprise compliance | Adobe Acrobat Pro | Not yet enterprise-hardened |

---

*Last updated: March 29, 2026. Pricing and features of third-party tools should be verified at their official sources.*
