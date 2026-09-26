// Lightweight DOM contract, not a browser/layout simulator. Uses the real page IDs
// and executes the production renderer/navigation with supplied API responses.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

class Element {
  constructor(tag = 'div') {
    this.tagName = tag;
    this.children = [];
    this.attributes = {};
    this.className = '';
    this.hidden = false;
    this.disabled = false;
    this.style = {};
    this.value = '';
    this.files = [];
    this.classList = {
      toggle: (name, force) => {
        const classes = new Set(this.className.split(' ').filter(Boolean));
        const add = force === undefined ? !classes.has(name) : force;
        if (add) classes.add(name); else classes.delete(name);
        this.className = [...classes].join(' ');
      },
      add: (...names) => names.forEach(name => this.classList.toggle(name, true)),
      remove: (...names) => names.forEach(name => this.classList.toggle(name, false)),
      contains: name => this.className.split(' ').includes(name),
    };
  }
  set textContent(value) { this.children = []; this.text = String(value); }
  get textContent() { return (this.text || '') + this.children.map(child => child.textContent).join(''); }
  append(...nodes) { nodes.forEach(node => { node.parentElement = this; this.children.push(node); }); }
  replaceChildren(...nodes) { this.children = []; this.text = ''; this.append(...nodes); }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  removeAttribute(name) { delete this.attributes[name]; }
  closest() { return this.parentElement; }
  scrollIntoView() {}
  focus() { this.focused = true; }
  click() { if (!this.disabled && !this.hidden) return this.onclick?.(); }
}

