# MRJ Horizontal Clinical Journey Architecture

**Version:** 1.0
**Status:** ACCEPTED — R0 RADIOLOGY HORIZONTAL ARCHITECTURE CHECKPOINT
**Date:** 17 September 2026
**Active domain:** Radiology only
**Document type:** Accepted architecture authority; implementation requires separately authorized milestones

## 1. Purpose

This document defines the accepted next MRJ development direction: build the first complete, clinically meaningful Radiology journey horizontally across all seven public stages before optimizing any one stage deeply.

```text
REAL RADIOLOGY REPORTS
  → 01 UNDERSTAND
  → 02 PROTECT
  → 03 EXTRACT
  → 04 STANDARDIZE
  → 05 ANALYZE
  → 06 VISUALIZE
  → 07 INDICATORS
```

INGEST remains the internal intake, extraction/parsing, and `DocumentContent` construction operation inside UNDERSTAND. It is not an eighth public stage.

This accepted architecture is additive and subordinate to the frozen UNDERSTAND v1 authority package. It does not change the Domain Matrix, Blueprint v2.0, Architecture Crosswalk v2.0, Semantic Context Contract v0.2, Extraction Contract v0.2, or current production behavior.

## 2. Status and scope

### 2.1 In scope

- A Radiology-only horizontal product architecture.
- Stage ownership and handoff boundaries.
- The report-to-collection transition.
- A shared state model for reports, runs, stages, and collections.
- Clinical and scientific governance for analyses and indicators.
- A model-agnostic evidence architecture.
- A staged R0–R7 implementation roadmap.

### 2.2 Out of scope

- Application, API, database, frontend, backend, or test implementation.
- Reopening UNDERSTAND recognition tuning.
- New privacy-policy semantics.
- Public Health or other domain implementation planning.
- MedGemma integration or any dependency/model installation.
- Production or clinical certification.

Public Health may inform reusable workflow experience, but the active architecture and implementation track described here is Radiology.

### 2.3 Document authority and ownership

The five R0 documents form one package with non-overlapping primary ownership:

| Document | Primary authority within the accepted R0 package |
|---|---|
| `MRJ_Horizontal_Clinical_Journey_Architecture_v1.0.md` | Horizontal development strategy, seven-stage journey invariants, Report → Collection transition, R0–R7 roadmap, and development governance |
| `MRJ_Domain_Clinical_Extraction_Architecture_v1.0.md` | Common Clinical Context architecture, Domain Intelligence Pack contract, Extraction Profile contract, and cross-domain extraction principles |
| `MRJ_Radiology_Intelligence_Pack_v1.0.md` | Radiology-specific clinical schema, `RadiologyFinding`, Radiology reference/terminology usage, deduplication semantics, and Radiology analytics contracts |
| `MRJ_Seven_Stage_Contracts_v1.0.md` | Formal stage input/output contracts, stage ownership boundaries, and the Collection boundary contract |
| `MRJ_Clinical_Journey_UX_Architecture_v1.0.md` | Interaction model, workspace behavior, Journey Rail, and report-centric → collection-centric UX transition |

When a concept is summarized outside its owning document, the owning definition controls. In particular, `RadiologyFinding` must not evolve independently in the stage or UX documents, and stage inputs/outputs must not evolve independently outside the Seven-Stage Contracts. All five remain subordinate to the frozen UNDERSTAND v1 authority package until final human acceptance.

## 3. Product value invariant

MRJ is not primarily a document counter, administrative dashboard, classifier demonstration, or sequence of format conversions. Its principal value is **clinical intelligence derived from medical reports**.

Every stage must do at least one of the following:

1. Preserve clinical meaning.
2. Increase clinical structure.
3. Increase clinical interpretability.
4. Increase scientific usability.
5. Prepare governed data for a defined downstream clinical or scientific purpose.

Counts such as “20 CT reports” may support operations, but they are not the primary clinical outcome. The target value is traceable analysis of findings, anatomy, severity, measurements, relationships, temporal patterns, and governed indicators.

## 4. Horizontal development rule

The accepted development rule is:

