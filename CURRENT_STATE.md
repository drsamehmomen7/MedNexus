# MRJ Current State

**Authoritative date:** 17 September 2026

## MRJ Phase 0 public identity and documentation

MRJ is the approved public identity of the continuing MedNexus project. MRJ means **Medical Report Journey**. The MedNexus-named frozen Blueprint v2.0, UNDERSTAND Domain Matrix v1.0, Crosswalk v2.0, Semantic Context Contract v0.2, and Extraction Contract v0.2 remain the governing technical authority for MRJ. Their files, versions, technical identifiers, and historical names are not renamed by this public-identity migration.

**The medical report is the hero of the platform.** The product narrative is **REPORT | PATHWAY | OUTCOME**.

Approved language:

- Every Medical Report Has a Journey.
- From Medical Report to Measurable Indicator.
- From Document to Decision.
- Understand it. Protect it. Structure it. Analyze it. Measure what matters.
- REPORT | PATHWAY | OUTCOME

The public journey remains **UNDERSTAND → PROTECT → EXTRACT → STANDARDIZE → ANALYZE → VISUALIZE → INDICATORS**, with INGEST internal to UNDERSTAND. Radiology remains primary and Public Health secondary. Recognition, privacy processing, contracts, policies, provenance, and external-engine candidate-only authority are unchanged. PROTECT and STANDARDIZE ownership stays with the platform; this rebrand implements no future stage or multi-engine runtime.

Approved MRJ icons are installed at `frontend/assets/brand/mrj/`; original supplied bytes are preserved. Native typography provides the wordmark. Public titles, labels, and branding on `/app`, `/understanding`, and `/privacy` use MRJ. Old raster branding remains unreferenced and unedited; `/app` domain visuals are brand-neutral native SVG. Technical policy/provenance values can still contain MedNexus and remain unmodified.

Accepted checkpoints remain M0 `081e8b178f63850beb18f41a09494452aeacc4fc`, design `b64a8ee`, Radiology `31b22ab`, and MRJ identity/website baseline `9e96656`. The UNDERSTAND Single/Batch workspace is now an accepted checkpoint, freshly verified at **966 passed, 8 warnings, 0 failures**.

MRJ Website Experience / Cinematic Hero V1 is closed. The UNDERSTAND Single + Batch Journey Foundation is also accepted and closed below. PROTECT redesign and later work remain separately authorized; no naming exploration, logo redesign, or internal-identifier migration is authorized.

## Radiology Horizontal Clinical Journey Architecture R0 — Accepted

Human architecture review formally accepted and closed the R0 foundation on **2026-09-17** for a Radiology-only horizontal journey across all seven public stages. The accepted package consists of:

- [MRJ Horizontal Clinical Journey Architecture v1.0](docs/architecture/MRJ_Horizontal_Clinical_Journey_Architecture_v1.0.md)
- [MRJ Domain Clinical Extraction Architecture v1.0](docs/architecture/MRJ_Domain_Clinical_Extraction_Architecture_v1.0.md)
- [MRJ Radiology Intelligence Pack v1.0](docs/domain/radiology/MRJ_Radiology_Intelligence_Pack_v1.0.md)
- [MRJ Clinical Journey UX Architecture v1.0](docs/design/MRJ_Clinical_Journey_UX_Architecture_v1.0.md)
- [MRJ Seven-Stage Contracts v1.0](docs/contracts/MRJ_Seven_Stage_Contracts_v1.0.md)

Every document is **ACCEPTED — R0 RADIOLOGY HORIZONTAL ARCHITECTURE CHECKPOINT**. R0 now governs horizontal Radiology implementation while remaining subordinate to the frozen UNDERSTAND v1 authority. It fixes ownership between PROTECT-produced `PatientAnalyticContext` and EXTRACT-assembled `CommonClinicalContext`; confines `RadiologyFinding` to current observations; keeps R2 V0 deliberately small; defines pre-standardization `MRJClinicalConcept`; requires structured/versioned Collection definition and membership; guarantees report-level Clinical V0 without demographics; governs duplicate analytical contributions; and defers statistical association testing. The accepted UNDERSTAND Single + Batch workspace and current Phase 1 PROTECT foundation remain the implemented baselines. Public Health is unchanged and outside this active implementation track.

