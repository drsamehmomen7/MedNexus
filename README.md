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

The current implemented capabilities are **Clinical Privacy Policy Engine / De-identification** and the accepted foundation of **Medical Document Understanding & Recognition**. Phase 2 implements the MedNexus-owned UNDERSTAND stage after existing ingestion; Phase 1 remains frozen at its accepted POC checkpoint.

The Clinical Privacy Policy Engine combines:

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

## Medical Document Understanding & Recognition

Phase 2 Foundation status: **FOUNDATION CHECKPOINT ACCEPTED** at commit `a1e8ff2`, with **714 passed, 8 warnings, 0 failures**. The standalone implemented flow is:

```text
Source File / Text
  → Existing ExtractorFactory and DocumentContent
  → Language Detection
  → Structural Section Detection
  → Evidence-Based Document Classification
  → Confidence and Decision Evidence
  → Symbolic Downstream Routing
```

The deterministic, explainable POC recognizes Radiology, Pathology, Laboratory, Emergency, Admission/Discharge, Public Health, and Unknown. Supported types are `RADIOLOGY_REPORT`, `PATHOLOGY_REPORT`, `LABORATORY_REPORT`, `EMERGENCY_REPORT`, `ADMISSION_NOTE`, `DISCHARGE_SUMMARY`, `PUBLIC_HEALTH_DOCUMENT`, and `UNKNOWN`. Radiology may resolve `X_RAY`, `CT`, `MRI`, `ULTRASOUND`, `MAMMOGRAPHY`, or `NUCLEAR_MEDICINE` when evidence is adequate. Language results are `ENGLISH`, `ARABIC`, `MIXED`, or `UNKNOWN`.

The result includes domain, type, optional subtype, language, complete non-overlapping major-section ranges, confidence/band, explainable evidence, symbolic routing, metadata, and warnings. `UNKNOWN` and low confidence are intentional safe outcomes. Routing recommends future profiles only; it does not claim that extraction or terminology engines exist.

Phase 2 reuses the existing TXT, DOCX, text-based PDF, `ExtractorFactory`, and `DocumentContent` boundary. It introduces no parser or duplicate content contract and does not depend on Phase 1 privacy internals. Standalone APIs are `POST /api/v1/understanding/analyze-text` and `POST /api/v1/understanding/analyze-file`.

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

**Medical Document Intelligence — Phase 1 frozen; Phase 2 Foundation accepted**

Status: **Phase 1 — Accepted POC Checkpoint / Paused.** The synthetic acceptance baseline is frozen; this is not production certification or exhaustive clinical validation.

Completed and integrated:

- MedNexus Intelligence Core
- OpenMed candidate adaptation
- Deterministic identifier detection in the real service
- MedNexus-owned final output construction
- TXT, DOCX, and text-based PDF extraction
- Unified document extraction contract and extractor registry/factory
- File-processing service and upload/de-identification API path

Accepted checkpoint baselines:

- Phase 1 frozen: **681 passed, 8 warnings, 0 failures** at `3486c206085652e2edac2574d277ff0970e037e2`.
- Phase 2 initial foundation: **705 passed, 8 warnings, 0 failures**.
- Phase 2 hardened checkpoint: **714 passed, 8 warnings, 0 failures** at `a1e8ff2`; focused Phase 2 suite: **33 passed**.

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

The current synthetic POC acceptance checkpoint is complete. Broader real medical-document validation is intentionally deferred and is expected to reveal additional cases. This checkpoint does not establish clinical or production certification.

The next intended milestone is **Phase 2 Recognition Validation — Round 1**, using a small representative set across supported domains plus ambiguous/UNKNOWN cases. OCR, scanned-document recognition, layout vision, tables, ML/transformer/LLM classification, external classifiers, embeddings, advanced clinical extraction, FHIR/HL7, frontend integration, dashboards, and broad synthetic classifier tuning remain deliberately deferred. Known technical debt is tracked in `backend/TECH_DEBT.md`.
