# MRJ Radiology EXTRACT UX Contract

**Version:** 1.0
**Status:** ACCEPTED AND CLOSED
**Acceptance date:** 2026-09-24
**Date:** 24 September 2026
**Checkpoint:** R2.0A — Radiology Clinical Fact Contract + EXTRACT UX Contract
**Runtime status:** UX contract only; no frontend behavior is implemented

## 1. Purpose and authority

This document defines how a future Radiology EXTRACT result must appear inside the existing MRJ Clinical Journey Workspace. It refines Stage 03 UX under the accepted `MRJ_Clinical_Journey_UX_Architecture_v1.0.md` and consumes the proposed `MRJ_Radiology_Clinical_Fact_Contract_v1.0.md` without redefining clinical semantics.

The medical report remains the hero. EXTRACT is not a disconnected page, dashboard, model console, or generic entity viewer. This specification changes no current HTML, CSS, JavaScript, route, API, UNDERSTAND, or PROTECT behavior.

## 2. Experience objective

Within seconds, a user should be able to answer:

1. What clinically meaningful facts did MRJ extract?
2. Which facts are present, absent, uncertain, partial, or review-required?
3. Where in the protected report did each fact come from?
4. What privacy-safe context is available?
5. Can this report continue to STANDARDIZE?

Engine metrics, candidate objects, and raw JSON remain secondary audit material.

## 3. Journey integration

The fixed rail remains:

```text
UNDERSTAND → PROTECT → EXTRACT → STANDARDIZE
           → ANALYZE → VISUALIZE → INDICATORS
```

When EXTRACT is active:

- UNDERSTAND and PROTECT show their real retained states;
- EXTRACT shows its real state and is the active workspace;
- later stages remain truthful `NOT_STARTED`, `BLOCKED`, or other actual states;
- no frontend animation can mark a stage complete;
- document-level UNDERSTAND review and fact-level EXTRACT review remain distinct.

No unnecessary page transition or re-upload occurs. The selected report, JourneyRun, protected artifact, policy/access context, and stable report identity carry forward.

## 4. Stage eligibility expectation

R1 established that PROTECT eligibility does not imply EXTRACT eligibility. A future profile resolver may consider:

- authoritative `RADIOLOGY` domain;
- supported `RADIOLOGY_REPORT` profile;
- sufficient subdomain/family and context for that profile;
- protected/permitted input representation;
- usable source text;
- available pinned pack/profile version;
- unresolved review or policy gates.

`RADIOLOGY / UNKNOWN` may remain PROTECT-eligible while EXTRACT is review-required or blocked. `RADIOLOGY / OTHER` may use only a separately approved conservative generic Radiology profile. This contract does not implement final runtime rules.

## 5. Desktop workspace

The future Stage 03 desktop layout is a report-reading workspace:

```text
┌──────────────────────────────────────────────────────────────────┐
│ Journey Rail                                                     │
│ UNDERSTAND ✓  PROTECT ✓  EXTRACT ●  STANDARDIZE ○  ...         │
├───────────────────────────────┬──────────────────────────────────┤
│ Protected Report              │ Clinical Extraction              │
│                               │                                  │
│ Protected PDF / Text          │ Summary                          │
│ source evidence highlight     │ Finding filters                  │
│                               │ Clinical Finding cards           │
│                               │ Relationships                    │
│                               │ Clinical Context                 │
└───────────────────────────────┴──────────────────────────────────┘
```

The left reading surface and right clinical-fact surface remain visually linked. Exact ratios are responsive implementation decisions; this contract does not prescribe rigid pixels.

## 6. Primary information hierarchy

1. Selected report identity and EXTRACT state.
2. Compact extraction summary.
3. Clinical findings with unmistakable assertion state.
4. Direct connection from finding to source evidence.
5. Explicit source-supported relationships.
6. Privacy-safe clinical context.
7. Warnings, unknowns, and review actions.
8. Collapsed technical provenance/audit details.
9. Governed next-stage action.

## 7. Extraction summary

The summary uses clinical, mutually understood counts derived from canonical output:

```text
Clinical Extraction

14 Clinical Findings
Diagnoses       3
Negated         2
Measured        2
Needs Review    1
```

Count semantics:

| Count | Meaning |
|---|---|
| Clinical Findings | Canonical accepted or partial `RadiologyFinding` objects; not raw candidates. |
| Diagnoses | Findings whose `semantic_class` is `DIAGNOSIS`. |
| Negated | Findings with `ABSENT_NEGATED`; never positive findings. |
| Measured | Findings with one or more valid owned measurements. |
| Needs Review | Findings/relations requiring explicit extraction review. |

