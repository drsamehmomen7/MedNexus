const test = require('node:test');
const assert = require('node:assert/strict');
const { projection, reviewable, reviewProgress, nextReviewEntry, completionEligible,
  acceptancePolicy, validatedEvidence } =
  require('../report-workspace-model.js');

function report(overrides = {}) {
  const protectedText = 'Findings: Right renal cyst measures 12 mm. No hydronephrosis.';
  const facts = [
    { fact_id: 'one', group: 'KEY', display_label: 'Right renal cyst', assertion_state: 'PRESENT',
      evidence_anchors: [{ start_offset: 10, end_offset: 26, quote: 'Right renal cyst' }] },
    { fact_id: 'two', group: 'NEGATIVE', display_label: 'Hydronephrosis', assertion_state: 'ABSENT_NEGATED',
      evidence_anchors: [] },
    { fact_id: 'three', group: 'DIAGNOSTIC', display_label: 'Possible benign etiology',
      assertion_state: 'UNCERTAIN', evidence_anchors: [] },
    { fact_id: 'four', group: 'NEGATIVE', display_label: 'Liver lesion', assertion_state: 'NOT_DOCUMENTED',
      evidence_anchors: [] },
  ];
  return {
    document_id: 'a'.repeat(32), original_filename: 'Synthetic ultrasound.txt', source_type: 'txt',
    review_status: 'CLEAR',
    stage_status: { PROTECT: { status: 'COMPLETE' }, EXTRACT: { status: 'COMPLETE' },
      STANDARDIZE: { status: 'COMPLETE' } },
    stage_results: {
      UNDERSTAND: { document_context: { identity: { subdomain_or_family: 'ULTRASOUND' } } },
      PROTECT: { protected_document: { report_id: 'a'.repeat(32), protected_text: protectedText },
        protection_result: { review_required: false } },
      EXTRACT: { report_id: 'a'.repeat(32),
        clinical_synthesis: { clinical_synthesis: 'A right renal cyst is present.', canonical_facts: facts } },
      STANDARDIZE: { report_id: 'a'.repeat(32), standardized_study_context: {
        original_exam_name: 'Renal ultrasound', normalized_modality: 'US', normalized_body_region: 'KIDNEY',
      }, summary: { facts_needing_review: 0, measurements: { needs_review: 0, unassigned_context: 0 } },
      standardized_facts: [{ source_fact_id: 'one', standardized_measurements: [{
        original_text: '12 mm', normalized_value: '12', normalized_unit: 'mm', mapping_status: 'MATCHED',
      }] }], unassigned_measurements: [] },
    },
    ...overrides,
  };
}

test('real Journey fields become distinct findings, explicit negatives, and measurements', () => {
  const value = projection(report());
  assert.equal(value.title, 'Renal ultrasound');
  assert.equal(value.descriptor, 'US · Kidney');
  assert.deepEqual(value.groups.key.map(fact => fact.display_label), ['Right renal cyst']);
  assert.deepEqual(value.groups.negative.map(fact => fact.display_label), ['Hydronephrosis']);
  assert.deepEqual(value.groups.diagnostic.map(fact => fact.display_label), ['Possible benign etiology']);
  assert.deepEqual(value.measurements, [{ label: 'Right renal cyst', value: '12 mm', context: '12 mm' }]);
  assert.equal(value.protectedText, report().stage_results.PROTECT.protected_document.protected_text);
});

