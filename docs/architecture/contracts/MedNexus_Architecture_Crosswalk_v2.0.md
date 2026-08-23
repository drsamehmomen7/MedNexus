# MEDNEXUS ARCHITECTURE CROSSWALK — v2.0

## Status

**FROZEN ARCHITECTURE AUTHORITY**

**Date:** 23 August 2026

This successor preserves [Architecture Crosswalk v1.1](MedNexus_Architecture_Crosswalk_v1.1.md) as architecture history. Where the two differ, v2.0 follows the human-approved [UNDERSTAND Domain Matrix v1.0](../MedNexus_UNDERSTAND_Domain_Matrix_v1.0.md).

## 1. Authoritative MEDNEXUS7 journey

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

INGEST remains an internal technical operation within UNDERSTAND. The journey is target product architecture, not a claim that all seven transformations are implemented.

## 2. Stage ownership crosswalk

| Stage | Owns | Does not own | Primary handoff |
|---|---|---|---|
| **UNDERSTAND** | Reference-driven document identity; domain; supported subdomain/family or `OTHER`; document type; language; approximately 3–4 approved light-context fields; semantic regions/relationships; provenance; confidence; document-review requirement; routing readiness | Detailed clinical facts, exact values, diagnoses, measurements, recommendation text, terminology coding | `MedNexusDocumentContext` conforming to Semantic Context Contract v0.2 |
| **PROTECT** | Purpose-based privacy decisions, access/governance rules, transformations, and MedNexus-owned protected output | Document classification or clinical fact extraction | Current Phase 1 privacy output; future `ProtectionContext`/Protected Execution Envelope when implemented |
| **EXTRACT** | Domain-specific detailed clinical facts, diagnoses/findings, exact values and dates, measurements, recommendations, structured output, per-field provenance/confidence, extraction-review requirement | Re-deciding document domain; terminology mapping; privacy-policy decisions | Terminology-independent extraction result conforming to Extraction Contract v0.2 |
| **STANDARDIZE** | Terminology mapping/coding, mapping status, terminology provenance/version, units and canonical representations | Changing extraction recognition or confidence | Standardized structured clinical data |
| **ANALYZE** | Traceable analysis over governed structured data | Direct uncontrolled free-text inference as authoritative data | Analytical results |
| **VISUALIZE** | User-facing representation of governed outputs | Recomputing upstream clinical or privacy decisions | Views/dashboards |
| **INDICATORS** | Validated operational, clinical, research, and Public Health indicators | Creating facts absent from governed upstream data | Traceable indicators |

## 3. Frozen document-domain model

| Domain | v1.0 status | UNDERSTAND priority | Required subtype behavior |
|---|---|---:|---|
| `RADIOLOGY` | Approved | P0/full | Supported Radiology family or `OTHER` |
| `PUBLIC_HEALTH` | Approved | P0/full | Supported Public Health family or `OTHER` |
| `LABORATORY` | Approved | P1/catalogue only | `OTHER` until a detailed matrix is approved |
| `ADMISSION` | Approved | P1/catalogue only | `OTHER` until a detailed matrix is approved |
| `DISCHARGE` | Approved | P1/catalogue only | `OTHER` until a detailed matrix is approved |
| `ICU` | Approved | P1/catalogue only | `OTHER` until a detailed matrix is approved |
| `EMERGENCY` | Approved | P1/catalogue only | `OTHER` until a detailed matrix is approved |
| `PATHOLOGY` | Future | Not implemented by this authority | `UNKNOWN` until approved |

`UNKNOWN` is a safety outcome when the domain itself is not confidently established. It is not an implemented domain.

## 4. Domain is not workflow

Document domain describes the native semantic identity of the source. Workflow/application describes how it is consumed.

```text
Patient Laboratory Report
  Domain: LABORATORY
  Consuming workflow: Public Health

Result: domain remains LABORATORY
```

For the current MedNexus product scope, a native immunization/vaccination document is `PUBLIC_HEALTH / IMMUNIZATION`. This is a document-taxonomy decision, not permission to relabel other clinical documents because a Public Health application consumes them.

`PUBLIC_HEALTH / LABORATORY_DERIVED_SURVEILLANCE` requires both:

1. Native Public Health surveillance/reporting identity or context.
2. Laboratory-derived surveillance data/context.

Laboratory results alone are insufficient. If surveillance identity is not established, do not guess.

## 5. Frozen Radiology model

