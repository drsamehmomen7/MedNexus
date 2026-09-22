const getElement = id => globalThis.document.getElementById(id);
const makeElement = tag => globalThis.document.createElement(tag);

const MAX_BATCH_REPORTS = 10;
const SUPPORTED_EXTENSIONS = new Set(['txt', 'docx', 'pdf']);
const TERMINAL_STATES = new Set(['COMPLETE', 'NEEDS_REVIEW', 'FAILED']);
const JOURNEY_STAGES = ['UNDERSTAND', 'PROTECT', 'EXTRACT', 'STANDARDIZE', 'ANALYZE', 'VISUALIZE', 'INDICATORS'];

let inputMode = 'file';
let workflowMode = 'single';
let singlePayload = null;
let singleRun = null;
let singleSelectedFile = null;
let batchEntries = [];
let batchRun = null;
let selectedBatchDocumentId = null;
let batchProcessing = false;
let batchSubmittedCount = 0;
let activeJourneyStage = 'UNDERSTAND';
let protectProcessing = false;
let protectionSubmittedCount = 0;
let activeCompareTarget = null;
let compareRequestVersion = 0;
let artifactRequestVersion = 0;
let protectedArtifactUrl = null;
let originalArtifactUrl = null;
let activeProtectionView = { pdfOrigin: false, protectedText: '' };

const LABELS = {
  UNKNOWN: 'Not determined', NEEDS_REVIEW: 'Needs Review', NOT_STARTED: 'Not Started',
  QUEUED: 'Queued', PROCESSING: 'Processing', COMPLETE: 'Complete', FAILED: 'Failed',
  BLOCKED: 'Blocked', OTHER: 'Other / Requires Review',
  ADMISSION_DISCHARGE: 'Admission / Discharge',
  RADIOLOGY_REPORT: 'Radiology Report',
  LABORATORY_REPORT: 'Laboratory Report',
  EMERGENCY_REPORT: 'Emergency Report',
  ADMISSION_NOTE: 'Admission Note',
  DISCHARGE_SUMMARY: 'Discharge Summary',
  PUBLIC_HEALTH_DOCUMENT: 'Public Health Document',
  X_RAY: 'X-ray',
  NUCLEAR_MEDICINE: 'Nuclear Medicine',
  ENGLISH: 'English',
  ARABIC: 'Arabic',
  MIXED: 'Mixed Arabic / English',
  COMPLETED_REPORT: 'Completed Report',
  STRUCTURED_TEMPLATE: 'Structured Template',
  PARTIAL_REPORT: 'Partial Report',
  WITH_CONTRAST: 'With contrast',
  WITHOUT_CONTRAST: 'Without contrast',
  PRE_AND_POST_CONTRAST: 'Pre/Post contrast',
  CT: 'CT', CTA: 'CTA', MRI: 'MRI', MRA: 'MRA', MRV: 'MRV',
  CR: 'CR', DX: 'DX', XR: 'XR', SPECT: 'SPECT', PET: 'PET',
  SPECT_CT: 'SPECT / CT', PET_CT: 'PET / CT',
  GENERAL_DIAGNOSTIC: 'General Diagnostic',
  CONTRAST_STUDY: 'Contrast Study',
  DYNAMIC_FUNCTIONAL_STUDY: 'Dynamic / Functional Study',
  STANDARD_VIEWS: 'Standard Views',
  TOMOSYNTHESIS: 'Tomosynthesis',
  MULTIPLANAR_RECONSTRUCTION: 'Multiplanar Reconstruction',
  ANGIOGRAPHIC: 'Angiographic',
};

const REGION_LABELS = {
  STUDY_OR_EVENT_IDENTITY: 'Study Identity',
  CLINICAL_OR_REPORTING_INDICATION: 'Clinical Indication',
  TECHNIQUE_OR_ACQUISITION: 'Technique / Acquisition',
  OBSERVATION_NARRATIVE: 'Findings / Observation Narrative',
  CONCLUSION_OR_STATUS: 'Impression / Conclusion',
  COMPARISON_OR_PRIOR_CONTEXT: 'Comparison / Prior Study',
  RECOMMENDATION_OR_FUTURE_ACTION: 'Recommendation / Future Action',
  PROFESSIONAL_OR_AUTHORITY_AUTHENTICATION: 'Professional Authentication',
};

const OTHER_REASON_LABELS = {
  UNSUPPORTED_FAMILY: 'The imaging family is outside the current supported set.',
  CONFLICTING_CURRENT_FAMILY: 'Conflicting current-study family evidence requires review.',
  INSUFFICIENT_FAMILY_EVIDENCE: 'The imaging family does not have enough governed evidence.',
  INTERVENTIONAL_PROCEDURE: 'This Radiology procedure does not belong to a supported diagnostic imaging family.',
};

const PROTECTION_CATEGORY_LABELS = {
  Names: 'Names',
  Identifiers: 'Patient identifiers',
  Dates: 'Dates',
  'Contact Details': 'Contact details',
  'Locations and Facilities': 'Locations and facilities',
  'Other Identity Signals': 'Other identity signals',
};

function label(value) {
  const key = String(value || 'UNKNOWN');
  return LABELS[key] || key.toLowerCase().replaceAll('_', ' ').replace(/\b\w/g, character => character.toUpperCase());
}

function publicPolicyLabel(value) {
  return String(value || 'Selected privacy workflow')
    .replace(/^MedNexus\s+/i, '')
    .replace(/^MRJ\s+/i, '');
}