Roadmap: R0 architecture/contracts/UX (**accepted and closed**) → R1 PROTECT Single + Batch journey integration → R2 Radiology EXTRACT V0 → R3 Radiology STANDARDIZE V0 → R4 Radiology Collection V0 → R5 ANALYZE V0 → R6 VISUALIZE V0 → R7 INDICATORS V0 → real-report Radiology Horizontal Acceptance. **R1 implementation has not started.** MedGemma remains future-compatible and is not required for R1. The last verified regression remains **966 passed, 8 warnings, 0 failures** and was not rerun for this documentation-only acceptance closure.

## MRJ Website Experience / Cinematic Hero V1 — Closed

The accepted `/app` renderer uses `frontend/assets/video/mrj-kling-cinematic.mp4` as the primary cinematic Hero. The full native SVG/Web-Animations scene remains preserved for direct rollback and automatic fallback. Reduced-motion environments receive its static final composition; media/autoplay failure selects the native renderer; no-JavaScript presentation retains the meaningful static native scene. The video is decorative, muted, inline, control-free, one-shot, viewport-paused while incomplete, and held on its final frame.

Desktop navigation is **How MRJ Works → Radiology → Public Health → Privacy & Governance**. Page order is **Hero → MRJ Journey → Radiology/Public Health → Multi-Engine Intelligence → Governance → remaining value and closing sections**. The Hero has one enlarged **Explore the Journey** action targeting `#journey`; local native SVG illustrations distinguish Radiology and Public Health without exposing legacy branding. Final desktop container geometry removes the unnecessary top band and gives the headline/video stronger first-viewport presence while preserving complete video content and bounded tablet/mobile behavior. No frontend dependency, route, API, backend, clinical, `/understanding`, or `/privacy` behavior changed. Closure verification: focused homepage **2 passed, 48 deselected, 1 warning**; full regression **950 passed, 8 warnings, 0 failures**.

## UNDERSTAND Single + Batch Journey Foundation — Accepted Checkpoint

**Human acceptance date:** 2026-09-15.

`/understanding` now presents **Single Report** and **Batch Reports** as explicit first-class modes in one compact clinical workspace. Single mode preserves paste/upload, the authoritative recognition/context result, and the existing one-document Privacy Protection handoff. Batch mode accepts up to 10 TXT, DOCX, or text-based PDF reports, validates a visible pre-queue, processes them sequentially, preserves request order and stable document IDs, isolates unsupported/empty/extraction failures, and supports safe retry of failed items.

The additive, process-local `JourneyRun` contract represents single or batch mode across the unchanged seven stages, with per-document/per-stage status, stage history, results, warnings, review state, errors, and aggregate counts. It is an explicit POC boundary: capacity-bounded, sliding-TTL (30 minutes), non-durable, lost on restart, and free of raw clinical-content persistence in browser storage. Each batch item delegates to the same extraction, `DocumentUnderstandingService`, `MedNexusDocumentContext`, and serialization path as a single report; no second classifier or reasoning route exists.

A **Report** is one clinical document with its own seven-stage journey. A **Journey Run** is a processing event containing one or more reports, and a **Batch Run** is a multi-report Journey Run. A future **Report Collection** is a separate persistent analytical cohort that may combine reports originating from different Single or Batch Runs; it is not the Batch Run itself.