| Radiology subdomain | Governed family decisions | UNDERSTAND → downstream |
|---|---|---|
| `CT` | CT and CTA study families | Light context routes the CT extractor; EXTRACT owns findings, measurements, diagnoses, and exact acquisition facts |
| `MRI` | MRI, MRA, and MRV study families | Light context routes the MR extractor; EXTRACT owns signal characteristics and detailed findings |
| `X_RAY` | CR/DX/XR normalize to X-ray while source type may be retained | Views/laterality/body region remain bounded context; findings remain EXTRACT |
| `ULTRASOUND` | Doppler/Vascular Ultrasound is a study-family specialization | Flow/velocity presence may route extraction; exact velocities and vascular findings remain EXTRACT |
| `MAMMOGRAPHY` | Screening/diagnostic and view/tomosynthesis context | BI-RADS presence may be context; category/value remains EXTRACT |
| `NUCLEAR_MEDICINE` | `PLANAR`, `SPECT`, `PET`, `SPECT_CT`, `PET_CT`, `OTHER` | Tracer/uptake presence may route extraction; exact substance, dose, and uptake values remain EXTRACT |
| `FLUOROSCOPY` | Diagnostic fluoroscopic imaging only | Interventional/image-guided procedure documentation resolves to `RADIOLOGY/OTHER` until a future family is approved |
| `OTHER` | Known Radiology; unsupported/unsafe family | Preserve generic structure/provenance and require review as indicated |

## 6. Frozen Public Health model

| Public Health subdomain/family | Identity condition | UNDERSTAND → downstream |
|---|---|---|
| `NOTIFIABLE_DISEASE` | Native case-notification/eCR identity | Route detailed case extraction; exact condition, dates, exposure, and case values remain EXTRACT |
| `IMMUNIZATION` | Native immunization/vaccination document identity | Route vaccination extraction; exact date, dose, lot, manufacturer, route/site, and code remain EXTRACT/STANDARDIZE |
| `SURVEILLANCE` | Native surveillance report/summary identity | Route surveillance extraction; counts, rates, and exact topics remain EXTRACT |
| `SYNDROMIC_SURVEILLANCE` | Native encounter/population syndromic feed/report identity | Route syndromic extraction; complaints, diagnoses, counts, and dates remain EXTRACT |
| `OUTBREAK_CLUSTER` | Native outbreak/cluster investigation identity | Route outbreak extraction; case line lists, exposures, counts, and control actions remain EXTRACT |
| `LABORATORY_DERIVED_SURVEILLANCE` | Native Public Health surveillance identity plus laboratory-derived surveillance context | Route surveillance extraction without relabeling patient Laboratory documents |
| `OTHER` | Known Public Health; unsupported/unsafe family | Preserve generic structure/provenance and require review as indicated |

## 7. Review model

Review remains two-layer:

- `document_review_required`: UNDERSTAND/process-level uncertainty or safety signal.
- `extraction_review_required`: EXTRACT field/record-level validation signal.

A UI may derive a combined notice, but the two authoritative signals retain separate provenance.

## 8. PROTECT governance boundary

PROTECT is a policy/governance gate, not unconditional destructive redaction before EXTRACT. The future MedNexus Protected Execution Envelope may govern protected text, raw-text access, field restrictions, policy identity, transformations, and provenance. It remains planned until implemented and validated.

## 9. Parallel-development ownership

### MedNexus Main / Codex

- UNDERSTAND
- PROTECT
- Shared platform and core contracts
- Core semantic foundations

### Claude / Claude Code Domain Intelligence

- Domain-specific EXTRACT
- Domain STANDARDIZE implementation
- ANALYZE
- VISUALIZE
- INDICATORS

Public Health remains the current downstream reference vertical. Radiology extraction is a future Domain Intelligence vertical after the Radiology UNDERSTAND contract stabilizes.

A Cross-Track Sync Brief remains mandatory when shared architecture/contracts change, either track reaches a stable checkpoint, a cross-track dependency appears, or before an Integrated Domain Checkpoint.

## 10. Architecture authority versus implementation

This crosswalk defines the target contract. It does not claim current implementation completion. Pending migrations include:

- Align the code domain catalogue.
- Add consistent `OTHER` support.
- Add `ICU` and split `ADMISSION` from `DISCHARGE`.
- Demote compatibility-era `PATHOLOGY` to future status.
- Bound Radiology context to approved fields.
- Add typed Public Health context.
- Preserve legacy aliases during additive migration.
- Retain compatibility `DOPPLER` behavior until safely aliased to Ultrasound specialization.

No production behavior changes are authorized by this document alone.
