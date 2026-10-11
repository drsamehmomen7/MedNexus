const test = require('node:test');
const assert = require('node:assert/strict');
const { prepareReport, ProcessingIssue } = require('../report-workspace-flow.js');

const response = value => ({ ok: true, json: async () => value });
const file = () => new Blob(['Synthetic radiology report.'], { type: 'text/plain' });
const item = (id, order, through) => ({
  document_id: id, order,
  stage_status: Object.fromEntries(['UNDERSTAND', 'PROTECT', 'EXTRACT', 'STANDARDIZE'].map(stage =>
    [stage, { status: ['UNDERSTAND', 'PROTECT', 'EXTRACT', 'STANDARDIZE'].indexOf(stage) <=
      ['UNDERSTAND', 'PROTECT', 'EXTRACT', 'STANDARDIZE'].indexOf(through) ? 'NEEDS_REVIEW' : 'NOT_STARTED' }])),
  stage_results: {},
});

test('one upload automatically runs the established endpoints in order', async () => {
  const id = 'a'.repeat(32);
  const runId = 'b'.repeat(32);
  const calls = [];
  const stages = [];
  const outputs = [
    { journey: { run_id: runId }, document_context: { document: { document_id: id } } },
    { documents: [item(id, 0, 'UNDERSTAND')] },
    { documents: [item(id, 0, 'PROTECT')] },
    { documents: [item(id, 0, 'EXTRACT')] },
    { documents: [item(id, 0, 'STANDARDIZE')] },
  ];
  const fetchImpl = async (url, options = {}) => {
    calls.push({ url, options });
    return response(outputs.shift());
  };
  const prepared = await prepareReport({ file: file(), fetchImpl,
    onUpdate: update => stages.push(update.stage) });
  assert.equal(prepared.documentId, id);
  assert.deepEqual(stages, ['UNDERSTAND', 'PROTECT', 'EXTRACT', 'STANDARDIZE']);
  assert.deepEqual(calls.map(call => call.url.split('/').pop()),
    ['analyze-file', runId, 'protect', 'extract', 'standardize']);
  assert.deepEqual(JSON.parse(calls[2].options.body).document_ids, [id]);
  assert.equal(calls[3].options.body, undefined);
});

test('two files in one batch keep independent document IDs and protection calls', async () => {
  const runId = 'c'.repeat(32);
  const ids = ['d'.repeat(32), 'e'.repeat(32)];
  const calls = [];
  const fetchImpl = async (url, options = {}) => {
    calls.push({ url, options });
    const order = url.endsWith('/documents') ? Number(options.body.get('order')) :
      url.includes(ids[1]) || calls.some(call => call.url.endsWith('/documents') &&
        call.options.body.get('order') === '1') ? 1 : 0;
    const stage = url.endsWith('/documents') ? 'UNDERSTAND' :
      url.endsWith('/protect') ? 'PROTECT' :
        url.endsWith('/extract') ? 'EXTRACT' : 'STANDARDIZE';
    return response({ documents: [item(ids[order], order, stage)] });
  };
  const first = await prepareReport({ file: file(), batchRunId: runId, order: 0, fetchImpl });
  const second = await prepareReport({ file: file(), batchRunId: runId, order: 1, fetchImpl });
  assert.notEqual(first.documentId, second.documentId);
  assert.equal(calls.filter(call => call.url.endsWith('/documents')).length, 2);
  assert.deepEqual(calls.filter(call => call.url.endsWith('/protect'))
    .map(call => JSON.parse(call.options.body).document_ids), [[ids[0]], [ids[1]]]);
  assert.equal(calls.filter(call => call.url.endsWith('/standardize')).length, 2);
});

test('a failed stage stops the automatic journey before claiming readiness', async () => {
  const runId = 'f'.repeat(32);
  const id = '1'.repeat(32);
  const calls = [];
  const fetchImpl = async url => {
    calls.push(url);
    if (url.endsWith('/documents')) return response({ documents: [item(id, 0, 'UNDERSTAND')] });
    return response({ documents: [{ ...item(id, 0, 'UNDERSTAND'),
      stage_status: { ...item(id, 0, 'UNDERSTAND').stage_status, PROTECT: { status: 'FAILED' } } }] });
  };
  await assert.rejects(prepareReport({ file: file(), batchRunId: runId, fetchImpl }),
    error => error instanceof ProcessingIssue && error.stage === 'PROTECT');
  assert.equal(calls.length, 2);
});
