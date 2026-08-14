# MedNexus Current State

**Authoritative date:** 15 August 2026

## Current Platform State

MedNexus is an Enterprise Medical Document Intelligence Platform. Its public MEDNEXUS⁷ journey is Understand → Protect → Extract → Standardize → Analyze → Visualize → Indicators. Capabilities are modular, independently usable, and connected through shared platform contracts.

Public product signature: **MEDNEXUS⁷ — One document. Seven intelligent transformations.** The homepage presents seven public transformations and treats INGEST as internal file/text intake, extraction/parsing, and `DocumentContent` construction inside UNDERSTAND. Internal identifiers and backend architecture remain `MedNexus`. Latest verification for this UI/product-architecture update: focused homepage suite **48 passed, 1 warning**; full repository regression **743 passed, 8 warnings, 0 failures**.

Public product signature: **MEDNEXUS⁷ — One document. Seven intelligent transformations.** The homepage presents seven public transformations and treats INGEST as internal file/text intake, extraction/parsing, and `DocumentContent` construction inside UNDERSTAND. Internal identifiers and backend architecture remain `MedNexus`. Latest verification for this UI/product-architecture update: focused homepage suite **48 passed, 1 warning**; full repository regression **743 passed, 8 warnings, 0 failures**.

## Phase 1 Status

**Phase 1 — Accepted POC Checkpoint / Paused.** The Clinical Privacy Policy Engine has reached its accepted architecture and synthetic-validation checkpoint. It is not production-ready, exhaustively validated, or clinically certified.

## Current Functional Capability

Medical Document Intelligence — Clinical Privacy Policy Engine / De-identification is functional end to end. Medical Document Understanding & Recognition has reached the accepted Document Context & Journey Foundation checkpoint. `/app` is the enterprise homepage; `/understanding` is the standalone UNDERSTAND workspace; `/privacy` is the functional privacy POC.

## Supported Input

Implemented: pasted text, TXT, DOCX, and text-based PDF. Scanned-PDF OCR is not implemented.

## Privacy Profiles

Canonical profiles are `MEDNEXUS_CLINICAL`, `MEDNEXUS_RESEARCH`, `MEDNEXUS_ANALYTICS_PUBLIC_HEALTH`, and `MEDNEXUS_STRICT_PRIVACY`. Executable actions are `KEEP`, `REPLACE`, `HASH`, `MASK`, and `REMOVE`; advanced transformations remain planned.

## Current Architecture Ownership

Contextual and deterministic MedNexus detection plus OpenMed candidates converge through canonicalization, `RoleResolver`, `ContextValidator`, merging/orchestration, the purpose-based policy engine, and `MedNexusOutputBuilder`. OpenMed is candidate-only; its `deidentified_text` is non-authoritative. MedNexus owns interpretation, privacy decisions, transformations, and final protected output.

## Latest Acceptance Fixes

- Formatted international phone values such as `+123 456 7890` are accepted by conservative contact validation and remain policy-controlled.
- Reporting Physician, Admitting Consultant, and Consultant Pathologist contexts resolve consistently as clinician identity.
- Supported Arabic professional contexts, including `طبيب الأشعة`, create complete clinician-name spans.
- `Dr.` and `د.` remain outside personal-name spans; the selected policy controls clinician KEEP or transformation.

## Verified Test Baseline

- Targeted acceptance: **103 passed, 7 warnings**.
- Full regression: **681 passed, 8 warnings, 0 failures**.
- Synthetic acceptance is intentionally frozen at this checkpoint.

## Phase 2 Foundation Checkpoint

**Medical Document Understanding & Recognition — FOUNDATION CHECKPOINT ACCEPTED.** Checkpoint commit: `a1e8ff2`. Accepted regression baseline: **714 passed, 8 warnings, 0 failures**; focused Phase 2 hardening suite: **33 passed**. The earlier initial foundation baseline was **705 passed, 8 warnings, 0 failures**, with no Phase 1 regression.

