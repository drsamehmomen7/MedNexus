# Phase D: Clinical Extraction Profiles V0.1

Status: **ACCEPTED — Clinical Extraction Profiles V1 (Phase D + D.1 + D.2), 13 October 2026**.

## Authority and flow

The profile hierarchy is Radiology Core → modality → exam. The Radiology Core
names shared report concepts (indication, comparison, identity, findings,
measurements, negatives, recommendations, limitations, and provenance). The
initial exam profiles are `MRJ_RAD_US_ABDOMEN` V0.1 and
`MRJ_RAD_MRI_SHOULDER` V0.1. The registry has an explicit active-version map;
registering another version does not activate it. The registry activates only
on current UNDERSTAND Radiology domain, exact modality/family, and governed anatomy. Unsupported or ambiguous
identity returns no profile. It does not consult a filename. Profiles consume
protected sections and existing canonical facts after STANDARDIZE; they never
write or modify a clinical fact, measurement mapping, or stage authority.

Each profile defines stable sections and elements with original MRJ labels,
applicability, measurement-type context, evidence requirement, and laterality.
Measurement type declarations do not supersede MRJ's governed measurement
identity, value, unit, source evidence, or normalization.

## Assertion and coverage

Clinical assertion (`PRESENT`, `EXPLICITLY_ABSENT_OR_NORMAL`,
`INDETERMINATE`) is separate from documentation coverage (`DOCUMENTED`,
`NOT_DOCUMENTED`, `LIMITED_OR_NOT_VISUALIZED`, `NOT_APPLICABLE`). The evaluator
uses protected FINDINGS/DIAGNOSTIC_SUMMARY sentences and exactly grounded
canonical fact anchors. An explicit structure mention can establish
documentation; explicit normal language or a grounded negative is required for
normal/absent assertion. Limited visibility takes precedence over a negative
classification. Silence never establishes a negative. Coverage notes do not
create Needs Review alerts.

US scope is COMPLETE, LIMITED_OR_FOCUSED,
RETROPERITONEAL_OR_URINARY, or UNKNOWN. Complete exams expose the abdominal
structures; exact renal/retroperitoneal context excludes abdominal structures
outside that scope. Unknown or nonspecific focused scope can report silence as
`NOT_DOCUMENTED` but makes no completeness claim or review alert. Right and
left kidneys are independent. Optional bladder coverage is applicable only in
the supported urinary scope. Other conditional organs and special techniques
are metadata candidates for future versions, not forced completeness criteria.

MRI shoulder scope is `UNKNOWN` until current metadata reliably distinguishes
routine MRI from MR arthrography. Its shared shoulder structures are evaluated
in either case; the unknown variant does not imply an arthrogram. No instability
diagnosis is inferred from component findings.

## Identity/content compatibility

The safety validator returns `COMPATIBLE`, `POSSIBLE_ANATOMY_MISMATCH`, or
`INSUFFICIENT_INFORMATION`. It examines only facts with exact protected source
anchors and structured anatomy that also occurs in those anchors. A possible
mismatch requires at least three foreign facts from two distinct clauses and
a three-to-one dominance over the activated profile. Comparison against another
registered profile additionally requires two of its sections; broad gross
body-region families permit review of clearly cranial content under a shoulder
exam even without an active brain profile. A single incidental extra-profile
finding is insufficient. Weak or ungrounded anatomy abstains. The validator
only adds a Major Review signal and never changes a clinical fact.

## UI and durable provenance

The accepted Report Workspace layout remains. A resolved profile gives a
governed title, compact Exam Coverage, and a progressive-disclosure details
drawer. `NOT_DOCUMENTED` and `LIMITED_OR_NOT_VISUALIZED` have distinct labels;
neither is placed in Pertinent Negatives. Only a supported mismatch enters
Major Review. The profile details' technical provenance is collapsed by default.

ReviewedClinicalRecord schema V2 adds `profile_provenance` with exact
`profile_id`, `profile_version`, resolved scope, and evaluation status (or null
when unsupported). Schema V1 remains readable unchanged. Repository rows store
the original snapshot JSON, so reopening an old record never re-evaluates it
under the current registry. A repeat acceptance of a V1 record compares against
the V1 format for idempotence. Profile version changes require a new contract
decision; accepted V0.1 snapshots are not silently upgraded.

## References and rights

