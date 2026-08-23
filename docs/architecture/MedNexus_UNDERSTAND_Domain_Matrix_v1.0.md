# MEDNEXUS UNDERSTAND DOMAIN MATRIX

## Version 1.0

**Status:** FROZEN ARCHITECTURE AUTHORITY

**Date:** 23 August 2026

**Human approval date:** 23 August 2026

**Scope:** UNDERSTAND only

**Successor architecture:** Blueprint v2.0 and successor contracts adopt this matrix as their domain/subdomain/context authority

## 1. Purpose and governing boundary

UNDERSTAND is the first MedNexus processing stage after upload or pasted-text intake. INGEST is its internal file/text intake, extraction/parsing, and `DocumentContent` construction operation.

```text
Document
  → Domain
  → Subdomain / Modality / Document Family, or OTHER
  → 3–4 high-value contextual metadata items
  → Semantic document regions and document-level relationships
  → Provenance, confidence, and review requirement
  → Ready for PROTECT and EXTRACT
```

UNDERSTAND identifies what a document is and enough reliable context to route and configure downstream processing. It does not create save-ready clinical facts.

### 1.1 Decision labels

- **AR — Authoritative reference:** directly supported by a named standards or professional authority.
- **MC — MedNexus curated decision:** a bounded MedNexus product/architecture choice informed by authoritative references.
- **FNF — Future / not yet frozen:** requires later domain validation or human architecture approval.

### 1.2 Domain and workflow are different axes

`Document Domain` describes the native semantic identity of the source document. `Application / Workflow Vertical` describes why or where the document is consumed.

- A patient laboratory report remains `LABORATORY` when consumed by Public Health.
- A public-health surveillance summary built from laboratory feeds may be `PUBLIC_HEALTH / LABORATORY_DERIVED_SURVEILLANCE`.
- A native immunization/vaccination document is `PUBLIC_HEALTH / IMMUNIZATION` in the current MedNexus product scope.
- Immunization taxonomy remains distinct from consuming-workflow semantics: the classification follows the native document identity, not merely the presence of a vaccine term or a later analytical use.

## 2. Approved domain catalog

| Domain | Status | Current implementation priority | Required fallback |
|---|---|---:|---|
| `RADIOLOGY` | Approved | P0 — full | `RADIOLOGY / OTHER` |
| `PUBLIC_HEALTH` | Approved | P0 — full | `PUBLIC_HEALTH / OTHER` |
| `LABORATORY` | Approved | P1 — catalogue only in v1.0 | `LABORATORY / OTHER` |
| `ADMISSION` | Approved | P1 — catalogue only in v1.0 | `ADMISSION / OTHER` |
| `DISCHARGE` | Approved | P1 — catalogue only in v1.0 | `DISCHARGE / OTHER` |
| `ICU` | Approved | P1 — catalogue only in v1.0 | `ICU / OTHER` |
| `EMERGENCY` | Approved | P1 — catalogue only in v1.0 | `EMERGENCY / OTHER` |
| `PATHOLOGY` | Planned future domain | Future | Not applicable until approved |
| `UNKNOWN` | Safety outcome, not a domain implementation | Always available | Review required |

Every implemented domain must return a supported subdomain/document family or `OTHER`. Unsupported subdomains are never guessed.

## 3. Generic semantic-region model

These are document-region and relationship roles, not extracted clinical facts.

| Canonical region/relationship | Meaning in UNDERSTAND | Typical downstream value |
|---|---|---|
| `STUDY_OR_EVENT_IDENTITY` | The performed study, public-health event, encounter, or document-family identity | Selects the appropriate PROTECT/EXTRACT configuration |
| `CLINICAL_OR_REPORTING_INDICATION` | Why the study/event/report exists, when explicitly represented | Helps route the correct extractor; does not extract the reason text |
| `TECHNIQUE_OR_ACQUISITION` | Document region describing acquisition, specimen/workflow method, or reporting process | Configures domain processing without extracting parameters |
| `OBSERVATION_NARRATIVE` | Findings, results narrative, surveillance observations, or event description | Declares finding/result-bearing content; does not extract facts |
| `CONCLUSION_OR_STATUS` | Impression, conclusion, assessment, case status, or summary | Locates the authoritative conclusion/status region |
| `COMPARISON_OR_PRIOR_CONTEXT` | Prior study, prior period, baseline, or historical comparison | Prevents prior context from becoming current context |
| `RECOMMENDATION_OR_FUTURE_ACTION` | Recommended future study/action, follow-up, control action, or plan | Prevents future actions from redefining the current document |
| `PROFESSIONAL_OR_AUTHORITY_AUTHENTICATION` | Author, interpreter, reporting authority, jurisdiction, signature, or attestation | Supports provenance and authentication context |