**ACCEPTED CHECKPOINT.** One shared Report Card serves Single and the selected Batch report. Domain/type/modality occupy one identity header; body region, contrast and language form a compact grid with at most one additional useful study-family or acquisition item. Missing context is not guessed. Structure remains visible as compact chips; only plain-language Recognition Evidence is expandable. Technical Details and the third/duplicate Active Report column are absent from the normal UI. Batch uses a compact four-metric strip, 30/70 navigator/detail desktop layout, stacked mobile presentation, and one full card regardless of batch size. Request-bound activity, meaningful UNDERSTAND counters and quiet “Not Started” future stages replace ambiguous progress. Final typography gives the batch title 600-weight authority and the metric numbers stronger weight than their labels, while preserving the warm MRJ paper/cream, charcoal and restrained teal system. The configured font stack remains `"Mona Sans", "Segoe UI", Arial, sans-serif`; no font asset or dependency was added. Single PROTECT and all retained Batch results are preserved; Batch PROTECT remains unavailable and Report Collection remains future architecture. This consolidation changes no backend clinical behavior, JourneyRun architecture, recognition, reference data, API contract, privacy behavior, `/app`, or `/privacy` code.

Final acceptance verification: focused UNDERSTAND/Journey checks **74 passed, 1 warning** in **36.19s**; fresh full regression **966 passed, 8 warnings, 0 failures** in **96.21s**. During consolidation, only `US_CT_01.pdf`–`US_CT_05.pdf` from the already-authorized external InfoBay CT set were re-run: all HTTP 200, Radiology / CT, 100% high confidence and Complete; **5 analyzed, 5 recognized, 5 high-confidence, 0 needs-review, 0 failed**. The single CT and five batch results were passed into the production frontend renderer using a lightweight DOM contract (not a browser simulator); every navigator and previous/next handler selected the correct retained report, with five compact navigator cards and one full card. CT report 02 has no backend contrast value, so none is invented in the UI. Synthetic contracts also cover ten compact cards, review/failure views, bounded metadata, mode switching and absent/partial-run counters. No clinical vocabulary or recognition rules changed. Human review accepted the resulting functional and visual workspace.

## Prior checkpoint records — historical context

The records below retain their original dates, product names, counts, scope and then-current next steps. Their MedNexus branding and former visual direction do not override the MRJ decision above; older “pending” and “not implemented” descriptions are checkpoint snapshots, not a replacement for current source code or the latest accepted implementation baseline.

## UI/UX Design Blueprint v1.0 — Accepted Design Checkpoint

The M0 architecture/documentation checkpoint is complete at `081e8b178f63850beb18f41a09494452aeacc4fc`. Human design review accepted [MedNexus UI/UX Design Blueprint v1.0](docs/design/MedNexus_UI_UX_Design_Blueprint_v1.0.md) as the M1 design direction. It preserves MEDNEXUS⁷ and the frozen architecture authority while defining a Mona Sans, light/Oak, clinically readable product system with Radiology visually primary, Public Health secondary, and UNDERSTAND/PROTECT treated as clinical workspaces rather than marketing pages.

No frontend HTML, CSS, JavaScript, route, API, backend, test, dependency, font, model, or clinical behavior changed in this checkpoint. The current frontend remains the working implementation baseline. The next active step is a visual Landing Page prototype/mockup for human review before production frontend implementation. The approved later order is `UX foundation → Landing → UNDERSTAND → PROTECT → responsive/accessibility/regression polish`.

## Multi-Engine Medical Intelligence Strategy v1.1 — Accepted Architecture Checkpoint

**Status:** ACCEPTED ARCHITECTURE STRATEGY CHECKPOINT — v1.1. No multi-engine runtime implementation is authorized or claimed. The current accepted [Multi-Engine Medical Intelligence Strategy v1.1](docs/architecture/MedNexus_Multi_Engine_Medical_Intelligence_Strategy_v1.1.md) updates current priority, the MedGemma experiment state, hardware sequencing, UI direction, and roadmap while remaining subordinate to the frozen UNDERSTAND v1 authority package below. The accepted [Strategy v1.0 predecessor](docs/architecture/MedNexus_Multi_Engine_Medical_Intelligence_Strategy_v1.0.md) remains the immutable historical M0 checkpoint.

