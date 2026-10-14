(() => {
  'use strict';
  const base = '/api/v1/understanding';
  const el = id => document.getElementById(id);
  const validId = id => typeof id === 'string' && /^[0-9a-f]{32}$/.test(id);
  const count = n => Number.isInteger(n) && n >= 0 ? n : 0;
  const plural = (n, noun) => `${count(n)} ${noun}${n === 1 ? '' : 's'}`;
  const node = (tag, value, className) => {
    const item = document.createElement(tag);
    item.textContent = String(value ?? '');
    if (className) item.className = className;
    return item;
  };
  const clear = id => { el(id).replaceChildren(); return el(id); };
  const profile = id => ({ MRJ_RAD_US_ABDOMEN: 'Ultrasound abdomen', MRJ_RAD_MRI_SHOULDER: 'MRI shoulder' }[id] ||
    String(id || 'General radiology').replaceAll('_', ' ').toLowerCase().replace(/^./, c => c.toUpperCase()));
  const examLabel = item => [item.modality, item.body_region].filter(value => value && value !== 'UNKNOWN')
    .map(value => ({ MRI: 'MRI', CT: 'CT', US: 'Ultrasound', ULTRASOUND: 'Ultrasound' }[value] ||
      String(value).toLowerCase().replace(/^./, c => c.toUpperCase()))).join(' · ') || 'Exam type unavailable';
  const concept = metric => metric.display_label || String(metric.concept_identity || 'Clinical measurement')
    .split(':').slice(-4).join(' ').replaceAll('_', ' ');
  const elementLabel = id => ({ ivc: 'IVC', ac_joint: 'AC joint' }[String(id).toLowerCase()] ||
    String(id).replaceAll('_', ' '));
  const coverageSummary = item => item.denominator === 0 ? 'Out of scope' :
    item.documented === item.denominator ? `Documented ${item.documented}/${item.denominator}` :
    item.limited === item.denominator ? `Limited ${item.limited}/${item.denominator}` :
    item.not_documented === item.denominator ? `Not documented ${item.not_documented}/${item.denominator}` :
    `Mixed coverage · ${item.denominator} eligible`;
  let current = null, analysis = null, openingButton = null;
  async function request(path, options = {}) {
    const response = await fetch(base + path, { cache: 'no-store', ...options });
    if (!response.ok) throw new Error('Collection request failed');
    const result = await response.json();
    if (!result || typeof result !== 'object') throw new Error('Invalid collection response');
    return result;
  }
  function showError(message) { el('collection-error').textContent = message; el('collection-error').hidden = !message; }
  function empty(parent, message) { parent.append(node('p', message, 'collection-empty-message')); }
  function mini(parent, title, value) {
    const row = node('div', '', 'collection-mini-row');
    row.append(node('span', title), node('strong', value));
    parent.append(row);
  }
  function frequencyBar(parent, numerator, denominator) {
    const track = node('div', '', 'frequency-track');
    const fill = node('span', '', 'frequency-fill');
    fill.style.width = `${denominator > 0 ? Math.min(100, Math.max(0, numerator / denominator * 100)) : 0}%`;
    track.setAttribute('aria-hidden', 'true');
    track.append(fill); parent.append(track);
  }
  const ratio = metric => `${count(metric.numerator)} / ${count(metric.denominator)} reports`;
  function switchTab(name) {
    document.querySelectorAll('.collection-tabs button').forEach(button => {
      if (button.dataset.tab === name) button.setAttribute('aria-current', 'page');
      else button.removeAttribute('aria-current');
    });
    document.querySelectorAll('.collection-tab-panel').forEach(panel => { panel.hidden = panel.id !== 'tab-' + name; });
  }
  function renderOverview() {
    const summary = analysis.collection_summary || {};
    const stats = clear('overview-stats');
    [['▤', 'Reviewed reports', current.member_count], ['✓', 'Included in analysis', summary.included_reports],
      ['≡', 'Finding groups', analysis.finding_frequencies.length],
      ['◫', 'Measurement groups', analysis.measurement_distributions.length]].forEach(([icon, title, value]) => {
      const item = node('div', '', 'overview-stat');
      const symbol = node('span', icon, 'overview-stat-icon');
      symbol.setAttribute('aria-hidden', 'true');
      const copy = node('div', '', 'overview-stat-copy');
      copy.append(node('strong', count(value)), node('span', title));
      item.append(symbol, copy);
      stats.append(item);
    });
    const findings = clear('overview-findings');
    const top = analysis.finding_frequencies.slice(0, 5);
    if (!top.length) empty(findings, 'No documented findings among eligible reviewed reports.');
    top.forEach(metric => {
      const row = node('div', '', 'overview-finding');
      const heading = node('div', '', 'overview-finding-heading');
      heading.append(node('strong', metric.display_label), node('span', ratio(metric)));
      row.append(heading); frequencyBar(row, metric.numerator, metric.denominator);
      findings.append(row);
    });
    const composition = clear('overview-composition');
    const exams = (analysis.stratifications || []).filter(item => item.dimension === 'modality');
    if (!exams.length) empty(composition, 'Exam composition is unavailable.');
    exams.forEach(metric => {
      const label = metric.category === 'MISSING' ? 'Exam type unavailable' :
        ({ ULTRASOUND: 'Ultrasound', US: 'Ultrasound', MRI: 'MRI', CT: 'CT' }[metric.category] || metric.category);
      mini(composition, label, ratio(metric));
    });
    if (exams.length === 1) composition.classList.add('composition-single');
    else composition.classList.remove('composition-single');
    const measures = clear('overview-measurements');
    const samples = analysis.measurement_distributions.slice(0, 4);
    if (!samples.length) empty(measures, 'No comparable governed measurements are available.');
    samples.forEach(metric => mini(measures, concept(metric), plural(metric.sample_count, 'value')));
    const quality = clear('overview-quality');
    mini(quality, 'Records without coverage snapshot', count(analysis.data_quality?.records_without_coverage_snapshot));
    mini(quality, 'Review alerts', count(analysis.data_quality?.review_alert_reports));
    mini(quality, 'Eligible for analysis', `${count(summary.included_reports)} / ${count(current.member_count)}`);
    const sections = (analysis.data_quality?.profile_coverage || [])
      .filter(item => !item.element_id.includes('.'))
      .sort((a, b) => Number(b.denominator > 0) - Number(a.denominator > 0));
    if (sections.length) {
      quality.append(node('h3', 'Exam coverage', 'overview-coverage-heading'));
      sections.slice(0, 6).forEach(item => mini(quality,
        `${profile(item.profile_id)} · ${elementLabel(item.element_id)}`,
        coverageSummary(item)));
      const button = node('button', 'View full coverage →', 'product-text-button');
      button.type = 'button'; button.addEventListener('click', () => switchTab('quality'));
      quality.append(button);
    }
  }
  function table(targetId, headers) {
    const wrap = node('div', '', 'metric-table-wrap');
    const table = node('table', '', 'metric-table');
    const head = document.createElement('thead'), tr = document.createElement('tr');
    headers.forEach(value => tr.append(node('th', value)));
    head.append(tr);
    const body = document.createElement('tbody');
    table.append(head, body); wrap.append(table); clear(targetId).append(wrap);
    return body;
  }
  async function drilldown(kind, index, heading) {
    try {
      const result = await request(`/reviewed-collection-analyses/${analysis.analysis_run_id}/${kind}/${index}/contributors`);
      el('drilldown-title').textContent = heading;
      el('drilldown-summary').textContent =
        `${kind === 'measurements' ? `${plural(result.metric.sample_count, 'governed value')} · ` : ''}${ratio(result.metric)} · ${plural(result.contributors.length, 'contributing reviewed fact')} · protected evidence`;
      const target = clear('drilldown-reports');
      if (!result.contributors.length) empty(target, 'No verified contributing evidence is available.');
      result.contributors.forEach((item, reportIndex) => {
        const context = item.exam_context || {};
        const card = node('article', '', 'contributor');
        card.append(node('h3', `Reviewed report ${reportIndex + 1}: ${item.fact_label || 'Reviewed finding'}`),
          node('p', [context.normalized_modality, context.normalized_body_region,
            context.normalized_laterality].filter(value => value && value !== 'MISSING').join(' · ') ||
            'Exam metadata unavailable'));
        (item.measurements || []).forEach(measure => card.append(node('p',
          `Original: ${measure.original_text || 'Unavailable'} · Governed: ${measure.normalized_value ?? 'Unavailable'} ${measure.normalized_unit || ''}`)));
        card.append(node('blockquote', item.evidence?.quote || 'Evidence unavailable'));
        target.append(card);
      });
      el('collection-drilldown').showModal();
    } catch { showError('Source evidence could not be opened. Please try again.'); }
  }
  function renderFindings() {
    const rows = analysis.finding_frequencies;
    if (!rows.length) { empty(clear('findings-results'), 'No documented findings among eligible reviewed records.'); return; }
    const body = clear('findings-results');
    body.className = 'finding-list';
    rows.forEach((metric, index) => {
      const row = node('article', '', 'finding-row');
      const marker = node('span', '', 'finding-marker'); marker.setAttribute('aria-hidden', 'true');
      const copy = node('div', '', 'finding-copy');
      copy.append(node('h3', metric.display_label));
      const context = [...(metric.anatomy || []),
        metric.laterality && metric.laterality !== 'MISSING' ? metric.laterality : null].filter(Boolean);
      if (context.length) copy.append(node('p', context.join(' · '), 'finding-context'));
      const aside = node('div', '', 'finding-frequency');
      aside.append(node('strong', `${count(metric.numerator)} / ${count(metric.denominator)}`),
        node('span', 'eligible reviewed reports'));
      frequencyBar(aside, metric.numerator, metric.denominator);
      const button = node('button', 'View reports →', 'collection-link');
      button.type = 'button';
      button.addEventListener('click', () => drilldown('findings', index, metric.display_label));
      row.append(marker, copy, aside, button); body.append(row);
    });
  }
  function renderMeasurements() {
    const rows = analysis.measurement_distributions;
    if (!rows.length) { empty(clear('measurement-results'), 'No comparable governed measurements are available.'); return; }
    const body = clear('measurement-results');
    body.className = 'measurement-list';
    rows.forEach((metric, index) => {
      const row = node('article', '', 'measurement-row');
      const icon = node('span', '◫', 'measurement-icon'); icon.setAttribute('aria-hidden', 'true');
      const copy = node('div', '', 'measurement-copy');
      copy.append(node('h3', concept(metric)), node('p',
        `${metric.measurement_type.replaceAll('_', ' ').toLowerCase()} · ${profile(metric.profile_context)} · ${plural(metric.sample_count, 'value')} from ${ratio(metric)}`));
      const values = node('div', '', 'measurement-values');
      values.append(node('strong', `${metric.median} ${metric.normalized_unit}`),
        node('span', metric.sample_count === 1 ? 'Observed value' : 'Median'));
      if (metric.sample_count > 1) values.append(node('small',
        `Range ${metric.minimum}–${metric.maximum} ${metric.normalized_unit}`));
      const button = node('button', 'View reports →', 'collection-link');
      button.type = 'button';
      button.addEventListener('click', () => drilldown('measurements', index, concept(metric)));
      row.append(icon, copy, values, button); body.append(row);
    });
  }
  function renderQuality() {
    const target = clear('quality-results'), quality = analysis.data_quality || {};
    const withoutSnapshot = count(quality.records_without_coverage_snapshot);
    target.append(node('p', withoutSnapshot ?
      `${plural(withoutSnapshot, 'reviewed record')} without an accepted profile coverage snapshot. Their coverage is unavailable, not inferred.` :
      'Every reviewed record has an accepted profile coverage snapshot.', 'collection-note'));
    const standard = analysis.standardization_coverage || {};
    const intro = node('div', '', 'quality-summary');
    mini(intro, 'Governed whole-fact matches', `${count(standard.whole_fact_matched)} / ${count(standard.denominator_facts)} facts`);
    mini(intro, 'Standardization needs review', count(standard.needs_review));
    mini(intro, 'Unclassified measurements', count(analysis.measurement_coverage?.unclassified_measurements));
    mini(intro, 'Review alerts', count(quality.review_alert_reports));
    mini(intro, 'Eligible reports', `${count(analysis.collection_summary?.included_reports)} / ${count(current.member_count)}`);
    target.append(intro);
    const groups = new Map();
    (quality.profile_coverage || []).forEach(item => {
      const key = `${profile(item.profile_id)} · profile version ${item.profile_version}`;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(item);
    });
    if (!groups.size) { empty(target, 'No accepted profile coverage snapshots are available.'); return; }
    for (const [name, items] of groups) {
      const section = node('section', '', 'quality-group');
      section.append(node('h3', name));
      const strip = node('div', '', 'quality-strip');
      items.filter(item => !item.element_id.includes('.')).forEach(item => {
        const card = node('div', '', 'quality-strip-item');
        card.append(node('strong', elementLabel(item.element_id)), node('span', coverageSummary(item)));
        card.dataset.coverage = item.denominator === 0 ? 'OUT_OF_SCOPE' :
          item.documented === item.denominator ? 'DOCUMENTED' :
            item.limited === item.denominator ? 'LIMITED' :
              item.not_documented === item.denominator ? 'NOT_DOCUMENTED' : 'MIXED';
        strip.append(card);
      });
      section.append(strip);
      const details = document.createElement('details');
      details.className = 'quality-details';
      details.append(node('summary', 'View element-level coverage'));
      const wrap = node('div', '', 'metric-table-wrap'), table = node('table', '', 'quality-table');
      const head = document.createElement('thead'), tr = document.createElement('tr');
      ['Exam element', 'Documented', 'Limited', 'Not documented', 'Eligible reports', 'Out of scope'].forEach(value => tr.append(node('th', value)));
      head.append(tr); table.append(head);
      const body = document.createElement('tbody');
      items.forEach(item => {
        const row = document.createElement('tr');
        [elementLabel(item.element_id).replaceAll('.', ' · '), item.documented, item.limited,
          item.not_documented, item.denominator, item.not_applicable].forEach(value => row.append(node('td', value)));
        body.append(row);
      });
      table.append(body); wrap.append(table); details.append(wrap); section.append(details); target.append(section);
    }
  }
  function renderAnalysis() {
    renderOverview(); renderFindings(); renderMeasurements(); renderQuality();
    el('collection-detail-summary').textContent = [
      plural(current.member_count, 'reviewed report'),
      `${count(analysis.collection_summary.included_reports)} eligible for analysis`,
      ...(current.exam_types || []).map(examLabel),
    ].join('  ·  ');
  }
  async function openCollection(id, button = null) {
    showError('');
    el('collections-status').textContent = 'Opening collection…';
    try {
      const collection = await request('/reviewed-collections/' + id);
      if (!validId(collection.collection_id) || collection.collection_id !== id) throw new Error('Invalid collection');
      const result = await request(`/reviewed-collections/${id}/analyze`, { method: 'POST' });
      if (!validId(result.analysis_run_id) || result.collection_id !== id) throw new Error('Invalid analysis');
      current = collection; analysis = result; openingButton = button;
      el('collection-detail-title').textContent = collection.name;
      renderAnalysis();
      el('collection-index').hidden = true; el('collection-detail').hidden = false;
      switchTab('overview');
      window.history.replaceState(null, '', '#' + id);
      el('collection-detail-title').focus();
    } catch {
      el('collections-status').textContent = 'This collection could not be opened. Please try again.';
      showError('Collection analysis or pinned reviewed records are unavailable.');
    }
  }
  function renderListItem(item) {
    const tr = document.createElement('tr');
    const dateValue = new Date(item.updated_at);
    const updated = Number.isNaN(dateValue.getTime()) ? 'Unavailable' :
      new Intl.DateTimeFormat(undefined, { year: 'numeric', month: 'short', day: 'numeric' }).format(dateValue);
    const identity = document.createElement('td');
    const identityWrap = node('div', '', 'collection-list-identity');
    const icon = node('span', '▤', 'collection-list-icon');
    icon.setAttribute('aria-hidden', 'true');
    identityWrap.append(icon, node('strong', item.name));
    identity.append(identityWrap); tr.append(identity);
    [item.member_count == null ? 'Unavailable' : plural(item.member_count, 'report'),
      (item.exam_types || []).map(examLabel).join(', ') || 'Exam type unavailable', updated].forEach(value => tr.append(node('td', value)));
    const td = document.createElement('td');
    const status = node('span', item.integrity === 'FAILED' ? 'Integrity issue' :
      item.state === 'READY_FOR_ANALYSIS' ? 'Ready' : item.state || 'Unavailable', 'collection-pill');
    status.dataset.state = item.integrity === 'FAILED' ? 'FAILED' : item.state;
    td.append(status); tr.append(td);
    const action = document.createElement('td'), button = node('button', 'Open →', 'product-text-button collection-open-action');
    button.type = 'button'; button.disabled = item.integrity === 'FAILED';
    button.setAttribute('aria-label', 'Open ' + item.name);
    button.addEventListener('click', () => openCollection(item.collection_id, button));
    action.append(button); tr.append(action); el('collection-list').append(tr);
  }
  async function loadCollections() {
    el('collections-status').textContent = 'Loading collections…';
    el('collections-retry').hidden = true; clear('collection-list');
    try {
      const result = await request('/reviewed-collections');
      if (!Array.isArray(result.collections)) throw new Error('Invalid collection list');
      const items = result.collections.filter(item => item && validId(item.collection_id) && typeof item.name === 'string');
      items.forEach(renderListItem);
      if (!items.length) {
        const tr = document.createElement('tr');
        const td = node('td', 'No reviewed collections yet. Accept clinical records in Reports, then create a collection from the Review Complete screen.', 'collection-empty');
        td.colSpan = 6; tr.append(td); el('collection-list').append(tr);
      }
      el('collections-status').textContent = items.length ? plural(items.length, 'reviewed collection') : '';
      const linked = window.location.hash.slice(1);
      if (validId(linked) && items.some(item => item.collection_id === linked)) await openCollection(linked);
    } catch {
      el('collections-status').textContent = 'Collections could not be loaded. Please try again.';
      el('collections-retry').hidden = false;
    }
  }
  async function viewReports() {
    if (!current) return;
    try {
      const result = await request(`/reviewed-collections/${current.collection_id}/versions/${current.version}`);
      const target = clear('collection-reports-list');
      (result.members || []).forEach(member => {
        const context = member.exam_context || {}, card = node('article', '', 'contributor');
        card.append(node('h3', [context.normalized_modality, context.normalized_body_region,
          context.normalized_laterality].filter(Boolean).join(' · ') || 'Reviewed report'),
          node('p', `Accepted clinical record · version ${member.reviewed_record_version}`));
        target.append(card);
      });
      el('collection-reports').showModal();
    } catch { showError('Pinned reviewed reports could not be opened.'); }
  }
  el('collections-retry').addEventListener('click', loadCollections);
  el('collection-back').addEventListener('click', () => {
    current = null; analysis = null; showError('');
    el('collection-detail').hidden = true; el('collection-index').hidden = false;
    el('collections-status').textContent = plural(el('collection-list').children.length, 'reviewed collection');
    window.history.replaceState(null, '', window.location.pathname);
    if (openingButton?.isConnected) openingButton.focus();
  });
  el('collection-view-reports').addEventListener('click', viewReports);
  document.querySelectorAll('.collection-tabs button').forEach(button =>
    button.addEventListener('click', () => switchTab(button.dataset.tab)));
  document.querySelectorAll('[data-close]').forEach(button =>
    button.addEventListener('click', () => el(button.dataset.close).close()));
  loadCollections();
})();
