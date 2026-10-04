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
  click() { if (!this.disabled && !this.hidden) return this.onclick?.({ currentTarget: this }); }
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
assert.match(read('extractFindings').textContent, /No clinical extraction result/);
assert.equal(read('extractTechnical').attributes.open, undefined);
assert.equal(read('extractViewEvidenceBtn').attributes['aria-expanded'], 'false');
assert.equal(requests.length, 0, 'Opening the shell must not invoke a model or EXTRACT endpoint');

// Canonical clinical facts drive the human view; raw engine evidence stays collapsed.
const fact = (id, label, group, anchors, extra = {}) => ({
  fact_id: id, display_label: label, group, fact_type: group === 'DIAGNOSTIC' ? 'DIAGNOSTIC_HYPOTHESIS' : 'FINDING',
  assertion_state: group === 'DIAGNOSTIC' ? 'UNCERTAIN' : 'PRESENT',
  salience: group === 'KEY' ? 'PRIMARY' : 'SECONDARY',
  evidence_anchors: anchors, observations: [], review_required: group === 'DIAGNOSTIC',
  review_reason: group === 'DIAGNOSTIC' ? ['DIAGNOSTIC_INTERPRETATION'] : [], ...extra,
});
const summaryAnchor = { role: 'SUMMARY_ASSERTION', section_role: 'DIAGNOSTIC_SUMMARY',
  quote: 'alpha', start_offset: 0, end_offset: 5, engine_evidence_ids: ['e1'] };
const detailAnchor = { role: 'DETAIL_SUPPORT', section_role: 'FINDINGS_DESCRIPTION',
  quote: 'beta', start_offset: 6, end_offset: 10, engine_evidence_ids: ['e2'] };
const facts = {
  report_id: 'one', candidate_count: 41,
  clinical_synthesis: {
    clinical_synthesis: 'Observation A with associated detail.',
    canonical_facts: [
      fact('canonical-1', 'Observation A', 'KEY', [summaryAnchor, detailAnchor],
        { observations: [{ source_context: 'NON_CONTRAST', count: 1, measurements: ['26 x 23 mm'] }] }),
      fact('canonical-2', 'Possible diagnosis', 'DIAGNOSTIC', [summaryAnchor], { hypothesis_status: 'POSSIBLE' }),
      fact('canonical-3', 'Incidental finding', 'SECONDARY', [detailAnchor]),
      fact('canonical-4', 'Pertinent absence', 'NEGATIVE', [detailAnchor], { assertion_state: 'ABSENT_NEGATED' }),
    ],
    review_summary: { targeted_fact_count: 1 },
    technical_evidence_mapping: { 'canonical-1': ['e1', 'e2'] },
  },
  raw_engine_evidence: { candidates: Array.from({ length: 41 }, (_, index) => ({ candidate_id: `e${index + 1}` })),
    sections: [{ entities: { e1: { label: 'Observation::definitely present' } } }] },
  radiology_findings: Array.from({ length: 41 }, (_, index) => ({ finding_id: `raw-${index + 1}` })),
  radiology_finding_relationships: [{ relationship_id: 'relation-1', relationship_type: 'ASSOCIATED_WITH' }],
  clinical_context_facts: [{ context_concept: { display: 'Context A' }, context_role: 'INDICATION',
    assertion_state: 'PRESENT', evidence_span: summaryAnchor }],
};
context.facts = facts;
run('renderExtractFacts(facts, "alpha beta gamma", "NEEDS_REVIEW")');
assert.match(read('extractMetrics').textContent, /1Key Findings/);
assert.match(read('extractMetrics').textContent, /1Diagnostic Considerations/);
assert.match(read('extractMetrics').textContent, /1Secondary Findings/);
assert.doesNotMatch(read('extractMetrics').textContent, /41/);
assert.match(read('extractSynthesisText').textContent, /Observation A with associated detail/);
assert.equal(read('extractFindings').children.length, 1);
assert.match(read('extractFindings').textContent, /26 x 23 mm/);
assert.match(read('extractFindings').textContent, /2 evidence anchors/);
assert.match(read('extractDiagnoses').textContent, /Possible diagnosis/);
assert.match(read('extractDiagnoses').textContent, /Possible/);
assert.doesNotMatch(read('extractFindings').textContent, /Possible diagnosis/);
assert.match(read('extractSecondaryFacts').textContent, /Incidental finding/);
assert.match(read('extractNegativeFacts').textContent, /Pertinent absence/);
assert.equal(read('extractSecondary').attributes.open, undefined);
assert.equal(read('extractNegatives').attributes.open, undefined);
assert.equal(read('extractTechnical').attributes.open, undefined);
assert.match(read('extractTechnicalCount').textContent, /41 validated engine findings/);
assert.doesNotMatch(read('extractTechnicalCount').textContent, /raw candidates/);
assert.match(read('extractTechnicalBody').textContent, /Raw extraction candidates/);
assert.equal(read('extractDiagnoses').children[0].tagName, 'details');
assert.equal(read('extractDiagnoses').children[0].attributes.open, undefined);
assert.equal(read('extractSecondaryFacts').children[0].tagName, 'details');
assert.equal(read('extractFindings').children[0].tagName, 'article');
assert.equal(read('extractReviewDetails').hidden, false);
assert.match(read('extractReviewSummary').textContent, /Needs Review · 1 item/);
assert.equal(read('extractReviewSummary').attributes['aria-expanded'], 'false');
assert.equal(read('extractContextDetails').attributes.open, undefined);
assert.match(read('extractTechnicalBody').textContent, /raw-41/);
assert.match(read('extractTechnicalBody').textContent, /technical_evidence_mapping/);
assert.match(read('extractContext').textContent, /Context A/);
assert.doesNotMatch(read('extractFindings').textContent, /raw-41/);
assert.equal(read('extractSecondarySummary').attributes['aria-expanded'], 'false');
assert.equal(read('extractTechnicalSummary').attributes['aria-expanded'], 'false');
const expandedFacts = structuredClone(facts);
expandedFacts.clinical_synthesis.canonical_facts.splice(1, 0, fact('canonical-associated', 'Associated edema', 'KEY', [detailAnchor],
  { salience: 'ASSOCIATED', review_reason: ['SOURCE_SPECIFIC_LESION_COUNT'] }));
