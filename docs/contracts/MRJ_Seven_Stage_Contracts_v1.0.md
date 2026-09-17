# MRJ Seven-Stage Contracts

**Version:** 1.0
**Status:** ACCEPTED — R0 RADIOLOGY HORIZONTAL ARCHITECTURE CHECKPOINT
**Date:** 17 September 2026
**Active domain:** Radiology only
**Document type:** Accepted conceptual contract authority; no API or runtime implementation claim

## 1. Purpose

This document defines the accepted V1 conceptual input/output contracts for the seven public MRJ stages and the Report Collection boundary between STANDARDIZE and ANALYZE.

```text
01 UNDERSTAND
  → 02 PROTECT
  → 03 EXTRACT
  → 04 STANDARDIZE
  → [REPORT COLLECTION BOUNDARY]
  → 05 ANALYZE
  → 06 VISUALIZE
  → 07 INDICATORS
```

INGEST is an internal operation within UNDERSTAND. The Collection boundary is an object-building boundary, not an eighth stage.

These contracts are subordinate to the frozen UNDERSTAND v1 authority package. They preserve the existing Semantic Context Contract v0.2 and Extraction Contract v0.2 and do not claim implementation.

### 1.1 Authority relationship

This document is authoritative within the accepted R0 package for formal stage input/output contracts, stage-level ownership boundaries, and the Collection boundary contract. The Domain Clinical Extraction Architecture owns `CommonClinicalContext`, `MRJClinicalConcept`, Domain Intelligence Pack, and Extraction Profile principles. The Radiology Intelligence Pack owns the exact `RadiologyFinding` schema, Radiology analytical deduplication, and Radiology analytics contracts. This document references those owned definitions rather than redefining them independently.

## 2. Contract conventions

### 2.1 Common identifiers

All stage outputs should carry, as applicable:

- `journey_run_id`
- `report_id`
- `source_document_version`
- `stage_execution_id`
- `stage_contract_version`
- `created_at`
- `producer_id/version`
- `input_references[]`
- `policy/access_context_reference`
- `warnings[]`
- `provenance`

Collection-centric outputs additionally carry `collection_id` and `collection_version`.

### 2.2 Shared state

```text
NOT_STARTED
QUEUED
PROCESSING
COMPLETE
NEEDS_REVIEW
FAILED
BLOCKED
```

The state is recorded at `Report + Stage` and run/collection aggregate levels. Each transition retains timestamp, reason, actor/system identity, and prior state.

### 2.3 Missing-value semantics

When relevant, fields distinguish:

```text
KNOWN
UNKNOWN
NOT_AVAILABLE
NOT_APPLICABLE
RESTRICTED
```

Missing never means false, zero, negative, normal, or complete.

### 2.4 Review semantics

- `document_review_required` belongs to UNDERSTAND/process context.
- `extraction_review_required` belongs to EXTRACT fact/field context.
- `mapping_review_required` belongs to STANDARDIZE.
- Collection/analysis review belongs to eligibility, method, coverage, or denominator governance.

An aggregate notice may summarize these states but must preserve their distinct cause and provenance.

### 2.5 Authority

Candidate engines may contribute evidence. MRJ owns grounding, eligibility, role qualification, validation, conflict resolution, stage completion, review routing, persistence, and final outputs.

## 3. Internal INGEST operation

INGEST is not a public contract/stage. It performs intake and parsing within UNDERSTAND.

### 3.1 Input

```text
SourceInput
  pasted_text OR uploaded_file
  source_filename (optional)
  media_type
  intake_metadata
```

### 3.2 Internal output

```text
DocumentContent
  text
  source_type
  source_filename
  extraction_metadata
  warnings
  provenance
```

Supported current ingestion remains TXT, DOCX, and text-based PDF. OCR/scanned-PDF processing is not implied.

## 4. Stage 01 — UNDERSTAND

### 4.1 Input

```text
RawDocument
  DocumentContent
  report_id
  source_document_version
  intake_provenance
```

### 4.2 Output

