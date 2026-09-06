# MedNexus Multi-Engine Medical Intelligence Strategy

## Version 1.0

**Status:** ACCEPTED ARCHITECTURE STRATEGY CHECKPOINT — v1.0

**Date:** 6 September 2026

**Scope:** Model-agnostic clinical-intelligence evolution, initially focused on Radiology

**Implementation authorization:** None; this document defines direction only

This is the current accepted MedNexus multi-engine architecture strategy. It is an additive, versioned, evolvable strategy subordinate to—and required to remain consistent with—the frozen UNDERSTAND v1 authority package: [UNDERSTAND Domain Matrix v1.0](MedNexus_UNDERSTAND_Domain_Matrix_v1.0.md), [Blueprint v2.0](MedNexus_Enterprise_Architecture_and_Engineering_Blueprint_v2.0.docx), [Architecture Crosswalk v2.0](contracts/MedNexus_Architecture_Crosswalk_v2.0.md), [Clinical Semantic Context Contract v0.2](contracts/MedNexus_Clinical_Semantic_Context_Contract_v0.2.md), and [Clinical Extraction Contract v0.2](contracts/MedNexus_Clinical_Extraction_Contract_v0.2.md). It does not replace or modify those frozen artifacts. Future strategy evolution requires a new version or successor rather than silent modification of frozen authority. Where this strategy proposes future capabilities, the frozen contracts continue to govern stage boundaries and implementation work until formally superseded.

## 1. Executive architectural decision

MedNexus will evolve into a model-agnostic, multi-engine clinical-intelligence platform without becoming a thin wrapper around any model, vendor, or research system.

> **Models generate evidence. MedNexus determines authority.**

External engines may generate candidate evidence, interpretations, extraction candidates, imaging observations, transformations, or reasoning. MedNexus retains ownership of orchestration, routing, evidence eligibility, semantic context, authority, arbitration, conflict resolution, abstention, confidence, human-review decisions, privacy and policy enforcement, provenance, validation, clinical extraction contracts, terminology standardization, persistent structured data, longitudinal intelligence, analytics, visualization, and indicators.

The existing reference-and-context principle remains authoritative and extends to model-generated and multimodal evidence:

> **Reference knowledge tells MedNexus what concepts may mean; document structure and semantic context tell it what those concepts mean here; MedNexus reasoning decides what is authoritative for this document.**

No model output is authoritative merely because it is fluent, confident, multimodal, or supported by another model.

## 2. Why the strategy is changing

The current MedNexus foundation proves a deterministic, reference-driven path for document ingestion, UNDERSTAND, PROTECT, and bounded Radiology context. Future medical foundation models and unified understanding-and-generation engines may improve difficult-case recall, image understanding, candidate extraction, and cross-modal reasoning. They also introduce hallucination, calibration, provenance, licensing, privacy, reproducibility, infrastructure, and clinical-safety risks.

The architecture therefore needs stable integration and governance boundaries before any model spike becomes production coupling. The strategic change is not a transfer of authority to models; it is a controlled expansion of the evidence sources MedNexus can evaluate.

Immediate specialization remains:

1. `RADIOLOGY` — first and current priority.
2. `PUBLIC_HEALTH` — next major vertical, preserved for future compatibility but not designed or implemented here.

## 3. Relationship to MedNexus Seven

The authoritative public journey remains unchanged:

```text
01 UNDERSTAND
      ↓
02 PROTECT
      ↓
03 EXTRACT
      ↓
04 STANDARDIZE
      ↓
05 ANALYZE
      ↓
06 VISUALIZE
      ↓
07 INDICATORS
```

INGEST remains an internal operation inside UNDERSTAND. It is not an eighth public transformation.

Multi-engine capability is a cross-cutting implementation option within governed stages, not a new public stage. An engine may contribute candidates only to stages and capabilities explicitly authorized by its metadata and the current policy. It cannot collapse UNDERSTAND into EXTRACT, bypass PROTECT, move terminology authority out of STANDARDIZE, or create authoritative analytical facts outside the MedNexus Seven contracts.