All roles are optional. Unknown or absent roles remain absent; the system does not fabricate a complete grammar.

## 4. Radiology matrix

### 4.1 Radiology modeling decisions

- **MC:** The frozen Radiology subdomain set should be `CT`, `MRI`, `X_RAY`, `ULTRASOUND`, `MAMMOGRAPHY`, `NUCLEAR_MEDICINE`, `FLUOROSCOPY`, and `OTHER`.
- **MC:** CTA is a CT study family; MRA/MRV are MRI study families. They are not separate top-level subdomains.
- **MC:** Doppler/Vascular Ultrasound is an Ultrasound study-family specialization because Doppler may coexist with other sonographic acquisition.
- **MC:** Nuclear Medicine study families are `PLANAR`, `SPECT`, `PET`, `SPECT_CT`, `PET_CT`, and `OTHER`. PET and SPECT are not top-level subdomains. A hybrid study records its governed family without becoming multiple documents.
- **AR/MC:** CR and DX are acquisition modalities that normalize to the X-ray/Radiography subdomain; source modality is retained as bounded study-type context.
- **MC:** Body region means performed-study anatomy. Findings-only, comparison, historical, and recommended-study anatomy cannot override it.

Abbreviations used below: `ID` = `STUDY_OR_EVENT_IDENTITY`; `IND` = `CLINICAL_OR_REPORTING_INDICATION`; `TECH` = `TECHNIQUE_OR_ACQUISITION`; `OBS` = `OBSERVATION_NARRATIVE`; `CONC` = `CONCLUSION_OR_STATUS`; `COMP` = `COMPARISON_OR_PRIOR_CONTEXT`; `REC` = `RECOMMENDATION_OR_FUTURE_ACTION`; `AUTH` = `PROFESSIONAL_OR_AUTHORITY_AUTHENTICATION`.

