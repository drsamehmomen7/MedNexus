# MedNexus Current State

**Authoritative date:** 16 August 2026

## Cross-Domain Architecture Contract Baseline

**Status:** Approved architecture-contract baseline; implementation remains controlled and incremental. **Date:** 16 August 2026.

The authoritative baseline artifacts are [MedNexus Architecture Crosswalk v1.1](docs/architecture/contracts/MedNexus_Architecture_Crosswalk_v1.1.md), [MedNexus Clinical Semantic Context Contract v0.1](docs/architecture/contracts/MedNexus_Clinical_Semantic_Context_Contract_v0.1.md), and [MedNexus Clinical Extraction Contract v0.1](docs/architecture/contracts/MedNexus_Clinical_Extraction_Contract_v0.1.md). They are architecture-contract baselines; implementation remains controlled and incremental.

The authoritative MEDNEXUS⁷ journey is `01 UNDERSTAND → 02 PROTECT → 03 EXTRACT → 04 STANDARDIZE → 05 ANALYZE → 06 VISUALIZE → 07 INDICATORS`. INGEST is an internal operation within UNDERSTAND, not an independent transformation.

UNDERSTAND will progressively produce a rich typed `MedNexusClinicalContext`: a generic semantic core with backward-compatible typed domain extensions such as `RadiologyClinicalContext`, `LaboratoryClinicalContext`, `PublicHealthClinicalContext`, and `ImmunizationClinicalContext`. It describes document identity and semantic/clinical contexts; it must not become field-level EXTRACT. Untyped attributes remain only a controlled compatibility escape hatch.

Document-domain taxonomy is independent of the consuming application vertical. Notifiable-disease and epidemiological-surveillance documents may be `PUBLIC_HEALTH`; patient laboratory reports remain `LABORATORY`; immunization records use the independent `IMMUNIZATION` domain. A laboratory document consumed by a Public Health workflow remains Laboratory.

PROTECT remains the frozen Phase 1 policy/governance boundary. A future `ProtectionContext` / Protected Execution Envelope may govern protected text, raw-text access (`ALLOWED`, `DENIED`, or `RESTRICTED`), policy identity, transformations, permissions, and provenance; this full envelope is not implemented. Dates require future semantic privacy roles such as event, report, specimen collection, result, administration, and birth. Consequently, `MEDNEXUS_ANALYTICS_PUBLIC_HEALTH` is not approved for real production Public Health use until date semantics are resolved.

EXTRACT produces terminology-independent clinical facts, entities, and observations with per-field confidence/provenance. Mapping failure must not alter extraction recognition or confidence. Future contract terminology is `document_review_required` and `extraction_review_required`; current implementation names remain supported until a backward-compatible migration. STANDARDIZE exclusively owns terminology/code mapping, including ICD, LOINC, SNOMED CT, RadLex, CVX, and UCUM where appropriate.

Development proceeds in parallel: Track A (MedNexus Core) owns rich UNDERSTAND, PROTECT, and generic EXTRACT/STANDARDIZE foundations; Track B (the separate Domain Intelligence workspace) owns domain implementations of EXTRACT, STANDARDIZE, ANALYZE, VISUALIZE, and INDICATORS. Radiology remains the first rich UNDERSTAND reference domain. Public Health Stable Scope Checkpoint v0.1.0 is a scope checkpoint, not a production-readiness claim; Laboratory follows as the next domain vertical using Public Health assets as seeds rather than a complete Laboratory specification, followed by Pathology and later downstream Radiology intelligence.

Current Core regression baseline: **780 passed, 8 warnings, 0 failures**. Latest Radiology composition checkpoint: `53a988cafd23e514b31d85e240688a6d0c3b1b31`.

The two repositories, runtimes, frontends, and deployment workflows remain operationally separate. GitHub is source-code authority; Render may be used for synthetic/development deployment but is not mandatory platform architecture, and real PHI must not enter it without appropriate protection and infrastructure governance.

A standing bidirectional Cross-Track Synchronization Policy requires a concise Cross-Track Sync Brief when shared architecture/contracts change, either track reaches a stable checkpoint, a cross-track dependency or impact appears, or before integration/convergence. Routine internal changes with no shared-contract effect do not require a brief. Domain Development Checkpoints may use synthetic/local bootstrap detection; a MedNexus Integrated Domain Checkpoint requires conformance with canonical contracts, including `MedNexusDocumentContext` where applicable.

