# MRJ Radiology Clinical Fact Contract

**Version:** 1.0
**Status:** ACCEPTED AND CLOSED
**Acceptance date:** 2026-09-24
**Date:** 24 September 2026
**Checkpoint:** R2.0A — Radiology Clinical Fact Contract + EXTRACT UX Contract
**Domain:** `RADIOLOGY`
**Runtime status:** Contract only; Radiology EXTRACT is not implemented

## 1. Purpose and authority

This document refines the minimum scientifically useful Radiology EXTRACT V0 target without reopening the accepted R0 architecture. It is the proposed contract target for R2.0B ground truth, R2.0C evaluation harness, R2.0D benchmark, R2.0E engine decision, and the separately authorized R2 implementation.

The accepted R0 package remains controlling:

- `MRJ_Horizontal_Clinical_Journey_Architecture_v1.0.md` owns horizontal strategy and scientific boundaries.
- `MRJ_Domain_Clinical_Extraction_Architecture_v1.0.md` owns `CommonClinicalContext`, `MRJClinicalConcept`, profiles, and candidate architecture.
- `MRJ_Radiology_Intelligence_Pack_v1.0.md` owns `RadiologyFinding`, Radiology role firewalls, and analytics eligibility.
- `MRJ_Seven_Stage_Contracts_v1.0.md` owns formal stage handoffs.
- `MRJ_Clinical_Journey_UX_Architecture_v1.0.md` owns the continuous workspace.

If this draft conflicts with an accepted R0 boundary, R0 controls until a successor is explicitly accepted. This draft does not change UNDERSTAND, PROTECT, privacy, APIs, persistence, reference data, dependencies, or frontend behavior.

## 2. Clinical target

R2 V0 does not extract generic medical words. It produces source-grounded, terminology-independent Radiology facts that preserve assertion, anatomy, attributes, evidence, and provenance.

```text
Protected/permitted Radiology report
  + authoritative DocumentContext
  + optional PatientAnalyticContext
  + pinned Radiology profile/pack
        ↓
ClinicalEvidenceCandidate[]
        ↓ MRJ grounding, role qualification, validation, arbitration
RadiologyClinicalFactGraph V0
  ├── CommonClinicalContext
  ├── ClinicalContextFact[]
  ├── RadiologyFinding[]
  └── RadiologyFindingRelationship[]
```

The graph is a logical contract, not a graph database requirement. No graph infrastructure is authorized by this document.

## 3. Contract-wide semantics

### 3.1 Missing-value states

Every optional clinical field has a value state when ambiguity matters:

| State | Meaning |
|---|---|
| `KNOWN` | A source-supported value is available. |
| `UNKNOWN` | The value may exist, but MRJ cannot establish it safely. |
| `NOT_STATED` | The source does not state the value in eligible evidence. |
| `NOT_AVAILABLE` | Required source or permitted context is unavailable. |
| `NOT_APPLICABLE` | The field does not apply to this fact. |
| `RESTRICTED` | Privacy or access policy prevents use or disclosure. |

Missing, null, or `UNKNOWN` never means false, absent, normal, bilateral, zero, or complete. Transport implementations may use a typed value-state envelope; they must not discard the distinction above.

### 3.2 Requirement labels

| Label | Contract meaning |
|---|---|
| `REQUIRED` | Needed for an accepted V0 object. |
| `OPTIONAL` | Populated only when directly supported. |
| `UNKNOWN-ALLOWED` | Required semantic slot may explicitly abstain or remain unresolved. |
| `NOT-APPLICABLE-ALLOWED` | The field can truthfully not apply. |

### 3.3 Source roles

Eligible current findings normally originate in Findings/Observation or Impression/Conclusion roles. Indication/history, comparison, recommendation, technique, and authentication evidence retain their source roles and cannot silently become current findings.

## 4. RadiologyFinding V0

`RadiologyFinding` remains the canonical current Radiology observation object. A disease or diagnosis may be a finding, but findings also include lesions, structural or physiological abnormalities, negative observations, and other source-supported clinical observations.

