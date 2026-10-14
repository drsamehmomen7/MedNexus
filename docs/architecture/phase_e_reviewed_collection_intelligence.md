# Phase E — Reviewed Collection Intelligence V1

Status: **accepted** for Phase E architecture and visual implementation. No relational Clinical Insights engine is included.

## Authority and membership

Product Collections admit only exact, existing versions of durable `ReviewedClinicalRecord` envelopes. The repository revalidates the accepted review decision, major-review acknowledgement, protected-source digest, and exact evidence anchors on admission and again when a version is read. A Journey document, extraction result, or unreviewed report is not a membership reference. The existing validation-only `ReportCollectionStore` and `/analysis-collections` routes remain available, but do not back the product Collections workspace.

`ReviewedCollectionMember` is the domain membership contract. `SqliteReviewedCollectionRepository` stores collection heads, append-only membership snapshots, and immutable AnalysisRun payloads in `reviewed_collections.sqlite3`, alongside the existing reviewed-record database by default. `MRJ_REVIEWED_COLLECTION_DB` may select a different local database. A snapshot pins each `reviewed_record_id` and `reviewed_record_version` plus safe exam/profile metadata. Membership JSON and AnalysisRun payloads have SHA-256 integrity checks. The repository never substitutes a later record version if a pinned version is missing; it raises an integrity error. Changing membership creates a new Collection version. Historical AnalysisRuns remain bound to their old Collection version and exact member list.

## Analysis and lineage

The reviewed projection maps verified canonical facts and governed standardized measurements into the established `analyze_collection`/AnalysisRun calculation path. It excludes superseded facts and assessment/recommendation prose from finding frequency. The new eligibility branch requires durable review; legacy validation eligibility is unchanged. Report-level finding frequencies preserve `n / eligible N`; no population prevalence is claimed. Measurement groups require compatible clinical concept, anatomy, laterality, measurement type, dimension, unit, and profile context. The frontend renders calculated results and does not calculate clinical metrics. Relationship/co-occurrence outputs are omitted from the Phase E product AnalysisRun.

Finding and measurement contributor endpoints resolve the pinned record version, its fact, and an exact protected-source evidence anchor. They do not consult transient Journey memory or original identified source. A missing or altered record fails instead of silently losing a contributor.

## Coverage and mixed profiles

Accepted record schema V3 includes the evaluated Clinical Extraction Profile coverage snapshot. V1/V2 records remain readable; their missing snapshot is explicitly unavailable. Data Quality groups coverage by profile ID and profile version, then by element. `NOT_APPLICABLE` is excluded from the eligible denominator; `NOT_DOCUMENTED`, `LIMITED_OR_NOT_VISUALIZED`, and `DOCUMENTED` remain distinct. Mixed-profile collections retain separate profile-specific coverage and measurement groups. Review alerts and standardization counts remain descriptive, not clinical assertions.

## Product behavior and visual contract

Review Complete creates a Collection only from the session's durably reviewed records with exact versions; unreviewed or failed reports are explicitly excluded. `/collections` lists durable Collections and opens Overview, Findings, Measurements, Data Quality, an Insights next-phase state, and a Trends abstention state. Report/fact/evidence drilldown uses the protected reviewed envelope. The accepted five-image MRJ high-fidelity reference pack governs the visual direction: compact MRJ navigation, white clinical surfaces on warm off-white, navy/teal hierarchy, dense restrained panels, a roughly 28/72 report queue/record split, compact coverage strip, and Collection tabs. Clinical values in the references are illustrative only; the product renders actual backend values.

Current visual deviations from the references are deliberate: Export and Edit Collection are omitted because governed export/edit workflows are not in Phase E; the clinical-relationship cards and contributing-report/“Why this insight?” drawer in the Insights reference are deferred to Phase F; the Report Workspace retains accepted processing/review controls rather than inventing Save for later or Edit behavior; V1/V2 reviewed records have no persisted profile coverage and display an unavailable state; empty measurement panels remain empty when no governed comparable values exist. Human review accepted these deviations and the final desktop visual implementation.

The local validation run used three independently available synthetic US Abdomen source reports through the live UNDERSTAND → PROTECT → EXTRACT → STANDARDIZE → durable acceptance pipeline, then analyzed their pinned reviewed versions. The synthetic collection contained three eligible reports, ten finding groups, four comparable measurement groups, and profile coverage snapshots. A separate mixed collection used two synthetic ultrasound reports and one synthetic MRI report to exercise heterogeneous exam types; their profile-dependent coverage is not merged. Full-width 1536-pixel screenshots of the Reports queue, US Abdomen record and coverage, Collections list, Overview, Findings, both lineage dialogs, Measurements, Data Quality, and Insights next-phase state were saved outside the repository under `D:\MedNexus\Debug\Phase_E_Visual_Review`. The independent shoulder-source PDF is currently classified by UNDERSTAND as `MRI · Extremity`, so an MRI Shoulder coverage strip cannot be shown for that source without a clinical classification change. This is a data/clinical-engine deviation from the reference, not a visual override in Phase E. Human review accepted the final visual comparison.

A separate automated browser pass of the actual Reports UI uploaded three synthetic reports, completed their review decisions in the isolated test database, used **Analyze these reports**, and opened the resulting Collection with three pinned reviewed records and three eligible analysis reports. This validates the live UI handoff; it does not substitute for clinical human review.

Validation before final closure: 1287 backend tests passed with 8 existing deprecation warnings; 20 frontend tests passed; touched Python files passed AST parsing; modified JavaScript passed `node --check`; `git diff --check` passed.

## Deferred work

Phase F may define exam-specific Clinical Intelligence Profiles, relational insight definitions, reference basis, support thresholds, and the approved insight-card/drawer experience. Trends require governed report dates and adequate eligible samples. No inferred dates, clinical thresholds, inferential statistics, OpenMed, or MedGemma integration are added here.