function isPresent(value) {
  return value !== null && value !== undefined && value !== '' && (!Array.isArray(value) || value.length > 0);
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fileExtension(name) {
  const parts = String(name || '').split('.');
  return parts.length > 1 ? parts.pop().toLowerCase() : '';
}

function terminalState(state) {
  return TERMINAL_STATES.has(state);
}

function getRunDocumentById(run, documentId) {
  return (run?.documents || []).find(runDocument => runDocument.document_id === documentId) || null;
}

function getRunDocumentResult(run, documentId) {
  return getRunDocumentStageResult(run, documentId, 'UNDERSTAND');
}

function getRunDocumentStageResult(run, documentId, stage) {
  return getRunDocumentById(run, documentId)?.stage_results?.[stage] || null;
}

function adjacentRunDocumentId(run, documentId, offset) {
  const documents = run?.documents || [];
  const index = documents.findIndex(runDocument => runDocument.document_id === documentId);
  const adjacent = index + offset;
  return index >= 0 && adjacent >= 0 && adjacent < documents.length ? documents[adjacent].document_id : null;
}

function activeWorkflowResult(nextMode, singleResult, run, selectedDocumentId) {
  return nextMode === 'single' ? (singleResult || null) : getRunDocumentResult(run, selectedDocumentId);
}

function buildBatchReportRows(run, stage = 'UNDERSTAND') {
  return (run?.documents || []).map(runDocument => {
    const result = runDocument.stage_results?.[stage] || null;
    const state = runDocument.stage_status?.[stage]?.status || 'NOT_STARTED';
    const model = stage === 'PROTECT'
      ? buildProtectionViewModel(result, { state })
      : buildReportViewModel(result, { state });
    return {
      documentId: runDocument.document_id,
      order: runDocument.order,
      filename: runDocument.original_filename,
      recognition: stage === 'PROTECT'
        ? (result ? model.policy : label(state))
        : result ? [model.modality, model.bodyRegion].filter(Boolean).join(' · ') : 'No result',
      confidence: stage === 'PROTECT' ? '' : model.confidence,
      confidenceBand: stage === 'PROTECT' ? '' : model.confidenceBand,
      state, result,
      error: runDocument.stage_errors?.[stage] || runDocument.error || null,
    };
  });
}

function createBatchDataTrace({ selectedCount, submittedCount, run }) {
  const runDocuments = run?.documents || [];
  const terminal = runDocuments.filter(runDocument => terminalState(runDocument.stage_status?.UNDERSTAND?.status)).length;
  const results = runDocuments.filter(runDocument => Boolean(runDocument.stage_results?.UNDERSTAND)).length;
  const rows = buildBatchReportRows(run);
  return {
    selected: selectedCount,
    submitted: submittedCount,
    journeyRunDocuments: runDocuments.length,
    terminal,
    apiResultsReturned: results,
    frontendResultsStored: results,
    reportRowsGenerated: rows.length,
  };
}

function createProtectionDataTrace({ selectedCount, submittedCount, run }) {
  const runDocuments = run?.documents || [];
  const eligible = run?.protection_summary?.eligible || 0;
  const terminal = runDocuments.filter(runDocument =>
    TERMINAL_STATES.has(runDocument.stage_status?.PROTECT?.status),
  ).length;
  const results = runDocuments.filter(runDocument => Boolean(runDocument.stage_results?.PROTECT)).length;
  return {
    selected: selectedCount,
    understandResults: runDocuments.filter(runDocument => Boolean(runDocument.stage_results?.UNDERSTAND)).length,
    protectEligible: eligible,
    protectSubmitted: submittedCount,
    protectTerminal: terminal,
    protectionResultsStored: results,
    navigatorResults: buildBatchReportRows(run, 'PROTECT').length,
  };
}

function protectionEligibleDocumentIds(run) {
  return [...(run?.handoff?.protect?.eligible_document_ids || [])];
}

async function processSequentialBatch(entries, processEntry, presentAfterEntry) {
  for (let index = 0; index < entries.length; index += 1) {
    const entry = entries[index];
    try {
      await processEntry(entry, index);
    } catch (failure) {
      entry.status = 'FAILED';
      entry.error = failure.message || 'MRJ could not process this report.';
    }
    try {
      presentAfterEntry(entry, index);
    } catch (_) {
      // Presentation is deliberately isolated from authoritative batch processing.
    }
  }
}

function setInputMode(nextMode) {
  inputMode = nextMode;
  const uploadActive = nextMode === 'file';
  getElement('fileTab').classList.toggle('active', uploadActive);
  getElement('textTab').classList.toggle('active', !uploadActive);
  getElement('fileTab').setAttribute('aria-selected', String(uploadActive));
  getElement('textTab').setAttribute('aria-selected', String(!uploadActive));
  getElement('fileMode').hidden = !uploadActive;
  getElement('fileMode').classList.toggle('active', uploadActive);
  getElement('textMode').hidden = uploadActive;
  getElement('selectedFileCard').hidden = !uploadActive || !singleSelectedFile;
  getElement('status').textContent = '';
}

function setSingleFile(file) {
  singleSelectedFile = file || null;
  const selected = Boolean(singleSelectedFile);
  getElement('selectedFileCard').hidden = !selected || inputMode !== 'file';
  getElement('fileMode').classList.toggle('has-file', selected);
  getElement('fileName').textContent = selected ? singleSelectedFile.name : 'No report selected';
  getElement('selectedFileIcon').textContent = selected ? (fileExtension(singleSelectedFile.name).toUpperCase() || 'FILE') : 'FILE';
  getElement('selectedFileMeta').textContent = selected ? `${formatBytes(singleSelectedFile.size)} · Ready` : '';
}

function setWorkflowMode(nextMode) {
  if (batchProcessing || protectProcessing) return;
  resetCompareView();
  workflowMode = nextMode;
  activeJourneyStage = 'UNDERSTAND';
  const singleActive = nextMode === 'single';
  getElement('singleModeTab').classList.toggle('active', singleActive);
  getElement('batchModeTab').classList.toggle('active', !singleActive);
  getElement('singleModeTab').setAttribute('aria-selected', String(singleActive));
  getElement('batchModeTab').setAttribute('aria-selected', String(!singleActive));
  getElement('singleWorkspace').hidden = !singleActive;
  getElement('batchWorkspace').hidden = singleActive;

  const activeResult = activeWorkflowResult(nextMode, singlePayload, batchRun, selectedBatchDocumentId);
  if (singleActive && activeResult) {
    renderReportResult(activeResult, { scroll: false });
  } else if (!singleActive && getRunDocumentById(batchRun, selectedBatchDocumentId)) {
    selectBatchDocument(selectedBatchDocumentId, false);
  } else {
    getElement('results').classList.remove('show', 'batch-view');
  }
  updateActiveStagePresentation();
  updateJourneyRail(
    singleActive ? singleRun : batchRun,
    singleActive ? singlePayload?.document_context : null,
  );
}

function renderList(target, items, renderer, emptyMessage) {
  target.replaceChildren();
  if (!items.length) {
    const empty = makeElement('div');
    empty.className = 'empty-state';
    empty.textContent = emptyMessage;
    target.append(empty);
    return;
  }
  items.forEach(value => target.append(renderer(value)));
}

function renderRows(target, rows) {
  target.replaceChildren();
  rows.filter(([, value]) => isPresent(value)).forEach(([key, value]) => {
    const row = makeElement('div');
    const term = makeElement('dt');
    const description = makeElement('dd');
    term.textContent = key;
    description.textContent = Array.isArray(value) ? value.map(label).join(' · ') : value;
    row.append(term, description);
    target.append(row);
  });
}

function xrayViewContext(context) {
  const values = [];
  if (context.views?.length) values.push(context.views.map(label).join(' / '));
  if (context.view_count) values.push(`${context.view_count}${context.view_count_qualifier === 'OR_MORE' ? ' or more' : ''} views`);
  return values.join(' · ') || null;
}

// Presentation picks a bounded subset of canonical context; it never derives clinical facts.
const RADIOLOGY_CONTEXT_RENDERERS = {
  CT: context => context.acquisition_summary || [],
  MRI: context => context.sequence_context || [],
  X_RAY: context => xrayViewContext(context),
  ULTRASOUND: context => [context.study_extent, context.vascular_context, context.specialization].filter(isPresent),
  MAMMOGRAPHY: context => context.acquisition_context || [],
  NUCLEAR_MEDICINE: () => null,
  FLUOROSCOPY: () => null,
  OTHER: () => null,
};

function buildReportViewModel(payload, options = {}) {
  const context = payload?.document_context || {};
  const identity = context.identity || {};
  const domain = identity.domain || identity.healthcare_domain || payload?.domain || 'UNKNOWN';
  const type = identity.document_type || payload?.document_type || 'UNKNOWN';
  const subdomain = identity.subdomain_or_family;
  const unknown = domain === 'UNKNOWN' || type === 'UNKNOWN';
  const lightContext = context.light_context || {};
  const family = lightContext.domain_type === 'RADIOLOGY' ? lightContext.family_context : null;
  // A mismatched family is not allowed to lend context to the selected identity.
  const current = family?.subdomain === subdomain ? family : null;
  const processing = context.processing_context || {};
  const protectReady = Boolean(processing.protect_ready);
  const review = unknown || subdomain === 'OTHER' ||
    (processing.document_review_required ?? processing.manual_review_required ?? true);
  const failed = !payload;
  const state = failed ? 'FAILED' : (options.state || (review ? 'NEEDS_REVIEW' : 'COMPLETE'));
  const valueLabel = value => Array.isArray(value) ? value.map(label).join(' · ') : label(value);
  const bodyRegion = isPresent(current?.body_region) ? valueLabel(current.body_region) : null;
  const metadata = [];
  if (!failed) {
    if (bodyRegion) metadata.push(['Body Region', bodyRegion]);
    if (isPresent(current?.contrast)) metadata.push(['Contrast', valueLabel(current.contrast)]);
    metadata.push(['Language', label(identity.language || context.document?.primary_language || payload.language)]);
    const studyFamily = current?.study_family;
    if (studyFamily && studyFamily !== subdomain && studyFamily !== 'OTHER') {
      metadata.push(['Study Family', label(studyFamily)]);
    } else {
      const acquisition = current && RADIOLOGY_CONTEXT_RENDERERS[subdomain]?.(current);
      if (isPresent(acquisition)) metadata.push(['Acquisition Context', valueLabel(acquisition)]);
    }
  }
  const canonicalRegions = (context.semantic_regions || []).filter(region => region.role);
  const regions = canonicalRegions.length
    ? canonicalRegions.map(region => REGION_LABELS[region.role] || label(region.role))
    : (context.structure || []).map(region => region.semantic_role).filter(Boolean).map(label);
  const explanations = (payload?.recognition_explanations || []).map(item => item.message).filter(Boolean);
  const confidence = identity.confidence ?? payload?.confidence;
  const band = identity.confidence_band || payload?.confidence_band;
  return {
    filename: options.sourceName || context.document?.source_name || 'Pasted medical text',
    domain: label(domain),
    type: label(type),
    modality: failed ? 'Unable to analyze' : unknown ? 'Report needs review' : label(subdomain),
    bodyRegion, metadata,
    state, failed, unknown,
    confidence: !failed && confidence != null ? `${Math.round(Number(confidence) * 100)}%` : '—',
    confidenceBand: !failed && band ? `${label(band)} Confidence` : 'No confidence result',
    confidenceNote: unknown && !failed ? 'Document type not confidently identified.' : '',
    reviewNote: failed ? options.error || 'MRJ could not process this report.'
      : subdomain === 'OTHER' ? OTHER_REASON_LABELS[current?.review_reason] || 'The imaging family requires review; no modality has been guessed.'
      : unknown ? 'There is not enough evidence to identify this report reliably.' : '',
    structures: [...new Set(regions)], explanations,
    warnings: payload?.warnings || [],
    readiness: failed ? 'Retry this report from the navigator. Other results are preserved.'
      : protectReady && review
        ? 'Recognition needs review, but this readable report is ready for Privacy Protection.'
      : protectReady ? 'Ready for Privacy Protection.'
      : 'Privacy Protection is not ready for this report.',
    handoff: protectReady ? payload?.journey?.continue_to_protect : null,
    context,
  };
}

function buildProtectionViewModel(payload, options = {}) {
  const state = options.state || payload?.protection_result?.status || 'NOT_STARTED';
  const result = payload?.protection_result || {};
  const protectedDocument = payload?.protected_document || {};
  const artifact = protectedDocument.artifact || null;
  const sourceName = String(options.sourceName || '');
  const sourceType = String(options.sourceType || '').toLowerCase();
  const pdfOrigin = sourceType === 'pdf' || sourceName.toLowerCase().endsWith('.pdf');
  const patientContext = payload?.patient_analytic_context || {};
  const provenance = payload?.protection_provenance || {};
  const populated = new Set(patientContext.populated_fields || []);
  const analyticContext = Object.entries(patientContext.fields || {})
    .filter(([name, field]) => populated.has(name) && field?.state === 'KNOWN' && isPresent(field.value))
    .map(([name, field]) => [label(name), Array.isArray(field.value) ? field.value.map(label).join(' · ') : String(field.value)]);
  const categorySummary = Object.entries(result.protected_entity_category_summary || {});
  const candidateCounts = provenance.candidate_counts || {};
  const count = name => Number.isFinite(candidateCounts[name]) ? candidateCounts[name] : 0;
  const candidateTotal = Number.isFinite(candidateCounts.total)
    ? candidateCounts.total
    : count('accepted') + count('rejected') + count('review_required') + count('pending');
  const unresolvedCount = count('review_required') + count('pending');
  const reviewSignals = Array.isArray(result.review_signal_summary)
    ? result.review_signal_summary
      .filter(item => item && item.human_label && Number(item.count) > 0)
      .map(item => ({
        category: String(item.category || ''),
        humanLabel: String(item.human_label),
        count: Number(item.count),
      }))
    : [];
  const failed = state === 'FAILED' || state === 'BLOCKED';
  const processing = state === 'PROCESSING' || state === 'QUEUED';
  const reviewRequired = Boolean(result.review_required);
  const zeroPhi = !failed && !processing && !reviewRequired && candidateTotal === 0;
  const transformedCount = categorySummary.reduce((total, [, value]) => total + Number(value || 0), 0);
  const summaryRows = zeroPhi
    ? [['PHI detection', 'No PHI detected']]
    : [
        ['Automatic transformations', transformedCount ? `${transformedCount} applied` : 'None applied'],
        ...categorySummary
          .filter(([, value]) => Number(value) > 0)
          .map(([name, value]) => [
            PROTECTION_CATEGORY_LABELS[name] || label(name),
            `${value} protected`,
          ]),
        ...(unresolvedCount > 0 ? [['Requires review', `${unresolvedCount} ${unresolvedCount === 1 ? 'signal' : 'signals'}`]] : []),
      ];
  const reviewMessage = reviewRequired
    ? reviewSignals.length
      ? reviewSignals
        .map(item => `${item.humanLabel}: ${item.count}`)
        .join(' · ')
      : unresolvedCount > 0
      ? `${unresolvedCount} unresolved identity ${unresolvedCount === 1 ? 'signal requires' : 'signals require'} human review.`
      : 'One or more identity signals require human review.'
    : '';
  return {
    state,
    failed,
    processing,
    policy: publicPolicyLabel(result.policy_display_name || options.policyLabel),
    categorySummary,
    summaryRows,
    analyticContext,
    protectedText: protectedDocument.protected_text || '',
    artifact,
    pdfOrigin,
    hasPdfArtifact: Boolean(
      artifact?.availability && artifact?.media_type === 'application/pdf',
    ),
    protectedFilename: artifact?.filename
      || (sourceName.toLowerCase().endsWith('.pdf')
        ? `${sourceName.slice(0, -4)}_PROTECTED.pdf`
        : 'MRJ_PROTECTED.pdf'),
    warnings: result.warnings || protectedDocument.warnings || [],
    reviewRequired,
    zeroPhi,
    candidateTotal,
    unresolvedCount,
    reviewSignals,
    reviewMessage,
    error: options.error || '',
  };
}

function buildCompareLines(value, counterpart) {
  const lines = String(value || '').split('\n');
  const otherLines = String(counterpart || '').split('\n');
  return lines.map((text, index) => ({
    text,
    changed: text !== (otherLines[index] ?? ''),
  }));
}

function renderComparePane(target, value, counterpart) {
  const lines = buildCompareLines(value, counterpart);
  target.replaceChildren(...lines.map((line, index) => {
    const item = makeElement('span');
    item.className = `compare-line${line.changed ? ' changed' : ''}`;
    item.textContent = `${line.text}${index < lines.length - 1 ? '\n' : ''}`;
    return item;
  }));
}

function buildNextStagePresentation(run, protectionModel) {
  const documents = run?.documents || [];
  if (documents.length > 1 || run?.mode === 'batch') {
    const summary = run?.protection_summary || {};
    const ready = summary.complete || 0;
    const review = summary.needs_review || 0;
    const unavailable = (summary.failed || 0) + (summary.blocked || 0);
    const parts = [
      `${ready} ${ready === 1 ? 'report is' : 'reports are'} ready for the next stage`,
    ];
    if (review) parts.push(`${review} ${review === 1 ? 'requires' : 'require'} review`);
    if (unavailable) parts.push(`${unavailable} ${unavailable === 1 ? 'is' : 'are'} unavailable`);
    return {
      message: `${parts.join(' · ')}. Unaffected reports remain eligible to continue.`,
      buttonLabel: ready
        ? `Continue ${ready} Eligible ${ready === 1 ? 'Report' : 'Reports'} — Coming next`
        : 'Continue to EXTRACT — Coming next',
    };
  }
  if (protectionModel.state === 'COMPLETE') {
    return {
      message: 'This report is ready for the next stage.',
      buttonLabel: 'Continue 1 Eligible Report — Coming next',
    };
  }
  if (protectionModel.reviewRequired) {
    return {
      message: 'Resolve the protection review before this report continues.',
      buttonLabel: 'Continue to EXTRACT — Coming next',
    };
  }
  return {
    message: 'Clinical extraction begins in a future checkpoint.',
    buttonLabel: 'Continue to EXTRACT — Coming next',
  };
}

function compareTargetKey(target) {
  return target ? `${target.runId}:${target.documentId}` : '';
}

function revokeArtifactUrl(name) {
  const value = name === 'protected' ? protectedArtifactUrl : originalArtifactUrl;
  if (value) globalThis.URL?.revokeObjectURL(value);
  if (name === 'protected') protectedArtifactUrl = null;
  else originalArtifactUrl = null;
}

function clearPdfFrame(id) {
  const frame = getElement(id);
  if (frame) frame.src = 'about:blank';
}

function releaseOriginalArtifact() {
  clearPdfFrame('originalComparePdf');
  revokeArtifactUrl('original');
}

function releaseAllArtifactUrls() {
  releaseOriginalArtifact();
  clearPdfFrame('protectedPdfViewer');
  clearPdfFrame('protectedComparePdf');
  revokeArtifactUrl('protected');
}

function protectedArtifactEndpoint(target) {
  return `/api/v1/understanding/journey-runs/${encodeURIComponent(target.runId)}/documents/${encodeURIComponent(target.documentId)}/protected-artifact`;
}

function originalArtifactEndpoint(target) {
  return `/api/v1/understanding/journey-runs/${encodeURIComponent(target.runId)}/documents/${encodeURIComponent(target.documentId)}/compare-artifact`;
}

async function artifactBlob(endpoint, method, fallback) {
  const response = await fetch(endpoint, { method, cache: 'no-store' });
  if (!response.ok) {
    let detail = fallback;
    try {
      detail = (await response.json()).detail || detail;
    } catch (_) {
      // The response had no JSON error body.
    }
    throw Error(detail);
  }
  const blob = await response.blob();
  if (blob.type !== 'application/pdf') throw Error(fallback);
  return blob;
}

async function loadProtectedPdf(target, artifact) {
  if (!target) return;
  const requestVersion = ++artifactRequestVersion;
  const targetKey = compareTargetKey(target);
  getElement('protectedPdfStatus').textContent = 'Preparing protected document…';
  try {
    const blob = await artifactBlob(
      protectedArtifactEndpoint(target),
      'GET',
      'The protected PDF is unavailable.',
    );
    if (requestVersion !== artifactRequestVersion || targetKey !== compareTargetKey(activeCompareTarget)) return;
    revokeArtifactUrl('protected');
    protectedArtifactUrl = globalThis.URL.createObjectURL(blob);
    getElement('protectedPdfViewer').src = protectedArtifactUrl;
    getElement('protectedPdfDownloadBtn').href = protectedArtifactUrl;
    getElement('protectedPdfDownloadBtn').download = artifact?.filename || 'MRJ_PROTECTED.pdf';
    getElement('protectedPdfDownloadBtn').hidden = false;
    getElement('protectedPdfStatus').textContent = '';
    getElement('compareViewBtn').disabled = !activeCompareTarget;
  } catch (failure) {
    if (requestVersion !== artifactRequestVersion || targetKey !== compareTargetKey(activeCompareTarget)) return;
    clearPdfFrame('protectedPdfViewer');
    getElement('protectedPdfDownloadBtn').hidden = true;
    getElement('compareViewBtn').disabled = true;
    getElement('protectedPdfStatus').textContent = failure.message || 'The protected PDF is unavailable.';
  }
}

function setProtectViewButton(activeId) {
  ['protectedViewBtn', 'compareViewBtn', 'textViewBtn'].forEach(id => {
    const active = id === activeId;
    getElement(id).classList.toggle('active', active);
    getElement(id).setAttribute('aria-pressed', String(active));
  });
}

function resetCompareView(target = null, protectedOutput = '', pdfOrigin = false, artifact = null) {
  compareRequestVersion += 1;
  artifactRequestVersion += 1;
  releaseAllArtifactUrls();
  activeCompareTarget = target;
  activeProtectionView = { pdfOrigin, protectedText: protectedOutput };
  getElement('originalCompareText').textContent = '';
  getElement('protectedCompareText').textContent = protectedOutput;
  getElement('originalCompareText').hidden = pdfOrigin;
  getElement('protectedCompareText').hidden = pdfOrigin;
  getElement('comparePanel').hidden = true;
  getElement('protectedPdfPanel').hidden = !pdfOrigin;
  getElement('protectedText').hidden = pdfOrigin;
  getElement('compareStatus').hidden = true;
  getElement('compareStatus').textContent = '';
  getElement('protectedPdfStatus').textContent = pdfOrigin ? 'Preparing protected document…' : '';
  getElement('protectedPdfDownloadBtn').hidden = true;
  getElement('protectedViewBtn').textContent = pdfOrigin ? 'Protected PDF' : 'Protected Report';
  getElement('textViewBtn').hidden = !pdfOrigin;
  setProtectViewButton('protectedViewBtn');
  getElement('compareViewBtn').disabled = pdfOrigin
    ? true
    : !target || !protectedOutput;
  if (pdfOrigin) loadProtectedPdf(target, artifact);
}

function showProtectedView() {
  compareRequestVersion += 1;
  releaseOriginalArtifact();
  getElement('originalCompareText').textContent = '';
  getElement('comparePanel').hidden = true;
  getElement('protectedPdfPanel').hidden = !activeProtectionView.pdfOrigin;
  getElement('protectedText').hidden = activeProtectionView.pdfOrigin;
  getElement('compareStatus').hidden = true;
  getElement('compareStatus').textContent = '';
  setProtectViewButton('protectedViewBtn');
  getElement('compareViewBtn').disabled = !activeCompareTarget
    || (activeProtectionView.pdfOrigin ? !protectedArtifactUrl : !activeProtectionView.protectedText);
}

function showTextView() {
  compareRequestVersion += 1;
  releaseOriginalArtifact();
  getElement('comparePanel').hidden = true;
  getElement('protectedPdfPanel').hidden = true;
  getElement('protectedText').hidden = false;
  getElement('compareStatus').hidden = true;
  getElement('compareStatus').textContent = '';
  setProtectViewButton('textViewBtn');
}

async function showCompareView() {
  const target = activeCompareTarget;
  if (!target || (!activeProtectionView.protectedText && !activeProtectionView.pdfOrigin)) return;
  if (activeProtectionView.pdfOrigin && !protectedArtifactUrl) return;
  const targetKey = compareTargetKey(target);
  const requestVersion = ++compareRequestVersion;
  releaseOriginalArtifact();
  getElement('compareViewBtn').disabled = true;
  getElement('compareStatus').hidden = false;
  getElement('compareStatus').textContent = 'Loading the retained source for this temporary comparison…';
  try {
    if (activeProtectionView.pdfOrigin) {
      const originalBlob = await artifactBlob(
        originalArtifactEndpoint(target),
        'POST',
        'MRJ could not open the original PDF for comparison.',
      );
      if (requestVersion !== compareRequestVersion || targetKey !== compareTargetKey(activeCompareTarget)) return;
      originalArtifactUrl = globalThis.URL.createObjectURL(originalBlob);
      getElement('originalComparePdf').src = originalArtifactUrl;
      getElement('protectedComparePdf').src = protectedArtifactUrl || 'about:blank';
      getElement('originalComparePdf').hidden = false;
      getElement('protectedComparePdf').hidden = false;
      getElement('originalCompareText').hidden = true;
      getElement('protectedCompareText').hidden = true;
      getElement('originalCompareTitle').textContent = 'Original PDF';
      getElement('protectedCompareTitle').textContent = 'Protected PDF';
    } else {
      const response = await fetch(
        `/api/v1/understanding/journey-runs/${encodeURIComponent(target.runId)}/documents/${encodeURIComponent(target.documentId)}/compare-source`,
        { method: 'POST', cache: 'no-store' },
      );
      const payload = await responsePayload(response, 'MRJ could not open the original report for comparison.');
      if (requestVersion !== compareRequestVersion || targetKey !== compareTargetKey(activeCompareTarget)) return;
      const originalText = payload.source_text || '';
      const protectedText = activeProtectionView.protectedText;
      renderComparePane(getElement('originalCompareText'), originalText, protectedText);
      renderComparePane(getElement('protectedCompareText'), protectedText, originalText);
      getElement('originalComparePdf').hidden = true;
      getElement('protectedComparePdf').hidden = true;
      getElement('originalCompareText').hidden = false;
      getElement('protectedCompareText').hidden = false;
      getElement('originalCompareTitle').textContent = 'Original Text';
      getElement('protectedCompareTitle').textContent = 'Protected Text';
    }
    getElement('protectedPdfPanel').hidden = true;
    getElement('protectedText').hidden = true;
    getElement('comparePanel').hidden = false;
    setProtectViewButton('compareViewBtn');
    getElement('compareStatus').textContent = 'Sensitive original shown temporarily for this review. It is not stored by the browser.';
  } catch (failure) {
    if (requestVersion !== compareRequestVersion || targetKey !== compareTargetKey(activeCompareTarget)) return;
    getElement('originalCompareText').textContent = '';
    getElement('comparePanel').hidden = true;
    getElement('protectedPdfPanel').hidden = !activeProtectionView.pdfOrigin;
    getElement('protectedText').hidden = activeProtectionView.pdfOrigin;
    getElement('compareStatus').hidden = false;
    getElement('compareStatus').textContent = failure.message || 'The original report is unavailable for comparison.';
  } finally {
    if (requestVersion === compareRequestVersion && targetKey === compareTargetKey(activeCompareTarget)) {
      getElement('compareViewBtn').disabled = false;
    }
  }
}

function prepareResultsWorkspace(batchView) {
  getElement('results').classList.toggle('batch-view', batchView);
  getElement('batchReportBrowser').hidden = !batchView;
  getElement('reportNavigation').hidden = !batchView;
}

function updateActiveStagePresentation() {
  const protectActive = activeJourneyStage === 'PROTECT';
  getElement('activeStageNumber').textContent = protectActive ? '02' : '01';
  getElement('activeStageName').textContent = protectActive ? 'PROTECT' : 'UNDERSTAND';
  getElement('activeStageDescription').textContent = protectActive
    ? 'Purpose-based privacy protection'
    : 'Document identity and context';
  getElement('resultsEyebrow').textContent = protectActive ? 'Protection Result' : 'Report Result';
  getElement('resultsTitle').textContent = protectActive ? 'What MRJ protected' : 'What MRJ understood';
  getElement('anotherBtn').textContent = protectActive
    ? 'Review UNDERSTAND'
    : workflowMode === 'batch' ? 'Back to batch overview' : 'Analyze another report';
}

function renderProtectionResult(payload, options = {}) {
  const model = buildProtectionViewModel(payload, options);
  const batchView = workflowMode === 'batch' && Boolean(batchRun);
  prepareResultsWorkspace(batchView);
  activeJourneyStage = 'PROTECT';
  updateActiveStagePresentation();
  getElement('reportCard').hidden = true;
  getElement('protectionCard').hidden = false;
  getElement('protectionCard').className = `protection-card ${statusClass(model.state)}`;
  getElement('protectReportNumber').textContent = options.number
    ? `Report ${String(options.number).padStart(2, '0')}`
    : 'Report';
  getElement('protectStatus').className = `status-badge ${statusClass(model.state)}`;
  getElement('protectStatus').textContent = `${liveStatusSymbol(model.state)} ${label(model.state)}`;
  getElement('protectPolicy').textContent = `${model.policy} workflow`;
  getElement('protectionTitle').textContent = options.sourceName || 'Retained medical report';
  const transformedCount = model.categorySummary.reduce(
    (total, [, value]) => total + Number(value || 0),
    0,
  );
  getElement('protectStatusMessage').textContent = model.processing
    ? 'Protection in progress.'
    : model.failed ? 'Privacy Protection could not complete for this report.'
      : model.reviewRequired
        ? model.reviewMessage
        : model.zeroPhi ? 'No PHI detected. Clinical content remains available.'
          : `${transformedCount} automatic ${transformedCount === 1 ? 'transformation' : 'transformations'} applied.`;

  const resultAvailable = Boolean(payload);
  const compareTarget = resultAvailable && options.runId && options.documentId
    ? { runId: options.runId, documentId: options.documentId }
    : null;
  getElement('protectedEntitiesTitle').closest('section').hidden = !resultAvailable;
  getElement('analyticContextTitle').closest('section').hidden = !resultAvailable;
  getElement('protectedDocumentSection').hidden = !resultAvailable;
  renderRows(
    getElement('protectedEntitySummary'),
    model.summaryRows,
  );
  getElement('protectedEntitiesTitle').textContent = model.zeroPhi
      ? 'No additional de-identification required'
      : 'Protected identity information';
  getElement('protectionReview').hidden = !resultAvailable || !model.reviewRequired;
  getElement('protectionReviewMessage').textContent = model.reviewMessage;
  getElement('reviewProtectionBtn').textContent = model.unresolvedCount
    ? `Review ${model.unresolvedCount} ${model.unresolvedCount === 1 ? 'Signal' : 'Signals'}`
    : 'Review Protection';
  getElement('reviewProtectionBtn').disabled = !compareTarget
    || (!model.protectedText && !model.pdfOrigin);
  getElement('reviewProtectionBtn').onclick = showCompareView;
  renderRows(getElement('analyticContextSummary'), model.analyticContext);
  getElement('analyticContextSummary').hidden = !model.analyticContext.length;
  getElement('analyticContextEmpty').hidden = Boolean(model.analyticContext.length);
  getElement('protectedText').textContent = model.protectedText;
  getElement('protectedDocumentTitle').textContent = model.pdfOrigin
    ? `${model.protectedFilename}${model.artifact?.page_count ? ` · ${model.artifact.page_count} ${model.artifact.page_count === 1 ? 'page' : 'pages'}` : ''}`
    : 'Protected report text';
  resetCompareView(
    compareTarget,
    model.protectedText,
    model.pdfOrigin,
    model.artifact,
  );
  getElement('protectedViewBtn').onclick = showProtectedView;
  getElement('compareViewBtn').onclick = showCompareView;
  getElement('textViewBtn').onclick = showTextView;
  const displayWarnings = model.warnings.filter(
    warning => warning !== 'One or more privacy candidates require review.',
  );
  getElement('protectWarnings').classList.toggle('show', displayWarnings.length > 0);
  getElement('protectWarnings').textContent = displayWarnings.length
    ? `Please note: ${displayWarnings.join(' · ')}`
    : '';
  getElement('protectionError').hidden = !model.failed;
  getElement('protectionError').textContent = model.failed
    ? model.error || 'This report could not be protected. Other eligible reports continued.'
    : '';
  const nextStage = buildNextStagePresentation(batchView ? batchRun : null, model);
  getElement('nextStageSummary').textContent = nextStage.message;
  getElement('continueExtractBtn').textContent = nextStage.buttonLabel;
  getElement('continueExtractBtn').disabled = true;
  getElement('continueExtractBtn').setAttribute('aria-disabled', 'true');
  getElement('copyProtectedBtn').disabled = !model.protectedText;
  getElement('copyProtectedBtn').onclick = async () => {
    if (!model.protectedText) return;
    try {
      await globalThis.navigator.clipboard.writeText(model.protectedText);
      getElement('copyProtectedBtn').textContent = 'Copied';
      globalThis.setTimeout(() => { getElement('copyProtectedBtn').textContent = 'Copy protected text'; }, 1000);
    } catch (_) {
      getElement('copyProtectedBtn').textContent = 'Copy unavailable';
    }
  };
  getElement('results').classList.add('show');
  if (batchView) renderBatchRows();
  configureReportNavigation();
  updateJourneyRail(batchView ? batchRun : singleRun);
  if (options.scroll !== false) {
    getElement('protectionCard').focus({ preventScroll: true });
    const reducedMotion = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    getElement('protectionCard').scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' });
  }
}

// Exactly one card and one render model serve Single and selected Batch reports.
function renderReportResult(payload, options = {}) {
  resetCompareView();
  const model = buildReportViewModel(payload, options);
  const batchView = workflowMode === 'batch' && Boolean(batchRun);
  prepareResultsWorkspace(batchView);
  activeJourneyStage = 'UNDERSTAND';
  updateActiveStagePresentation();
  getElement('singleWorkspace').hidden = true;
  getElement('reportCard').hidden = false;
  getElement('protectionCard').hidden = true;
  getElement('reportCard').className = `report-card ${statusClass(model.state)}`;
  getElement('reportNumber').textContent = options.number ? `Report ${String(options.number).padStart(2, '0')}` : 'Report';
  getElement('resultFileName').textContent = model.filename;
  getElement('domainValue').textContent = model.domain;
  getElement('domainValue').hidden = model.failed || model.unknown;
  getElement('reportType').textContent = model.type;
  getElement('reportType').hidden = model.failed || model.unknown;
  getElement('reportModality').textContent = model.modality;
  getElement('confidenceValue').textContent = model.confidence;
  getElement('confidenceBand').textContent = model.confidenceBand;
  getElement('reportConfidence').hidden = model.failed;
  getElement('confidenceNote').textContent = model.confidenceNote;
  getElement('confidenceNote').hidden = !model.confidenceNote;
  getElement('resultStatus').className = `status-badge ${statusClass(model.state)}`;
  getElement('resultStatus').textContent = `${liveStatusSymbol(model.state)} ${label(model.state)}`;
  renderRows(getElement('reportMetadata'), model.metadata);
  getElement('reportMetadata').hidden = !model.metadata.length;
  getElement('reportReviewNote').hidden = !model.reviewNote;
  getElement('reportReviewNote').textContent = model.reviewNote;
  getElement('reportStructure').hidden = model.failed;
  renderList(getElement('sectionList'), model.structures, value => {
    const item = makeElement('span');
    item.className = 'structure-item';
    item.textContent = value;
    return item;
  }, 'No report sections were identified.');
  getElement('recognitionEvidence').hidden = model.failed;
  getElement('recognitionEvidence').removeAttribute('open');
  getElement('evidenceCount').textContent = `${model.explanations.length} ${model.explanations.length === 1 ? 'signal' : 'signals'} identified`;
  renderList(getElement('recognitionReasons'), model.explanations, value => {
    const item = makeElement('p');
    item.className = 'explanation-item';
    item.textContent = value;
    return item;
  }, 'Recognition explanation is unavailable.');
  getElement('warnings').classList.toggle('show', model.warnings.length > 0);
  getElement('warnings').textContent = model.warnings.length ? `Please note: ${model.warnings.join(' · ')}` : '';
  getElement('readinessMessage').textContent = model.readiness;
  const handoff = !batchView && workflowMode === 'single' ? model.handoff : null;
  getElement('singleProtectActions').hidden = !handoff;
  getElement('continueBtn').hidden = !handoff;
  getElement('continueBtn').onclick = () => beginProtectJourney();
  getElement('results').classList.add('show');
  configureReportNavigation();
  updateJourneyRail(batchView ? batchRun : singleRun, model.context);
  if (options.scroll !== false) {
    getElement('reportCard').focus({ preventScroll: true });
    const reducedMotion = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    getElement('reportCard').scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' });
  }
}

function renderFailedRunDocument(runDocument, scroll = true) {
  renderReportResult(null, {
    sourceName: runDocument.original_filename,
    number: runDocument.order + 1,
    error: runDocument.error,
    scroll,
  });
}

async function responsePayload(response, fallback) {
  let payload = {};
  try {
    payload = await response.json();
  } catch (_) {
    // The response had no JSON body.
  }
  if (!response.ok) throw Error(payload.detail || fallback);
  return payload;
}

async function analyzeSingle() {
  try {
    activeJourneyStage = 'UNDERSTAND';
    singleRun = null;
    getElement('analyzeBtn').disabled = true;
    getElement('status').textContent = 'Analyzing report…';
    getElement('status').classList.add('analyzing');
    let response;
    if (inputMode === 'text') {
      const text = getElement('textInput').value.trim();
      if (!text) throw Error('Paste medical report text before analysis.');
      response = await fetch('/api/v1/understanding/analyze-text', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) });
    } else {
      const file = singleSelectedFile || getElement('fileInput').files[0];
      if (!file) throw Error('Choose a supported report before analysis.');
      const form = new FormData();
      form.append('file', file);
      response = await fetch('/api/v1/understanding/analyze-file', { method: 'POST', body: form });
    }
    singlePayload = await responsePayload(response, 'MRJ could not understand this report.');
    renderReportResult(singlePayload, { sourceName: singlePayload.document_context?.document?.source_name });
    getElement('status').textContent = '';
  } catch (failure) {
    getElement('status').textContent = failure.message || 'MRJ could not understand this report.';
  } finally {
    getElement('analyzeBtn').disabled = false;
    getElement('status').classList.remove('analyzing');
  }
}