## Radiology Validation and Composition Checkpoint

The Radiology forensic sequence confirmed two reusable architecture corrections. First, conservative clustered-heading recovery handles flattened reports using governed headings and exact offsets. Second, when PDF extraction preserves a strongly composed report whose findings narrative lacks an explicit `FINDINGS` heading, the report gate may use the combination of explicit Impression, radiologist attribution, modality, and multiple technique/acquisition concepts. Extraction, normalization, terminology, mappings, and confidence thresholds remain unchanged.

Checkpoint `53a988cafd23e514b31d85e240688a6d0c3b1b31` records the generic composition correction. No filename, vendor template, blind-report phrase, production vocabulary, alias, mapping, or report-specific rule was introduced. Current complete regression: **780 passed, 8 warnings, 0 failures**.

## Current Platform State

MedNexus is an Enterprise Medical Document Intelligence Platform. Its public MEDNEXUS⁷ journey is Understand → Protect → Extract → Standardize → Analyze → Visualize → Indicators. Capabilities are modular, independently usable, and connected through shared platform contracts.

Public product signature: **MEDNEXUS⁷ — One document. Seven intelligent transformations.** The homepage presents seven public transformations and treats INGEST as internal file/text intake, extraction/parsing, and `DocumentContent` construction inside UNDERSTAND. Internal identifiers and backend architecture remain `MedNexus`. Latest verification for this UI/product-architecture update: focused homepage suite **48 passed, 1 warning**; full repository regression **743 passed, 8 warnings, 0 failures**.

## Radiology Intelligence Architecture v2 — Pending Review

Radiology now uses a compositional, MedNexus-owned reasoning path: normalized knowledge concepts → exact-offset `DocumentEvidenceFrame` → domain coherence → document-type reasoning → modality and domain-context construction → `MedNexusDocumentContext`. Evidence is grouped by modality, technique, acquisition, anatomy, contrast, structure, clinical purpose, and professional/service context; external standards remain provenance inputs only.

Domain recognition and Radiology Report recognition are separate decisions. Coherent imaging evidence can establish Radiology context without fabricating a report type; Findings/Impression or explicit report identity supports report classification. Strong Emergency, Admission, or Discharge structure remains authoritative over incidental imaging mentions. `SectionDetector` v2 supports line headings, inline heading/content, and colon-delimited flattened templates while preserving exact source offsets.

Radiology context now supports MRI, CT, X-ray, Ultrasound, Doppler, Mammography, and Nuclear Medicine; multiple broad body regions; composed examination names; pre/post contrast; imaging-technique families; and broad clinical purpose. Validation Failure R-001 resolves as Radiology / Radiology Report / MRI, `MRI Abdomen & Pelvis`, abdomen and pelvis, pre/post contrast, Oncologic Staging, the expected MRI technique families and six structural sections, with HIGH confidence. Focused verification: **77 passed, 1 warning**. Full uncommitted regression: **758 passed, 8 warnings, 0 failures**.

## Reference Model Foundation v1 — Pending Review

An explicit governed Reference Model now sits beneath Radiology Intelligence v2: official-source registry and manifest → controlled offline import boundary → stable MedNexus canonical concepts → cross-standard mappings and relationships → canonical resolver → `DocumentEvidenceFrame` → MedNexus reasoning. External standards provide reference knowledge; they do not replace MedNexus normalization, evidence composition, conflicts, decisions, or context construction.

The manifest records LOINC/RSNA 2.82, the DICOM 2026 current rolling edition, RadLex current-at-controlled-download, SNOMED CT International 20260701, and the enabled MedNexus Radiology Reference Derivative v1. External distributions are not bundled. LOINC, DICOM and RadLex require controlled acquisition under their terms; SNOMED content remains license-restricted. Runtime is deterministic and offline.

The model preserves stable MedNexus IDs, external mappings, relationship provenance, source versions, and distribution policy. Domain/type decisions remain valid when modality is unresolved; structured templates with multiple modality options can resolve as Radiology/Radiology Report with modality UNKNOWN and document nature STRUCTURED_TEMPLATE. Validation reports remain firewalled from production knowledge. Focused verification: **83 passed, 1 warning**. Full regression: **764 passed, 8 warnings, 0 failures**.

## Authoritative Reference Data Population v1 — Pending Review

