(() => {
  'use strict';

  const api = '/api/v1/understanding';
  const model = window.MRJReportModel;
  const flow = window.MRJReportFlow;
  const byId = id => document.getElementById(id);
  const statuses = { UPLOADING: 'Uploading', PROCESSING: 'Processing', READY: 'Ready',
    NEEDS_REVIEW: 'Needs review', REVIEWED: 'Reviewed', FAILED: 'Failed' };
  const entries = [];
  const supported = new Set(['pdf', 'docx', 'txt']);
  let selected = null;
  let working = false;
  let batchSerial = 0;
  let originalUrl = null;
  let originalToken = 0;
  let showCompletion = false;
  let majorConfirmationKey = null;
  let savingReview = false;
  let creatingCollection = false;
  let comparisonMode = false;
  const comparisonNames = { AGREEMENT: 'Agreement', MRJ_ONLY: 'MRJ only',
    MEDGEMMA_ONLY: 'MedGemma only', CONFLICT: 'Conflict',
    UNSUPPORTED: 'Unsupported', UNRESOLVED: 'Unresolved' };

  const escapeId = value => encodeURIComponent(value);
  const docPath = entry => `${api}/journey-runs/${escapeId(entry.runId)}/documents/${escapeId(entry.documentId)}`;
  const activeEntry = () => entries.find(entry => entry.key === selected) || null;
  const ownDocument = (payload, entry, order) => (payload.documents || []).find(item =>
    entry.documentId ? item.document_id === entry.documentId : item.order === order);

  async function json(response) {
    let payload = null;
    try { payload = await response.json(); } catch { /* A safe generic error is shown below. */ }
    if (!response.ok) throw new Error('The report could not be prepared.');
    if (!payload || typeof payload !== 'object') throw new Error('The report could not be prepared.');
    return payload;
  }

  async function postJson(path, body) {
    return json(await fetch(path, { method: 'POST', cache: 'no-store',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }));
  }

  function updateFromRun(entry, payload, order) {
    const item = ownDocument(payload, entry, order);
    if (!item) throw new Error('The report could not be found in its processing session.');
    entry.documentId = item.document_id;
    entry.document = item;
    return item;
  }

  function renderQueue() {
    const target = byId('report-queue-list');
    target.replaceChildren();
    const filtered = byId('needs-review-filter').checked
      ? entries.filter(entry => entry.status === 'NEEDS_REVIEW') : entries;
    filtered.forEach(entry => {
      const row = document.createElement('li');
      const button = document.createElement('button');
      const number = document.createElement('span');
      const icon = document.createElement('span');
      const copy = document.createElement('span');
      const name = document.createElement('strong');
      const status = document.createElement('span');
      number.className = 'queue-index';
      number.textContent = String(entries.indexOf(entry) + 1).padStart(2, '0');
      const modality = String(entry.record?.descriptor || '').toUpperCase();
      icon.className = 'queue-modality-icon';
      icon.textContent = modality.startsWith('MRI') ? '◉' : modality.startsWith('ULTRASOUND') || modality.startsWith('US ')
        ? '≋' : modality.includes('CT') ? '▣' : modality.includes('X-RAY') ? '✣' : '▤';
      icon.setAttribute('aria-hidden', 'true');
      copy.className = 'queue-copy';
      name.textContent = entry.record?.title || entry.name;
      status.className = 'queue-state';
      status.dataset.state = entry.status;
      status.textContent = statuses[entry.status];
      copy.append(name, status);
      button.type = 'button';
      button.setAttribute('aria-label', `Open ${entry.name}: ${statuses[entry.status]}`);
      button.setAttribute('aria-current', String(entry.key === selected));
      button.addEventListener('click', () => selectEntry(entry));
      button.append(number, icon, copy);
      row.append(button);
      target.append(row);
    });
    if (!filtered.length) {
      const empty = document.createElement('li');
      empty.className = 'product-muted';
      empty.textContent = 'No reports currently need review.';
      target.append(empty);
    }
    const count = kind => entries.filter(entry => entry.status === kind).length;
    const preparing = count('UPLOADING') + count('PROCESSING');
    byId('queue-count').textContent = `${entries.length} total`;
    byId('queue-summary').textContent = [
      `${entries.length} ${entries.length === 1 ? 'report' : 'reports'}`,
      count('READY') ? `${count('READY')} ready` : null,
      count('NEEDS_REVIEW') ? `${count('NEEDS_REVIEW')} need review` : null,
      preparing ? `${preparing} processing` : null,
      count('REVIEWED') ? `${count('REVIEWED')} reviewed` : null,
      count('FAILED') ? `${count('FAILED')} failed` : null,
    ].filter(Boolean).join(' · ');
    byId('queue-summary').hidden = !entries.length;
  }

  function renderFactList(targetId, sectionId, facts) {
    const target = byId(targetId);
    target.replaceChildren();
    byId(sectionId).hidden = !facts.length;
    facts.forEach(fact => {
      const row = document.createElement('li');
      const label = document.createElement('span');
      const button = document.createElement('button');
      label.textContent = fact.display_label || 'Clinical finding';
      row.append(label);
      if (Array.isArray(fact.evidence_anchors) && fact.evidence_anchors.length) {
        button.type = 'button';
        button.className = 'product-text-button';
        button.textContent = 'View evidence';
        button.setAttribute('aria-label', `View evidence for ${label.textContent}`);
        button.addEventListener('click', () => showEvidence(fact));
        row.append(button);
      }
      target.append(row);
    });
  }

  function renderMeasurements(rows) {
    const target = byId('record-measurements');
    target.replaceChildren();
    byId('measurements-section').hidden = !rows.length;
    rows.forEach(row => {
      const tr = document.createElement('tr');
      [row.label, row.value, row.context].forEach(value => {
        const td = document.createElement('td');
        td.textContent = value;
        tr.append(td);
      });
      target.append(tr);
    });
  }

  function renderMedGemmaMarkdown(raw) {
    const target = byId('medgemma-content');
    target.replaceChildren();
    let list = null;
    String(raw || '').split(/\r?\n/).forEach(line => {
      const value = line.trim();
      if (!value) { list = null; return; }
      const heading = value.match(/^(?:#{1,4}\s*)?\*\*(.+?):?\*\*:?$/) || value.match(/^#{1,4}\s+(.+)$/);
      if (heading) {
        const h = document.createElement('h4');
        h.textContent = heading[1].replace(/:$/, '');
        target.append(h); list = null; return;
      }
      const bullet = value.match(/^(?:[-*+]\s+|\d+[.)]\s+)(.*)$/);
      if (bullet) {
        if (!list) { list = document.createElement('ul'); target.append(list); }
        const item = document.createElement('li');
        item.textContent = bullet[1].replaceAll('**', '');
        list.append(item); return;
      }
      const paragraph = document.createElement('p');
      paragraph.textContent = value.replaceAll('**', '');
      target.append(paragraph); list = null;
    });
  }

  function renderComparison(entry) {
    const mode = comparisonMode;
    byId('comparison-mode-indicator').hidden = !mode;
    byId('native-evaluation-title').hidden = !mode;
    byId('medgemma-section').hidden = !mode;
    byId('comparison-section').hidden = !mode;
    if (!mode) return;
    const evaluation = entry.comparison || { status: 'PROCESSING', comparison: { status: 'NOT_AVAILABLE' } };
    const generationLimited = evaluation.failure_code === 'GENERATION_REPETITION_LIMIT' ||
      evaluation.output_tokens >= 2000;
    const status = generationLimited ? 'FAILED' : ['AVAILABLE', 'PROCESSING', 'FAILED', 'UNAVAILABLE'].includes(evaluation.status)
      ? evaluation.status : 'UNAVAILABLE';
    byId('medgemma-status').textContent = status[0] + status.slice(1).toLowerCase();
    byId('medgemma-status').dataset.state = status;
    byId('medgemma-elapsed').textContent = Number.isFinite(evaluation.elapsed_seconds)
      ? `MedGemma processing: ${evaluation.elapsed_seconds.toFixed(1)} s` : '';
    renderMedGemmaMarkdown(status === 'AVAILABLE' ? evaluation.raw_response : '');
    if (generationLimited) {
      const target = byId('medgemma-content');
      target.textContent = 'MedGemma generation became repetitive and was stopped for this report.';
      if (evaluation.raw_response) {
        const disclosure = document.createElement('details');
        const summary = document.createElement('summary');
        summary.textContent = 'Inspect incomplete raw MedGemma response';
        const raw = document.createElement('pre');
        raw.textContent = evaluation.raw_response;
        disclosure.append(summary, raw);
        target.append(disclosure);
      }
    }
    if (status !== 'AVAILABLE') {
      byId('comparison-unavailable').textContent = generationLimited
        ? 'Comparison not valid: MedGemma output incomplete.' : status === 'PROCESSING'
        ? 'MedGemma is processing. MRJ Native remains available.' : 'MedGemma result unavailable.';
      byId('comparison-counts').replaceChildren();
      byId('comparison-groups').replaceChildren();
      return;
    }
    const comparison = evaluation.comparison || {};
    byId('comparison-unavailable').textContent = comparison.status === 'MODEL_CONTENT_FAILURE'
      ? 'Model content failure: MedGemma did not extract findings present in the protected report.'
      : comparison.comparison_valid === false ? 'Comparison not valid: MedGemma output incomplete.' : '';
    const counts = byId('comparison-counts');
    counts.replaceChildren(...Object.entries(comparisonNames).map(([key, name]) => {
      const chip = document.createElement('span');
      chip.textContent = `${name}: ${comparison.counts?.[key] || 0}`;
      return chip;
    }));
    const groups = byId('comparison-groups');
    groups.replaceChildren();
    Object.entries(comparisonNames).forEach(([key, name]) => {
      const items = comparison.groups?.[key] || [];
      if (!items.length) return;
      const section = document.createElement('section');
      section.className = 'comparison-group';
      section.dataset.category = key;
      const title = document.createElement('h4'); title.textContent = `${name} (${items.length})`;
      section.append(title);
      items.forEach(item => {
        const row = document.createElement('div'); row.className = 'comparison-item';
        const native = document.createElement('p');
        native.textContent = item.mrj ? `MRJ Native: ${item.mrj}` : key === 'UNRESOLVED'
          ? 'MRJ correspondence uncertain' : 'Not identified by MRJ Native';
        const gemma = document.createElement('p');
        gemma.textContent = item.medgemma ? `MedGemma: ${item.medgemma}` : key === 'UNRESOLVED'
          ? 'MedGemma correspondence uncertain' : 'No matching supported MedGemma claim';
        row.append(native, gemma);
        if (item.reason) {
          const reason = document.createElement('p');
          reason.className = 'comparison-reason';
          reason.textContent = item.reason;
          row.append(reason);
        }
        section.append(row);
      });
      groups.append(section);
    });
  }

  async function pollComparison(entry) {
    if (!entry.runId || !entry.documentId || !comparisonMode) return;
    const path = `${api}/medgemma-comparison/evaluations/${escapeId(entry.runId)}/${escapeId(entry.documentId)}`;
    try {
      entry.comparison = await json(await fetch(path, { cache: 'no-store' }));
    } catch {
      entry.comparison = { status: 'UNAVAILABLE', comparison: { status: 'NOT_AVAILABLE' } };
    }
    if (activeEntry() === entry) renderRecord(entry);
    if (entry.comparison.status === 'PROCESSING') setTimeout(() => pollComparison(entry), 2500);
  }

  async function startComparison(entry) {
    if (!comparisonMode || !entry.record) return;
    entry.comparison = { status: 'PROCESSING', comparison: { status: 'NOT_AVAILABLE' } };
    if (activeEntry() === entry) renderRecord(entry);
    try {
      const path = `${api}/medgemma-comparison/evaluations/${escapeId(entry.runId)}/${escapeId(entry.documentId)}`;
      entry.comparison = await json(await fetch(path, { method: 'POST', cache: 'no-store' }));
      if (activeEntry() === entry) renderRecord(entry);
      if (entry.comparison.status === 'PROCESSING') setTimeout(() => pollComparison(entry), 2500);
    } catch {
      entry.comparison = { status: 'UNAVAILABLE', comparison: { status: 'NOT_AVAILABLE' } };
      if (activeEntry() === entry) renderRecord(entry);
    }
  }

  async function initializeComparison() {
    try {
      const config = await json(await fetch(`${api}/medgemma-comparison/config`, { cache: 'no-store' }));
      comparisonMode = config.enabled === true;
    } catch { comparisonMode = false; }
    if (comparisonMode) await loadRetainedComparisonRun();
    render();
  }

  async function loadRetainedComparisonRun() {
    const runId = new URLSearchParams(window.location.search).get('comparison_run');
    if (!/^[0-9a-f]{32}$/.test(runId || '') || entries.length) return;
    try {
      const listed = await json(await fetch(`${api}/medgemma-comparison/evaluations`, { cache: 'no-store' }));
      const matches = (listed.evaluations || []).filter(item => item.run_id === runId)
        .sort((left, right) => String(left.created_at).localeCompare(String(right.created_at))).slice(0, 20);
      for (const item of matches) {
        const path = `${api}/medgemma-comparison/evaluations/${escapeId(runId)}/${escapeId(item.document_id)}`;
        const evaluation = await json(await fetch(path, { cache: 'no-store' }));
        const document = evaluation.native_document;
        const record = model.projection(document);
        if (!record) continue;
        const name = record.title;
        const entry = { key: Symbol('retained-comparison'), file: null, uploadValid: false,
          name, status: record.needsReview ? 'NEEDS_REVIEW' : 'READY',
          runId, documentId: item.document_id, document, record, comparison: evaluation,
          retainedPreview: true };
        entries.push(entry);
      }
      if (entries.length) {
        selected = entries[0].key;
        setStatus('Retained Comparison Mode results · read-only · no extraction started.');
      }
    } catch {
      setStatus('Retained evaluation could not be loaded. No extraction was started.');
    }
  }

  function renderCompletion() {
    const progress = model.reviewProgress(entries);
    const complete = showCompletion && model.completionEligible(entries);
    byId('review-complete').hidden = !complete;
    if (!complete) return false;
    const failed = progress.failed > 0;
    byId('completion-eyebrow').textContent = 'Review session';
    byId('completion-title').textContent = 'Review complete';
    byId('completion-count').textContent = failed ? `${progress.reviewed} reviewed · ${progress.failed} failed`
      : `${progress.reviewed} of ${progress.total} ${progress.total === 1 ? 'report' : 'reports'} reviewed`;
    byId('completion-message').textContent = failed
      ? 'Available reports have been reviewed. Failed reports still need attention.'
      : 'All reports in this upload session have been reviewed.';
    byId('retry-failed').hidden = !failed;
    byId('analyze-reports').hidden = false;
    if (!creatingCollection) {
      const excluded = entries.length - progress.reviewed;
      byId('analyze-message').textContent = excluded
        ? `${excluded} unreviewed or failed ${excluded === 1 ? 'report is' : 'reports are'} excluded from collection analysis.` : '';
      byId('analyze-message').hidden = !excluded;
    }
    return true;
  }

  function renderRecord(entry) {
    const completed = renderCompletion();
    byId('record-pending').hidden = completed || Boolean(entry?.record);
    byId('record-ready').hidden = completed || !entry?.record;
    if (completed) return;
    const ready = Boolean(entry?.record);
    if (!ready) {
      const failed = entry?.status === 'FAILED';
      byId('pending-title').textContent = failed ? 'We couldn’t prepare this report'
        : entry ? entry.status === 'UPLOADING' ? 'Uploading report…' : 'Preparing clinical record…'
          : 'Choose a report';
      byId('pending-message').textContent = failed
        ? entry.uploadIssue || 'This report could not be prepared for review. Retry it or remove it from the queue.'
        : entry ? 'The report will appear here when it is ready for review.'
          : 'Select a report from the queue to review its clinical record.';
      byId('retry-report').hidden = !failed || !entry?.file || !entry.uploadValid || working;
      byId('remove-report').hidden = !failed;
      byId('processing-details').hidden = !failed;
      byId('processing-detail-text').textContent = failed && entry.failureStage
        ? 'Report preparation stopped before a clinical record was accepted.' : '';
      return;
    }
    const record = entry.record;
    byId('view-original').hidden = Boolean(entry.retainedPreview);
    byId('record-title').textContent = record.title;
    byId('record-descriptor').textContent = record.descriptor;
    byId('record-descriptor').hidden = !record.descriptor;
    byId('record-filename').textContent = record.filename;
    byId('record-summary').textContent = record.summary;
    byId('summary-section').hidden = !record.summary;
    byId('exam-coverage-section').hidden = !record.profile;
    if (record.profile) {
      const labels = { DOCUMENTED: 'Documented', NOT_DOCUMENTED: 'Not documented',
        LIMITED_OR_NOT_VISUALIZED: 'Limited / not visualized', NOT_APPLICABLE: 'Not applicable' };
      const coverageItem = item => {
        const row = document.createElement('li');
        row.dataset.coverage = item.coverage;
        const name = document.createElement('span');
        name.textContent = item.label;
        const status = document.createElement('span');
        status.textContent = labels[item.coverage] || 'Unknown';
        row.append(name, status);
        return row;
      };
      byId('exam-coverage-list').replaceChildren(...record.profile.coverage.map(coverageItem));
      byId('profile-title').textContent = record.profile.name;
      byId('profile-scope').textContent = `Exam scope: ${record.profile.scope.replaceAll('_', ' ').toLowerCase()}`;
      byId('profile-coverage-list').replaceChildren(...record.profile.coverage.flatMap(section => [
        coverageItem(section), ...(section.elements || []).map(element => {
          const row = coverageItem(element);
          row.classList.add('profile-element');
          return row;
        }),
      ]));
      byId('profile-provenance').textContent = `${record.profile.id} · version ${record.profile.version}. ` +
        record.profile.references.map(ref => `${ref.organization}: ${ref.title}`).join('; ');
    }
    renderFactList('record-findings', 'findings-section', record.groups.key);
    renderFactList('record-negatives', 'negative-section', record.groups.negative);
    renderFactList('record-assessments', 'assessment-section', record.groups.assessment || []);
    renderFactList('record-recommendations', 'recommendation-section', record.groups.recommendation || []);
    renderFactList('record-diagnostics', 'diagnostic-section', record.groups.diagnostic);
    renderFactList('record-secondary', 'secondary-section', record.groups.secondary.slice(0, 4));
    renderFactList('record-secondary-more', 'secondary-section', record.groups.secondary.slice(4));
    byId('secondary-section').hidden = !record.groups.secondary.length;
    byId('secondary-more').hidden = record.groups.secondary.length <= 4;
    renderMeasurements(record.measurements);
    const reviewSection = byId('review-section');
    reviewSection.hidden = !record.reviewAlerts.length;
    const issues = byId('record-review-issues');
    issues.replaceChildren(...record.reviewAlerts.map(alert => {
      const item = document.createElement('li');
      item.dataset.severity = alert.severity;
      if (alert.severity === 'major') {
        const badge = document.createElement('strong');
        badge.className = 'major-review-label';
        badge.textContent = 'Major review';
        item.append(badge);
      }
      const message = document.createElement('span');
      message.textContent = alert.message;
      item.append(message);
      return item;
    }));
    reviewSection.dataset.severity = record.reviewAlerts.some(alert => alert.severity === 'major') ? 'major' : 'review';
    renderComparison(entry);
    const state = record.reviewed ? 'REVIEWED' : record.needsReview ? 'NEEDS_REVIEW' : 'READY';
    byId('record-state').dataset.state = state;
    byId('record-state').textContent = statuses[state];
    const acceptance = model.acceptancePolicy(record, entries.length);
    byId('accept-record').disabled = record.reviewed || savingReview;
    byId('accept-record').hidden = Boolean(entry.retainedPreview);
    byId('accept-record').textContent = acceptance.label;
    byId('accept-record').parentElement.dataset.majorReview = String(acceptance.confirmMajor);
    byId('record-save-note').textContent = entry.retainedPreview
      ? 'Retained evaluation preview. This view cannot save a review decision.' : record.reviewed
      ? 'Review decision recorded for this session.'
      : 'Review the clinical record and source evidence. This decision applies to the current session.';
  }

  function render() {
    document.body.classList.toggle('has-reports', entries.length > 0);
    byId('report-empty').hidden = entries.length > 0;
    byId('report-work-area').hidden = entries.length === 0;
    byId('page-guidance').hidden = entries.length > 0;
    byId('session-eyebrow').textContent = entries.length ? 'Review session' : 'Report Workspace';
    byId('add-reports').disabled = working;
    renderQueue();
    if (entries.length) renderRecord(activeEntry());
  }

  function selectEntry(entry) {
    if (byId('evidence-dialog').open) byId('evidence-dialog').close();
    if (byId('profile-dialog').open) byId('profile-dialog').close();
    if (byId('original-dialog').open) byId('original-dialog').close();
    if (byId('major-review-dialog').open) byId('major-review-dialog').close();
    selected = entry.key;
    showCompletion = false;
    render();
    if (entry.record) byId('record-title').focus({ preventScroll: true });
  }

  function setStatus(message) { byId('workspace-status').textContent = message; }

  async function processEntry(entry, batchRunId, order) {
    entry.status = 'UPLOADING';
    entry.failureStage = null;
    entry.record = null;
    entry.runId = null;
    entry.documentId = null;
    render();
    try {
      const prepared = await flow.prepareReport({ file: entry.file, batchRunId, order, fetchImpl: fetch,
        onUpdate(update) {
          entry.runId = update.runId;
          entry.documentId = update.documentId;
          entry.document = update.document;
          entry.status = 'PROCESSING';
          render();
        },
      });
      entry.runId = prepared.runId;
      entry.documentId = prepared.documentId;
      entry.document = prepared.document;
      entry.record = model.projection(entry.document);
      if (!entry.record) throw new flow.ProcessingIssue('clinical record');
      entry.status = entry.record.needsReview ? 'NEEDS_REVIEW' : 'READY';
      startComparison(entry);
    } catch (error) {
      entry.status = 'FAILED';
      entry.failureStage = error instanceof flow.ProcessingIssue ? error.stage :
        entry.documentId ? 'report preparation' : 'upload';
    }
    if (showCompletion && (entry.status === 'READY' || entry.status === 'NEEDS_REVIEW')) {
      showCompletion = false;
      selected = entry.key;
    }
    if (model.completionEligible(entries)) showCompletion = true;
    render();
  }

  async function addFiles(fileList) {
    if (working) return;
    const files = Array.from(fileList || []);
    if (!files.length) return;
    if (files.length > 20) { setStatus('Choose up to 20 reports at a time.'); return; }
    const previousSessionComplete = showCompletion;
    working = true;
    showCompletion = false;
    setStatus(`${files.length} ${files.length === 1 ? 'report' : 'reports'} added. Preparing clinical review…`);
    const incoming = files.map(file => {
      const extension = file.name.split('.').pop().toLowerCase();
      const valid = supported.has(extension) && file.size > 0;
      const entry = { key: Symbol('report'), file, name: file.name, status: valid ? 'UPLOADING' : 'FAILED',
        uploadValid: valid, uploadIssue: valid ? null : supported.has(extension)
          ? 'This file is empty. Add a report with content.'
          : 'This file type cannot be processed. Add a PDF, DOCX, or TXT report.',
        failureStage: valid ? null : 'upload', runId: null, documentId: null, document: null, record: null };
      entries.push(entry);
      return entry;
    });
    if (previousSessionComplete || !selected || activeEntry()?.status === 'REVIEWED')
      selected = incoming[0].key;
    render();
    const valid = incoming.filter(entry => entry.status !== 'FAILED');
    let batchRunId = null;
    if (valid.length > 1) {
      try {
        batchSerial += 1;
        const batchName = `Report Workspace ${new Date().toISOString()} ${batchSerial}`;
        const run = await postJson(`${api}/journey-runs`, { mode: 'batch', batch_name: batchName });
        batchRunId = run.run_id;
        if (!batchRunId) throw new Error('The report session could not be created.');
      } catch {
        valid.forEach(entry => { entry.status = 'FAILED'; entry.failureStage = 'upload'; });
      }
    }
    for (const entry of valid) {
      if (entry.status === 'FAILED') break;
      await processEntry(entry, batchRunId, incoming.indexOf(entry));
    }
    working = false;
    if (model.completionEligible(entries)) showCompletion = true;
    render();
    const failures = incoming.filter(entry => entry.status === 'FAILED').length;
    setStatus(failures ? `${incoming.length - failures} prepared; ${failures} could not be prepared.`
      : `${incoming.length} ${incoming.length === 1 ? 'report is' : 'reports are'} ready for clinical review.`);
  }

  function showEvidence(fact) {
    const entry = activeEntry();
    if (!entry?.record) return;
    byId('evidence-fact').textContent = fact.display_label || 'Clinical finding';
    const reasons = Array.isArray(fact.review_reason) ? fact.review_reason :
      typeof fact.review_reason === 'string' ? [fact.review_reason] : [];
    const conflict = reasons.some(reason => ['CONFLICTING_SOURCE_ASSERTION', 'INTERNAL_SOURCE_CONFLICT',
      'INTERNAL_REPORT_CONFLICT'].includes(reason));
    byId('evidence-interpretation').textContent = conflict
      ? 'Conflicting source statements — interpretation requires review.'
      : fact.group === 'DIAGNOSTIC' ? 'Diagnostic consideration — not a confirmed finding.'
        : fact.assertion_state === 'ABSENT_NEGATED' ? 'Explicitly absent in the report.'
          : fact.assertion_state === 'PRESENT' ? 'Present finding.' : 'Requires clinical review.';
    byId('evidence-provenance').open = false;
    byId('evidence-provenance-text').textContent = 'Evidence is linked to the protected report used for clinical extraction.';
    const target = byId('evidence-context');
    target.replaceChildren();
    const source = entry.record.protectedText;
    const anchor = model.validatedEvidence(fact, source);
    if (anchor) {
      const start = Math.max(0, anchor.start_offset - 150);
      const end = Math.min(source.length, anchor.end_offset + 150);
      const marked = document.createElement('mark');
      marked.textContent = source.slice(anchor.start_offset, anchor.end_offset);
      target.append(document.createTextNode(source.slice(start, anchor.start_offset)), marked,
        document.createTextNode(source.slice(anchor.end_offset, end)));
      byId('evidence-message').textContent = 'Highlighted text is an exact match in the protected report.';
    } else {
      const context = (fact.evidence_anchors || []).find(item => Number.isInteger(item.start_offset) &&
        item.start_offset >= 0 && item.start_offset < source.length);
      target.textContent = context ? source.slice(Math.max(0, context.start_offset - 150),
        Math.min(source.length, context.start_offset + 150)) :
        'Exact protected source context is unavailable for this finding.';
      byId('evidence-message').textContent = 'An exact evidence match could not be verified, so no text is highlighted.';
    }
    byId('evidence-dialog').showModal();
  }

  function clearOriginal() {
    originalToken += 1;
    byId('original-pdf').src = 'about:blank';
    byId('original-pdf').hidden = true;
    byId('original-text').textContent = '';
    byId('original-text').hidden = true;
    byId('original-record-identity').textContent = '';
    byId('original-record-summary').textContent = '';
    byId('original-record-findings').replaceChildren();
    if (originalUrl) URL.revokeObjectURL(originalUrl);
    originalUrl = null;
  }

  async function showOriginal() {
    const entry = activeEntry();
    if (!entry?.record) return;
    if (byId('evidence-dialog').open) byId('evidence-dialog').close();
    clearOriginal();
    const token = ++originalToken;
    byId('original-record-identity').textContent = entry.record.title;
    byId('original-record-summary').textContent = entry.record.summary;
    byId('original-record-findings').replaceChildren(...entry.record.groups.key.map(fact => {
      const item = document.createElement('li');
      item.textContent = fact.display_label || 'Clinical finding';
      return item;
    }));
    byId('original-status').textContent = 'Loading the original report…';
    byId('original-dialog').showModal();
    try {
      if (entry.document?.source_type?.toLowerCase() === 'pdf') {
        const response = await fetch(`${docPath(entry)}/compare-artifact`, { method: 'POST', cache: 'no-store' });
        if (!response.ok) throw new Error('Original report unavailable.');
        const source = await response.blob();
        if (token !== originalToken || !byId('original-dialog').open || activeEntry() !== entry) return;
        originalUrl = URL.createObjectURL(source);
        byId('original-pdf').src = originalUrl;
        byId('original-pdf').hidden = false;
      } else {
        const response = await fetch(`${docPath(entry)}/compare-source`, { method: 'POST', cache: 'no-store' });
        const payload = await json(response);
        if (token !== originalToken || !byId('original-dialog').open || activeEntry() !== entry) return;
        byId('original-text').textContent = payload.source_text || '';
        byId('original-text').hidden = false;
      }
      byId('original-status').textContent = 'Original report shown for this review only.';
    } catch {
      if (token === originalToken && byId('original-dialog').open)
        byId('original-status').textContent = 'The original report is unavailable. The protected evidence remains available.';
    }
  }

  async function saveReviewDecision(majorReviewAcknowledged = false) {
    const entry = activeEntry();
    if (!entry?.record || entry.record.reviewed || savingReview) return;
    savingReview = true;
    byId('accept-record').disabled = true;
    setStatus('Saving your review decision…');
    try {
      const payload = await postJson(`${docPath(entry)}/accept`,
        { major_review_acknowledged: majorReviewAcknowledged });
      const accepted = ownDocument(payload, entry, entry.document.order);
      if (accepted?.review_status !== 'REVIEWED' || !accepted.durably_reviewed ||
          !accepted.reviewed_record_id || !Number.isInteger(accepted.reviewed_record_version))
        throw new Error('Review decision was not saved.');
      updateFromRun(entry, payload, entry.document.order);
      entry.record = model.projection(entry.document);
      entry.status = 'REVIEWED';
      entry.file = null;
      setStatus('Reviewed clinical record saved.');
      const next = model.nextReviewEntry(entries);
      if (next) selectEntry(next);
      else {
        showCompletion = model.completionEligible(entries);
        render();
        if (showCompletion) byId('completion-title').focus({ preventScroll: true });
      }
    } catch {
      byId('accept-record').disabled = false;
      setStatus('We couldn’t save this reviewed record. Please try again.');
    } finally {
      savingReview = false;
      render();
    }
  }

  function acceptRecord() {
    const entry = activeEntry();
    if (!entry?.record || entry.record.reviewed || savingReview) return;
    if (model.acceptancePolicy(entry.record, entries.length).confirmMajor) {
      majorConfirmationKey = entry.key;
      byId('major-review-dialog').showModal();
      return;
    }
    saveReviewDecision();
  }

  byId('add-reports').addEventListener('click', () => byId('report-files').click());
  byId('empty-add-reports').addEventListener('click', () => byId('report-files').click());
  byId('report-files').addEventListener('change', event => {
    addFiles(event.target.files);
    event.target.value = '';
  });
  byId('needs-review-filter').addEventListener('change', () => {
    if (byId('needs-review-filter').checked && activeEntry()?.status !== 'NEEDS_REVIEW') {
      const next = entries.find(entry => entry.status === 'NEEDS_REVIEW');
      if (next) { selectEntry(next); return; }
    }
    renderQueue();
  });
  byId('retry-report').addEventListener('click', async () => {
    const entry = activeEntry();
    if (!entry?.file || working) return;
    working = true;
    render();
    await processEntry(entry, null, 0);
    working = false;
    render();
    setStatus(entry.status === 'FAILED' ? 'Retry failed. You can add a corrected file.' : 'Report is ready for clinical review.');
  });
  byId('remove-report').addEventListener('click', () => {
    const entry = activeEntry();
    if (!entry || entry.status !== 'FAILED') return;
    entries.splice(entries.indexOf(entry), 1);
    selected = entries[0]?.key || null;
    showCompletion = model.completionEligible(entries);
    render();
    setStatus('Failed report removed from this queue.');
  });
  byId('review-again').addEventListener('click', () => {
    const next = entries.find(entry => entry.status === 'READY' || entry.status === 'NEEDS_REVIEW') ||
      entries.find(entry => entry.status === 'PROCESSING' || entry.status === 'UPLOADING') || entries[0];
    if (next) selectEntry(next);
  });
  byId('retry-failed').addEventListener('click', () => {
    const failed = entries.find(entry => entry.status === 'FAILED');
    if (failed) selectEntry(failed);
  });
  byId('back-to-reports').addEventListener('click', () => window.location.assign('/reports'));
  byId('analyze-reports').addEventListener('click', async () => {
    if (creatingCollection) return;
    const members = model.reviewedCollectionMembers(entries);
    const message = byId('analyze-message');
    const name = byId('collection-name').value.trim();
    if (!members.length || !name) {
      message.textContent = !members.length ? 'Accept at least one reviewed report first.' : 'Enter a collection name.';
      message.hidden = false;
      return;
    }
    creatingCollection = true;
    byId('analyze-reports').disabled = true;
    message.textContent = `Creating a collection from ${members.length} accepted ${members.length === 1 ? 'report' : 'reports'}…`;
    message.hidden = false;
    try {
      const result = await postJson(`${api}/reviewed-collections`,
        { name, creation_method: 'REVIEW_SESSION', members });
      if (!/^[0-9a-f]{32}$/.test(result.collection_id || '')) throw new Error('Collection unavailable');
      window.location.assign(`/collections#${result.collection_id}`);
    } catch {
      creatingCollection = false;
      byId('analyze-reports').disabled = false;
      message.textContent = 'The reviewed collection could not be created. Please try again.';
      message.hidden = false;
    }
  });
  byId('accept-record').addEventListener('click', acceptRecord);
  byId('cancel-major-acceptance').addEventListener('click', () => byId('major-review-dialog').close());
  byId('confirm-major-acceptance').addEventListener('click', () => {
    const entry = activeEntry();
    if (!entry || entry.key !== majorConfirmationKey || !entry.record || entry.record.reviewed) return;
    byId('major-review-dialog').close();
    saveReviewDecision(true);
  });
  byId('major-review-dialog').addEventListener('close', () => { majorConfirmationKey = null; });
  byId('view-original').addEventListener('click', showOriginal);
  byId('view-profile-details').addEventListener('click', () => {
    if (activeEntry()?.record?.profile) byId('profile-dialog').showModal();
  });
  byId('evidence-original').addEventListener('click', showOriginal);
  document.querySelectorAll('[data-close]').forEach(button => button.addEventListener('click', () =>
    byId(button.dataset.close).close()));
  byId('original-dialog').addEventListener('close', clearOriginal);
  const drop = byId('report-drop-zone');
  drop.addEventListener('dragover', event => { event.preventDefault(); drop.classList.add('dragging'); });
  drop.addEventListener('dragleave', () => drop.classList.remove('dragging'));
  drop.addEventListener('drop', event => {
    event.preventDefault();
    drop.classList.remove('dragging');
    addFiles(event.dataTransfer.files);
  });
  render();
  initializeComparison();
})();