| Domain | Subdomain / modality / family | Recognition basis | High-value UNDERSTAND metadata (maximum four) | Semantic regions expected | Deferred to EXTRACT | Primary reference authority | Fallback / OTHER behavior | Priority | Notes / ambiguity |
|---|---|---|---|---|---|---|---|---:|---|
| RADIOLOGY | **CT family** (`CT`; study family `CT` or `CTA`) | Multi-signal composition: current DICOM/LOINC modality + performed anatomy + report structure; angiographic evidence must be tied to current study | 1. body region; 2. contrast context; 3. study family `CT/CTA`; 4. bounded acquisition/phase summary when reliable | ID, IND, TECH, OBS, CONC; optional COMP, REC, AUTH | Lesions, diagnoses, exact phase/timing, vessel findings, measurements, recommendation text | **AR:** DICOM CT IOD/modality; LOINC/RSNA Modality, Anatomy, Pharmaceutical and Timing attributes; HL7 DiagnosticReport structure. **MC:** CTA is study-family metadata | Known Radiology with unsupported CT variant → `CT` with unknown family or `RADIOLOGY/OTHER`; never infer CTA from a vessel mention | P0 | Acquisition/phase is a bounded summary, not a list of exact phases |
| RADIOLOGY | **MRI family** (`MRI`; study family `MRI`, `MRA`, or `MRV`) | Current MR modality + performed anatomy + governed angiographic/venographic or sequence context + report structure | 1. body region; 2. contrast context; 3. study family `MRI/MRA/MRV`; 4. sequence-family summary | ID, IND, TECH, OBS, CONC; optional COMP, REC, AUTH | Lesion signal, diagnosis, exact sequence parameters, measurements, recommendation text | **AR:** DICOM MR IOD/modality; LOINC/RSNA Modality subtype, Anatomy, Pharmaceutical; RSNA/RadLex. **MC:** MRA/MRV are study families | Unsupported MR specialization → `MRI` with unknown study family; unresolved modality → `RADIOLOGY/OTHER` | P0 | Sequence summary is a small governed family set, not protocol extraction |
| RADIOLOGY | **X-ray / Radiography** (`X_RAY`; source type `CR`, `DX`, `XR`) | Current DICOM CR/DX or LOINC/RadLex XR evidence in study/title/procedure context + performed anatomy; short codes are context-governed | 1. body region/current-study anatomy; 2. study-level laterality; 3. named views **or** view-count context; 4. source radiography type when reliable | ID, IND, TECH, OBS, CONC; optional COMP, REC, AUTH | Fracture/degeneration findings, exact measurements, diagnosis, recommendation text | **AR:** DICOM CR/DX and View Position; LOINC/RSNA Modality Type, Region Imaged, Laterality, View Type and View Aggregation; RadLex projection radiography. **MC:** normalize CR/DX/XR to X-ray | Unsupported radiographic study → `X_RAY` with nullable metadata; known Radiology without safe modality → `RADIOLOGY/OTHER` | P0 | Named projections and numeric view count are different fields; directional “lateral” is not automatically a view |
| RADIOLOGY | **Ultrasound** (`ULTRASOUND`; nonvascular/general sonography) | Current US modality + performed organ/body region + report composition; do not infer from incidental “ultrasound” | 1. body region/organ-system context; 2. complete-vs-limited context; 3. bounded sonographic technique context; 4. measurement-bearing presence | ID, IND, TECH, OBS, CONC; optional COMP, REC, AUTH | Exact organ findings, measurements, lesion dimensions, diagnoses, recommendation text | **AR:** DICOM US IOD/modality; LOINC/RSNA US modality/anatomy/maneuver; HL7 DiagnosticReport. **MC:** measurement-bearing is boolean presence only | Unsupported US specialization → `ULTRASOUND` with nullable context; unsafe modality → `RADIOLOGY/OTHER` | P0 | Complete/limited remains FNF until reference-backed vocabulary and validation are frozen |
| RADIOLOGY | **Doppler / Vascular Ultrasound** (study family under `ULTRASOUND`) | Current US + Doppler/duplex evidence tied to current acquisition and vascular territory; mixed US+Doppler remains one study | 1. vascular territory/body region; 2. arterial-vs-venous context; 3. Doppler study context; 4. flow/velocity-measurement presence | ID, IND, TECH, OBS, CONC; optional COMP, REC, AUTH | Velocities, waveforms, stenosis, thrombosis, reflux, measurements, diagnosis | **AR:** LOINC/RSNA `US.doppler` modality subtype; DICOM US; RSNA/RadLex. **MC:** Doppler is an Ultrasound specialization | Inadequate vascular/Doppler evidence → general `ULTRASOUND`; unresolved current modality → `RADIOLOGY/OTHER` | P0 | Arterial/venous is nullable and must be current-study governed |
| RADIOLOGY | **Mammography** (`MAMMOGRAPHY`) | Current MG/mammography modality + breast study identity + report composition | 1. screening-vs-diagnostic context; 2. study-level laterality; 3. view/tomosynthesis context; 4. BI-RADS assessment **presence** | ID, IND, TECH, OBS, CONC, AUTH; optional COMP, REC | BI-RADS category/value, masses/calcifications, density value, diagnosis, exact recommendation | **AR:** DICOM MG IOD; LOINC/RSNA MG modality/view/laterality; ACR BI-RADS report organization and assessment framework. **MC:** only BI-RADS presence belongs to UNDERSTAND | Unsupported breast-imaging specialization → `MAMMOGRAPHY` with nullable context; unsafe modality → `RADIOLOGY/OTHER` | P0 | BI-RADS exact category is EXTRACT, not context metadata |
| RADIOLOGY | **Nuclear Medicine** (`NUCLEAR_MEDICINE`; study family `PLANAR`, `SPECT`, `PET`, or `OTHER`) | Current NM/PT evidence + organ/body region + study structure; SPECT is an NM subtype in the LOINC/RSNA model | 1. study family; 2. organ/body region; 3. radiopharmaceutical-context presence; 4. quantitative-uptake presence | ID, IND, TECH, OBS, CONC; optional COMP, REC, AUTH | Exact radiopharmaceutical/dose, SUV/uptake values, findings, diagnosis, measurements | **AR:** DICOM NM/PT IODs and radiopharmaceutical modules; LOINC/RSNA `NM.SPECT`, `PT`, anatomy and pharmaceutical attributes. **MC:** bounded presence fields only | Unsupported NM specialization → `NUCLEAR_MEDICINE/OTHER`; unsafe modality → `RADIOLOGY/OTHER` | P0 | “Radiopharmaceutical present” is context; substance/dose is EXTRACT |
| RADIOLOGY | **PET/SPECT hybrid imaging** (`SPECT_CT` or `PET_CT` family under `NUCLEAR_MEDICINE`) | Governed current composition such as NM.SPECT+CT or PT+CT; recommended/reference modalities are excluded | 1. study family; 2. governed hybrid composition; 3. organ/body region; 4. quantitative-uptake presence | ID, IND, TECH, OBS, CONC; optional COMP, REC, AUTH | Exact tracer/dose, uptake values, lesion characterization, diagnosis | **AR:** LOINC/RSNA modality composition (`+`) and SPECT subtype conventions; DICOM NM/PT and hybrid imaging structures. **MC:** one current hybrid study, not competing subtypes | Unsupported or unsafe hybrid composition → `NUCLEAR_MEDICINE/OTHER`; unsafe current modality → `RADIOLOGY/OTHER` | P0 | `PLANAR`, `SPECT`, `PET`, `SPECT_CT`, `PET_CT`, and `OTHER` are the frozen family identifiers |
| RADIOLOGY | **Diagnostic Fluoroscopy / Contrast Studies** (`FLUOROSCOPY`) | Current diagnostic RF or governed contrast-study identity + performed body system + diagnostic report structure | 1. study/procedure family; 2. body system; 3. contrast-study context; 4. dynamic/functional context | ID, IND, TECH, OBS/PROCEDURE_NARRATIVE, CONC; optional REC, AUTH | Exact procedural steps, administered contrast quantity, complications, measurements, diagnosis | **AR:** DICOM RF modality/IODs; LOINC/RSNA action, object, route and modality attributes; ACR procedure/reporting parameters. **MC:** diagnostic Fluoroscopy is distinct from image-guided intervention | Image-guided interventional documentation with clear Radiology identity → `RADIOLOGY/OTHER`; never infer Fluoroscopy from “contrast” alone | P0 | No Interventional Radiology subtype exists in v1.0 |
| RADIOLOGY | **OTHER** | Radiology domain is coherent but no supported current modality/family is sufficiently established | 1. domain; 2. subdomain=`OTHER`; 3. generic semantic structure; 4. review/provenance | Any safely detected generic Radiology regions | All modality-specific and clinical facts | **MC:** explicit safe fallback consistent with MedNexus non-guessing policy | Return `RADIOLOGY/OTHER`; if Radiology itself is not confident, return `UNKNOWN` and require review | P0 | `OTHER` is a successful bounded classification, not an error |