function addBatchFiles(fileList) {
  if (batchProcessing || batchRun) return;
  const incoming = Array.from(fileList);
  const remaining = MAX_BATCH_REPORTS - batchEntries.length;
  if (incoming.length > remaining) {
    getElement('batchStatus').textContent = `A batch can contain at most ${MAX_BATCH_REPORTS} reports. ${remaining} more can be added.`;
    return;
  }
  const signatures = new Set(batchEntries.map(entry => entry.signature));
  let duplicates = 0;
  incoming.forEach(file => {
    const signature = `${file.name.toLowerCase()}|${file.size}|${file.lastModified}`;
    if (signatures.has(signature)) {
      duplicates += 1;
      return;
    }
    signatures.add(signature);
    const extension = fileExtension(file.name);
    batchEntries.push({
      file,
      signature,
      extension,
      status: SUPPORTED_EXTENSIONS.has(extension) ? 'READY' : 'UNSUPPORTED',
      error: SUPPORTED_EXTENSIONS.has(extension) ? null : `.${extension || 'unknown'} is not supported`,
      serverDocumentId: null,
    });
  });
  getElement('batchStatus').textContent = duplicates ? `${duplicates} duplicate ${duplicates === 1 ? 'report was' : 'reports were'} not added.` : '';
  getElement('batchFileInput').value = '';
  renderPreQueue();
}

