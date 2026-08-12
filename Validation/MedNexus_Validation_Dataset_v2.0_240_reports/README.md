# MedNexus Validation Dataset v2.0

This archive contains 240 high-fidelity synthetic medical and public-health reports.
It contains no real patient data and no real PHI.

Purpose:
- File ingestion validation
- Extraction validation
- De-identification validation
- Regression testing
- UI validation
- Performance testing

Languages:
- English
- Arabic
- Mixed Arabic/English

Formats:
- TXT
- DOCX
- Text-based PDF
- Scanned PDF
- PNG images

Clinical and operational domains:
- Radiology
- Laboratory
- Pathology
- Operative Note
- Discharge Summary
- Referral
- Death Certificate
- Emergency
- Admission
- Nursing
- ICU
- Public Health
- Vaccination
- Laboratory Batch
- Notification Form
- Screening Report
- Occupational Health
- School Health
- Maternal Health
- Child Growth

Negative tests include:
- Empty TXT, DOCX, and PDF
- Corrupted PDF and DOCX
- Unsupported JPG and EXE
- Password-protected PDF
- Very large TXT and DOCX stress files

Password for password_protected.pdf:
MedNexus123

Expected PHI values for every case are available in:
07_Manifests/manifest.json

Current checkpoint (12 August 2026): synthetic POC acceptance is complete for the current checkpoint at **681 passed, 8 warnings, 0 failures**. Real medical-document acceptance is deferred to future validation. This evidence does not establish production readiness, exhaustive privacy coverage, or clinical certification.