> No fine-tuning or stage-depth optimization until the first complete Radiology seven-stage journey is operational.

Only a genuine blocker may interrupt horizontal delivery. A blocker is a defect that prevents safe handoff, corrupts clinical meaning, breaches privacy/governance, creates false authority, or makes a later stage impossible.

Non-blocking uncertainty must remain explicit and allow eligible work to continue:

| Condition | Required representation | Horizontal behavior |
|---|---|---|
| UNDERSTAND cannot establish one report confidently | `NEEDS_REVIEW` or governed `OTHER`/`UNKNOWN` | Continue eligible reports |
| EXTRACT cannot determine one attribute | `UNKNOWN` / `NOT_AVAILABLE` | Retain the fact/evidence that is known; continue |
| STANDARDIZE cannot map one concept | `UNMAPPED` / `NEEDS_REVIEW` | Preserve the extracted fact unchanged; continue |
| One report fails safely | Report-stage `FAILED` | Isolate it; continue eligible reports |
| Privacy or access policy denies processing | `BLOCKED` with reason | Do not process that report beyond the authorized boundary |

This rule forbids endless report-specific tuning loops during horizontal development. It does not weaken safety, privacy, review, or abstention requirements.

## 5. Seven-stage architecture

### 5.1 UNDERSTAND

UNDERSTAND identifies the document and produces bounded routing/context information. It owns document domain, supported subdomain/family or `OTHER`, document type, language, approved light context, semantic regions/relationships, provenance, confidence, review state, and downstream readiness.

It does not emit save-ready findings, diagnoses, exact measurements, recommendation content, or terminology codes. The accepted Single + Batch workspace and authoritative Radiology decision remain unchanged.

### 5.2 PROTECT

PROTECT applies the existing MRJ purpose-based privacy architecture to the source document and governs what downstream processing may receive. It owns privacy decisions and MRJ-owned protected output.

The horizontal architecture requires future handoffs to preserve clinically useful, policy-permitted analytical context without claiming that age derivation, geographic generalization, date shifting, pseudonymization, or a Protected Execution Envelope is currently implemented.

### 5.3 EXTRACT

EXTRACT converts protected, understood Radiology content into terminology-independent, domain-specific clinical facts. It owns detailed findings, source-grounded attributes, evidence spans, confidence, provenance, and extraction review.

It inherits document identity from UNDERSTAND and may not run a competing authoritative classifier. It may produce unknown or partial facts without inventing values.

### 5.4 STANDARDIZE

STANDARDIZE maps extracted facts to governed canonical representations, terminology concepts, and normalized units. It is domain-aware and is not text cleanup.

Mapping failure must not erase an extracted fact or change its extraction recognition/confidence. MRJ canonical field identities remain stable even when external terminology is unavailable.

### 5.5 ANALYZE

ANALYZE operates on a versioned Radiology collection of eligible standardized facts. It produces explicitly defined clinical analyses, including frequencies, stratifications, co-occurrence, distributions, and methods appropriate to the available denominator and evidence.

It may not infer population prevalence, association, or causation without the required method and denominator.

### 5.6 VISUALIZE

VISUALIZE renders governed `ClinicalAnalysisResult` objects. It may select an appropriate view and presentation model but may not silently calculate new clinical facts or analyses.

Every visualization retains collection scope, denominator where applicable, data coverage, and a source-analysis reference.

### 5.7 INDICATORS

INDICATORS produces governed clinical indicator objects with definitions, numerators, denominators, eligibility, exclusions, level, time window, provenance, collection version, coverage, and uncertainty where applicable.

Clinical indicators are the primary value. Data/quality indicators are secondary supporting measures.

## 6. Report, run, batch, and collection

These concepts are not interchangeable.

| Object | Definition | Persistence/identity rule |
|---|---|---|
| `Report` | One atomic clinical document and its stable document identity | Never becomes a run or cohort |
| `JourneyRun` | One processing event across one or more reports and selected stages | Records execution, stage state, timestamps, and outputs |
| `BatchRun` | A `JourneyRun` containing multiple reports | An ingestion/processing grouping, not an analytical cohort |
| `ReportCollection` | A persistent logical analytical cohort of eligible report/subject records | May span runs; is versioned and explicitly curated |

