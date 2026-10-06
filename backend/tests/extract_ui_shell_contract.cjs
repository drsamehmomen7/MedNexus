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
  document: { getElementById: read, createElement: tag => new Element(tag),
    createElementNS: (_namespace, tag) => new Element(tag) },
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
  assert.equal(read('continueStandardizeBtn').disabled, false);
  assert.equal(read('continueStandardizeBtn').hidden, false);
  read('continueStandardizeBtn').click();
  assert.equal(run('activeJourneyStage'), 'STANDARDIZE');
  assert.equal(read('standardizeCard').hidden, false);
  assert.equal(read('extractCard').hidden, true);
  assert.equal(read('activeStageNumber').textContent, '04');
  assert.match(read('standardizeReportName').textContent, /one.txt/);
  assert.equal(read('runStandardizeBtn').disabled, false);
  facts.clinical_synthesis.canonical_facts[3].display_label = 'No diverticulum';
  const sourceBefore = JSON.stringify(facts);
  const standardized = {
    report_id: 'one', state: 'NEEDS_REVIEW',
    summary: { clinical_concepts: { total: 4, matched: 2, needs_review: 1, unmapped: 1 },
      whole_fact_exact_mappings: 1, component_exact_mappings: 2,
      facts_with_component_standardization: 2, facts_needing_review: 1, facts_fully_unmapped: 1,
      anatomy: { total: 0, matched: 0, needs_review: 0, unmapped: 0 },
      measurements: { total: 2, normalized: 2, needs_review: 0, unmapped: 0 },
      study_identity: 'UNMAPPED' },
    standardized_study_context: { original_exam_name: 'MRI Extremity', normalized_modality: 'MRI',
      normalized_body_region: 'EXTREMITY', normalized_laterality: null,
      procedure_mapping: { mapping_status: 'UNMAPPED', code: null } },
    technical_diagnostics: { provider_versions: { RADLEX_CURRENT: '4.3', LOINC_RSNA_2_82: '2.82' } },
    standardized_facts: [{ source_fact_id: 'canonical-1',
      source_assertion_state: 'PRESENT',
      concept_mappings: [{ terminology_system: 'RADLEX_CURRENT', code: 'RID1',
        preferred_label: 'Observation A', match_type: 'EXACT_LABEL', mapping_status: 'MATCHED',
        lookup_scope: 'WHOLE_LABEL', mapping_method: 'LOCAL_REFERENCE_EXACT' }],
      component_mappings: [], anatomy_mappings: [], standardized_measurements: [
        { original_text: '1.4 cm', normalized_value: '14', normalized_unit: 'mm' },
        { original_text: '4 mm', normalized_value: '4', normalized_unit: 'mm' }] },
    { source_fact_id: 'canonical-2', source_assertion_state: 'UNCERTAIN',
      concept_mappings: [{ terminology_system: 'RADLEX_CURRENT', code: null,
        mapping_status: 'NEEDS_REVIEW', match_type: 'BROADER', mapping_method: 'STRUCTURED_COMPONENTS' }],
      component_mappings: [{ source_text: 'edema', code: 'RID4865', match_type: 'EXACT_LABEL', relationship_to_fact: 'BROADER' }],
      anatomy_mappings: [], standardized_measurements: [] },
    { source_fact_id: 'canonical-3', source_assertion_state: 'PRESENT',
      concept_mappings: [{ terminology_system: 'RADLEX_CURRENT', code: null,
        mapping_status: 'UNMAPPED', match_type: 'NONE', mapping_method: 'NO_MAPPING' }],
      component_mappings: [], anatomy_mappings: [], standardized_measurements: [] },
    { source_fact_id: 'canonical-4', source_assertion_state: 'ABSENT_NEGATED',
      concept_mappings: [{ terminology_system: 'RADLEX_CURRENT', code: 'RID4817', preferred_label: 'diverticulum',
        mapping_status: 'MATCHED', match_type: 'EXACT_LABEL', lookup_scope: 'CANONICAL_CONCEPT',
        mapping_method: 'STRUCTURED_CANONICAL_CONCEPT' }],
      component_mappings: [{ source_text: 'diverticulum', code: 'RID4817', match_type: 'EXACT_LABEL', relationship_to_fact: 'EXACT_CONCEPT_ASSERTION_SEPARATE' }],
      anatomy_mappings: [], standardized_measurements: [] }],
  };
  context.fetch = async (url, options) => {
    requests.push([url, options.method]);
    assert.equal(read('standardizeStatus').textContent, 'Processing');
    assert.equal(read('runStandardizeBtn').disabled, true);
    return { ok: true, json: async () => ({ run_id: 'pilot-run', documents: [{ ...run('singleRun.documents[0]'),
      stage_status: { ...run('singleRun.documents[0].stage_status'), STANDARDIZE: { status: 'NEEDS_REVIEW' } },
      stage_results: { ...run('singleRun.documents[0].stage_results'), STANDARDIZE: standardized },
    }] }) };
  };
  await read('runStandardizeBtn').click();
  assert.equal(requests.length, 2);
  assert.equal(requests[1][0], '/api/v1/understanding/journey-runs/pilot-run/documents/one/standardize');
  assert.equal(requests[1][1], 'POST');
  assert.match(read('standardizeSummary').textContent, /4 total/);
  assert.match(read('standardizeSummary').textContent, /2 matched · 1 need review · 1 unmapped/);
  assert.match(read('standardizeSummary').textContent, /2 exact components/);
  assert.equal(read('standardizeOverview').hidden, false);
  assert.equal(read('standardizeConceptSection').hidden, false);
  assert.equal(read('standardizeStudySection').hidden, false);
  assert.match(read('standardizeFacts').textContent, /Observation A/);
  assert.match(read('standardizeFacts').textContent, /RID1/);
  assert.match(read('standardizeFacts').textContent, /Clinical component: edema → RadLex RID4865/);
  assert.match(read('standardizeFacts').textContent, /Whole expression: NEEDS REVIEW/);
  assert.match(read('standardizeFacts').textContent, /Whole expression: UNMAPPED/);
  assert.match(read('standardizeFacts').textContent, /No diverticulum.*Assertion: ABSENT/);
  assert.match(read('standardizeFacts').textContent, /RID4817.*assertion remains ABSENT/);
  assert.doesNotMatch(read('standardizeFacts').children[2].children[0].textContent, /FAILED/);
  assert.match(read('standardizeMeasurements').textContent, /1.4 cm → 14 mm/);
  assert.match(read('standardizeMeasurements').textContent, /4 mm → 4 mm/);
  assert.match(read('standardizeStudy').textContent, /MRI Extremity/);
  assert.match(read('standardizeStudy').textContent, /Procedure mapping: Unmapped/);
  assert.equal(read('standardizeTechnical').hidden, false);
  assert.equal(read('standardizeTechnical').attributes.open, undefined);
  assert.match(read('standardizeTechnicalBody').textContent, /RADLEX_CURRENT 4.3/);
  assert.equal(JSON.stringify(facts), sourceBefore, 'STANDARDIZE must not mutate EXTRACT facts');
  assert.equal(read('railStandardize').textContent, 'Needs Review');
  assert.match(read('stageStandardize').className, /active/);
  assert.doesNotMatch(read('stageExtract').className, /active/);
  read('returnExtractBtn').click();
  assert.equal(run('activeJourneyStage'), 'EXTRACT');
  assert.equal(read('extractCard').hidden, false);
  assert.equal(read('standardizeCard').hidden, true);
  assert.match(read('extractFindings').textContent, /Observation A/);
  read('continueStandardizeBtn').click();
  assert.equal(read('continueAnalyzeBtn').hidden, false);
  const collection = { collection_id: 'c'.repeat(32), name: 'Synthetic validation collection',
    version: 1, report_count: 1, eligible: 0, review_required: 1, excluded: 0 };
  const metric = (label, numerator, denominator) => ({ metric_type: 'finding_report_frequency',
    analysis_level: 'REPORT_LEVEL', display_label: label, concept_identity: `MRJ:${label}`,
    numerator, denominator, value: numerator / denominator, anatomy: [] });
  const analysis = { analysis_run_id: 'a'.repeat(32), collection_id: collection.collection_id,
    collection_version: 1, collection_name: collection.name, analysis_level: 'REPORT_LEVEL',
    generated_at: '2026-10-05T00:00:00Z', diagnostics: ['INSUFFICIENT_COMPARABLE_MEASUREMENTS'],
    eligibility_policy: { include_review_required_for_validation: true, human_review_asserted: false },
    collection_summary: { total_reports: 1, eligible_reports: 0, review_required_reports: 1,
      excluded_reports: 0, included_reports: 1, included_review_required_reports: 1,
      facts_total: 4, present_facts: 1, negative_facts: 1, uncertain_facts: 1,
      standardized_matched: 2, standardized_review: 1, standardized_unmapped: 1 },
    eligibility_summary: { reports: [{ report_id: 'synthetic-one', status: 'NEEDS_REVIEW',
      reasons: ['REPORT_REVIEW_REQUIRED'] }] },
    finding_frequencies: [metric('Observation A', 1, 1)],
    diagnostic_hypothesis_frequencies: [{ ...metric('Hypothesis', 1, 1), assertion: 'FAVORED' }],
    pertinent_negative_frequencies: [metric('diverticulum', 1, 1)],
    measurement_distributions: [], measurement_coverage: { unclassified_measurements: 2 },
    stratifications: [{ dimension: 'modality', category: 'MRI', numerator: 1, denominator: 1 }],
    cooccurrences: [{ concept_a: 'MRJ:edema', concept_b: 'MRJ:mass', numerator: 1, denominator: 1, value: 1 }],
    cooccurrence_presentation: { minimum_support: 2, top_n: 20, repeated_patterns: [],
      total_valid_pairs: 1, one_off_pairs: 1 },
    coverage_metrics: [{ field: 'modality', available: 1, missing: 0, denominator: 1 }],
    standardization_coverage: { whole_fact_matched: 2, needs_review: 1, unmapped: 1,
      component_mappings_available: 2, denominator_facts: 4 },
  };
  const vizPanel = (panel_id, title, visualization_type, data, empty_state = null) => ({
    panel_id, title, visualization_type, data, empty_state, subtitle: `${title} source values`,
    accessibility_description: `${title} textual description`, default_display_limit: 10,
  });
  const visualization = { visualization_run_id: 'v'.repeat(32), analysis_run_id: analysis.analysis_run_id,
    collection_id: collection.collection_id, collection_version: 1, collection_name: collection.name,
    generated_at: '2026-10-05T00:00:00Z', generated_at_basis: 'ANALYSIS_RUN_GENERATED_AT',
    analysis_policy: { include_review_required_for_validation: true, human_review_asserted: false, filters: {} },
    collection_summary: { included_reports: 1, included_review_required_reports: 1 },
    panels: [
      vizPanel('collection_snapshot', 'Collection Snapshot', 'SUMMARY_METRIC', [{ total_reports: 1,
        included_reports: 1, excluded_reports: 0, review_required_reports: 1,
        included_review_required_reports: 1, facts_total: 4 }]),
      vizPanel('top_findings', 'Top Findings', 'HORIZONTAL_BAR', [{ display_label: 'Observation A',
        concept_identity: 'MRJ:Observation A', anatomy: [], laterality: 'MISSING',
        numerator: 1, denominator: 1, value: 1 }]),
      vizPanel('diagnostic_considerations', 'Diagnostic Considerations', 'HORIZONTAL_BAR', [
        { display_label: 'Hypothesis', assertion: 'FAVORED', numerator: 1, denominator: 1, value: 1 }]),
      vizPanel('pertinent_negatives', 'Pertinent Negatives', 'HORIZONTAL_BAR', [
        { display_label: 'diverticulum', numerator: 1, denominator: 1, value: 1 }]),
      vizPanel('measurements', 'Measurements', 'TABLE', [],
        'INSUFFICIENT_COMPARABLE_MEASUREMENTS: No safely comparable measurement distributions.'),
      vizPanel('stratification', 'Stratification', 'HORIZONTAL_BAR', [
        { dimension: 'modality', category: 'MRI', numerator: 1, denominator: 1, value: 1 }]),
      vizPanel('temporal', 'Report Year', 'TABLE', [],
        'MISSING_TEMPORAL_DATA: No comparable report-year series is available.'),
      vizPanel('cooccurrence', 'Co-occurrence', 'HORIZONTAL_BAR', [],
        'No repeated co-occurrence patterns were observed in this collection.'),
      vizPanel('coverage', 'Data Coverage', 'COVERAGE_BAR', [
        { field: 'modality', available: 0, missing: 1, denominator: 1, value: 0 }]),
      vizPanel('standardization', 'Standardization Coverage', 'TABLE', [{ whole_fact_matched: 2,
        needs_review: 1, unmapped: 1, denominator_facts: 4, component_mappings_available: 2 }]),
    ],
  };
  let visualized = false;
  const indicatorEntry = (indicator_type, name, numerator, denominator, value, readiness_state, unit = 'REPORT_FRACTION') => {
    const indicator_id = `${indicator_type}_${name}`;
    return [
      { indicator_id, version: 1, name, indicator_type, analysis_level: 'REPORT_LEVEL',
        numerator_definition: `Included reports with ${name}`, denominator_definition: 'Included reports in AnalysisRun',
        eligibility_rule: 'INHERIT_ANALYSIS_RUN_POLICY', exclusions: 'INHERIT_ANALYSIS_RUN_EXCLUSIONS',
        time_window_definition: 'ANALYSIS_COLLECTION_SNAPSHOT',
        interpretation_scope: `Report-level interpretation of ${name}.`, unit },
      { indicator_id, numerator, denominator, value, readiness_state, warnings: [], coverage: {} },
    ];
  };
  const entries = [
    indicatorEntry('REPORT_FINDING_FREQUENCY', 'Cerebral atrophy', 1, 8, 0.125, 'VALIDATION_ONLY'),
    indicatorEntry('DIAGNOSTIC_CONSIDERATION_FREQUENCY', 'Metastatic tumor FAVORED', 1, 8, 0.125, 'VALIDATION_ONLY'),
    indicatorEntry('DOCUMENTED_NEGATIVE_FREQUENCY', 'Documented absence: aspiration', 1, 8, 0.125, 'VALIDATION_ONLY'),
    indicatorEntry('DATA_COVERAGE', 'Report service date coverage', 0, 8, 0, 'VALIDATION_ONLY'),
    indicatorEntry('STANDARDIZATION_COVERAGE', 'Whole-fact MATCHED coverage', 3, 55, null,
      'VALIDATION_ONLY', 'CANONICAL_FACT_RATIO'),
    indicatorEntry('MEASUREMENT_SUMMARY', 'Comparable measurement summary', null, 8, null, 'NOT_READY'),
  ];
  const indicators = { indicator_run_id: 'i'.repeat(32), analysis_run_id: analysis.analysis_run_id,
    collection_id: collection.collection_id, collection_version: 1, collection_name: collection.name,
    generated_at: '2026-10-05T00:00:00Z', generated_at_basis: 'ANALYSIS_RUN_GENERATED_AT',
    analysis_policy: { include_review_required_for_validation: true, human_review_asserted: false, filters: {} },
    collection_summary: { included_reports: 8, included_review_required_reports: 8 },
    readiness_summary: { READY: 0, VALIDATION_ONLY: 5, NEEDS_REVIEW: 0, NOT_READY: 1, INVALID: 0 },
    definitions: entries.map(entry => entry[0]), results: entries.map(entry => entry[1]),
  };
  let indicated = false;
  let indicatorErrorDetail = null;
  context.fetch = async (url, options = {}) => {
    requests.push([url, options.method || 'GET']);
    if (url.endsWith('/analysis-collections') && !options.method)
      return { ok: true, json: async () => ({ collections: [] }) };
    if (url.endsWith('/analysis-collections') && options.method === 'POST') {
      assert.deepEqual(JSON.parse(options.body).report_refs, [{ run_id: 'pilot-run', document_id: 'one' }]);
      return { ok: true, json: async () => collection };
    }
    if (url.endsWith('/analyze')) {
      assert.equal(JSON.parse(options.body).include_review_required_for_validation, true);
      assert.equal(read('runAnalysisBtn').disabled, true);
      return { ok: true, json: async () => analysis };
    }
    if (url.endsWith('/visualize')) {
      assert.equal(JSON.parse(options.body).journey_run_id, 'pilot-run');
      visualized = true;
      return { ok: true, json: async () => visualization };
    }
    if (url.endsWith('/indicators')) {
      assert.equal(JSON.parse(options.body).journey_run_id, 'pilot-run');
      if (indicatorErrorDetail) return { ok: false, status: 404, json: async () => ({ detail: indicatorErrorDetail }) };
      indicated = true;
      return { ok: true, json: async () => indicators };
    }
    if (url.endsWith('/journey-runs/pilot-run')) return { ok: true, json: async () => ({
      ...run('singleRun'), documents: [{ ...run('singleRun.documents[0]'),
        stage_status: { ...run('singleRun.documents[0].stage_status'), ANALYZE: { status: 'NEEDS_REVIEW' },
          VISUALIZE: { status: visualized ? 'NEEDS_REVIEW' : 'NOT_STARTED' },
          INDICATORS: { status: indicated ? 'NEEDS_REVIEW' : 'NOT_STARTED' } } }] }) };
    throw Error(`Unexpected Stage 05 request: ${url}`);
  };
  await read('continueAnalyzeBtn').click();
  assert.equal(run('activeJourneyStage'), 'ANALYZE');
  assert.equal(read('activeStageNumber').textContent, '05');
  assert.equal(read('analyzeCard').hidden, false);
  assert.equal(read('standardizeCard').hidden, true);
  read('analyzeCollectionName').value = collection.name;
  await read('createAnalysisCollectionBtn').click();
  assert.match(read('analyzeCollectionDetails').textContent, /1 reports.*0 eligible.*1 need review/);
  read('includeReviewAnalysis').checked = true;
  await read('runAnalysisBtn').click();
  assert.equal(read('railAnalyze').textContent, 'Needs Review');
  assert.match(read('stageAnalyze').className, /active/);
  assert.match(read('analyzeSummary').textContent, /1 included in this run/);
  assert.match(read('analyzeEligibility').textContent, /no human review asserted/i);
  assert.match(read('analyzeFindings').textContent, /1 \/ 1 included reports.*report frequency/);
  assert.match(read('analyzeNegatives').textContent, /ABSENT/);
  assert.match(read('analyzeMeasurements').textContent, /No safely comparable measurements/);
  assert.match(read('analyzeCooccurrences').textContent, /No repeated co-occurrence patterns were observed/);
  assert.match(read('analyzeCooccurrences').textContent, /at least 2 included reports; top 20/);
  assert.doesNotMatch(read('analyzeCooccurrences').textContent, /MRJ:edema \+ MRJ:mass/);
  assert.match(read('analyzeTechnicalBody').textContent, /1 valid co-occurrence pairs, including 1 one-off pairs/);
  context.analysisFixture = { ...analysis, cooccurrence_presentation: { minimum_support: 2,
    top_n: 20, total_valid_pairs: 2, one_off_pairs: 1, repeated_patterns: [
      { concept_a: 'MRJ:edema', concept_b: 'MRJ:mass', numerator: 3, denominator: 8, value: 0.375 },
    ] } };
  run('renderAnalysisResult(analysisFixture)');
  assert.match(read('analyzeCooccurrences').textContent, /MRJ:edema \+ MRJ:mass · 3 \/ 8 included reports \(38% report-level co-occurrence\)/);
  assert.match(read('analyzeCoverage').textContent, /0 missing/);
  assert.match(read('analyzeStandardization').textContent, /Component mappings are not whole-fact matches/);
  assert.equal(read('analyzeTechnical').attributes.open, undefined);
  assert.doesNotMatch(read('analyzeCard').textContent.toLowerCase(), /population prevalence|incidence|caused by|association/);
  assert.equal(read('continueVisualizeBtn').hidden, false);
  await read('continueVisualizeBtn').click();
  assert.equal(run('activeJourneyStage'), 'VISUALIZE');
  assert.equal(read('activeStageNumber').textContent, '06');
  assert.equal(read('visualizeCard').hidden, false);
  assert.equal(read('analyzeCard').hidden, true);
  assert.match(read('railVisualize').textContent, /Needs Review/);
  assert.match(read('visualizeContext').textContent, /Synthetic validation collection.*version 1.*AnalysisRun/);
  assert.match(read('visualizePolicy').textContent, /1 review-required reports.*does not imply human review/);
  assert.match(read('visualizePanels').textContent, /Observation A.*1 \/ 1 included reports/);
  assert.match(read('visualizePanels').textContent, /Hypothesis · FAVORED diagnostic consideration/);
  assert.match(read('visualizePanels').textContent, /Documented absence: diverticulum/);
  assert.match(read('visualizePanels').textContent, /INSUFFICIENT_COMPARABLE_MEASUREMENTS/);
  assert.match(read('visualizePanels').textContent, /MISSING_TEMPORAL_DATA/);
  assert.match(read('visualizePanels').textContent, /No repeated co-occurrence patterns/);
  assert.match(read('visualizePanels').textContent, /modality.*0 \/ 1 included reports available.*1 missing/);
  assert.match(read('visualizePanels').textContent, /Component mappings available \(separate\)/);
  assert.match(read('visualizeTechnicalBody').textContent, /VisualizationRun.*AnalysisRun.*Collection/);
  assert.equal(read('visualizeTechnical').attributes.open, undefined);
  assert.doesNotMatch(read('visualizeCard').textContent.toLowerCase(), /population prevalence|incidence|risk|association|correlation|causation/);
  context.temporalFixture = vizPanel('temporal', 'Report Year', 'LINE', [
    { category: '2023', numerator: 1, denominator: 2, value: 0.5 },
    { category: '2025', numerator: 2, denominator: 2, value: 1 },
  ]);
  const temporal = run('renderVisualizationPanel(temporalFixture)');
  assert.match(temporal.textContent, /2023: 1 \/ 2 included reports/);
  assert.equal(temporal.children.some(child => child.tagName === 'svg'), true);
  context.repeatedFixture = vizPanel('cooccurrence', 'Co-occurrence', 'HORIZONTAL_BAR', [
    { concept_a: 'MRJ:edema', concept_b: 'MRJ:mass', numerator: 3, denominator: 8, value: 0.375 },
  ]);
  assert.match(run('renderVisualizationPanel(repeatedFixture)').textContent,
    /MRJ:edema \+ MRJ:mass.*3 \/ 8 included reports.*37.5%/);
  const longLabel = 'Very long synthetic finding label '.repeat(8);
  context.longFixture = vizPanel('top_findings', 'Top Findings', 'HORIZONTAL_BAR',
    Array.from({ length: 12 }, (_, index) => ({ display_label: index ? `Finding ${index}` : longLabel,
      concept_identity: `MRJ:synthetic_${index}`, anatomy: [], laterality: 'MISSING',
      numerator: 1, denominator: 8, value: 0.125 })));
  const longPanel = run('renderVisualizationPanel(longFixture)');
  assert.match(longPanel.textContent, /Very long synthetic finding label/);
  assert.match(longPanel.textContent, /Show 2 more analysis rows/);
  assert.equal(longPanel.children.some(child => child.tagName === 'details'), true);
  const firstBar = longPanel.children.find(child => child.tagName === 'ol').children[0].children[1];
  assert.equal(firstBar.tagName, 'progress');
  assert.equal(firstBar.max, 1);
  assert.equal(firstBar.value, 0.125);
  assert.match(firstBar.attributes['aria-label'], /1 \/ 8 included reports.*scale starts at zero/);
  const css = fs.readFileSync(path.join(root, 'frontend/understanding-styles.css'), 'utf8');
  assert.match(css, /\.visualize-panels.*minmax\(min\(100%, 390px\), 1fr\)/);
  assert.match(css, /\.visualize-table-wrap.*overflow-x: auto/);
  assert.equal(read('continueIndicatorsBtn').hidden, false);
  context.savedAnalysis = run('analysisResult');
  run('analysisResult = null');
  await read('continueIndicatorsBtn').click();
  assert.equal(requests.filter(([url]) => url.endsWith('/indicators')).at(-1)[0],
    `/api/v1/understanding/analysis-runs/${visualization.analysis_run_id}/indicators`);
  run('analysisResult = savedAnalysis');
  assert.equal(run('activeJourneyStage'), 'INDICATORS');
  assert.equal(read('activeStageNumber').textContent, '07');
  assert.equal(read('indicatorsCard').hidden, false);
  assert.equal(read('visualizeCard').hidden, true);
  assert.match(read('railIndicators').textContent, /Needs Review/);
  assert.match(read('indicatorsContext').textContent, /Synthetic validation collection.*version 1.*AnalysisRun/);
  assert.match(read('indicatorsPolicy').textContent, /VALIDATION ONLY.*does not imply human clinical review/);
  assert.match(read('indicatorsReadiness').textContent, /VALIDATION_ONLY: 5.*NOT_READY: 1/);
  assert.match(read('indicatorSections').textContent, /Cerebral atrophy.*1 \/ 8 included reports.*12.5%/);
  assert.match(read('indicatorSections').textContent, /Metastatic tumor FAVORED/);
  assert.match(read('indicatorSections').textContent, /Documented absence: aspiration/);
  assert.match(read('indicatorSections').textContent, /Report service date coverage.*0 \/ 8 included reports.*0%/);
  assert.match(read('indicatorSections').textContent, /Whole-fact MATCHED coverage.*3 \/ 55 canonical facts/);
  assert.match(read('indicatorSections').textContent, /Comparable measurement summary.*NOT READY.*— \/ 8 included reports/);
  assert.match(read('indicatorsTechnicalBody').textContent, /IndicatorRun.*AnalysisRun.*Collection/);
  assert.equal(read('indicatorsTechnical').attributes.open, undefined);
  assert.match(css, /\.indicator-list.*minmax\(min\(100%, 320px\), 1fr\)/);
  read('returnVisualizeBtn').click();
  assert.equal(run('activeJourneyStage'), 'VISUALIZE');
  assert.equal(read('visualizeCard').hidden, false);
  assert.equal(read('indicatorsCard').hidden, true);
  run('indicatorRun = null');
  indicatorErrorDetail = 'Not Found';
  await read('continueIndicatorsBtn').click();
  assert.match(read('indicatorsMessage').textContent, /INDICATORS is unavailable in the running server/);
  assert.equal(read('indicatorSections').textContent, '');
  read('returnVisualizeBtn').click();
  indicatorErrorDetail = 'SOURCE_ANALYSIS_NOT_AVAILABLE';
  await read('continueIndicatorsBtn').click();
  assert.match(read('indicatorsMessage').textContent, /Source AnalysisRun could not be loaded/);
  read('returnVisualizeBtn').click();
  indicatorErrorDetail = null;
  await read('continueIndicatorsBtn').click();
  assert.match(read('indicatorsReadiness').textContent, /VALIDATION_ONLY: 5.*NOT_READY: 1/);
  assert.match(read('indicatorSections').textContent, /Cerebral atrophy/);
  read('returnVisualizeBtn').click();
  read('returnAnalyzeBtn').click();
  assert.equal(run('activeJourneyStage'), 'ANALYZE');
  assert.equal(read('analyzeCard').hidden, false);
  assert.equal(read('visualizeCard').hidden, true);
  read('returnStandardizeBtn').click();
  assert.equal(run('activeJourneyStage'), 'STANDARDIZE');
  assert.equal(read('standardizeCard').hidden, false);
})().catch(error => { console.error(error); process.exitCode = 1; });
