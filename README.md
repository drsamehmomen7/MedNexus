# MRJ

Medical Report Journey

Enterprise Medical Document Intelligence Platform

---

## Public identity — 13 September 2026

MRJ is the approved public identity of the continuing MedNexus project. MRJ means **Medical Report Journey**. The MedNexus-named frozen Blueprint v2.0, UNDERSTAND Domain Matrix v1.0, Crosswalk v2.0, Semantic Context Contract v0.2, and Extraction Contract v0.2 remain the governing technical authority for MRJ. Their files, versions, technical identifiers, and historical names are not renamed by this public-identity migration.

**The medical report is the hero of the platform.** The product narrative is **REPORT | PATHWAY | OUTCOME**.

Approved language:

- Every Medical Report Has a Journey.
- From Medical Report to Measurable Indicator.
- From Document to Decision.
- Understand it. Protect it. Structure it. Analyze it. Measure what matters.
- REPORT | PATHWAY | OUTCOME

The approved icon is installed unchanged from the owner-supplied MRJ pack. The public wordmark is native text: MRJ / Medical Report Journey. Public identity is migrated on `/app`, `/understanding`, and `/privacy`. Legacy branded raster artwork remains unreferenced; the accepted `/app` domain visuals are brand-neutral native SVG illustrations.

## Overview

MRJ is an enterprise platform that turns medical documents into protected, structured, standardized, and analyzable clinical information. Capabilities are modular and may operate independently while participating in one connected document journey.

The public MRJ journey is:

```text
01 UNDERSTAND → 02 PROTECT → 03 EXTRACT → 04 STANDARDIZE
→ 05 ANALYZE → 06 VISUALIZE → 07 INDICATORS
```

This is the target product architecture, not a claim that all seven stages are implemented. INGEST remains an internal technical operation inside UNDERSTAND, covering file/text intake, extraction/parsing, and `DocumentContent` construction.

Public identity: **MRJ — Medical Report Journey**. The former MEDNEXUS⁷ signature is historical. The seven-stage architecture is unchanged; internal code, policy IDs, APIs, schemas, provenance values, filenames, and `D:\MedNexus` paths retain their existing names.

The current implemented capabilities are **Clinical Privacy Policy Engine / De-identification** and **Medical Document Understanding & Recognition**, with Radiology as the primary current specialization. Public Health is the second strategic specialization. Phase 1 remains frozen at its accepted POC checkpoint.

The [Multi-Engine Medical Intelligence Strategy v1.1](docs/architecture/MedNexus_Multi_Engine_Medical_Intelligence_Strategy_v1.1.md) is the current accepted strategy and records the current priority, technical-spike checkpoint, hardware transition, UI direction, and roadmap. The accepted [Strategy v1.0 predecessor](docs/architecture/MedNexus_Multi_Engine_Medical_Intelligence_Strategy_v1.0.md) remains the immutable historical M0 checkpoint. External medical AI engines may contribute candidate evidence through a future vendor-neutral Gateway, while MRJ retains authority, policy, provenance, arbitration, clinical contracts, standardization, and persistent intelligence. The accepted strategy remains subordinate to the frozen UNDERSTAND v1 authority and does not claim runtime implementation.

## Accepted Radiology Horizontal Clinical Journey R0

Human architecture review formally accepted and closed the Radiology-only R0 architecture checkpoint on **2026-09-17**. It governs the next development direction: complete the first clinically meaningful horizontal journey across `UNDERSTAND → PROTECT → EXTRACT → STANDARDIZE → ANALYZE → VISUALIZE → INDICATORS` before deeper fine-tuning of an individual stage. INGEST remains internal to UNDERSTAND. The package defines domain-specific extraction, the Radiology Intelligence Pack, seven-stage handoff contracts, a versioned Report Collection boundary, scientific/indicator governance, shared journey state, and one continuous clinical-workspace UX.