async function verifyReportCards(input) {
  const root = path.resolve(__dirname, '../..');
  const html = fs.readFileSync(path.join(root, 'frontend/understanding.html'), 'utf8');
  const source = fs.readFileSync(path.join(root, 'frontend/understanding.js'), 'utf8');
  const nodes = new Map();
  for (const match of html.matchAll(/<([a-z][a-z0-9]*)\b([^>]*\bid="([^"]+)"[^>]*)>/gi)) {
    assert(!nodes.has(match[3]), `duplicate page ID: ${match[3]}`);
    const node = new Element(match[1]);
    node.hidden = /\bhidden\b/.test(match[2]);
    node.className = match[2].match(/class="([^"]+)"/)?.[1] || '';
    node.parentElement = new Element();
    nodes.set(match[3], node);
  }
  const read = id => { assert(nodes.has(id), `renderer references missing page ID ${id}`); return nodes.get(id); };
  const navigation = [];
  const artifactRequests = [];
  const context = vm.createContext({
    document: { getElementById: read, createElement: tag => new Element(tag) },
    location: { assign: url => navigation.push(url) },
    fetch: async (url, options = {}) => {
      artifactRequests.push({url, method: options.method || 'GET'});
      return {
        ok: true,
        blob: async () => ({type: 'application/pdf', endpoint: url}),
        json: async () => ({}),
      };
    },
    URL: {
      createObjectURL: blob => `blob:${blob.endpoint}`,
      revokeObjectURL: () => {},
    },
    input,
  });
  vm.runInContext(source, context);
  const run = script => vm.runInContext(script, context);
  const snapshot = () => ({
    filename: read('resultFileName').textContent,
    modality: read('reportModality').textContent,
    domain: read('domainValue').textContent,
    type: read('reportType').textContent,
    metadata: read('reportMetadata').textContent,
    structures: read('sectionList').textContent,
    evidence: read('recognitionReasons').textContent,
    confidence: read('confidenceValue').textContent,
    status: read('resultStatus').textContent,
  });
  assert.equal((html.match(/id="reportCard"/g) || []).length, 1);
  for (const forbidden of ['technical-details', 'machineDetails', 'Active report summary', 'identityFacts']) {
    assert(!html.includes(forbidden), forbidden);
  }

  run('singlePayload = input.single; renderReportResult(singlePayload, {scroll:false});');
  const single = snapshot();
  assert.equal(read('singleWorkspace').hidden, true);
  assert.equal(read('batchReportBrowser').hidden, true);
  assert(!('open' in read('recognitionEvidence').attributes));
  const handoff = run('buildReportViewModel(singlePayload).handoff');
  assert.equal(read('continueBtn').hidden, !handoff);
  if (handoff) assert.equal(typeof read('continueBtn').onclick, 'function');
  assert.equal(navigation.length, 0, 'Single handoff must remain inside the Journey workspace');

  run(`workflowMode = 'batch'; batchRun = input.run;
    batchEntries = batchRun.documents.map(item => ({file:{name:item.original_filename}, status:item.stage_status.UNDERSTAND.status}));
    renderBatchReportBrowser(); renderBatchDashboard();`);
  const before = JSON.stringify(input.run);
  const cardSnapshots = [];
  const count = input.run.documents.length;
  assert.equal(read('batchResultList').children.length, count);
  assert.equal(read('batchMetrics').children.length, 4);
  for (let index = 0; index < count; index += 1) {
    // Execute the actual navigator click handler, not just a model lookup.
    read('batchResultList').children[index].children[0].click();
    const current = snapshot();
    const expected = input.run.documents[index];
    assert.equal(current.filename, expected.original_filename);
    assert.equal(read('continueBtn').hidden, true);
    assert(!('open' in read('recognitionEvidence').attributes));
    assert(read('reportMetadata').children.length <= 4); // Plus 3 identity fields.
    assert.equal(read('reportNumber').textContent, `Report ${String(index + 1).padStart(2, '0')}`);
    assert.equal(read('reportCounter').textContent, `Report ${index + 1} of ${count}`);
    assert.equal(read('batchResultList').children.filter(row => row.classList.contains('selected')).length, 1);
    assert(!/NEEDS_REVIEW|NOT_STARTED|RADIOLOGY_REPORT|WITH_CONTRAST/.test(Object.values(current).join(' ')));
    cardSnapshots.push(current);
    read('recognitionEvidence').setAttribute('open', '');
  }
  for (let index = count - 2; index >= 0; index -= 1) {
    read('previousReportBtn').click();
    assert.deepEqual(snapshot(), cardSnapshots[index]);
  }
  assert.equal(read('previousReportBtn').disabled, true);
  for (let index = 1; index < count; index += 1) {
    read('nextReportBtn').click();
    assert.deepEqual(snapshot(), cardSnapshots[index]);
  }
  assert.equal(read('nextReportBtn').disabled, true);
  assert.equal(read('batchProtectBtn').disabled, !Boolean(input.run.handoff?.protect?.available));
  assert.equal(typeof read('batchProtectBtn').onclick, 'function');
  read('continueBtn').click();
  assert.equal(navigation.length, 0, 'Batch must never silently hand off a single report');
  assert.equal(JSON.stringify(input.run), before, 'rendering must not mutate retained results');

  run("setWorkflowMode('single')");
  assert.deepEqual(snapshot(), single);
  read('anotherBtn').click();
  assert.equal(read('singleWorkspace').hidden, false);
  run("setInputMode('text')");
  assert.equal(read('fileMode').hidden, true);
  assert.equal(read('selectedFileCard').hidden, true);
  assert.equal(read('textMode').hidden, false);
  run("setWorkflowMode('batch')");
  assert.deepEqual(snapshot(), cardSnapshots[count - 1]);
  assert.equal(read('railUnderstand').textContent, `${count} / ${count}`);
  assert.equal(read('railProtect').textContent, 'Not Started');

  run(`batchRun = {mode:'batch', summary:{total:0, analyzed:0}};
    batchEntries = []; updateJourneyRail(batchRun);`);
  assert.equal(read('railUnderstand').textContent, 'Ready');
  run(`batchEntries = Array.from({length:5}, (_, i) => ({file:{name:'queued-'+i}, status:i===2?'PROCESSING':i<2?'COMPLETE':'WAITING'}));
    batchProcessing = true; updateJourneyRail(batchRun); updateBatchProgress(2, 5);`);
  assert.equal(read('railUnderstand').textContent, '2 / 5');
  assert.equal(read('batchProgressText').textContent, 'Analyzing report 3 of 5');
  assert.equal(read('processingActivity').hidden, false);
  run('batchProcessing = false; updateBatchProgress(5, 5);');
  assert.equal(read('processingActivity').hidden, true);

  run(`{
    const seed = input.run.documents[0];
    const states = ['COMPLETE', 'NEEDS_REVIEW', 'COMPLETE', 'FAILED', 'COMPLETE'];
    const documents = states.map((state, index) => {
      const item = JSON.parse(JSON.stringify(seed));
      item.document_id = 'protect-' + (index + 1);
      item.order = index;
      item.original_filename = 'protect-' + (index + 1) + '.pdf';
      item.source_type = 'pdf';
      item.current_stage = 'PROTECT';
      item.stage_status.UNDERSTAND = {status:'COMPLETE'};
      item.stage_status.PROTECT = {status:state};
      item.stage_errors = state === 'FAILED' ? {PROTECT:'Privacy Protection could not process this report.'} : {};
      item.stage_results = {UNDERSTAND:item.stage_results.UNDERSTAND};
      if (state !== 'FAILED') {
        const review = state === 'NEEDS_REVIEW';
        item.stage_results.PROTECT = {
          protected_document:{
            report_id:item.document_id,
            protected_text:'Protected report ' + (index + 1),
            artifact:index === 2 ? null : {
              filename:'protect-' + (index + 1) + '_PROTECTED.pdf', media_type:'application/pdf',
              availability:true, page_count:1,
            },
          },
          patient_analytic_context:{fields:{}, populated_fields:[]},
          protection_result:{
            status:state,
            policy_display_name:'Clinical Workflow',
            protected_entity_category_summary:index === 2 ? {Names:1} : {},
            review_signal_summary:review ? [{
              category:'possible_person_name',
              human_label:'Possible person-name signal',
              count:2,
            }] : [],
            review_required:review,
            warnings:review ? ['One or more privacy candidates require review.'] : [],
          },
          protection_provenance:{
            output_owner:'MedNexus',
            external_engine_role:'candidate_detector',
            privacy_decision_path:'unified',
            candidate_counts:review
              ? {total:2, accepted:0, rejected:0, review_required:2, pending:0}
              : index === 0 ? {total:0, accepted:0, rejected:0, review_required:0, pending:0}
              : {total:1, accepted:1, rejected:0, review_required:0, pending:0},
          },
        };
      }
      return item;
    });
    batchRun = {
      run_id:'protect-contract', mode:'batch', documents,
      protection_summary:{eligible:5, submitted:5, terminal:5, results_stored:4, complete:3, needs_review:1, failed:1, blocked:0},
      handoff:{protect:{available:false, eligible_document_ids:[]}},
    };
    batchEntries = documents.map(item => ({file:{name:item.original_filename}, status:item.stage_status.PROTECT.status}));
    workflowMode = 'batch'; activeJourneyStage = 'PROTECT'; selectedBatchDocumentId = documents[0].document_id;
    renderBatchReportBrowser(); selectBatchDocument(selectedBatchDocumentId, false);
  }`);
  await Promise.resolve();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(read('batchResultList').children.length, 5);
  assert.equal(read('protectedViewBtn').attributes['aria-pressed'], 'true');
  assert.equal(read('protectedPdfPanel').hidden, false);
  assert.equal(read('protectedText').hidden, true);
  assert.equal(read('textViewBtn').hidden, false);
  assert.equal(read('comparePanel').hidden, true);
  assert.equal(read('originalCompareText').textContent, '');
  assert.equal(read('protectedPdfViewer').src, 'blob:/api/v1/understanding/journey-runs/protect-contract/documents/protect-1/protected-artifact');
  assert.deepEqual(artifactRequests.at(-1), {
    url:'/api/v1/understanding/journey-runs/protect-contract/documents/protect-1/protected-artifact',
    method:'GET',
  });
  await run('showCompareView()');
  assert.equal(read('comparePanel').hidden, false);
  assert.equal(read('originalComparePdf').hidden, false);
  assert.equal(read('protectedComparePdf').hidden, false);
  assert.equal(read('originalCompareText').hidden, true);
  assert.equal(read('protectedCompareText').hidden, true);
  assert.equal(read('originalCompareTitle').textContent, 'Original PDF');
  assert.equal(read('protectedCompareTitle').textContent, 'Protected PDF');
  assert.equal(read('originalComparePdf').src, 'blob:/api/v1/understanding/journey-runs/protect-contract/documents/protect-1/compare-artifact');
  assert.equal(read('protectedComparePdf').src, 'blob:/api/v1/understanding/journey-runs/protect-contract/documents/protect-1/protected-artifact');
  assert.match(read('protectedEntitySummary').textContent, /No PHI detected/);

  await read('batchResultList').children[1].children[0].click();
  await Promise.resolve();
  await new Promise(resolve => setImmediate(resolve));
  assert.match(read('protectStatus').textContent, /Needs Review/);
  assert.equal(read('protectionReview').hidden, false);
  assert.match(read('protectionReviewMessage').textContent, /Possible person-name signal: 2/);
  assert.equal(typeof read('reviewProtectionBtn').onclick, 'function');
  read('originalCompareText').textContent = 'SENSITIVE ORIGINAL';
  read('comparePanel').hidden = false;
  read('protectedText').hidden = true;

  await read('batchResultList').children[2].children[0].click();
  await Promise.resolve();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(read('originalCompareText').textContent, '');
  assert.equal(read('comparePanel').hidden, true);
  assert.equal(read('protectedPdfPanel').hidden, false);
  assert.equal(read('protectedText').hidden, true);
  assert.equal(read('protectedText').textContent, 'Protected report 3');
  assert.equal(read('protectedPdfViewer').src, 'blob:/api/v1/understanding/journey-runs/protect-contract/documents/protect-3/protected-artifact');
  assert.match(read('nextStageSummary').textContent, /3 reports have completed Privacy Protection/);
  assert.match(read('nextStageSummary').textContent, /1 requires review/);
  assert.equal(read('continueExtractBtn').textContent, 'Open EXTRACT Workspace');
  assert.equal(read('continueExtractBtn').disabled, false);
  assert.equal(read('railProtect').textContent, '5 / 5');

  await read('batchResultList').children[3].children[0].click();
  assert.equal(read('protectionError').hidden, false);
  assert.match(read('protectionError').textContent, /could not process this report/);
  assert.equal(read('protectionReview').hidden, true);

  return {
    single,
    navigatorCards: count,
    selectedCardsVerified: cardSnapshots,
    navigation: 'all previous/next verified',
    runPreserved: true,
    protection: 'mixed states, selected-report PDF artifacts, compare PDFs, and sensitive DOM clearing verified',
  };
}

module.exports = { verifyReportCards };
if (require.main === module) {
  const input = JSON.parse(fs.readFileSync(0, 'utf8'));
  verifyReportCards(input)
    .then(result => process.stdout.write(JSON.stringify(result)))
    .catch(error => {
      console.error(error);
      process.exitCode = 1;
    });
}
