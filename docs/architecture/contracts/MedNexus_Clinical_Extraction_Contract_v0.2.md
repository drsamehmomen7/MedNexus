# MEDNEXUS CLINICAL EXTRACTION CONTRACT

## Version 0.2

**Status:** FROZEN ARCHITECTURE AUTHORITY

**Date:** 23 August 2026

**Scope:** UNDERSTAND/PROTECT → domain EXTRACT → review → STANDARDIZE

This successor preserves [Clinical Extraction Contract v0.1](MedNexus_Clinical_Extraction_Contract_v0.1.md) as architecture history. Version 0.2 adopts bounded UNDERSTAND context and makes EXTRACT the sole owner of detailed clinical facts.

## 1. Governing pipeline

```text
UNDERSTAND
  → MedNexusDocumentContext
PROTECT
  → governed document/access decision
EXTRACT
  → terminology-independent clinical facts
STANDARDIZE
  → terminology mappings and coded representations
```

Architecture authority does not imply that the future Protected Execution Envelope or every domain extractor is implemented.

## 2. Input to EXTRACT

EXTRACT receives an understood and policy-governed document package containing, as available:

- Original document identity and provenance
- `MedNexusDocumentContext` conforming to Semantic Context Contract v0.2
- The selected privacy policy/profile
- MedNexus-owned protected text/output
- A future `ProtectionContext` or equivalent access decision when implemented
- Raw text only when explicitly permitted by the governing execution policy

The extractor must not bypass PROTECT or infer its own privacy policy.

### 2.1 Protected Execution Envelope direction

PROTECT is a governance/policy boundary, not unconditional destructive redaction before EXTRACT. A future envelope may govern:

- `protected_text`
- raw-text access: `ALLOWED`, `DENIED`, or `RESTRICTED`
- per-field access restrictions
- policy identity and transformations
- execution and output provenance

This remains planned until code and validation prove it. No document may present it as implemented merely because the contract defines the direction.

## 3. Identity inheritance

EXTRACT consumes the document domain/subdomain/family selected by UNDERSTAND. It does not run a competing authoritative document classifier.

- `LABORATORY` remains `LABORATORY` when consumed by Public Health.
- Native immunization/vaccination documents use `PUBLIC_HEALTH / IMMUNIZATION` in the current product scope.
- `PUBLIC_HEALTH / LABORATORY_DERIVED_SURVEILLANCE` is valid only when UNDERSTAND established native Public Health surveillance identity plus laboratory-derived surveillance context.
- `OTHER` selects a generic/manual-review route; it does not authorize guessed domain extraction.
- `UNKNOWN` requires review before domain-specific routing.

## 4. EXTRACT ownership

EXTRACT owns:

- Detailed clinical facts and entities
- Diagnoses, findings, symptoms, procedures, medications, tests, organisms, exposures, and relationships
- Exact values, measurements, units, dates, doses, lots, manufacturers, routes, and sites
- Exact recommendation, impression, assessment, and conclusion content
- Domain-specific structured output
- Per-field source spans and provenance
- Per-field confidence
- `extraction_review_required`
- Human-review preparation before persistence or downstream use

UNDERSTAND context may route the extractor but never substitutes for extracted facts.

## 5. Terminology independence

EXTRACT emits recognized facts using source text and terminology-independent canonical field semantics. It must not require successful terminology mapping to recognize or retain a fact.

```text
Extraction recognition/confidence
  must remain unchanged
  when terminology mapping is absent, unavailable, or unsuccessful.
```

Terminology identifiers may appear as source evidence or mapping candidates, but STANDARDIZE owns the authoritative mapping decision.

## 6. Conceptual extraction result

```text
ClinicalExtractionResult
  document/domain identity inherited from UNDERSTAND
  domain_profile
  extracted_facts[]
    field_id
    source_value
    normalized_value_without_external_code (optional)
    source_span/provenance
    confidence
    evidence/method
    review_state
  extraction_review_required
  extractor identity/version
  warnings
```

Domain-specific schemas should be typed. A generic dictionary may be used as an interchange envelope, not as a substitute for governed domain field definitions.

## 7. Domain examples and firewall

| UNDERSTAND context | EXTRACT owns later |
|---|---|
| CT body region, contrast context, CT/CTA family, acquisition summary | Lesion location/size, vessel findings, diagnoses, measurements, exact phases, recommendation content |
| MRI body region, contrast context, MRI/MRA/MRV family, sequence summary | Signal characteristics, lesions, diagnoses, measurements, exact sequences |
| X-ray body region, views/laterality, source radiography type | Fracture, opacity, degeneration, diagnosis, measurements, recommendation content |
| Mammography screening/diagnostic context and BI-RADS presence | BI-RADS category, density, masses, calcifications, exact assessment/recommendation |
| Public Health condition/case-status context | Exact condition, classification, onset/report dates, exposures, laboratory facts |
| Immunization vaccine-family and administration-event context | Exact vaccine/CVX, date, dose, lot, manufacturer/MVX, route/site, provider |
| Surveillance topic/period/geography/population context | Counts, rates, cases, stratified metrics, exact dates and clinical variables |
| Laboratory-derived surveillance routing context | Exact test, specimen, organism, value, unit, polarity, code |

## 8. Review model

- `document_review_required` is inherited from UNDERSTAND and retains its own provenance.
- `extraction_review_required` is computed by EXTRACT for fields/records and retains extraction provenance.
- Human review cannot silently convert unknown or unsupported facts into accepted data.
- A UI may display a combined review notice but must preserve both underlying signals.

## 9. Handoff to STANDARDIZE

STANDARDIZE consumes terminology-independent extracted facts and owns:

- Code-system selection
- Mapping to ICD, LOINC, SNOMED CT, RadLex, CVX, UCUM, or other approved systems
- Mapping status and confidence
- Terminology version, license/provenance, and activation state
- Unit and coded-representation normalization
- Human review of ambiguous mappings

Mapping failure must not erase an extracted fact or lower its extraction confidence. External identifiers never replace MedNexus canonical field identities.

## 10. Ownership model

### MedNexus Main / Codex

- UNDERSTAND and PROTECT
- Shared platform/core contracts
- Core semantic and extraction foundations

### Claude / Claude Code Domain Intelligence

- Domain-specific EXTRACT implementations
- Domain STANDARDIZE implementation
- ANALYZE, VISUALIZE, and INDICATORS

Public Health remains the current downstream reference vertical. Radiology extraction is expected to become a future Domain Intelligence vertical after the Radiology UNDERSTAND contract stabilizes.

## 11. Compatibility and implementation state

- Existing Public Health extraction schemas and review fields may require adapters rather than immediate breaking renames.
- Temporary domain detection in a Domain Intelligence workspace is bootstrap logic and must retire when canonical UNDERSTAND context is integrated.
- The future Protected Execution Envelope must not be simulated.
- Domain extraction is incomplete in MedNexus Main; this contract defines the governed destination.
- No production behavior changes are authorized by this document alone.