Therefore:

```text
Report != JourneyRun != BatchRun != ReportCollection
```

A future collection may include reports from one batch, several batches, single-report runs, or mixed ingestion events. It must never be inferred solely from upload proximity.

## 7. Report-to-collection boundary

The transition occurs after STANDARDIZE:

```text
REPORT INTELLIGENCE
  standardized report-level facts
        ↓
COLLECTION BOUNDARY
  explicit eligibility + inclusion/exclusion + version
        ↓
COLLECTIVE CLINICAL INTELLIGENCE
  ANALYZE → VISUALIZE → INDICATORS
```

`ReportCollection` / `RadiologyCollection` is a boundary object, not a public stage. Building or updating it is a governed operation between Stage 04 and Stage 05.

### 7.1 Collection V0

The accepted minimum collection contract is:

- `collection_id`
- `collection_name`
- `collection_definition_id`
- `collection_definition_version`
- structured `clinical_scope`:
  - `domain` (`RADIOLOGY`)
  - `document_type`
  - `modality` when relevant
  - `body_region` when relevant
  - `procedure_or_study_family` when relevant
  - `time_window` when relevant
- `inclusion_criteria[]`
- `exclusion_criteria[]`
- `source_run_ids[]`
- `report_ids[]`
- `membership_snapshot`
- `membership_digest`
- `subject_identity_mode`
- `unique_subject_count` when safely and legitimately available
- `eligible_report_count`
- `included_report_ids[]`
- `exclusions[]` with reasons
- `time_window` when safely defined
- `extraction_coverage`
- `standardization_coverage`
- `version`
- `created_at`
- collection provenance and policy context

`collection_name` is a human label, not an analytical definition. A name such as “MRI Knee Cohort” is insufficient without the structured scope and versioned criteria. Unknown or unavailable subject counts and time windows remain explicit; they are not treated as zero.

### 7.2 Versioning

Adding, removing, reprocessing, or changing the eligibility of reports creates a new collection version. Analyses, visualizations, and indicators must identify the exact collection ID and version that produced them.

## 8. Shared state model

The accepted shared state vocabulary is:

```text
NOT_STARTED
QUEUED
PROCESSING
COMPLETE
NEEDS_REVIEW
FAILED
BLOCKED
```

It applies at `Report + Stage` level and at run or collection aggregate level.

### 8.1 State meanings

| State | Meaning |
|---|---|
| `NOT_STARTED` | No stage execution has been requested or made eligible |
| `QUEUED` | Eligible and awaiting execution |
| `PROCESSING` | Real stage work is in progress |
| `COMPLETE` | Required stage output exists and passed its completion gate |
| `NEEDS_REVIEW` | Output exists but requires explicit review before a governed next action |
| `FAILED` | Execution ended without a valid stage output; retry may be possible |
| `BLOCKED` | A policy, prerequisite, dependency, or safety gate prohibits execution |

`NEEDS_REVIEW` is not automatically a failure. `BLOCKED` must name the blocking condition. No stage may display `COMPLETE` merely because an animation finished.

### 8.2 Aggregate state

Aggregate status must derive from real child states and include meaningful counts only after a run or collection exists. Do not show `0/0` placeholders. Aggregate completion does not erase report-level review, failure, or exclusion state.

## 9. Patient Analytic Context and Common Clinical Context

The ownership chain is explicit:

```text
UNDERSTAND → DocumentContext
PROTECT    → PatientAnalyticContext
EXTRACT    → CommonClinicalContext
```

`PatientAnalyticContext` is the privacy-safe, policy-approved patient context produced only by PROTECT. It may carry, when genuinely implemented and permitted:

- pseudonymous subject key
- age or age band
- sex
- event/study date or safe time period
- facility
- generalized geography

EXTRACT assembles `CommonClinicalContext` from:

```text
DocumentContext
  + PatientAnalyticContext
  + approved common non-domain facts established during EXTRACT
```

