# MRJ Radiology Intelligence Pack

**Version:** 1.0
**Status:** ACCEPTED — R0 RADIOLOGY HORIZONTAL ARCHITECTURE CHECKPOINT
**Date:** 17 September 2026
**Domain:** `RADIOLOGY`
**Initial document profile:** `RADIOLOGY_REPORT`
**Document type:** Accepted Domain Intelligence Pack architecture; not an implementation claim

## 1. Purpose

This document defines the accepted first MRJ Domain Intelligence Pack architecture. It specifies the Radiology domain boundary, a versioned report extraction profile, terminology-independent clinical facts, reference bindings, validation, analytics eligibility, and governed indicator opportunities.

The pack is constrained by the frozen UNDERSTAND v1 architecture. It does not modify Radiology recognition, reclassify documents, broaden UNDERSTAND light context, or claim that Radiology EXTRACT/STANDARDIZE is implemented.

### 1.1 Authority relationship

This document is authoritative within the accepted R0 package for the Radiology-specific clinical schema, `RadiologyFinding`, Radiology reference/terminology usage, Radiology analytical deduplication, and Radiology analytics contracts. Cross-domain extraction concepts such as `MRJClinicalConcept` and the Domain Intelligence Pack contract are owned by the Domain Clinical Extraction Architecture. Formal stage envelopes are owned by the Seven-Stage Contracts.

## 2. Pack identity

```text
domain_pack_id: MRJ-RADIOLOGY
version: 1.0
status: PROPOSED
active_implementation_target: Radiology horizontal journey V0
authoritative_owner: MRJ
```

The pack consists conceptually of:

```text
MRJ-RADIOLOGY/
  domain_definition
  document_profiles/RADIOLOGY_REPORT/1.0
  extraction_schemas/RadiologyFinding/1.0
  terminology_bindings/1.0
  validation_rules/1.0
  analytics_contracts/1.0
```

## 3. Domain definition

Radiology clinical intelligence concerns imaging reports and their source-grounded clinical observations, anatomy, measurements, assessments, comparisons, and recommendations.

The frozen UNDERSTAND Radiology subdomains remain:

```text
CT
MRI
X_RAY
ULTRASOUND
MAMMOGRAPHY
NUCLEAR_MEDICINE
FLUOROSCOPY
OTHER
```

Study families such as CTA, MRA/MRV, Doppler, CR/DX/XR, PET, and SPECT remain governed family/specialization metadata rather than new top-level subdomains.

### 3.1 Exclusions

This pack does not authorize:

- a competing document classifier;
- imaging-pixel interpretation;
- image-report concordance;
- autonomous diagnosis;
- report rewriting;
- universal medical extraction;
- inferring clinical absence from missing text;
- terminology mappings without active governed sources;
- using recommendation/history/comparison content as current findings without an explicit fact role.

## 4. Document profile: RADIOLOGY_REPORT v1.0

### 4.1 Profile identity

```text
profile_id: MRJ-RADIOLOGY-RADIOLOGY_REPORT
version: 1.0
domain: RADIOLOGY
document_type: RADIOLOGY_REPORT
```

### 4.2 Routing prerequisites

- UNDERSTAND provides an authoritative `RADIOLOGY` domain decision.
- Document type is `RADIOLOGY_REPORT`, or a future explicitly approved compatible report type.
- Supported Radiology subdomain/family or `OTHER` is retained exactly as selected by UNDERSTAND.
- Document review state is honored.
- PROTECT permits the exact input representation and output use.
- Profile and pack versions are available and pinned.

`UNKNOWN` may not automatically enter the Radiology profile. `RADIOLOGY / OTHER` must use conservative field eligibility and must not guess modality-specific facts.

### 4.3 Input

The profile consumes:

- MRJ-owned protected/permitted document representation;
- authoritative `MedNexusDocumentContext` / `DocumentContext` from UNDERSTAND;
- optional `PatientAnalyticContext` from PROTECT;
- the selected policy/access context;
- source document and run provenance;
- exact pack and profile version.

