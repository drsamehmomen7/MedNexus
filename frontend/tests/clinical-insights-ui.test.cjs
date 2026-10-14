const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'collections.html'), 'utf8');
const script = fs.readFileSync(path.join(__dirname, '..', 'collections.js'), 'utf8');
const css = fs.readFileSync(path.join(__dirname, '..', 'collections.css'), 'utf8');
const id = 'a'.repeat(32), analysisId = 'b'.repeat(32), insightId = 'c'.repeat(32);

class Element {
  constructor(tag = 'div') {
    this.tagName = tag; this._text = ''; this.children = []; this.dataset = {};
    this.style = {}; this.attributes = {}; this.handlers = {}; this.hidden = false;
    this.className = ''; this.isConnected = true; this.open = false;
    this.classList = { add: () => {}, remove: () => {} };
  }
  set textContent(value) { this._text = String(value ?? ''); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent ?? String(child)).join(''); }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; this._text = ''; }
  addEventListener(name, handler) { this.handlers[name] = handler; }
  setAttribute(name, value) { this.attributes[name] = value; }
  removeAttribute(name) { delete this.attributes[name]; }
  focus() {}
  showModal() { this.open = true; }
  close() { this.open = false; }
  click() { return this.handlers.click?.(); }
}

const descendants = (root, predicate) => {
  const found = [];
  const visit = node => {
    if (!(node instanceof Element)) return;
    if (predicate(node)) found.push(node);
    node.children.forEach(visit);
  };
  visit(root);
  return found;
};
const tick = async () => {
  for (let i = 0; i < 5; i++) await new Promise(resolve => setImmediate(resolve));
};
const group = (groupId, label, numerator, denominator, barPercent) => ({
  group_id: groupId, label, numerator, denominator, bar_percent: barPercent, contributors: []
});
const definition = (name, state, groups, title = name, verified = false) => ({
  insight_id: name, definition_version: '0.1', title, question: 'Governed clinical question?',
  insight_type: 'CO_DOCUMENTATION', state, analysis_level: 'REPORT', eligible_n: 8,
  event_support: 3, groups, summary: state === 'INSUFFICIENT_DATA' ?
    'Not enough eligible reviewed reports under the current MRJ support policy.' :
    'In this Collection, findings were documented in eligible reviewed reports.',
  support_policy: { minimum_eligible_n: 6, minimum_group_n: 2, minimum_event_support: 2,
                    policy_role: 'MRJ_POLICY', policy_label: 'MRJ V1 descriptive support policy' },
  eligibility_rule: 'Only explicit reviewed assertions qualify.',
  denominator_rule: 'Question-specific eligible reports.',
  exam_profile_reference: { organization: 'ACR', title: 'Abdominal ultrasound practice parameter',
                            url: 'https://www.acr.org/reference', role: 'EXAM_PROFILE_REFERENCE' },
  clinical_relationship_reference: verified ?
    { organization: 'Primary study', title: 'Verified MRI relationship study',
      url: 'https://pubmed.ncbi.nlm.nih.gov/16768763/', role: 'CLINICAL_RELATIONSHIP_REFERENCE' } : null,
  relationship_reference_status: verified ? 'VERIFIED' : 'PENDING_VERIFICATION',
  limitations: 'Descriptive report-level observation only.'
});