MedNexus is evolving toward a model-agnostic, multi-engine clinical-intelligence platform while preserving MEDNEXUS⁷: `UNDERSTAND → PROTECT → EXTRACT → STANDARDIZE → ANALYZE → VISUALIZE → INDICATORS`, with INGEST internal to UNDERSTAND. The governing principle is **“Models generate evidence. MedNexus determines authority.”** External engines remain replaceable candidate contributors; MedNexus continues to own routing, semantic roles and eligibility, privacy, arbitration, abstention, confidence, provenance, clinical contracts, terminology standardization, persistent structured data, analytics, visualization, indicators, and human-review decisions.

The proposed MedNexus Medical Intelligence Gateway supplies a future vendor-neutral engine boundary and capability registry. MedGemma is a planned candidate engine only. MedUAG and the wider unified medical understanding-and-generation class remain `WATCH` / benchmark / future-adapter candidates pending independent verification of model and code availability, licensing and commercial rights, reproducibility, hardware, security/privacy, and MedNexus-specific validation. The planned MedNexus Evidence Fusion & Arbitration layer will not use model confidence or cross-engine agreement as clinical truth. Future Radiology image-report concordance remains review-oriented until clinically validated and appropriately governed.

Current product concentration is `RADIOLOGY` first and `PUBLIC_HEALTH` second. Radiology should reach strong end-to-end maturity before broad multi-engine expansion to other clinical domains. The immediate acceptance constraint is insufficient authorized real-world Radiology data, not synthetic regression. Real clinical reports remain the primary acceptance benchmark; synthetic reports remain secondary for adversarial, abstention, controlled-conformance, and stress testing.

The strategy now defines a cross-cutting PROTECT-owned Engine Data-Access Preflight before any external engine receives clinical input. It authorizes a specific data exposure, engine/version, execution context, and stage/capability without completing Stage 02 PROTECT or reordering MEDNEXUS⁷; local execution alone is not compliance. Future engine approvals bind to reproducible artifacts, adapters, contracts, configurations, terms, validation scope, and use scope. Fusion is stage-scoped and acyclic, with evidence lineage/correlation controls and a strict distinction between raw engine confidence and MedNexus-calibrated support. Future Image-Report Concordance has five review-safe outcomes, including `INDETERMINATE`, and cannot automatically rewrite reports or create clinical facts.

PROTECT remains the MedNexus-owned policy boundary; EXTRACT remains source-grounded and terminology-independent; STANDARDIZE remains the governed terminology authority. No external engine may directly establish authoritative document identity, persistent clinical facts, privacy decisions, terminology mappings, analytics, or indicators.

Current accepted working regression baseline: **950 passed, 8 warnings, 0 failures**. It was not re-run or changed by this documentation task. MedNexus is awaiting responses or sample information from external real-world Radiology dataset providers; no approval, delivery, price, sample count, or acquisition result is inferred.

## MedGemma Technical Spike M1.1 — Safely Paused

The accepted historical [M1.1 checkpoint](docs/experiments/MedNexus_MedGemma_Technical_Spike_M1.1.md) records `google/medgemma-1.5-4b-it`, official version `1.5.0`, as the exact planned candidate model. “M1.1” is the historical experiment identifier from the prior strategy sequence, not milestone M1 in the accepted Strategy v1.1 roadmap; controlled resumption is roadmap M6. The experiment is **safely paused at the Hugging Face access/terms gate**; this is not an inference failure. Authenticated access had not completed, so no immutable revision SHA was obtained or guessed.

No Colab GPU was allocated, model loaded, clinical inference run, local model/dependency installed, PHI used, or unopened holdout inspected. A100/L4 availability, CUDA, PyTorch, Transformers, resolved model/processor classes, VRAM, and latency remain unmeasured. No fallback model, quantization, dtype, GPU, or unofficial checkpoint was substituted.

The planned current loading path uses `AutoProcessor` and `AutoModelForImageTextToText`, pins the future immutable revision, loads BF16 with `device_map="auto"`, and uses deterministic `do_sample=False`; it remains unexecuted. Secure resumption requires accepted HAI-DEF terms, a fine-grained read-only token stored only as Colab Secret `HF_TOKEN`, and complete model/runtime/terms provenance.