### 4.1 Identity, meaning, and assertion

| Field | Requirement | V0 semantics |
|---|---|---|
| `finding_id` | REQUIRED | Stable identity within one extraction result; not a terminology code. |
| `finding_concept` | REQUIRED | Terminology-independent `MRJClinicalConcept`. |
| `source_expression` | REQUIRED | Verbatim or source-faithful expression tied to eligible evidence. |
| `semantic_class` | REQUIRED | `DIAGNOSIS`, `LESION`, `FINDING`, or `OTHER_CLINICAL_OBSERVATION`. |
| `assertion_state` | REQUIRED | Authoritative presence/negation/uncertainty state. |
| `source_section` | REQUIRED | Canonical semantic section/region. |
| `evidence_span` | REQUIRED | Exact source span and quote in the permitted canonical representation. |
| `extraction_confidence` | REQUIRED | MRJ-calibrated fact confidence, separate from engine confidence. |
| `validation_state` | REQUIRED | `VALID`, `PARTIAL`, `NEEDS_REVIEW`, `REJECTED`, or `UNKNOWN`. |
| `review_state` | REQUIRED | Whether review is required and its governed disposition. |
| `extraction_method` | REQUIRED | MRJ Native, deterministic, external-candidate plus MRJ arbitration, or human-reviewed. |
| `provenance` | REQUIRED | Field/fact lineage defined in Section 10. |

`semantic_class` is a small descriptive V0 classification, not an external terminology mapping and not an invitation to create a universal clinical ontology. `ABNORMALITY` is not an independent V0 class because it overlaps diagnosis, lesion, and finding. Classification must not inflate certainty or determine assertion state.

Operational annotation guidance uses this precedence:

1. `DIAGNOSIS` — an explicitly asserted named disease, pathological condition, or diagnostic assessment.
2. `LESION` — a discrete focal structural lesion when lesion representation is clinically useful and no stronger disease-class representation applies.
3. `FINDING` — another source-supported imaging observation.
4. `OTHER_CLINICAL_OBSERVATION` — safe fallback when the prior classes cannot be applied reliably.

Reviewers classify the source assertion, not an inferred disease vocabulary. If `DIAGNOSIS` and `LESION` appear plausible, the explicitly asserted diagnostic meaning takes precedence; otherwise use the more conservative supported class or review. External terminology mapping remains owned by STANDARDIZE.

### 4.2 Assertion model

`assertion_state` is the single authoritative V0 polarity contract:

| Value | Meaning | Example interpretation |
|---|---|---|
| `PRESENT` | Source asserts the finding is present. | “Right pleural effusion.” |
| `ABSENT_NEGATED` | Source explicitly negates the finding. | “No pleural effusion.” |
| `UNCERTAIN` | Source describes possibility or unresolved uncertainty. | “Possible small pleural effusion.” |
| `CONDITIONAL` | Assertion depends on a stated condition or future confirmation. | A conditional source assertion, preserved without promotion. |
| `UNKNOWN` | MRJ cannot safely resolve the assertion. | Conflicting or insufficient eligible evidence. |

V0 does not add separate boolean `presence` or `negation` fields because they could contradict `assertion_state`. Negation cues and uncertainty language may be retained in evidence/provenance for review. An absent finding remains a real source-grounded fact with `ABSENT_NEGATED`; it must never contribute as a positive finding in later analytics.

## 5. Finding attributes

### 5.1 Anatomy and laterality

| Field | Requirement | Semantics |
|---|---|---|
| `anatomic_site` | OPTIONAL / UNKNOWN-ALLOWED | Specific anatomy bound to this finding. |
| `body_region` | OPTIONAL / UNKNOWN-ALLOWED | Broader finding-level body region. |
| `laterality` | OPTIONAL / UNKNOWN-ALLOWED / NOT-APPLICABLE-ALLOWED | `LEFT`, `RIGHT`, `BILATERAL`, `MIDLINE`, `OTHER`, `UNKNOWN`, or `NOT_APPLICABLE`. |
| `anatomic_qualifiers[]` | OPTIONAL | Source-supported segment, lobe, compartment, level, or subsite. |