function removeBatchEntry(index) {
  if (batchProcessing || batchRun) return;
  batchEntries.splice(index, 1);
  renderPreQueue();
}

function statusClass(state) {
  if (state === 'PROCESSING') return 'processing';
  if (state === 'COMPLETE') return 'complete';
  if (state === 'NEEDS_REVIEW') return 'review';
  if (state === 'FAILED' || state === 'UNSUPPORTED' || state === 'BLOCKED') return 'failed';
  return '';
}

function renderPreQueue() {
  getElement('batchCount').textContent = `${batchEntries.length} / ${MAX_BATCH_REPORTS}`;
  getElement('batchPreQueue').replaceChildren();
  if (!batchEntries.length) {
    const empty = makeElement('li');
    empty.className = 'empty-state';
    empty.textContent = 'No reports selected yet.';
    getElement('batchPreQueue').append(empty);
  } else {
    batchEntries.forEach((entry, index) => {
      const row = makeElement('li');
      const number = makeElement('span');
      const filename = makeElement('span');
      const type = makeElement('span');
      const size = makeElement('span');
      const status = makeElement('span');
      const remove = makeElement('button');
      number.className = 'queue-index';
      number.textContent = String(index + 1).padStart(2, '0');
      filename.className = 'queue-file';
      filename.textContent = `${String(index + 1).padStart(2, '0')}  ${entry.file.name}`;
      type.className = 'queue-type';
      type.textContent = entry.extension.toUpperCase() || 'FILE';
      size.className = 'queue-size';
      size.textContent = formatBytes(entry.file.size);
      status.className = `status-badge ${statusClass(entry.status)}`;
      status.textContent = label(entry.status);
      remove.className = 'queue-remove';
      remove.type = 'button';
      remove.textContent = 'Remove';
      remove.setAttribute('aria-label', `Remove ${entry.file.name}`);
      remove.onclick = () => removeBatchEntry(index);
      row.append(number, filename, type, size, status, remove);
      getElement('batchPreQueue').append(row);
    });
  }
  getElement('analyzeBatchBtn').disabled = batchProcessing || !batchEntries.length || Boolean(batchRun);
  getElement('clearBatchBtn').disabled = batchProcessing || !batchEntries.length || Boolean(batchRun);
  getElement('analyzeBatchBtn').textContent = batchEntries.length ? `Analyze ${batchEntries.length} ${batchEntries.length === 1 ? 'Report' : 'Reports'} →` : 'Analyze Reports →';
}