The five accepted documents are [Horizontal Clinical Journey Architecture](docs/architecture/MRJ_Horizontal_Clinical_Journey_Architecture_v1.0.md), [Domain Clinical Extraction Architecture](docs/architecture/MRJ_Domain_Clinical_Extraction_Architecture_v1.0.md), [Radiology Intelligence Pack](docs/domain/radiology/MRJ_Radiology_Intelligence_Pack_v1.0.md), [Clinical Journey UX Architecture](docs/design/MRJ_Clinical_Journey_UX_Architecture_v1.0.md), and [Seven-Stage Contracts](docs/contracts/MRJ_Seven_Stage_Contracts_v1.0.md). Their status is **ACCEPTED — R0 RADIOLOGY HORIZONTAL ARCHITECTURE CHECKPOINT**. UNDERSTAND Single + Batch is accepted. **R1 — PROTECT Journey Integration was ACCEPTED AND CLOSED on 2026-09-22.** Radiology remains the active implementation track, Public Health is unchanged, and MedGemma remains future-compatible but was not required for R1. The frozen UNDERSTAND v1 authority and accepted privacy engine remain unchanged. The current verified full regression is **999 passed, 8 warnings, 0 failures**.

## R1 — PROTECT Journey Integration

Single and Batch reports now continue from UNDERSTAND to PROTECT inside the same bounded, process-local `JourneyRun`. Every report retains independent PROTECT status, history, error and result ownership; eligible Batch reports are processed sequentially with failure isolation and the existing maximum of 10. The integration delegates to the accepted `DeidentificationService` and unified intelligence/policy/output path—no PHI detector, OpenMed authority, policy rule, merger, output builder or standalone `/privacy` behavior was replaced.

R1 establishes the `ProtectedDocument`, `PatientAnalyticContext`, `ProtectionResult`, and `ProtectionProvenance` handoff foundation. For PDF-origin reports, the authoritative protected text is deterministically rebuilt into a new per-report protected PDF; the original PDF remains unchanged and both artifacts stay only in bounded process memory. Artifact responses are non-cacheable, metadata—not document bytes—travels in Journey JSON, and Batch failures remain isolated. `/understanding` keeps the same report-centric shell and navigator while making the protected PDF the primary view, retaining protected text as a secondary utility, and exposing original-PDF comparison only after explicit activation. Status, concise protection summary, human-readable review notice, analytical context, and real Journey Rail state remain visible without normal-workflow engine diagnostics.

PROTECT eligibility is stage-specific: a readable, privacy-processable `UNKNOWN` or `OTHER` report may proceed while UNDERSTAND remains `NEEDS_REVIEW`; this does not imply EXTRACT readiness. The protection-completeness guard blocks downstream-safe artifact exposure when known high-risk PHI remains unprotected. Human acceptance covered 20 reports: 20 UNDERSTAND terminal, 20 PROTECT attempted, 20 independent protected PDFs, zero known Patient Name/Patient ID/Visit ID misses, zero wrong clinical transformations, and preserved clinical content. All 20 remained `NEEDS_REVIEW`; that accepted review burden, ambiguous narrative person signals, the current Patient ID compatibility representation, empty `PatientAnalyticContext`, absent age-band/date-shift/pseudonymous-subject derivations, and absent OCR-specific privacy validation remain future work rather than R1 blockers. R1 is **ACCEPTED AND CLOSED**.

## R2.0A — Radiology Clinical Fact and EXTRACT UX Specification

R2.0A is **ACCEPTED AND CLOSED** as of **2026-09-24**. Its authoritative specification package consists of the terminology-independent [Radiology Clinical Fact Contract v1.0](docs/contracts/MRJ_Radiology_Clinical_Fact_Contract_v1.0.md), the continuous-workspace [Radiology EXTRACT UX Contract v1.0](docs/design/MRJ_Radiology_EXTRACT_UX_Contract_v1.0.md), and the engine-neutral [R2.0 Radiology Extraction Evaluation Plan v1.0](docs/evaluation/MRJ_R2_0_Radiology_Extraction_Evaluation_Plan_v1.0.md). The package defines `RadiologyFinding` V0, a bounded four-value semantic class, assertion/negation, anatomy, laterality, finding-owned measurements, a bounded explicit-source relationship set, structured `ClinicalContextFact`, `CommonClinicalContext`, evidence/provenance, report-linked UX, future 20–30-report ground truth, and benchmark criteria.

This is architecture and specification only. R2 EXTRACT has not started; no runtime, frontend behavior, API, dependency, model, dataset, ground truth, evaluation harness, benchmark, engine selection, STANDARDIZE, or analytics capability is implemented. The next checkpoint is **R2.0B — Radiology Ground Truth Dataset**, followed by R2.0C Evaluation Harness, R2.0D Benchmark, R2.0E Engine Decision, and R2 Radiology Clinical EXTRACT V0.

