# MedNexus

Enterprise Medical Document Intelligence Platform

---

## Overview

MedNexus is an enterprise platform that turns medical documents into protected, structured, standardized, and analyzable clinical information. Capabilities are modular and may operate independently while participating in one connected document journey.

The public MEDNEXUS⁷ product journey is:

```text
01 UNDERSTAND → 02 PROTECT → 03 EXTRACT → 04 STANDARDIZE
→ 05 ANALYZE → 06 VISUALIZE → 07 INDICATORS
```

This is the target product architecture, not a claim that all seven stages are implemented. INGEST remains an internal technical operation inside UNDERSTAND, covering file/text intake, extraction/parsing, and `DocumentContent` construction.

Public signature: **MEDNEXUS⁷ — One document. Seven intelligent transformations.** This is a visual/product brand signature. Internal code identifiers, packages, classes, APIs, routes, repositories, and runtime contracts remain `MedNexus`; `MedNexus7` is only a textual fallback where superscript typography is unavailable.

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

Phase 2 status: **ACCEPTED DOCUMENT CONTEXT & JOURNEY FOUNDATION CHECKPOINT** at commit `fa1a8ba68d66a3d40f40c8af3bf644f3b909191a`. Previous checkpoints are `a1e8ff2` (foundation) and `551be07` (documentation synchronization). The standalone implemented flow is:

```text
Source File / Text
  → Existing ExtractorFactory and DocumentContent
  → Language Detection
  → Structural Section Detection
  → Evidence-Based Document Classification
  → Confidence and Decision Evidence
  → Symbolic Downstream Routing
```

The deterministic, explainable POC recognizes Radiology, Pathology, Laboratory, Emergency, Admission/Discharge, Public Health, and Unknown. Supported types are `RADIOLOGY_REPORT`, `PATHOLOGY_REPORT`, `LABORATORY_REPORT`, `EMERGENCY_REPORT`, `ADMISSION_NOTE`, `DISCHARGE_SUMMARY`, `PUBLIC_HEALTH_DOCUMENT`, and `UNKNOWN`. Radiology may resolve `X_RAY`, `CT`, `MRI`, `ULTRASOUND`, `DOPPLER`, `MAMMOGRAPHY`, or `NUCLEAR_MEDICINE` when evidence is adequate. Language results are `ENGLISH`, `ARABIC`, `MIXED`, or `UNKNOWN`.

The result includes domain, type, optional subtype, language, complete non-overlapping major-section ranges, confidence/band, explainable evidence, symbolic routing, metadata, and warnings. `UNKNOWN` and low confidence are intentional safe outcomes. Routing recommends future profiles only; it does not claim that extraction or terminology engines exist.

Phase 2 reuses the existing TXT, DOCX, text-based PDF, `ExtractorFactory`, and `DocumentContent` boundary. It introduces no parser or duplicate content contract and does not depend on Phase 1 privacy internals. Standalone APIs are `POST /api/v1/understanding/analyze-text` and `POST /api/v1/understanding/analyze-file`.

The active POC product page is `/understanding`, supporting pasted text and TXT/DOCX/text-based PDF upload. It renders primary recognition, confidence, sections, evidence, symbolic routing, warnings, and valid UNKNOWN/manual-review outcomes. On `/app`, active capabilities follow the journey order: Document Recognition, Clinical Privacy Policy Engine, Clinical Extraction, then Public Health Intelligence.

The result workspace uses progressive disclosure for a broad audience: a dominant human-readable recognition summary comes first, followed by detected structure, plain-language evidence, and the recommended journey. Raw enums, offsets, evidence weights/matches, and routing identifiers remain available in collapsed technical details. Primary-language detection favors the dominant clinical content rather than short second-script labels or technical footers.

Radiology recognition is backed by an offline MedNexus-owned compositional knowledge and reasoning package. Typed concepts with stable IDs feed an exact-offset `DocumentEvidenceFrame`; MedNexus evaluates evidence-family diversity, imaging coherence, structure, incidental-mention risk, and conflicting document signatures before making separate domain and report-type decisions. LOINC Document Ontology, DICOM/Structured Reporting, RSNA RadLex/Playbook/RadReport, SNOMED CT, HL7 CDA/C-CDA, and WHO ICD-10/ICD-11 are reference/provenance families only; they do not supply runtime decisions.

The primary UNDERSTAND output is `MedNexusDocumentContext`, not classification alone. Radiology v2 derives modality, composed examination, one or more broad body regions, contrast context, imaging-technique families, broad clinical purpose, structure, and radiologist/authentication context without claiming lesion, disease, measurement, or staging extraction.

The Reference Model Foundation separates authoritative source governance from runtime intelligence. A machine-readable manifest records official version, license/distribution policy, acquisition location, verification date, checksum where published, and enabled state for LOINC/RSNA, DICOM, RadLex, SNOMED CT, and the local MedNexus derivative. Stable MedNexus concept IDs normalize cross-standard mappings and relationships; the application consumes only the deterministic offline canonical model. External standards are reference inputs, not runtime decision engines, and validation reports are never knowledge sources.