Finding anatomy must be linked through shared evidence or an explicit source relation. Anatomy elsewhere in the report is insufficient. Performed-study anatomy inherited from UNDERSTAND remains distinct and cannot be rewritten by a finding's anatomy.

Example conceptual representation:

```text
finding_concept: Intraparenchymal hemorrhage
anatomic_site: Temporal lobe
laterality: RIGHT
```

No RadLex or SNOMED CT code is required at EXTRACT.

### 5.2 Certainty, severity, and attributes

| Field | Requirement | Semantics |
|---|---|---|
| `certainty` | OPTIONAL / UNKNOWN-ALLOWED | Source-supported degree of certainty; does not replace assertion state. |
| `severity` | OPTIONAL / UNKNOWN-ALLOWED | Source-supported severity only. |
| `attributes[]` | OPTIONAL | Bounded source-supported morphology or other profile-declared attributes. |

No default certainty or severity is inferred from omission. V0 uses `HAS_ATTRIBUTE` relations when an attribute must retain its own evidence or identity; simple validated attributes may remain attached fields.

### 5.3 Temporal and change semantics

V0 supports a deliberately small source vocabulary at the contract level without implementing parsing:

- temporal status examples: `ACUTE`, `CHRONIC`, `INDETERMINATE`, `OTHER`;
- change status examples: `NEW`, `STABLE`, `INCREASED`, `DECREASED`, `IMPROVED`, `PROGRESSED`, `RESOLVED`, `UNKNOWN`.

| Field | Requirement | Semantics |
|---|---|---|
| `temporal_status` | OPTIONAL / UNKNOWN-ALLOWED | Explicit status of the current finding. |
| `change_status` | OPTIONAL / UNKNOWN-ALLOWED | Explicit current-versus-prior change for the same finding. |
| `comparison_reference` | OPTIONAL | Reference to governed comparison context when available. |

Historical or comparison-only content cannot create a current positive finding. Full longitudinal, comparison, and temporal graphs remain deferred.

## 6. RadiologyMeasurement V0

A measurement is never an unrelated standalone number. It is owned by a finding and linked through `MEASURED_AS` or the finding's `measurements[]` collection.

```text
RadiologyMeasurement V0
  measurement_id
  quantity_type
  source_value
  numeric_value (optional)
  source_unit (optional)
  dimensions[] (optional)
  dimension_axes[] (optional)
  qualifier (optional)
  evidence_span
  extraction_confidence
  validation_state
  provenance
```

| Field | Requirement | Semantics |
|---|---|---|
| `measurement_id` | REQUIRED | Stable identity within extraction result. |
| `quantity_type` | REQUIRED / UNKNOWN-ALLOWED | Size, distance, volume, angle, or other profile-declared source quantity. |
| `source_value` | REQUIRED | Source-faithful measurement expression. |
| `numeric_value` | OPTIONAL / UNKNOWN-ALLOWED | Parsed numeric value only when supported. |
| `source_unit` | OPTIONAL / UNKNOWN-ALLOWED | Unit exactly as stated. |
| `dimensions[]` | OPTIONAL | Explicit multi-dimensional values in source order. |
| `dimension_axes[]` | OPTIONAL | Axis labels only when explicitly stated or profile-governed. |
| `evidence_span` | REQUIRED | Exact source evidence. |
| confidence/validation/provenance | REQUIRED | Independent measurement lineage. |

Unpaired or ambiguous measurements require review or remain partial. EXTRACT preserves source units; UCUM mapping and value/unit normalization belong to STANDARDIZE.

## 7. RadiologyFindingRelationship V0

V0 supports a small, clinically readable relationship set:

