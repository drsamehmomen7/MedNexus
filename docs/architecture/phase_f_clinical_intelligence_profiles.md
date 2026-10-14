# Phase F — Clinical Intelligence Profiles and descriptive Insights V1

Status: **ACCEPTED** by human product review on 14 October 2026. The Phase F checkpoint is closed; no additional Insight definitions or visual redesign are part of closure.

## Authority and contracts

EXTRACT retains clinical meaning; STANDARDIZE enriches representation; the durable, human-accepted `ReviewedClinicalRecord` supplies facts, exact protected evidence, and Clinical Extraction Profile provenance. Product Collection snapshots pin exact reviewed-record versions. The existing `analyze_collection` AnalysisRun remains the numerical authority for collection frequencies, measurements, and eligibility. The Phase F backend Insight engine adds narrowly governed, question-specific report-level calculations bound to that exact AnalysisRun. The browser renders only backend counts, state, wording, and bar percentages. It does not mine relationships or calculate Insight numerators, denominators, or support decisions.

`ClinicalIntelligenceProfile`, `ClinicalInsightDefinition`, `ClinicalInsightVariable`, `ClinicalInsightSupport`, and `ClinicalInsightReference` are immutable MRJ-owned contracts. The registry resolves only an exact compatible Clinical Extraction Profile ID and version, then an explicit active Intelligence Profile version. Unsupported exams yield no profile. Definition order is registry order, never effect-size order. No new Clinical Extraction Profile or clinical fact is created.

## Questions and assertions

US Abdomen V0.1 (`MRJ_INTEL_US_ABDOMEN`) defines hepatomegaly/ascites, steatosis/gallstones, same-side renal calculus/hydronephrosis, and pancreas visualization. MRI Shoulder V0.1 (`MRJ_INTEL_MRI_SHOULDER`) defines labral tear/Hill-Sachs, explicit Bankart or glenoid injury/Hill-Sachs, rotator-cuff tear/retraction, and cuff tear/cuff-muscle degeneration. Generic labral tears do not become Bankart lesions. The renal question requires explicit same-side laterality. The cuff-muscle question requires relevant muscle anatomy. These are fixed clinical questions over curated reviewed facts, not free-form text search or arbitrary correlation mining.

Each finding variable admits `PRESENT`, `EXPLICITLY_ABSENT_OR_NORMAL` from `ABSENT_NEGATED`, `INDETERMINATE`, and `NOT_DOCUMENTED`. Mixed or uncertain assertions are indeterminate. Comparison groups include explicit present versus explicit absent only. An unmentioned concept is never silently counted as absent. Finding-context denominators require both a present exposure and an explicit outcome assessment. Superseded/prior facts, hypotheses, assessments, recommendations, and facts without the governed concept/anatomy requirement cannot supply an event. The primary analysis level is **REPORT**, with no patient deduplication or patient-level claims.

The pancreas quality question reads the pinned Clinical Extraction Profile element `pancreas.visualization`. Its applicable denominator includes documented, limited/not visualized, and not-documented coverage; `NOT_APPLICABLE` is excluded. The current accepted coverage snapshot has no fact or protected-evidence pointer. Quality contributors therefore resolve to the exact reviewed-record version and coverage state, while the UI explicitly discloses the absent fact-level anchor. A nearby pancreas finding is never presented as proof of visualization quality.

## Eligibility, denominators, support, and states

Every question first restricts records to the exact compatible reviewed profile/version and allowed scope, then evaluates its own required assertions or coverage. It records excluded counts separately for unsupported scope, missing documentation, indeterminate assertions, missing coverage, and out-of-scope coverage. No question uses the whole Collection N as a substitute for its own eligible N.

The versioned `MRJ_INSIGHT_SUPPORT_V0_1` policy is classified as `MRJ_POLICY`, labeled **MRJ V1 descriptive support policy**. It is an internal descriptive presentation gate, not a statistical significance, reliability, power, or generalizability threshold:

| Question type | Minimum eligible reports | Minimum per comparison group | Minimum documented events |
|---|---:|---:|---:|
| Two-group co-documentation | 6 | 2 | 2 total |
| Finding context | 3 | 1 | 2 |
| Coverage quality | 5 | 1 | 0 |

Below these thresholds, the result is `INSUFFICIENT_DATA` with the exact wording: “Not enough eligible reviewed reports under the current MRJ support policy.” It never says there is no relationship. `NO_CLEAR_DESCRIPTIVE_PATTERN` is used only for exactly equal observed two-group fractions after support passes; it makes no inferential claim. `OBSERVATION_AVAILABLE`, `NOT_APPLICABLE`, and `UNAVAILABLE` cover the other governed states. Wording is confined to documentation in eligible reviewed **reports in this Collection**, with explicit n/N. There are no p-values, confidence intervals, odds ratios, risk estimates, population prevalence claims, causal claims, or predictive language.

## Reproducibility and lineage

The backend persists an immutable Insight run with a SHA-256 integrity check and foreign keys to the exact AnalysisRun and Collection version. Its deterministic ID includes the AnalysisRun ID and a digest of the full versioned Intelligence Profile configuration, including definitions, references, and support policy. Changing Collection membership creates a new Collection/AnalysisRun/Insight run; activating a different Intelligence Profile version creates a different Insight run. Historical runs are read from their stored payload and do not silently adopt a new profile version.

