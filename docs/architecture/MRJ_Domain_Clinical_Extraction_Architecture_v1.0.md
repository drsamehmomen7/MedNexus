# MRJ Domain Clinical Extraction Architecture

**Version:** 1.0
**Status:** ACCEPTED — R0 RADIOLOGY HORIZONTAL ARCHITECTURE CHECKPOINT
**Date:** 17 September 2026
**Active implementation target:** Radiology only
**Document type:** Accepted architecture authority; no runtime implementation claim

## 1. Purpose

This document defines the accepted domain-specific clinical extraction architecture for MRJ. It extends, without replacing, the frozen Clinical Semantic Context Contract v0.2 and Clinical Extraction Contract v0.2.

The governing composition is:

```text
Common Clinical Context
  + MRJ Domain Intelligence Pack
  + Document-Type Extraction Profile
  + Domain-Specific Clinical Facts
```

MRJ must not force all medicine into one universal `ClinicalFinding` schema. Common context is shared where clinically and safely meaningful; detailed facts remain typed by domain.

### 1.1 Authority relationship

This document is authoritative within the accepted R0 package for Common Clinical Context, the Domain Intelligence Pack contract, the Extraction Profile contract, `MRJClinicalConcept`, and cross-domain extraction principles. The Radiology Intelligence Pack owns the Radiology-specific fact schema and analytics contracts; the Seven-Stage Contracts own formal stage input/output shapes. The Horizontal Architecture owns the package-wide authority matrix and roadmap.

## 2. Governing boundaries

1. UNDERSTAND owns bounded document identity and routing context, not detailed clinical facts.
2. PROTECT governs downstream access and MRJ-owned protected output.
3. EXTRACT owns source-grounded, terminology-independent clinical facts.
4. STANDARDIZE owns authoritative terminology and unit mappings.
5. External engines emit candidates only; MRJ validates and determines authority.
6. Missing information is explicit and is never interpreted as false.
7. This accepted architecture does not claim that Radiology EXTRACT or STANDARDIZE is implemented.

## 3. Logical clinical record composition

```text
MRJClinicalRecord
  identity
    report_id
    journey_run_id
    document_context_reference
  common_clinical_context
  domain_clinical_facts[]
  extraction_result
  policy_and_access_context
  provenance
```

The envelope may transport facts across stages, but it does not flatten their domain-specific definitions.

Illustrative future fact families include `RadiologyFinding`, `ImmunizationEvent`, `ReportableDiseaseCase`, and `LaboratoryObservation`. Only Radiology is in scope for the accepted R0–R7 roadmap.

## 4. Patient Analytic Context and Common Clinical Context

These objects have different owners and purposes:

```text
UNDERSTAND produces DocumentContext
PROTECT produces PatientAnalyticContext
EXTRACT assembles CommonClinicalContext
```

`PatientAnalyticContext` contains only policy-approved, privacy-safe patient context produced or retained by PROTECT, such as a permitted pseudonymous subject key, age/age band, sex, safe temporal context, generalized geography, or other approved context. It is optional and every value retains policy/derivation provenance.

EXTRACT assembles `CommonClinicalContext` from:

```text
DocumentContext
  + PatientAnalyticContext
  + approved common non-domain facts established during EXTRACT
```

`CommonClinicalContext` is downstream analytical context. EXTRACT must not rediscover or recreate an identifier removed by PROTECT, derive a prohibited replacement, or override a PROTECT decision. If PROTECT did not provide a privacy-sensitive value, EXTRACT cannot recover it from protected output merely to populate common context.

### 4.1 CommonClinicalContext fields