```text
DocumentContext
  document_identity
    domain
    subdomain_or_family
    document_type
    language
    confidence
    confidence_band
    document_review_required
  light_context
  semantic_regions[]
  semantic_relationships[]
  privacy_context
  processing_context
    protect_readiness
    extraction_profile_recommendation
    supported_next_capabilities[]
  provenance
  warnings[]
```

The current concrete migration base remains `MedNexusDocumentContext` conforming to Semantic Context Contract v0.2.

### 4.3 Preconditions

- A canonical `DocumentContent` representation exists.
- The source format is supported or fails clearly.
- No downstream stage has redefined document identity.

### 4.4 Invariants

- Known domain + unsupported/unsafe family resolves to `OTHER`.
- Unknown domain resolves to `UNKNOWN` and review.
- Light context remains bounded by the Domain Matrix.
- Recommendation, comparison, history, and findings-only evidence cannot override current-study identity.
- No detailed clinical facts, exact measurements, diagnoses, or terminology codes are emitted as authoritative output.

### 4.5 Completion and continuation

`COMPLETE` requires a valid context, including safe `OTHER` where applicable. `NEEDS_REVIEW` may carry a valid context but can restrict downstream profile resolution. Eligible reports in the run continue independently.

## 5. Stage 02 — PROTECT

### 5.1 Input

```text
ProtectInput
  RawDocument
  DocumentContext
  selected PolicyDefinition/PolicyProfile
  purpose_of_use
  execution_context
```

### 5.2 Accepted target output envelope

```text
ProtectOutput
  ProtectedDocument
  PatientAnalyticContext
  ProtectionResult
  ProtectionProvenance
```

The envelope is conceptual. Current Phase 1 output remains authoritative until an accepted implementation introduces compatible objects.

### 5.3 ProtectedDocument

```text
ProtectedDocument
  report_id
  protected_text
  output_version
  selected_policy_id/version
  transformations_applied[]
  warnings[]
  integrity/provenance
```

MRJ constructs the final protected text. External-engine de-identified text is non-authoritative.

### 5.4 PatientAnalyticContext

`PatientAnalyticContext` is produced only by PROTECT. This accepted optional target object carries only policy-permitted analysis-safe patient context:

```text
PatientAnalyticContext
  pseudonymous_subject_key (optional)
  age (optional)
  age_band (optional)
  sex (optional)
  safe_time_context (optional)
  generalized_geography (optional)
  facility_context (optional)
  field_state_and_provenance
```

No listed derivation/generalization is claimed as implemented. Unsupported fields remain `UNKNOWN`, `NOT_AVAILABLE`, `NOT_APPLICABLE`, or `RESTRICTED`; they are never simulated.

EXTRACT may consume this object but may not rediscover/recreate removed identifiers, derive a prohibited substitute, or override any PROTECT decision. `PatientAnalyticContext` is not interchangeable with `CommonClinicalContext`.

### 5.5 ProtectionResult

```text
ProtectionResult
  status
  policy_id/version
  accepted_decisions[]
  protected_entity_category_summary
  review_required
  warnings[]
```

### 5.6 ProtectionProvenance

Records source representation, policy/profile, intelligence-core version, detector candidates, MRJ decisions, actions, output-builder version, timestamps, and integrity references without exposing restricted PHI unnecessarily.

### 5.7 Invariants

- Reuse the authoritative Phase 1 pipeline.
- Do not create a second privacy-decision path.
- OpenMed remains candidate-only.
- `PolicyTransformer` and `KeepEntityProtector` remain outside the authoritative service path.
- Protection preserves clinical utility only as policy and implemented capability permit.
- EXTRACT may receive raw text only under an explicit future access decision; local execution alone is not authorization.

### 5.8 Completion and continuation

Reports blocked by policy/access do not proceed. Reports with valid protected output may continue independently. Review state must describe whether downstream processing is allowed, restricted, or paused.

## 6. Stage 03 — EXTRACT

### 6.1 Input

```text
ExtractInput
  ProtectedDocument
  DocumentContext
  PatientAnalyticContext (optional; produced by PROTECT)
  resolved Radiology Extraction Profile
  policy/access context
  domain pack version
```

### 6.2 Internal logical layers

```text
EXTRACT
  ├── Common Context Extraction
  └── Domain Clinical Extraction
```

Both remain within Stage 03. They do not create additional public stages.