## UI/UX Design Blueprint v1.0

The M0 architecture/documentation checkpoint is complete at `081e8b178f63850beb18f41a09494452aeacc4fc`. Human review accepted the [MedNexus UI/UX Design Blueprint v1.0](docs/design/MedNexus_UI_UX_Design_Blueprint_v1.0.md) as the M1 design direction. That documentation-only checkpoint established Mona Sans, light/Oak reference tokens, Radiology-first hierarchy, Public Health secondary, the seven stages and clinical workspaces. The 13 September MRJ decision supersedes its public brand identity; it does not retroactively claim that the earlier checkpoint implemented UI changes.

The Landing implementation stage is now complete as **MRJ Website Experience / Cinematic Hero V1**. Later UNDERSTAND, PROTECT, and responsive/accessibility refinements remain separately authorized work; the immediate product focus returns to core MRJ clinical validation.

### MRJ Website Experience / Cinematic Hero V1 — Closed

`/app` uses `frontend/assets/video/mrj-kling-cinematic.mp4` as its primary warm-ivory cinematic Hero renderer. The complete native SVG/Web-Animations Hero remains available as the renderer fallback and rollback path. Reduced-motion users receive the static native final scene; video load/autoplay failure activates the native renderer; without JavaScript, the static native composition remains visible. The video plays muted and inline once, pauses while offscreen, and holds its final frame.

The final navigation order is **How MRJ Works → Radiology → Public Health → Privacy & Governance**. The landing sequence is **Hero → MRJ Journey → Radiology/Public Health → Multi-Engine Intelligence → Governance → value/closing sections**. The Journey retains all seven stages and is the single enlarged Hero CTA destination. Radiology and Public Health use local brand-neutral SVG domain illustrations. Desktop top whitespace was removed at the container-geometry source, and copy/video scale now uses the first viewport deliberately without changing backend, route, API, clinical, `/understanding`, or `/privacy` behavior. No frontend dependency was added. Fresh closure regression: **950 passed, 8 warnings, 0 failures**.

## UNDERSTAND v1 Architecture Package

The **FROZEN UNDERSTAND v1 Architecture Authority** consists of [MedNexus UNDERSTAND Domain Matrix v1.0](docs/architecture/MedNexus_UNDERSTAND_Domain_Matrix_v1.0.md), the current [MedNexus Enterprise Architecture & Engineering Blueprint v2.0](docs/architecture/MedNexus_Enterprise_Architecture_and_Engineering_Blueprint_v2.0.docx), [Architecture Crosswalk v2.0](docs/architecture/contracts/MedNexus_Architecture_Crosswalk_v2.0.md), [Clinical Semantic Context Contract v0.2](docs/architecture/contracts/MedNexus_Clinical_Semantic_Context_Contract_v0.2.md), and [Clinical Extraction Contract v0.2](docs/architecture/contracts/MedNexus_Clinical_Extraction_Contract_v0.2.md). Blueprint v1.9 and the v1.1/v0.1 contracts remain preserved architecture history. Architecture authority is not a claim of completed implementation.

