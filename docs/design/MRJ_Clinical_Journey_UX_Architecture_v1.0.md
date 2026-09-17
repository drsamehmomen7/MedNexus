# MRJ Clinical Journey UX Architecture

**Version:** 1.0
**Status:** ACCEPTED — R0 RADIOLOGY HORIZONTAL ARCHITECTURE CHECKPOINT
**Date:** 17 September 2026
**Active domain:** Radiology only
**Document type:** Accepted UX architecture authority; no frontend implementation claim

## 1. Purpose

This document defines the accepted user-experience architecture for one continuous MRJ Radiology clinical journey:

```text
UNDERSTAND → PROTECT → EXTRACT → STANDARDIZE
           → ANALYZE → VISUALIZE → INDICATORS
```

The seven stages must feel like one clinical application workflow, not seven unrelated pages or tools. This document does not change the accepted `/understanding`, `/privacy`, Landing/Hero, route, API, or backend implementation.

### 1.1 Authority relationship

This document is authoritative within the accepted R0 package for the interaction model, shared workspace behavior, Journey Rail, and report-centric → collection-centric UX transition. It presents but does not redefine the stage contracts owned by the Seven-Stage Contracts, the cross-domain extraction concepts owned by the Domain Clinical Extraction Architecture, or the `RadiologyFinding`/analytics contracts owned by the Radiology Intelligence Pack.

## 2. Governing experience principles

1. **The medical report remains the protagonist.**
2. **Clinical meaning comes before operational counts.**
3. **One journey, one run context, one status language.**
4. **Report-centric work transitions explicitly to collection-centric intelligence.**
5. **Automation is preferred when safe; review remains explicit.**
6. **Missing, unknown, blocked, failed, and review-required are distinct.**
7. **Motion reflects real work and never simulates progress.**
8. **Evidence and provenance remain available without overwhelming the normal workflow.**
9. **Clinical results favor readability, stability, and broad-audience comprehension.**
10. **The UI never claims a capability or stage output that the backend has not produced.**

## 3. Relationship to accepted experience

The accepted workspace architecture reuses rather than replaces established patterns:

- The accepted UNDERSTAND Single + Batch report navigator and shared Report Card establish the report identity/navigation model.
- The current PROTECT privacy engine and same-document handoff remain authoritative.
- The accepted MRJ visual direction remains clinical, premium, calm, serious, and human-centered, using warm paper/cream surfaces, charcoal text, restrained teal, and the configured Mona Sans-first stack.
- Technical Details remain absent from normal UNDERSTAND UI. Future stage evidence may be progressively disclosed only where review or accountable interpretation requires it.

This accepted architecture does not reopen accepted UNDERSTAND visual or clinical tuning.

## 4. MRJ Clinical Journey Workspace

The accepted shell is:

```text
HEADER / RUN CONTEXT
  ↓
SEVEN-STAGE JOURNEY RAIL
  ↓
MAIN WORKSPACE
```

### 4.1 Header / Run Context

The header should identify:

- MRJ / Medical Report Journey
- current journey/run name or ID
- domain: Radiology
- mode: Single Report or Batch Reports
- report count after a run exists
- overall state
- policy/access status when relevant
- pause/resume/cancel actions only when supported
- last meaningful update

Internal IDs may be secondary. Clinical users should first understand what is being processed and whether intervention is required.

### 4.2 Seven-Stage Journey Rail

The rail presents the fixed seven public stages in order. INGEST is not shown as a stage.

```text
UNDERSTAND   10/10 COMPLETE
PROTECT      10/10 COMPLETE
EXTRACT       7/10 PROCESSING
STANDARDIZE   Waiting
ANALYZE       Waiting
VISUALIZE     Waiting
INDICATORS    Waiting
```

The display is conceptual; labels and counts must derive from real state. Before a run exists, the rail shows stage names/readiness, not meaningless `0/0` values.

### 4.3 Main Workspace

For Stages 01–04:

```text
LEFT:  Report Navigator
RIGHT: Current Stage Workspace
```

For Stages 05–07:

```text
LEFT:  Collection / Analysis Navigator
RIGHT: Collective Clinical Intelligence Workspace
```

The transition between these modes is explicit and occurs through the Report Collection boundary after STANDARDIZE.

## 5. Continuous journey behavior

The preferred primary action is **Run Clinical Journey**.

When prerequisites are met, the application advances automatically:

```text
Understanding reports...        COMPLETE
Protecting clinical identity... COMPLETE
Extracting clinical findings... PROCESSING
Standardizing concepts...       QUEUED
Building clinical collection... NOT_STARTED
Analyzing clinical patterns...  NOT_STARTED
Generating visual intelligence... NOT_STARTED
Calculating clinical indicators... NOT_STARTED
```

