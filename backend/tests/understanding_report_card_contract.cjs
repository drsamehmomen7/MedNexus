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
  scrollIntoView() {}
  focus() { this.focused = true; }
  click() { if (!this.disabled) this.onclick?.(); }
}

function verifyReportCards(input) {
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
  const context = vm.createContext({
    document: { getElementById: read, createElement: tag => new Element(tag) },
    location: { assign: url => navigation.push(url) },
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
  if (handoff) { read('continueBtn').click(); assert.equal(navigation.pop(), handoff); }

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
  assert.equal(read('batchProtectBtn').disabled, true);
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
  return {single, navigatorCards: count, selectedCardsVerified: cardSnapshots, navigation: 'all previous/next verified', runPreserved: true};
}

module.exports = { verifyReportCards };
if (require.main === module) {
  const input = JSON.parse(fs.readFileSync(0, 'utf8'));
  process.stdout.write(JSON.stringify(verifyReportCards(input)));
}