function syncEntriesFromRun(run) {
  (run?.documents || []).forEach(runDocument => {
    const entry = batchEntries[runDocument.order];
    if (!entry) return;
    entry.serverDocumentId = runDocument.document_id;
    entry.status = runDocument.stage_status.UNDERSTAND.status;
    entry.error = runDocument.error;
  });
}

function batchTerminalCount() {
  return batchEntries.filter(entry => terminalState(entry.status)).length;
}

function updateBatchProgress(processed, total) {
  getElement('batchProgressBar').style.width = `${total ? (processed / total) * 100 : 0}%`;
  const active = batchEntries.findIndex(entry => entry.status === 'PROCESSING');
  getElement('batchProgressText').textContent = active >= 0
    ? `Analyzing report ${active + 1} of ${total}`
    : total ? `${processed} of ${total} processed` : 'Preparing batch';
  getElement('processingActivity').hidden = !batchProcessing;
  getElement('processingActivityText').textContent = active >= 0
    ? `Analyzing ${batchEntries[active].file.name}…`
    : processed === total && total ? 'Finalizing batch…' : 'Preparing reports…';
}

function liveStatusSymbol(state) {
  if (state === 'COMPLETE') return '✓';
  if (state === 'PROCESSING') return '●';
  if (['NEEDS_REVIEW', 'FAILED', 'UNSUPPORTED'].includes(state)) return '!';
  return '○';
}