Before any external engine is invoked within any stage, a cross-cutting PROTECT-owned **Engine Data-Access Preflight** must authorize whether the specific input may be exposed to that specific engine and execution context. This preflight is not completion of Stage 02 PROTECT, does not produce the final protected output, and does not reorder MEDNEXUS⁷. It is a narrow pre-invocation data-access decision required even when an engine contributes candidates during UNDERSTAND.

## 4. MedNexus Medical Intelligence Gateway

The **MedNexus Medical Intelligence Gateway** is the proposed stable, vendor-neutral integration and orchestration boundary for external medical AI engines. It is not merely a network gateway or API proxy, is not a clinical authority, and does not replace the existing MedNexus Intelligence Core. The name is retained because it describes controlled ingress of engine capabilities without assigning final clinical decisions to the Gateway.

```text
MedicalIntelligenceEngine
    |
    +-- MedGemmaFoundationEngine          (planned candidate)
    +-- OpenMedCandidateEngine            (existing capability, future adapter alignment)
    +-- UnifiedMedicalImagingEngine       (future class)
    +-- UnifiedMedicalUAGEngine           (research/future class)
    +-- FutureMedicalEngine               (replaceable)
```

The Gateway is responsible for stable request/response envelopes, capability discovery, policy eligibility, execution routing, timeouts, failure isolation, output provenance, version capture, and conversion into MedNexus candidate-evidence contracts. It does not determine document identity, clinical truth, privacy action, final extraction persistence, or terminology mappings.

An engine failure must remain containable. MedNexus must be able to abstain, fall back to an approved path, or route to human review without silently changing authority rules.

## 5. Engine capability model

A future **Engine Capability Registry** should record, at minimum:

| Metadata | Purpose |
|---|---|
| `engine_id` | Stable MedNexus identifier independent of deployment endpoint |
| `provider` | Model or service provider |
| `model_family` / `model_variant` / `model_version` | Exact model lineage and release identity |
| `artifact_source` / `artifact_digest` | Authoritative acquisition source plus immutable checksum or digest |
| `adapter_version` | Exact MedNexus adapter implementation |
| `candidate_contract_version` | Candidate input/output schema and semantic contract version |
| `runtime_configuration_id` | Reproducible runtime, prompt/configuration, quantization, dependency, and execution identity |
| `engine_type` | Detector, foundation model, imaging model, UAG engine, or other governed class |
| `supported_domains` | MedNexus domains for which the engine has a defined role |
| `supported_modalities` | Text, document, X-ray, CT, MRI, ultrasound, pathology image, or other declared inputs |
| `permitted_stages` | MedNexus stages in which candidate contribution is allowed |
| `permitted_input_types` | Text, image, multimodal, structured, metadata, or other authorized inputs |
| `permitted_candidate_types` | Candidate detection, context, extraction, VQA, generation, reconstruction, translation, or other bounded outputs |
| `execution_mode` / `execution_class` | Local, managed remote, or approved hybrid deployment and its execution class |
| `deployment_endpoint` | Approved endpoint or local deployment identity |
| `jurisdiction` / `data_residency` | Geographic processing and storage constraints |
| `retention_behavior` | Input, output, cache, and derivative retention rules |
| `logging_behavior` | Content, metadata, audit, and provider logging behavior |
| `data_egress_behavior` | Network destinations and data categories permitted to leave the controlled environment |
| `resource_requirements` | Hardware, memory, runtime, latency, and operating-cost envelope |
| `license_terms_identity` | Applicable license/terms source, snapshot or version, and effective date |
| `commercial_use_status` | Commercial-use authorization and unresolved conditions |
| `distribution_constraints` | Redistribution, hosted-service, derivative, attribution, and notice obligations |
| `intended_use` / `excluded_uses` | Approved role plus excluded or prohibited uses |
| `known_limitations` | Declared modality, language, population, calibration, safety, and operational limitations |
| `privacy_classification` / `privacy_eligibility` | Data sensitivity and handling eligibility |
| `policy_route` | `LOCAL_ALLOWED`, `REMOTE_ALLOWED`, `RESTRICTED`, or `DENIED` |
| `clinical_use_status` | Research-only, decision-support candidate, or separately approved status |
| `validation_status` / `validation_scope` | Current state and precisely bounded validated capability |
| `acceptance_dataset_version` | Locked dataset and version supporting the validation claim |
| `validated_slices` | Applicable modality, site/source, language, population, and workflow scope |
| `approval_owner` / `approval_date` | Accountable owner and recorded approval date |
| `revalidation_date` / `drift_status` | Expiry, revalidation schedule, and monitored model/version drift |
| `emergency_disable` | Kill-switch or routing-disable capability |
| `rollback_target` | Previously approved engine/deployment identity or safe native path |
| `retirement_status` / `retirement_owner` | Controlled retirement state and accountable owner |
| `provenance_requirements` | Inputs, prompts/configuration, outputs, timestamps, versions, and source grounding required for audit |
| `confidence_semantics` | What a raw engine score means, known calibration limits, and whether scores are comparable |

