# MRJ R2.0 Radiology Extraction Evaluation Plan

**Version:** 1.0
**Status:** ACCEPTED AND CLOSED
**Acceptance date:** 2026-09-24
**Date:** 24 September 2026
**Checkpoint:** R2.0A — Evaluation target definition
**Runtime status:** Plan only; no dataset, harness, engine, model, or benchmark is implemented

## 1. Purpose

This plan defines how future Radiology text-extraction engines will be evaluated against the proposed `MRJ_Radiology_Clinical_Fact_Contract_v1.0.md`. It does not select an engine, install a dependency, create ground truth, fabricate benchmark results, or authorize R2 implementation.

Planned sequence:

```text
R2.0A  Contract + UX + evaluation specification
R2.0B  Manually reviewed Radiology ground-truth dataset
R2.0C  Engine-neutral evaluation harness
R2.0D  Controlled engine benchmark
R2.0E  Evidence-based engine decision
R2      Radiology Clinical EXTRACT V0 implementation
```

## 2. Evaluation principles

1. The benchmark target is clinically meaningful `RadiologyFinding` output, not generic NER volume.
2. Exact source evidence, assertion state, semantic role, and finding-owned attributes matter as much as concept detection.
3. Recommendation, comparison, history, technique, and current findings must remain role-separated.
4. False positive current findings and lost negation are high-severity failures.
5. Engines emit candidates; MRJ grounds, validates, arbitrates, and determines authority.
6. External engine schemas never become MRJ contracts.
7. No report text, phrase, filename, or ground-truth label may be turned into report-specific production logic.
8. Synthetic reports may support controlled engineering tests but cannot replace real-world acceptance evidence.
9. Results must be slice-aware, reproducible, and tied to exact engine/runtime artifacts.
10. No benchmark number will be fabricated in this specification.

## 3. Evaluation target

The canonical target is:

```text
RadiologyClinicalFactGraph V0
  CommonClinicalContext
  ClinicalContextFact[]
  RadiologyFinding[]
  RadiologyMeasurement[]
  RadiologyFindingRelationship[]
  evidence and provenance
```

The benchmark evaluates only fields and semantics approved in the V0 fact contract. Terminology mapping, collection analytics, image interpretation, and report-image concordance are outside this text-extraction evaluation.

## 4. Candidate engine categories

Potential candidates for later controlled evaluation include:

| Candidate | Intended evaluation role | Current R2.0A state |
|---|---|---|
| MRJ Native / deterministic baseline | Transparent baseline and orchestration reference | Existing architecture concept; extraction baseline not implemented here |
| RadGraph-XL | Specialized Radiology entity/relation candidate | Not installed; suitability to be verified |
| GLiNER2.5 | Configurable clinical candidate extraction | Not installed; suitability to be verified |
| Hybrid strategies | Candidate fusion under MRJ validation/arbitration | Not implemented |
| MedGemma | Future/optional candidate subject to hardware, access, privacy, license, and separate approval | Not installed; not required for R2.0 |

MedImageInsight is not a text-extraction candidate. It belongs to future image-level intelligence or report-image concordance evaluation.

Names above identify categories for investigation, not approval. Exact provider, model variant/version, artifact digest, license/terms, adapter, configuration, quantization, runtime, data flow, and validation scope must be pinned before any benchmark.

## 5. Common candidate contract

Every engine output must adapt into the accepted `ClinicalEvidenceCandidate` boundary:

```text
ClinicalEvidenceCandidate
  candidate_id
  target_profile_id/version
  candidate_type
  proposed_fact_type
  proposed_field
  candidate_value
  attributes
  candidate_relations
  verbatim_evidence
  MRJ-grounded source_span
  semantic_region
  semantic_role
  assertion
  engine_id/version
  adapter_contract_version
  raw_engine_confidence
  correlation_family
  grounding_state
  provenance
  warnings
```

