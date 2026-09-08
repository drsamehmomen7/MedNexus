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

The current implemented capabilities are **Clinical Privacy Policy Engine / De-identification** and **Medical Document Understanding & Recognition**, with Radiology as the primary current specialization. Public Health is the second strategic specialization. Phase 1 remains frozen at its accepted POC checkpoint.

The [Multi-Engine Medical Intelligence Strategy v1.1](docs/architecture/MedNexus_Multi_Engine_Medical_Intelligence_Strategy_v1.1.md) is the current accepted strategy and records the current priority, technical-spike checkpoint, hardware transition, UI direction, and roadmap. The accepted [Strategy v1.0 predecessor](docs/architecture/MedNexus_Multi_Engine_Medical_Intelligence_Strategy_v1.0.md) remains the immutable historical M0 checkpoint. External medical AI engines may contribute candidate evidence through a future vendor-neutral Gateway, while MedNexus retains authority, policy, provenance, arbitration, clinical contracts, standardization, and persistent intelligence. The accepted strategy remains subordinate to the frozen UNDERSTAND v1 authority and does not claim runtime implementation.

## UI/UX Design Blueprint v1.0

The M0 architecture/documentation checkpoint is complete at `081e8b178f63850beb18f41a09494452aeacc4fc`. Human review has accepted the [MedNexus UI/UX Design Blueprint v1.0](docs/design/MedNexus_UI_UX_Design_Blueprint_v1.0.md) as the M1 design direction. It establishes a Mona Sans, light/Oak, clinically readable shared product system with Radiology visually primary, Public Health secondary, MEDNEXUS⁷ unchanged, and UNDERSTAND/PROTECT treated as clinical workspaces. No frontend implementation, route/API change, dependency, or font download is part of this checkpoint.

The next active step is a visual Landing Page prototype/mockup for human review before production frontend implementation. The approved later sequence remains `UX foundation → Landing → UNDERSTAND → PROTECT → responsive/accessibility/regression polish`.

## UNDERSTAND v1 Architecture Package

The **FROZEN UNDERSTAND v1 Architecture Authority** consists of [MedNexus UNDERSTAND Domain Matrix v1.0](docs/architecture/MedNexus_UNDERSTAND_Domain_Matrix_v1.0.md), the current [MedNexus Enterprise Architecture & Engineering Blueprint v2.0](docs/architecture/MedNexus_Enterprise_Architecture_and_Engineering_Blueprint_v2.0.docx), [Architecture Crosswalk v2.0](docs/architecture/contracts/MedNexus_Architecture_Crosswalk_v2.0.md), [Clinical Semantic Context Contract v0.2](docs/architecture/contracts/MedNexus_Clinical_Semantic_Context_Contract_v0.2.md), and [Clinical Extraction Contract v0.2](docs/architecture/contracts/MedNexus_Clinical_Extraction_Contract_v0.2.md). Blueprint v1.9 and the v1.1/v0.1 contracts remain preserved architecture history. Architecture authority is not a claim of completed implementation.

