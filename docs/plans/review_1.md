# PLAN.md — Review (review_1)

Thorough review of `PLAN.md` for the PII Scrubfile implementation plan.

---

## Strengths

**Problem framing**  
The gap analysis (text-only detectors vs. format-preserving redaction, local vs. cloud) is clear and the phased scope (explicit terms → multi-format → auto-detect) is a sensible way to ship value early.

**Architecture**  
Single entry point `redact()`, Typer CLI, JSON mode, and later MCP fit the “LLM-discoverable” goal well. Exit codes, `--help`, and preview before apply are the right primitives for automation.

**Honest risk sections**  
Phase 1 calls out scanned PDFs, partial matches, and split text; Phase 2 calls out OCR limits and DOCX edge cases; Phase 3 calls out FP/FN and span-to-layout mapping. That alignment between promise and limitation matters for a PII tool.

**Licensing**  
Calling out **PyMuPDF’s AGPL-3.0** early is important. The plan correctly flags that distribution (not just “running locally”) is what triggers AGPL obligations for a combined work, and that alternatives are heavier.

---

## Technical clarifications and corrections

**AGPL wording**  
The line that AGPL is “no issue” for “local CLI use” is easy to misread. More precise: **private use without distribution** is unconstrained; **shipping** a product that bundles or depends on AGPL PyMuPDF in a derivative work triggers share-alike. Worth one sentence in the plan so future PyPI/GitHub release decisions are unambiguous.

**Optional dependencies vs. “default” OCR**
The `pyproject.toml` snippet marks `easyocr` as optional with a “(default)” comment. In practice you need a rule: either **Phase 2+** makes `easyocr` a default dependency of the published package, or **images require** `pip install scrubfile[easyocr]`. The plan should state which, so install docs and CI don’t drift.

**`stdin` and binary PDFs**  
`cat file.pdf | scrubfile` is fine if implemented as “read stdin into a temp file or buffer then process,” but it should be called out: many CLIs struggle with TTY vs pipe, large files, and Windows parity. Worth a short “supported or not” note.

**PyMuPDF APIs**  
`set_metadata`, `scrub`, and exact redaction behavior vary by version. The plan should say “verify against pinned PyMuPDF version” so `doc.scrub()` / metadata clearing stay accurate in code and tests.

**Presidio output → PDF coordinates**  
The hard part in Phase 3 is not running `AnalyzerEngine.analyze(text)` but **aligning character spans in a single extracted text stream with PyMuPDF’s text model** (reading order, hyphenation, multi-column, headers). `search_for()` works when the span is an **exact** substring of what PyMuPDF would find; NER spans that don’t match the PDF text byte-for-byte need a documented fallback (fuzzy match, per-page text blocks, or user warning). The plan gestures at this; making it an explicit work item would reduce surprise.

**Package name**  
“Publish as `scrubfile` on PyPI” assumes the name is free and not confused with existing packages. A one-line “check availability / consider `pii-redactor` style name” note avoids late rename pain.

---

## Gaps worth adding (even briefly)

**Security and abuse cases**  
For a CLI that opens arbitrary PDFs/DOCX/images: limits on file size, nested decompression, and safe output paths (no symlink tricks) are worth a short “non-goals / hardening” bullet. Not full sandboxing—just awareness.

**Locales and scripts**  
Presidio + `en_core_web_lg` is English-centric. A sentence on non-English documents and optional models prevents false expectations.

**“100% offline”**  
EasyOCR/spaCy model **downloads** on first use are still offline after cache. Saying “no network at runtime except optional first-time model download” matches reality and avoids nitpicks.

**Verification**  
You already have manual checks. Adding **golden PDFs** (known strings at known positions) and asserting copy-paste and metadata in automated tests would lock Phase 1 quality.

---

## Minor landscape notes

- **Foxit “AI may need cloud”** is speculative; you could soften to “verify vendor docs before relying on it for offline use.”
- **Presidio and images**  
  The plan uses Presidio on **extracted** text; that’s fine. OCR noise will increase FN/FP—Phase 3 risks should mention **OCR error** as a first-class issue, not only “low-res.”

---

## Verdict

The plan is **coherent, technically grounded, and implementable**. The main improvements are: tighten **licensing language** for distribution, resolve **optional vs default** packaging for OCR, and elevate **span-to-PDF alignment** and **OCR noise** to explicit Phase 3 design items. Addressing those in `PLAN.md` would make execution and external communication (especially around AGPL and accuracy) much safer without changing the overall structure.
