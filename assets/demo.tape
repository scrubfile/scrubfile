Output assets/demo.gif

Set Shell "bash"
Set FontSize 16
Set Width 900
Set Height 500
Set Padding 20
Set Theme "Dracula"

Type "# Scrub PII from a PDF with explicit terms"
Enter
Sleep 500ms

Type "scrubfile examples/sample_employee_record.pdf -r 'Arjun Vikram Sharma' -r '287-65-4321'"
Enter
Sleep 3s

Type ""
Enter
Sleep 500ms

Type "# Auto-detect all PII"
Enter
Sleep 500ms

Type "scrubfile examples/sample_medical_form.pdf --auto"
Enter
Sleep 8s

Type ""
Enter
Sleep 500ms

Type "# JSON output for automation"
Enter
Sleep 500ms

Type "scrubfile examples/sample_employee_record.pdf -r 'Arjun Vikram Sharma' --json"
Enter
Sleep 3s

Sleep 2s