- UNDERSTAND is the first stage after upload/paste and evolves toward a bounded typed `MedNexusClinicalContext`: document identity, supported subdomain/modality or `OTHER`, a small amount of reliable routing context, semantic regions/relationships, provenance/confidence, and readiness for PROTECT/EXTRACT. It remains separate from field-level EXTRACT.
- Phase 1 remains the accepted and frozen PROTECT foundation. PROTECT is a policy/governance boundary rather than unconditional destructive redaction before EXTRACT; a Protected Execution Envelope is planned, not implemented.
- EXTRACT produces terminology-independent clinical facts with per-field provenance and confidence. STANDARDIZE owns terminology/code mapping.
- The frozen target catalog is Radiology, Public Health, Laboratory, Admission, Discharge, ICU, and Emergency; Pathology is future. Radiology and Public Health are the full implementation priorities. Native immunization/vaccination documents use `PUBLIC_HEALTH / IMMUNIZATION` in the current product scope. `PUBLIC_HEALTH / LABORATORY_DERIVED_SURVEILLANCE` requires native Public Health surveillance identity plus laboratory-derived context; native Laboratory documents remain Laboratory even when used by Public Health workflows.
- Nuclear Medicine remains one Radiology subdomain with `PLANAR`, `SPECT`, `PET`, `SPECT_CT`, `PET_CT`, and `OTHER` study families. Diagnostic Fluoroscopy is distinct from image-guided intervention, which remains `RADIOLOGY / OTHER` until a future family is approved.
- MedNexus Main/Core and Claude/Claude Code Domain Intelligence develop in parallel. Main/Core owns UNDERSTAND, PROTECT, core contracts/foundations, and shared platform semantics; Domain Intelligence owns downstream domain-specific EXTRACT, STANDARDIZE implementation, ANALYZE, VISUALIZE, and INDICATORS.
- A standing Cross-Track Synchronization Policy requires a concise Cross-Track Sync Brief when shared architecture or contracts change, either track reaches a stable checkpoint, a cross-track dependency or impact appears, or before integration. Routine internal changes with no shared-contract impact do not require a brief.
- The current accepted Radiology UNDERSTAND v1 working baseline is **950 passed, 8 warnings, 0 failures**. The earlier Core Migration baseline remains **872 passed, 8 warnings, 0 failures**, and the previous accepted Core checkpoint remains **780 passed, 8 warnings, 0 failures** at `53a988cafd23e514b31d85e240688a6d0c3b1b31`.

Radiology remains the first rich UNDERSTAND reference domain. Its current compositional reasoning and active offline LOINC/RadLex/DICOM reference foundation preserve the separation between document/domain understanding and future field-level extraction. The latest correction supports strongly composed Radiology reports whose findings narrative lacks an explicit `FINDINGS` heading without introducing report-specific production rules, vocabulary, mappings, or threshold changes.

## Multi-Engine Medical Intelligence Strategy

MedNexus is evolving toward a model-agnostic, multi-engine clinical-intelligence platform under one governing principle: **Models generate evidence. MedNexus determines authority.** The future [MedNexus Medical Intelligence Gateway](docs/architecture/MedNexus_Multi_Engine_Medical_Intelligence_Strategy_v1.1.md) will provide a stable candidate-engine boundary and capability registry; MedNexus-owned Evidence Fusion & Arbitration will remain responsible for eligibility, source authority, conflicts, abstention, confidence, and human-review routing.

Before any external engine receives clinical input, a cross-cutting PROTECT-owned Engine Data-Access Preflight must authorize the exact engine, version, data exposure, execution environment, stage/capability, and local or remote route. This preflight is not completion of Stage 02 PROTECT and does not reorder MEDNEXUS⁷. Local execution alone does not establish compliance.

MedGemma is a planned candidate engine, not MedNexus-owned intelligence. Unified medical understanding-and-generation systems such as MedUAG remain research-watch and future benchmark/adapter candidates pending independent verification of availability, license, commercial rights, reproducibility, runtime, privacy, and MedNexus-specific performance. No external model is authorized to own document identity, privacy decisions, persistent extraction, terminology mapping, analytics, or indicators.

The strategy preserves MEDNEXUS⁷ and the frozen stage boundaries. It proposes future Radiology document and imaging planes, followed by MedNexus-owned evidence arbitration and review-oriented image-report concordance. Public Health compatibility is preserved without starting a Public Health multi-engine implementation. Current accepted working regression baseline before this architecture-only task: **950 passed, 8 warnings, 0 failures**; tests were not re-run and the baseline is unchanged. MedNexus is awaiting responses or approval from external real-world Radiology dataset providers; no provider outcome or date is inferred.

Future engine approval is exact-artifact, adapter, contract, configuration, terms, validation-scope, and use-scope specific. Fusion remains stage-scoped and acyclic; correlated evidence is not independent corroboration, raw engine confidence is distinct from MedNexus-calibrated support, and downstream evidence cannot silently rewrite upstream authority. Future concordance explicitly supports concordant, discordant, unsupported-assertion, possible-omission, and indeterminate review outcomes without automatically rewriting reports or creating clinical facts.