Secondary descriptors overlap and are not additive partitions. One diagnosed finding may also be negated, measured, and review-required. The UI must not imply that Diagnoses + Negated + Measured + Needs Review equals the Clinical Findings total. The summary does not show engine precision, raw candidate count, token count, debug confidence, model identifiers, or ungrounded candidate totals.

## 8. Quick filters

V0 filters remain limited:

- **All**
- **Diagnoses**
- **Findings**
- **Present**
- **Negated**
- **Needs Review**

`PRESENT` is an assertion state and does not itself mean clinically abnormal. Filters change presentation only; they do not change canonical facts or stage state. Active filters are keyboard-accessible, announce result counts, and never hide the existence of unresolved review items.

## 9. Clinical Finding card

The normal card prioritizes meaning:

```text
Intraparenchymal Hemorrhage

DIAGNOSIS   PRESENT   HIGH CONFIDENCE

Anatomy       Right temporal lobe
Laterality    Right
Temporal      Acute
Measurement   28 mm

Evidence
“Acute right temporal intraparenchymal hemorrhage...”

Source
Findings
```

The card displays only supported fields. Unknown or restricted fields use human-readable states rather than invented values. Internal class names, candidate IDs, engine IDs, raw JSON, and numeric debug scores are absent from the normal card.

### 9.1 Assertion presentation

Assertion state is text-first and not color-only:

| Canonical state | User-facing behavior |
|---|---|
| `PRESENT` | Clear present/observed label. |
| `ABSENT_NEGATED` | Prominent **Absent / Not observed** treatment, visually distinct from positive findings. |
| `UNCERTAIN` | **Possible / Uncertain** with source-language explanation. |
| `CONDITIONAL` | **Conditional** with the stated condition where safely available. |
| `UNKNOWN` | **Assertion unresolved — review required**. |

Example negated card:

```text
Pneumothorax
ABSENT
Evidence: “No evidence of pneumothorax.”
```

It must not share the positive-abnormal visual treatment.

### 9.2 Review presentation

Example:

```text
Possible Subarachnoid Hemorrhage
NEEDS REVIEW

Reason
The report describes this finding as possible.

Evidence
“Cannot exclude a small subarachnoid hemorrhage.”
```

Human meaning precedes numeric confidence. Review controls must state their downstream consequence and cannot silently accept unsupported evidence.

## 10. Evidence interaction contract

Selecting a finding or relationship must connect the clinical fact to its source:

1. The selected card becomes programmatically active.
2. The Protected Report navigates to the best available source location.
3. The exact governed `evidence_span` is highlighted when technically possible.
4. The source section and quote remain visible in the fact panel.
5. If exact visual highlighting is unavailable—for example, because a rebuilt PDF cannot map text geometry—the UI navigates to a page/section where possible and presents the exact protected-text quote without pretending to highlight the PDF.
6. Multiple evidence spans are navigable in source order.
7. Highlighting never changes the source artifact or becomes persisted clinical annotation.

The interaction must let a non-technical reviewer answer “What did MRJ extract?” and “Where did it come from?” without opening Technical Details.

Evidence shown in the normal UI is the protected/permitted representation. Original PHI is not reintroduced.

## 11. Relationships view

V0 uses a readable list, not a force-directed graph:

```text
Hemorrhage
  associated with → Edema

Mass
  located at → Left frontal lobe

Mass
  measured as → 28 mm
```

Supported labels map directly to the bounded contract: Located at, Associated with, Suggestive of, Has attribute, and Measured as. Selecting a relation invokes the same evidence interaction and shows its explicit source span.

Canonical V0 relationships are source-explicit. An inferred engine candidate is not presented as an accepted relation. A future sophisticated graph visualization is deferred.

## 12. Clinical Context view

The view presents `CommonClinicalContext` and structured `ClinicalContextFact` items while preserving ownership, source role, and privacy state:

```text
Age                 76
Age Band            70–79
Sex                 Male
Study Date          2026-08-22
Clinical Indication Recent head trauma
Relevant History    Hypertension
```

Every populated value requires approved provenance. The UI distinguishes:

- **Available** — supported and permitted;
- **Unknown** — cannot be established safely;
- **Not stated** — absent from eligible source evidence;
- **Not available** — source/context unavailable;
- **Not applicable** — field does not apply;
- **Not retained for privacy reasons** — `RESTRICTED`.

Patient-derived values come only from `PatientAnalyticContext`. Structured clinical indication, symptom, history/comorbidity, and event/exposure items may come from eligible narrative evidence as `ClinicalContextFact`, but remain context rather than current findings. Their assertion, source evidence, and review state must remain available. Current R1 does not populate Patient Analytic Context; the UI must not simulate these example values.

## 13. Technical Details and audit disclosure