| Type | Meaning | V0 rule |
|---|---|---|
| `LOCATED_AT` | Finding is explicitly located at anatomy. | Source-supported only. |
| `ASSOCIATED_WITH` | Source explicitly connects two current findings without asserting causality. | Source-supported only. |
| `SUGGESTIVE_OF` | Source explicitly states one observation is suggestive of another assessment. | Preserve direction and uncertainty. |
| `HAS_ATTRIBUTE` | Finding has a separately represented severity, temporal, morphology, or other attribute. | Use only when an attached field is insufficient. |
| `MEASURED_AS` | Measurement belongs to the finding. | Required ownership link when measurement is a separate object. |

`MODIFIES` is not a separate V0 type; its safe cases use `HAS_ATTRIBUTE`. `CAUSES` is not a V0 relationship. MRJ must not infer causality from proximity, co-occurrence, terminology relationships, or model suggestion.

```text
RadiologyFindingRelationship V0
  relationship_id
  relationship_type
  source_fact_id
  target_fact_or_attribute_id
  relation_origin
  evidence_span
  extraction_confidence
  validation_state
  review_state
  provenance
```

### 7.1 Relation origin

The only canonical V0 origin is:

```text
EXPLICIT_SOURCE_RELATION
```

An engine-proposed or model-inferred relationship may remain a `ClinicalEvidenceCandidate` with origin `MODEL_INFERRED_CANDIDATE`, but it cannot enter the canonical V0 graph unless MRJ validates explicit supporting source evidence. This deliberately defers inferred authoritative relations.

Every accepted relation requires its own evidence, confidence, validation, and provenance. Shared sentence context may support a relation, but concept co-occurrence alone is insufficient.

## 8. RadiologyClinicalFactGraph V0

```text
RadiologyClinicalFactGraph V0
  graph_id
  report_id
  journey_run_id
  source_document_version
  inherited_document_identity
  common_clinical_context
  clinical_context_facts[]
  findings[]
  measurements[]
  relationships[]
  extraction_coverage
  extraction_review_required
  warnings[]
  extraction_profile_id/version
  domain_pack_id/version
  provenance
```

This logical object connects report-level context, structured clinical-context facts, Radiology findings, attributes, evidence, and provenance. It does not require Neo4j, RDF, a graph database, persistent storage, or a new API.

Comparison and recommendation facts remain separate future/deferred objects and are not silently inserted as current findings or V0 relationships.

## 9. Clinical context and CommonClinicalContext boundary

Ownership remains:

```text
UNDERSTAND → DocumentContext
PROTECT    → PatientAnalyticContext
EXTRACT    → CommonClinicalContext assembly
```

EXTRACT may assemble, but never recreate identity or reverse privacy:

| Context item | Permitted source owner | R2.0A requirement |
|---|---|---|
| Source document identity/domain/type/language | `DocumentContext` | Required where defined by R0. |
| `pseudonymous_subject_key` | `PatientAnalyticContext` only | Optional; currently unavailable. |
| age / age band | Privacy-approved `PatientAnalyticContext` | Optional; currently unavailable. |
| sex | Privacy-approved `PatientAnalyticContext` | Optional; currently unavailable. |
| safe study/event date or time bucket | Privacy-approved context with semantic time role | Optional; currently unavailable. |
| facility / generalized geography | Privacy-approved context | Optional; currently unavailable. |
| clinical indication | Eligible clinical narrative evidence established during EXTRACT | Optional; not an identity field. |
| relevant clinical history | Eligible clinical narrative evidence established during EXTRACT | Optional; not a current finding. |

Clinical indication/history may be source-grounded clinical context, but it must retain that role and evidence. A patient name, identifier, exact prohibited date, or other removed identity may not be rediscovered from source or model output. Every displayed or persisted populated context item requires provenance and a value state.

The current accepted R1 `PatientAnalyticContext` remains unpopulated. This contract does not implement age bands, safe dates, geography reduction, or pseudonymous keys.

### 9.1 ClinicalContextFact V0

`ClinicalContextFact` gives source-grounded clinical indication and history enough structure for future governed analysis without converting them into current Radiology findings.

```text
ClinicalContextFact V0
  context_fact_id
  context_concept
  context_role
  assertion_state
  temporal_status (optional)
  source_section
  semantic_role
  evidence_span
  extraction_confidence
  validation_state
  review_state
  provenance
```