The Reference Model now has executable offline import, checksum verification, activation, health reporting, conservative deduplication, source trust levels, and runtime loading. Official DICOM PS3.6 2026c XML is populated and active from `D:\MedNexus\Reference_Data`: **41 controlled concepts / 41 source mappings**, SHA-256 `ff1dcdfb557d57db96420614fcaf6d739bb76aa74b73eba77f367be9fab0be3e`. LOINC/RSNA 2.82, RadLex, and SNOMED CT International 20260701 have real local importers but remain unpopulated pending their authenticated/licensed official artifacts.

Runtime remains offline and queries the active local Reference Model before the MedNexus curated compatibility fallback. External identifiers never become MedNexus primary keys, and no cross-standard mapping is invented. Frozen available validation after activation remains correct: Arabic CT and English CT resolve as Radiology/Radiology Report/CT/HIGH; Discharge and Emergency controls retain their stronger domains. MRI R-001 remains covered by the frozen test; the unseen liver artifact is unavailable and was not reconstructed or used for tuning. Focused verification: **28 passed**. Full regression: **771 passed, 8 warnings, 0 failures**.

## Radiology Authoritative Knowledge Population — Complete / Pending Checkpoint Review

Official LOINC 2.82, RadLex 4.3, DICOM PS3.6 2026c, and the controlled Radiology-focused DICOM PS3.16/DCMR 2026c subset are populated, checksum-valid, active, and consumed by the offline runtime. The LOINC artifact at the canonical path `D:\MedNexus\Reference_Data\LOINC\2.82\Loinc_2.82.zip` is 83,924,362 bytes with SHA-256 `6844c04ee57cb9b77050df54f4b0a5b82cd6be520cad9245e8de54db0638dd62`.

LOINC contributes 19,230 stored concepts and 71,155 mappings across 7,010 Playbook procedures, 1,492 relevant Parts, ordered `PartSequenceOrder` composition, official RID/RPID and Part-related RadLex mappings, 3,660 Document Ontology records, and 7,043 Imaging Documents. RadLex contributes 24,092 concepts; DCMR contributes 43 controlled Context Groups, 680 stored concepts and 1,317 mappings; PS3.6 contributes 41 controlled attributes. After conservative reconciliation, the runtime contains **43,811 canonical concepts, 96,528 external mappings, and 88,325 relationships**.

Imported reference matches enrich exact-offset MedNexus evidence with provenance and relationship coherence without becoming independent duplicate confidence votes. Structural evidence still requires detected headings, cross-domain precedence remains intact, and external standards remain subordinate to MedNexus-owned reasoning. Frozen validation opened only after focused gates passed: all three Radiology TXT reports resolved as Radiology / Radiology Report / CT / HIGH, and 57 non-Radiology TXT controls produced zero Radiology false positives. No report-derived production vocabulary or rules were added. Focused verification: **88 passed, 1 warning**. Full regression: **775 passed, 8 warnings, 0 failures**.

## Superseded Pre-LOINC Population Snapshot

Official RadLex 4.3 OWL plus CSV and official DICOM PS3.16 2026c are now populated and active outside Git. RadLex contributes 24,092 reconciled ontology concepts with preferred labels, permitted synonyms, definitions, hierarchy and relationship properties. The controlled DCMR subset contributes 43 Context Groups and 637 imported group-member relationships before conservative canonical deduplication; PS3.6 remains active with 41 attributes. The combined offline runtime currently contains **24,609 canonical concepts, 25,402 external mappings and 24,739 relationships**.

Runtime performs indexed candidate generation, preserves ambiguity, feeds imported canonical concepts and provenance into `DocumentEvidenceFrame`, and uses matched relationships as a bounded coherence contribution. Cold initialization measured 2.2103 seconds; warm recognition measured 0.0107 seconds for a representative short report. SNOMED remains configured but inactive; DCMR SNOMED identifiers are provenance mappings only.

This snapshot preceded canonical path reconciliation and is retained only as chronology. Its missing-artifact conclusion is superseded by the complete active population above.

## Superseded Pre-LOINC Population Snapshot (Duplicate Historical Draft)

Official RadLex 4.3 OWL plus CSV and official DICOM PS3.16 2026c are now populated and active outside Git. RadLex contributes 24,092 reconciled ontology concepts with preferred labels, permitted synonyms, definitions, hierarchy and relationship properties. The controlled DCMR subset contributes 43 Context Groups and 637 imported group-member relationships before conservative canonical deduplication; PS3.6 remains active with 41 attributes. The combined offline runtime currently contains **24,609 canonical concepts, 25,402 external mappings and 24,739 relationships**.

