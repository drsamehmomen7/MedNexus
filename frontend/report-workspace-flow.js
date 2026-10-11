/* Browser-side orchestration over the established Journey API, one report at a time. */
((root, factory) => {
  const flow = factory();
  if (typeof module === 'object' && module.exports) module.exports = flow;
  if (root) root.MRJReportFlow = flow;
})(typeof window !== 'undefined' ? window : null, () => {
  const api = '/api/v1/understanding';
  const finished = state => state === 'COMPLETE' || state === 'NEEDS_REVIEW';
  const path = value => encodeURIComponent(value);

  class ProcessingIssue extends Error {
    constructor(stage) {
      super('The report could not be prepared.');
      this.stage = stage;
    }
  }

  async function payload(response) {
    let value = null;
    try { value = await response.json(); } catch { /* No clinical details enter errors. */ }
    if (!response.ok || !value || typeof value !== 'object') throw new ProcessingIssue('report preparation');
    return value;
  }

  function documentFrom(run, documentId, order) {
    return (run.documents || []).find(item => documentId ? item.document_id === documentId : item.order === order);
  }

  function requireStage(run, documentId, order, stage) {
    const item = documentFrom(run, documentId, order);
    if (!item || !finished(item.stage_status?.[stage]?.status)) throw new ProcessingIssue(stage);
    return item;
  }

  async function prepareReport({ file, batchRunId = null, order = 0, fetchImpl, onUpdate = () => {} }) {
    const form = new FormData();
    form.append('file', file);
    let runId = batchRunId;
    let documentId = null;
    let run;
    if (batchRunId) {
      form.append('order', String(order));
      run = await payload(await fetchImpl(`${api}/journey-runs/${path(batchRunId)}/documents`,
        { method: 'POST', body: form, cache: 'no-store' }));
    } else {
      const understood = await payload(await fetchImpl(`${api}/analyze-file`,
        { method: 'POST', body: form, cache: 'no-store' }));
      runId = understood.journey?.run_id;
      documentId = understood.document_context?.document?.document_id;
      if (!runId || !documentId) throw new ProcessingIssue('upload');
      run = await payload(await fetchImpl(`${api}/journey-runs/${path(runId)}`, { cache: 'no-store' }));
    }
    let item = requireStage(run, documentId, order, 'UNDERSTAND');
    documentId = item.document_id;
    onUpdate({ stage: 'UNDERSTAND', runId, documentId, document: item });
    run = await payload(await fetchImpl(`${api}/journey-runs/${path(runId)}/protect`, {
      method: 'POST', cache: 'no-store', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ policy: 'mednexus_clinical', document_ids: [documentId] }),
    }));
    item = requireStage(run, documentId, order, 'PROTECT');
    onUpdate({ stage: 'PROTECT', runId, documentId, document: item });
    const documentPath = `${api}/journey-runs/${path(runId)}/documents/${path(documentId)}`;
    run = await payload(await fetchImpl(`${documentPath}/extract`, { method: 'POST', cache: 'no-store' }));
    item = requireStage(run, documentId, order, 'EXTRACT');
    onUpdate({ stage: 'EXTRACT', runId, documentId, document: item });
    run = await payload(await fetchImpl(`${documentPath}/standardize`, { method: 'POST', cache: 'no-store' }));
    item = requireStage(run, documentId, order, 'STANDARDIZE');
    onUpdate({ stage: 'STANDARDIZE', runId, documentId, document: item });
    return { runId, documentId, document: item };
  }

  return { prepareReport, ProcessingIssue };
});