EXTRACT assembles `CommonClinicalContext` from `DocumentContext`, `PatientAnalyticContext`, and approved common non-domain facts. The Radiology profile consumes that assembled context for downstream use; it does not recreate protected identifiers or override privacy decisions.

### 4.4 Output

```text
RadiologyExtractionResult
  report_id
  inherited_document_identity
  common_clinical_context
  findings[]: RadiologyFinding
  comparison_facts[]: ComparisonFact (future/deferred)
  recommendation_facts[]: RecommendationFact (future/deferred)
  extraction_coverage
  extraction_review_required
  warnings[]
  profile_id/version
  pack_id/version
  provenance
```

`RadiologyFinding` contains only current clinical Radiology observations/findings. Comparison, history, and recommendation statements never enter `findings[]`. Future `ComparisonFact` and `RecommendationFact` objects remain separate so their semantic roles cannot be lost; they are not required for R2 Horizontal V0.

## 5. RadiologyFinding v1.0

`RadiologyFinding` is a current clinical Radiology observation/finding. Its schema is broad and future-capable, but R2 V0 populates only the small clinically meaningful subset defined in Section 7. Recommendation text and historical/comparison assertions are not `RadiologyFinding` objects.

### 5.1 Identity and concept

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `finding_id` | Identifier | Yes | Stable fact identity within an extraction result |
| `finding_concept` | MRJClinicalConcept | Yes for accepted finding | Terminology-independent MRJ pre-standardization concept |
| `source_expression` | Text | Yes | Verbatim or source-faithful expression |
| `assertion_state` | Enum | Yes | `PRESENT`, `ABSENT_NEGATED`, `UNCERTAIN`, `CONDITIONAL`, `UNKNOWN` |

### 5.2 Anatomy

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `anatomic_site` | MRJClinicalConcept | No | Specific site tied to the finding |
| `body_region` | MRJClinicalConcept | No | Broader body region |
| `laterality` | Enum/concept | No | Left, right, bilateral, midline, other, unknown |
| `anatomic_qualifiers[]` | MRJClinicalConcept[] | No | Subsite, segment, compartment, level, or other governed qualifier |

Performed-study anatomy inherited from UNDERSTAND and finding anatomy are different concepts. Finding anatomy must not rewrite current-study identity.

### 5.3 Certainty, severity, and morphology

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `certainty` | Enum/MRJClinicalConcept | No | Degree of diagnostic/observational certainty |
| `severity` | Enum/MRJClinicalConcept | No | Source-supported severity |
| `morphology[]` | MRJClinicalConcept[] | No | Shape, margin, signal/density/echogenicity, distribution, or other governed descriptors |

No default certainty or severity is inferred from omission.

### 5.4 Measurements

```text
RadiologyMeasurement
  measurement_id
  quantity_type
  source_value
  numeric_value (optional)
  source_unit (optional)
  standardized_value (STANDARDIZE output only)
  standardized_unit (STANDARDIZE output only)
  dimension_axis (optional)
  method/qualifier (optional)
  evidence_span
  confidence
  validation_state
```

A measurement may be one-dimensional, multidimensional, interval, qualitative, or non-normalizable. Numeric parsing and unit pairing require evidence; absent units are not fabricated.

### 5.5 Temporal and change context

This is future-capable metadata for a current finding when the source explicitly compares that same current finding with a prior state. It does not convert a historical/comparison-only statement into a current finding and is not required for R2 V0.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `temporal_status` | Enum/concept | No | Acute, chronic, interval, prior, indeterminate, or other supported state |
| `change_status` | Enum/concept | No | New, increased, decreased, stable, resolved, progressed, improved, unknown |
| `comparison_reference` | Reference | No | Link to comparison fact/study context where available |
| `time_basis` | Semantically typed time | No | Evidence-grounded time role, subject to PROTECT |

Historical or comparison observations cannot become current findings merely because they contain a valid finding concept.

### 5.6 Relationships