## 5. Public Health matrix

### 5.1 Public Health modeling decisions

- **MC:** Public Health subdomains describe native public-health reporting/document families, not every clinical document later consumed by a Public Health application.
- **AR/MC:** Notifiable Disease / Case Notification follows NNDSS/eCR reporting identity and case-notification structure.
- **AR/MC:** Native immunization/vaccination documents use `PUBLIC_HEALTH / IMMUNIZATION` in the current MedNexus product scope.
- **AR/MC:** Syndromic Surveillance remains distinct from general surveillance because NSSP uses encounter-oriented HL7 feeds and a defined priority data model.
- **MC:** Laboratory-derived Surveillance is valid only for a surveillance envelope, aggregate, or public-health report. A native patient result remains `LABORATORY`.
- **MC:** Condition, vaccine, syndrome, and test “family” fields are coarse routing hints. Exact names/codes are EXTRACT/STANDARDIZE outputs.

| Domain | Subdomain / document family | Recognition basis | High-value UNDERSTAND metadata (maximum four) | Semantic regions expected | Deferred to EXTRACT | Primary reference authority | Fallback / OTHER behavior | Priority | Notes / ambiguity |
|---|---|---|---|---|---|---|---|---:|---|
| PUBLIC_HEALTH | **Notifiable Disease / Case Notification** | Native case-notification/eCR identity + reporting authority/jurisdiction + case/status structure; condition mention alone is insufficient | 1. coarse condition family; 2. case-status context; 3. jurisdiction/geography context; 4. event-vs-report-time context | ID, CLINICAL_OR_REPORTING_INDICATION, OBS/CASE_INFORMATION, CONC/CASE_STATUS, AUTH; optional REC | Exact condition/code, patient facts, onset/report dates, exposures, lab results, case-classification value | **AR:** CDC NNDSS MMGs; HL7 eCR; LOINC where used by the guide. **MC:** four routing fields only | Unsupported notification family → `PUBLIC_HEALTH/OTHER`; no native PH identity → another domain or `UNKNOWN` | P0 | Exact NNDSS event code is not UNDERSTAND metadata |
| PUBLIC_HEALTH | **Immunization / Vaccination** | Native immunization/vaccination document identity + administration, history, status, or registry structure; a vaccine word alone is insufficient | 1. coarse vaccine family; 2. administration-event context; 3. age-group context; 4. jurisdiction/provider context | ID, EVENT/ADMINISTRATION_CONTEXT, OBS/IMMUNIZATION_HISTORY, CONC/STATUS, AUTH | Exact date, vaccine/CVX, dose, lot, manufacturer/MVX, route/site, administering provider | **AR:** CDC IIS Functional Standards/Core Data Elements and CVX code sets; HL7 immunization messaging/FHIR where adopted. **MC:** current product taxonomy is `PUBLIC_HEALTH/IMMUNIZATION`; exact values remain EXTRACT/STANDARDIZE | Unsupported native immunization document → `PUBLIC_HEALTH/OTHER`; absence of native immunization identity → another domain or `UNKNOWN` | P0 | Canonical current-scope decision; consuming workflow alone still never determines domain |
| PUBLIC_HEALTH | **Surveillance** | Native surveillance report/summary identity + topic/period/geographic/population structure | 1. surveillance topic/family; 2. reporting period context; 3. geographic scope; 4. population-group context | ID, REPORTING_SCOPE, OBS/SURVEILLANCE_SUMMARY, CONC/TREND_SUMMARY, AUTH; optional REC | Counts, rates, case records, exact disease names/codes, stratified metrics, statistical findings | **AR:** WHO surveillance standards; CDC surveillance standards/program artifacts; HL7 MedMorph where relevant. **MC:** bounded routing context | Unsupported surveillance family → `PUBLIC_HEALTH/OTHER` | P0 | “Topic/family” is a classifier hint, not a coded surveillance fact |
| PUBLIC_HEALTH | **Syndromic Surveillance** | Native NSSP/PHIN syndromic feed/report identity + encounter/population/time-window structure | 1. syndrome-group hint; 2. time-window context; 3. geographic scope; 4. encounter/population setting | ID, ENCOUNTER_SCOPE, OBS/SYNDROMIC_SIGNAL, CONC/SIGNAL_STATUS, AUTH | Chief complaint, diagnoses, encounter facts, exact dates, patient demographics, counts and rates | **AR:** CDC NSSP and PHIN Messaging Guide for Syndromic Surveillance. **MC:** syndrome group remains coarse | Unsupported syndromic family → `PUBLIC_HEALTH/OTHER`; individual ED report remains `EMERGENCY` | P0 | A source ED document is not Public Health merely because NSSP consumes it |
| PUBLIC_HEALTH | **Outbreak / Cluster Investigation** | Native outbreak/cluster investigation identity + case-definition/person-place-time structure + public-health authority | 1. event/cluster family; 2. geography/facility context; 3. time-window context; 4. population/setting context | ID, CASE_DEFINITION_SCOPE, OBS/INVESTIGATION_NARRATIVE, CONC/STATUS, REC/ACTION, AUTH | Exact case line list, exposures, counts, diagnoses, laboratory findings, hypotheses, control actions | **AR:** CDC and WHO outbreak investigation guidance based on person/place/time and case definitions. **MC:** document-level contexts only | Unsupported investigation type → `PUBLIC_HEALTH/OTHER` | P0 | Exact case-definition criteria are EXTRACT, not UNDERSTAND |
| PUBLIC_HEALTH | **Laboratory-derived Surveillance** | The document itself must establish native Public Health surveillance/reporting identity **and** laboratory-derived surveillance context; laboratory-result presence alone is insufficient | 1. surveillance test-family hint; 2. specimen-context presence; 3. result-polarity context; 4. pathogen/disease-surveillance family | ID, TECH/SPECIMEN_WORKFLOW, OBS/SURVEILLANCE_RESULTS, CONC/STATUS, AUTH | Exact analyte/test, specimen, organism, values, units, reference range, result, code | **AR:** NNDSS/MMGs, LOINC laboratory/document semantics, HL7 DiagnosticReport/eCR as applicable. **MC:** this row is a native surveillance/reporting artifact, not a relabeling rule | Native patient laboratory report → `LABORATORY`; insufficient surveillance identity → do not guess (`LABORATORY`, another supported domain, or `UNKNOWN` as evidence warrants) | P0 | **Hard boundary:** consumption by Public Health never changes a Laboratory report’s native domain |
| PUBLIC_HEALTH | **OTHER** | Public Health domain is coherent but no supported native PH document family is safely established | 1. domain; 2. subdomain=`OTHER`; 3. generic semantic structure; 4. review/provenance | Any safely detected generic Public Health regions | All subdomain-specific and record-level facts | **MC:** safe fallback | Return `PUBLIC_HEALTH/OTHER`; if Public Health itself is not confident, return `UNKNOWN` and require review | P0 | Successful bounded domain classification, not an error |

