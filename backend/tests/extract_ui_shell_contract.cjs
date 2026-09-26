// DOM contract for the R2 EXTRACT shell; all clinical values below are test-only.
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

const root = path.resolve(__dirname, '../..');
const html = fs.readFileSync(path.join(root, 'frontend/understanding.html'), 'utf8');
const source = fs.readFileSync(path.join(root, 'frontend/understanding.js'), 'utf8');
const nodes = new Map();
for (const match of html.matchAll(/<([a-z][a-z0-9]*)\b([^>]*\bid="([^"]+)"[^>]*)>/gi)) {
  assert(!nodes.has(match[3]), `duplicate ID ${match[3]}`);
  const node = new Element(match[1]);
  node.hidden = /\bhidden\b/.test(match[2]);
  node.className = match[2].match(/class="([^"]+)"/)?.[1] || '';
  node.parentElement = new Element();
  nodes.set(match[3], node);
}
const read = id => { assert(nodes.has(id), `missing page ID ${id}`); return nodes.get(id); };
const requests = [];
const context = vm.createContext({
  document: { getElementById: read, createElement: tag => new Element(tag) },
  fetch: async (url, options = {}) => { requests.push([url, options.method || 'GET']); throw Error('No extraction endpoint exists'); },
  URL: { revokeObjectURL() {}, createObjectURL() { throw Error('No PDF test asset'); } },
});
vm.runInContext(source, context);
const run = script => vm.runInContext(script, context);
const protectedResult = (reportId, text, status = 'COMPLETE') => ({
  protected_document: { report_id: reportId, protected_text: text },
  protection_result: { status, policy_display_name: 'Clinical Workflow' },
});
const runDocument = (id, name, text, protectStatus = 'COMPLETE') => ({
  document_id: id, original_filename: name, source_type: 'txt',
  stage_status: { UNDERSTAND: { status: 'COMPLETE' }, PROTECT: { status: protectStatus }, EXTRACT: { status: 'NOT_STARTED' } },
  stage_results: { PROTECT: protectedResult(id, text, protectStatus) },
});

const first = runDocument('one', 'one.txt', 'alpha beta gamma');
context.fixture = { run_id: 'single-run', documents: [first] };
run('singleRun = fixture; singlePayload = {document_context:{document:{source_name:"one.txt"},processing_context:{extract_ready:false}}}; renderProtectionResult(fixture.documents[0].stage_results.PROTECT, {runId:"single-run",documentId:"one",sourceName:"one.txt",sourceType:"txt",state:"COMPLETE",scroll:false});');
assert.equal(read('continueExtractBtn').disabled, false);
assert.equal(read('continueExtractBtn').textContent, 'Open EXTRACT Workspace');
read('continueExtractBtn').click();
assert.equal(run('activeJourneyStage'), 'EXTRACT');
assert.equal(read('extractCard').hidden, false);
assert.equal(read('protectionCard').hidden, true);
assert.equal(first.stage_status.EXTRACT.status, 'NOT_STARTED');
assert.equal(run('singlePayload.document_context.processing_context.extract_ready'), false);
assert.equal(read('railExtract').textContent, 'Not Started');
assert.match(read('extractReadiness').textContent, /has not been run/);
assert.equal(read('extractStageStatus').textContent, 'Not run yet');
assert.equal(read('extractInputStatus').textContent, 'Protected input ready');
assert.equal(read('extractProtectedText').textContent, 'alpha beta gamma');
assert.equal(read('extractMetrics').hidden, true);
assert.equal(read('extractMetrics').textContent, '');
assert.equal(read('extractSummaryEmpty').hidden, false);
assert.match(read('extractSummaryEmpty').textContent, /Not run yet/);
assert.match(read('extractFindings').textContent, /No clinical extraction has been run/);
assert.equal(read('extractTechnical').attributes.open, undefined);
assert.equal(read('extractFindingsTab').attributes['aria-selected'], 'true');
read('extractRelationshipsTab').click();
assert.equal(read('extractRelationshipsPanel').hidden, false);
read('extractContextTab').click();
assert.equal(read('extractContextPanel').hidden, false);
assert.equal(requests.length, 0, 'Opening the shell must not invoke a model or EXTRACT endpoint');