Relationship graphs are future/advanced capability and are not required for R2 V0. A directly stated associated finding may be captured as a bounded attribute or separate current finding with shared evidence; complex graph construction is deferred.

```text
RadiologyFindingRelationship
  relationship_type
  target_finding_id
  source_evidence_span
  confidence
  validation_state
```

Potential future governed relationship types include `ASSOCIATED_WITH`, `LOCATED_IN`, and `SOURCE_ASSERTED_CAUSAL_RELATION`. `SOURCE_ASSERTED_CAUSAL_RELATION` preserves an explicit causal assertion made in source text; MRJ does not establish causality from co-occurrence, retrospective association, terminology proximity, or model suggestion. Comparison and recommendation relationships belong to future `ComparisonFact` and `RecommendationFact` models, not the core `RadiologyFinding` graph.

### 5.7 Evidence and provenance

| Field | Required | Meaning |
|---|---:|---|
| `source_section` | Yes | Canonical semantic region/section |
| `source_evidence_span` | Yes for source-grounded fact | Exact offsets/range and source quote where available |
| `evidence_candidates[]` | No | Candidate lineage retained for audit |
| `extraction_method` | Yes | MRJ Native, deterministic, terminology, external candidate plus arbitration, or human-reviewed |
| `engine_provenance[]` | Yes | Exact contributing engine/adapter/version/configuration identities |
| `extraction_confidence` | Yes | MRJ fact confidence, distinct from raw engine confidence |
| `validation_state` | Yes | `VALID`, `PARTIAL`, `NEEDS_REVIEW`, `REJECTED`, or `UNKNOWN` |
| `review_state` | Yes | Review requirement and disposition |

### 5.8 Terminology bindings

`terminology_bindings[]` are STANDARDIZE-owned additions. Each binding retains canonical concept, vocabulary, concept identifier/display, vocabulary version, mapping method/confidence/status, source evidence, engine/validator, and reference artifact provenance.

An extracted finding remains valid when it is `UNMAPPED`. External terminology codes never replace source evidence or MRJ fact identity.

## 6. Missing is not false

This pack formalizes:

> Missing ≠ False.

Examples:

- Missing laterality does not mean bilateral.
- Missing measurement does not mean zero size.
- Missing severity does not mean mild or normal.
- Missing negation does not by itself prove presence.
- Missing comparison does not mean unchanged.
- Missing finding evidence does not establish absence.
- Missing patient key makes patient-level prevalence ineligible; it does not imply zero patients.

Fields use explicit state/value pairs where ambiguity would otherwise be unsafe.

## 7. Radiology Clinical Extraction V0

V0 must be clinically meaningful while remaining narrow enough for horizontal delivery.

### 7.1 Required V0 capability

For each accepted finding, the R2 Horizontal V0 contract is deliberately small.

Required for an accepted finding:

- Finding Concept
- Presence/Negation/Assertion State
- Source Section
- Exact Evidence Span
- MRJ Confidence
- Engine/Method Provenance
- Validation/Review State

Target fields when directly available:

- Anatomic Site
- Body Region
- Laterality
- Certainty
- Severity
- Measurement + Unit
- Directly stated associated finding, without requiring a relationship graph

### 7.2 Not sufficient for V0

The following alone do not satisfy V0:

- copying the Findings section into one text field;
- copying the Impression section into one text field;
- counting report sections;
- returning only a free-text summary;
- producing terminology codes without source-grounded clinical facts.

Section text may be retained as source context, but V0 must produce structured clinical observations.

### 7.3 V0 optional capability

- Multiple measurements per finding
- Temporal/change state
- Comparison linkage
- Recommendation linkage
- Morphology qualifiers
- Terminology candidate mappings

Optional capability must be represented as absent/unknown when unsupported, not simulated.

### 7.4 Explicitly deferred beyond R2 V0

- complex associated-finding graphs
- causal relationship modeling beyond preserving an explicit source assertion
- advanced temporal graphs
- full comparison relationship graphs
- recommendation linkage graphs
- morphology relationship graphs