- UNDERSTAND is the first stage after upload/paste and evolves toward a bounded typed `MedNexusClinicalContext`: document identity, supported subdomain/modality or `OTHER`, a small amount of reliable routing context, semantic regions/relationships, provenance/confidence, and readiness for PROTECT/EXTRACT. It remains separate from field-level EXTRACT.
- Phase 1 remains the accepted and frozen PROTECT foundation. PROTECT is a policy/governance boundary rather than unconditional destructive redaction before EXTRACT; a Protected Execution Envelope is planned, not implemented.
- EXTRACT produces terminology-independent clinical facts with per-field provenance and confidence. STANDARDIZE owns terminology/code mapping.
- The frozen target catalog is Radiology, Public Health, Laboratory, Admission, Discharge, ICU, and Emergency; Pathology is future. Radiology and Public Health are the full implementation priorities. Native immunization/vaccination documents use `PUBLIC_HEALTH / IMMUNIZATION` in the current product scope. `PUBLIC_HEALTH / LABORATORY_DERIVED_SURVEILLANCE` requires native Public Health surveillance identity plus laboratory-derived context; native Laboratory documents remain Laboratory even when used by Public Health workflows.
- Nuclear Medicine remains one Radiology subdomain with `PLANAR`, `SPECT`, `PET`, `SPECT_CT`, `PET_CT`, and `OTHER` study families. Diagnostic Fluoroscopy is distinct from image-guided intervention, which remains `RADIOLOGY / OTHER` until a future family is approved.
- MRJ Main/Core and Claude/Claude Code Domain Intelligence develop in parallel. Main/Core owns UNDERSTAND, PROTECT, core contracts/foundations, and shared platform semantics; Domain Intelligence owns downstream domain-specific EXTRACT, STANDARDIZE implementation, ANALYZE, VISUALIZE, and INDICATORS.
- A standing Cross-Track Synchronization Policy requires a concise Cross-Track Sync Brief when shared architecture or contracts change, either track reaches a stable checkpoint, a cross-track dependency or impact appears, or before integration. Routine internal changes with no shared-contract impact do not require a brief.
- The current accepted Radiology UNDERSTAND v1 working baseline is **950 passed, 8 warnings, 0 failures**. The earlier Core Migration baseline remains **872 passed, 8 warnings, 0 failures**, and the previous accepted Core checkpoint remains **780 passed, 8 warnings, 0 failures** at `53a988cafd23e514b31d85e240688a6d0c3b1b31`.

Radiology remains the first rich UNDERSTAND reference domain. Its current compositional reasoning and active offline LOINC/RadLex/DICOM reference foundation preserve the separation between document/domain understanding and future field-level extraction. The latest correction supports strongly composed Radiology reports whose findings narrative lacks an explicit `FINDINGS` heading without introducing report-specific production rules, vocabulary, mappings, or threshold changes.

## Multi-Engine Medical Intelligence Strategy

MRJ is evolving toward a model-agnostic, multi-engine clinical-intelligence platform under one governing principle: **Models generate evidence. MRJ determines authority.** The future [MedNexus Medical Intelligence Gateway](docs/architecture/MedNexus_Multi_Engine_Medical_Intelligence_Strategy_v1.1.md) will provide a stable candidate-engine boundary and capability registry; MRJ-owned Evidence Fusion & Arbitration will remain responsible for eligibility, source authority, conflicts, abstention, confidence, and human-review routing.

Before any external engine receives clinical input, a cross-cutting PROTECT-owned Engine Data-Access Preflight must authorize the exact engine, version, data exposure, execution environment, stage/capability, and local or remote route. This preflight is not completion of Stage 02 PROTECT and does not reorder MRJ seven-stage journey. Local execution alone does not establish compliance.

MedGemma is a planned candidate engine, not MRJ-owned intelligence. Unified medical understanding-and-generation systems such as MedUAG remain research-watch and future benchmark/adapter candidates pending independent verification of availability, license, commercial rights, reproducibility, runtime, privacy, and MRJ-specific performance. No external model is authorized to own document identity, privacy decisions, persistent extraction, terminology mapping, analytics, or indicators.

The strategy preserves MRJ seven-stage journey and the frozen stage boundaries. It proposes future Radiology document and imaging planes, followed by MRJ-owned evidence arbitration and review-oriented image-report concordance. Public Health compatibility is preserved without starting a Public Health multi-engine implementation. Current accepted working regression baseline before this architecture-only task: **950 passed, 8 warnings, 0 failures**; tests were not re-run and the baseline is unchanged. MRJ is awaiting responses or approval from external real-world Radiology dataset providers; no provider outcome or date is inferred.

Future engine approval is exact-artifact, adapter, contract, configuration, terms, validation-scope, and use-scope specific. Fusion remains stage-scoped and acyclic; correlated evidence is not independent corroboration, raw engine confidence is distinct from MRJ-calibrated support, and downstream evidence cannot silently rewrite upstream authority. Future concordance explicitly supports concordant, discordant, unsupported-assertion, possible-omission, and indeterminate review outcomes without automatically rewriting reports or creating clinical facts.