| Field | Meaning | Required? |
|---|---|---:|
| `subject_key` | Stable pseudonymous key scoped by policy and environment | No |
| `age` | Policy-permitted age at a governed reference time | No |
| `age_band` | Governed derived band with derivation provenance | No |
| `sex` | Source-grounded sex value using an approved representation | No |
| `event_time` | Semantically typed study/event time | No |
| `safe_time_period` | Policy-permitted generalized period | No |
| `facility_context` | Policy-permitted facility identity or class | No |
| `geography_context` | Policy-permitted generalized geography | No |
| `source_document_identity` | Stable reference to the source report | Yes |
| `document_domain` | Domain inherited from UNDERSTAND | Yes |
| `document_type` | Type inherited from UNDERSTAND | Yes |
| `language` | Primary document/clinical language | No |
| `confidence` | Confidence belonging to the specific common-context assertion | No |
| `provenance` | Evidence, method, policy, engine, and version lineage | Yes for populated fields |

The patient-related fields in this table originate from `PatientAnalyticContext`; document identity fields originate from `DocumentContext`; only approved common non-domain facts may be added by EXTRACT.

### 4.2 Missing-value semantics

Optional fields use explicit states:

| State | Meaning |
|---|---|
| `KNOWN` | A supported value exists |
| `UNKNOWN` | The source may contain a value, but MRJ cannot establish it safely |
| `NOT_AVAILABLE` | The necessary source or permitted information is unavailable |
| `NOT_APPLICABLE` | The field does not apply to this record/context |
| `RESTRICTED` | A policy or execution boundary prevents use or disclosure |

`null`, absence, and `UNKNOWN` must never be normalized to `false`, `0`, “normal,” or “not present.”

### 4.3 Privacy boundary

The common layer is not permission to retain identity. Every field must be compatible with the selected privacy policy and the future execution/access envelope when implemented. This architecture does not assert that age bands, generalized geography, safe dates, or pseudonymous subject keys are currently implemented transformations. `PatientAnalyticContext` remains the sole owner of privacy-safe retained/derived patient context; `CommonClinicalContext` consumes it without changing its privacy meaning.

## 5. MRJ Domain Intelligence Pack

An **MRJ Domain Intelligence Pack** is a versioned, MRJ-owned knowledge and contract bundle for one clinical domain.

```text
domain_pack/
  domain_definition
  document_profiles
  extraction_schemas
  terminology_bindings
  validation_rules
  analytics_contracts
```

### 5.1 Required pack contents

1. **Domain definition** — semantic scope, exclusions, supported families, and ownership.
2. **Document profiles** — supported document types and their routing prerequisites.
3. **Extraction schemas** — typed domain facts and field semantics.
4. **Terminology bindings** — permitted vocabularies, versions, mapping roles, and provenance rules.
5. **Validation rules** — evidence, cardinality, internal consistency, and review requirements.
6. **Analytics contracts** — which combinations of fields support which analyses and indicators.

AI or deterministic engines do not define the pack. Engines are replaceable contributors constrained by it.

### 5.2 Pack identity and lifecycle

Each pack requires:

- `domain_pack_id`
- semantic `version`
- status: `PROPOSED`, `ACTIVE`, `DEPRECATED`, or `RETIRED`
- compatible document-context contract versions
- compatible extraction-profile versions
- compatible terminology-source versions
- schema and validation-rule digests
- effective date
- accountable owner
- migration/compatibility notes

A pack version change must not silently reinterpret persisted facts.

## 6. MRJ Extraction Profile Registry

The accepted **MRJ Extraction Profile Registry** architecture resolves a governed extraction profile from authoritative document identity and supported downstream capability.

```text
RADIOLOGY
  RADIOLOGY_REPORT
    version 1.0

PUBLIC_HEALTH
  IMMUNIZATION_REPORT
    future
  NOTIFIABLE_DISEASE_REPORT
    future
```

Only the Radiology profile is in current scope. Future examples demonstrate extensibility, not implementation.

### 6.1 Profile definition

Each profile defines:

- profile ID and version
- owning domain pack
- supported document domain/type/subdomain/family
- prerequisite UNDERSTAND confidence/review conditions
- permitted input representations under PROTECT
- fields/fact types that may be extracted
- field definitions and data types
- cardinality
- optionality
- missing-value semantics
- evidence requirements
- allowed candidate engines/capabilities
- validation rules
- reference standards and terminology-binding targets
- downstream analytical eligibility
- abstention and review behavior
- compatibility and retirement metadata