## 6. Conservative catalogue for other approved domains

These rows define only the architecture slot and fallback. Their subdomain taxonomies and metadata are **FNF** and must receive separate reference-driven matrices before full implementation.

| Domain | Current v1.0 document-family decision | Allowed light context now | Deferred to EXTRACT | Fallback | Priority |
|---|---|---|---|---|---:|
| LABORATORY | Supported family taxonomy not frozen | Generic document identity, status/structure presence, provenance/review | Tests, analytes, specimens, numeric/categorical results, units, ranges, organisms | `LABORATORY/OTHER` | P1 |
| ADMISSION | Supported family taxonomy not frozen | Generic admission identity, encounter-section structure, provenance/review | Diagnoses, medications, history, assessment, plan, dates | `ADMISSION/OTHER` | P1 |
| DISCHARGE | Supported family taxonomy not frozen | Generic discharge identity, discharge-section structure, provenance/review | Diagnoses, medications, condition, instructions, follow-up facts, dates | `DISCHARGE/OTHER` | P1 |
| ICU | Supported family taxonomy not frozen | Generic ICU identity, temporal/section structure, provenance/review | Vitals, ventilation, medications, organ support, scores, clinical events | `ICU/OTHER` | P1 |
| EMERGENCY | Supported family taxonomy not frozen | Generic Emergency identity, encounter/section structure, provenance/review | Chief complaint, diagnoses, vitals, interventions, disposition facts | `EMERGENCY/OTHER` | P1 |
| PATHOLOGY | Future planned domain; no current matrix authority | None beyond `UNKNOWN`/review until approved | All Pathology clinical facts | `UNKNOWN` until domain approval | Future |