The accepted historical [MedGemma M1.1 technical-spike checkpoint](docs/experiments/MedNexus_MedGemma_Technical_Spike_M1.1.md) is safely paused at the official Hugging Face access/terms gate; this is not an inference failure. “M1.1” is a historical experiment identifier from the prior strategy sequence, not roadmap milestone M1 of accepted Strategy v1.1; controlled MedGemma resumption is roadmap M6. No immutable revision was guessed, no GPU or runtime was measured, no model or dependency was installed locally, no clinical inference occurred, and no PHI or unopened holdout was used. `MG-RAD-CANDIDATE-v0.2` remains an experimental exact-quote, no-model-offset candidate contract with deterministic MRJ grounding.

The UI/UX Blueprint v1.0 retains its accepted structural guidance, with MRJ identity superseding its former MedNexus branding and the accepted Cinematic Hero V1 closure qualifying its earlier pre-implementation Landing assumptions. Landing V1 is complete; further UNDERSTAND, PROTECT, and responsive/accessibility work requires separate authorization. Hardware migration and controlled MedGemma resumption remain later roadmap work.

### Radiology UNDERSTAND v1 Current Baseline

**Architecture status: FROZEN. Implementation status: EVOLVING UNDER CONTROLLED MILESTONES.** The accepted working baseline is **950 passed, 8 warnings, 0 failures**. One authoritative `RadiologyUnderstandingDecision`, semantic-role and eligibility qualification, cross-domain arbitration, and serialization-only context construction remain core invariants.

The canonical Radiology taxonomy remains `CT`, `MRI`, `X_RAY`, `ULTRASOUND`, `MAMMOGRAPHY`, `NUCLEAR_MEDICINE`, `FLUOROSCOPY`, and `OTHER`. Actual implementation scope is governed by current code and tests; UNDERSTAND remains bounded and does not emit EXTRACT-level clinical facts. The primary unresolved acceptance blocker is a sufficient authorized real-world Radiology dataset. Synthetic coverage supports engineering regression and conformance but cannot establish clinical acceptance or production readiness.

## Local Development Startup

Start MRJ Main from the repository root using the verified recovered Python 3.10.11 runtime and retained site-packages:

```powershell
cd D:\MedNexus\07_Source_Code
.\start_backend.ps1
```

Open `http://127.0.0.1:8001`. Local development port convention: MRJ Main uses `127.0.0.1:8001`; the separate MRJ Public Health workspace reserves `127.0.0.1:8002`.

The Clinical Privacy Policy Engine combines:

- AI-based candidate entity detection
- Deterministic identifier detection
- Healthcare-aware role and context validation
- Purpose-based clinical privacy policies
- MRJ-owned output construction

OpenMed is a candidate detector only. Its detections are treated as suggestions and its `deidentified_text` is non-authoritative. MRJ owns intelligence decisions, false-positive rejection, purpose-based policy application, and construction of the final de-identified text.

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

The MedNexus Deterministic Identifier Detector is integrated into the real de-identification service alongside the OpenMed candidate path. MRJ merges and evaluates detections before producing the final output.

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

Extracted text enters the same MRJ-owned De-identification Intelligence pipeline used for direct text processing. Scanned or image-based PDF OCR and image extraction are not implemented yet.

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

Phase 2 reuses the existing TXT, DOCX, text-based PDF, `ExtractorFactory`, and `DocumentContent` boundary. It introduces no duplicate parser. Standalone APIs are `POST /api/v1/understanding/analyze-text` and `POST /api/v1/understanding/analyze-file`; the accepted batch foundation adds bounded journey-run creation, per-report analysis, run retrieval, and failed-report retry endpoints while delegating every report to the same authoritative UNDERSTAND service. R1 adds `POST /api/v1/understanding/journey-runs/{run_id}/protect`, which orchestrates the existing authoritative privacy service for eligible retained reports. Completed PDF-origin results expose a non-cacheable protected-artifact endpoint; the retained original PDF is available only through an explicit non-cacheable Compare request.

The active POC product page is `/understanding`, supporting first-class **Single Report** and **Batch Reports** modes. Single mode accepts pasted text or TXT/DOCX/text-based PDF upload. Batch mode accepts up to 10 reports, validates a visible pre-queue, processes reports sequentially through the same single-report service, isolates individual failures, preserves order and stable document identity, and lets users review one report at a time through the shared result renderer. Its accepted frontend uses one shared Report Card for Single and selected Batch UNDERSTAND results. Accepted R1 continues the same reports and run into a report-centric PROTECT result, with compact navigator cards and independent per-report state/result ownership. Rendering failures remain isolated from authoritative JourneyRun processing. On `/app`, active capabilities follow the journey order: Document Recognition, Clinical Privacy Policy Engine, Clinical Extraction, then Public Health Intelligence.