Common Context Assembly produces:

```text
CommonClinicalContext
  = DocumentContext
  + PatientAnalyticContext
  + approved common non-domain facts established during EXTRACT
```

`CommonClinicalContext` is downstream analytical context assembled by EXTRACT. It preserves the ownership and provenance of each source field and cannot reverse a privacy decision.

### 6.3 Output

```text
RadiologyClinicalFacts
  report_id
  inherited_document_identity
  common_clinical_context
  findings[]: RadiologyFinding
  comparison_facts[]: ComparisonFact (future/deferred)
  recommendation_facts[]: RecommendationFact (future/deferred)
  extraction_coverage
  extraction_review_required
  warnings[]
  extraction_profile_id/version
  domain_pack_id/version
  evidence_and_provenance
```

### 6.4 Preconditions

- Authoritative Radiology identity and routing context exist.
- PROTECT/access permits the exact input.
- The Radiology pack and profile versions are available.
- `UNKNOWN` has not been silently converted into Radiology.

### 6.5 Invariants

- Facts are terminology-independent.
- Output is constrained by the extraction profile.
- Every accepted populated field has source evidence/provenance.
- Missing is not false.
- Recommendation, comparison, history, and current findings remain role-separated.
- `RadiologyFinding` contains only a current clinical observation/finding; recommendation/history/comparison text does not enter `findings[]`.
- Extracted concepts use `MRJClinicalConcept` and do not require an external terminology mapping.
- External output enters as `ClinicalEvidenceCandidate`, not an authoritative fact.
- EXTRACT does not reclassify the document or choose privacy policy.

### 6.6 Partial output

An extraction may be `PARTIAL` with valid known facts and explicit unknowns. One unknown attribute does not invalidate unrelated supported fields. Unsafe facts are rejected/reviewed without fabricating replacements.

### 6.7 R2 Horizontal V0 boundary

R2 requires current `RadiologyFinding` objects with concept, assertion/presence/negation, source section, exact evidence span, confidence, provenance, and validation/review state. It targets anatomy, body region, laterality, certainty, severity, and measurement/unit where directly available.

Complex associated-finding graphs, causal graphs, advanced temporal graphs, full comparison graphs, recommendation linkage graphs, and morphology relationship graphs are deferred. The complete future schema is not an R2 acceptance requirement.

## 7. Stage 04 — STANDARDIZE

### 7.1 Input

```text
StandardizeInput
  RadiologyClinicalFacts[]
  Radiology Intelligence Pack version
  terminology binding profile
  active terminology source metadata
```

### 7.2 Output

```text
StandardizedRadiologyResult
  standardized_facts[]
  terminology_mappings[]
  unit_normalizations[]
  standardization_coverage
  validation_state
  mapping_review_required
  warnings[]
  provenance
```

### 7.3 Standardized fact

```text
StandardizedRadiologyFact
  source_fact_id
  unchanged_extraction_assertion
  canonical_representation
  terminology_bindings[]
  standardized_measurements[]
  mapping_status
  mapping_confidence
  review_state
  provenance
```

### 7.4 Terminology binding

```text
TerminologyBinding
  mrj_concept_reference
  vocabulary
  concept_id
  preferred_term
  vocabulary_version
  mapping_method
  mapping_confidence
  mapping_status
  validation_state
  source_evidence_span
  generating_engine
  validator
  reference_artifact_provenance
```

### 7.5 Invariants

- STANDARDIZE is domain-aware, not text cleanup.
- `MRJClinicalConcept` is a valid EXTRACT output before mapping; `TerminologyBinding` is an additive STANDARDIZE result.
- Mapping failure never erases a fact or changes extraction confidence.
- `UNMAPPED`, `AMBIGUOUS`, and `NEEDS_REVIEW` are valid governed outcomes.
- Only active, licensed/approved, versioned reference sources may be authoritative mappings.
- External identifiers do not replace MRJ fact IDs or source evidence.

### 7.6 Completion and continuation

A report may be eligible for selected analyses with partial standardization if the applicable analytics contract allows it. Coverage and exclusions must remain explicit.

## 8. Report Collection boundary

The Collection boundary consumes report-level intelligence and produces a persistent analytical cohort.