Runtime performs indexed candidate generation, preserves ambiguity, feeds imported canonical concepts and provenance into `DocumentEvidenceFrame`, and uses matched relationships as a bounded coherence contribution. Cold initialization measured 2.2103 seconds; warm recognition measured 0.0107 seconds for a representative short report. SNOMED remains configured but inactive; DCMR SNOMED identifiers are provenance mappings only.

This duplicate draft also predates canonical path reconciliation. Its missing-artifact conclusion is superseded by the complete active population above.

## Authoritative Reference Data Population v1 — Pending Review

The Reference Model now has executable offline import, checksum verification, activation, health reporting, conservative deduplication, source trust levels, and runtime loading. Official DICOM PS3.6 2026c XML is populated and active from `D:\MedNexus\Reference_Data`: **41 controlled concepts / 41 source mappings**, SHA-256 `ff1dcdfb557d57db96420614fcaf6d739bb76aa74b73eba77f367be9fab0be3e`. LOINC/RSNA 2.82, RadLex, and SNOMED CT International 20260701 have real local importers but remain unpopulated pending their authenticated/licensed official artifacts.

Runtime remains offline and queries the active local Reference Model before the MedNexus curated compatibility fallback. External identifiers never become MedNexus primary keys, and no cross-standard mapping is invented. Frozen available validation after activation remains correct: Arabic CT and English CT resolve as Radiology/Radiology Report/CT/HIGH; Discharge and Emergency controls retain their stronger domains. MRI R-001 remains covered by the frozen test; the unseen liver artifact is unavailable and was not reconstructed or used for tuning. Focused verification: **28 passed**. Full regression: **pending this batch's final run**.

## Reference Model Foundation v1 — Pending Review

An explicit governed Reference Model now sits beneath Radiology Intelligence v2: official-source registry and manifest → controlled offline import boundary → stable MedNexus canonical concepts → cross-standard mappings and relationships → canonical resolver → `DocumentEvidenceFrame` → MedNexus reasoning. External standards provide reference knowledge; they do not replace MedNexus normalization, evidence composition, conflicts, decisions, or context construction.

The manifest records LOINC/RSNA 2.82, the DICOM 2026 current rolling edition, RadLex current-at-controlled-download, SNOMED CT International 20260701, and the enabled MedNexus Radiology Reference Derivative v1. External distributions are not bundled. LOINC, DICOM and RadLex require controlled acquisition under their terms; SNOMED content remains license-restricted. Runtime is deterministic and offline.

The model preserves stable MedNexus IDs, external mappings, relationship provenance, source versions, and distribution policy. Domain/type decisions remain valid when modality is unresolved; structured templates with multiple modality options can resolve as Radiology/Radiology Report with modality UNKNOWN and document nature STRUCTURED_TEMPLATE. Validation reports remain firewalled from production knowledge. Focused verification: **83 passed, 1 warning**. Full regression: **764 passed, 8 warnings, 0 failures**.

## Radiology Intelligence Architecture v2 — Pending Review

Radiology now uses a compositional, MedNexus-owned reasoning path: normalized knowledge concepts → exact-offset `DocumentEvidenceFrame` → domain coherence → document-type reasoning → modality and domain-context construction → `MedNexusDocumentContext`. Evidence is grouped by modality, technique, acquisition, anatomy, contrast, structure, clinical purpose, and professional/service context; external standards remain provenance inputs only.

Domain recognition and Radiology Report recognition are separate decisions. Coherent imaging evidence can establish Radiology context without fabricating a report type; Findings/Impression or explicit report identity supports report classification. Strong Emergency, Admission, or Discharge structure remains authoritative over incidental imaging mentions. `SectionDetector` v2 supports line headings, inline heading/content, and colon-delimited flattened templates while preserving exact source offsets.

Radiology context now supports MRI, CT, X-ray, Ultrasound, Doppler, Mammography, and Nuclear Medicine; multiple broad body regions; composed examination names; pre/post contrast; imaging-technique families; and broad clinical purpose. Validation Failure R-001 resolves as Radiology / Radiology Report / MRI, `MRI Abdomen & Pelvis`, abdomen and pelvis, pre/post contrast, Oncologic Staging, the expected MRI technique families and six structural sections, with HIGH confidence. Focused verification: **77 passed, 1 warning**. Full uncommitted regression: **758 passed, 8 warnings, 0 failures**.

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