// Contract-shaped future output is rendered only when explicitly supplied for that report.
const facts = {
  report_id: 'one',
  radiology_findings: [
    { finding_concept: { display: 'Observation A' }, semantic_class: 'FINDING', clinical_salience: 'PRIMARY', assertion_state: 'PRESENT', evidence_anchors: [
      { role: 'SUMMARY_ASSERTION', quote: 'alpha', start_offset: 0, end_offset: 5 },
      { role: 'DETAIL_SUPPORT', quote: 'beta', start_offset: 6, end_offset: 10 },
    ] },
    { finding_concept: { display: 'Observation B' }, semantic_class: 'DIAGNOSIS', clinical_salience: 'SECONDARY', assertion_state: 'ABSENT_NEGATED', evidence_span: { role: 'NEGATION_SUPPORT', quote: 'gamma', start_offset: 11, end_offset: 16 } },
    { finding_concept: { display: 'Observation C' }, clinical_salience: 'SUPPORTING', assertion_state: 'UNCERTAIN', review_state: 'NEEDS_REVIEW', internal_report_conflict: { summary_assertion: 'ABSENT_NEGATED', detail_assertion: 'UNCERTAIN' } },
  ],
  radiology_finding_relationships: [{ source_finding: 'A', relationship_type: 'ASSOCIATED_WITH', target_finding: 'B', evidence_span: { role: 'RELATION_SUPPORT', quote: 'beta' } }],
  clinical_context_facts: [{ context_concept: { display: 'Context A' }, context_role: 'INDICATION', assertion_state: 'PRESENT', evidence_span: { role: 'CONTEXT_SUPPORT', quote: 'alpha' } }],
};
context.facts = facts;
run('renderExtractFacts(facts, "alpha beta gamma")');
assert.match(read('extractFindings').textContent, /Observation A/);
assert.match(read('extractFindings').textContent, /Primary/);
assert.match(read('extractFindings').textContent, /Secondary/);
assert.match(read('extractFindings').textContent, /Supporting/);
assert.match(read('extractFindings').textContent, /Present/);
assert.match(read('extractFindings').textContent, /Absent \/ Not observed/);
assert.match(read('extractFindings').textContent, /Possible \/ Uncertain/);
assert.match(read('extractFindings').textContent, /Needs Review/);
assert.match(read('extractFindings').textContent, /Internal Report Conflict/);
assert.match(read('extractFindings').textContent, /Diagnostic Summary: Absent/);
assert.match(read('extractFindings').textContent, /Findings Description: Possible/);
assert.match(read('extractRelationships').textContent, /Associated With/);
assert.match(read('extractContext').textContent, /Context A/);
assert.doesNotMatch(read('extractContext').textContent, /Age Band/);
const firstEvidence = read('extractFindings').children[0].children.find(child => child.className === 'extract-evidence-list').children[0].children.find(child => child.tagName === 'button');
assert(firstEvidence, 'finding evidence button exists');
firstEvidence.click();
assert.equal(read('extractProtectedText').children.find(child => child.tagName === 'mark').textContent, 'alpha');
assert.equal(read('extractProtectedText').hidden, false);

// A genuine completed result with no findings can display numeric zero counts.
run('renderExtractFacts({report_id:"one",radiology_findings:[]}, "alpha beta gamma", "COMPLETE")');
assert.equal(read('extractMetrics').hidden, false);
assert.match(read('extractMetrics').textContent, /0Clinical Findings/);
assert.equal(read('extractSummaryEmpty').hidden, true);

const second = runDocument('two', 'two.txt', 'delta epsilon', 'NEEDS_REVIEW');
context.reviewResult = second.stage_results.PROTECT;
assert.doesNotMatch(run('buildNextStagePresentation(null, buildProtectionViewModel(reviewResult, {state:"NEEDS_REVIEW",sourceType:"txt"}), buildExtractInputSafety(reviewResult,"NEEDS_REVIEW",false)).message'), /resolve the protection review before clinical extraction/i);
first.stage_results.EXTRACT = facts;
first.stage_status.EXTRACT.status = 'COMPLETE';
context.batchFixture = { run_id: 'batch-run', mode: 'batch', documents: [first, second] };
run('workflowMode = "batch"; batchRun = batchFixture; selectedBatchDocumentId = "one"; renderExtractWorkspace(batchFixture.documents[0], batchFixture.run_id, {scroll:false});');
assert.equal(read('extractReportName').textContent, 'one.txt');
assert.equal(read('extractProtectedText').textContent, 'alpha beta gamma');
assert.match(read('extractFindings').textContent, /Observation A/);
run('selectBatchDocument("two", false)');
assert.equal(read('extractReportName').textContent, 'two.txt');
assert.equal(read('extractProtectedText').textContent, 'delta epsilon');
assert.doesNotMatch(read('extractFindings').textContent, /Observation A/);
assert.equal(read('extractStageStatus').textContent, 'Not run yet');
assert.equal(read('extractInputStatus').textContent, 'Protected input ready');
assert.match(read('extractReadiness').textContent, /Workspace ready/);
assert.equal(read('extractMetrics').hidden, true);
assert.equal(read('extractMetrics').textContent, '');
assert.equal(read('reportCounter').textContent, 'Report 2 of 2');
assert.equal(requests.length, 0);

// Review is not the safety gate; an incomplete protection result is.
const unsafe = runDocument('three', 'three.txt', 'unprotected identity', 'BLOCKED');
unsafe.stage_status.EXTRACT.status = 'BLOCKED';
context.unsafeFixture = unsafe;
assert.match(run('buildNextStagePresentation(null, buildProtectionViewModel(unsafeFixture.stage_results.PROTECT, {state:"BLOCKED",sourceType:"txt"}), buildExtractInputSafety(unsafeFixture.stage_results.PROTECT,"BLOCKED",false)).message'), /safe protected representation is unavailable/i);
run('renderExtractWorkspace(unsafeFixture, "batch-run", {scroll:false})');
assert.equal(read('extractStageStatus').textContent, 'Blocked');
assert.equal(read('extractInputStatus').textContent, 'Protected input unavailable');
assert.match(read('extractReadiness').textContent, /input blocked/);
assert.doesNotMatch(read('extractProtectedText').textContent, /unprotected identity/);
assert.equal(read('extractMetrics').hidden, true);
assert.equal(requests.length, 0);

// PDF-origin input requires an available, integrity-identified protected artifact.
assert.equal(run('buildExtractInputSafety({protection_result:{status:"NEEDS_REVIEW"},protected_document:{protected_text:"safe",artifact:{availability:true,media_type:"application/pdf",integrity_sha256:"digest"}}},"NEEDS_REVIEW",true).ready'), true);
assert.equal(run('buildExtractInputSafety({protection_result:{status:"NEEDS_REVIEW"},protected_document:{protected_text:"safe",artifact:null}},"NEEDS_REVIEW",true).ready'), false);
console.log('EXTRACT UI shell contract: state, privacy-safety, zero-result and no-execution checks passed');