The application pauses only when:

- human review is required;
- a policy choice is required;
- a failure blocks safe continuation;
- the user explicitly chooses to pause.

No unnecessary “Continue” action should separate stages that are eligible for safe automatic progression.

## 6. Shared state presentation

The shared stage states are:

```text
NOT_STARTED
QUEUED
PROCESSING
COMPLETE
NEEDS_REVIEW
FAILED
BLOCKED
```

### 6.1 State language

| State | User-facing intent |
|---|---|
| `NOT_STARTED` | This stage has not begun |
| `QUEUED` | Ready and waiting to run |
| `PROCESSING` | Real work is currently executing |
| `COMPLETE` | The required stage result is available |
| `NEEDS_REVIEW` | A result exists but requires human review |
| `FAILED` | Processing ended without a valid result; retry may be available |
| `BLOCKED` | A prerequisite, policy, dependency, or safety gate prevents processing |

States must be expressed with text and accessible icons, not color alone.

### 6.2 Scope

State exists at:

- Report + Stage
- JourneyRun aggregate
- Collection build/update
- Collection + Stage for ANALYZE/VISUALIZE/INDICATORS

Aggregate status never hides report-level exceptions. A run may be complete with exclusions, but those exclusions and reasons remain visible.

## 7. Report navigator

Stages 01–04 reuse the accepted UNDERSTAND interaction model:

- compact report cards/rows;
- stable source order and report identity;
- original filename when available;
- current stage state;
- concise review/failure warning;
- previous/next navigation;
- one selected report and one full result panel;
- responsive stacking on narrow screens.

The navigator must not be redesigned independently for every stage. Stage-specific state appears within the same stable report identity model.

## 8. Stage 01 — UNDERSTAND workspace

The accepted workspace remains the Stage 01 baseline:

- Single Report and bounded Batch Reports modes
- authoritative document identity
- compact high-value Radiology context
- recognized structure
- recognition evidence
- report-by-report review
- Single → PROTECT handoff
- no Technical Details in normal UI

This UX architecture adds only the surrounding continuous-journey concept. It does not reopen result hierarchy, recognition evidence, clinical logic, or batch behavior.

## 9. Stage 02 — PROTECT workspace

### 9.1 Primary purpose

Communicate that identity is protected under a selected purpose-based policy while preserving permitted clinical analytical utility.

### 9.2 Selected-report hierarchy

1. Protection status
2. Selected privacy policy/purpose
3. Safe analytical context retained, only when actually produced
4. Summary of protected entity categories
5. Warnings and review requirement
6. Protected output access/copy/download actions when supported
7. Provenance and advanced details only when needed

Do not expose overwhelming PHI detector internals during the normal successful flow. Detailed evidence should be review-oriented and access-controlled.

### 9.3 Batch behavior

R1 must preserve every report and apply the authoritative Phase 1 pipeline independently. It may not silently process only the first report, build a second privacy pipeline, or use external-engine de-identified text as final output.

### 9.4 Truthfulness

Age bands, safe dates, generalized geography, and pseudonymous subject keys may be displayed only when genuinely implemented and returned under policy. Planned transformations must not be simulated.

## 10. Stage 03 — EXTRACT workspace

EXTRACT is the first strongly clinical intelligence view.

### 10.1 Primary hierarchy

1. Extraction status and review state
2. Number of accepted/partial findings, with coverage context
3. Clinical finding cards
4. EXTRACT-assembled Common Clinical Context when available and permitted
5. Warnings/unknowns
6. Evidence/provenance disclosure for review

### 10.2 Finding card

```text
Finding 01
Bone marrow lesion

Anatomy        Right femoral neck
Measurement    8 mm
Presence       Present
Certainty      High, if supported
Confidence     High

Source evidence
“...”
```

The example demonstrates hierarchy, not a hard-coded clinical value.

Cards must:

- use human-readable labels;
- omit or mark unavailable fields rather than invent them;
- distinguish absent/negated from missing;
- show current findings separately from comparison/history/recommendations;
- retain a path to exact source evidence and provenance;
- show review state without requiring raw JSON.

### 10.3 Partial extraction

Partial valid findings remain visible with their known fields. Unknown optional fields do not make the entire report appear failed. Rejected candidates remain hidden from ordinary results but are available to authorized review/audit where appropriate.

## 11. Stage 04 — STANDARDIZE workspace

STANDARDIZE should make the transformation from source fact to governed representation understandable.

```text
SOURCE
“focal marrow lesion”

CANONICAL
Bone marrow lesion

ANATOMY
Femoral neck

TERMINOLOGY
RadLex / SNOMED CT candidate or mapped concept

STATUS
Standardized / Unmapped / Needs Review
```