function renderLiveBatchQueue(stage = 'UNDERSTAND') {
  const rows = batchEntries.map((entry, index) => {
    const runDocument = batchRun?.documents?.[index];
    const stageState = stage === 'PROTECT'
      ? runDocument?.stage_status?.PROTECT?.status || 'NOT_STARTED'
      : entry.status;
    const row = makeElement('li');
    const icon = makeElement('span');
    const filename = makeElement('b');
    const status = makeElement('span');
    icon.className = `live-icon ${statusClass(stageState)}`;
    icon.textContent = liveStatusSymbol(stageState);
    filename.textContent = entry.file.name;
    status.className = `status-badge ${statusClass(stageState)}`;
    status.textContent = label(stageState);
    row.append(icon, filename, status);
    return row;
  });
  getElement('batchLiveQueue').replaceChildren(...rows);
}

function batchDisplaySummary() {
  const serverSummary = batchRun?.summary || {};
  return {
    analyzed: batchTerminalCount(),
    recognized: serverSummary.recognized || 0,
    high_confidence: serverSummary.high_confidence || 0,
    needs_review: serverSummary.needs_review || 0,
    failed: batchEntries.filter(entry => entry.status === 'FAILED' || entry.status === 'UNSUPPORTED').length,
  };
}

function renderBatchDashboard() {
  const terminal = batchTerminalCount();
  const complete = batchEntries.length > 0 && terminal === batchEntries.length;
  getElement('batchSetup').hidden = batchProcessing || Boolean(batchRun);
  getElement('batchDashboard').hidden = !(batchProcessing || batchRun);
  getElement('batchSummaryEyebrow').textContent = complete ? 'Batch Complete' : 'Understanding Batch';
  getElement('batchSummaryTitle').textContent = complete ? `${batchEntries.length} reports processed` : 'Analyzing reports';
  updateBatchProgress(terminal, batchEntries.length);
  getElement('batchProgressText').hidden = complete;
  getElement('batchProgressBar').parentElement.hidden = complete;
  renderLiveBatchQueue();
  getElement('batchLiveQueue').hidden = complete;
  getElement('batchMetrics').hidden = !complete;
  if (complete) {
    const summary = batchDisplaySummary();
    const metrics = [['Analyzed', summary.analyzed], ['High Confidence', summary.high_confidence], ['Needs Review', summary.needs_review], ['Failed', summary.failed]];
    getElement('batchMetrics').replaceChildren(...metrics.map(([name, value]) => {
      const item = makeElement('div');
      const count = makeElement('strong');
      const title = makeElement('span');
      item.className = 'summary-metric';
      count.textContent = value;
      title.textContent = name;
      item.append(count, title);
      return item;
    }));
  }
  updateJourneyRail(batchRun);
}

function safelyRenderBatchState() {
  try {
    renderPreQueue();
    renderBatchDashboard();
  } catch (_) {
    // The JourneyRun and processing loop remain authoritative if presentation fails.
  }
}

