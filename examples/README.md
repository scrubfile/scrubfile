# Example Files for scrubfile

This directory contains synthetic demo files with **fictional PII** for testing [scrubfile](https://github.com/aniketananddeshmukh/redactor).

All personal information in these files is entirely made up and does not correspond to any real person.

## Files

| File | Format | Description |
|------|--------|-------------|
| `sample_employee_record.pdf` | Text PDF | HR employee record (name, SSN, email, address, salary) |
| `sample_medical_form.pdf` | Text PDF | Patient intake form (name, SSN, insurance ID, medications) |
| `sample_contract.docx` | DOCX | Employment contract with compensation and emergency contact table |
| `sample_id_card.jpg` | JPEG image | Simulated corporate ID card (requires OCR for redaction) |
| `sample_scanned_letter.png` | PNG image | Scanned business letter with employment offer details (requires OCR) |

## Regenerating

To regenerate the example files:

```bash
cd examples/
python generate_examples.py
```

### Requirements

- Python 3.9+
- PyMuPDF (`fitz`)
- Pillow (`PIL`)
- python-docx (`docx`)

These are the same dependencies used by scrubfile itself.