test('current Addendum, primary negative, assessment and recommendation project separately', () => {
  const item = report();
  const facts = item.stage_results.EXTRACT.clinical_synthesis.canonical_facts;
  facts[0].temporal_status = 'SUPERSEDED';
  facts[1].salience = 'PRIMARY';
  facts.push({ fact_id: 'current', group: 'KEY', display_label: 'Implant stable',
    assertion_state: 'PRESENT', temporal_status: 'CURRENT', evidence_anchors: [] });
  facts.push({ fact_id: 'assessment', group: 'ASSESSMENT', display_label: 'CATEGORY 2 benign',
    assertion_state: 'NOT_APPLICABLE', evidence_anchors: [] });
  facts.push({ fact_id: 'recommendation', group: 'RECOMMENDATION', display_label: 'Follow-up advised',
    assertion_state: 'NOT_APPLICABLE', evidence_anchors: [] });
  const value = projection(item);
  assert.deepEqual(value.groups.key.map(fact => fact.display_label), ['Implant stable']);
  assert.deepEqual(value.groups.negative.map(fact => fact.fact_id), ['two']);
  assert.deepEqual(value.groups.assessment.map(fact => fact.fact_id), ['assessment']);
  assert.deepEqual(value.groups.recommendation.map(fact => fact.fact_id), ['recommendation']);
});

test('review issues are conditional and not-documented is never negative', () => {
  const quiet = report();
  quiet.stage_results.EXTRACT.clinical_synthesis.canonical_facts.splice(2, 1);
  assert.deepEqual(projection(quiet).reviewIssues, []);
  assert.equal(projection(quiet).needsReview, false);
  const flagged = report();
  flagged.stage_results.STANDARDIZE.summary.measurements.needs_review = 1;
  assert.match(projection(flagged).reviewIssues.join(' '), /Measurement assignment or normalization requires review/);
  assert.equal(projection(flagged).groups.negative.length, 1);
});

test('major review uses a genuine conflicting key finding and not an inferred exam mismatch', () => {
  const flagged = report();
  flagged.stage_results.EXTRACT.clinical_synthesis.canonical_facts[0].review_reason =
    ['CONFLICTING_SOURCE_ASSERTION'];
  const value = projection(flagged);
  assert.deepEqual(value.reviewAlerts, [{ message: 'Conflicting statements require review.', severity: 'major' },
    { message: 'Assertion is indeterminate and requires review.', severity: 'review' }]);
  assert.equal(value.needsReview, true);
  assert.equal(value.reviewIssues.some(message => /mismatch/i.test(message)), false);
});

test('an existing extraction conflict string is a major alert for a key finding', () => {
  const flagged = report();
  flagged.stage_results.EXTRACT.clinical_synthesis.canonical_facts.splice(2, 1);
  flagged.stage_results.EXTRACT.clinical_synthesis.canonical_facts[0].review_reason =
    'INTERNAL_REPORT_CONFLICT';
  assert.deepEqual(projection(flagged).reviewAlerts,
    [{ message: 'Conflicting statements require review.', severity: 'major' }]);
});

test('review progress distinguishes complete, processing, failures, and remaining review', () => {
  const state = statuses => reviewProgress(statuses.map(status => ({ status }))).state;
  assert.equal(state(['REVIEWED']), 'COMPLETE');
  assert.equal(state(['REVIEWED', 'PROCESSING']), 'PROCESSING');
  assert.equal(state(['REVIEWED', 'FAILED']), 'FINISHED_WITH_FAILURES');
  assert.equal(state(['REVIEWED', 'READY']), 'REVIEWING');
});

test('one and three reviewed reports enter completion only when nothing remains or processes', () => {
  const eligible = statuses => completionEligible(statuses.map(status => ({ status })));
  assert.equal(eligible(['REVIEWED']), true);
  assert.equal(eligible(['REVIEWED', 'REVIEWED', 'REVIEWED']), true);
  assert.equal(eligible(['REVIEWED', 'REVIEWED', 'READY']), false);
  assert.equal(eligible(['REVIEWED', 'REVIEWED', 'NEEDS_REVIEW']), false);
  assert.equal(eligible(['REVIEWED', 'REVIEWED', 'PROCESSING']), false);
  assert.equal(eligible(['REVIEWED', 'UPLOADING']), false);
  assert.equal(eligible(['REVIEWED', 'REVIEWED', 'FAILED']), true);
  assert.equal(eligible(['FAILED']), false);
  assert.equal(eligible([]), false);
});