async function analyzeBatch() {
  if (batchProcessing || !batchEntries.length || batchEntries.length > MAX_BATCH_REPORTS) return;
  activeJourneyStage = 'UNDERSTAND';
  batchProcessing = true;
  batchRun = null;
  selectedBatchDocumentId = null;
  batchSubmittedCount = 0;
  batchEntries.forEach(entry => {
    entry.status = 'WAITING';
    entry.error = null;
    entry.serverDocumentId = null;
  });
  getElement('results').classList.remove('show', 'batch-view');
  safelyRenderBatchState();
  try {
    const createResponse = await fetch('/api/v1/understanding/journey-runs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ mode: 'batch' }) });
    batchRun = await responsePayload(createResponse, 'MRJ could not create the batch.');
    safelyRenderBatchState();

    await processSequentialBatch(
      batchEntries,
      async (entry, index) => {
        entry.status = 'PROCESSING';
        safelyRenderBatchState();
        const form = new FormData();
        form.append('order', String(index));
        form.append('file', entry.file);
        batchSubmittedCount += 1;
        const response = await fetch(`/api/v1/understanding/journey-runs/${encodeURIComponent(batchRun.run_id)}/documents`, { method: 'POST', body: form });
        batchRun = await responsePayload(response, `MRJ could not process ${entry.file.name}.`);
        syncEntriesFromRun(batchRun);
      },
      () => safelyRenderBatchState(),
    );

    safelyRenderBatchState();
    renderBatchReportBrowser();
    const firstRunDocument = batchRun.documents[0];
    if (firstRunDocument) {
      try {
        selectBatchDocument(firstRunDocument.document_id, false);
      } catch (_) {
        // The complete run remains available even if the first detail view cannot render.
      }
    }
  } catch (failure) {
    if (!batchRun) {
      getElement('batchSetup').hidden = false;
      getElement('batchDashboard').hidden = true;
    }
    getElement('batchStatus').textContent = failure.message || 'MRJ could not process this batch.';
  } finally {
    batchProcessing = false;
    safelyRenderBatchState();
  }
}

function renderBatchReportBrowser() {
  if (!batchRun) return;
  prepareResultsWorkspace(true);
  renderBatchRows();
  getElement('batchHandoff').hidden = activeJourneyStage !== 'UNDERSTAND';
  const handoff = batchRun.handoff?.protect || {};
  getElement('batchProtectBtn').disabled = !handoff.available;
  getElement('batchProtectBtn').setAttribute('aria-disabled', String(!handoff.available));
  getElement('batchProtectBtn').textContent = 'Continue to PROTECT';
  getElement('batchProtectBtn').onclick = () => beginProtectJourney();
  getElement('batchHandoffNote').textContent = handoff.available
    ? `${handoff.eligible_count} ${handoff.eligible_count === 1 ? 'report is' : 'reports are'} ready for Privacy Protection.`
    : handoff.reason || 'No report is currently eligible for Privacy Protection.';
}

function renderBatchRows() {
  if (!batchRun) return;
  const rows = buildBatchReportRows(batchRun, activeJourneyStage).map(model => {
    const row = makeElement('div');
    const selection = makeElement('button');
    const number = makeElement('span');
    const reportCopy = makeElement('span');
    const filename = makeElement('b');
    const recognition = makeElement('small');
    const confidence = makeElement('span');
    const status = makeElement('span');
    row.className = `batch-result-row ${statusClass(model.state)}${model.documentId === selectedBatchDocumentId ? ' selected' : ''}`;
    row.setAttribute('role', 'listitem');
    selection.type = 'button';
    selection.className = 'report-select';
    selection.setAttribute('aria-label', `Review report ${model.order + 1}: ${model.filename}`);
    selection.setAttribute('aria-current', model.documentId === selectedBatchDocumentId ? 'true' : 'false');
    number.className = 'report-index';
    number.textContent = String(model.order + 1).padStart(2, '0');
    reportCopy.className = 'report-copy';
    filename.textContent = model.filename;
    recognition.textContent = model.recognition;
    reportCopy.append(filename, recognition);
    confidence.className = 'report-confidence';
    confidence.textContent = model.confidence;
    confidence.hidden = !model.confidence;
    status.className = `status-badge ${statusClass(model.state)}`;
    status.textContent = `${liveStatusSymbol(model.state)} ${label(model.state)}`;
    selection.append(number, reportCopy, confidence, status);
    selection.onclick = () => selectBatchDocument(model.documentId);
    row.append(selection);
    if (model.state === 'FAILED' && activeJourneyStage === 'UNDERSTAND') {
      const retry = makeElement('button');
      retry.type = 'button';
      retry.className = 'retry-report';
      retry.textContent = 'Retry Report';
      retry.onclick = interaction => {
        interaction.stopPropagation();
        retryBatchDocument(model.documentId);
      };
      row.append(retry);
    }
    return row;
  });
  getElement('batchResultList').replaceChildren(...rows);
}

function selectBatchDocument(documentId, scroll = true) {
  const runDocument = getRunDocumentById(batchRun, documentId);
  if (!runDocument) return;
  selectedBatchDocumentId = documentId;
  renderBatchRows();
  const position = batchRun.documents.indexOf(runDocument) + 1;
  const stage = activeJourneyStage;
  const result = getRunDocumentStageResult(batchRun, documentId, stage);
  if (stage === 'PROTECT') {
    renderProtectionResult(result, {
      runId: batchRun.run_id,
      documentId: runDocument.document_id,
      sourceName: runDocument.original_filename,
      sourceType: runDocument.source_type,
      state: runDocument.stage_status.PROTECT.status,
      number: position,
      error: runDocument.stage_errors?.PROTECT || runDocument.error,
      policyLabel: label(getElement('batchPolicySelect').value),
      scroll,
    });
  } else if (result) {
    renderReportResult(result, {
      sourceName: runDocument.original_filename,
      state: runDocument.stage_status.UNDERSTAND.status,
      number: position,
      scroll,
    });
  } else {
    renderFailedRunDocument(runDocument, scroll);
  }
}

function configureReportNavigation() {
  const batchView = workflowMode === 'batch' && Boolean(batchRun?.documents?.length);
  getElement('reportNavigation').hidden = !batchView;
  updateActiveStagePresentation();
  if (!batchView) return;
  const index = batchRun.documents.findIndex(runDocument => runDocument.document_id === selectedBatchDocumentId);
  const previousDocumentId = adjacentRunDocumentId(batchRun, selectedBatchDocumentId, -1);
  const nextDocumentId = adjacentRunDocumentId(batchRun, selectedBatchDocumentId, 1);
  getElement('reportCounter').textContent = `Report ${Math.max(index + 1, 1)} of ${batchRun.documents.length}`;
  getElement('previousReportBtn').disabled = !previousDocumentId;
  getElement('nextReportBtn').disabled = !nextDocumentId;
  getElement('previousReportBtn').onclick = () => {
    if (previousDocumentId) selectBatchDocument(previousDocumentId);
  };
  getElement('nextReportBtn').onclick = () => {
    if (nextDocumentId) selectBatchDocument(nextDocumentId);
  };
}

async function retryBatchDocument(documentId) {
  const runDocument = getRunDocumentById(batchRun, documentId);
  const entry = runDocument ? batchEntries[runDocument.order] : null;
  if (!runDocument || !entry || batchProcessing) return;
  batchProcessing = true;
  entry.status = 'PROCESSING';
  safelyRenderBatchState();
  try {
    const form = new FormData();
    form.append('file', entry.file);
    const response = await fetch(`/api/v1/understanding/journey-runs/${encodeURIComponent(batchRun.run_id)}/documents/${encodeURIComponent(documentId)}/retry`, { method: 'POST', body: form });
    batchRun = await responsePayload(response, `MRJ could not retry ${runDocument.original_filename}.`);
    syncEntriesFromRun(batchRun);
    safelyRenderBatchState();
    renderBatchReportBrowser();
    try {
      selectBatchDocument(documentId, false);
    } catch (_) {
      // A completed retry remains complete even if detail presentation fails.
    }
  } catch (failure) {
    entry.status = 'FAILED';
    entry.error = failure.message;
  } finally {
    batchProcessing = false;
    safelyRenderBatchState();
  }
}

function selectedPolicy() {
  return workflowMode === 'batch'
    ? getElement('batchPolicySelect').value
    : getElement('singlePolicySelect').value;
}

function selectedPolicyLabel() {
  const select = workflowMode === 'batch'
    ? getElement('batchPolicySelect')
    : getElement('singlePolicySelect');
  return select.options?.[select.selectedIndex]?.text || label(select.value);
}

function setLocalProtectStatus(run, documentId, state) {
  const runDocument = getRunDocumentById(run, documentId);
  if (!runDocument) return;
  runDocument.current_stage = 'PROTECT';
  runDocument.stage_status.PROTECT.status = state;
}

function renderProtectionBatchProgress(current, total) {
  const summary = batchRun?.protection_summary || {};
  const eligible = summary.eligible ?? total;
  const terminal = summary.terminal ?? 0;
  const complete = eligible > 0 && terminal === eligible;
  getElement('batchSetup').hidden = true;
  getElement('batchDashboard').hidden = false;
  getElement('batchSummaryEyebrow').textContent = complete ? 'Protection Complete' : 'Protecting Batch';
  getElement('batchSummaryTitle').textContent = complete
    ? `${terminal} ${terminal === 1 ? 'report' : 'reports'} processed`
    : `Protecting report ${Math.min(current, total)} of ${total}`;
  getElement('batchProgressBar').style.width = `${eligible ? (terminal / eligible) * 100 : 0}%`;
  getElement('batchProgressText').hidden = complete;
  getElement('batchProgressText').textContent = complete ? '' : `${terminal} of ${eligible} terminal`;
  getElement('batchProgressBar').parentElement.hidden = complete;
  getElement('processingActivity').hidden = !protectProcessing;
  getElement('processingActivityText').textContent = protectProcessing
    ? 'Applying the selected privacy workflow and preparing protected documents…'
    : 'Privacy Protection complete.';
  renderLiveBatchQueue('PROTECT');
  getElement('batchLiveQueue').hidden = complete;
  getElement('batchMetrics').hidden = !complete;
  if (complete) {
    const metrics = [
      ['Complete', summary.complete || 0],
      ['Needs Review', summary.needs_review || 0],
      ['Failed', summary.failed || 0],
      ['Blocked', summary.blocked || 0],
    ];
    getElement('batchMetrics').replaceChildren(...metrics.map(([name, value]) => {
      const item = makeElement('div');
      const count = makeElement('strong');
      const title = makeElement('span');
      item.className = 'summary-metric';
      count.textContent = value;
      title.textContent = name;
      item.append(count, title);
      return item;
    }));
  }
  updateJourneyRail(batchRun);
}

async function requestProtection(runId, policy, documentIds = null) {
  const body = { policy };
  if (documentIds) body.document_ids = documentIds;
  const response = await fetch(
    `/api/v1/understanding/journey-runs/${encodeURIComponent(runId)}/protect`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
  );
  return responsePayload(response, 'MRJ could not continue this journey through Privacy Protection.');
}

async function beginProtectJourney() {
  if (protectProcessing) return;
  const policy = selectedPolicy();
  const policyLabel = selectedPolicyLabel();
  protectProcessing = true;
  protectionSubmittedCount = 0;
  activeJourneyStage = 'PROTECT';
  updateActiveStagePresentation();
  try {
    if (workflowMode === 'single') {
      const runId = singlePayload?.journey?.run_id;
      if (!runId) throw Error('The retained Single Report journey is unavailable.');
      renderProtectionResult(null, {
        sourceName: singlePayload?.document_context?.document?.source_name,
        sourceType: singlePayload?.document_context?.document?.source_type,
        state: 'PROCESSING',
        policyLabel,
        scroll: false,
      });
      protectionSubmittedCount = 1;
      singleRun = await requestProtection(runId, policy);
      const runDocument = singleRun.documents[0];
      renderProtectionResult(runDocument?.stage_results?.PROTECT || null, {
        runId: singleRun.run_id,
        documentId: runDocument?.document_id,
        sourceName: runDocument?.original_filename,
        sourceType: runDocument?.source_type,
        state: runDocument?.stage_status?.PROTECT?.status || 'FAILED',
        number: 1,
        error: runDocument?.stage_errors?.PROTECT || runDocument?.error,
        policyLabel,
      });
      return;
    }

    const runId = batchRun?.run_id;
    const documentIds = protectionEligibleDocumentIds(batchRun);
    if (!runId || !documentIds.length) {
      throw Error(batchRun?.handoff?.protect?.reason || 'No retained report is eligible for Privacy Protection.');
    }
    activeJourneyStage = 'PROTECT';
    selectedBatchDocumentId = documentIds[0];
    renderBatchReportBrowser();
    for (let index = 0; index < documentIds.length; index += 1) {
      const documentId = documentIds[index];
      setLocalProtectStatus(batchRun, documentId, 'PROCESSING');
      protectionSubmittedCount += 1;
      renderProtectionBatchProgress(index + 1, documentIds.length);
      selectBatchDocument(documentId, false);
      try {
        batchRun = await requestProtection(runId, policy, [documentId]);
      } catch (failure) {
        setLocalProtectStatus(batchRun, documentId, 'FAILED');
        const runDocument = getRunDocumentById(batchRun, documentId);
        if (runDocument) {
          runDocument.stage_errors = runDocument.stage_errors || {};
          runDocument.stage_errors.PROTECT = failure.message;
        }
      }
      renderProtectionBatchProgress(index + 1, documentIds.length);
      renderBatchReportBrowser();
      selectBatchDocument(documentId, false);
    }
    const firstDocument = batchRun.documents[0];
    if (firstDocument) selectBatchDocument(firstDocument.document_id, false);
  } catch (failure) {
    if (workflowMode === 'single') {
      renderProtectionResult(null, {
        sourceName: singlePayload?.document_context?.document?.source_name,
        sourceType: singlePayload?.document_context?.document?.source_type,
        state: 'FAILED',
        error: failure.message,
        policyLabel,
      });
    } else {
      getElement('batchHandoffNote').textContent = failure.message;
    }
  } finally {
    protectProcessing = false;
    if (workflowMode === 'batch' && batchRun) {
      renderProtectionBatchProgress(
        batchRun.protection_summary?.terminal || 0,
        batchRun.protection_summary?.eligible || 0,
      );
    }
    updateJourneyRail(workflowMode === 'batch' ? batchRun : singleRun);
  }
}

function stageDisplay(run, stage, context = null) {
  const documents = run?.documents || [];
  if (!documents.length) {
    if (stage === 'UNDERSTAND') {
      const review = context?.processing_context?.document_review_required
        ?? context?.processing_context?.manual_review_required;
      if (context) return { label: review ? 'Needs Review' : 'Complete', state: review ? 'NEEDS_REVIEW' : 'COMPLETE' };
      return { label: 'Ready', state: 'NOT_STARTED' };
    }
    if (stage === 'PROTECT' && protectProcessing) return { label: 'Processing', state: 'PROCESSING' };
    return { label: 'Not Started', state: 'NOT_STARTED' };
  }
  const statuses = documents.map(runDocument => runDocument.stage_status?.[stage]?.status || 'NOT_STARTED');
  const terminal = statuses.filter(state => ['COMPLETE', 'NEEDS_REVIEW', 'FAILED', 'BLOCKED'].includes(state)).length;
  const processing = statuses.some(state => state === 'PROCESSING');
  const queued = statuses.some(state => state === 'QUEUED');
  const state = processing ? 'PROCESSING'
    : queued ? 'QUEUED'
    : statuses.every(value => value === 'COMPLETE') ? 'COMPLETE'
    : statuses.some(value => value === 'NEEDS_REVIEW') ? 'NEEDS_REVIEW'
    : statuses.some(value => value === 'FAILED') ? 'FAILED'
    : statuses.every(value => value === 'BLOCKED') ? 'BLOCKED'
    : 'NOT_STARTED';
  if (documents.length === 1) return { label: label(statuses[0]), state: statuses[0] };
  if (terminal || processing || queued) return { label: `${terminal} / ${documents.length}`, state };
  return { label: 'Not Started', state };
}

function updateJourneyRail(run = null, context = null) {
  JOURNEY_STAGES.forEach(stage => {
    const suffix = stage.charAt(0) + stage.slice(1).toLowerCase();
    const target = getElement(`rail${suffix}`);
    const stageNode = getElement(`stage${suffix}`);
    const pendingBatchRun = stage === 'UNDERSTAND'
      && workflowMode === 'batch'
      && batchProcessing
      && batchEntries.length
      && !(run?.documents?.length)
      ? {
          documents: batchEntries.map(entry => ({
            stage_status: {
              UNDERSTAND: {
                status: entry.status === 'WAITING' ? 'NOT_STARTED' : entry.status,
              },
            },
          })),
        }
      : run;
    const display = stageDisplay(pendingBatchRun, stage, context);
    target.textContent = display.label;
    stageNode.className = `journey-stage${stage === activeJourneyStage ? ' active' : ''} ${statusClass(display.state)}`.trim();
  });
}

function resetBatch() {
  if (batchProcessing || protectProcessing) return;
  resetCompareView();
  batchEntries = [];
  batchRun = null;
  selectedBatchDocumentId = null;
  batchSubmittedCount = 0;
  protectionSubmittedCount = 0;
  activeJourneyStage = 'UNDERSTAND';
  getElement('batchSetup').hidden = false;
  getElement('batchDashboard').hidden = true;
  getElement('batchStatus').textContent = '';
  getElement('results').classList.remove('show', 'batch-view');
  getElement('batchReportBrowser').hidden = true;
  renderPreQueue();
  updateActiveStagePresentation();
  updateJourneyRail();
  getElement('batchDropzone').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function showUnderstandStage() {
  activeJourneyStage = 'UNDERSTAND';
  updateActiveStagePresentation();
  if (workflowMode === 'batch' && batchRun?.documents?.length) {
    const documentId = selectedBatchDocumentId || batchRun.documents[0].document_id;
    renderBatchReportBrowser();
    selectBatchDocument(documentId);
  } else if (singlePayload) {
    renderReportResult(singlePayload, {
      sourceName: singlePayload.document_context?.document?.source_name,
    });
  }
}

function initializeUnderstandingWorkspace() {
  getElement('singleModeTab').onclick = () => setWorkflowMode('single');
  getElement('batchModeTab').onclick = () => setWorkflowMode('batch');
  getElement('fileTab').onclick = () => setInputMode('file');
  getElement('textTab').onclick = () => setInputMode('text');
  getElement('fileInput').onchange = interaction => setSingleFile(interaction.target.files[0]);
  getElement('fileMode').ondragover = interaction => {
    interaction.preventDefault();
    getElement('fileMode').classList.add('dragging');
  };
  getElement('fileMode').ondragleave = () => getElement('fileMode').classList.remove('dragging');
  getElement('fileMode').ondrop = interaction => {
    interaction.preventDefault();
    getElement('fileMode').classList.remove('dragging');
    setSingleFile(interaction.dataTransfer.files[0]);
  };
  getElement('fileMode').onkeydown = keyAction => {
    if (keyAction.key === 'Enter' || keyAction.key === ' ') {
      keyAction.preventDefault();
      getElement('fileInput').click();
    }
  };
  getElement('removeSingleFileBtn').onclick = interaction => {
    interaction.preventDefault();
    interaction.stopPropagation();
    getElement('fileInput').value = '';
    setSingleFile(null);
  };
  getElement('analyzeBtn').onclick = analyzeSingle;
  getElement('batchFileInput').onchange = interaction => addBatchFiles(interaction.target.files);
  getElement('batchDropzone').ondragover = interaction => {
    interaction.preventDefault();
    getElement('batchDropzone').classList.add('dragging');
  };
  getElement('batchDropzone').ondragleave = () => getElement('batchDropzone').classList.remove('dragging');
  getElement('batchDropzone').ondrop = interaction => {
    interaction.preventDefault();
    getElement('batchDropzone').classList.remove('dragging');
    addBatchFiles(interaction.dataTransfer.files);
  };
  getElement('batchDropzone').onkeydown = keyAction => {
    if (keyAction.key === 'Enter' || keyAction.key === ' ') {
      keyAction.preventDefault();
      getElement('batchFileInput').click();
    }
  };
  getElement('analyzeBatchBtn').onclick = analyzeBatch;
  getElement('clearBatchBtn').onclick = resetBatch;
  getElement('newBatchBtn').onclick = resetBatch;
  getElement('anotherBtn').onclick = () => {
    if (activeJourneyStage === 'PROTECT') {
      showUnderstandStage();
      return;
    }
    if (workflowMode === 'batch') {
      getElement('batchDashboard').scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      getElement('results').classList.remove('show');
      getElement('singleWorkspace').hidden = false;
      getElement('workspace').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  renderPreQueue();
  updateActiveStagePresentation();
  updateJourneyRail();
  setInputMode('file');
}

if (typeof globalThis.document !== 'undefined') initializeUnderstandingWorkspace();
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    activeWorkflowResult,
    adjacentRunDocumentId,
    buildBatchReportRows,
    buildCompareLines,
    buildNextStagePresentation,
    buildProtectionViewModel,
    buildReportViewModel,
    createBatchDataTrace,
    createProtectionDataTrace,
    getRunDocumentStageResult,
    getRunDocumentResult,
    processSequentialBatch,
    protectionEligibleDocumentIds,
    stageDisplay,
    terminalState,
  };
}