async function launch() {
  const elements = Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)]
    .map(match => [match[1], new Element()]));
  const tabs = ['overview', 'findings', 'measurements', 'insights', 'trends', 'quality']
    .map(name => { const item = new Element('button'); item.dataset.tab = name; return item; });
  const panels = tabs.map(tab => { const item = elements['tab-' + tab.dataset.tab]; item.id = 'tab-' + tab.dataset.tab; return item; });
  const calls = [];
  const insight = {
    insight_run_id: insightId, analysis_run_id: analysisId, collection_id: id, collection_version: 1,
    summary: { relationships_evaluated: 3, OBSERVATION_AVAILABLE: 1, INSUFFICIENT_DATA: 1,
               NO_CLEAR_DESCRIPTIVE_PATTERN: 1, NOT_APPLICABLE: 0, UNAVAILABLE: 0 },
    unsupported_profile_records: 0,
    profiles: [
      { intelligence_profile_id: 'MRJ_INTEL_US_ABDOMEN', intelligence_profile_version: '0.1',
        clinical_profile_id: 'MRJ_RAD_US_ABDOMEN', compatible_reviewed_reports: 8, definitions: [
          definition('US_HEPATOMEGALY_ASCITES', 'OBSERVATION_AVAILABLE',
            [group('with', 'With hepatomegaly', 2, 4, 37.5), group('without', 'Explicitly without hepatomegaly', 1, 4, 25)],
            'Hepatomegaly + ascites'),
          definition('US_RENAL_CALCULUS_HYDRONEPHROSIS', 'INSUFFICIENT_DATA',
            [group('with', 'With renal calculus', 1, 2, 50)], 'Renal calculus + hydronephrosis')
        ] },
      { intelligence_profile_id: 'MRJ_INTEL_MRI_SHOULDER', intelligence_profile_version: '0.1',
        clinical_profile_id: 'MRJ_RAD_MRI_SHOULDER', compatible_reviewed_reports: 3, definitions: [
          definition('MRI_LABRAL_TEAR_HILL_SACHS', 'NO_CLEAR_DESCRIPTIVE_PATTERN',
            [group('with', 'With labral tear', 2, 3, 66.67)], 'Labral tear + Hill-Sachs', true)
        ] }
    ]
  };
  const collection = { collection_id: id, name: 'Synthetic reviewed collection', version: 1,
                       member_count: 8, state: 'READY_FOR_ANALYSIS', exam_types: [],
                       updated_at: '2030-01-01T00:00:00Z' };
  const analysis = { analysis_run_id: analysisId, collection_id: id,
    collection_summary: { included_reports: 8 }, finding_frequencies: [],
    measurement_distributions: [], stratifications: [], data_quality: { profile_coverage: [] },
    standardization_coverage: { denominator_facts: 0 } };
  const fetch = async (url, options = {}) => {
    calls.push({ url, method: options.method || 'GET' });
    const payload = url.endsWith('/reviewed-collections') ? { collections: [collection] } :
      url.endsWith('/reviewed-collections/' + id) ? collection :
      url.includes('/analyze') ? analysis :
      url.includes('/insights?') ? insight :
      url.includes('/contributors') ? {
        contributors: [{ exam_context: { normalized_modality: 'US', normalized_body_region: 'ABDOMEN' },
          reviewed_record_version: 1, event: true,
          facts: [{ fact_label: 'Hepatomegaly', quote: 'Synthetic protected evidence.' }] }]
      } : {};
    return { ok: true, json: async () => payload };
  };
  const document = { getElementById: name => elements[name], createElement: tag => new Element(tag),
    querySelectorAll: selector => selector === '.collection-tabs button' ? tabs :
      selector === '.collection-tab-panel' ? panels : [] };
  const context = { document, fetch, window: { location: { hash: '', pathname: '/collections' },
    history: { replaceState() {} } }, console, Date, Intl, URL };
  vm.runInNewContext(script, context);
  await tick();
  const open = descendants(elements['collection-list'], element =>
    element.tagName === 'button' && element.textContent === 'Open →')[0];
  assert.ok(open); open.click(); await tick();
  tabs.find(tab => tab.dataset.tab === 'insights').click(); await tick();
  return { elements, tabs, calls };
}

test('Insights uses real backend run and retains governed profile order and abstention card', async () => {
  const { elements, calls } = await launch();
  assert.ok(calls.some(call => call.url.includes('/insights?version=1') && call.method === 'POST'),
    JSON.stringify({ calls, error: elements['collection-error'].textContent,
      status: elements['insights-status'].textContent }));
  assert.match(elements['insights-groups'].textContent, /Hepatomegaly \+ ascites/);
  assert.match(elements['insights-groups'].textContent, /Renal calculus \+ hydronephrosis/);
  assert.match(elements['insights-groups'].textContent, /Insufficient data/);
  assert.ok(elements['insights-groups'].textContent.indexOf('Hepatomegaly + ascites') <
    elements['insights-groups'].textContent.indexOf('Renal calculus + hydronephrosis'));
  assert.match(elements['insights-groups'].textContent, /Ultrasound abdomen Insights/);
  assert.match(elements['insights-groups'].textContent, /MRI shoulder Insights/);
  assert.match(elements['insights-stats'].textContent, /Questions/);
  assert.match(elements['insights-stats'].textContent, /Observations/);
});

