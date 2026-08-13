# MedNexus Current State

**Authoritative date:** 13 August 2026

## Current Platform State

MedNexus is an Enterprise Medical Document Intelligence Platform. Its target journey is Ingest → Understand → Protect → Extract → Standardize → Analyze → Visualize → Indicators. Capabilities are modular, independently usable, and connected through shared platform contracts.

## Phase 1 Status

**Phase 1 — Accepted POC Checkpoint / Paused.** The Clinical Privacy Policy Engine has reached its accepted architecture and synthetic-validation checkpoint. It is not production-ready, exhaustively validated, or clinically certified.

## Current Functional Capability

Medical Document Intelligence — Clinical Privacy Policy Engine / De-identification is functional end to end, and Medical Document Understanding & Recognition has an accepted standalone foundation. `/app` is the enterprise homepage; `/privacy` is the functional privacy POC.

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

## Known Limitations / Deferred Validation

Deferred: broader real medical-report validation, additional real-report privacy edge cases, broader multilingual person/clinician coverage, OCR, production hardening, performance/load validation, formal benchmark expansion, and remaining frontend visual refinements. These are not blockers for this POC checkpoint.

## Frontend Checkpoint

The current Deep Teal Hybrid `/app` and `/privacy` experience is an accepted working baseline. Minor visual refinements are intentionally deferred.

## Active Parallel Work

Public Health Intelligence is active parallel MedNexus work aligned to the shared journey while retaining domain-specific extraction schemas, analytics, dashboards, and indicators. It is not declared production-complete.

## Next Development Direction

**Phase 2 Recognition Validation — Round 1.** Validate the current foundation using a small representative set spanning Radiology, Pathology, Laboratory, Emergency, Admission, Discharge, Public Health, and ambiguous/UNKNOWN documents. Review domain, type, subtype, language, sections, confidence, evidence, and routing before expanding the classifier or frontend.

OCR, scanned recognition, layout vision, table extraction, universal or ML/transformer/LLM classifiers, external classification, embeddings, advanced clinical extraction, FHIR/HL7, frontend/dashboard integration, and broad synthetic tuning remain deliberately deferred.