External engines may provide verbatim evidence, but their offsets are non-authoritative. MRJ performs exact grounding against the canonical permitted source representation. Ungrounded or ambiguously grounded candidates cannot become accepted facts.

The candidate path is:

```text
Engine output
  → adapter
  → ClinicalEvidenceCandidate
  → MRJ grounding and role qualification
  → profile validation and conflict handling
  → canonical RadiologyFinding / relation / review / abstention
```

## 6. R2.0B ground-truth dataset design

No dataset is created in R2.0A. The proposed R2.0B set is approximately 20–30 manually reviewed Radiology reports, subject to authorization, privacy, provenance, licensing, and leakage controls.

### 6.1 Coverage target

Deliberate coverage should span available report types and styles across:

- CT, including contrast and non-contrast where available;
- MRI;
- X-ray/radiography;
- Ultrasound;
- Doppler;
- Mammography;
- Fluoroscopy;
- complete and partial-report composition;
- positive, negative, uncertain, and mixed assertions;
- anatomy and laterality variation;
- measurements and multi-dimensional values;
- comparison/history/recommendation distractors;
- reports with and without privacy-safe analytical context.

Coverage is a design goal, not permission to inspect or use unapproved reports.

Selection must also cover extraction phenomena, not merely modality. The future set should contain sufficient examples where available of:

- positive disease/diagnostic assessments;
- non-disease imaging findings;
- discrete lesions;
- negation and uncertainty;
- anatomy and laterality;
- measurements and multi-dimensional values;
- explicit finding relationships;
- clinical indications;
- presenting symptoms;
- history/comorbidity;
- event/exposure context such as trauma;
- comparison/history/recommendation distractors.

Not every report is required to contain clinical context or every phenomenon. The manifest must report the annotation denominator for each phenomenon. When support is too small for a meaningful metric, report the count and uncertainty and do not present the metric as definitive.

### 6.2 Annotation unit

Annotation is report-scoped and uses only the V0 contract:

```text
Report annotation
  report_id / source version
  eligible semantic regions
  CommonClinicalContext annotations
  ClinicalContextFact annotations[]
  RadiologyFinding annotations[]
  RadiologyMeasurement annotations[]
  explicit RadiologyFindingRelationship annotations[]
  report-level exclusions / ambiguity notes
```

### 6.3 Finding annotation fields

At minimum:

- stable annotation ID;
- exact evidence span and quote;
- source section/semantic region;
- source expression;
- finding concept label, terminology-independent;
- semantic class;
- assertion state: present, absent-negated, uncertain, conditional, or unknown;
- anatomic site and body region when stated;
- laterality when stated;
- certainty and severity when stated;
- temporal/change status when stated and current-role eligible;
- measurement value, unit, dimensions, and evidence when attached;
- validation ambiguity/reviewer note;
- explicit relation annotations and relation evidence;
- role exclusions for history, comparison, recommendation, technique, and authentication content.

### 6.4 ClinicalContextFact annotation fields

For every eligible structured clinical-context fact, annotate:

- stable context-fact annotation ID;
- exact evidence span and quote;
- source section and semantic role;
- terminology-independent context concept;
- context role: `INDICATION`, `SYMPTOM`, `HISTORY_OR_COMORBIDITY`, `EVENT_OR_EXPOSURE`, or `OTHER_CLINICAL_CONTEXT`;
- assertion state;
- temporal status when explicitly supported;
- reviewer ambiguity/validation note;
- provenance and adjudication state.

Clinical-context annotation is optional per report. Reviewers must not infer a missing indication, symptom, history, or exposure, and must not turn context into a current Radiology finding.

### 6.5 CommonClinicalContext annotation fields

Annotate only permitted V0 context and ownership:

- document-derived identity references from UNDERSTAND;
- privacy-approved values supplied by Patient Analytic Context, if any;
- clinical indication and relevant clinical history from eligible narrative evidence;
- value state and field-level provenance;
- explicit `RESTRICTED`, `NOT_AVAILABLE`, `NOT_STATED`, `UNKNOWN`, and `NOT_APPLICABLE` states where appropriate.