For the POC journey, a bounded in-memory session retains the original `DocumentContent` together with its context. The `/understanding` workspace can continue the same document to `/privacy`, which calls the existing privacy service with the retained source and selected policy. This is deliberately process-local and non-durable; production session persistence remains future infrastructure.

The frontend includes a reusable Progressive Result Reveal convention for substantial results. The backend first returns the complete authoritative output; the browser then presents protected text through intact lines or small line groups, with Show Full Result and reduced-motion fallback. The original document and privacy report appear immediately, and copy operations always use the complete authoritative protected output. This is not backend token streaming.

## Current Product Experience

- `/app` — MEDNEXUS⁷ Enterprise Medical Document Intelligence homepage and seven-transformation product journey.
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

**Medical Document Intelligence — Phase 1 frozen; Phase 2 Document Context & Journey Foundation accepted**

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
- Phase 2 frontend integration: **718 passed, 8 warnings, 0 failures**; focused Understanding/API/frontend suite: **37 passed**.
- Arabic Radiology and Recognition UX hardening: **725 passed, 8 warnings, 0 failures**; focused suite: **44 passed**. `MNX-01-03_Radiology_Arabic.txt` resolves as Radiology / Radiology Report / CT / Arabic with HIGH confidence.
- Recognition Knowledge Layer v1 and simplified result UX: **731 passed, 8 warnings, 0 failures**; focused suite: **50 passed**.
- MedNexus Document Context foundation and same-document journey: **737 passed, 8 warnings, 0 failures**; focused suite: **64 passed**.
- Phase 2 UI polish and Progressive Result Reveal: **739 passed, 8 warnings, 0 failures**; focused suite: **75 passed**.
- Phase 2 Document Context & Journey Foundation accepted checkpoint: **742 passed, 8 warnings, 0 failures** at `fa1a8ba68d66a3d40f40c8af3bf644f3b909191a`.
- MEDNEXUS⁷ seven-transformation UI/product-architecture update: **743 passed, 8 warnings, 0 failures**; focused homepage suite: **48 passed, 1 warning**.
- Radiology Intelligence Architecture v2 (uncommitted review state): **758 passed, 8 warnings, 0 failures**; focused Radiology/Understanding suite: **77 passed, 1 warning**. Validation Failure R-001 resolves compositionally as MRI Abdomen & Pelvis with pre/post contrast, Oncologic Staging, MRI technique context, and HIGH confidence.
- Reference Model Foundation v1 (uncommitted review state): **764 passed, 8 warnings, 0 failures**; focused reference/Radiology/Understanding suite: **83 passed, 1 warning**.

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

After architectural review, the next intended activity is an **unseen Radiology validation round**, followed by broader Phase 2 Recognition Validation. OCR, scanned-document recognition, layout vision, tables, ML/transformer/LLM classification, external classifiers, embeddings, advanced clinical extraction, FHIR/HL7, dashboard integration, and broad synthetic classifier tuning remain deliberately deferred. Known technical debt is tracked in `backend/TECH_DEBT.md`.

## Latest Privacy Handoff Correction

The same-document UNDERSTAND → PROTECT handoff now preserves the uploaded source filename and displays a compact receipt/context/status summary before privacy processing. Its lifecycle is READY → PROCESSING → PROTECTED, with stable `#workspace` navigation and an explicit path back to standalone paste/upload. Progressive reveal paints the first intact chunk immediately while respecting production reduced-motion behavior. Verification: focused suite **78 passed, 8 warnings**; full regression **742 passed, 8 warnings, 0 failures**.
## Authoritative Radiology Reference Data

Radiology UNDERSTAND can load active, versioned reference derivatives from `D:\MedNexus\Reference_Data` while remaining fully offline at recognition time. The governed command supports `status`, `import`, `verify`, and `activate`; source-specific instructions are in `backend/app/modules/medical_document_intelligence/understanding/reference_model/README.md`.

Current local population includes checksum-verified official LOINC 2.82, RadLex 4.3, DICOM PS3.6 2026c, and a controlled Radiology-focused DICOM PS3.16/DCMR 2026c subset. The LOINC import contributes 19,230 stored concepts and 71,155 mappings from the Radiology Playbook, Parts, ordered composition, RID/RPID crosswalks, Document Ontology, and Imaging Documents. RadLex contributes 24,092 concepts; DCMR contributes 43 controlled Context Groups, 680 stored concepts, and 1,317 mappings; PS3.6 contributes 41 controlled attributes.

After conservative cross-source reconciliation, the active offline runtime contains **43,811 canonical concepts, 96,528 external mappings, and 88,325 relationships**. LOINC, RadLex, and both DICOM sources are populated, checksum-valid, active, and consumed through the same MedNexus canonical registry. SNOMED remains inactive; SNOMED identifiers carried by DCMR/LOINC remain provenance mappings rather than active terminology concepts. No external distribution is stored in Git, no cross-standard mapping is fabricated, and frozen validation reports are not knowledge sources. Latest verification: focused suite **88 passed, 1 warning**; full regression **775 passed, 8 warnings, 0 failures**.
