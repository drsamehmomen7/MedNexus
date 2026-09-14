# MedNexus Multi-Engine Medical Intelligence Strategy

## Version 1.1

**Public identity clarification — 13 September 2026:** MedNexus is now **MRJ — Medical Report Journey**. The report-centered product narrative is **REPORT | PATHWAY | OUTCOME**. The original acceptance date and strategy version below are preserved. This editorial identity synchronization changes no technical architecture, planned engine/component name, stage ownership, runtime status, safeguard, or frozen contract. MedNexus-named frozen artifacts continue to govern MRJ; their filenames, links and identifiers are intentionally retained.

**Status:** ACCEPTED ARCHITECTURE STRATEGY CHECKPOINT — v1.1

**Date:** 8 September 2026

**Scope:** Model-agnostic clinical intelligence, initially specialized in Radiology with Public Health second

**Implementation authorization:** None; this document records product and architecture direction only

Version 1.1 is the current accepted MedNexus Multi-Engine Medical Intelligence Strategy and the versioned successor to the accepted [Multi-Engine Medical Intelligence Strategy v1.0](MedNexus_Multi_Engine_Medical_Intelligence_Strategy_v1.0.md). Version 1.0 remains the immutable historical accepted predecessor and M0 architecture checkpoint, preserved unchanged. This successor updates project priority, the MedGemma experiment state, hardware sequencing, UI direction, and the near-term roadmap. It does not alter the frozen UNDERSTAND v1 authority package: [UNDERSTAND Domain Matrix v1.0](MedNexus_UNDERSTAND_Domain_Matrix_v1.0.md), [Blueprint v2.0](MedNexus_Enterprise_Architecture_and_Engineering_Blueprint_v2.0.docx), [Architecture Crosswalk v2.0](contracts/MedNexus_Architecture_Crosswalk_v2.0.md), [Clinical Semantic Context Contract v0.2](contracts/MedNexus_Clinical_Semantic_Context_Contract_v0.2.md), and [Clinical Extraction Contract v0.2](contracts/MedNexus_Clinical_Extraction_Contract_v0.2.md).

All safety, governance, privacy, provenance, validation, audit, and clinical-control requirements established in accepted Strategy v1.0 remain binding unless v1.1 explicitly supersedes a specific requirement. Version 1.1 extends and evolves v1.0; it does not silently weaken or discard accepted safeguards. Version 1.0 remains an immutable accepted historical checkpoint, and v1.1 is its approved versioned successor. The frozen UNDERSTAND v1 authority documents remain unchanged and continue to take precedence within their scope.

## 1. Strategic decision

MRJ is evolving into a model-agnostic, multi-engine clinical intelligence platform without becoming a thin wrapper around one model, vendor, or research system.

> **Models generate evidence. MRJ determines authority.**

External engines may contribute candidate semantic interpretations, document understanding, structured extraction, imaging observations, multimodal reasoning, report generation, reconstruction, enhancement, translation, synthetic augmentation, or other medically useful evidence. MRJ retains authority over context, evidence eligibility, orchestration, routing, validation, provenance, source hierarchy, arbitration, conflicts, abstention, human review, privacy and policy, extraction contracts, terminology governance, persistent structured clinical data, longitudinal intelligence, analytics, visualization, and indicators.

The existing reference-driven principle extends to every external and image-derived candidate:

> **Reference knowledge tells MRJ what concepts may mean; document structure and semantic context tell it what those concepts mean here; MRJ reasoning decides what is authoritative for this document.**

Fluency, model confidence, multimodality, or agreement between engines does not independently establish clinical truth.

## 2. Current product concentration

Near-term development is concentrated on two flagship clinical domains:

1. `RADIOLOGY` - primary current specialization and immediate maturity target.
2. `PUBLIC_HEALTH` - second strategic specialization and parallel product vertical.