Annotators must not reconstruct removed identifiers.

### 6.6 Reviewer rules

1. Annotate what the source states, not what the reviewer believes is clinically likely.
2. Preserve assertion and role exactly; “no pneumothorax” is absent, not positive.
3. Do not convert indication/history/recommendation/comparison into current findings.
4. Link anatomy, laterality, measurement, and attributes only to the finding they modify.
5. Annotate a relationship only when the source explicitly supports it.
6. Do not add external terminology codes during V0 extraction annotation.
7. Use explicit unknown/ambiguous states rather than guessing.
8. Record disagreements; do not silently overwrite them.
9. Preserve exact character spans in the canonical permitted text representation.
10. Do not expose identity or restricted information in annotation exports.

### 6.7 Review and adjudication

The future protocol should use at least two appropriately qualified reviewers for a defined adjudication subset, with:

- independent initial annotation where feasible;
- documented adjudication rules;
- disagreement categories by field and relation;
- versioned corrections and immutable source linkage;
- reviewer identity/role retained in controlled provenance;
- an adjudicated locked evaluation set not used for production-rule learning.

Inter-reviewer agreement should be reported for fields where a meaningful measure is defined. Agreement is not a substitute for clinical correctness.

### 6.8 Dataset governance

- Pin provenance, authorization, license/use restrictions, source type, and de-identification status.
- Segregate real, synthetic, transformed, and generated artifacts.
- Prevent validation/test leakage into prompts, rules, aliases, profiles, or tuning data.
- Version the annotation schema and dataset manifest.
- Store clinical datasets outside Git unless explicit governance says otherwise.
- Do not commit raw reports or ground truth containing restricted content.

## 7. Evaluation harness requirements

R2.0C should provide an engine-neutral harness that:

- presents the same canonical permitted input to each candidate;
- pins profile/pack/candidate-contract versions;
- records exact runtime and configuration;
- adapts output without silently repairing it;
- applies the same MRJ grounding and scoring rules;
- preserves raw candidate output separately from canonical evaluation output;
- supports per-report and aggregate metrics;
- reports modality/source/language/composition slices when sample size permits;
- records failures, abstentions, timeouts, and invalid output;
- produces reproducible machine-readable results without clinical data leakage;
- never writes benchmark output into production reference knowledge.

The harness is not implemented by this plan.

## 8. Benchmark dimensions

### 8.1 Clinical fact detection

- precision, recall, and F1 for finding concepts;
- exact and clinically acceptable span matching, reported separately;
- false positives and false negatives by semantic class;
- duplicate fact rate;
- unsupported current-finding rate from history/comparison/recommendation/technique.

### 8.2 Assertion and attributes

- assertion-state accuracy and confusion matrix;
- negation recall and false-positive-positive rate;
- uncertainty/conditional detection;
- semantic-class accuracy;
- anatomy and body-region accuracy;
- laterality accuracy;
- severity/certainty/temporal accuracy when annotated;
- measurement attachment accuracy;
- numeric value, unit, and dimensions accuracy.

### 8.3 Clinical context

- clinical-context concept precision, recall, and F1;
- context-role accuracy and confusion matrix;
- context assertion-state accuracy;
- temporal-status accuracy when annotated;
- evidence-grounding success and span accuracy;
- false clinical-context extraction rate;
- context incorrectly promoted to a current Radiology finding;
- privacy/identity-boundary violations.

### 8.4 Evidence and relationships

- evidence grounding success, ambiguity, and failure rates;
- evidence-span exact/overlap measures;
- relation precision, recall, and F1 by V0 type;
- relation direction and endpoint accuracy;
- unsupported inferred-relation rate;
- fact-to-anatomy and fact-to-measurement attachment errors.

### 8.5 Safety and abstention

