/* A presentation-only projection of the existing protected Journey outputs. */
((root, factory) => {
  const model = factory();
  if (typeof module === 'object' && module.exports) module.exports = model;
  if (root) root.MRJReportModel = model;
})(typeof window !== 'undefined' ? window : null, () => {
  const complete = status => ['COMPLETE', 'NEEDS_REVIEW'].includes(status);
  const stage = (document, name) => document?.stage_status?.[name]?.status;
  const result = (document, name) => document?.stage_results?.[name] || null;
  const text = value => typeof value === 'string' ? value.trim() : '';
  const readable = value => /^(CT|CTA|MRI|MRA|MRV|MR|US|XR|DX|CR|PET|SPECT)$/.test(text(value)) ? text(value) :
    text(value).replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, char => char.toUpperCase());

  function reviewable(document) {
    const protection = result(document, 'PROTECT');
    const extraction = result(document, 'EXTRACT');
    const standardized = result(document, 'STANDARDIZE');
    return complete(stage(document, 'PROTECT')) && complete(stage(document, 'EXTRACT')) &&
      complete(stage(document, 'STANDARDIZE')) &&
      Boolean(protection?.protected_document?.report_id === document?.document_id &&
        protection.protected_document.protected_text?.trim() &&
        extraction?.report_id === document?.document_id && extraction.clinical_synthesis &&
        standardized?.report_id === document?.document_id);
  }

  function unique(values) {
    return [...new Set(values.filter(Boolean))];
  }

  function reviewProgress(entries) {
    const count = state => entries.filter(entry => entry.status === state).length;
    const reviewed = count('REVIEWED');
    const failed = count('FAILED');
    const processing = count('UPLOADING') + count('PROCESSING');
    const remaining = count('READY') + count('NEEDS_REVIEW');
    const state = remaining ? 'REVIEWING' : processing ? 'PROCESSING' :
      failed ? 'FINISHED_WITH_FAILURES' : entries.length && reviewed === entries.length ? 'COMPLETE' : 'EMPTY';
    return { total: entries.length, reviewed, failed, processing, remaining, state };
  }

  function nextReviewEntry(entries) {
    return entries.find(entry => entry.status === 'NEEDS_REVIEW' || entry.status === 'READY') || null;
  }

  function completionEligible(entries) {
    const progress = reviewProgress(entries);
    return progress.reviewed > 0 && progress.remaining === 0 && progress.processing === 0;
  }

  function acceptancePolicy(record, reportCount) {
    if (record.reviewed) return { label: 'Reviewed', confirmMajor: false };
    const confirmMajor = record.reviewAlerts.some(alert => alert.severity === 'major');
    return { label: confirmMajor ? 'Review & Accept' : reportCount > 1 ? 'Accept & Next' : 'Accept & Save',
      confirmMajor };
  }

  function validatedEvidence(fact, protectedText) {
    if (typeof protectedText !== 'string') return null;
    return (fact?.evidence_anchors || []).find(item => Number.isInteger(item.start_offset) &&
      Number.isInteger(item.end_offset) && item.start_offset >= 0 &&
      item.end_offset > item.start_offset && item.end_offset <= protectedText.length &&
      typeof item.quote === 'string' &&
      protectedText.slice(item.start_offset, item.end_offset) === item.quote) || null;
  }

  function reviewAlerts({ facts, protection, standardized, synthesis, document }) {
    const alerts = [];
    const add = (message, severity = 'review') => {
      if (!alerts.some(item => item.message === message)) alerts.push({ message, severity });
    };
    if (protection.protection_result?.review_required || stage(document, 'PROTECT') === 'NEEDS_REVIEW')
      add('Privacy protection requires confirmation before accepting this report.');
    for (const fact of facts) {
      const reasons = Array.isArray(fact.review_reason) ? fact.review_reason :
        typeof fact.review_reason === 'string' ? [fact.review_reason] : [];
      if (reasons.some(reason => ['CONFLICTING_SOURCE_ASSERTION', 'INTERNAL_SOURCE_CONFLICT',
        'INTERNAL_REPORT_CONFLICT'].includes(reason))) {
        add('Conflicting statements require review.', fact.group === 'KEY' ? 'major' : 'review');
      } else if (fact.assertion_state === 'UNKNOWN' || fact.assertion_state === 'UNCERTAIN') {
        add('Assertion is indeterminate and requires review.');
      } else if (fact.review_required) {
        add(`${text(fact.display_label) || 'A clinical finding'} requires confirmation.`);
      }
    }
    if (standardized.standardized_study_context?.procedure_mapping?.review_required)
      add('Exam classification requires review.');
    if (standardized.summary?.facts_needing_review > 0)
      add('Clinical terminology requires review.');
    if (standardized.summary?.measurements?.needs_review > 0 ||
        standardized.summary?.measurements?.unassigned_context > 0)
      add('Measurement assignment or normalization requires review.');
    if (synthesis.technical_diagnostics?.code === 'SYNTHESIS_COVERAGE_FAILURE')
      add('Clinical findings could not be fully prepared from validated evidence.', 'major');
    if (!alerts.length && ['EXTRACT', 'STANDARDIZE'].some(name => stage(document, name) === 'NEEDS_REVIEW'))
      add('The clinical record requires confirmation.');
    return alerts;
  }

  function projection(document) {
    if (!reviewable(document)) return null;
    const understanding = result(document, 'UNDERSTAND') || {};
    const protection = result(document, 'PROTECT') || {};
    const extraction = result(document, 'EXTRACT');
    const standardized = result(document, 'STANDARDIZE');
    const synthesis = extraction.clinical_synthesis;
    const study = standardized.standardized_study_context || {};
    const facts = Array.isArray(synthesis.canonical_facts) ? synthesis.canonical_facts : [];
    const present = fact => fact.assertion_state === 'PRESENT';
    const groups = {
      key: facts.filter(fact => fact.group === 'KEY' && present(fact)),
      secondary: facts.filter(fact => fact.group === 'SECONDARY' && present(fact)),
      negative: facts.filter(fact => fact.group === 'NEGATIVE' && fact.assertion_state === 'ABSENT_NEGATED'),
      diagnostic: facts.filter(fact => fact.group === 'DIAGNOSTIC'),
    };
    const protectedText = typeof protection.protected_document?.protected_text === 'string'
      ? protection.protected_document.protected_text : '';
    const reviewAlertsValue = reviewAlerts({ facts, protection, standardized, synthesis, document });
    const measurements = [];
    for (const item of standardized.standardized_facts || []) {
      const owner = facts.find(fact => fact.fact_id === item.source_fact_id);
      for (const measurement of item.standardized_measurements || []) {
        if (!text(measurement.original_text)) continue;
        const normalized = measurement.mapping_status === 'MATCHED' &&
          measurement.normalized_value != null && text(measurement.normalized_unit);
        measurements.push({
          label: text(owner?.display_label) || 'Measurement',
          value: normalized ? `${measurement.normalized_value} ${measurement.normalized_unit}` : measurement.original_text,
          context: normalized ? measurement.original_text : 'Review source value',
        });
      }
    }
    for (const measurement of standardized.unassigned_measurements || []) {
      if (text(measurement.original_text)) measurements.push({
        label: 'Unassigned measurement', value: measurement.original_text, context: 'Needs review',
      });
    }
    const identity = understanding.document_context?.identity || {};
    const title = text(study.original_exam_name) || text(document.original_filename) || 'Clinical report';
    const descriptor = unique([
      text(study.normalized_modality), text(study.normalized_body_region),
      text(study.normalized_laterality),
    ].filter(value => value && !['UNKNOWN', 'NOT_DETERMINED'].includes(value))).map(readable).join(' · ');
    const coverageFailure = synthesis.technical_diagnostics?.code === 'SYNTHESIS_COVERAGE_FAILURE';
    return {
      title, descriptor: descriptor || readable(identity.subdomain_or_family),
      filename: text(document.original_filename),
      summary: text(synthesis.clinical_synthesis), groups, measurements,
      protectedText, reviewAlerts: reviewAlertsValue,
      reviewIssues: reviewAlertsValue.map(item => item.message),
      needsReview: ['PROTECT', 'EXTRACT', 'STANDARDIZE'].some(name => stage(document, name) === 'NEEDS_REVIEW') ||
        reviewAlertsValue.length > 0,
      reviewed: document.review_status === 'REVIEWED',
      coverageFailure,
    };
  }

  return { projection, reviewable, reviewProgress, nextReviewEntry, completionEligible,
    acceptancePolicy, validatedEvidence };
});