The resulting downstream analytical context may additionally include:

- source document identity
- document domain/type/language
- provenance and confidence

Fields are optional. Missing values use explicit semantics such as `UNKNOWN`, `NOT_AVAILABLE`, or `NOT_APPLICABLE`; absence never means false.

EXTRACT must not rediscover or recreate identifiers removed by PROTECT, reverse a privacy decision, or treat unavailable privacy-safe context as extractable source data. `CommonClinicalContext` complements domain facts; it is not a universal clinical-finding schema.

## 10. Domain-specific clinical intelligence

MRJ uses this composition:

```text
Common Clinical Context
  + Domain Intelligence Pack
  + Document-Type Extraction Profile
  + Domain-Specific Clinical Facts
```

The first accepted pack architecture is Radiology. Other domain fact types may later exist, but they are cited only to prove extensibility; they are not implementation commitments in this checkpoint.

## 11. Scientific governance

MRJ must label analytical claims precisely.

| Term | Governed meaning |
|---|---|
| Count | Number of qualifying observations at a named level |
| Frequency | Occurrences relative to an explicitly defined eligible denominator |
| Prevalence | Affected units in a defined population and time basis; requires an appropriate denominator |
| Co-occurrence | A and B observed together within a declared unit/window |
| Association | A statistically evaluated relationship using a named method and assumptions |
| Causation | A causal claim requiring a suitable design and evidence; never inferred from retrospective report association alone |

Every result declares its level:

- report-level
- patient-level
- collection-level
- population-level

Report-level finding frequency must not be presented as patient prevalence. Patient-level prevalence requires safe, valid subject linkage. Population prevalence requires a defined population denominator.

### 11.1 V0 analytical levels

**Required Clinical V0** must complete using standardized report-level clinical facts alone. It includes report-level finding frequency, report-level finding co-occurrence, anatomy × finding distribution, measurement distribution when measurements exist, and severity distribution when severity exists.

**Enhanced Clinical V0** is optional and available only when `PatientAnalyticContext` supplies privacy-safe age/age-band or sex. It includes age- and sex-stratified report-level finding frequency.

**Patient-level analytics** are optional and available only when a stable, safe subject key and a governed time window exist. Patient-level finding prevalence is not a prerequisite for first horizontal acceptance.

### 11.2 Analytical deduplication

For report-level finding frequency, each eligible report contributes at most one positive contribution per standardized clinical finding concept under the indicator definition. Repetition of the same finding in Findings and Impression does not create two positive reports. Source facts and evidence remain preserved; deduplication governs analytical contribution rather than deleting facts.

Patient-level contribution is defined by the specific indicator and its time window. Detailed patient deduplication is deferred, but it may never be an accidental consequence of row counts.

## 12. Indicator categories

### 12.1 Clinical indicators — primary

Required Clinical V0:

- Finding Frequency
- Finding Co-occurrence Rate
- Anatomy × Finding Distribution
- Lesion Measurement Distribution
- Severity Distribution

Optional Enhanced Clinical V0:

- Age-stratified Finding Rate
- Sex-stratified Finding Rate

Optional patient-level analytics:

- Patient-level Finding Prevalence, only when safe subject identity, denominator, and time window exist

Follow-up Recommendation Rate by Finding, association strength, and statistical inference are future advanced analytics, not Horizontal V0 requirements. Odds ratios, chi-square, Fisher exact tests, regression, confounder adjustment, and statistical-significance testing are deferred.

### 12.2 Data and quality indicators — secondary

- Extraction Coverage
- Standardization Coverage
- Needs Review Rate
- Report Structure Completeness
- Mapping Confidence/Coverage

Operational processing metrics may exist, but they must not dominate the clinical product proposition.

## 13. Model-agnostic engine architecture

The invariant remains:

> Models generate evidence. MRJ determines authority.

Potential engines include MRJ Native reasoning, deterministic/rule engines, terminology engines, MedGemma, and future foundation models. All must emit bounded candidate evidence through adapters. MRJ owns grounding, eligibility, role qualification, validation, conflicts, arbitration, confidence, abstention, review, persistence, and final stage outputs.