The accepted historical [MedGemma M1.1 technical-spike checkpoint](docs/experiments/MedNexus_MedGemma_Technical_Spike_M1.1.md) is safely paused at the official Hugging Face access/terms gate; this is not an inference failure. “M1.1” is a historical experiment identifier from the prior strategy sequence, not roadmap milestone M1 of accepted Strategy v1.1; controlled MedGemma resumption is roadmap M6. No immutable revision was guessed, no GPU or runtime was measured, no model or dependency was installed locally, no clinical inference occurred, and no PHI or unopened holdout was used. `MG-RAD-CANDIDATE-v0.2` remains an experimental exact-quote, no-model-offset candidate contract with deterministic MedNexus grounding.

The light, clinical UI/UX Blueprint v1.0 is accepted, but no frontend redesign has been implemented. Near-term work now begins with a visual Landing Page prototype/mockup, followed only after review by the approved UX foundation, Landing, Radiology UNDERSTAND, PROTECT, and responsive/accessibility/regression implementation sequence. Hardware migration and controlled MedGemma resumption remain later roadmap work.

### Radiology UNDERSTAND v1 Current Baseline

**Architecture status: FROZEN. Implementation status: EVOLVING UNDER CONTROLLED MILESTONES.** The accepted working baseline is **950 passed, 8 warnings, 0 failures**. One authoritative `RadiologyUnderstandingDecision`, semantic-role and eligibility qualification, cross-domain arbitration, and serialization-only context construction remain core invariants.

The canonical Radiology taxonomy remains `CT`, `MRI`, `X_RAY`, `ULTRASOUND`, `MAMMOGRAPHY`, `NUCLEAR_MEDICINE`, `FLUOROSCOPY`, and `OTHER`. Actual implementation scope is governed by current code and tests; UNDERSTAND remains bounded and does not emit EXTRACT-level clinical facts. The primary unresolved acceptance blocker is a sufficient authorized real-world Radiology dataset. Synthetic coverage supports engineering regression and conformance but cannot establish clinical acceptance or production readiness.

## Local Development Startup

Start MedNexus Main from the repository root using the verified recovered Python 3.10.11 runtime and retained site-packages:

```powershell
cd D:\MedNexus\07_Source_Code
.\start_backend.ps1
```

Open `http://127.0.0.1:8001`. Local development port convention: MedNexus Main uses `127.0.0.1:8001`; the separate MedNexus Public Health workspace reserves `127.0.0.1:8002`.

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

The current deterministic POC still recognizes compatibility-era Radiology, Pathology, Laboratory, Emergency, combined Admission/Discharge, Public Health, and Unknown types. This is implemented behavior, not the approved target catalog. The target catalog separates Admission and Discharge, adds ICU, makes Pathology future, and requires each implemented domain to resolve a supported subdomain or `OTHER`. Radiology and Public Health are the current full implementation priorities.

The result includes domain, type, optional subtype, language, complete non-overlapping major-section ranges, confidence/band, explainable evidence, symbolic routing, metadata, and warnings. `UNKNOWN` and low confidence are intentional safe outcomes. Routing recommends future profiles only; it does not claim that extraction or terminology engines exist.

Phase 2 reuses the existing TXT, DOCX, text-based PDF, `ExtractorFactory`, and `DocumentContent` boundary. It introduces no parser or duplicate content contract and does not depend on Phase 1 privacy internals. Standalone APIs are `POST /api/v1/understanding/analyze-text` and `POST /api/v1/understanding/analyze-file`.

The active POC product page is `/understanding`, supporting pasted text and TXT/DOCX/text-based PDF upload. It renders primary recognition, confidence, sections, evidence, symbolic routing, warnings, and valid UNKNOWN/manual-review outcomes. On `/app`, active capabilities follow the journey order: Document Recognition, Clinical Privacy Policy Engine, Clinical Extraction, then Public Health Intelligence.

The result workspace uses progressive disclosure for a broad audience: a dominant human-readable recognition summary comes first, followed by detected structure, plain-language evidence, and the recommended journey. Raw enums, offsets, evidence weights/matches, and routing identifiers remain available in collapsed technical details. Primary-language detection favors the dominant clinical content rather than short second-script labels or technical footers.