### 6.2 Resolution rules

1. The registry consumes authoritative UNDERSTAND identity; it does not reclassify the document.
2. `UNKNOWN` cannot select a domain-specific profile automatically.
3. `RADIOLOGY / OTHER` may select a conservative generic Radiology profile only if approved; it may not guess a modality-specific profile.
4. A profile version is pinned per extraction operation and retained in provenance.
5. An unavailable profile yields `BLOCKED` or review; it does not generate arbitrary JSON.

### 6.3 Model constraint

The profile is the output contract presented to any engine. An engine may omit optional values or abstain. It may not add undeclared fields, silently change cardinality, create terminology authority, or return free-form structures as authoritative data.

## 7. MRJClinicalConcept and domain-specific clinical facts

### 7.1 MRJClinicalConcept

`MRJClinicalConcept` is MRJ's pre-standardization representation of what the source report says. It is valid without an external terminology mapping.

```text
MRJClinicalConcept
  label
  source_expression
  semantic_type
  normalization_state
  source_evidence
  confidence
  provenance
```

`normalization_state` describes MRJ-local interpretation, for example `SOURCE_ONLY`, `MRJ_NORMALIZED`, `AMBIGUOUS`, or `UNKNOWN`; it does not claim a RadLex, SNOMED CT, or other external code. `source_evidence` links the concept to the permitted canonical source span.

EXTRACT understands and structures the source into `MRJClinicalConcept` and typed domain facts. STANDARDIZE later attaches one or more `TerminologyBinding` objects. A fact remains valid when mapping is unavailable, ambiguous, or unsuccessful.

### 7.2 Domain-specific clinical facts

A domain fact is a typed assertion owned by the domain pack. It has clinical content plus evidence, confidence, validation, and provenance.

```text
DomainClinicalFact
  fact_id
  fact_type
  source_value
  clinical_concept: MRJClinicalConcept (optional)
  attributes
  source_section
  source_evidence_span
  evidence_candidates[]
  extraction_confidence
  assertion_state
  validation_state
  review_state
  extraction_profile_id/version
  engine_and_method_provenance
```

The Radiology specialization is defined in `MRJ_Radiology_Intelligence_Pack_v1.0.md`.

## 8. ClinicalEvidenceCandidate

`ClinicalEvidenceCandidate` is the accepted vendor-neutral candidate-envelope architecture for MRJ Native, deterministic, terminology, MedGemma, or future engines.

### 8.1 Conceptual fields

| Field | Purpose |
|---|---|
| `candidate_id` | Unique evidence-candidate identity |
| `target_profile_id/version` | Profile that constrains the candidate |
| `proposed_fact_type` | Domain fact type the evidence may support |
| `proposed_field` | Profile-defined field, if field-level |
| `candidate_value` | Non-authoritative proposed value |
| `verbatim_evidence` | Exact source quote where applicable |
| `source_span` | MRJ-grounded offsets; never trusted solely from an external model |
| `semantic_region` | Source region inherited/linked from UNDERSTAND |
| `semantic_role` | Current finding, comparison, history, recommendation, or other governed role |
| `assertion` | Present, absent/negated, uncertain, conditional, or unknown candidate state |
| `engine_id/version` | Exact source engine identity |
| `adapter_contract_version` | Candidate adapter and schema version |
| `engine_confidence` | Raw engine confidence, kept distinct from MRJ confidence |
| `correlation_family` | Prevents duplicated/correlated evidence from being counted as independent |
| `grounding_state` | `GROUNDED`, `GROUNDING_FAILURE`, or `AMBIGUOUS_GROUNDING` where relevant |
| `provenance` | Runtime, artifact, configuration, and operation lineage |
| `warnings` | Candidate limitations or conflicts |

