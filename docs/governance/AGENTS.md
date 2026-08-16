# MedNexus Engineering Constitution

## 1. Project Identity

MedNexus is an existing, continuing enterprise healthcare AI project. Never treat a new Codex or chat session as a new MedNexus project.

- Platform identity: Enterprise Medical Document Intelligence Platform
- Current functional modules: Clinical Privacy Policy Engine / De-identification and Medical Document Understanding & Recognition
- Current Phase 1 status: Accepted POC Checkpoint / Paused; synthetic baseline frozen at 681 passed, 8 warnings, 0 failures
- Current Phase 2 status: Accepted Document Context & Journey Foundation Checkpoint at `fa1a8ba68d66a3d40f40c8af3bf644f3b909191a`; baseline 742 passed, 8 warnings, 0 failures

## 2. Workspace and Git Boundary

- Workspace root: `D:\MedNexus`
- Git repository: `D:\MedNexus\07_Source_Code`
- Run Git commands only against `07_Source_Code`.
- Never initialize Git at `D:\MedNexus` or move, recreate, or replace the existing `.git`.
- Material outside `07_Source_Code` may govern architecture, requirements, validation, research, datasets, and project context.

## 3. Sources of Truth

Use this precedence:

1. Implemented behavior: current source code and tests.
2. Architecture principles and roadmap: latest Enterprise Architecture & Engineering Blueprint, qualified by current code for implementation status.
3. Current implementation summary: `07_Source_Code/README.md`.
4. Engineering chronology/current milestone: latest current-state section of `07_Source_Code/BUILD_HISTORY.md`.
5. Technical debt: `07_Source_Code/backend/TECH_DEBT.md`.
6. Validation corpus and expected PHI: current validation dataset README and manifests.

Historical documents, diagrams, archives, `.venv`, caches, and `.pytest_cache` never override current code or current-state documentation.

## 4. Locked De-identification Architecture

- OpenMed is external, replaceable, and a candidate detector only.
- Never use OpenMed `deidentified_text` as authoritative final output.
- External-engine entities must pass through MedNexus adapters and contracts.
- MedNexus owns canonicalization, role resolution, context validation, false-positive rejection, overlap/conflict merging, policy/privacy decisions, and final de-identified output construction.
- Preserve the integrated Intelligence Core. Do not create parallel or split privacy-decision pipelines.
- Treat De-identification as a Clinical Privacy Policy Engine: Detection → Unified Intelligence → Purpose-Based Policy Engine → MedNexusOutputBuilder → MedNexus-owned output.
- Purpose-of-use policies and regulatory frameworks are separate concepts. Future custom or institutional policies must reuse the same unified pipeline.
- Current implemented policy transformations are KEEP, REPLACE, HASH, MASK, and REMOVE. Never present GENERALIZE, SHIFT_DATE, derivation, geographic reduction, pseudonymization/tokenization, privacy–utility assessment, residual re-identification risk assessment, or the Custom Policy Builder as implemented until code and validation prove it.

Current major components: `MedNexusCandidateEntity`, `EntityCanonicalizer`, `OpenMedCandidateAdapter`, `RoleResolver`, `ContextValidator`, `DetectionMerger`, `MedNexusIntelligenceOrchestrator`, `MedNexusOutputBuilder`, and `DeterministicIdentifierDetector`.

## 5. Current Ingestion Boundary

Implemented: TXT, DOCX, text-based PDF, the unified document extraction contract, extractor registry/factory, file-processing service, and upload/de-identification path.

Not implemented: OCR/scanned-PDF processing and an image extraction pipeline. Do not describe future formats or capabilities as implemented until code and tests prove them.

## 6. Engineering Change Rules

Before changing code, inspect the implementation, understand the architecture, check relevant tests and current technical debt, prefer minimal architecture-preserving changes, and never silently remove existing functionality.

Classify new bugs when possible under detection, canonicalization, role resolution, context validation, merging, policy, output construction, or ingestion/extraction. Prefer generalized deterministic or canonical rules over accumulating report-specific regex patches. Preserve exact source offsets wherever candidate spans depend on them.

## 7. Testing Rules

- Run focused tests for the modified component first where appropriate.
- Run the full regression suite before declaring a coding task complete.
- Phase 1 frozen baseline: 681 passed, 8 warnings, 0 failures.
- Current verified repository baseline: 780 passed, 8 warnings, 0 failures.
- Change the baseline only after a fresh verified full test run.
- `.pytest_cache` is never authoritative.
- Synthetic or controlled validation is not production certification.

## 8. Git Rules

Before proposing completion, inspect `git diff`, `git status`, and confirm that only intended files changed. Never commit or push unless explicitly authorized. Preserve a clean `main` at approved checkpoints.

## 9. Documentation Synchronization

Documentation synchronization is mandatory at every meaningful implementation checkpoint. Review relevant state, build history, architecture/status documentation, validation documentation, and Blueprint version before moving to the next major stage. Preserve historical entries instead of rewriting history and clearly distinguish implemented, validated, planned, and technical-debt states.

## 10. Clinical Privacy and Safety