The US profile cites the [AIUM Abdomen or Retroperitoneum practice-parameter
listing](https://www.aium.org/resources/practice-parameters/abdomen-or-retroperitoneum).
The listing shows 2026 and also displays a 2021 date; its exact bibliographic
date remains pending verification. The MRI profile cites the official
[ACR–SPR–SSR MRI Shoulder practice-parameter portal](https://gravitas.acr.org/PPTS/GetDocumentView?docId=45);
the current release date remains pending verification. Both cite the
[RSNA RadLex/LOINC Playbook overview](https://www.rsna.org/practice-tools/data-tools-and-standards/radlex-radiology-lexicon)
for exam-identity provenance. These are reference metadata, not copied
guideline prose or tables. No licensed SNOMED content is included; future
terminology imports require a separate licensing review.

## Known limitations

Current UNDERSTAND MRI context does not reliably encode arthrography or MRI
laterality. Exact shoulder anatomy may be unresolved in some reports; such
reports receive no profile rather than a guessed one. A limited abdomen exam
without an explicit renal/retroperitoneal focus does not identify every
out-of-scope organ. Coverage is a conservative report-documentation projection,
not a claim that every profile element was imaged. The mismatch comparison can
abstain on sparse or ungrounded structured facts; it cannot detect every
exam/content contradiction. Individual reports still require clinical review.

The D.1 synthetic audit found that a legacy generic `atrophy` normalization
assigned the display “Cerebral atrophy” before source anatomy was considered.
The protected source instead said “Mild fatty atrophy of the supraspinatus
muscle”; its engine entity was `atrophy` and the relation attached only the
generic `muscle` site. STANDARDIZE preserved the already-wrong EXTRACT label;
it did not introduce the substitution. The same run's engine emitted only
`full-thickness` for the measured tendon tear, so the original source recovery
did not make a tear fact despite corroboration in Impression. D.1 removed the
generic anatomy-expanding label, preserves nominal source phrases and exact
same-clause Anatomy entities, and recovers a measured finding only when its
engine modifier and independent diagnostic summary corroborate the subject.
STANDARDIZE continues to attach terminology separately without rewriting facts.
Sparse or uncorroborated abnormalities can still be missed; clinical review is
required.

## D.2 hold-out correction (clinically accepted)

Five independent report bodies supplied in `5Files.zip` exposed six general
boundaries. The archived PDF hashes matched the existing raw corpus files;
three separately available synthetic reconstructions gave the same core CT,
Doppler, and RUQ failures. Baseline and follow-up diagnostics were run through
UNDERSTAND, PROTECT, EXTRACT, and STANDARDIZE with the cached models offline.
Original report text was never sent directly to RadGraph.

**Addendum authority.** UNDERSTAND currently folds an Addendum into a broad
semantic region. EXTRACT therefore detects an explicit Addendum/correction
heading in the protected source and requires a decisive resolving statement
plus local subject overlap before changing a prior interpretation's status.
The later interpretation becomes current; the earlier canonical fact and its
exact evidence remain retrievable as `HISTORICAL`/`SUPERSEDED`, with a
`SUPERSEDED_BY` relation. Unresolved related uncertainty stays review-required.
A later ordinary sentence has no such authority. An Addendum that spans an
interrupted PDF page may retain a long protected contextual anchor; clinical
review is still required for ambiguous co-reference.

**Primary negative.** The generic “negative for” construction is now accepted
as explicit negation. When it occurs in a diagnostic summary, the negative fact
can carry primary salience and lead the clinical summary, while a separate
positive incidental finding remains separate. Routine secondary negatives do
not acquire that salience automatically. No condition-name list is involved.

**Source function and report conclusions.** An acquisition-action predicate
(`performed`, `obtained`, `acquired`) cannot become a patient finding merely
because its object contains a lesion noun. Independently grounded adjacent
findings remain eligible. Explicit final classifications and future actions
are retained as separate source-anchored `REPORT_ASSESSMENT` and
`RECOMMENDATION` facts with a non-disease assertion state. The Report Workspace
projects them in their own small sections; it does not show them as present
findings. ReviewedClinicalRecord V1/V2 retain their evidence through the
existing canonical-fact envelope without changing the schema.

**Focused scope.** An explicit protected exam title naming an upper quadrant
resolves US Abdomen scope to `LIMITED_OR_FOCUSED` when generic UNDERSTAND extent
is unknown. The opposite-side kidney and structures outside that explicit
quadrant become `NOT_APPLICABLE`. Complete, urinary/retroperitoneal, and
unknown scopes retain their distinct behavior; a passing findings mention
does not imply a focused exam. Profiles still consume EXTRACT facts and never
create them.

**Measurements.** EXTRACT first uses a unique existing same-sentence fact. A
headed same-clause measurement (`structure: measures value`) or a clear
existential measured observation can provide a neutral source-anchored
`MEASURED_OBSERVATION` owner when no clinical fact exists. This is measurement
context, not an inferred abnormal diagnosis. Laterality and exact value spans
are retained; ambiguous values remain unassigned for review. STANDARDIZE
continues to normalize and enrich only.

At profile evaluation, a governed value may document a profile measurement
element only when its exact protected span is linked to a canonical fact,
remains present in STANDARDIZE, has source-supported anatomy and compatible
laterality, and its source measurement type matches explicit profile metadata.
This changes coverage documentation only: it does not assert an abnormality,
reinterpret an unassigned value, or override `NOT_APPLICABLE` scope.

These corrections change EXTRACT's source interpretation and the optional
profile scope projection. They do not add a new Breast profile or any
report-ID/filename rule. Human clinical review accepted the five independent
post-fix synthetic hold-out records and closed Phase D + D.1 + D.2 as one V1
checkpoint.