`MG-RAD-CANDIDATE-v0.2` remains experimental and unintegrated. It returns exact evidence quotes without model-calculated offsets. MedNexus grounds each quote against the exact canonical source string as `GROUNDED`, `GROUNDING_FAILURE`, or `AMBIGUOUS_GROUNDING`, with no Unicode, whitespace, punctuation, or newline normalization and no silent quote repair or first-occurrence selection. Candidate roles remain bounded to `CURRENT_STUDY`, `RECOMMENDATION`, `COMPARISON`, `HISTORY`, `FINDINGS`, and `UNRESOLVED`.

After a harmless smoke succeeds, the first planned clinical candidate is the previously exposed and accepted de-identified `D:\MedNexus\Validation_Input\cr_chest.pdf`; it was not opened or submitted in this task. The previously considered Open-I paired case remains blocked pending clear case-level reuse/license terms. No MIMIC-CXR material was used.

M0 architecture/documentation and M1 UI/UX Design Blueprint v1.0 remain accepted; the Landing/Cinematic Hero V1 and UNDERSTAND Single/Batch workspace checkpoints are now closed. PROTECT/DE-ID UX, later responsive/accessibility work, hardware migration, controlled MedGemma resumption, generic engine integration, benchmarking, fusion, imaging, concordance, UAG-class evaluation, and Radiology analytics remain separately authorized roadmap states, not implementation claims.

## UNDERSTAND Domain Matrix v1.0 — Frozen Architecture Authority

UNDERSTAND is the first MedNexus processing stage after upload or pasted-text intake; INGEST remains its internal intake/parsing operation. Its bounded responsibility is `Document → Domain → Subdomain/Modality (or OTHER) → small high-value routing context → semantic document structure and relationships → provenance/confidence → readiness for PROTECT and EXTRACT`. UNDERSTAND is not a mini-extractor.

The **FROZEN UNDERSTAND v1 Architecture Authority**, human-approved on 23 August 2026, is [MedNexus UNDERSTAND Domain Matrix v1.0](docs/architecture/MedNexus_UNDERSTAND_Domain_Matrix_v1.0.md), the current [Blueprint v2.0](docs/architecture/MedNexus_Enterprise_Architecture_and_Engineering_Blueprint_v2.0.docx), [Architecture Crosswalk v2.0](docs/architecture/contracts/MedNexus_Architecture_Crosswalk_v2.0.md), [Clinical Semantic Context Contract v0.2](docs/architecture/contracts/MedNexus_Clinical_Semantic_Context_Contract_v0.2.md), and [Clinical Extraction Contract v0.2](docs/architecture/contracts/MedNexus_Clinical_Extraction_Contract_v0.2.md). Architecture authority does not imply implementation completion.

The approved target domain catalog is `RADIOLOGY`, `PUBLIC_HEALTH`, `LABORATORY`, `ADMISSION`, `DISCHARGE`, `ICU`, and `EMERGENCY`. `PATHOLOGY` is planned/future. Radiology and Public Health are the current full implementation priorities; the remaining approved domains are architecture scope rather than claims of complete implementation. Every implemented domain must resolve a supported subdomain or `OTHER`, never guess an unsupported subtype.

The current code has not yet been migrated to that complete catalog: it still exposes compatibility-era `PATHOLOGY` and combined `ADMISSION_DISCHARGE`, has no independent `ICU`, and does not yet provide `OTHER` consistently across domains. Those are implementation differences, not authority for the future taxonomy.

UNDERSTAND v1 may expose only three or four reliable, high-value context items per subdomain when they help PROTECT, EXTRACT, or routing. Its conceptual output is Document Identity, Light Context Metadata, Semantic Structure, Semantic Relationships, Provenance/Review Requirement, and Routing readiness. It may identify document-level context such as modality, body region, contrast, semantic regions, recommendation presence, or measurement-bearing content. It must not emit lesion sizes, diagnoses, numeric measurements, extracted disease entities, recommendation text, vaccine lot/dose/manufacturer, or analyte results; those are EXTRACT responsibilities.