### 8.2 Authority path

```text
Engine output
  → adapter
  → ClinicalEvidenceCandidate
  → exact grounding
  → profile eligibility
  → semantic-role qualification
  → validation and conflict handling
  → MRJ arbitration
  → typed domain fact or abstention/review
```

Candidate evidence is never persisted as an authoritative clinical fact solely because an engine produced it. Raw engine confidence is not MRJ-calibrated support.

### 8.3 Source integrity

- External models return exact evidence quotes, not authoritative offsets.
- MRJ grounds the quote against the canonical permitted source representation.
- Missing or ambiguous grounding cannot become an accepted fact.
- Recommendation, comparison, history, and unrelated sections retain their roles and cannot silently become current findings.
- Clinical text and model output are untrusted data, never instructions.

## 9. EXTRACT logical layers

EXTRACT contains two logical layers under one public stage:

```text
EXTRACT
  ├── Common Context Extraction
  └── Domain Clinical Extraction
```

### 9.1 Common Context Assembly

Assembles `CommonClinicalContext` from `DocumentContext`, the optional `PatientAnalyticContext`, and approved common non-domain facts established during EXTRACT. It preserves source ownership and field-level provenance. It does not duplicate UNDERSTAND identity, rediscover protected identifiers, infer unavailable privacy transformations, or override a PROTECT decision.

### 9.2 Domain Clinical Extraction

Uses the resolved extraction profile and domain pack to produce detailed terminology-independent facts. It retains partial facts and explicit unknowns when profile validation permits them.

## 10. Evidence and provenance

Every populated clinical field should be traceable through:

- source report and version
- source section/semantic region
- exact evidence span where available
- extraction profile ID/version
- candidate engine and adapter version
- candidate grounding state
- MRJ extraction method and validator
- extraction confidence and review state
- policy/access context used for execution
- timestamp and journey-run identity

Provenance is field-level where fields may have different evidence or methods. A document-level provenance object cannot replace this lineage.

## 11. Validation architecture

Validation occurs before a candidate becomes an accepted typed fact.

### 11.1 Validation classes

- Schema and data-type validation
- Cardinality validation
- Evidence/grounding validation
- Semantic-role validation
- Assertion/negation/certainty validation
- Internal relationship validation
- Measurement/unit pairing validation
- Cross-field consistency validation
- Profile/domain eligibility validation
- Privacy/access output validation

### 11.2 Validation states

```text
VALID
PARTIAL
NEEDS_REVIEW
REJECTED
UNKNOWN
```

`PARTIAL` means a useful profile-permitted subset is valid. `REJECTED` evidence is retained for audit where permitted but does not become a fact. Validation may abstain.

## 12. Terminology independence and STANDARDIZE

EXTRACT emits `MRJClinicalConcept` values and typed facts without requiring an external code. It must retain the fact when terminology mapping is unavailable or unsuccessful.

STANDARDIZE owns:

- target terminology selection
- mapping resolution and ambiguity
- code/display/version
- unit normalization using an approved standard
- mapping confidence and review
- terminology license, activation, and provenance

The standardized binding is additive to the extracted fact and does not rewrite source evidence.

## 13. Machine-oriented terminology binding

```text
TerminologyBinding
  binding_id
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
  created_at
```

Recommended `mapping_status` values are `MAPPED`, `PARTIAL`, `AMBIGUOUS`, `UNMAPPED`, `NEEDS_REVIEW`, and `NOT_APPLICABLE`.

An inactive or unlicensed terminology may be carried as source provenance but cannot be represented as an active authoritative mapping.

## 14. Reference roles across the journey

