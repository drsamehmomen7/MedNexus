# MEDNEXUS CLINICAL SEMANTIC CONTEXT CONTRACT

## Version 0.2

**Status:** FROZEN ARCHITECTURE AUTHORITY

**Date:** 23 August 2026

**Scope:** bounded output of UNDERSTAND, consumed by PROTECT and EXTRACT

This successor preserves [Clinical Semantic Context Contract v0.1](MedNexus_Clinical_Semantic_Context_Contract_v0.1.md) as architecture history. Version 0.2 narrows the contract so UNDERSTAND remains a Reference-Driven Document Context Layer rather than a clinical extractor.

## 1. Governing invariant

```text
Document
  → Document Identity
  → Supported Subdomain / Family, or OTHER
  → Approximately 3–4 approved light-context fields
  → Semantic regions and document relationships
  → Provenance, confidence, and review
  → Routing readiness for PROTECT and EXTRACT
```

UNDERSTAND does not emit save-ready clinical facts.

## 2. Conceptual top-level output

```text
MedNexusDocumentContext
  document_identity
  light_context
  semantic_regions
  semantic_relationships
  privacy_context
  processing_context
  provenance
```

### 2.1 Document identity

The identity component contains:

- `domain`
- `subdomain_or_family`
- `document_type`
- `language`
- recognition confidence and confidence band
- `document_review_required`

The domain must be one of:

```text
RADIOLOGY
PUBLIC_HEALTH
LABORATORY
ADMISSION
DISCHARGE
ICU
EMERGENCY
UNKNOWN
```

`PATHOLOGY` is future and is not part of the frozen current target enum. `UNKNOWN` is a safety outcome, not a domain implementation.

### 2.2 Subdomain safety

- Known domain plus supported subtype/family → return the governed value.
- Known domain plus unsupported or unsafe subtype/family → return `OTHER`.
- Domain itself not confidently established → return `UNKNOWN` and require review.
- Never guess an unsupported subtype.

## 3. Domain and workflow separation

`domain` describes the native document. A consuming application or workflow is separate metadata and cannot overwrite document identity.

- A Laboratory report used in Public Health remains `LABORATORY`.
- A native immunization/vaccination document is `PUBLIC_HEALTH / IMMUNIZATION` in the current product scope.
- `PUBLIC_HEALTH / LABORATORY_DERIVED_SURVEILLANCE` requires native Public Health surveillance/reporting identity plus laboratory-derived surveillance context.

## 4. Light Context Metadata

Each supported subtype/family may expose approximately three or four fields approved by the frozen Domain Matrix. Unknown values remain absent/null. Implementations must not grow an unbounded metadata dictionary as a competing contract.

### 4.1 Radiology typed context

| Subdomain/family | Approved light context |
|---|---|
| `CT` | body region; contrast context; CT/CTA family; bounded acquisition/phase summary |
| `MRI` | body region; contrast context; MRI/MRA/MRV family; sequence-family summary |
| `X_RAY` | current-study body region; study-level laterality; named views or view-count context; source CR/DX/XR type |
| `ULTRASOUND` | body region/organ system; complete/limited context; bounded technique context; measurement-bearing presence |
| Ultrasound/Doppler specialization | vascular territory; arterial/venous context; Doppler context; flow/velocity-measurement presence |
| `MAMMOGRAPHY` | screening/diagnostic context; laterality; view/tomosynthesis context; BI-RADS assessment presence |
| `NUCLEAR_MEDICINE` | family (`PLANAR`, `SPECT`, `PET`, `SPECT_CT`, `PET_CT`, `OTHER`); organ/body region; radiopharmaceutical-context presence; quantitative-uptake presence |
| `FLUOROSCOPY` | diagnostic study family; body system; contrast-study context; dynamic/functional context |
| `OTHER` | domain, `OTHER`, safe generic structure, provenance/review |

Diagnostic Fluoroscopy is distinct from image-guided interventional procedure documentation. Until an Interventional Radiology family is approved, clear Radiology interventional documents resolve to `RADIOLOGY / OTHER`.

### 4.2 Public Health typed context

| Subdomain/family | Approved light context |
|---|---|
| `NOTIFIABLE_DISEASE` | coarse condition family; case-status context; jurisdiction/geography context; event-versus-report-time context |
| `IMMUNIZATION` | coarse vaccine family; administration-event context; age-group context; jurisdiction/provider context |
| `SURVEILLANCE` | surveillance topic/family; reporting-period context; geographic scope; population-group context |
| `SYNDROMIC_SURVEILLANCE` | syndrome-group hint; time-window context; geographic scope; encounter/population setting |
| `OUTBREAK_CLUSTER` | event/cluster family; geography/facility context; time-window context; population/setting context |
| `LABORATORY_DERIVED_SURVEILLANCE` | surveillance test-family hint; specimen-context presence; result-polarity context; pathogen/disease-surveillance family |
| `OTHER` | domain, `OTHER`, safe generic structure, provenance/review |