The implemented boundary is `Source File / Text → existing ExtractorFactory → existing DocumentContent → Language Detection → Structural Section Detection → Evidence-Based Classification → Confidence/Evidence → Symbolic Routing`. UNDERSTAND is independently usable and does not depend on privacy internals. Text and file APIs are exposed at `/api/v1/understanding/analyze-text` and `/api/v1/understanding/analyze-file`.

Initial domains are Radiology, Pathology, Laboratory, Emergency, Admission/Discharge, Public Health, and Unknown. Results include type/subtype, language, major section ranges, confidence, explainable evidence, symbolic routing, metadata, and warnings. `UNKNOWN` and low confidence are intentionally valid.

## Phase 2 Accepted Document Context & Journey Foundation Checkpoint

**Status: ACCEPTED DOCUMENT CONTEXT & JOURNEY FOUNDATION CHECKPOINT.** Accepted commit: `fa1a8ba68d66a3d40f40c8af3bf644f3b909191a`. Previous Phase 2 checkpoints are `a1e8ff2` (foundation) and `551be07` (foundation documentation synchronization). Phase 1 remains frozen at `3486c206085652e2edac2574d277ff0970e037e2`.

The canonical public target journey is `01 UNDERSTAND → 02 PROTECT → 03 EXTRACT → 04 STANDARDIZE → 05 ANALYZE → 06 VISUALIZE → 07 INDICATORS`. INGEST remains an internal technical operation within UNDERSTAND: file/text intake, extraction/parsing, and `DocumentContent` construction. `MedNexusDocumentContext` is the reusable semantic handoff between stages. UNDERSTAND produces document identity, structure, clinical context, privacy context, processing context, and provenance while preserving unknown values as null/unknown.

The current POC flow is `Upload once → INGEST → UNDERSTAND → MedNexusDocumentContext → Continue to Privacy Protection → existing Phase 1 privacy pipeline`, without a second upload. The retained source filename and document status remain visible during the handoff.

Recognition Knowledge Layer v1 provides MedNexus-owned multilingual concepts, domain signatures, evidence interpretation, and external-reference provenance, with Radiology as the first reference domain. LOINC Document Ontology, DICOM/Structured Reporting, RSNA RadLex/Playbook/RadReport, SNOMED CT, HL7 CDA/C-CDA, and WHO ICD-10/ICD-11 are reference inputs only. MedNexus owns curation, normalization, recognition signatures, context construction, and decision logic.

Progressive Result Reveal is frontend presentation of a completed authoritative result, not backend streaming. Accepted regression baseline: **742 passed, 8 warnings, 0 failures**.

## Phase 2 Product Integration

`/understanding` is the active standalone Medical Document Understanding & Recognition POC. It supports pasted text and existing TXT/DOCX/text-based PDF ingestion, displays recognition, confidence, sections, evidence, symbolic route recommendations and warnings, and treats UNKNOWN/manual review as a valid outcome. `/app` now orders its capability entry points as Document Recognition → Clinical Privacy Policy Engine → Clinical Extraction → Public Health Intelligence.

Frontend integration verification: focused Understanding/API/frontend suite **37 passed, 1 warning**; full repository regression **718 passed, 8 warnings, 0 failures**.

## Recognition UX and Arabic Radiology Hardening

Arabic Radiology evidence now includes conservative department, examination, structural heading, radiologist-role, and modality concepts. Primary-language detection represents the dominant meaningful clinical language, so small English technical footers do not force an otherwise Arabic report to MIXED. The real validation file `MNX-01-03_Radiology_Arabic.txt` now resolves as `RADIOLOGY` / `RADIOLOGY_REPORT` / `CT` / `ARABIC`, confidence `1.0` HIGH, with Radiology Examination, Technique, Findings, Impression, and Radiologist/Authentication sections.

The `/understanding` result hierarchy is now: human-readable recognition summary → detected structure → plain-language evidence → recommended journey → warnings → collapsed technical details. UNKNOWN remains a successful outcome presented as “Document type not confidently identified” with manual review recommended.