The result workspace presents domain, report type and modality once in the shared card header, followed by a compact context grid (body region, contrast and language when available, plus at most one useful study-family or acquisition field), recognized structure chips, collapsed plain-language Recognition Evidence, and readiness. Technical Details and the duplicate status sidebar are removed from the normal UI; authoritative backend evidence and contracts remain unchanged. Warm paper surfaces, restrained teal, lighter typography weights, reduced-motion support and a stacked mobile layout follow the MRJ visual language. The existing Mona Sans / Segoe UI / Arial font stack is retained; no font binary was added. Processing activity reflects actual requests, not simulated recognition stages. Primary-language detection favors the dominant clinical content rather than short second-script labels or technical footers.

Radiology recognition is backed by an offline MRJ-owned compositional knowledge and reasoning package. Typed concepts with stable IDs feed an exact-offset `DocumentEvidenceFrame`; semantic roles and explicit eligibility determine which evidence supports current identity, report composition, context only, or no authoritative score. Recommendation, comparison, history, and findings-only secondary context remains preserved for provenance without inflating current-study identity. LOINC Document Ontology, DICOM/Structured Reporting, RSNA RadLex/Playbook/RadReport, SNOMED CT, HL7 CDA/C-CDA, and WHO ICD-10/ICD-11 are reference/provenance families only; they do not supply runtime decisions.

The primary UNDERSTAND output is `MedNexusDocumentContext`, not classification alone. UNDERSTAND is intentionally bounded to document identity, small high-value context, semantic structure/relationships, provenance/confidence, review requirements, and routing. Radiology currently derives document-level modality, study anatomy/examination, contrast, selected technique or view context, and semantic composition without claiming lesion, diagnosis, exact measurement, recommendation-text, or other clinical-fact extraction.

The Reference Model Foundation separates authoritative source governance from runtime intelligence. A machine-readable manifest records official version, license/distribution policy, acquisition location, verification date, checksum where published, and enabled state for LOINC/RSNA, DICOM, RadLex, SNOMED CT, and the local MedNexus derivative. Stable MedNexus concept IDs normalize cross-standard mappings and relationships; the application consumes only the deterministic offline canonical model. External standards are reference inputs, not runtime decision engines, and validation reports are never knowledge sources.

For the POC journey, a bounded in-memory `JourneyRun` retains original `DocumentContent` and context with per-document/per-stage status, history, result, warning, review, and error state. A Report is one clinical document with its own seven-stage journey; a Journey Run is a processing event containing one or more reports; and a Batch Run is a multi-report Journey Run. A future Report Collection is a distinct persistent analytical cohort that may combine reports originating from separate Single or Batch Runs—it is not the Batch Run itself. Storage is process-local, non-durable, capacity-bounded, and expires after a sliding 30-minute TTL; raw clinical content is not written to browser storage or logs. R1 keeps Single and Batch reports in the same run through PROTECT, stores sanitized per-report protection envelopes, and leaves durable storage, background workers and Report Collections as future infrastructure. The standalone `/privacy` workspace remains preserved.

The frontend includes a reusable Progressive Result Reveal convention for substantial results. The backend first returns the complete authoritative output; the browser then presents protected text through intact lines or small line groups, with Show Full Result and reduced-motion fallback. The original document and privacy report appear immediately, and copy operations always use the complete authoritative protected output. This is not backend token streaming.

## Current Product Experience

- `/app` — MRJ Medical Report Journey homepage and seven-stage product journey.
- `/understanding` — accepted Single/Batch UNDERSTAND and R1 PROTECT Journey workspace with same-run report-by-report protection review.
- `/privacy` — functional Clinical Privacy Policy Engine POC.