| Field | Requirement | Semantics |
|---|---|---|
| `context_fact_id` | REQUIRED | Stable identity within the extraction result. |
| `context_concept` | REQUIRED | Terminology-independent `MRJClinicalConcept` for source-stated clinical context. |
| `context_role` | REQUIRED | One bounded role from the table below. |
| `assertion_state` | REQUIRED | The same authoritative `PRESENT`, `ABSENT_NEGATED`, `UNCERTAIN`, `CONDITIONAL`, or `UNKNOWN` model used by findings. |
| `temporal_status` | OPTIONAL / UNKNOWN-ALLOWED | Explicit context timing such as recent or remote, without constructing a longitudinal model. |
| `source_section` / `semantic_role` | REQUIRED | Eligible indication/history region and governed context role. |
| `evidence_span` | REQUIRED | Exact permitted-source span and quote. |
| confidence/validation/review/provenance | REQUIRED | Independent MRJ authority and lineage. |

The V0 context-role set is deliberately small:

| Role | Operational meaning | Example source meaning |
|---|---|---|
| `INDICATION` | Stated clinical reason for the imaging study. | Evaluation requested for a stated concern. |
| `SYMPTOM` | Source-stated presenting symptom. | Severe headache. |
| `HISTORY_OR_COMORBIDITY` | Relevant prior/current clinical history or comorbidity. | History of hypertension. |
| `EVENT_OR_EXPOSURE` | Source-stated event or exposure relevant to the study. | Recent head trauma. |
| `OTHER_CLINICAL_CONTEXT` | Safe fallback for supported clinical context that does not fit the prior roles. | A supported but otherwise uncategorized context fact. |

`ClinicalContextFact` is not a universal clinical ontology and is not a route for identity recovery. It must not contain patient name, identifier, prohibited exact identity information, or privacy-restricted demographics. Age, age band, sex, safe dates, facility/geography, and pseudonymous subject keys remain owned by `PatientAnalyticContext` and retain its policy/derivation provenance.

Context facts remain distinct from `RadiologyFinding`. “Recent head trauma” may become `EVENT_OR_EXPOSURE`; “history of hypertension” may become `HISTORY_OR_COMORBIDITY`; and “presenting with severe headache” may become `SYMPTOM`. None becomes a current imaging finding merely because it appears in the same report.

## 10. Evidence and provenance

Every accepted fact, populated attribute, measurement, and relation must retain:

- `report_id`, source document version, and JourneyRun/stage execution identity;
- permitted canonical source representation and exact evidence span/quote;
- source section/semantic region and semantic role;
- extraction profile and Radiology pack versions;
- contributing engine/method and adapter version;
- raw engine confidence separately from MRJ fact confidence when applicable;
- grounding state and correlation family for candidate evidence;
- MRJ validator/arbitration version and validation/review disposition;
- policy/access context governing extraction;
- creation time and integrity/digest references where applicable.

Offsets are MRJ-grounded. External engine offsets are not authoritative. Evidence disclosure must respect privacy/access policy.

## 11. Candidate-to-fact authority path

All engines adapt to the accepted `ClinicalEvidenceCandidate` architecture:

```text
Engine candidate
  → exact MRJ grounding
  → extraction-profile eligibility
  → semantic-role qualification
  → assertion and attribute validation
  → relationship validation
  → conflict/correlation handling
  → MRJ arbitration
  → RadiologyFinding / relationship / abstention / review
```

External schemas do not become MRJ contracts. Models generate evidence; MRJ determines authority.

## 12. Validation and review

An accepted finding requires concept, assertion state, eligible role, exact evidence, source section, confidence, validation/review state, profile/pack identity, and provenance.

Review is required for cases such as:

- ambiguous or failed grounding;
- conflicting assertion/negation;
- unresolved current versus history/comparison/recommendation role;
- incompatible anatomy or laterality candidates;
- unattached measurement or ambiguous unit;
- unsupported semantic class or field cardinality;
- relation without explicit connecting evidence;
- candidate disagreement MRJ cannot safely resolve.