Hardening verification: focused suite **44 passed, 1 warning**; full repository regression **725 passed, 8 warnings, 0 failures**.

## Recognition Knowledge Layer v1

Radiology recognition now consumes a MedNexus-owned, offline knowledge package rather than hard-coded profile vocabulary. Stable bilingual concept IDs cover document identity, service context, sections, author role, and modality. A Radiology Report signature requires combinations of identity, structural, and supporting evidence; incidental modality mentions remain insufficient. LOINC Document Ontology, DICOM/DICOM SR, RSNA RadLex/Playbook/RadReport, SNOMED CT, and HL7 CDA/C-CDA are traceability reference families only—MedNexus owns runtime interpretation and no external terminology service is called.

The `/understanding` result now uses one vertical primary result card (domain → type → subtype → language → confidence), no more than two default explanatory blocks, a compact journey, and collapsed technical details containing concept IDs and provenance. Fresh direct-service and live-browser validation of `MNX-01-03_Radiology_Arabic.txt` agree at `RADIOLOGY` / `RADIOLOGY_REPORT` / `CT` / `ARABIC`, confidence `1.0` HIGH. The earlier browser UNKNOWN was caused by a stale non-reload server retaining pre-hardening Python modules.

Knowledge-layer verification: focused suite **50 passed, 1 warning**; full repository regression **731 passed, 8 warnings, 0 failures**.

## MedNexus Document Context Foundation

UNDERSTAND now produces `MedNexusDocumentContext` as the reusable semantic handoff for one ingested document. The v1 contract contains document/ingestion identity, recognized healthcare identity, semantic section structure, conservative domain clinical context, privacy-relevant regions, symbolic processing recommendations, and knowledge/evidence provenance. Unknown values remain null or explicitly unknown.

Radiology is the first meaningful domain extension. The real Arabic CT report produces modality `CT`, examination `CT Chest`, body region `CHEST`, contrast `WITH_CONTRAST`, five semantic sections, Radiologist/Authentication privacy context, and traceable knowledge concept IDs. This is document context—not Stage 04 structured clinical extraction.

A bounded process-local POC journey retains the original `DocumentContent` with its context. `/understanding` can continue to `/privacy?journey_id=…`; the privacy page invokes the existing frozen `DeidentificationService` using the retained text and selected policy without a second upload. It introduces no database, durable workflow claim, or change to Phase 1 privacy decisions.

Document Context verification: focused suite **64 passed, 8 warnings**; full repository regression **737 passed, 8 warnings, 0 failures**. Direct service, live Understanding API/UI, and the same live journey agree on the real Arabic acceptance case.

## Phase 2 UI Polish and Progressive Result Reveal

The accepted `/understanding` information architecture now uses desktop space more effectively through a wide, balanced identity/overview composition while preserving the single-column mobile experience. Recognized Sections, Reusable Document Context, Ready for MedNexus, and collapsed Technical Details remain unchanged semantically.

`MedNexusProgressiveResult` is a reusable framework-free presentation helper. After the authoritative privacy response arrives, the original document appears completely while the protected document is revealed by intact lines or small line groups over several seconds. Users can show the full result immediately; Copy always uses the complete authoritative output. Reduced-motion environments bypass animation. This is frontend presentation—not backend streaming—and does not change privacy decisions.

UI-polish verification: focused suite **75 passed, 8 warnings**; full repository regression **739 passed, 8 warnings, 0 failures**. Desktop and 390×844 mobile browser reviews found no horizontal overflow; the real Arabic journey remains intact.

## Phase 2 UI Polish and Progressive Result Reveal

The accepted `/understanding` information architecture now uses desktop space more effectively through a wide, balanced identity/overview composition while preserving the single-column mobile experience. Recognized Sections, Reusable Document Context, Ready for MedNexus, and collapsed Technical Details remain unchanged semantically.