test('only a genuine Major Review alert requires confirmation and changes acceptance wording', () => {
  const major = projection(report());
  major.reviewAlerts = [{ message: 'Conflicting statements require review.', severity: 'major' }];
  assert.deepEqual(acceptancePolicy(major, 3), { label: 'Review & Accept', confirmMajor: true });
  const ordinary = { ...major, reviewAlerts: [{ message: 'Check privacy.', severity: 'review' }] };
  assert.deepEqual(acceptancePolicy(ordinary, 3), { label: 'Accept & Next', confirmMajor: false });
  assert.deepEqual(acceptancePolicy({ ...ordinary, reviewAlerts: [] }, 1),
    { label: 'Accept & Save', confirmMajor: false });
  assert.deepEqual(acceptancePolicy({ ...major, reviewed: true }, 3),
    { label: 'Reviewed', confirmMajor: false });
});

test('accepting a report advances to the next pending item in queue order', () => {
  const entries = [{ status: 'REVIEWED' }, { status: 'PROCESSING' }, { status: 'NEEDS_REVIEW' },
    { status: 'READY' }];
  assert.equal(nextReviewEntry(entries), entries[2]);
  entries[2].status = 'REVIEWED';
  assert.equal(nextReviewEntry(entries), entries[3]);
  entries[3].status = 'REVIEWED';
  assert.equal(nextReviewEntry(entries), null);
});

test('protected evidence is highlighted only for exact validated offsets and quote', () => {
  const source = 'Findings: Right renal cyst measures 12 mm.';
  const anchor = { start_offset: 10, end_offset: 26, quote: 'Right renal cyst' };
  assert.deepEqual(validatedEvidence({ evidence_anchors: [anchor] }, source), anchor);
  assert.equal(validatedEvidence({ evidence_anchors: [{ ...anchor, quote: 'Left renal cyst' }] }, source), null);
  assert.equal(validatedEvidence({ evidence_anchors: [{ ...anchor, end_offset: 100 }] }, source), null);
});

test('a record is never ready before current protected extraction and standardization exist', () => {
  const incomplete = report();
  incomplete.stage_status.STANDARDIZE.status = 'FAILED';
  assert.equal(reviewable(incomplete), false);
  assert.equal(projection(incomplete), null);
  const mismatched = report();
  mismatched.stage_results.STANDARDIZE.report_id = 'b'.repeat(32);
  assert.equal(reviewable(mismatched), false);
});

test('governed exam coverage stays separate from negative findings and review alerts', () => {
  const item = report();
  item.stage_results.EXTRACT.clinical_synthesis.canonical_facts.splice(2, 1);
  item.stage_results.STANDARDIZE.profile_evaluation = {
    status: 'EVALUATED', profile_id: 'MRJ_RAD_US_ABDOMEN', profile_version: '0.1',
    profile_name: 'Ultrasound Abdomen', scope: 'COMPLETE', compatibility: 'INSUFFICIENT_INFORMATION',
    review_alerts: [], coverage: [
      { section_id: 'liver', label: 'Liver', coverage: 'NOT_DOCUMENTED', assertion: 'INDETERMINATE', elements: [] },
      { section_id: 'pancreas', label: 'Pancreas', coverage: 'LIMITED_OR_NOT_VISUALIZED',
        assertion: 'INDETERMINATE', elements: [] },
    ],
  };
  const value = projection(item);
  assert.equal(value.title, 'Ultrasound Abdomen');
  assert.deepEqual(value.profile.coverage.map(row => row.coverage),
    ['NOT_DOCUMENTED', 'LIMITED_OR_NOT_VISUALIZED']);
  assert.equal(value.groups.negative.length, 1);
  assert.deepEqual(value.reviewAlerts, []);
  item.stage_results.STANDARDIZE.profile_evaluation.compatibility = 'POSSIBLE_ANATOMY_MISMATCH';
  item.stage_results.STANDARDIZE.profile_evaluation.review_alerts = [{ code: 'PROFILE_ANATOMY_MISMATCH' }];
  assert.match(projection(item).reviewIssues.join(' '), /Extracted anatomy may not match the exam/);
  assert.equal(projection(item).reviewAlerts.find(alert => /Extracted anatomy/.test(alert.message)).severity, 'major');
});