### 11.1 Primary hierarchy

1. Standardization coverage
2. Standardized findings
3. Unmapped/ambiguous facts requiring review
4. Unit normalization where applicable
5. Terminology provenance/version

The primary UI must not become a giant technical mapping table. A mapping failure retains the extracted fact and must not make it appear unrecognized.

## 12. Report-to-collection transition

After eligible report-level standardization, the workspace changes mode explicitly:

```text
REPORT INTELLIGENCE COMPLETE
        ↓
CREATE / BUILD CLINICAL COLLECTION
        ↓
COLLECTIVE CLINICAL INTELLIGENCE
```

This is a boundary operation, not an eighth stage.

### 12.1 Collection build view

Show:

- collection name
- collection definition ID/version
- structured clinical scope: domain, document type, modality, body region, procedure/study family, and time window where relevant
- inclusion and exclusion criteria
- source runs
- included reports
- excluded reports and reasons
- membership snapshot/digest and collection version
- unique subjects when safely/validly available
- eligible report count
- time window when defined
- extraction coverage
- standardization coverage
- collection version

The user must be able to understand why a report is included or excluded. A BatchRun is not automatically a ReportCollection.

### 12.2 Collection version changes

When reports are added, removed, reprocessed, or requalified, show that a new collection version will be produced. Existing analyses/indicators remain attached to the earlier version.

## 13. Stage 05 — ANALYZE workspace

ANALYZE is a clinical analysis workspace, not an operational processing dashboard.

Potential sections, only when supported by data and contract:

- Top Clinical Findings
- Finding Co-occurrence
- Anatomy/Finding Patterns
- Measurement Distribution
- Severity Distribution

These report-level views form **Required Clinical V0** and must remain available without demographics or subject linkage. **Enhanced Clinical V0** may add age- and sex-stratified report-level findings only when policy-safe context exists. Patient-level prevalence appears only when safe stable subject linkage, an explicit denominator, and a time window exist; it is not required for first horizontal acceptance.

### 13.1 Analysis result card

Each result should show:

- analysis name and clinical question
- result and level: report/patient/collection/population
- numerator and denominator where relevant
- eligible/excluded count
- collection ID/version
- analysis method/version
- coverage and uncertainty
- source facts/profile versions
- review/warning state

The interface must never label report frequency as patient or population prevalence.

For report-level finding frequency, the UI must present one contribution per eligible report per standardized finding concept under the indicator definition. Repetition in Findings and Impression is not displayed as two positive reports. Evidence views may still show both source spans.

## 14. Stage 06 — VISUALIZE workspace

Potential governed visualization cards include:

- Finding Frequency
- Age × Finding Heatmap
- Sex × Finding Distribution
- Finding Co-occurrence Matrix
- Clinical Finding Network
- Measurement Distribution
- Severity Distribution
- Temporal Trend

Each visualization carries:

- cohort/collection context
- declared analytical level
- denominator where applicable
- data coverage/exclusions
- collection version
- source analysis reference
- accessible text/table alternative

VISUALIZE may choose presentation but may not perform undisclosed new analysis or create facts not present in its `ClinicalAnalysisResult` input.

## 15. Stage 07 — INDICATORS workspace

Indicators are governed clinical objects, not decorative KPI tiles.

```text
MENISCAL TEAR FREQUENCY
39.1%
34 / 87 eligible reports

Clinical scope      MRI Knee
Level               Report-level
Collection          MRI Knee Cohort V1
Evidence coverage   ...
```

The example is illustrative only and must never be seeded as an outcome.

### 15.1 Indicator hierarchy

1. Indicator name and clinical meaning
2. Value with numerator/denominator and unit
3. Level and eligibility criteria
4. Clinical scope/time window
5. Collection/version
6. Coverage, exclusions, confidence/uncertainty
7. Definition/provenance

### 15.2 Categories

Clinical indicators are primary. Data and quality indicators appear as supporting context and must not dominate the page.

## 16. Clinical value over administrative metrics

The workspace may show processing totals, but the visual hierarchy must favor:

- structured findings;
- clinically meaningful patterns;
- governed denominators;
- uncertainty and coverage;
- traceable clinical indicators.

“20 CT reports” is processing context. “Finding X occurred in N of M eligible reports under Collection V” is a governed clinical result.

## 17. Review experience

### 17.1 Two review layers

- Document review belongs to UNDERSTAND/process context.
- Extraction review belongs to EXTRACT fact/field context.

The UI may summarize both but must preserve the distinct cause and provenance.

### 17.2 Review queue behavior

Review should identify:

- report and stage
- exact issue and safety impact
- source evidence
- affected field/fact
- candidate and MRJ decision where appropriate
- allowed reviewer actions
- downstream consequences
- audit trail