Frozen human decisions: native immunization/vaccination documents use `PUBLIC_HEALTH / IMMUNIZATION`; Nuclear Medicine uses `PLANAR`, `SPECT`, `PET`, `SPECT_CT`, `PET_CT`, and `OTHER` study families beneath `NUCLEAR_MEDICINE`; diagnostic fluoroscopic reports use `RADIOLOGY / FLUOROSCOPY`, while image-guided intervention remains `RADIOLOGY / OTHER` until a future family is designed; and Laboratory-derived Surveillance requires native Public Health surveillance/reporting identity plus laboratory-derived context.

MedNexus Main/Codex owns UNDERSTAND, PROTECT, core contracts/foundations, and shared platform semantics. Claude/Claude Code Domain Intelligence owns downstream domain-specific EXTRACT, STANDARDIZE implementation, ANALYZE, VISUALIZE, and INDICATORS. Public Health remains the downstream reference vertical; future Radiology extraction may consume the stabilized UNDERSTAND contract without moving extraction into UNDERSTAND.

Latest verified Radiology UNDERSTAND v1 Core Migration regression: **872 passed, 8 warnings, 0 failures**.

## Radiology UNDERSTAND v1 Core Migration Checkpoint

**Status:** MILESTONES 1–4 ACCEPTED. **Architecture:** FROZEN. **Implementation:** PARTIALLY MIGRATED.

The migrated core has one authoritative `RadiologyUnderstandingDecision`. `RadiologyReasoner` executes once per UNDERSTAND operation; `DocumentClassifier` consumes that decision for cross-domain arbitration; and `DocumentContextBuilder` performs mechanical serialization only. Current-study context is semantic-role-qualified, and confidence uses explicit eligibility categories for current identity, document composition, context-only evidence, and unresolved/non-authoritative evidence. Recommendation, comparison, history, and findings-only secondary context remains preserved without inflating performed-study identity support.

The canonical Radiology taxonomy is `CT`, `MRI`, `X_RAY`, `ULTRASOUND`, `MAMMOGRAPHY`, `NUCLEAR_MEDICINE`, `FLUOROSCOPY`, and `OTHER`. Implemented/conformed families are currently `CT`, `MRI`, `X_RAY`, and `ULTRASOUND`, with compatibility normalization `CTA → CT`, `MRA/MRV → MRI`, `Doppler → ULTRASOUND`, and `CR/DX/XR → X_RAY`. Context remains bounded to frozen-matrix document metadata and does not emit diagnoses, lesions, exact measurements, recommendation text, or other EXTRACT-level facts.

Pending implementation migration: Mammography, Nuclear Medicine, Fluoroscopy, the complete `RADIOLOGY / OTHER` policy, frontend canonical-contract migration, and the final validation matrix. Blueprint v2.0 and the frozen UNDERSTAND v1 contracts remain the architecture authority and were not revised by this implementation checkpoint.

## UNDERSTAND v1 Successor Contract Baseline

**Status:** FROZEN ARCHITECTURE AUTHORITY; implementation remains controlled and incremental. **Date:** 23 August 2026.

The successor artifacts are [MedNexus Architecture Crosswalk v2.0](docs/architecture/contracts/MedNexus_Architecture_Crosswalk_v2.0.md), [MedNexus Clinical Semantic Context Contract v0.2](docs/architecture/contracts/MedNexus_Clinical_Semantic_Context_Contract_v0.2.md), and [MedNexus Clinical Extraction Contract v0.2](docs/architecture/contracts/MedNexus_Clinical_Extraction_Contract_v0.2.md). Crosswalk v1.1 and the v0.1 contracts remain preserved as the 16 August 2026 historical baseline.

The authoritative MEDNEXUS⁷ journey is `01 UNDERSTAND → 02 PROTECT → 03 EXTRACT → 04 STANDARDIZE → 05 ANALYZE → 06 VISUALIZE → 07 INDICATORS`. INGEST is an internal operation within UNDERSTAND, not an independent transformation.

