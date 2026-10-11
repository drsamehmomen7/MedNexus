(() => {
  const endpoint = '/api/v1/understanding/analysis-collections';
  const list = document.getElementById('collection-list');
  const status = document.getElementById('collections-status');
  const retry = document.getElementById('collections-retry');
  const detail = document.getElementById('collection-detail');
  const detailTitle = document.getElementById('collection-detail-title');
  const detailSummary = document.getElementById('collection-detail-summary');
  const detailCounts = document.getElementById('collection-detail-counts');
  let openingButton = null;

  const count = value => Number.isInteger(value) && value >= 0 ? value : 0;
  const collectionId = value => typeof value === 'string' && /^[0-9a-f]{32}$/.test(value);
  const reportLabel = value => `${count(value)} ${count(value) === 1 ? 'report' : 'reports'}`;

  function addCount(label, value) {
    const item = document.createElement('div');
    const term = document.createElement('dt');
    const number = document.createElement('dd');
    term.textContent = label;
    number.textContent = String(count(value));
    item.append(term, number);
    detailCounts.append(item);
  }

  async function openCollection(id, button) {
    status.textContent = 'Opening collection…';
    try {
      const response = await fetch(`${endpoint}/${encodeURIComponent(id)}`, { cache: 'no-store' });
      if (!response.ok) throw new Error('Collection unavailable');
      const collection = await response.json();
      if (!collectionId(collection.collection_id) || collection.collection_id !== id ||
          typeof collection.name !== 'string') throw new Error('Collection unavailable');
      openingButton = button;
      detailTitle.textContent = collection.name;
      detailSummary.textContent = `${reportLabel(collection.report_count)} in this collection.`;
      detailCounts.replaceChildren();
      addCount('Reports', collection.report_count);
      addCount('Eligible', collection.eligible);
      addCount('Needs review', collection.review_required);
      addCount('Excluded', collection.excluded);
      detail.hidden = false;
      status.textContent = 'Collection opened.';
      detailTitle.focus();
    } catch {
      status.textContent = 'This collection could not be opened. Try again.';
    }
  }

  function renderCollection(collection) {
    const row = document.createElement('li');
    row.className = 'collection-row';
    const copy = document.createElement('div');
    copy.className = 'collection-row-copy';
    const title = document.createElement('h3');
    title.textContent = collection.name;
    const summary = document.createElement('p');
    const reviewCount = count(collection.review_required);
    summary.textContent = `${reportLabel(collection.report_count)} · ${reviewCount} ${reviewCount === 1 ? 'needs' : 'need'} review`;
    copy.append(title, summary);
    const button = document.createElement('button');
    button.className = 'product-text-button';
    button.type = 'button';
    button.textContent = 'Open collection →';
    button.setAttribute('aria-label', `Open ${collection.name} collection`);
    button.addEventListener('click', () => openCollection(collection.collection_id, button));
    row.append(copy, button);
    list.append(row);
  }

  async function loadCollections() {
    status.textContent = 'Loading collections…';
    retry.hidden = true;
    list.replaceChildren();
    detail.hidden = true;
    try {
      const response = await fetch(endpoint, { cache: 'no-store' });
      if (!response.ok) throw new Error('Collections unavailable');
      const payload = await response.json();
      if (!Array.isArray(payload.collections)) throw new Error('Collections unavailable');
      const collections = payload.collections.filter(item =>
        item && collectionId(item.collection_id) && typeof item.name === 'string');
      collections.forEach(renderCollection);
      status.textContent = collections.length
        ? `${collections.length} saved ${collections.length === 1 ? 'collection' : 'collections'}.`
        : 'No collections yet. Governed report collections will appear here when created.';
    } catch {
      status.textContent = 'Collections could not be loaded. Try again.';
      retry.hidden = false;
    }
  }

  retry.addEventListener('click', loadCollections);
  document.getElementById('collection-back').addEventListener('click', () => {
    detail.hidden = true;
    status.textContent = 'Saved collections.';
    if (openingButton?.isConnected) openingButton.focus();
  });
  loadCollections();
})();