`MedNexusProgressiveResult` is a reusable framework-free presentation helper. After the authoritative privacy response arrives, the original document appears completely while the protected document is revealed by intact lines or small line groups over several seconds. Users can show the full result immediately; Copy always uses the complete authoritative output. Reduced-motion environments bypass animation. This is frontend presentation—not backend streaming—and does not change privacy decisions.

UI-polish verification: focused suite **75 passed, 8 warnings**; full repository regression **739 passed, 8 warnings, 0 failures**. Desktop and 390×844 mobile browser reviews found no horizontal overflow; the real Arabic journey remains intact.

## MedNexus Document Context Foundation

UNDERSTAND now produces `MedNexusDocumentContext` as the reusable semantic handoff for one ingested document. The v1 contract contains document/ingestion identity, recognized healthcare identity, semantic section structure, conservative domain clinical context, privacy-relevant regions, symbolic processing recommendations, and knowledge/evidence provenance. Unknown values remain null or explicitly unknown.

Radiology is the first meaningful domain extension. The real Arabic CT report produces modality `CT`, examination `CT Chest`, body region `CHEST`, contrast `WITH_CONTRAST`, five semantic sections, Radiologist/Authentication privacy context, and traceable knowledge concept IDs. This is document context—not Stage 04 structured clinical extraction.

A bounded process-local POC journey retains the original `DocumentContent` with its context. `/understanding` can continue to `/privacy?journey_id=…`; the privacy page invokes the existing frozen `DeidentificationService` using the retained text and selected policy without a second upload. It introduces no database, durable workflow claim, or change to Phase 1 privacy decisions.

Document Context verification: focused suite **64 passed, 8 warnings**; full repository regression **737 passed, 8 warnings, 0 failures**. Direct service, live Understanding API/UI, and the same live journey agree on the real Arabic acceptance case.

## MedNexus Document Context Foundation

UNDERSTAND now produces `MedNexusDocumentContext` as the reusable semantic handoff for one ingested document. The v1 contract contains document/ingestion identity, recognized healthcare identity, semantic section structure, conservative domain clinical context, privacy-relevant regions, symbolic processing recommendations, and knowledge/evidence provenance. Unknown values remain null or explicitly unknown.

Radiology is the first meaningful domain extension. The real Arabic CT report produces modality `CT`, examination `CT Chest`, body region `CHEST`, contrast `WITH_CONTRAST`, five semantic sections, Radiologist/Authentication privacy context, and traceable knowledge concept IDs. This is document context—not Stage 04 structured clinical extraction.

A bounded process-local POC journey retains the original `DocumentContent` with its context. `/understanding` can continue to `/privacy?journey_id=…`; the privacy page invokes the existing frozen `DeidentificationService` using the retained text and selected policy without a second upload. It introduces no database, durable workflow claim, or change to Phase 1 privacy decisions.

Document Context verification: focused suite **64 passed, 8 warnings**; full repository regression **737 passed, 8 warnings, 0 failures**. Direct service, live Understanding API/UI, and the same live journey agree on the real Arabic acceptance case.

Knowledge-layer verification: focused suite **50 passed, 1 warning**; full repository regression **731 passed, 8 warnings, 0 failures**.

## Recognition Knowledge Layer v1

Radiology recognition now consumes a MedNexus-owned, offline knowledge package rather than hard-coded profile vocabulary. Stable bilingual concept IDs cover document identity, service context, sections, author role, and modality. A Radiology Report signature requires combinations of identity, structural, and supporting evidence; incidental modality mentions remain insufficient. LOINC Document Ontology, DICOM/DICOM SR, RSNA RadLex/Playbook/RadReport, SNOMED CT, and HL7 CDA/C-CDA are traceability reference families only—MedNexus owns runtime interpretation and no external terminology service is called.

The `/understanding` result now uses one vertical primary result card (domain → type → subtype → language → confidence), no more than two default explanatory blocks, a compact journey, and collapsed technical details containing concept IDs and provenance. Fresh direct-service and live-browser validation of `MNX-01-03_Radiology_Arabic.txt` agree at `RADIOLOGY` / `RADIOLOGY_REPORT` / `CT` / `ARABIC`, confidence `1.0` HIGH. The earlier browser UNKNOWN was caused by a stale non-reload server retaining pre-hardening Python modules.

