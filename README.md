# MedNexus

Enterprise Medical Document Intelligence Platform

---

## Overview

MedNexus is an enterprise platform that turns medical documents into protected, structured, standardized, and analyzable clinical information. Capabilities are modular and may operate independently while participating in one connected document journey.

The enterprise target journey is:

```text
01 INGEST → 02 UNDERSTAND → 03 PROTECT → 04 EXTRACT
→ 05 STANDARDIZE → 06 ANALYZE → 07 VISUALIZE → 08 INDICATORS
```

This is the target architecture, not a claim that all eight stages are implemented.

The current module is **Medical Document Intelligence – De-identification**, implemented as a purpose-based **Clinical Privacy Policy Engine**, not merely an anonymizer. It uses a hybrid architecture combining:

- AI-based candidate entity detection
- Deterministic identifier detection
- Healthcare-aware role and context validation
- Purpose-based clinical privacy policies
- MedNexus-owned output construction

OpenMed is a candidate detector only. Its detections are treated as suggestions and its `deidentified_text` is non-authoritative. MedNexus owns intelligence decisions, false-positive rejection, purpose-based policy application, and construction of the final de-identified text.

---

## Current De-identification Architecture

```text
Detection
  → Unified Intelligence
  → Purpose-Based Policy Engine
  → MedNexusOutputBuilder
  → MedNexus-owned output
```

Context-rule, deterministic, and OpenMed candidates converge through one canonicalization, role-resolution, context-validation, and detection-merging path. `PolicyTransformer` and `KeepEntityProtector` remain compatibility components outside the authoritative service path.

The MedNexus Intelligence Core currently includes:

- `MedNexusCandidateEntity`
- `EntityCanonicalizer`
- `OpenMedCandidateAdapter`
- `RoleResolver`
- `ContextValidator`
- `DetectionMerger`
- `MedNexusIntelligenceOrchestrator`
- `MedNexusOutputBuilder`

The MedNexus Deterministic Identifier Detector is integrated into the real de-identification service alongside the OpenMed candidate path. MedNexus merges and evaluates detections before producing the final output.

The purpose-based policy model uses `PolicyRule` and `PolicyDefinition` and currently provides four canonical profiles:

- `MEDNEXUS_CLINICAL`
- `MEDNEXUS_RESEARCH`
- `MEDNEXUS_ANALYTICS_PUBLIC_HEALTH`
- `MEDNEXUS_STRICT_PRIVACY`

Text and file APIs select policies through the same resolver. Implemented transformations are `KEEP`, `REPLACE`, `HASH`, `MASK`, and `REMOVE`. `GENERALIZE`, `SHIFT_DATE`, age/age-band derivation, geographic generalization, pseudonymization/tokenization, Privacy–Utility assessment, Residual Re-identification Risk assessment, and the Custom Policy Builder are planned, not implemented.

Purpose-of-use policies are distinct from regulatory frameworks. The future policy model will distinguish direct identifiers, quasi-identifiers, clinical attributes, and contextual or analytical attributes while continuing to use the same unified pipeline.

## Current Document Ingestion

The implemented document-processing path supports:

- TXT ingestion
- DOCX ingestion
- Text-based PDF ingestion
- A unified `DocumentContent` extraction contract
- Extractor registry and factory architecture
- `FileProcessingService`
- The `/api/v1/document/deidentify/file` upload and de-identification endpoint

Extracted text enters the same MedNexus-owned De-identification Intelligence pipeline used for direct text processing. Scanned or image-based PDF OCR and image extraction are not implemented yet.

## Current Product Experience

- `/app` — MedNexus Enterprise Medical Document Intelligence homepage and eight-stage platform vision.
- `/privacy` — functional Clinical Privacy Policy Engine POC.

The current frontend is an accepted working design baseline, not final brand or visual polish. Public Health Intelligence is active parallel domain work aligned to the shared document journey; it is not represented as production-complete.

---

## Project Structure

```text
backend/
frontend/
docs/
requirements/
Validation/
```

---

## Current Status

**Medical Document Intelligence – Clinical Privacy Policy Engine / De-identification Phase 1**

Status: **Functionally complete end-to-end POC, pending final real-document acceptance validation.**

Completed and integrated:

- MedNexus Intelligence Core
- OpenMed candidate adaptation
- Deterministic identifier detection in the real service
- MedNexus-owned final output construction
- TXT, DOCX, and text-based PDF extraction
- Unified document extraction contract and extractor registry/factory
- File-processing service and upload/de-identification API path

Current confirmed regression baseline:

- **671 passing tests**
- **8 warnings**
- **0 failures**

Earlier controlled and synthetic validation provides evidence across samples from:

- Radiology
- Emergency
- Discharge Summary
- Pathology
- Laboratory
- Referral
- Operative Note
- Notification Form
- Death Certificate
- Admission
- ICU

This historical validation is evidence for the current implementation. It does not close Phase 1 or establish clinical/production certification.

The next immediate task is **Clinical Privacy Policy Engine real-document acceptance validation**, followed by regression confirmation and a verified Phase 1 baseline freeze. Known technical debt is tracked in `backend/TECH_DEBT.md`.