The remaining approved domain architecture stays valid but does not dominate current positioning or near-term implementation. Radiology should reach strong end-to-end maturity before broad multi-engine expansion to other clinical domains.

The accepted Radiology working baseline remains **950 passed, 8 warnings, 0 failures**. This documentation task does not re-run or change it. The principal acceptance blocker is insufficient authorized real-world Radiology acceptance data, not the synthetic regression suite. MRJ is awaiting responses or sample information from external dataset providers; no approval, delivery, price, sample count, or acquisition outcome is inferred.

Real-world clinical Radiology reports remain the primary acceptance benchmark. Synthetic material remains secondary for adversarial, abstention, controlled-conformance, and stress testing and cannot replace real-world acceptance data.

## 3. Relationship to MRJ seven-stage journey

The authoritative public journey remains:

```text
01 UNDERSTAND
      ->
02 PROTECT
      ->
03 EXTRACT
      ->
04 STANDARDIZE
      ->
05 ANALYZE
      ->
06 VISUALIZE
      ->
07 INDICATORS
```

INGEST remains internal to UNDERSTAND. It covers file/text intake, extraction/parsing, and `DocumentContent` construction and is not an eighth public stage.

Multi-engine participation is a governed implementation option within an authorized stage. It cannot collapse UNDERSTAND into EXTRACT, bypass PROTECT, transfer terminology authority out of STANDARDIZE, or create authoritative analytical facts outside the MRJ seven-stage journey contracts.

## 4. MedNexus Medical Intelligence Gateway

The future **MedNexus Medical Intelligence Gateway** is a vendor- and model-agnostic engine integration and orchestration boundary. It is not implemented, is not merely a network proxy, is not a clinical authority, and does not replace the MedNexus Intelligence Core.

```text
MedicalIntelligenceEngine
    |
    +-- MedNexus Native Engine
    +-- OpenMed Candidate Engine
    +-- MedGemma Foundation Engine
    +-- Unified Medical Imaging / UAG Engine
    +-- Future Medical Engines
```

The Gateway should eventually provide stable request and response envelopes, capability discovery, policy eligibility, execution routing, timeouts, failure isolation, version capture, provenance, and conversion into MedNexus candidate contracts. Every engine remains replaceable, and engine failure must permit safe abstention, an approved fallback, or human review without changing authority rules.

### 4.1 Future Engine Capability Registry

Registration does not authorize use. A future registry should bind any approval to exact, reproducible metadata including:

- `engine_id` and `provider`.
- Exact `model_name`, model family/variant, and exact `model_version` / `model_revision`.
- `engine_type`.
- `supported_domains`, `supported_modalities`, `supported_capabilities`, `supported_input_types`, permitted MedNexus stages, and permitted candidate-output types.
- Local or remote `execution_mode`, deployment endpoint, jurisdiction/residency, retention, logging, and egress behavior.
- `privacy_classification` and policy route such as `LOCAL_ALLOWED`, `REMOTE_ALLOWED`, `RESTRICTED`, or `DENIED`.
- `licensing_status`, exact license/terms identity, `commercial_use_status`, distribution restrictions, attribution, intended use, and prohibited uses.
- `clinical_use_status`, such as research-only, decision-support candidate, or separately approved status.
- `validation_status`, dataset/version, scope, slices, owner, approval/expiry dates, drift state, and revalidation conditions.
- `known_limitations`, including declared modality, language, population, calibration, safety, and operational limitations.
- `provenance_requirements` and `confidence_semantics`, including MedNexus calibration status.
- `runtime_requirements`, including adapter, candidate-contract, prompt/configuration, dependency, dtype, quantization, memory, latency, and cost envelope.
- `hardware_requirements`.
- Artifact source, immutable revision/checkpoint, checksum or digest.
- Emergency-disable capability, rollback target, retirement state, and accountable owner.