These future capabilities must not delay the first horizontal Radiology journey. The broad schema is an evolution boundary, not an R2 completion checklist.

## 8. Evidence and semantic-role rules

### 8.1 Eligible finding evidence

Current clinical findings normally require source evidence in an observation/findings or conclusion/impression role, subject to profile validation.

### 8.2 Role firewalls

- Recommendation evidence remains a future-action fact.
- Comparison evidence remains prior/comparison context unless the report explicitly asserts current change.
- History/indication evidence is not a current finding.
- Technique/acquisition content does not become a diagnosis.
- Authentication content does not become a clinical fact.
- A terminology match identifies what text may mean, not its role in the document.

### 8.3 Partial reports

A report with a valid impression but limited findings narrative may still yield source-grounded facts when its document identity and semantic region are governed. A profile must not require every conventional section if the available evidence is otherwise valid. Missing sections remain recorded as coverage limitations.

## 9. Reference architecture by journey stage

| Reference | UNDERSTAND | PROTECT | EXTRACT | STANDARDIZE | ANALYZE / VISUALIZE / INDICATORS |
|---|---|---|---|---|---|
| **DICOM** | Modality, study/acquisition, anatomy and document/imaging context reference | Metadata/privacy/de-identification reference where applicable | Source context for image/report-linked facts; no pixel interpretation in V0 | Preserve governed DICOM identifiers/attributes where permitted | Scope analyses by study/modality context; never infer clinical facts from identifiers alone |
| **RSNA RadLex** | Radiology concept and anatomy reference supporting MRJ reasoning | No privacy authority | Candidate vocabulary for findings, anatomy, procedures and relationships | Approved Radiology mapping target with version/provenance | Supports concept grouping only through governed mappings |
| **RSNA RadReport** | Structured reporting/section guidance | No privacy authority | Profile/template guidance and expected fact organization | Preserve template/profile references | Supports completeness interpretation, not clinical truth by itself |
| **LOINC / RSNA Playbook** | Study/procedure/document identity and normalization reference | No privacy authority | Inherited procedure context; not a substitute for findings | Procedure/document mapping target | Cohort scoping by standardized study/procedure where eligible |
| **SNOMED CT** | Broader reference mappings only | No privacy authority | Candidate broader clinical representation | Approved mapping target when active/licensed | Supports broader clinical grouping with exact version/provenance |
| **FHIR DiagnosticReport** | Report-level interoperability shape | Carries policy-governed report content only | Container for report-level extraction representation | Standardized report representation | Source/report linkage for interoperable outputs |
| **FHIR Observation** | Not an UNDERSTAND fact source | Carries policy-governed observation content only | Interoperability shape for atomic observations | Coded observation representation | Analytical inputs only after MRJ validation/standardization |
| **UCUM** | No document-classification authority | No privacy authority | Preserve source unit/value | Authoritative unit representation and conversion where valid | Comparable measurement distributions require compatible standardized units |

These sources are reference inputs. MRJ owns profile curation, semantic-role decisions, validation, mapping authority, analytical eligibility, and final outputs.

## 10. Terminology binding profile

Each binding must carry:

```text
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

### 10.1 Preferred role by source

- RadLex: Radiology-specific findings, anatomy, procedure and semantic relationships.
- SNOMED CT: broader clinical representations and cross-domain interoperability.
- LOINC/RSNA Playbook: study/procedure/document identity.
- UCUM: measurement units.
- DICOM: imaging/study/acquisition identifiers and context.

Preference is field-specific and profile-governed. MRJ must not invent mappings between sources.

## 11. Validation rules v1.0

### 11.1 Fact validation

An accepted finding requires:

- a profile-declared finding concept representation;
- valid fact role;
- source evidence and section/region linkage;
- an assertion state;
- exact report/document provenance;
- MRJ confidence and validation state;
- no unresolved contradiction that makes the fact unsafe to persist.

### 11.2 Attribute validation

- Anatomy must be tied to the finding, not merely present somewhere in the report.
- Laterality must be evidence-grounded and anatomically compatible.
- Severity/certainty must not be inferred from punctuation or omission alone.
- Measurements require value/evidence and retain unresolved units explicitly.
- Association links require evidence that connects the facts.
- Comparison/change requires current/prior role separation.

### 11.3 Review triggers

- Ambiguous evidence grounding
- Conflicting assertion/negation
- Unresolved current-versus-prior role
- Multiple incompatible anatomy targets
- Unpaired measurement/unit where the profile requires a pair
- Candidate disagreement that MRJ cannot resolve safely
- Unsupported profile field or cardinality
- Mapping ambiguity that affects downstream aggregation

## 12. Extraction coverage

Coverage is not a clinical outcome. Accepted coverage fields include:

- eligible finding regions
- processed finding regions
- accepted finding count
- partial/review finding count
- rejected candidate count by reason
- evidence-grounded field count
- optional-field availability by type

Coverage must not reward engines for producing more unsupported candidates.

## 13. Analytics contracts

The pack defines named contracts between validated facts and downstream analyses.

### 13.1 Required Clinical V0 — no demographics required

These contracts operate on standardized report-level facts and must permit the first horizontal journey to complete when age, sex, and subject linkage are unavailable.

| Contract | Required inputs | Output level | Key safety rule |
|---|---|---|---|
| Finding Frequency | standardized finding concept, eligible reports | Report/collection | Denominator is eligible reports, not all uploads |
| Finding Co-occurrence | two standardized findings in the same eligible report | Report/collection | Co-occurrence is not association or causation |
| Anatomy × Finding Distribution | standardized finding + anatomy, eligible reports | Report/collection | Missing anatomy remains excluded/unknown, not a fabricated category |
| Measurement Distribution | finding, compatible measurement/unit | Finding/report | Run only when measurements exist; exclude or stratify non-comparable units |
| Severity Distribution | finding, governed severity | Finding/report | Run only when severity exists; missing severity is not mild |

### 13.2 Enhanced Clinical V0 — optional privacy-safe context

| Contract | Required inputs | Output level | Key safety rule |
|---|---|---|---|
| Age-stratified Finding Frequency | finding + policy-permitted age/age band | Report/collection | Declare unknown-age exclusions and report-level denominator |
| Sex-stratified Finding Frequency | finding + policy-permitted sex | Report/collection | Declare missing/unknown handling and report-level denominator |

### 13.3 Patient-level analytics — optional

| Contract | Required inputs | Output level | Key safety rule |
|---|---|---|---|
| Patient Finding Prevalence | finding concept, stable permitted subject key, eligible patients, defined time window | Patient | Ineligible without safe linkage and an explicit patient denominator |

Patient-level analytics are not prerequisites for first Horizontal V0 acceptance.

### 13.4 Future/advanced contracts

Recommendation rate by finding, temporal-change distributions, and statistical association analysis require future typed facts/methods. Odds ratios, chi-square, Fisher exact tests, regression, confounder adjustment, and statistical-significance testing are explicitly deferred beyond Horizontal V0.

Analytical contracts pin pack/profile versions and required standardization coverage.

### 13.5 Analytical deduplication

For report-level finding frequency, one eligible report contributes at most one positive contribution per standardized finding concept under the indicator definition. The same clinical finding repeated in Findings and Impression therefore contributes one positive report, not two. MRJ retains both source evidence spans and any valid fact linkage; deduplication affects the analytical contribution, not the evidence record.

For report-level co-occurrence, each concept is first reduced to report-level presence under the contract before concept pairs are counted. For patient-level analytics, each eligible patient contributes according to the specific indicator definition and time window. Detailed patient deduplication remains future work, but the governing rule must be explicit rather than an implementation accident.

## 14. Clinical indicator opportunities

### 14.1 Primary clinical indicators

- Finding Frequency
- Finding Co-occurrence Rate
- Anatomy × Finding Distribution
- Lesion Measurement Distribution
- Severity Distribution

Optional enhanced indicators include Age-stratified and Sex-stratified Finding Frequency when privacy-safe context exists. Patient-level Finding Prevalence is optional when safe stable subject linkage and a governed denominator/time window exist.

Association Strength, Follow-up Recommendation Rate by Finding, and advanced temporal indicators are future/advanced rather than Horizontal V0 requirements.

### 14.2 Secondary data/quality indicators

- Extraction Coverage
- Standardization Coverage
- Needs Review Rate
- Evidence Grounding Rate
- Mapping Confidence/Coverage
- Report Structure Completeness

Each indicator must retain definition, clinical meaning, numerator, denominator, eligibility, exclusions, level, time window, collection version, provenance, coverage, and uncertainty where applicable.

## 15. Scientific interpretation safeguards

- Finding count is not report frequency unless a report denominator is defined.
- Report frequency is not patient prevalence.
- Patient prevalence is not population prevalence.
- Co-occurrence does not establish association.
- Association does not establish causation.
- MRJ may preserve an explicit source-authored causal assertion as `SOURCE_ASSERTED_CAUSAL_RELATION`; MRJ does not establish causality from co-occurrence or retrospective association.
- A visualization cannot upgrade the scientific strength of an analysis.
- Missing data and review exclusions must be visible in coverage.

## 16. FHIR representation direction

FHIR is an interoperability representation, not MRJ's internal reasoning authority.

- `DiagnosticReport` may represent report-level identity, status, conclusion, and links to observations.
- `Observation` may represent source-grounded atomic findings and measurements.
- Profiles must retain MRJ fact IDs, evidence/provenance links, terminology-binding status, and collection lineage.
- An unstandardized MRJ fact must not be discarded merely because a coded FHIR representation is incomplete.

No FHIR endpoint or profile implementation is claimed by this document.

## 17. Model and engine compatibility

The pack constrains all engines equally.

Potential contributors:

- MRJ Native
- deterministic/rule engine
- terminology engine
- MedGemma
- future foundation or specialized engines

All output enters as `ClinicalEvidenceCandidate`. MRJ performs grounding, role qualification, validation, conflict handling, arbitration, confidence, and review. Models may not define new fields or return arbitrary authoritative JSON.

MedGemma is planned/future and unavailable locally. V0 must remain implementable without it. Future use requires the accepted multi-engine governance, exact model/artifact approval, data-access preflight, candidate adapter, and validation.

## 18. Provenance minimum

Each result must be traceable to:

- report and report version
- journey run and stage execution
- `MedNexusDocumentContext` version/reference
- privacy policy/access decision
- extraction pack/profile version
- source span/section
- engine/adapter/method versions
- validation/review disposition
- terminology source/version/mapping method when standardized
- collection ID/version when analyzed

## 19. V0 success criteria

Radiology Extraction V0 is architecture-conformant when it can:

1. Consume an eligible protected Radiology report without reclassifying it.
2. Produce typed, source-grounded findings rather than section-text copies.
3. Preserve negation, uncertainty, missingness, and semantic role.
4. Retain exact evidence/provenance and profile versions.
5. Abstain or require review safely.
6. Hand terminology-independent facts to STANDARDIZE.
7. Make at least one genuine downstream clinical analysis eligible without fake values.

R2 does not require complex relationship graphs, demographics, stable subject linkage, full schema population, or successful external terminology mapping. The minimum horizontal chain is real structured findings → real standardized findings → a structured clinical collection → report-level analyses → visual models → governed indicators.

## 20. Deferred capability

- Full schema population across all Radiology families
- Image/pixel interpretation
- Image-report concordance
- Automated report rewriting
- MedGemma or other model integration
- Advanced temporal/causal reasoning
- Statistical association testing and confounder-adjusted analysis
- Complex finding/comparison/recommendation relationship graphs
- Clinical certification
- Public Health or other domain packs

## 21. Acceptance and implementation gate

Human review accepted this pack architecture on 2026-09-17. It governs future Radiology extraction, standardization, analytics, and indicator implementation, but acceptance itself authorizes no reference-data mutation, model integration, API change, or clinical claim. R2 implementation has not started.