Human review cannot silently convert unsupported evidence into accepted data.

## 18. Error, blocker, and empty states

### 18.1 Failed

Explain what failed, which report/stage is affected, whether retry is safe, and whether other reports continued.

### 18.2 Blocked

Explain the prerequisite, policy, or safety gate. Do not present a disabled stage as “still processing.”

### 18.3 Needs Review

Show that a result exists but requires a decision before a defined downstream action.

### 18.4 No eligible data

Explain why an analysis or indicator is unavailable. Do not render a zero value that could be mistaken for a clinical result.

## 19. Motion and processing feedback

Motion must reflect actual processing events:

- Recognizing report...
- Protecting identity...
- Extracting clinical findings...
- Standardizing concepts...
- Building collection...
- Analyzing patterns...
- Generating visual intelligence...
- Calculating clinical indicators...

Requirements:

- no fake substeps;
- no artificial delay for animation;
- no stage completion before backend confirmation;
- results remain accessible without animation;
- reduced-motion support is mandatory;
- reading clinical text uses stable surfaces without decorative movement.

## 20. Automatic progression and user control

### 20.1 Automatic progression

Advance when:

- the prior stage output exists;
- the report/collection is eligible;
- privacy/access policy permits execution;
- the required profile/capability is available;
- no review gate blocks continuation.

### 20.2 User controls

Controls may include pause, resume, retry failed item, open review, exclude/include where authorized, and stop future stages. They must not imply rollback of immutable audit history.

### 20.3 No hidden destructive action

Excluding a report from a collection, changing a policy, or accepting a reviewed fact must show the effect and create a new governed version where applicable.

## 21. Responsive architecture

### 21.1 Desktop

- Persistent journey rail or clearly available stage navigation.
- Report/collection navigator beside the active workspace.
- Wide reading surface for clinical cards, evidence, and visualizations.

### 21.2 Tablet

- Journey rail may become horizontally scrollable or compact.
- Navigator may collapse into a report/collection selector.
- Stage status remains visible.

### 21.3 Mobile

- One primary task per viewport.
- Journey stage selector remains ordered and accessible.
- Report/collection selector precedes the result.
- Tables provide responsive alternatives.
- Critical status, denominator, and review state are never hidden behind hover.

## 22. Accessibility

- Keyboard access for stage navigation, report selection, review actions, and disclosures.
- Programmatic active stage and selected report/collection state.
- Text/icon/shape status cues; color is supplementary.
- Logical heading order and landmark regions.
- Visible focus states.
- Accessible chart descriptions and tabular alternatives.
- Sufficient contrast for paper surfaces and restrained teal/semantic states.
- Screen-reader announcements for genuine state transitions without excessive noise.

## 23. Provenance and technical detail disclosure

The normal UI presents human-readable evidence and clinically useful metadata. Authorized review/audit views may progressively reveal:

- canonical identifiers
- exact source offsets/spans
- pack/profile versions
- engine/adapter versions
- terminology source/version/mapping method
- validator and decision lineage
- collection and analysis versions

Raw internal data must not replace the primary clinical explanation.

## 24. Current, proposed, and unavailable labels

The workspace must distinguish:

- **Current/implemented** — actual backend-supported behavior.
- **Proposed** — architecture approved for design but not implemented.
- **Planned/future** — not available for use.
- **Blocked** — intended but currently prevented by a specific gate.
- **Research** — not a product capability.

MedGemma, Protected Execution Envelope, age derivation, generalized geography, date shifting, advanced association analysis, and future indicators must not appear as live unless implemented and validated.

## 25. Acceptance criteria for future implementation

The journey UX is conformant when:

1. Users experience one continuous seven-stage application.
2. Stages 01–04 reuse one report identity/navigation model.
3. The report-to-collection transition is explicit.
4. Stages 05–07 are collection-centric.
5. Shared statuses reflect real backend state.
6. No `0/0`, fake stage, fake delay, or seeded clinical outcome appears.
7. Partial failures and review do not silently discard eligible reports.
8. Clinical meaning, denominator, coverage, uncertainty, and provenance remain visible.
9. VISUALIZE performs no hidden analysis.
10. INDICATORS are governed objects, not unexplained KPI numbers.
11. The UI remains accessible and usable on desktop and mobile.
12. Existing UNDERSTAND/PROTECT functionality is preserved until explicitly migrated.

## 26. Acceptance and implementation gate

Human review accepted this UX architecture on 2026-09-17. It governs future Journey workspace implementation but does not itself authorize frontend, route, API, or stage implementation changes. The accepted UNDERSTAND Single + Batch workspace and current PROTECT experience remain the implemented baselines. R1 has not started.