test('bars use backend presentation percentage and show backend n/N without relational calculation', async () => {
  const { elements } = await launch();
  const fills = descendants(elements['insights-groups'], item => item.className === 'insight-bar-fill');
  assert.equal(fills[0].style.width, '37.5%');
  assert.match(elements['insights-groups'].textContent, /2 \/ 4/);
  assert.match(elements['insights-groups'].textContent, /1 \/ 4/);
  assert.doesNotMatch(html, /4 \/ 6|1 \/ 12|16 \/ 20/);
});

test('contributor and Why this insight panels use protected backend evidence and collapsed provenance', async () => {
  const { elements, calls } = await launch();
  const card = descendants(elements['insights-groups'], item =>
    item.className === 'insight-card' && item.textContent.includes('Hepatomegaly + ascites'))[0];
  const report = descendants(card, item => item.tagName === 'button' &&
    item.textContent.includes('View with hepatomegaly reports'))[0];
  assert.ok(report); report.click(); await tick();
  assert.ok(calls.some(call => call.url.endsWith('/US_HEPATOMEGALY_ASCITES/with/contributors')));
  assert.match(elements['insights-contributors'].textContent, /Synthetic protected evidence/);
  assert.match(elements['insights-why'].textContent, /Clinical question/);
  assert.match(elements['insights-why'].textContent, /Eligibility rule/);
  assert.match(elements['insights-why'].textContent, /Numerator \/ denominator/);
  assert.match(elements['insights-why'].textContent, /Reference basis/);
  assert.match(elements['insights-why'].textContent, /Exam\/profile basis/);
  assert.match(elements['insights-why'].textContent, /Clinical relationship basis/);
  assert.match(elements['insights-why'].textContent, /Pending verification/);
  assert.match(elements['insights-why'].textContent,
    /References justify why MRJ defines this question; they do not validate the result observed in this Collection\./);
  assert.match(elements['insights-why'].textContent, /Limitations/);
  const details = descendants(elements['insights-why'], item => item.tagName === 'details')[0];
  assert.ok(details && !details.open);
});

test('verified clinical relationship source is separate from the exam basis', async () => {
  const { elements } = await launch();
  const card = descendants(elements['insights-groups'], item =>
    item.className === 'insight-card' && item.textContent.includes('Labral tear + Hill-Sachs'))[0];
  const why = descendants(card, item => item.tagName === 'button' && item.textContent === 'Why this insight?')[0];
  why.click();
  assert.match(elements['insights-why'].textContent, /Exam\/profile basis/);
  assert.match(elements['insights-why'].textContent, /Clinical relationship basis/);
  assert.match(elements['insights-why'].textContent, /Verified MRI relationship study/);
  assert.doesNotMatch(elements['insights-why'].textContent, /Pending verification/);
});

test('insufficient state names MRJ descriptive support policy without reliability language', async () => {
  const { elements } = await launch();
  const card = descendants(elements['insights-groups'], item =>
    item.className === 'insight-card' && item.textContent.includes('Renal calculus + hydronephrosis'))[0];
  assert.match(card.textContent, /Not enough eligible reviewed reports under the current MRJ support policy/);
  assert.match(card.textContent, /MRJ V1 descriptive support policy requires 6/);
  assert.doesNotMatch(card.textContent, /reliab|statistical|significant|prevalence|risk|caus/i);
});

test('accepted dashboard shell has real Insight surfaces and no Phase E placeholder', () => {
  assert.match(html, /id="insights-groups"/);
  assert.match(html, /id="insights-contributors"/);
  assert.match(html, /id="insights-why"/);
  assert.doesNotMatch(html, /No relationship results have been calculated/);
  assert.match(css, /\.insights-layout\s*\{[^}]*grid-template-columns:/);
  assert.match(script, /bar_percent/);
});
