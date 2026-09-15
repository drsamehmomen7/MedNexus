const getElement = id => globalThis.document.getElementById(id);
const makeElement = tag => globalThis.document.createElement(tag);

const MAX_BATCH_REPORTS = 10;
const SUPPORTED_EXTENSIONS = new Set(['txt', 'docx', 'pdf']);
const TERMINAL_STATES = new Set(['COMPLETE', 'NEEDS_REVIEW', 'FAILED']);
const JOURNEY_STAGES = ['UNDERSTAND', 'PROTECT', 'EXTRACT', 'STANDARDIZE', 'ANALYZE', 'VISUALIZE', 'INDICATORS'];

let inputMode = 'file';
let workflowMode = 'single';
let singlePayload = null;
let singleSelectedFile = null;
let batchEntries = [];
let batchRun = null;
let selectedBatchDocumentId = null;
let batchProcessing = false;
let batchSubmittedCount = 0;

const LABELS = {
  UNKNOWN: 'Not determined', NEEDS_REVIEW: 'Needs Review', NOT_STARTED: 'Not Started',
  PROCESSING: 'Analyzing', OTHER: 'Other / Requires Review',
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

function label(value) {
  const key = String(value || 'UNKNOWN');
  return LABELS[key] || key.toLowerCase().replaceAll('_', ' ').replace(/\b\w/g, character => character.toUpperCase());
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
  return getRunDocumentById(run, documentId)?.stage_results?.UNDERSTAND || null;
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

function buildBatchReportRows(run) {
  return (run?.documents || []).map(runDocument => {
    const result = runDocument.stage_results?.UNDERSTAND || null;
    const state = runDocument.stage_status?.UNDERSTAND?.status || 'WAITING';
    const model = buildReportViewModel(result, { state });
    return {
      documentId: runDocument.document_id,
      order: runDocument.order,
      filename: runDocument.original_filename,
      recognition: result ? [model.modality, model.bodyRegion].filter(Boolean).join(' · ') : 'No result',
      confidence: model.confidence,
      confidenceBand: model.confidenceBand,
      state, result,
      error: runDocument.error || null,
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
  if (batchProcessing) return;
  workflowMode = nextMode;
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
  updateJourneyRail(singleActive ? null : batchRun, singleActive ? singlePayload?.document_context : null);
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
      : review ? 'Manual review required before continuing.'
      : processing.protect_ready ? 'Ready for Privacy Protection.'
      : 'Privacy Protection is not ready for this report.',
    handoff: !review && processing.protect_ready ? payload?.journey?.continue_to_protect : null,
    context,
  };
}

function prepareResultsWorkspace(batchView) {
  getElement('results').classList.toggle('batch-view', batchView);
  getElement('batchReportBrowser').hidden = !batchView;
  getElement('reportNavigation').hidden = !batchView;
}

// Exactly one card and one render model serve Single and selected Batch reports.
function renderReportResult(payload, options = {}) {
  const model = buildReportViewModel(payload, options);
  const batchView = workflowMode === 'batch' && Boolean(batchRun);
  prepareResultsWorkspace(batchView);
  getElement('singleWorkspace').hidden = true;
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
  getElement('continueBtn').hidden = !handoff;
  getElement('continueBtn').onclick = () => {
    if (handoff) globalThis.location.assign(handoff);
  };
  getElement('results').classList.add('show');
  configureReportNavigation();
  updateJourneyRail(batchView ? batchRun : null, model.context);
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
  if (state === 'FAILED' || state === 'UNSUPPORTED') return 'failed';
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

function renderLiveBatchQueue() {
  const rows = batchEntries.map((entry, index) => {
    const row = makeElement('li');
    const icon = makeElement('span');
    const filename = makeElement('b');
    const status = makeElement('span');
    icon.className = `live-icon ${statusClass(entry.status)}`;
    icon.textContent = liveStatusSymbol(entry.status);
    filename.textContent = entry.file.name;
    status.className = `status-badge ${statusClass(entry.status)}`;
    status.textContent = label(entry.status);
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
  const handoff = batchRun.handoff?.protect || {};
  getElement('batchProtectBtn').disabled = !handoff.available;
  getElement('batchProtectBtn').setAttribute('aria-disabled', String(!handoff.available));
  getElement('batchHandoffNote').textContent = handoff.available ? 'This batch is ready for Privacy Protection.' : 'Batch privacy processing is not yet enabled.';
}

function renderBatchRows() {
  if (!batchRun) return;
  const rows = buildBatchReportRows(batchRun).map(model => {
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
    status.className = `status-badge ${statusClass(model.state)}`;
    status.textContent = `${liveStatusSymbol(model.state)} ${label(model.state)}`;
    selection.append(number, reportCopy, confidence, status);
    selection.onclick = () => selectBatchDocument(model.documentId);
    row.append(selection);
    if (model.state === 'FAILED') {
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
  const result = getRunDocumentResult(batchRun, documentId);
  if (result) {
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
  getElement('anotherBtn').textContent = batchView ? 'Back to batch overview' : 'Analyze another report';
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

function updateJourneyRail(run = null, context = null) {
  const batchView = workflowMode === 'batch';
  const total = batchView ? Math.max(batchEntries.length, run?.summary?.total || 0) : 0;
  const processed = Math.max(batchTerminalCount(), run?.summary?.analyzed || 0);
  const review = context?.processing_context?.document_review_required ?? context?.processing_context?.manual_review_required;
  getElement('railUnderstand').textContent = batchView
    ? total ? `${processed} / ${total}` : 'Ready'
    : context ? review ? 'Needs Review' : 'Complete' : 'Ready';
  JOURNEY_STAGES.slice(1).forEach(stage => {
    const target = getElement(`rail${stage.charAt(0)}${stage.slice(1).toLowerCase()}`);
    if (target) target.textContent = 'Not Started';
  });
}

function resetBatch() {
  if (batchProcessing) return;
  batchEntries = [];
  batchRun = null;
  selectedBatchDocumentId = null;
  batchSubmittedCount = 0;
  getElement('batchSetup').hidden = false;
  getElement('batchDashboard').hidden = true;
  getElement('batchStatus').textContent = '';
  getElement('results').classList.remove('show', 'batch-view');
  getElement('batchReportBrowser').hidden = true;
  renderPreQueue();
  updateJourneyRail();
  getElement('batchDropzone').scrollIntoView({ behavior: 'smooth', block: 'center' });
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
    if (workflowMode === 'batch') {
      getElement('batchDashboard').scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      getElement('results').classList.remove('show');
      getElement('singleWorkspace').hidden = false;
      getElement('workspace').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  renderPreQueue();
  updateJourneyRail();
  setInputMode('file');
}

if (typeof globalThis.document !== 'undefined') initializeUnderstandingWorkspace();
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    activeWorkflowResult,
    adjacentRunDocumentId,
    buildBatchReportRows,
    buildReportViewModel,
    createBatchDataTrace,
    getRunDocumentResult,
    processSequentialBatch,
    terminalState,
  };
}