## 7. Universal OTHER and UNKNOWN policy

```text
Known domain + unsupported or unsafe subtype
  → Domain = known
  → Subdomain = OTHER
  → Preserve safe generic structure/provenance
  → Do not guess

Domain itself not confidently recognized
  → Domain = UNKNOWN
  → Subdomain absent/unknown
  → Document review required
```

`OTHER` is not interchangeable with `UNKNOWN`. `OTHER` means the domain is established; `UNKNOWN` means it is not.

## 8. UNDERSTAND / EXTRACT firewall

| UNDERSTAND owns | EXTRACT owns later |
|---|---|
| Domain and supported subdomain/family or `OTHER` | Save-ready clinical records and facts |
| Language and document type | Exact disease, diagnosis, vaccine, test, or finding entities |
| Up to 3–4 reliable context fields | Exact measurements, values, units, dates, doses, lots, manufacturers, routes/sites |
| Semantic regions and document-level relationships | Text or structured content of findings, recommendations, impressions, case definitions, exposures |
| Presence flags such as measurement-bearing, BI-RADS-present, or radiopharmaceutical-present | The measurement, BI-RADS category, radiopharmaceutical, or coded value itself |
| Evidence/provenance, confidence, and document-review requirement | Per-field extraction provenance/confidence and extraction-review requirement |
| Routing readiness for PROTECT and EXTRACT | Terminology-independent extracted facts; STANDARDIZE later owns code mapping |

The word “context” never authorizes copying exact clinical values into `MedNexusDocumentContext`.

## 9. Comparison with current MedNexus implementation

### 9.1 Already aligned

- Existing ingestion produces one `DocumentContent` used by UNDERSTAND and the retained journey.
- `MedNexusDocumentContext` already separates identity, structure, clinical context, privacy context, processing context, and provenance.
- Current Radiology reasoning separates current study, indication, technique/acquisition, findings, impression, comparison, recommendation, and professional attribution roles.
- Current Radiology context already carries modality, performed-study anatomy/examination, contrast, selected technique summaries, X-ray named views/view count, finding-bearing presence, and governed provenance.
- Current logic prefers unknown over unsafe classification and preserves external reference provenance beneath MedNexus-owned reasoning.

### 9.2 Fields requiring tightening or demotion