- Privacy failures take precedence over cosmetic output issues.
- Do not remove clinical vocabulary merely because an external detector labels it as PHI.
- Clinician and staff names must follow MedNexus policy and contextual-role logic, not blanket name removal.
- Rejected or unresolved candidates must not silently corrupt clinical text.
- Never weaken a privacy rule merely to make a test pass.
- Never claim clinical or production certification without appropriate validation evidence.

## 11. Current Roadmap Boundary

Document Recognition knowledge must remain MedNexus-owned, offline, explainable, and domain-modular. External standards and terminologies may inform provenance and interoperability mapping, but must not become authoritative runtime classifiers or silently replace curated multilingual concepts and MedNexus recognition signatures. New domain knowledge should use stable concept identifiers, explicit evidence roles, conservative multi-signal signatures, and traceable reference families.

A real validation failure must be corrected by improving reusable knowledge, normalization, context, or reasoning logic. Never add report-specific rules merely to make one validation document pass.

Validation reports are not knowledge sources. New recognition concepts, aliases, mappings, or relationships require independent justification from an authoritative reference or a reusable MedNexus normalization rule. External terminology licensing, version, provenance, distribution, and activation state must remain explicit; restricted source content must never be committed without verified permission.

`MedNexusDocumentContext` is the shared semantic handoff for one ingested document. UNDERSTAND constructs context; PROTECT applies privacy decisions to the original document informed by context where supported; EXTRACT will later create formal structured clinical data; STANDARDIZE will normalize extracted concepts. Never collapse these stages or duplicate `DocumentContent`, privacy detection, or clinical extraction inside the context layer. Unknown context must remain null/unknown rather than inferred without evidence.

Do not implement future stages merely because they appear in architecture documents. The Phase 2 deterministic Understanding foundation is implemented; its next milestone is Recognition Validation — Round 1. Planned capabilities include expanded Document Understanding, Clinical Extraction, Terminology Services, Structured Data, Analytics, OCR, interoperability, and enterprise infrastructure.

The public MEDNEXUS⁷ journey is Understand → Protect → Extract → Standardize → Analyze → Visualize → Indicators. INGEST remains a real internal technical operation inside UNDERSTAND, covering file/text intake, extraction/parsing, and `DocumentContent` construction; it is not a separate public transformation. This is a target architecture, not a claim that all seven stages are implemented. Capabilities must remain modular and independently usable while sharing contracts that allow participation in the full journey. `MEDNEXUS⁷` is a visual/product signature only; internal code, APIs, packages, routes, and repositories remain `MedNexus`.

The approved cross-domain context direction is a generic typed `MedNexusClinicalContext` core with backward-compatible typed domain extensions. Untyped attributes are a controlled escape hatch, not the primary contract. UNDERSTAND describes document identity and semantic/clinical contexts; it must not perform field-level EXTRACT. EXTRACT produces terminology-independent facts with per-field provenance/confidence, and STANDARDIZE owns terminology mapping. Mapping failure must never change extraction recognition or confidence.

Document domains describe source-document semantics, not consuming applications. Public Health as a vertical is not equivalent to `DocumentDomain.PUBLIC_HEALTH`: patient laboratory reports remain `LABORATORY`, immunization records use independent `IMMUNIZATION`, and notifiable-disease/surveillance documents may use `PUBLIC_HEALTH`.

PROTECT is a policy/governance boundary, not unconditional destructive redaction before EXTRACT. The future Protected Execution Envelope and semantic date-role privacy model are planned contracts, not implemented capabilities. `MEDNEXUS_ANALYTICS_PUBLIC_HEALTH` must not be represented as approved for real production Public Health use until semantic date handling is resolved.

Core and Domain Intelligence workspaces remain operationally separate. Temporary domain detection is bootstrap logic and must not become a competing classifier. An Integrated Domain Checkpoint requires canonical-contract conformance, including `MedNexusDocumentContext` where applicable. Create a Cross-Track Sync Brief when shared architecture/contracts change, either track reaches a stable checkpoint, cross-track dependencies or impacts arise, or before integration; routine internal changes without shared-contract impact do not require one.

Public Health Intelligence is active parallel domain work aligned to the shared journey, but must not be described as production-complete without implementation and validation evidence.

Authoritative terminology distributions and normalized local reference stores belong under `D:\MedNexus\Reference_Data`, outside Git. Acquisition must use official sources and respect authentication, license, attribution, and redistribution constraints. Runtime reference resolution must remain offline, versioned, checksum-verifiable, provenance-preserving, and subordinate to MedNexus-owned canonical IDs and reasoning. Never invent cross-standard mappings or learn production terminology from frozen validation reports.

An external source is ACTIVE only after its real artifact is imported, checksum-verified, normalized and explicitly activated. Referenced identifiers from an inactive terminology (for example SNOMED codes carried by DICOM DCMR) remain provenance mappings, not active terminology concepts. Frozen validation must remain closed until the authorized reference-population set is complete.

The current `/app` and `/privacy` frontend experience is an accepted working baseline, not final brand or visual polish. Do not reopen deferred cosmetic design work unless explicitly requested.

Phase 1 synthetic tuning is intentionally paused at the accepted POC checkpoint. Broader validation will resume later using real medical reports. Do not expand Phase 2 beyond the authorized milestone or reopen synthetic edge-case tuning without explicit authorization.