The accepted generic evidence-envelope architecture is `ClinicalEvidenceCandidate`, defined in the Domain Clinical Extraction Architecture. It does not make an external model authoritative.

MedGemma remains planned/future and unavailable in the current local environment. It is not a dependency or blocker for R0–R7. This accepted architecture does not authorize model loading, integration, or inference.

## 14. Continuous journey operation

The preferred user action is **Run Clinical Journey**. Eligible stages advance automatically when real outputs and prerequisites exist. Processing pauses only for:

- human review
- policy decision
- a failure that blocks safe continuation
- a user-requested pause

The journey must remain useful under partial completion. An uncertain report may be isolated while eligible reports continue. Downstream collection eligibility must transparently exclude reports lacking required governed outputs.

## 15. Roadmap

| Milestone | Scope | Exit evidence |
|---|---|---|
| **R0 — Journey Architecture** | Contracts, shared state, report/collection model, UX architecture | **Accepted and closed 2026-09-17** |
| **R1 — PROTECT Journey Integration** | Single + Batch orchestration using the current privacy engine | Real report handoff, truthful state, no duplicate privacy pipeline |
| **R2 — Radiology Clinical EXTRACT V0** | Source-grounded clinically meaningful Radiology facts | Typed facts with evidence/provenance and partial/unknown handling |
| **R3 — Radiology STANDARDIZE V0** | Governed terminology/unit mappings | Mapping provenance, coverage, review, and unmapped preservation |
| **R4 — Radiology Collection V0** | Versioned analytical cohort boundary | Explicit inclusion/exclusion and exact source/version lineage |
| **R5 — Clinical ANALYZE V0** | Governed clinical analyses | Results tied to eligible facts, method, denominator, and collection version |
| **R6 — Clinical VISUALIZE V0** | Rendered analysis models | No hidden analysis; coverage and source-analysis traceability |
| **R7 — Clinical INDICATORS V0** | Governed clinical indicator objects | Definitions, numerator/denominator, scope, version, provenance, uncertainty |

After R7, **Radiology Horizontal Acceptance** requires real Radiology report content to produce real structured facts, standardized records, collection analyses, clinical visualizations, and governed indicators.

The architecture may support future sophistication, but Horizontal V0 implements only the minimum required to complete that real clinical chain. It does not require the entire future `RadiologyFinding` schema, advanced relationship graphs, demographic analytics, patient linkage, or association testing before acceptance.

## 16. Horizontal acceptance rule

Final acceptance must not rely on:

- hard-coded clinical outcomes
- fake findings
- mock indicators
- seeded final dashboard values
- report-specific rules learned from validation cases

Synthetic data may support tests, but it cannot substitute for the real-report horizontal acceptance path. Every final value must be traceable back through governed stage outputs to source evidence and the applicable collection version.

## 17. Architecture invariants

1. The public journey always has seven stages; INGEST stays internal.
2. UNDERSTAND stays bounded and does not become EXTRACT.
3. PROTECT remains the privacy/governance authority.
4. EXTRACT owns terminology-independent domain facts.
5. STANDARDIZE owns authoritative terminology mapping.
6. A batch is never implicitly an analytical collection.
7. ANALYZE does not bypass standardized, eligible data.
8. VISUALIZE renders governed analysis and performs no hidden analysis.
9. INDICATORS are defined, versioned, denominator-aware objects.
10. Missing never means false or zero.
11. Candidate engines never determine MRJ authority.
12. Partial uncertainty is represented, not guessed or silently dropped.

## 18. Acceptance and implementation gate

Human review accepted this document as R0 architecture authority on 2026-09-17. R0 is closed. Acceptance governs future horizontal Radiology implementation but does not itself implement a stage.

- Current accepted UNDERSTAND and PROTECT behavior remains authoritative.
- The frozen UNDERSTAND v1 package remains unchanged.
- R1 — PROTECT Journey Integration is the next checkpoint and has not started.
- R2–R7 remain future separately authorized implementation milestones.