- Unbounded `domain_concepts` and technique lists need explicit per-subdomain allowlists and cardinality limits.
- Broad `clinical_purpose` must remain a nullable routing context and cannot become an inferred diagnosis or extracted indication.
- `finding_bearing` is compliant only as “observation narrative present,” never “abnormal finding present.”
- `authoritative_anatomy` is compliant only when tied to current-study identity; findings-only or recommended anatomy remains excluded.
- Compatibility `attributes` must remain an escape hatch, not a second schema.

### 9.3 Missing target capabilities

- No general domain-subdomain contract with mandatory `OTHER` exists.
- CTA, MRA/MRV, Fluoroscopy, PET/SPECT/hybrid-family semantics are not fully modeled in the public subtype contract.
- Public Health lacks the required MedNexus-owned subdomain matrix, typed light-context model, semantic-role model, and `OTHER` behavior.
- Laboratory, Admission, Discharge, ICU, and Emergency lack approved independent subdomain models.

### 9.4 Taxonomy conflicts and temporary compatibility

- Current code exposes `PATHOLOGY` although Pathology is future in this matrix.
- Current code combines `ADMISSION_DISCHARGE`; the approved catalog separates them.
- Current code lacks `ICU`.
- Current Radiology has `DOPPLER` as a public subtype; this matrix treats it as an Ultrasound study-family specialization. Preserve the old value temporarily through a compatibility alias during migration.
- Current Nuclear Medicine does not fully distinguish PET/SPECT/hybrid study families.
- Existing flat clinical-context aliases should remain temporarily while typed domain context becomes canonical.
- Existing symbolic routing names may remain until the target subdomain contract is implemented additively.

### 9.5 Eventual simplification

- Replace parallel flat and typed context calculation with one canonical typed source plus serialized compatibility aliases.
- Replace generic non-Radiology profile scoring with domain-owned, reference-governed packages as each P1 domain is authorized.
- Keep one shared semantic-role vocabulary with domain extensions rather than per-screen or frontend inference.
- Generate human explanations from role-qualified identity evidence while retaining all evidence in Technical Details.

## 10. Successor-document impact after matrix freeze

### 10.1 Blueprint v2.0

- Replace broad/rich UNDERSTAND language with the bounded Domain Matrix contract.
- Adopt the seven-domain target catalog and Pathology-future status.
- Add domain/subdomain/`OTHER`/`UNKNOWN` semantics.
- Adopt the modality-family decisions in Sections 4 and 5.
- Replace previous work-ownership language with Main/Codex versus Claude/Domain Intelligence boundaries.
- Remove any implication that detailed clinical hints or save-ready facts belong in UNDERSTAND.

### 10.2 Architecture Crosswalk v2.0

- Map every matrix row to UNDERSTAND, PROTECT, EXTRACT, and STANDARDIZE ownership.
- Explicitly separate document domain from consuming application/workflow.
- Replace independent Immunization-domain assumptions with the approved-but-qualified Public Health subdomain decision and unresolved clinical-record caveat.
- Add `OTHER` versus `UNKNOWN` and compatibility-migration mappings.

### 10.3 Clinical Semantic Context Contract v0.2

- Replace the old domain enum target with the seven-domain catalog.
- Define `subdomain/document_family` plus mandatory `OTHER` semantics.
- Limit each typed extension to the matrix-approved 3–4 fields.
- Add the generic semantic-region/relationship vocabulary.
- Preserve compatibility aliases without duplicating semantic authority.
- Remove or demote fields that cross the firewall.

### 10.4 Clinical Extraction Contract v0.2

- Align extraction profiles with matrix subdomains while keeping extracted facts terminology-independent.
- Receive exact values explicitly deferred by every matrix row.
- Keep Laboratory native identity distinct from Public Health workflow consumption.
- Reconcile Immunization extraction ownership after the unresolved taxonomy decision.
- Preserve per-field provenance/confidence and independent extraction-review requirements.

## 11. Reference register

All external sources are reference inputs. MedNexus owns normalization, curated matrix decisions, runtime signatures, semantic roles, conflict resolution, and final context construction.

### Radiology authorities