context.expandedFacts = expandedFacts;
run('renderExtractFacts(expandedFacts, "alpha beta gamma", "NEEDS_REVIEW")');
assert.equal(read('extractFindings').children[0].tagName, 'article');
assert.equal(read('extractFindings').children[1].tagName, 'details');
assert.equal(read('extractFindings').children[1].attributes.open, undefined);
assert.match(read('extractFindings').children[1].textContent, /Associated with principal lesion complex/);
assert.doesNotMatch(read('extractFindings').textContent, /Diagnostic Interpretation|Source Specific Lesion Count/);
assert.match(read('extractReviewSummary').textContent, /Needs Review · 2 items/);
assert.match(read('extractReviewItems').textContent, /Diagnostic Interpretation/);
assert.match(read('extractReviewItems').textContent, /Source Specific Lesion Count/);
assert.equal(read('extractDiagnoses').children[0].children[0].attributes['aria-expanded'], 'false');
read('extractDiagnoses').children[0].open = true;
read('extractDiagnoses').children[0].ontoggle();
assert.equal(read('extractDiagnoses').children[0].children[0].attributes['aria-expanded'], 'true');
const associatedDetail = read('extractFindings').children[1].children[1];
const associatedEvidence = associatedDetail.children.find(child => child.className === 'extract-evidence-list')
  .children[0].children.find(child => child.tagName === 'button');
associatedEvidence.click();
assert.equal(read('extractProtectedText').children.find(child => child.tagName === 'mark').textContent, 'beta');
read('extractCloseEvidenceBtn').click();
run('renderExtractFacts(facts, "alpha beta gamma", "NEEDS_REVIEW")');
const evidenceDetail = read('extractFindings').children[0].children.find(child => child.className === 'extract-fact-evidence');
const firstEvidence = evidenceDetail.children.find(child => child.className === 'extract-evidence-list').children[0]
  .children.find(child => child.tagName === 'button');
assert(firstEvidence, 'canonical fact evidence button exists');
firstEvidence.click();
assert.equal(read('extractProtectedText').children.find(child => child.tagName === 'mark').textContent, 'alpha');
assert.equal(read('extractProtectedText').hidden, false);
assert.equal(read('extractViewEvidenceBtn').attributes['aria-expanded'], 'true');
assert.equal(read('extractPdfPanel').hidden, true);
read('extractCloseEvidenceBtn').click();
assert.equal(read('extractViewEvidenceBtn').attributes['aria-expanded'], 'false');
assert.match(fs.readFileSync(path.join(root, 'frontend/understanding-styles.css'), 'utf8'),
  /grid-template-columns: minmax\(0, 44fr\) minmax\(0, 56fr\)/);
assert.match(fs.readFileSync(path.join(root, 'frontend/understanding-styles.css'), 'utf8'),
  /\.extract-clinical \{ order: -1; \}/);