Partial facts retain supported fields and explicit unknowns. Rejected candidates do not enter canonical facts. Human review cannot silently transform unsupported evidence into a valid fact.

## 13. EXTRACT/STANDARDIZE boundary

EXTRACT captures source meaning:

```text
source expression
  → MRJClinicalConcept
  → typed RadiologyFinding
```

STANDARDIZE later adds:

- canonical terminology binding;
- vocabulary/code/display/version;
- mapping method, confidence, state, and provenance;
- unit normalization and approved conversion.

Potential later targets include RadLex, SNOMED CT, LOINC/RSNA where appropriate, and UCUM. A valid extracted fact may remain unmapped. Mapping failure cannot erase or lower the extraction fact's recognition confidence.

## 14. Future analytics readiness

This contract enables, but does not compute:

| Later analytical question | Required governed inputs |
|---|---|
| Finding frequency per eligible report collection | Standardized positive finding + eligible report denominator. |
| Finding by age band | Finding + privacy-approved age band; unknown-age exclusions explicit. |
| Finding by sex | Finding + privacy-approved sex; unknown handling explicit. |
| Finding co-occurrence | Two positive findings in the same eligible report. |
| Anatomy distribution | Finding + validated anatomy. |
| Severity distribution | Finding + source-supported severity. |
| Measurement distribution | Finding-owned measurement + compatible standardized unit. |
| Clinical-context association candidate | Finding + separately role-qualified clinical context; later method required. |

`ABSENT_NEGATED`, `UNCERTAIN`, `CONDITIONAL`, and `UNKNOWN` facts do not contribute as positive presence unless a future named analytical contract explicitly governs them. Repeated evidence in Findings and Impression does not create duplicate positive report contributions.

Clinical-context and finding co-occurrence may later support a cohort-level co-occurrence or association analysis under a named method. It never creates a causal edge: the presence of trauma context and a hemorrhage finding does not mean trauma caused hemorrhage.

Finding frequency is not patient prevalence. Co-occurrence is not statistical association or causation. EXTRACT produces report-level facts only; ANALYZE owns cohort-level computation.

## 15. R2 V0 minimum and deferred scope

### Required V0

- terminology-independent `RadiologyFinding` objects;
- semantic class and authoritative assertion state;
- exact evidence and source section;
- MRJ confidence, validation/review, and provenance;
- anatomy/laterality when directly supported;
- finding-owned measurement/unit when directly supported;
- explicit source relationships from the bounded V0 set when directly supported;
- structured `ClinicalContextFact` objects when eligible context is stated; reports are not required to contain one;
- `CommonClinicalContext` assembly without identity rediscovery;
- explicit partial/unknown/abstention behavior.

### Deferred

- automatic terminology mapping and unit standardization;
- full comparison and recommendation fact models;
- inferred/complex relationship graphs;
- causal reasoning;
- advanced longitudinal/temporal graphs;
- patient linkage and patient-level prevalence;
- imaging-pixel interpretation or image-report concordance;
- analytics, visualization, and indicators;
- clinical or production certification.

## 16. Conformance criteria

A future R2 implementation conforms only if it:

1. consumes an eligible protected/permitted Radiology report without reclassification;
2. preserves R1 privacy decisions and never rediscovers removed identifiers;
3. emits typed current findings rather than section copies or generic entities;
4. distinguishes present, absent, uncertain, conditional, and unknown assertions;
5. binds attributes, measurements, and relations to correct findings with evidence;
6. preserves exact source and field-level provenance;
7. separates comparison/history/recommendation from current findings;
8. remains valid without terminology mappings;
9. supports partial output, abstention, and review without fabrication;
10. hands terminology-independent facts to STANDARDIZE.

## 17. Acceptance gate

This document is the accepted R2.0A specification for future Radiology EXTRACT work. Its acceptance does not start R2 implementation. No EXTRACT runtime, endpoint, database, model, dependency, dataset, or generated clinical result is created by this specification.