1. DICOM PS3.3, current Information Object Definitions, including CR, CT, MR, NM, US, DX/MG and related modality-specific structures: <https://dicom.nema.org/medical/dicom/current/output/html/part03.html>
2. DICOM PS3.4, Standard SOP Classes, including CR, DX, and Mammography storage classes: <https://dicom.nema.org/medical/dicom/current/output/chtml/part04/sect_b.5.html>
3. DICOM CR Series Module/View Position semantics: <https://dicom.nema.org/dicom/2013/output/chtml/part03/sect_c.8.html>
4. LOINC/RSNA Radiology Playbook User Guide — modality, modality subtype/composition, anatomic location, laterality, view, pharmaceutical, timing, maneuver and guidance attributes: <https://loinc.org/kb/radiology/loinc-rsna-radiology-playbook-user-guide>
5. LOINC Radiology Reports unified model: <https://loinc.org/kb/users-guide/clinical-observations-and-measures/radiology-reports>
6. LOINC Parts and Part hierarchies, including XR, anatomy, View Type and View Aggregation examples: <https://loinc.org/kb/users-guide/additional-content-in-the-loinc-distribution/loinc-parts-and-part-hierarchies>
7. RSNA RadLex Radiology Lexicon and its relationship to the LOINC/RSNA Radiology Playbook: <https://www.rsna.org/practice-tools/data-tools-and-standards/radlex-radiology-lexicon>
8. RSNA RadReport reporting templates and structured-reporting purpose: <https://www.rsna.org/practice-tools/data-tools-and-standards/radreport-reporting-templates>
9. ACR BI-RADS reporting and assessment framework: <https://www.acr.org/Clinical-Resources/Clinical-Tools-and-Reference/Reporting-and-Data-Systems/BI-RADS>
10. ACR Practice Parameter for Communication of Diagnostic Imaging Findings: <https://gravitas.acr.org/PPTS/DownloadPreviewDocument?DocId=74&ReleaseId=2>
11. HL7 FHIR DiagnosticReport, including study, result, interpreter, conclusion, and presented-form boundaries: <https://hl7.org/fhir/diagnosticreport.html>

### Public Health authorities

12. CDC NNDSS Technical Resource Center and Message Mapping Guides for HL7 case notifications: <https://www.cdc.gov/nndss/technical-resource-center/index.html>
13. CDC NNDSS implementation guides: <https://ndc.services.cdc.gov/implementation-guides/>
14. HL7 FHIR Electronic Case Reporting Implementation Guide: <https://www.hl7.org/fhir/us/ecr/>
15. CDC IIS Functional Standards: <https://www.cdc.gov/iis/functional-standards/resource.html>
16. CDC IIS Core Data Elements — Immunizations: <https://www.cdc.gov/iis/core-data-elements/immunizations.html>
17. CDC Vaccine Data Code Sets (CVX/MVX and related crosswalks): <https://www.cdc.gov/iis/code-sets/index.html>
18. CDC NSSP Syndromic Data Element Prioritization and PHIN Messaging Guide linkage: <https://www.cdc.gov/nssp/php/onboarding-resources/element-prioritization.html>
19. CDC outbreak and case-definition guidance: <https://www.cdc.gov/urdo/php/surveillance/outbreak-case-definitions.html>
20. WHO outbreak investigation guidance: <https://www.who.int/emergencies/outbreak-toolkit/standardized-data-collection-tools/investigating-outbreak-of-unknown-disease>
21. WHO Recommended Surveillance Standards: <https://www.who.int/publications/i/item/who-recommended-surveillance-standards>
22. HL7 MedMorph public-health reporting reference architecture: <https://hl7.org/fhir/us/medmorph/STU1/>

## 12. Frozen human decisions

1. **Immunization taxonomy:** native immunization/vaccination documents use `PUBLIC_HEALTH/IMMUNIZATION` in the current MedNexus product scope. Native Laboratory reports remain `LABORATORY` regardless of Public Health consumption.
2. **Nuclear Medicine/hybrid model:** `NUCLEAR_MEDICINE` is the subdomain; its study families are `PLANAR`, `SPECT`, `PET`, `SPECT_CT`, `PET_CT`, and `OTHER`.
3. **Fluoroscopy boundary:** diagnostic fluoroscopic imaging reports use `RADIOLOGY/FLUOROSCOPY`; image-guided interventional documentation uses `RADIOLOGY/OTHER` when Radiology identity is clear until a future family is formally designed.
4. **Laboratory-derived Surveillance:** requires native Public Health surveillance/reporting identity plus laboratory-derived surveillance context. Laboratory results alone never satisfy the classification.

Separate reference-driven matrices remain required before implementing detailed subdomain models for `LABORATORY`, `ADMISSION`, `DISCHARGE`, `ICU`, or `EMERGENCY`. Until then, affected values remain `OTHER`, nullable, or `UNKNOWN` as appropriate.