### 8.1 Input

```text
CollectionBuildInput
  eligible StandardizedRadiologyResult[]
  source JourneyRun/BatchRun references
  collection_definition_id
  collection_definition_version
  structured clinical scope
  inclusion_criteria[]
  exclusion_criteria[]
  policy and subject-linkage context
```

### 8.2 Output

```text
RadiologyCollection
  collection_id
  collection_name
  version
  collection_definition_id
  collection_definition_version
  clinical_scope
    domain
    document_type
    modality (optional)
    body_region (optional)
    procedure_or_study_family (optional)
    time_window (optional)
  inclusion_criteria[]
  exclusion_criteria[]
  source_run_ids[]
  report_ids[]
  included_report_ids[]
  exclusions[]
  membership_snapshot
  membership_digest
  subject_identity_mode
  unique_subject_count (optional)
  eligible_report_count
  extraction_coverage
  standardization_coverage
  pack/profile/version compatibility
  created_at
  provenance
```

### 8.3 Invariants

- A BatchRun is not automatically a Collection.
- A free-text collection name is not a clinical definition; structured scope and versioned criteria govern membership.
- Inclusion/exclusion is explicit and traceable.
- `membership_snapshot` and `membership_digest` bind an analysis to the exact cohort membership.
- Unknown subject count is not zero.
- Collection modification creates a new version.
- Existing analyses/indicators remain bound to the exact earlier version.
- Mixed runs are allowed only when their contracts/versions are compatible or intentionally reconciled.

## 9. Stage 05 — ANALYZE

### 9.1 Input

```text
AnalyzeInput
  RadiologyCollection
  selected analytics_contracts[]
  analysis parameters
  method/version
```

### 9.2 Output

```text
ClinicalAnalysisResult
  analysis_id
  analysis_type
  clinical_question
  level
  collection_id/version
  numerator (optional)
  denominator (optional)
  result_values
  method/version
  eligibility_criteria
  exclusions
  data_coverage
  uncertainty/confidence (optional)
  source_fact/profile versions
  warnings/review_state
  provenance
```

### 9.3 Initial Radiology analyses

**Required Clinical V0 — standardized report-level facts only:**

- Finding frequency
- Finding co-occurrence
- Anatomy × finding distribution
- Measurement distribution when measurements exist
- Severity distribution when severity exists

**Enhanced Clinical V0 — optional privacy-safe context:**

- Age-stratified report-level finding frequency
- Sex-stratified report-level finding frequency

**Patient-level — optional safe stable subject linkage:**

- Patient-level finding prevalence under an explicit denominator and time window

Only analyses whose declared input contract is satisfied may run.

Required Clinical V0 must complete when age, sex, and subject linkage are unavailable. Association-strength/statistical testing, recommendation-rate analysis, and advanced temporal analysis are future milestones, not Horizontal V0 requirements.

### 9.4 Analytical deduplication

For report-level finding frequency, each eligible report contributes at most one positive contribution per standardized clinical finding concept under the indicator definition. The same finding repeated in Findings and Impression counts as one positive report while both evidence spans remain preserved.

Report-level co-occurrence first reduces each concept to presence/absence per eligible report before counting concept pairs. Patient-level contribution follows the indicator definition and time window; detailed patient deduplication is deferred but cannot be left to accidental row-count behavior.

### 9.5 Scientific invariants

- Count, frequency, prevalence, co-occurrence, association, and causation are distinct.
- Level is explicit: report, patient, collection, or population.
- Report frequency cannot be labeled patient/population prevalence.
- Patient analyses require safe valid subject linkage.
- Population claims require an appropriate population denominator.
- Association requires a named suitable method.
- Causation is never inferred from retrospective report association alone.
- MRJ may preserve a source-authored causal assertion as `SOURCE_ASSERTED_CAUSAL_RELATION`; that does not make MRJ the source of a causal conclusion.
- Odds ratio, chi-square, Fisher exact testing, regression, confounder adjustment, and statistical-significance testing are future advanced analytics.
- Missing values and exclusions remain visible.

### 9.6 Completion and continuation