| Reference | Primary accepted role |
|---|---|
| DICOM | Imaging/study context, modality/acquisition reference, privacy/de-identification metadata reference |
| RSNA RadLex | Radiology concepts, anatomy, findings, procedures, and radiology-specific semantic relationships |
| RSNA RadReport | Structured-reporting templates, section expectations, and profile guidance |
| LOINC / RSNA Radiology Playbook | Study/procedure/document identification and standardized procedure relationships |
| SNOMED CT | Broader clinical concept representation and approved mappings |
| HL7 FHIR DiagnosticReport | Report-level interoperability representation |
| HL7 FHIR Observation | Atomic observation/finding interoperability representation |
| UCUM | Measurement-unit representation and normalization |

Reference vocabularies inform governed profiles and STANDARDIZE. They do not determine a concept's semantic role in the source document or replace MRJ reasoning.

## 15. Analytics contracts

Each domain pack declares which validated fields make a downstream analysis eligible.

```text
fact fields + common context + collection eligibility
  → named analytical contract
  → governed result type
```

Example contract layers for Radiology include:

| Layer | Required data | Eligible analysis |
|---|---|---|
| Required Clinical V0 | finding + eligible report denominator | report-level finding frequency |
| Required Clinical V0 | finding A + finding B + shared eligible report | report-level co-occurrence |
| Required Clinical V0 | finding + anatomy | anatomy × finding distribution |
| Required Clinical V0 when values exist | finding + measurement + standardized unit | measurement distribution |
| Required Clinical V0 when values exist | finding + severity | severity distribution |
| Enhanced Clinical V0 | finding + policy-permitted age/age band | age-stratified report-level frequency |
| Enhanced Clinical V0 | finding + policy-permitted sex | sex-stratified report-level frequency |
| Optional patient-level | finding + valid subject key + patient denominator/time window | patient-level finding prevalence |
| Future/advanced | typed recommendation, temporal, or statistical-method inputs | recommendation, temporal, or association analysis |

If a required field or denominator is unavailable, the analysis is ineligible; MRJ does not substitute zero or fabricate an outcome.

Required Clinical V0 must not depend on demographics or patient linkage. Exact Radiology analytical deduplication is owned by the Radiology Intelligence Pack: repeated evidence for the same standardized concept in one report cannot create multiple positive report contributions.

## 16. Extensibility without premature taxonomy

The architecture permits future domain packs without defining them now. Each future pack must supply its own fact types, profiles, validation, terminology bindings, and analytics contracts while conforming to the common evidence/provenance boundary.

No future domain may copy Radiology semantics simply for schema uniformity. Shared concepts belong in Common Clinical Context only when they truly have cross-domain meaning.

## 17. Compatibility and versioning

- Existing `MedNexusDocumentContext` remains the authoritative UNDERSTAND handoff until an accepted compatible successor exists.
- New extraction profiles are additive and version-pinned.
- Persisted facts retain the profile and pack version that defined them.
- Breaking schema changes require a new major version and explicit migration.
- Terminology-version changes do not silently alter prior standardized records.
- An analytics contract pins the fact/profile versions it accepts.

## 18. Implementation sequence dependency

This accepted architecture supports the R0–R7 horizontal roadmap:

1. Accept architecture and contracts.
2. Integrate current PROTECT behavior into the journey.
3. Implement Radiology EXTRACT V0 against a versioned profile.
4. Implement domain-aware STANDARDIZE V0.
5. Build a versioned Radiology Collection.
6. Add governed analyses.
7. Render analysis outputs.
8. Produce governed indicators.

MedGemma is not required for any step. MRJ Native/deterministic implementations may establish the first path while retaining the same candidate contract for future engines.

The architecture may support a sophisticated future schema, but Horizontal V0 implements only the minimum needed for real structured facts → real standardized facts → a real clinically scoped collection → real report-level analysis → real clinical visualizations → real governed indicators. Full relationship graphs, complete future field coverage, demographics, patient linkage, and advanced association testing are not prerequisites.

## 19. Acceptance and implementation gate

Human review accepted this architecture contract on 2026-09-17. It now governs future domain clinical extraction implementation without claiming runtime implementation or clinical readiness. R1 is the next checkpoint and has not started; Radiology EXTRACT remains R2.
