# Security Audit Results

**Date:** 2026-03-29
**Codebase:** /Users/aniketananddeshmukh/projects/redactor
**Stack:** Python 3.10+, Typer (CLI), PyMuPDF (PDF), Rich (output formatting)

## Scorecard

| # | Check | Verdict | Detail |
|---|-------|---------|--------|
| 1 | Rate limiting | N/A | Local CLI tool, no HTTP server |
| 2 | Token storage | N/A | No authentication or credentials |
| 3 | Input sanitization | PASS | Literal search strings, no shell/eval/exec, validated paths |
| 4 | Hardcoded API keys | PASS | No secrets found, .gitignore covers standard patterns |
| 5 | Webhook verification | N/A | No webhooks |
| 6 | Database indexing | N/A | No database |
| 7 | Error boundaries | PASS | Exceptions caught with meaningful exit codes (0/1/2) |
| 8 | Session expiry | N/A | No sessions |
| 9 | Pagination | N/A | No database queries |
| 10 | Password reset expiry | N/A | No auth flows |
| 11 | Env var validation | PASS | No env vars used; all config via CLI args |
| 12 | Image/file uploads | PARTIAL | Input validated (type/size/existence); output permissions world-readable |
| 13 | CORS policy | N/A | No web server |
| 14 | Async email | N/A | No email |
| 15 | Connection pooling | N/A | No database |
| 16 | Admin RBAC | N/A | No admin routes |
| 17 | Health check | N/A | No HTTP endpoints |
| 18 | Production logging | PARTIAL | Console-only output; no structured logging; tracebacks discarded |
| 19 | Backup strategy | N/A | Stateless CLI |
| 20 | TypeScript/type safety | PARTIAL | Good type annotations on all functions; no mypy/pyright enforced |

## Summary: 4 PASS, 3 PARTIAL, 0 FAIL, 13 N/A

Plus 2 CLI-specific critical issues below.

## Critical Issues

### CRITICAL-1: PII terms echoed in output

**Files:**
- `src/redactor/cli.py:122-130` (JSON output includes `terms_found` dict with raw PII)
- `src/redactor/cli.py:138-139` (Rich table prints each PII term and its count)

**Problem:** The tool's output contains the exact PII strings the user wanted to redact. These appear in:
- Terminal scrollback
- Shell history if piped/redirected
- CI/CD logs
- Any log aggregation system

This directly undermines the tool's privacy mission.

**Fix:** Replace raw PII terms with masked versions in output. User already knows what they supplied; the tool should confirm counts, not echo the sensitive data back.

### CRITICAL-2: Output file permissions are world-readable

**File:** `src/redactor/pdf.py:63`

**Problem:** `doc.save()` creates files with default umask (typically 0o644 = rw-r--r--). On shared systems, any local user can read the redacted document.

**Fix:** `os.chmod(output_path, 0o600)` after save to restrict to owner-only.

## Warnings (PARTIAL)

### PARTIAL: Terms file accepts symlinks
**File:** `src/redactor/utils.py:61-76`

`load_terms_from_file()` resolves the path but doesn't check for symlinks (unlike output path handling). A symlink could point to any readable file. Low risk since the user controls their own inputs.

### PARTIAL: Metadata scrubbing completeness
**File:** `src/redactor/pdf.py:59-60`

`set_metadata({})` + `scrub()` clears standard metadata (author, title, creator — verified by tests). May not fully clear: XMP extended properties, embedded files/attachments, form field data. Adequate for Phase 1; document limitations.

### PARTIAL: No structured logging
**File:** `src/redactor/cli.py:104-106`

Broad `except Exception as e` converts to string and discards traceback. No Python `logging` module usage. Acceptable for Phase 1 CLI but should be improved before production use.

### PARTIAL: Unused `Any` import
**File:** `src/redactor/__init__.py:6`

`from typing import Any` imported but never used. Cosmetic issue only.

## Recommendations

### HIGH — Fix before release
1. **Mask PII in output** — Replace raw terms with `[REDACTED-1]`, `[REDACTED-2]` etc. in both table and JSON output
2. **Restrict output file permissions** — `os.chmod(output_path, 0o600)` after save
3. **Add symlink check to terms file loader** — Match the output path validation pattern

### MEDIUM — Should fix
4. **Add mypy to dev dependencies** — Enforce type safety in CI
5. **Add structured logging** — Python `logging` module with optional `--log-level` flag
6. **Remove unused `Any` import** from `__init__.py`
7. **Document metadata scrubbing limitations** — What `scrub()` does and doesn't remove

### LOW — Nice to have
8. **Terms file line limit** — Cap at 10,000 terms to prevent memory exhaustion
9. **PDF magic byte validation** — Check file header before `fitz.open()` (defense in depth)
10. **Add `.env` to .gitignore** — Preemptive for Phase 2+ if env vars are added