const css = fs.readFileSync(path.join(root, 'frontend/understanding-styles.css'), 'utf8');
assert.match(css, /@media \(max-width: 980px\)[\s\S]*?\.extract-source \{ display: none; position: fixed;/);
assert.match(css, /\.extract-mobile-report \{ display: flex;/);

// A result with engine entities but no eligible synthesis says so explicitly.
run('renderExtractFacts({candidate_count:41,clinical_synthesis:{canonical_facts:[],clinical_synthesis:"",review_summary:{targeted_fact_count:0}}}, "alpha beta gamma", "NEEDS_REVIEW")');
assert.match(read('extractSynthesisText').textContent, /No eligible canonical clinical facts/);
assert.equal(read('extractMetrics').hidden, false);
assert.match(read('extractTechnicalCount').textContent, /0 validated engine findings/);
assert.match(read('extractTechnicalBody').textContent, /Raw extraction candidates41/);
run('renderExtractFacts(null, "alpha beta gamma", "FAILED")');
assert.match(read('extractSummaryEmpty').textContent, /failed/i);
assert.equal(read('extractMetrics').hidden, true);

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
assert.equal(read('extractMetrics').hidden, true);
assert.equal(requests.length, 0);

// A protected PDF is fetched only after explicit View PDF interaction.
const pdfFixture = runDocument('pdf-one', 'synthetic.pdf', 'alpha beta gamma');
pdfFixture.source_type = 'pdf';
pdfFixture.stage_results.PROTECT.protected_document.artifact = {
  availability: true, media_type: 'application/pdf', integrity_sha256: 'digest',
};
context.pdfFixture = pdfFixture;
run('renderExtractWorkspace(pdfFixture, "single-run", {scroll:false})');
assert.equal(read('extractPdfPanel').hidden, true);
assert.equal(read('extractMobilePdfBtn').hidden, false);
assert.equal(requests.length, 0);
read('extractMobilePdfBtn').click();
assert.equal(read('extractPdfPanel').hidden, false);
assert.equal(read('extractMobilePdfBtn').attributes['aria-expanded'], 'true');
assert.equal(requests.length, 1);
read('extractCloseEvidenceBtn').click();
assert.equal(read('extractMobilePdfBtn').attributes['aria-expanded'], 'false');
requests.length = 0;

// Review is not the safety gate; an incomplete protection result is.
const unsafe = runDocument('three', 'three.txt', 'unprotected identity', 'BLOCKED');
unsafe.stage_status.EXTRACT.status = 'BLOCKED';
context.unsafeFixture = unsafe;
run('renderExtractWorkspace(unsafeFixture, "batch-run", {scroll:false})');
assert.match(read('extractReadiness').textContent, /input blocked/);
assert.doesNotMatch(read('extractProtectedText').textContent, /unprotected identity/);
assert.equal(read('extractMetrics').hidden, true);
assert.equal(requests.length, 0);

assert.equal(run('buildExtractInputSafety({protection_result:{status:"NEEDS_REVIEW"},protected_document:{protected_text:"safe",artifact:{availability:true,media_type:"application/pdf",integrity_sha256:"digest"}}},"NEEDS_REVIEW",true).ready'), true);
assert.equal(run('buildExtractInputSafety({protection_result:{status:"NEEDS_REVIEW"},protected_document:{protected_text:"safe",artifact:null}},"NEEDS_REVIEW",true).ready'), false);
console.log('EXTRACT clinical synthesis UI contract passed');

(async () => {
  first.stage_results.UNDERSTAND = { document_context: { identity: { healthcare_domain: 'RADIOLOGY' } } };
  first.stage_status.EXTRACT.status = 'NOT_STARTED';
  context.pilotFixture = { run_id: 'pilot-run', documents: [first] };
  context.fetch = async (url, options) => {
    requests.push([url, options.method]);
    assert.equal(first.stage_status.EXTRACT.status, 'PROCESSING');
    return { ok: true, json: async () => ({ run_id: 'pilot-run', documents: [{ ...first,
      stage_status: { ...first.stage_status, EXTRACT: { status: 'NEEDS_REVIEW' } },
      stage_results: { ...first.stage_results, EXTRACT: facts },
    }] }) };
  };
  run('workflowMode="single"; singleRun=pilotFixture; renderExtractWorkspace(pilotFixture.documents[0],"pilot-run",{scroll:false})');
  assert.equal(read('runClinicalExtractionBtn').disabled, false);
  assert.equal(requests.length, 0);
  await read('runClinicalExtractionBtn').click();
  assert.equal(requests.length, 1);
  assert.equal(requests[0][0], '/api/v1/understanding/journey-runs/pilot-run/documents/one/extract');
  assert.equal(requests[0][1], 'POST');
  assert.equal(read('extractStageStatus').textContent, 'Needs Review');
  assert.match(read('extractFindings').textContent, /Observation A/);
})().catch(error => { console.error(error); process.exitCode = 1; });