The contributor endpoint resolves each group against the pinned reviewed-record ID/version and fact IDs. For fact-based questions it revalidates exact protected evidence anchors through `ReviewedClinicalRecord.evidence_context`; altered or missing records fail safely. Coverage-quality lineage currently ends at the accepted profile snapshot because that contract has no fact/evidence reference. This is accepted V1 technical debt, not a reason to fabricate an evidence pointer. Comparison groups can be inspected separately. The Insights page presents profile groups, deterministic cards, backend n/N bars, an insufficient-data card, contributing reports, and a “Why this insight?” side panel with question, eligibility, group denominators, separate exam/profile and clinical relationship bases, limitations, and collapsed technical provenance. Technical IDs are not shown by default.

## References and deferred scope

`EXAM_PROFILE_REFERENCE` records the exam scope. `CLINICAL_RELATIONSHIP_REFERENCE` separately records a verified primary study relevant to a specific pair, or is absent with `relationship_reference_status=PENDING_VERIFICATION`. `MRJ_POLICY` identifies the internal descriptive support gate. No `ANALYTIC_POLICY_REFERENCE` is used in V1 because no external statistical method is claimed. The [ACR–AIUM–SPR–SRU abdomen/retroperitoneum ultrasound practice parameter](https://gravitas.acr.org/PPTS/GetDocumentView?docId=189&releaseId=2) (displayed 2021 revision) and [ACR–SPR–SSR shoulder MRI practice parameter](https://gravitas.acr.org/PPTS/GetDocumentView?docId=45) (title/URL verified; revision date pending) are **exam/profile bases only**. They are not cited as proof of any disease relationship.

| Governed question | Exam/profile basis | Clinical relationship basis | Relationship status |
|---|---|---|---|
| Hepatomegaly + ascites | ACR abdomen ultrasound parameter | None verified for this general report-level comparison | `PENDING_VERIFICATION` |
| Hepatic steatosis + gallstones | ACR abdomen ultrasound parameter | [Chang et al., ultrasound-based cohort study (2018)](https://pubmed.ncbi.nlm.nih.gov/30469392/) | `VERIFIED` |
| Renal calculus + same-side hydronephrosis | ACR abdomen ultrasound parameter | None verified for this exact broad renal-calculus question | `PENDING_VERIFICATION` |
| Pancreas visualization | ACR abdomen ultrasound parameter | Not applicable: this is `COVERAGE_QUALITY`, not a disease relationship | `PENDING_VERIFICATION` in the binary metadata; no clinical relationship source is required |
| Labral tear + Hill-Sachs | ACR shoulder MRI parameter | None verified for the full scope of generic labral tears | `PENDING_VERIFICATION` |
| Bankart/glenoid injury + Hill-Sachs | ACR shoulder MRI parameter | None verified for the full combined Bankart-or-glenoid-injury scope; a Bankart-only study does not cover the entire definition | `PENDING_VERIFICATION` |
| Rotator cuff tear + tendon retraction | ACR shoulder MRI parameter | [Bierry and Palmer, MRI study of full-thickness cuff-tear retraction (2019)](https://pubmed.ncbi.nlm.nih.gov/29982855/) | `VERIFIED` |
| Rotator cuff tear + muscle degeneration | ACR shoulder MRI parameter | [Matsumura et al., MRI study of fatty infiltration and atrophy in chronic cuff tears (2024)](https://pubmed.ncbi.nlm.nih.gov/38707576/) | `VERIFIED` |

These studies motivate predefined questions only; their selected populations and methods do not establish what was observed in an MRJ Collection. The “Why this insight?” panel states: “References justify why MRJ defines this question; they do not validate the result observed in this Collection.” No guideline prose is copied.

ReviewedClinicalRecord V3 does not persist governed sex or age in its accepted analytic envelope, and the reviewed Collection projection deliberately leaves report year unavailable. Earlier Journey/PROTECT analytic context is transient for this product boundary. Therefore gallstones-by-sex and age-band questions are deferred; no demographic value is parsed from free text or fabricated from the visual reference. Trends, inferential analysis, longitudinal patient intelligence, OpenMed, and MedGemma remain outside Phase F V1.

## Validation status

Closure validation: 16 focused backend Clinical Intelligence tests, 6 focused frontend Insights tests, 1303 full backend tests, and 26 complete frontend tests passed. JavaScript syntax, Python compilation, and Git whitespace checks passed. A separate 20-result before/after provenance probe found no changed numerical outputs or denominators. Human product acceptance covers the architecture and visual implementation, not clinical validity or population generalizability.

Focused synthetic fixtures exercise explicit/unknown assertions, question-specific denominators, laterality, profile separation, support abstention, version immutability, HTTP routes, and contributor evidence. A separate read-only copy of the previously available Phase E synthetic reviewed-record Collections yielded three sparse Collections; all four applicable US questions abstained in each Collection. This independent result was retained under `D:\MedNexus\Debug\Phase_F_Validation\independent_result.json`. Isolated visual-review Collections and the nine requested PNG screenshots are under `D:\MedNexus\Debug\Phase_F_Validation\screenshots`. These fixtures establish technical behavior, not clinical validity. Human product acceptance is recorded above and does not imply population generalizability.