Ineligible analyses return explicit ineligibility, not zero. Other eligible analyses may continue. A `ClinicalAnalysisResult` is immutable with respect to its source collection version and method version.

## 10. Stage 06 — VISUALIZE

### 10.1 Input

```text
VisualizeInput
  ClinicalAnalysisResult[]
  presentation context
  accessibility preferences
```

### 10.2 Output

```text
VisualizationModel
  visualization_id
  visualization_type
  title/subtitle
  source_analysis_id/version
  collection_id/version
  level
  dimensions
  series
  labels
  denominator/coverage annotations
  uncertainty annotations
  accessibility_description
  tabular_alternative
  warnings
  provenance
```

Potential types include frequency chart, age/finding heatmap, sex/finding distribution, co-occurrence matrix, finding network, measurement distribution, and temporal trend.

### 10.3 Invariants

- VISUALIZE renders analysis; it does not create new clinical analysis.
- The view cannot change the numerator, denominator, level, exclusions, or uncertainty.
- Source analysis and collection version remain visible/traceable.
- Accessible non-visual alternatives are required.
- Empty or ineligible results are explained, never represented as clinical zero.

## 11. Stage 07 — INDICATORS

### 11.1 Input

```text
IndicatorInput
  RadiologyCollection
  ClinicalAnalysisResult[]
  approved indicator definitions[]
```

### 11.2 Output

```text
ClinicalIndicatorSet
  collection_id/version
  indicators[]
  generation_version
  coverage_summary
  warnings/review_state
  provenance
```

```text
ClinicalIndicator
  indicator_id/version
  name
  definition
  clinical_meaning
  category
  numerator
  denominator
  eligibility_criteria
  exclusions
  unit
  level
  time_window
  value
  uncertainty/confidence (optional)
  source_analysis_ids[]
  source_collection_id/version
  data_coverage
  provenance
```

### 11.3 Categories

- `CLINICAL` — primary product value.
- `DATA_QUALITY` — secondary support.

### 11.4 Invariants

- An indicator must have a versioned definition.
- Numerator and denominator are explicit when the measure requires them.
- The level and clinical scope are explicit.
- The indicator cannot introduce a fact absent from governed upstream data.
- Changed collection membership or indicator definition creates a new version/result.
- Large-number presentation does not replace definition, coverage, and provenance.

## 12. Stage handoff matrix

| From | To | Required handoff | Forbidden shortcut |
|---|---|---|---|
| Internal INGEST | UNDERSTAND | Canonical `DocumentContent` | Parallel parser as semantic authority |
| UNDERSTAND | PROTECT | `RawDocument` + authoritative `DocumentContext` | Privacy engine reclassifies document |
| PROTECT | EXTRACT | Protected/permitted representation + context + policy/access provenance | Extractor bypasses policy or invents raw access |
| EXTRACT | STANDARDIZE | Terminology-independent typed facts + evidence/provenance | Terminology success required for fact existence |
| STANDARDIZE | Collection | Eligible standardized facts + coverage/version | Treat BatchRun as cohort automatically |
| Collection | ANALYZE | Versioned eligible cohort + analysis contract | Direct uncontrolled free-text analysis as authoritative |
| ANALYZE | VISUALIZE | Immutable analysis results | Hidden calculations inside visualization |
| ANALYZE/Collection | INDICATORS | Approved definition + exact inputs | KPI without governed numerator/denominator/scope |

## 13. ClinicalEvidenceCandidate boundary

All optional engines contribute through a generic candidate envelope:

```text
ClinicalEvidenceCandidate
  candidate_id
  target_profile_id/version
  proposed_fact_type/field/value
  verbatim_evidence
  MRJ-grounded source_span
  semantic_region/role
  assertion
  engine_id/version
  adapter_contract_version
  raw_engine_confidence
  correlation_family
  grounding_state
  provenance
  warnings
```

The candidate is not a stage output. It is an input to MRJ validation/arbitration inside the applicable stage.

## 14. Reference and terminology contract

The reference roles are:

- DICOM — imaging/study context and metadata/privacy reference.
- RadLex — Radiology concepts, anatomy, findings, and radiology-specific semantics.
- RadReport — structured reporting/template guidance.
- LOINC/RSNA Playbook — study/procedure/document identity and normalization.
- SNOMED CT — broader clinical representation/mapping.
- FHIR DiagnosticReport — report-level interoperability representation.
- FHIR Observation — atomic observation interoperability representation.
- UCUM — measurement-unit representation/normalization.

Reference matches establish what a concept can mean, not its role in this document. MRJ semantic-role and eligibility decisions remain authoritative.

## 15. Provenance chain

The complete chain should permit:

```text
Indicator
  → Analysis Result
  → Collection ID/version
  → Standardized Fact + terminology binding
  → Extracted Domain Fact
  → MRJ-validated evidence candidate(s)
  → exact source evidence span
  → Protected/permitted document representation
  → authoritative DocumentContext
  → source Report/version
```

Where policy restricts disclosure, the lineage remains auditable without exposing disallowed content.

## 16. Versioning and reproducibility

Each stage execution pins:

- stage contract version
- domain pack and extraction profile versions
- engine/adapter versions and exact configuration
- active reference/terminology versions
- policy/access version
- source document version
- validation/method version
- input object IDs and digests where appropriate

Reprocessing creates a new stage execution/result. It does not overwrite audit history silently.

## 17. Failure isolation and horizontal continuation

| Failure/uncertainty | Required behavior |
|---|---|
| One report cannot be understood | Review/OTHER/UNKNOWN; continue eligible reports |
| One attribute cannot be extracted | Explicit unknown/partial; continue valid fields |
| One candidate cannot be grounded | Reject/review candidate; do not repair it silently |
| One terminology mapping fails | Preserve extracted fact as `UNMAPPED`; continue |
| One report is excluded from collection | Record reason; continue eligible cohort |
| One analysis is ineligible | Explain ineligibility; run other eligible analyses |
| One visualization cannot render | Preserve analysis result; offer accessible fallback |
| One indicator lacks denominator | Do not calculate it; explain missing requirement |

## 18. Security and privacy constraints

- Clinical documents and engine output are untrusted data, never system instructions.
- Raw clinical data exposure requires explicit policy/access authorization.
- External engine access requires the accepted PROTECT-owned Engine Data-Access Preflight when applicable.
- Provenance/logging must not leak restricted identity.
- Protected output remains MRJ-owned.
- This contract does not represent the future Protected Execution Envelope as implemented.

## 19. Implementation-state labels

| Capability | State at this checkpoint |
|---|---|
| UNDERSTAND Single + Batch | Accepted current implementation |
| Phase 1 privacy engine | Accepted/frozen POC foundation |
| PROTECT journey Single + Batch integration | Proposed R1 |
| Radiology EXTRACT V0 | Proposed R2 |
| Radiology STANDARDIZE V0 | Proposed R3 |
| Radiology Collection V0 | Proposed R4 |
| ANALYZE V0 | Proposed R5 |
| VISUALIZE V0 | Proposed R6 |
| INDICATORS V0 | Proposed R7 |
| MedGemma participation | Planned/future; unavailable locally; non-blocking |

## 20. Contract conformance criteria

Human review accepted these contracts on 2026-09-17. Future implementation conforms only when it preserves:

1. Stage ownership matches frozen architecture.
2. UNDERSTAND remains bounded.
3. PROTECT reuses the authoritative privacy path.
4. EXTRACT is domain-specific and terminology-independent.
5. STANDARDIZE owns mappings.
6. Collection is a versioned boundary object, not a stage or batch synonym.
7. ANALYZE uses declared scientific contracts.
8. VISUALIZE performs no hidden analysis.
9. INDICATORS are governed and denominator-aware.
10. Candidate engines remain non-authoritative.
11. Partial/unknown/review/failure states support safe horizontal continuation.
12. Required Clinical V0 completes without demographics or patient linkage.
13. The minimum real chain reaches structured facts, standardized facts, a clinically scoped collection, report-level analyses, visual models, and governed indicators without fake values.

## 21. Acceptance and implementation gate

R0 accepted these conceptual contracts on 2026-09-17. They govern future implementation but do not themselves change runtime schemas, APIs, persistence, frontend behavior, privacy semantics, clinical reasoning, or test expectations. R1 is the next checkpoint and has not started.