## Known Limitations / Deferred Validation

## Privacy Handoff UX Correction

The UNDERSTAND → PROTECT journey now preserves the original uploaded filename in the retained `DocumentContent` and presents a compact handoff status in `/privacy`: document received, reusable context available, no re-upload required, and READY → PROCESSING → PROTECTED lifecycle state. The selected policy remains explicit, manual paste/upload controls remain available through “Use another document instead,” and standalone `/privacy` behavior is unchanged.

Progressive protected-result presentation now paints its first intact chunk immediately, keeps “Show full result” available during the reveal, and preserves reduced-motion behavior in normal use. A localhost-only validation override may force the animation for acceptance review; it does not alter production accessibility behavior or the authoritative complete backend result.

Correction verification: focused suite **78 passed, 8 warnings**; full repository regression **742 passed, 8 warnings, 0 failures**. Live Arabic and English browser journeys preserved their source filenames, landed at `#workspace`, completed the handoff lifecycle, and produced authoritative protected output without re-upload.

Deferred: broader real medical-report validation, additional real-report privacy edge cases, broader multilingual person/clinician coverage, OCR, production hardening, performance/load validation, formal benchmark expansion, and remaining frontend visual refinements. These are not blockers for this POC checkpoint.

## Frontend Checkpoint

The current Deep Teal Hybrid `/app` and `/privacy` experience is an accepted working baseline. Minor visual refinements are intentionally deferred.

## Active Parallel Work

Public Health Intelligence is active parallel MedNexus work aligned to the shared journey while retaining domain-specific extraction schemas, analytics, dashboards, and indicators. It is not declared production-complete.

## Next Development Direction

**Phase 2 Document Context Validation — Round 1.** Validate the common context contract and Radiology extension across a small representative set before adding meaningful context packages for other domains.

OCR, scanned recognition, layout vision, table extraction, universal or ML/transformer/LLM classifiers, external classification, embeddings, advanced clinical extraction, FHIR/HL7, dashboard integration, and broad synthetic tuning remain deliberately deferred.

## Privacy Handoff UX Correction

The UNDERSTAND → PROTECT journey now preserves the original uploaded filename in retained `DocumentContent` and presents a compact `/privacy` handoff receipt: document received, reusable context available, no re-upload required, and READY → PROCESSING → PROTECTED lifecycle state. Policy choice remains explicit, “Use another document instead” restores manual input, and standalone `/privacy` behavior is unchanged.

Progressive protected-result presentation paints its first intact chunk immediately, keeps “Show full result” available during reveal, and respects reduced-motion preferences. A localhost-only acceptance switch can force motion without changing production accessibility or the authoritative complete backend result.

Correction verification: focused suite **78 passed, 8 warnings**; full repository regression **742 passed, 8 warnings, 0 failures**. Live Arabic and English browser journeys preserved source filenames, landed at `#workspace`, completed the lifecycle, and produced protected output without re-upload.

## Privacy Handoff UX Correction

The UNDERSTAND → PROTECT journey now preserves the original uploaded filename in retained `DocumentContent` and presents a compact `/privacy` handoff receipt: document received, reusable context available, no re-upload required, and READY → PROCESSING → PROTECTED lifecycle state. Policy choice remains explicit, “Use another document instead” restores manual input, and standalone `/privacy` behavior is unchanged.

Progressive protected-result presentation paints its first intact chunk immediately, keeps “Show full result” available during reveal, and respects reduced-motion preferences. A localhost-only acceptance switch can force motion without changing production accessibility or the authoritative complete backend result.

Correction verification: focused suite **78 passed, 8 warnings**; full repository regression **742 passed, 8 warnings, 0 failures**. Live Arabic and English browser journeys preserved source filenames, landed at `#workspace`, completed the lifecycle, and produced protected output without re-upload.