MRJ Website Experience / Cinematic Hero V1 is the accepted `/app` presentation baseline. This visual checkpoint does not change or certify backend/clinical behavior. Public Health Intelligence is active parallel domain work aligned to the shared document journey; it is not represented as production-complete.

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
- MRJ-owned final output construction
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
- MRJ Website Experience / Cinematic Hero V1 closure: **950 passed, 8 warnings, 0 failures** in a fresh full regression; focused homepage suite: **2 passed, 48 deselected, 1 warning**.
- UNDERSTAND Single + Batch workspace (**accepted checkpoint**): final focused UNDERSTAND/Journey checks **74 passed, 1 warning** in **36.19s**; final full regression **966 passed, 8 warnings, 0 failures** in **96.21s**. At that checkpoint Batch Privacy Protection remained unavailable; R1 now supersedes that limitation while Report Collection remains future architecture.
- R1 PROTECT Journey Integration intermediate implementation: hardening-focused validation **88 passed, 8 warnings** in **67.79s**; dedicated Journey/UI contract **21 passed, 8 warnings** in **50.31s**; full regression **971 passed, 8 warnings, 0 failures** in **125.52s**.
- R1 protected-document intermediate correction: focused protected-artifact/Journey validation **24 passed, 8 warnings** in **72.44s**; full regression **974 passed, 8 warnings, 0 failures** in **115.55s**.
- R1 PROTECT Journey Integration (**accepted and closed 2026-09-22**): final focused UNDERSTAND/Journey validation **202 passed, 8 warnings**; protected-PDF artifact validation **5 passed, 1 warning**; privacy regression **272 passed, 7 warnings**; full regression **999 passed, 8 warnings, 0 failures** in **122.35s**. The accepted 20-report set produced 20 independent protected PDFs with zero known high-risk PHI misses and zero wrong clinical transformations while preserving clinical content. All 20 results remained safely explainable `NEEDS_REVIEW`; review-rate optimization is future work.

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

Landing/Cinematic Hero V1 is closed. The immediate product focus returns to core MRJ clinical validation, with sufficient authorized real-world Radiology acceptance data still the major unresolved validation requirement. Later workspace UI, hardware transition, controlled MedGemma resumption, generic engine, adapter, benchmark, fusion, imaging, concordance, UAG-class, and Radiology analytics milestones require separate authorization. OCR, scanned-document recognition, layout vision, advanced clinical extraction, and broad synthetic classifier tuning remain deliberately deferred. Known technical debt is tracked in `backend/TECH_DEBT.md`.

## Latest Privacy Handoff Correction

The same-document UNDERSTAND → PROTECT handoff now preserves the uploaded source filename and displays a compact receipt/context/status summary before privacy processing. Its lifecycle is READY → PROCESSING → PROTECTED, with stable `#workspace` navigation and an explicit path back to standalone paste/upload. Progressive reveal paints the first intact chunk immediately while respecting production reduced-motion behavior. Verification: focused suite **78 passed, 8 warnings**; full regression **742 passed, 8 warnings, 0 failures**.
## Authoritative Radiology Reference Data

Radiology UNDERSTAND can load active, versioned reference derivatives from `D:\MedNexus\Reference_Data` while remaining fully offline at recognition time. The governed command supports `status`, `import`, `verify`, and `activate`; source-specific instructions are in `backend/app/modules/medical_document_intelligence/understanding/reference_model/README.md`.

Current local population includes checksum-verified official LOINC 2.82, RadLex 4.3, DICOM PS3.6 2026c, and a controlled Radiology-focused DICOM PS3.16/DCMR 2026c subset. The LOINC import contributes 19,230 stored concepts and 71,155 mappings from the Radiology Playbook, Parts, ordered composition, RID/RPID crosswalks, Document Ontology, and Imaging Documents. RadLex contributes 24,092 concepts; DCMR contributes 43 controlled Context Groups, 680 stored concepts, and 1,317 mappings; PS3.6 contributes 41 controlled attributes.

After conservative cross-source reconciliation, the active offline runtime contains **43,811 canonical concepts, 96,528 external mappings, and 88,325 relationships**. LOINC, RadLex, and both DICOM sources are populated, checksum-valid, active, and consumed through the same MedNexus canonical registry. SNOMED remains inactive; SNOMED identifiers carried by DCMR/LOINC remain provenance mappings rather than active terminology concepts. No external distribution is stored in Git, no cross-standard mapping is fabricated, and frozen validation reports are not knowledge sources. Latest verification: focused suite **88 passed, 1 warning**; full regression **775 passed, 8 warnings, 0 failures**.
