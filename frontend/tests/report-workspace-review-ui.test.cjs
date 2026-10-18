const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const read = name => fs.readFileSync(path.join(__dirname, '..', name), 'utf8');
const html = read('reports.html');
const script = read('reports.js');
const workspaceCss = read('report-workspace.css');
const shellCss = read('product-shell.css');

test('Major Review appears before its action, with a separate explicit confirmation', () => {
  assert.ok(html.indexOf('id="review-section"') < html.indexOf('id="accept-record"'));
  assert.match(html, /id="major-review-message">This record contains a major review issue\. Confirm that you reviewed the source evidence before accepting\./);
  assert.match(html, /id="cancel-major-acceptance"[^>]*>Cancel</);
  assert.match(html, /id="confirm-major-acceptance"[^>]*>Confirm acceptance</);
  assert.match(workspaceCss, /\.record-actions\[data-major-review="true"\]\s*\{\s*position:\s*static;/);
  assert.match(script, /if \(model\.acceptancePolicy\(entry\.record, entries\.length\)\.confirmMajor\)/);
  assert.match(script, /entry\.key !== majorConfirmationKey/);
});

test('completion has Back to Reports first and primary, with working secondary actions', () => {
  const actions = html.match(/<div class="completion-actions">([\s\S]*?)<\/div>/)?.[1] || '';
  assert.match(actions, /^\s*<button id="back-to-reports" class="product-action"/);
  assert.ok(actions.indexOf('id="back-to-reports"') < actions.indexOf('id="review-again"'));
  assert.ok(actions.indexOf('id="review-again"') < actions.indexOf('id="analyze-reports"'));
  assert.match(actions, /id="review-again" class="product-text-button"/);
  assert.match(actions, /id="analyze-reports" class="product-text-button"/);
  assert.match(script, /byId\('review-again'\)\.addEventListener\('click',[\s\S]*?selectEntry\(next\)/);
  assert.match(script, /creation_method: 'REVIEW_SESSION'/);
  assert.match(script, /model\.reviewedCollectionMembers\(entries\)/);
  assert.match(script, /const complete = showCompletion && model\.completionEligible\(entries\)/);
});

test('skip link stays offscreen until focus and remains keyboard reachable', () => {
  assert.match(html, /<a class="product-skip-link" href="#main">Skip to content<\/a>/);
  assert.match(shellCss, /\.product-skip-link\s*\{[^}]*top:\s*-100px;/);
  assert.match(shellCss, /\.product-skip-link:focus\s*\{[^}]*top:\s*12px;/);
});

test('exam coverage and profile details use the accepted record layout', () => {
  assert.ok(html.indexOf('id="exam-coverage-section"') > html.indexOf('id="review-section"'));
  assert.match(html, /id="view-profile-details"/);
  assert.match(html, /id="profile-dialog"/);
  assert.match(script, /byId\('exam-coverage-section'\)\.hidden = !record\.profile/);
  assert.match(script, /byId\('profile-dialog'\)\.showModal\(\)/);
});

test('comparison mode keeps Native, complete MedGemma, and comparison in separate ordered sections', () => {
  assert.ok(html.indexOf('id="native-evaluation-section"') < html.indexOf('id="medgemma-section"'));
  assert.ok(html.indexOf('id="medgemma-section"') < html.indexOf('id="comparison-section"'));
  assert.match(html, /id="comparison-mode-indicator"[^>]*>Comparison Mode/);
  assert.match(script, /renderMedGemmaMarkdown\(status === 'AVAILABLE' \? evaluation\.raw_response/);
  assert.match(script, /const comparisonNames = \{ AGREEMENT:/);
  assert.match(script, /'No matching supported MedGemma claim'/);
  assert.match(script, /startComparison\(entry\)/);
  assert.match(script, /setTimeout\(\(\) => pollComparison\(entry\), 2500\)/);
  assert.match(script, /async function loadRetainedComparisonRun\(\)/);
  assert.match(script, /retainedPreview: true/);
  assert.match(script, /'Retained Comparison Mode results · read-only · no extraction started\.'/);
  assert.match(script, /UNSUPPORTED: 'Unsupported'/);
});