Technical Details remain collapsed by default and available only where permitted. They may show:

- canonical fact/relation IDs;
- exact source offsets and all evidence spans;
- extraction profile and pack versions;
- engine, model, adapter, configuration, and raw candidate confidence;
- MRJ confidence, grounding and validation state;
- mapping provenance only after STANDARDIZE;
- policy/access and stage-execution provenance.

The normal clinical result cannot be dominated by this material. Restricted source content remains access-controlled.

## 14. Batch UX

The accepted Report Navigator pattern remains stable:

```text
Report 01   12 facts   Complete
Report 02    8 facts   Needs Review
Report 03   15 facts   Complete
Report 04             Blocked
```

Selecting a report loads only that report's:

- Protected Report;
- extraction summary;
- findings and measurements;
- relationships;
- Common Clinical Context;
- warnings/review state;
- evidence and provenance.

No fact, context value, artifact URL, selection, or review action may leak across reports. One failed or blocked report does not discard eligible results. Aggregate counts never erase report-level review/failure. EXTRACT does not create a Report Collection or collection analytics.

## 15. Stage-state behavior

| State | User-facing EXTRACT behavior |
|---|---|
| `NOT_STARTED` | Explain that extraction has not begun and whether prerequisites are known. |
| `QUEUED` | Show that the report is eligible and waiting; no simulated output. |
| `PROCESSING` | Reflect real backend work; keep protected report stable and accessible. |
| `COMPLETE` | Canonical facts exist and passed the completion gate. |
| `NEEDS_REVIEW` | Useful output exists; show exact review scope and downstream consequence. |
| `FAILED` | No valid stage result; explain safe retry where available. |
| `BLOCKED` | Name the prerequisite, policy, unsupported profile, or safety gate. |

Document review from UNDERSTAND and extraction review remain separately labeled. A report may be privacy-protected yet blocked from a domain extraction profile.

## 16. Bottom action area

Complete example:

```text
Extraction Complete
12 Clinical Findings · 2 Relationships · 1 Needs Review

[Review Findings]  [Continue to Standardize]
```

Blocked example:

```text
Extraction unavailable
MRJ needs additional document review before domain-specific clinical
extraction can continue.
```

`Continue to Standardize` is available only when actual eligibility allows it. The action never implies that terminology mapping already occurred. Technical errors are translated into safe user-facing explanations with audit detail available separately.

## 17. Responsive principles

### Desktop

- Protected Report and Clinical Extraction remain visible side-by-side when space permits.
- Evidence selection keeps both source and fact context visible.
- Report Navigator remains stable for Batch.

### Tablet

- The navigator may collapse to a selector.
- Protected Report and Extraction may use adjacent tabs or a controlled split.
- Active stage and review state remain visible.

### Mobile

- One primary task per viewport.
- Order: stage/report identity → summary → findings → relationships → context → source evidence/action.
- A persistent, accessible action returns from a fact to source evidence.
- No critical state or evidence is hover-only.

## 18. Accessibility and motion

- Full keyboard operation for report selection, filters, finding cards, evidence navigation, review, and disclosures.
- Programmatic active stage, selected report, selected fact, and highlighted evidence state.
- Text/icon/shape status cues; color is supplementary.
- Logical landmarks and heading order.
- Visible focus and sufficient contrast.
- Screen-reader announcements only for real state changes.
- Stable reading surfaces; no decorative motion while reading clinical text.
- Reduced-motion support and no animation-dependent result access.

## 19. Truthfulness and unavailable capability

Until implemented, the UI must not display:

- fake facts, relationships, context values, or extraction progress;
- seeded summary counts;
- model-generated output as MRJ authority;
- terminology codes as if STANDARDIZE ran;
- age bands, safe dates, pseudonymous keys, or geography not returned by PROTECT;
- extraction controls on current production pages merely because this contract exists.

## 20. Future implementation acceptance criteria

A future EXTRACT UI conforms when:

1. it stays inside the continuous Journey Workspace;
2. the protected report remains the primary source surface;
3. facts are human-readable and assertion-safe;
4. every visible fact/relation has a usable path to source evidence;
5. negated facts cannot be mistaken for positive abnormalities;
6. uncertainty/review is clinically explained rather than reduced to a score;
7. context availability and privacy restriction are explicit;
8. Batch results preserve strict per-report ownership;
9. technical details are progressively disclosed;
10. stage states and bottom actions reflect real backend eligibility;
11. responsive and accessible behavior preserves the same meaning;
12. no collection analytics appear inside EXTRACT.

## 21. Acceptance gate

This document is the accepted R2.0A UX specification for future Stage 03 work. Its acceptance does not implement Stage 03, modify the current frontend, or select an extraction engine.