No model family may be approved in the abstract. Registry governance must explicitly cover approval, revalidation, drift review, disabling an engine, rollback, and retirement, with accountable ownership for each action. A material change to model, revision, adapter, contract, prompt, runtime, quantization, terms, deployment, or scope may require revalidation.

## 5. MedGemma candidate strategy and M1.1 checkpoint

MedGemma remains a planned external candidate engine, not implemented MRJ intelligence. The durable experiment record is [MedGemma Technical Spike M1.1](../experiments/MedNexus_MedGemma_Technical_Spike_M1.1.md).

**Identifier note:** “MedGemma Technical Spike M1.1” is a historical experiment identifier from the prior v1.0 sequence. It is not roadmap milestone M1 of the current v1.1 roadmap and must not be interpreted in that namespace.

The verified target is `google/medgemma-1.5-4b-it`, official model version `1.5.0`, a Gemma 3-based 4B multimodal instruction-tuned medical model. M1.1 is **safely paused at the Hugging Face access and terms gate**. This is not an inference failure.

No immutable Hugging Face revision was obtained or guessed. No Colab GPU was allocated, model loaded, clinical inference run, model downloaded locally, dependency installed, PHI used, or unopened holdout inspected. A100/L4 availability, CUDA, PyTorch, Transformers, concrete resolved model/processor classes, VRAM, and latency were therefore not measured. No fallback model, quantization, dtype, GPU, or unofficial checkpoint was substituted.

The planned current official loading route is recorded, but remains unexecuted:

```python
from transformers import AutoProcessor, AutoModelForImageTextToText

processor = AutoProcessor.from_pretrained(
    "google/medgemma-1.5-4b-it",
    revision=IMMUTABLE_REVISION,
)

model = AutoModelForImageTextToText.from_pretrained(
    "google/medgemma-1.5-4b-it",
    revision=IMMUTABLE_REVISION,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)
```

Planned generation is deterministic with `do_sample=False` and the model's official greedy defaults where applicable. Installed library versions and resolved implementation classes must be captured from the eventual runtime rather than inferred.

### 5.1 Secure resumption gate

Future authorized resumption must:

1. Accept applicable HAI-DEF terms through the official gated model mechanism.
2. Use a fine-grained read-only Hugging Face token.
3. Store the token in Colab Secrets as `HF_TOKEN`.
4. Never place tokens in source, documentation, logs, conversations, screenshots, or notebook output.
5. Capture the immutable model revision after authenticated access.
6. Preserve exact model, version, revision, runtime, configuration, and terms provenance.

The current development laptop must not be forced into heavy local MedGemma deployment. The clean local spike should resume after the expected hardware migration unless a controlled cloud test is intentionally authorized first.

## 6. Candidate evidence and deterministic grounding

`MG-RAD-CANDIDATE-v0.2` is the current experimental candidate-only Radiology UNDERSTAND contract. MedGemma output remains bounded, non-authoritative evidence.

- Current-study identity is separated from recommendation, comparison, history, findings-only context, and unresolved evidence.
- Recommendation, comparison, and history cannot redefine the performed study.
- Evidence is returned as exact verbatim source quotes.
- The model never calculates character offsets.
- Quotes are never repaired, normalized, completed, paraphrased, or invented.
- The model does not produce MedNexus confidence scores.
- Output remains within UNDERSTAND and excludes diagnosis, treatment advice, and detailed EXTRACT behavior.

Allowed semantic roles are `CURRENT_STUDY`, `RECOMMENDATION`, `COMPARISON`, `HISTORY`, `FINDINGS`, and `UNRESOLVED`.

MedNexus owns deterministic evidence grounding. It locates each quote in the exact canonical source string and calculates offsets separately from raw model output:

| Outcome | Rule |
|---|---|
| `GROUNDED` | Exact quote occurs once; calculate its start and end offsets |
| `GROUNDING_FAILURE` | Exact quote does not occur; never repair it |
| `AMBIGUOUS_GROUNDING` | Exact quote occurs more than once and cannot be uniquely disambiguated; never select the first occurrence silently |