Condition, vaccine, syndrome, test, and pathogen “family” values are coarse routing hints. Exact clinical names and codes are not UNDERSTAND output.

### 4.3 Catalogue-only domains

`LABORATORY`, `ADMISSION`, `DISCHARGE`, `ICU`, and `EMERGENCY` may carry generic identity, structure, provenance, confidence, and review context. Their detailed light-context schemas require later reference-driven matrices. Until then, implementations use their domain `OTHER` behavior rather than inventing subtype metadata.

## 5. Semantic regions and relationships

The shared optional vocabulary is:

| Role | Meaning |
|---|---|
| `STUDY_OR_EVENT_IDENTITY` | Performed study, public-health event, encounter, or document-family identity |
| `CLINICAL_OR_REPORTING_INDICATION` | Explicit reason the study/event/report exists |
| `TECHNIQUE_OR_ACQUISITION` | Acquisition, specimen/workflow method, or reporting process region |
| `OBSERVATION_NARRATIVE` | Findings, results narrative, surveillance observations, or event description |
| `CONCLUSION_OR_STATUS` | Impression, conclusion, assessment, case status, or summary |
| `COMPARISON_OR_PRIOR_CONTEXT` | Prior study, prior period, baseline, or historical comparison |
| `RECOMMENDATION_OR_FUTURE_ACTION` | Recommended future study/action, follow-up, control action, or plan |
| `PROFESSIONAL_OR_AUTHORITY_AUTHENTICATION` | Author, interpreter, authority, jurisdiction, signature, or attestation |

Each region retains its canonical identifier, source offsets/range where available, evidence, confidence, and provenance. Regions locate meaning; they do not copy their detailed contents into light context.

Relationships must preserve role boundaries. Recommended, historical, comparison, and findings-only concepts cannot override current study/event identity.

## 6. Provenance and confidence

Context provenance must identify, as applicable:

- MedNexus context/knowledge-layer version
- detector/reasoner identity and version
- exact evidence spans or structural references
- authoritative reference families and activated source versions
- normalization and relationship evidence
- warnings, conflicts, and review reasons

External standards and terminology are reference inputs. MedNexus owns curation, normalization, evidence composition, conflict resolution, context construction, confidence, and final decision logic.

## 7. Routing readiness

Processing context may recommend compatible downstream capabilities or profiles, but it must not execute EXTRACT or STANDARDIZE. It includes:

- selected/recommended PROTECT profile when available
- extraction profile/family identifier
- terminology profile recommendation
- supported next capabilities
- `document_review_required`

Routing identifiers are symbolic. They are not evidence that the downstream capability is implemented.

## 8. Two-layer review model

- `document_review_required` belongs to UNDERSTAND/process context.
- `extraction_review_required` belongs to EXTRACT output.

The two signals retain separate provenance. A presentation layer may combine them for display but must not discard their independent meanings.

## 9. Privacy-context boundary

UNDERSTAND may identify privacy-relevant regions and semantic roles needed by PROTECT. It does not choose privacy transformations. Semantic date-role privacy and the full Protected Execution Envelope remain planned contracts until implemented and validated.

## 10. Explicitly deferred to EXTRACT

The following never become authoritative light context:

- Lesion, finding, diagnosis, symptom, disease, or procedure facts
- Exact measurements, values, units, dates, doses, lots, manufacturers, routes, or sites
- Exact recommendation or impression content
- Exact vaccine, test, organism, analyte, or terminology code
- Save-ready domain records

Presence flags such as “measurement-bearing” or “BI-RADS present” may be approved context; the values themselves remain EXTRACT output.

## 11. Compatibility and migration

The contract is an architecture target, not a claim of completed code migration.

- Existing `MedNexusDocumentContext` remains the migration base.
- Typed domain context becomes canonical additively.
- Existing flat Radiology aliases may remain temporarily but must not become a second semantic authority.
- Compatibility `DOPPLER` may remain temporarily while it aliases to the Ultrasound specialization.
- Generic `attributes` remains a controlled escape hatch, not the primary contract.
- Compatibility-era `PATHOLOGY`, `ADMISSION_DISCHARGE`, and missing `ICU` require controlled migration to the frozen catalog.
