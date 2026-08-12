# MedNexus Engineering Constitution

## 1. Project Identity

MedNexus is an existing, continuing enterprise healthcare AI project. Never treat a new Codex or chat session as a new MedNexus project.

- Platform identity: Enterprise Medical Document Intelligence Platform
- Current functional module: Medical Document Intelligence — Clinical Privacy Policy Engine / De-identification
- Current Phase 1 status: functionally complete end-to-end POC, pending final real-document acceptance validation

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
- Current documented baseline: 671 passed, 8 warnings, 0 failures.
- Change the baseline only after a fresh verified full test run.
- `.pytest_cache` is never authoritative.
- Synthetic or controlled validation is not production certification.

## 8. Git Rules

Before proposing completion, inspect `git diff`, `git status`, and confirm that only intended files changed. Never commit or push unless explicitly authorized. Preserve a clean `main` at approved checkpoints.

## 9. Documentation Synchronization

After meaningful approved implementation milestones, assess whether `README.md`, `BUILD_HISTORY.md`, `TECH_DEBT.md`, the Enterprise Architecture Blueprint, and validation documentation need synchronization. Preserve historical entries instead of rewriting history. Clearly distinguish implemented, validated, planned, and technical-debt states.

## 10. Clinical Privacy and Safety

- Privacy failures take precedence over cosmetic output issues.
- Do not remove clinical vocabulary merely because an external detector labels it as PHI.
- Clinician and staff names must follow MedNexus policy and contextual-role logic, not blanket name removal.
- Rejected or unresolved candidates must not silently corrupt clinical text.
- Never weaken a privacy rule merely to make a test pass.
- Never claim clinical or production certification without appropriate validation evidence.

## 11. Current Roadmap Boundary

Do not implement future stages merely because they appear in architecture documents. Planned capabilities include Document Understanding, Clinical Extraction, Terminology Services, Structured Data, Analytics, OCR, interoperability, and enterprise infrastructure.

The enterprise target document journey is Ingest → Understand → Protect → Extract → Standardize → Analyze → Visualize → Indicators. This is a target architecture, not an implementation claim. Capabilities must remain modular and independently usable while sharing contracts that allow participation in the full journey.

Public Health Intelligence is active parallel domain work aligned to the shared journey, but must not be described as production-complete without implementation and validation evidence.

The current `/app` and `/privacy` frontend experience is an accepted working baseline, not final brand or visual polish. Do not reopen deferred cosmetic design work unless explicitly requested.

The immediate next milestone is representative real-document acceptance validation of the Clinical Privacy Policy Engine, followed by appropriate regression confirmation and a verified Phase 1 baseline freeze.