UNDERSTAND will progressively produce a bounded typed `MedNexusClinicalContext`: a generic semantic core with backward-compatible domain extensions. It describes document identity, small routing context, and semantic regions/relationships; it must not become field-level EXTRACT. Untyped attributes remain only a controlled compatibility escape hatch.

Document-domain taxonomy is independent of the consuming application vertical. Frozen `PUBLIC_HEALTH` families are Notifiable Disease, Immunization, Surveillance, Syndromic Surveillance, Outbreak/Cluster, Laboratory-derived Surveillance, and `OTHER`. Native patient laboratory reports remain `LABORATORY`; consumption by a Public Health workflow does not change their source-document identity. Laboratory-derived Surveillance requires both native Public Health surveillance/reporting identity and laboratory-derived context.

PROTECT remains the frozen Phase 1 policy/governance boundary. A future `ProtectionContext` / Protected Execution Envelope may govern protected text, raw-text access (`ALLOWED`, `DENIED`, or `RESTRICTED`), policy identity, transformations, permissions, and provenance; this full envelope is not implemented. Dates require future semantic privacy roles such as event, report, specimen collection, result, administration, and birth. Consequently, `MEDNEXUS_ANALYTICS_PUBLIC_HEALTH` is not approved for real production Public Health use until date semantics are resolved.

EXTRACT produces terminology-independent clinical facts, entities, and observations with per-field confidence/provenance. Mapping failure must not alter extraction recognition or confidence. Future contract terminology is `document_review_required` and `extraction_review_required`; current implementation names remain supported until a backward-compatible migration. STANDARDIZE exclusively owns terminology/code mapping, including ICD, LOINC, SNOMED CT, RadLex, CVX, and UCUM where appropriate.

Development proceeds in parallel: Track A (MedNexus Main/Core) owns bounded UNDERSTAND, PROTECT, core contracts/foundations, and shared platform semantics; Track B (Claude/Claude Code Domain Intelligence) owns downstream domain-specific EXTRACT, STANDARDIZE implementation, ANALYZE, VISUALIZE, and INDICATORS. Radiology and Public Health are the current UNDERSTAND implementation priorities. Public Health remains the downstream reference vertical, and no scope statement is a production-readiness claim.

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

The implemented compatibility classifier currently exposes Radiology, Pathology, Laboratory, Emergency, Admission/Discharge, Public Health, and Unknown. This historical implementation statement is qualified by the approved target catalog above. Results include type/subtype, language, major section ranges, confidence, explainable evidence, symbolic routing, metadata, and warnings. `UNKNOWN` and low confidence are intentionally valid.

## Phase 2 Accepted Document Context & Journey Foundation Checkpoint

**Status: ACCEPTED DOCUMENT CONTEXT & JOURNEY FOUNDATION CHECKPOINT.** Accepted commit: `fa1a8ba68d66a3d40f40c8af3bf644f3b909191a`. Previous Phase 2 checkpoints are `a1e8ff2` (foundation) and `551be07` (foundation documentation synchronization). Phase 1 remains frozen at `3486c206085652e2edac2574d277ff0970e037e2`.

The canonical public target journey is `01 UNDERSTAND → 02 PROTECT → 03 EXTRACT → 04 STANDARDIZE → 05 ANALYZE → 06 VISUALIZE → 07 INDICATORS`. INGEST remains an internal technical operation within UNDERSTAND: file/text intake, extraction/parsing, and `DocumentContent` construction. `MedNexusDocumentContext` is the reusable semantic handoff between stages. UNDERSTAND produces document identity, structure, clinical context, privacy context, processing context, and provenance while preserving unknown values as null/unknown.

The current POC flow is `Upload once → INGEST → UNDERSTAND → MedNexusDocumentContext → Continue to Privacy Protection → existing Phase 1 privacy pipeline`, without a second upload. The retained source filename and document status remain visible during the handoff.

Recognition Knowledge Layer v1 provides MedNexus-owned multilingual concepts, domain signatures, evidence interpretation, and external-reference provenance, with Radiology as the first reference domain. LOINC Document Ontology, DICOM/Structured Reporting, RSNA RadLex/Playbook/RadReport, SNOMED CT, HL7 CDA/C-CDA, and WHO ICD-10/ICD-11 are reference inputs only. MedNexus owns curation, normalization, recognition signatures, context construction, and decision logic.