Registration does not authorize use. Execution requires an approved capability, compatible policy route, reproducible version, validated role, and available provenance controls. The registry is planned; it is not implemented by this document.

## 6. MedGemma strategy

MedGemma is the first planned **Medical Foundation Model candidate engine**. It remains Google-owned external/open-weight technology, not MedNexus-owned intelligence. Google describes MedGemma as a developer model family for medical text and image comprehension and states that developers must validate it for their intended use; it is not automatically clinical-grade. See the [official MedGemma overview](https://developers.google.com/health-ai-developer-foundations/medgemma) and [model card](https://developers.google.com/health-ai-developer-foundations/medgemma/model-card).

Planned Radiology candidate uses include:

- Medical-document semantic-understanding candidates.
- Difficult or ambiguous report reasoning candidates.
- Candidate context generation.
- Structured candidate extraction.
- Medical-image understanding candidates.
- Future image/report multimodal reasoning.
- Possible longitudinal-reasoning candidates.

High-level Public Health exploration may occur later, but no Public Health multi-engine design or implementation is authorized here.

MedGemma must not directly become authoritative for document identity, PHI/privacy decisions, persistent extraction results, terminology mappings, clinical diagnosis, final analytics, or indicators. A future `MedGemmaAdapter` or generic foundation-model adapter must translate raw outputs into source-grounded MedNexus candidate evidence with engine/version, configuration, input-policy, confidence semantics, and provenance. MedNexus validation and arbitration must decide whether any candidate is eligible.

MedNexus never approves “MedGemma” as a family in the abstract. `BENCHMARK` or `INTEGRATE` status must bind to an exact model, variant, version, artifact digest, adapter version, candidate-contract version, runtime configuration and quantization where relevant, applicable license/terms snapshot, validation dataset/version, and approved use scope. A new release or variant, material configuration or quantization change, adapter or contract change, or applicable terms change may require revalidation and reapproval. This reproducible approval rule applies to every external engine, not only MedGemma.

## 7. Unified Medical UAG and MedUAG strategy

**Unified Medical Understanding and Generation (UAG) engines** are a future engine class that may combine medical image understanding and generation, visual question answering, report generation, image synthesis, modality translation, reconstruction, prediction, and multimodal reasoning.

The research paper [“MedUAG: Unified Understanding and Generation for Medical Multimodal Models” (arXiv:2608.18937)](https://arxiv.org/abs/2608.18937) reports a corpus of more than six million instances across fourteen imaging modalities and a benchmark spanning medical understanding and generation tasks. This is research evidence, not MedNexus validation.

MedUAG status in MedNexus is **WATCH / BENCHMARK CANDIDATE / FUTURE ADAPTER CANDIDATE**. It is not an approved dependency. Before any benchmark or integration, MedNexus must independently verify:

- Official model and code availability.
- Weight provenance and versioning.
- License, redistribution, and commercial-use rights.
- Hardware/runtime requirements and reproducibility.
- Security, privacy, and data-egress implications.
- MedNexus-specific performance, calibration, and failure behavior.

MedNexus must remain independent of MedUAG or any single UAG implementation.

## 8. Radiology document intelligence plane

```text
Radiology Report
    ↓
MedNexus UNDERSTAND
    ├─ native deterministic/reference reasoning
    └─ optional external semantic candidate engine(s)
                 ↓
     MedNexus evidence eligibility and arbitration
                 ↓
Authoritative MedNexusDocumentContext
```

The frozen UNDERSTAND v1 rules continue to govern document identity, bounded context, semantic roles, `OTHER`/`UNKNOWN`, provenance, confidence, and review. External candidates cannot bypass semantic-role and current-study eligibility rules, inflate authority through duplication, or introduce EXTRACT-level facts into UNDERSTAND.

## 9. Radiology imaging intelligence plane

```text
DICOM / governed medical imaging input
    ↓
Approved imaging engine adapter(s)
    ↓
Candidate imaging observations, representations,
or explicitly authorized transformations
    ↓
MedNexus provenance, eligibility, safety, and review controls
```

The imaging plane is planned. No image ingestion, model, interpretation, reconstruction, enhancement, or generation capability is claimed as implemented. Imaging transformations must preserve source lineage and must never be confused with original clinical images.

Document and imaging planes may later converge only in a MedNexus-owned multimodal layer. Neither plane gains authority merely because the other agrees.

## 10. Evidence Fusion & Arbitration

**MedNexus Evidence Fusion & Arbitration** is the proposed proprietary decision layer for reasoning across:

- Document structure and semantic roles.
- Governed reference knowledge.
- Native MedNexus reasoning.
- Model-generated candidate evidence.
- Imaging-derived candidate evidence.
- Extraction evidence where stage-appropriate.
- Provenance and source authority.
- Source-specific confidence and calibration.
- Temporal and longitudinal context.

It must support agreement, disagreement, concordance, discordance, authority hierarchy, conflict resolution, abstention, and human-review routing.

It is not majority voting. Agreement may increase support, but agreement alone does not establish clinical truth. Correlated engines may repeat the same error. A high-confidence external model may not override higher-authority document evidence solely because its numerical confidence is high. Confidence values with different semantics are not directly comparable without validated calibration.

Fusion decisions must retain the original candidates, their sources, eligibility outcomes, conflicts, and final authority rationale. This capability is planned and not implemented.

Fusion authority is stage-scoped and acyclic. Evidence generated downstream must not silently flow backward and rewrite an already authoritative upstream decision; in particular, EXTRACT evidence cannot silently rewrite UNDERSTAND authority. If later evidence justifies reconsideration, it must enter an explicit MedNexus reprocessing or review mechanism that is deliberate, versioned, provenance-preserving, auditable, and review-governed. This strategy does not prescribe that future mechanism.

Future evidence contracts must preserve evidence identity, source identity, dependency and lineage, and correlation/family identity. One underlying signal cannot be counted repeatedly merely because it appears through deterministic matching, reference mappings, multiple adapters, derivative models, models sharing an upstream foundation, or transformed copies. **Correlated evidence is not independent corroboration. Model consensus does not establish truth. Raw engine confidence and MedNexus-calibrated support are distinct concepts and must never be conflated.**

## 11. Image-Report Concordance

**MedNexus Image-Report Concordance** is a future Radiology decision-support capability:

```text
DICOM Images                         Radiology Report
     ↓                                      ↓
Imaging engine candidate             MedNexus document
observations                         intelligence/assertions
     └──────────────────┬───────────────────┘
                        ↓
             Concordance evaluation
                        ↓
       Governed concordance outcome
                        ↓
           Confidence, provenance, review
```

Potential uses include report/image disagreement detection, review of potentially unsupported assertions, review of potentially omitted observations, longitudinal comparison support, quality assurance, and concordance analytics.

Concordance output remains review-oriented decision support until clinically validated and all applicable regulatory, privacy, quality, and human-oversight requirements are satisfied. A discordance is not itself a diagnosis, report correction, or final clinical truth.

The future minimum outcome model is:

| Outcome | Safety meaning |
|---|---|
| `CONCORDANT` | Governed image and report evidence support the same bounded assertion; agreement increases support but does not independently establish truth |
| `DISCORDANT` | Eligible image and report evidence conflict materially and require an explicit review disposition |
| `UNSUPPORTED_REPORT_ASSERTION` | The imaging evidence does not support a report assertion under the validated capability; this is a review signal, not proof that the signed report is incorrect |
| `POSSIBLE_OMITTED_IMAGE_OBSERVATION` | Eligible imaging evidence suggests a potentially relevant observation absent from the report; this is a review signal, not proof of an omission |
| `INDETERMINATE` | Evidence is insufficient, incomparable, out of scope, technically limited, or unresolved; route to human review where appropriate |

Failure of an imaging model to detect something mentioned in a report does not establish that the report is incorrect. An imaging-model observation absent from the report does not establish a reporting omission. No concordance outcome may automatically rewrite a signed report, create a diagnosis, delete an assertion, or create an authoritative persistent clinical fact without an appropriately validated MedNexus downstream workflow.

Concordance provenance must eventually preserve the applicable unit of analysis: patient, encounter, study, series, image, and report version. Evidence from different units or versions cannot be compared as though it described the same clinical object.

## 12. PROTECT boundary

PROTECT remains MedNexus-owned. External foundation or imaging models cannot replace the Clinical Privacy Policy Engine or select their own privacy rules.

The **Engine Data-Access Preflight** is a cross-cutting, PROTECT-owned authorization gate invoked before clinical input is exposed to any external engine, including an engine contributing candidates during UNDERSTAND. It evaluates, as applicable: data classification; PHI/PII exposure; exact engine and version; local or remote execution; approved environment; permitted data types, MedNexus stage, and capability; jurisdiction and residency; retention and logging; data egress; and applicable license, policy, and use restrictions.

```text
Raw clinical input
    ↓
Engine Data-Access Preflight decision
    ↓
Specific authorization and engine policy route
    ↓
Authorized local or remote engine(s)
```

Future engine routing uses the policy states `LOCAL_ALLOWED`, `REMOTE_ALLOWED`, `RESTRICTED`, and `DENIED`, aligned with the planned Protected Execution Envelope direction. Local execution is preferred where policy or privacy requires it, but locality alone does not establish compliance. Data minimization, purpose, jurisdiction, access, retention, logging, contractual terms, and runtime security still apply.

The preflight is not the completion of public Stage 02 PROTECT, does not produce final protected output, and does not reorder MEDNEXUS⁷. It grants or denies only the specific contemplated exposure under the specific execution context. No external engine may receive raw clinical content merely because it participates in UNDERSTAND. A changed engine, version, deployment, data type, purpose, stage, capability, or execution context requires a compatible authorization decision.

The accepted Phase 1 path remains unchanged: Detection → Unified Intelligence → Purpose-Based Policy Engine → `MedNexusOutputBuilder` → MedNexus-owned output. OpenMed remains candidate-only and its `deidentified_text` remains non-authoritative.

## 13. EXTRACT and STANDARDIZE boundaries

External models may generate candidate structured extraction, but the frozen Clinical Extraction Contract remains authoritative:

```text
Candidate extraction
    ↓
Source grounding
    ↓
MedNexus validation and role eligibility
    ↓
Provenance and confidence assessment
    ↓
MedNexus extraction result
```

No unsupported model-generated fact may become authoritative persistent clinical data. EXTRACT remains terminology-independent, preserves per-field provenance/confidence, and retains `extraction_review_required` separately from UNDERSTAND review.

STANDARDIZE remains MedNexus-owned and governed. Models may suggest mapping candidates, but authoritative mapping uses approved, versioned, licensed terminology/reference services such as SNOMED CT, LOINC, RadLex, DICOM terminology, and ICD according to domain rules. Mapping failure must not erase extraction or change extraction confidence.

## 14. MedNexus proprietary value layer

MedNexus differentiation is not access to a foundation model. It is the governed system that turns heterogeneous evidence into durable, provenance-aware clinical intelligence through:

- Stable clinical and document contracts.
- Role-aware evidence eligibility and authority.
- Privacy and purpose-of-use governance.
- Conflict resolution, abstention, and human-review states.
- Source grounding and reproducible provenance.
- Governed terminology standardization.
- Persistent structured clinical data.
- Longitudinal intelligence and cross-document relationships.
- Validated analytics, visualizations, and indicators.

External engines remain replaceable contributors. MedNexus retains the durable data, decision, validation, and product layer.

## 15. ANALYZE, VISUALIZE, and INDICATORS strategy

After STANDARDIZE, stages 05–07 form a major MedNexus-owned product layer. Future Radiology possibilities include modality utilization, examination and body-region distribution, contrast utilization, finding prevalence, incidental-finding analysis, recommendation/follow-up analysis, longitudinal change, report-turnaround/workflow analytics when valid metadata exists, quality/concordance analytics, and population-level Radiology intelligence.

These are future examples, not implementation claims. ANALYZE must operate over governed structured data; VISUALIZE must present authoritative outputs without recomputing upstream decisions; INDICATORS must remain traceable to governed facts and definitions.

## 16. Engine lifecycle

Every external engine is replaceable and has an explicit lifecycle state:

| State | Meaning |
|---|---|
| `INTEGRATE` | Independently verified for a defined, bounded MedNexus candidate role with approved license, policy route, provenance, validation, and operational controls |
| `BENCHMARK` | Under independent evaluation against MedNexus acceptance datasets; not authoritative |
| `WATCH` | Promising research or model direction lacking sufficient availability, rights, reproducibility, validation, or strategic fit |
| `REJECT` | Fails licensing, privacy, safety, performance, maintainability, reproducibility, or strategic-value criteria |
| `RETIRE` | Previously used engine removed from active routing with preserved decision/version provenance and a controlled replacement path |

Lifecycle changes require recorded evidence and governance review. No external engine may become an irreversible architectural dependency.

## 17. Validation strategy

The accepted working regression baseline before this architecture-only task is **950 passed, 8 warnings, 0 failures**. It is unchanged and was not re-run for documentation work.

When authorized real-world Radiology acceptance data becomes available, use a future multi-arm benchmark:

- **A — MedNexus Native:** current governed deterministic/reference-driven path.
- **B — External Foundation Model Native:** isolated candidate engine evaluated without MedNexus fusion.
- **C — MedNexus Hybrid:** native path plus external candidates through MedNexus eligibility and arbitration.
- Additional approved imaging/UAG engines may appear as separate experimental arms.

Primary questions:

- Does an external engine improve recall on difficult or ambiguous cases?
- Does it increase false authoritative assertions?
- Does hybrid arbitration improve calibrated accuracy?
- Does it preserve safe abstention and human-review behavior?
- Can every accepted output be grounded to source evidence?
- What latency, hardware, operational, privacy, and security costs arise?
- Are licensing and commercial-use terms compatible with intended deployment?

Future benchmarks should use locked acceptance sets and explicit leakage controls; report modality, site/source, and language slices where relevant; assess calibration and confidence intervals; stratify failure severity; and monitor model, adapter, configuration, and version drift. These are planned benchmark requirements and are not represented as implemented validation infrastructure.

The objective is not to prove that MedNexus beats every foundation model. It is to determine whether MedNexus orchestration, governance, and evidence arbitration produce a safer and more useful system than direct model use.

MedNexus is currently awaiting responses or approval from external real-world Radiology dataset providers. Architecture work continues without inventing provider outcomes or dates; real-world Radiology data remains the primary acceptance benchmark.

## 18. Synthetic-data policy

Unified medical generation may later support controlled synthetic-data augmentation for stress testing, rare-case generation, conformance testing, image/report pair augmentation, and robustness evaluation.

Synthetic data must:

- Carry explicit synthetic provenance and generation configuration.
- Remain segregated from real clinical acceptance data.
- Never be silently presented as real or independently observed clinical evidence.
- Be reviewed for privacy leakage, memorization, clinical plausibility, bias, and unsafe artifacts.
- Never replace real-world acceptance data.

Generated or transformed images and reports must preserve immutable lineage to distinguish source, derivative, and synthetic artifacts.

## 19. Capability status matrix

| Capability | Status | Meaning |
|---|---|---|
| MedNexus deterministic/reference-driven Radiology UNDERSTAND | **CURRENT** | Governed implementation exists; frozen contracts and current code determine actual scope |
| MedNexus Clinical Privacy Policy Engine | **CURRENT** | Accepted Phase 1 PROTECT foundation; not production certification |
| MedNexus Medical Intelligence Gateway | **PLANNED** | Architecture concept only; no interface or registry implemented |
| Engine Capability Registry | **PLANNED** | Metadata and governance concept only |
| MedGemma candidate adapter and benchmark | **PLANNED** | Candidate-only technical spike and evaluation, subject to approval |
| MedNexus Evidence Fusion & Arbitration | **PLANNED** | Proprietary arbitration prototype after candidate adapters exist |
| Radiology imaging-intelligence plane | **FUTURE** | Requires governed image ingestion, engine validation, privacy, and operational controls |
| Image-Report Concordance | **FUTURE** | Review-oriented prototype only after both planes are validated |
| MedUAG / UAG-class engine | **RESEARCH / WATCH** | Benchmark or future adapter candidate pending independent due diligence |
| Synthetic image/report augmentation | **RESEARCH / FUTURE** | Controlled validation support; never replaces real acceptance data |
| Radiology ANALYZE/VISUALIZE/INDICATORS layer | **FUTURE** | Built over governed standardized clinical data; not current functionality |
| Public Health multi-engine capability | **FUTURE** | Compatibility preserved; no implementation or detailed design in this milestone |

## 20. Risks and architectural guardrails

- MedNexus is model-agnostic; every external model is replaceable.
- Models generate candidate evidence; MedNexus determines authority.
- No external model owns a MedNexus clinical data contract.
- No model confidence score alone establishes clinical truth.
- Unsupported model-generated facts cannot become authoritative persistent data.
- Reference matches establish possible meaning, not document-specific semantic role or authority.
- PROTECT remains MedNexus-owned; engines cannot bypass policy routing.
- STANDARDIZE remains governed, versioned, licensed, and provenance-aware.
- Every engine output requires reproducible version and execution provenance.
- Engine licensing, commercial rights, distribution limits, and attribution must be tracked.
- Real-world validation remains mandatory; synthetic data cannot replace it.
- Local execution is preferred where policy requires it, but does not automatically establish compliance.
- Human review and abstention remain explicit system states.
- Cross-engine agreement is support, not proof of clinical truth.
- Prompt, model, adapter, calibration, and runtime changes are versioned changes.
- Clinical documents, embedded text, image metadata, retrieved content, and external-engine responses are untrusted data, not trusted system instructions. Future adapters and orchestration must defend against prompt or instruction injection originating from clinical content.
- Generated/transformed artifacts must never be confused with original clinical source data.
- MedNexus must not become a thin wrapper around foundation models.

## 21. Near-term implementation roadmap

This roadmap proposes sequence only. It authorizes no implementation, dependency installation, model download, test change, reference-data change, or production behavior change.

| Milestone | Proposed outcome |
|---|---|
| **M0 — Architecture documentation and governance** | Finalize the accepted direction as a documentation checkpoint; confirm frozen-contract compatibility and cross-track implications |
| **M1 — MedGemma local technical spike** | Isolated, non-production environment; verify license, reproducibility, hardware, privacy posture, and candidate output behavior |
| **M2 — Generic Medical Intelligence Engine interface** | Stable candidate-only adapter contract, capability metadata, failure isolation, and provenance envelope |
| **M3 — MedGemma Adapter** | Candidate-only Radiology adapter; no authority or direct persistence |
| **M4 — Native vs MedGemma vs Hybrid benchmark** | Controlled multi-arm Radiology evaluation with real-world acceptance data when authorized |
| **M5 — Evidence Fusion & Arbitration prototype** | Source-aware eligibility, conflict, abstention, and review routing without majority-vote authority |
| **M6 — Imaging Intelligence experimental plane** | Governed image-ingestion experiment and approved imaging-engine adapters |
| **M7 — Image-Report Concordance prototype** | Review-oriented concordance/discordance over validated document and imaging candidates |
| **M8 — UAG-class evaluation** | Evaluate systems such as MedUAG only when legally and technically available and reproducible |
| **M9 — Radiology analytics layer** | Build traceable Radiology intelligence over governed standardized clinical data |

Public Health multi-engine implementation is explicitly outside this roadmap execution window. Its future compatibility must be preserved through generic engine and evidence contracts rather than Radiology-specific coupling.

Any milestone that changes shared contracts, reaches a stable checkpoint, creates a cross-track dependency, or precedes integration requires the established Cross-Track Sync Brief and human architecture review.