Radiology recognition is backed by an offline MedNexus-owned compositional knowledge and reasoning package. Typed concepts with stable IDs feed an exact-offset `DocumentEvidenceFrame`; semantic roles and explicit eligibility determine which evidence supports current identity, report composition, context only, or no authoritative score. Recommendation, comparison, history, and findings-only secondary context remains preserved for provenance without inflating current-study identity. LOINC Document Ontology, DICOM/Structured Reporting, RSNA RadLex/Playbook/RadReport, SNOMED CT, HL7 CDA/C-CDA, and WHO ICD-10/ICD-11 are reference/provenance families only; they do not supply runtime decisions.

The primary UNDERSTAND output is `MedNexusDocumentContext`, not classification alone. UNDERSTAND is intentionally bounded to document identity, small high-value context, semantic structure/relationships, provenance/confidence, review requirements, and routing. Radiology currently derives document-level modality, study anatomy/examination, contrast, selected technique or view context, and semantic composition without claiming lesion, diagnosis, exact measurement, recommendation-text, or other clinical-fact extraction.

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
- Radiology UNDERSTAND v1 Core Migration — Milestones 1–4 accepted: **872 passed, 8 warnings, 0 failures**; focused Radiology/UNDERSTAND conformance suite: **180 passed, 1 warning**.
- Current accepted working baseline before the Multi-Engine Medical Intelligence architecture task: **950 passed, 8 warnings, 0 failures**. This documentation-only task does not change or re-run that baseline.

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

The immediate roadmap is the Strategy v1.1 UI/UX and hardware-transition sequence, followed by controlled MedGemma resumption and later generic engine, adapter, benchmark, fusion, imaging, concordance, UAG-class, and Radiology analytics milestones. None is authorized by documentation alone. Real-world Radiology acceptance data remains the major unresolved validation requirement. OCR, scanned-document recognition, layout vision, advanced clinical extraction, and broad synthetic classifier tuning remain deliberately deferred. Known technical debt is tracked in `backend/TECH_DEBT.md`.

## Latest Privacy Handoff Correction

The same-document UNDERSTAND → PROTECT handoff now preserves the uploaded source filename and displays a compact receipt/context/status summary before privacy processing. Its lifecycle is READY → PROCESSING → PROTECTED, with stable `#workspace` navigation and an explicit path back to standalone paste/upload. Progressive reveal paints the first intact chunk immediately while respecting production reduced-motion behavior. Verification: focused suite **78 passed, 8 warnings**; full regression **742 passed, 8 warnings, 0 failures**.
## Authoritative Radiology Reference Data

Radiology UNDERSTAND can load active, versioned reference derivatives from `D:\MedNexus\Reference_Data` while remaining fully offline at recognition time. The governed command supports `status`, `import`, `verify`, and `activate`; source-specific instructions are in `backend/app/modules/medical_document_intelligence/understanding/reference_model/README.md`.

Current local population includes checksum-verified official LOINC 2.82, RadLex 4.3, DICOM PS3.6 2026c, and a controlled Radiology-focused DICOM PS3.16/DCMR 2026c subset. The LOINC import contributes 19,230 stored concepts and 71,155 mappings from the Radiology Playbook, Parts, ordered composition, RID/RPID crosswalks, Document Ontology, and Imaging Documents. RadLex contributes 24,092 concepts; DCMR contributes 43 controlled Context Groups, 680 stored concepts, and 1,317 mappings; PS3.6 contributes 41 controlled attributes.

After conservative cross-source reconciliation, the active offline runtime contains **43,811 canonical concepts, 96,528 external mappings, and 88,325 relationships**. LOINC, RadLex, and both DICOM sources are populated, checksum-valid, active, and consumed through the same MedNexus canonical registry. SNOMED remains inactive; SNOMED identifiers carried by DCMR/LOINC remain provenance mappings rather than active terminology concepts. No external distribution is stored in Git, no cross-standard mapping is fabricated, and frozen validation reports are not knowledge sources. Latest verification: focused suite **88 passed, 1 warning**; full regression **775 passed, 8 warnings, 0 failures**.