- false positive current findings;
- missed negation;
- role-firewall violations;
- identity rediscovery or privacy-boundary violation;
- unsafe output accepted without review;
- abstention/`UNKNOWN` rate;
- appropriate versus inappropriate abstention;
- review burden and review yield;
- malformed or out-of-contract output.

### 8.6 Operational measurements

- end-to-end latency per report;
- engine-only latency and MRJ-adapter/validation latency separately;
- throughput under declared batch/concurrency conditions;
- peak and steady memory usage;
- CPU/GPU utilization and GPU memory when applicable;
- model load/startup time;
- artifact size and local storage footprint;
- timeout/failure/retry rate;
- deterministic repeatability under pinned settings.

No target numbers are asserted by this accepted specification. Quantitative thresholds require approval with the future benchmark protocol.

All metrics must state their denominator. Metrics with inadequate annotated support remain descriptive and unstable; they must not be presented as definitive comparative evidence.

## 9. Scientific reporting

Every benchmark report should include:

- exact dataset and annotation version;
- exact engine/artifact/adapter/runtime/configuration identity;
- report count and field/relation support counts;
- confidence intervals where statistically appropriate;
- per-slice results with denominator warnings;
- failure-severity analysis, not only aggregate F1;
- review and abstention behavior;
- missing-data and annotation-disagreement limitations;
- hardware and execution environment;
- license, privacy, and deployment eligibility;
- reproducibility limitations.

Small-set results must not be presented as production certification or general clinical performance.

## 10. Decision criteria for R2.0E

No single metric determines the engine decision. R2.0E should evaluate:

1. Clinical safety: negation, role, evidence, and privacy failures.
2. V0 contract coverage: concepts, assertion, anatomy, laterality, measurement, and explicit relations.
3. Groundability and provenance quality.
4. Precision/recall balance under clinically weighted failure severity.
5. Calibrated abstention and manageable human-review burden.
6. Runtime feasibility on the approved target environment.
7. Determinism, reproducibility, adapter complexity, and maintainability.
8. Licensing, distribution, commercial-use, privacy, residency, and data-flow eligibility.
9. Model/version drift and revalidation burden.
10. Fit with MRJ authority: candidate-only participation and replaceability.

Possible decisions include MRJ Native baseline, one specialized candidate, a hybrid, a bounded per-capability combination, further evaluation, or no acceptable candidate. The decision must identify approved scope and rejected/unsupported scopes.

## 11. Engine governance gate

Before execution, each external candidate requires:

- exact provider/model/version/artifact source and digest;
- terms/license/commercial and redistribution review;
- approved runtime and data-flow architecture;
- PROTECT-owned data-access decision where applicable;
- adapter and candidate-contract version;
- emergency disable and rollback path;
- benchmark dataset authorization;
- responsible owner and revalidation conditions.

Local execution alone does not establish privacy or compliance eligibility.

## 12. Out of scope

- installing or running RadGraph-XL, GLiNER2.5, MedGemma, or another model;
- downloading weights or dependencies;
- choosing a winning engine;
- creating the R2.0B dataset or annotations;
- implementing the R2.0C harness;
- producing benchmark values;
- implementing EXTRACT, STANDARDIZE, analytics, or frontend changes;
- imaging-pixel interpretation or MedImageInsight evaluation;
- production or clinical certification.

## 13. Exit criteria for this specification

R2.0A evaluation planning is ready for human review when it:

1. evaluates all engines against one MRJ-owned V0 fact contract;
2. defines a governed 20–30-report annotation target without creating it;
3. preserves candidate-only engine authority;
4. defines clinical, safety, evidence, relation, abstention, and runtime metrics;
5. preserves real/synthetic separation and leakage controls;
6. leaves model selection and implementation to later approved checkpoints.

## 14. Acceptance gate

This plan was accepted as part of the R2.0A specification package on 2026-09-24. R2.0B remains a separate checkpoint and has not started. No engine is selected or installed by this document.