Progressive Result Reveal is frontend presentation of a completed authoritative result, not backend streaming. Accepted regression baseline: **742 passed, 8 warnings, 0 failures**.

## Phase 2 Product Integration

`/understanding` is the active standalone Medical Document Understanding & Recognition POC. It supports pasted text and existing TXT/DOCX/text-based PDF ingestion, displays recognition, confidence, sections, evidence, symbolic route recommendations and warnings, and treats UNKNOWN/manual review as a valid outcome. `/app` presents the MRJ Journey first after its Hero, followed by Radiology and Public Health as the primary and strategic application domains.

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

Deferred: broader real medical-report validation, additional real-report privacy edge cases, broader multilingual person/clinician coverage, OCR, production hardening, performance/load validation, formal benchmark expansion, and visual work outside the closed Landing V1 scope. These are not blockers for this POC checkpoint.

## Frontend Checkpoint

The light, warm-ivory MRJ `/app` Website Experience / Cinematic Hero V1 is the accepted Landing implementation baseline. Its cinematic MP4 is primary and its complete native Hero remains the accessibility/error/no-JavaScript fallback. `/understanding` and `/privacy` retain their existing functional working baselines and were not redesigned by this closure.

## Active Parallel Work

Public Health Intelligence is active parallel MedNexus work aligned to the shared journey while retaining domain-specific extraction schemas, analytics, dashboards, and indicators. It is not declared production-complete.

## Current Near-Term Direction

The UNDERSTAND Single + Batch Journey Foundation is accepted and closed. PROTECT/DE-ID redesign and broader responsive/accessibility polish require explicit later authorization. Hardware migration and controlled MedGemma resumption remain later Strategy v1.1 work unless an earlier cloud experiment is explicitly authorized. Dataset-acquisition follow-up continues because sufficient real-world Radiology acceptance data remains the main validation constraint.

OCR, scanned recognition, layout vision, table extraction, advanced clinical extraction, FHIR/HL7, dashboard integration, broad synthetic tuning, and ungoverned external-model integration remain deliberately deferred.

## Privacy Handoff UX Correction

The UNDERSTAND → PROTECT journey now preserves the original uploaded filename in retained `DocumentContent` and presents a compact `/privacy` handoff receipt: document received, reusable context available, no re-upload required, and READY → PROCESSING → PROTECTED lifecycle state. Policy choice remains explicit, “Use another document instead” restores manual input, and standalone `/privacy` behavior is unchanged.

Progressive protected-result presentation paints its first intact chunk immediately, keeps “Show full result” available during reveal, and respects reduced-motion preferences. A localhost-only acceptance switch can force motion without changing production accessibility or the authoritative complete backend result.

Correction verification: focused suite **78 passed, 8 warnings**; full repository regression **742 passed, 8 warnings, 0 failures**. Live Arabic and English browser journeys preserved source filenames, landed at `#workspace`, completed the lifecycle, and produced protected output without re-upload.

## Privacy Handoff UX Correction

The UNDERSTAND → PROTECT journey now preserves the original uploaded filename in retained `DocumentContent` and presents a compact `/privacy` handoff receipt: document received, reusable context available, no re-upload required, and READY → PROCESSING → PROTECTED lifecycle state. Policy choice remains explicit, “Use another document instead” restores manual input, and standalone `/privacy` behavior is unchanged.

Progressive protected-result presentation paints its first intact chunk immediately, keeps “Show full result” available during reveal, and respects reduced-motion preferences. A localhost-only acceptance switch can force motion without changing production accessibility or the authoritative complete backend result.

Correction verification: focused suite **78 passed, 8 warnings**; full repository regression **742 passed, 8 warnings, 0 failures**. Live Arabic and English browser journeys preserved source filenames, landed at `#workspace`, completed the lifecycle, and produced protected output without re-upload.