Lookup performs no Unicode, whitespace, punctuation, or newline normalization. Raw model output remains verbatim and immutable for evaluation.

After a harmless non-clinical smoke test succeeds, the designated first clinical candidate is the previously exposed and accepted de-identified `D:\MedNexus\Validation_Input\cr_chest.pdf`. It must not be opened or submitted during documentation work. The future Test 1 package includes exact extracted text, unchanged `MG-RAD-REPORT-v0.1`, `MG-RAD-CANDIDATE-v0.2`, the established MedNexus Native result, verbatim model output, deterministic grounding, and a scorecard for correctness, semantic role, grounding, unsupported assertions, hallucination, and incremental value. No unopened holdout or hidden answer key may be used.

## 7. MedUAG and unified medical understanding-generation engines

[MedUAG: Unified Understanding and Generation for Medical Multimodal Models](https://arxiv.org/abs/2608.18937) reports medical multimodal understanding, VQA, report generation, image synthesis, translation, reconstruction, prediction, synthetic augmentation, and more than six million instances across fourteen imaging modalities.

MRJ classifies MedUAG as **WATCH / BENCHMARK / FUTURE ADAPTER CANDIDATE**. This research evidence does not establish available production-ready weights, commercial rights, runtime suitability, reproducibility, MRJ validation, or integration. Independent verification of official model/code availability, artifact provenance, license and commercial/distribution rights, hardware, security, privacy, and clinical behavior is mandatory.

MedUAG represents the broader future engine class **Unified Medical Understanding and Generation Engines**. MRJ architecture remains independent of MedUAG itself.

## 8. Radiology multi-engine planes

### 8.1 Document Intelligence Plane

```text
Radiology Report
    ->
MedNexus UNDERSTAND
    ->
Native structure/reference/semantic reasoning
    +
optional approved candidate engines
    ->
MedNexus evidence eligibility and arbitration
    ->
Authoritative MedNexusDocumentContext
```

The frozen UNDERSTAND v1 rules continue to govern identity, bounded context, semantic roles, `OTHER`/`UNKNOWN`, provenance, confidence, and review. External candidates cannot inflate current-study authority, introduce EXTRACT facts, or bypass role eligibility.

### 8.2 Imaging Intelligence Plane

```text
DICOM / governed medical imaging
    ->
approved imaging engine adapters
    ->
candidate imaging evidence, representations,
or explicitly authorized transformations
    ->
MedNexus provenance, eligibility, safety, and review controls
```

The imaging plane is future. No image ingestion, interpretation, reconstruction, enhancement, generation, or translation capability is claimed as implemented. Original, transformed, derivative, and synthetic artifacts must retain distinct immutable lineage.

The planes may later converge only through a MRJ-owned multimodal intelligence layer.

## 9. MedNexus Evidence Fusion and Arbitration

Future MedNexus Evidence Fusion and Arbitration is a proprietary decision layer spanning document structure, semantic roles, reference knowledge, native evidence, external candidate evidence, imaging candidates, stage-appropriate extraction evidence, provenance, source authority, temporal context, confidence, and review state.

It should support agreement, disagreement, conflict resolution, image-report concordance and discordance, abstention, and human-review routing. It must not implement majority voting, confidence averaging, or model consensus as truth.

> **Agreement may increase support, but agreement alone does not establish clinical truth.**

> **A high-confidence external model cannot override higher-authority evidence solely because model confidence is high.**

Fusion remains stage-scoped and acyclic. Downstream evidence cannot silently rewrite upstream authority. Reconsideration requires explicit, versioned, auditable, provenance-preserving, review-governed reprocessing. Evidence identity, source, lineage, and correlation/family identity must prevent one underlying signal from being counted repeatedly. Raw engine confidence and MedNexus-calibrated support remain distinct.

For every authoritative MRJ decision involving candidate engines, the future audit record must retain or permit deterministic reconstruction of the original candidate outputs, candidate source and engine, exact engine version/revision, source evidence, evidence-eligibility outcomes, provenance, conflicts or disagreements, arbitration steps, abstention or review decisions, and the final authority rationale. Retaining only a final merged answer is insufficient; every authoritative result must remain auditable back to its contributing evidence.

## 10. Future Image-Report Concordance

```text
Medical Image                         Radiology Report
    ->                                     ->
Imaging engine candidates            MedNexus document intelligence
    ->                                     ->
              MedNexus Concordance
                       ->
       agreement / discordance / indeterminate
                       ->
          provenance, confidence, and review
```

Potential future uses include report/image disagreement review, potentially unsupported report assertion review, potentially omitted image observation review, longitudinal comparison support, quality assurance, and concordance analytics.

The future minimum outcome model is:

| Outcome | Conservative safety meaning |
|---|---|
| `CONCORDANT` | Governed image and report evidence support the same bounded assertion; agreement increases support but does not independently establish truth |
| `DISCORDANT` | Eligible image and report evidence conflict materially and require explicit human-review disposition |
| `UNSUPPORTED_REPORT_ASSERTION` | Imaging evidence does not support a report assertion within the validated capability; this is a review signal, not proof that the report is wrong |
| `POSSIBLE_OMITTED_IMAGE_OBSERVATION` | Eligible imaging evidence suggests a potentially relevant observation absent from the report; this is a review signal, not proof of a true missed diagnosis |
| `INDETERMINATE` | Evidence is insufficient, conflicting, incomparable, out of scope, technically limited, or unreliable; human-review routing remains available where appropriate |

These are decision-support and review states, not autonomous diagnostic conclusions. Concordance is not implemented. Future outcomes must preserve patient, encounter, study, series, image, and report-version scope; retain `INDETERMINATE`; route review explicitly; and never automatically rewrite a signed report, create a diagnosis, delete an assertion, or persist an authoritative fact.

## 11. PROTECT, EXTRACT, and STANDARDIZE authority

PROTECT remains MRJ-owned. External models do not replace the Clinical Privacy Policy Engine or choose privacy rules. Before any external engine receives clinical input, a PROTECT-owned Engine Data-Access Preflight must authorize the exact exposure, engine/version, environment, data type, stage/capability, jurisdiction/residency, retention/logging, egress, and policy/license route. This cross-cutting preflight does not complete Stage 02 PROTECT or reorder MRJ seven-stage journey. Local execution alone does not establish compliance.

The accepted Phase 1 authoritative path remains unchanged:

```text
Detection
    -> Unified Intelligence
    -> Purpose-Based Policy Engine
    -> MedNexusOutputBuilder
    -> MedNexus-owned protected/de-identified output
```

For document or text input, MedNexus deterministic and contextual detections and any permitted external detector candidates converge through the MedNexus Intelligence Core before policy decisions and final output construction. Pre-detection protection controls may govern whether an external detector is permitted to receive input; they do not transfer final privacy authority to that detector. OpenMed remains candidate-only, and its `deidentified_text` is not authoritative MedNexus output. No external model-generated de-identification text may silently replace MedNexus protection, policy, decision, or output authority.

External models may produce candidate structured extraction, but the Clinical Extraction Contract remains authoritative:

```text
Candidate extraction
    -> source grounding
    -> MedNexus validation and role eligibility
    -> provenance and confidence assessment
    -> MedNexus extraction result
```

Unsupported model-generated facts cannot silently become authoritative persistent clinical data. EXTRACT remains terminology-independent and preserves per-field provenance, confidence, and review.

STANDARDIZE remains MRJ-owned. Models may suggest terminology candidates, but authoritative mappings require governed, versioned, licensed terminology services. Mapping failure must not erase extraction or change extraction confidence.

## 12. MRJ proprietary value after STANDARDIZE

The product moat is not access to a foundation model. MRJ builds durable, provenance-aware clinical intelligence through:

- `05 ANALYZE`
- `06 VISUALIZE`
- `07 INDICATORS`

Future Radiology opportunities include examination and modality utilization, body-region and contrast distribution, finding prevalence, incidental findings, recommendation/follow-up analytics, longitudinal change, report/image concordance analytics, workflow analytics when valid metadata exists, and population-level Radiology intelligence. These are **FUTURE**, not current capabilities.

## 13. Engine lifecycle

| State | Meaning |
|---|---|
| `INTEGRATE` | Approved for an exact bounded candidate role with verified rights, policy, provenance, validation, and controls |
| `BENCHMARK` | Under controlled evaluation; never authoritative |
| `WATCH` | Promising but blocked by availability, rights, reproducibility, validation, or strategic fit |
| `REJECT / RETIRE` | Rejected or withdrawn with preserved provenance, disable controls, and a safe replacement path |

Each evaluation considers incremental clinical value, safety, hallucination, grounding, provenance, privacy, licensing and commercial rights, reproducibility, hardware, latency, maintainability, vendor lock-in, and strategic fit. Every engine remains replaceable.

## 14. Future validation strategy

When sufficient authorized real-world Radiology data becomes available, the benchmark should compare:

- **A - MedNexus Native**
- **B - External Foundation Model Native**, initially MedGemma where appropriate
- **C - MedNexus Hybrid**
- **D - Additional imaging/UAG experimental arms**, where legally and technically available

Evaluation may include domain/document identity, modality, anatomy, contrast, document type, extraction precision/recall, false authoritative assertions, hallucination, grounding, provenance, abstention, calibration, latency, hardware cost, privacy, and licensing implications. Locked-set/leakage controls, relevant modality/site/source/language slices, confidence intervals, failure-severity analysis, and version drift monitoring remain required future controls.

### 14.1 Synthetic-data governance

Synthetic data may support adversarial testing, conformance testing, stress testing, rare-case exploration, controlled augmentation, and robustness testing. Every synthetic or transformed artifact must carry explicit synthetic provenance and clear labeling, remain segregated from real-world acceptance data, and be traceable to its generation method, model, version, and configuration where applicable. Original, derived, transformed, and synthetic artifacts must remain distinguishable through preserved lineage.

Synthetic-data use requires review for privacy leakage, memorization risk, plausible clinical content, bias, and unsafe artifacts. Controls must prevent synthetic material from contaminating real-world acceptance sets or being presented as a genuine clinical record. Real-world clinical data remains the primary acceptance benchmark, and synthetic performance must never be reported as equivalent to real-world clinical validation.

The objective is not to make MRJ beat every foundation model. It is to determine whether MRJ orchestration, grounding, governance, provenance, and arbitration create a safer and more useful clinical intelligence system than direct model use.

The NLM Open-I/Indiana University collection may support future paired image/report research. Candidate case `CXR1108_IM-0075-1001` remains **BLOCKED** because case-level reuse and commercial permission were not conclusively verified. Collection-level public access does not establish commercial permission. No MIMIC-CXR material was used in the M1.1 experiment.

## 15. Hardware transition and UI direction

The project currently operates on an older development laptop. A stronger local development laptop is expected in approximately 21 days. Heavy local MedGemma deployment is deferred until that migration unless an appropriate controlled cloud test is explicitly authorized.

During the transition, priorities are documentation synchronization, product positioning, UI/UX redesign, dataset-acquisition follow-up, and preparation for later multi-engine work.

The next UI direction is strategic only and does not authorize frontend changes. MRJ will move away from the very-dark cinematic direction toward a light, clinical, calm, premium, professional, high-trust, spacious, simple, broad-audience experience. Near-term screens are:

1. Landing Page.
2. Radiology UNDERSTAND.
3. PROTECT / DE-ID.

The experience should emphasize Radiology, Public Health, MRJ seven-stage journey, multi-engine intelligence, governed evidence, structured clinical data, analytics, visualization, and indicators. The accepted UI/UX Blueprint v1.0 now carries the MRJ identity clarification. Existing uncommitted frontend work is preserved; further visual changes require a separate authorized task.

## 16. Current roadmap

The following sequence distinguishes planning from implementation. It authorizes no production change, dependency installation, model download, validation opening, or frontend implementation by itself.

The current roadmap uses its own M0-M14 namespace. The historical experiment label “MedGemma Technical Spike M1.1” is preserved unchanged from the prior sequence and does not denote the v1.1 roadmap's M1 UI/UX Design Blueprint; controlled MedGemma resumption is roadmap milestone M6.

| Milestone | Planned outcome |
|---|---|
| **M0** | Architecture and documentation synchronization |
| **M1** | UI/UX Design Blueprint |
| **M2** | Landing Page redesign |
| **M3** | Radiology UNDERSTAND UX redesign |
| **M4** | PROTECT / DE-ID UX redesign |
| **M5** | Hardware migration and stronger local environment |
| **M6** | Resume controlled MedGemma technical spike |
| **M7** | Generic Medical Intelligence Engine interface |
| **M8** | MedGemma candidate adapter |
| **M9** | Real-world Radiology benchmark: Native vs MedGemma vs Hybrid |
| **M10** | Evidence Fusion and Arbitration prototype |
| **M11** | Imaging Intelligence experimental plane |
| **M12** | Image-Report Concordance prototype |
| **M13** | UAG-class engine evaluation when technically and legally ready |
| **M14** | Radiology analytics over standardized clinical data |

Public Health remains the second flagship vertical. Multi-engine Public Health implementation follows Radiology maturity and must reuse generic engine/evidence contracts rather than introduce Radiology-specific coupling.

## 17. Capability status

| Capability | Status |
|---|---|
| MedNexus deterministic/reference-driven Radiology UNDERSTAND | **CURRENT** within code-verified scope |
| Clinical Privacy Policy Engine | **CURRENT** accepted Phase 1 POC foundation |
| MedNexus Medical Intelligence Gateway | **PLANNED** |
| Engine Capability Registry | **PLANNED** |
| MedGemma M1.1 runtime smoke | **PAUSED AT ACCESS/TERMS GATE** |
| `MG-RAD-CANDIDATE-v0.2` | **EXPERIMENTAL CONTRACT; NOT INTEGRATED** |
| Generic engine interface and MedGemma adapter | **PLANNED** |
| Evidence Fusion and Arbitration | **PLANNED** |
| Imaging Intelligence plane and Image-Report Concordance | **FUTURE** |
| MedUAG/UAG-class engines | **RESEARCH / WATCH** |
| Radiology analytics after STANDARDIZE | **FUTURE** |
| Public Health multi-engine implementation | **FUTURE AFTER RADIOLOGY MATURITY** |

## 18. Architecture guardrails

- Frozen UNDERSTAND v1 authority remains unchanged.
- Models generate candidates; MRJ determines authority.
- External engines cannot own MedNexus clinical contracts, privacy rules, terminology, persistence, or final decisions.
- Clinical documents, embedded text, image metadata, retrieved content, and model responses are untrusted data, never trusted instructions.
- No raw clinical exposure occurs without a PROTECT-owned engine data-access decision.
- No unsupported or ungrounded model fact becomes authoritative or persistent.
- Model confidence and engine agreement do not independently establish truth.
- Evidence remains source-grounded, provenance-preserving, role-qualified, correlation-aware, and stage-bounded.
- Real-world acceptance remains mandatory; synthetic data cannot replace it.
- No external engine becomes an irreversible dependency.
- Current, planned, research, future, and blocked states must remain explicit.

Any shared-contract change, stable checkpoint, cross-track dependency, or integration requires the established Cross-Track Sync Brief and human architecture review.
