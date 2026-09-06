const $ = id => document.getElementById(id);
let mode = 'text';

const LABELS = {
  ADMISSION_DISCHARGE: 'Admission / Discharge',
  RADIOLOGY_REPORT: 'Radiology Report',
  PATHOLOGY_REPORT: 'Pathology Report',
  LABORATORY_REPORT: 'Laboratory Report',
  EMERGENCY_REPORT: 'Emergency Report',
  ADMISSION_NOTE: 'Admission Note',
  DISCHARGE_SUMMARY: 'Discharge Summary',
  PUBLIC_HEALTH_DOCUMENT: 'Public Health Document',
  X_RAY: 'X-ray', NUCLEAR_MEDICINE: 'Nuclear Medicine',
  ENGLISH: 'English', ARABIC: 'Arabic', MIXED: 'Mixed Arabic / English',
  COMPLETED_REPORT: 'Completed Report', STRUCTURED_TEMPLATE: 'Structured Template',
  PARTIAL_REPORT: 'Partial Report', WITH_CONTRAST: 'With contrast',
  WITHOUT_CONTRAST: 'Without contrast', PRE_AND_POST_CONTRAST: 'Pre/Post contrast',
  CT: 'CT', CTA: 'CTA', MRI: 'MRI', MRA: 'MRA', MRV: 'MRV',
  CR: 'CR', DX: 'DX', XR: 'XR', SPECT: 'SPECT', PET: 'PET',
  SPECT_CT: 'SPECT / CT', PET_CT: 'PET / CT',
  GENERAL_DIAGNOSTIC: 'General Diagnostic', CONTRAST_STUDY: 'Contrast Study',
  DYNAMIC_FUNCTIONAL_STUDY: 'Dynamic / Functional Study',
  STANDARD_VIEWS: 'Standard Views', TOMOSYNTHESIS: 'Tomosynthesis',
  MULTIPLANAR_RECONSTRUCTION: 'Multiplanar Reconstruction', ANGIOGRAPHIC: 'Angiographic',
};

const REGION_LABELS = {
  STUDY_OR_EVENT_IDENTITY: 'Study Identity',
  CLINICAL_OR_REPORTING_INDICATION: 'Clinical Indication',
  TECHNIQUE_OR_ACQUISITION: 'Technique / Acquisition',
  OBSERVATION_NARRATIVE: 'Findings / Observation Narrative',
  CONCLUSION_OR_STATUS: 'Impression / Conclusion',
  COMPARISON_OR_PRIOR_CONTEXT: 'Comparison / Prior Study',
  RECOMMENDATION_OR_FUTURE_ACTION: 'Recommendation / Future Action',
  PROFESSIONAL_OR_AUTHORITY_AUTHENTICATION: 'Professional Authentication',
};

const OTHER_REASON_LABELS = {
  UNSUPPORTED_FAMILY: 'The imaging family is outside the current supported set.',
  CONFLICTING_CURRENT_FAMILY: 'Conflicting current-study family evidence requires review.',
  INSUFFICIENT_FAMILY_EVIDENCE: 'The imaging family does not have enough governed evidence.',
  INTERVENTIONAL_PROCEDURE: 'This Radiology procedure does not belong to a supported diagnostic imaging family.',
};

function label(value) {
  const key = String(value || 'UNKNOWN');
  return LABELS[key] || key.toLowerCase().replaceAll('_', ' ').replace(/\b\w/g, char => char.toUpperCase());
}

function isPresent(value) {
  return value !== null && value !== undefined && value !== '' && (!Array.isArray(value) || value.length > 0);
}

function presence(value) {
  if (value === true) return 'Present';
  if (value === false) return 'Not evidenced';
  return null;
}

function setMode(next) {
  mode = next;
  $('textTab').classList.toggle('active', next === 'text');
  $('fileTab').classList.toggle('active', next === 'file');
  $('textMode').style.display = next === 'text' ? 'block' : 'none';
  $('fileMode').classList.toggle('active', next === 'file');
  $('status').textContent = '';
}

function renderList(target, items, render, empty) {
  target.replaceChildren();
  if (!items.length) {
    const item = document.createElement('div');
    item.className = 'empty';
    item.textContent = empty;
    target.append(item);
    return;
  }
  items.forEach(value => target.append(render(value)));
}

function renderRows(target, rows) {
  target.replaceChildren();
  rows.filter(([, value]) => isPresent(value)).forEach(([key, value]) => {
    const row = document.createElement('div');
    const term = document.createElement('dt');
    const description = document.createElement('dd');
    term.textContent = key;
    description.textContent = Array.isArray(value) ? value.map(label).join(' · ') : value;
    row.append(term, description);
    target.append(row);
  });
}

function xrayViewContext(context) {
  const values = [];
  if (context.views?.length) values.push(context.views.map(label).join(' / '));
  if (context.view_count) {
    values.push(`${context.view_count}${context.view_count_qualifier === 'OR_MORE' ? ' or more' : ''} views`);
  }
  return values.join(' · ') || null;
}

const RADIOLOGY_CONTEXT_RENDERERS = {
  CT: context => [
    ['Study Family', context.study_family && label(context.study_family)],
    ['Body Region', context.body_region && label(context.body_region)],
    ['Contrast', context.contrast && label(context.contrast)],
    ['Acquisition Context', context.acquisition_summary || []],
  ],
  MRI: context => [
    ['Study Family', context.study_family && label(context.study_family)],
    ['Body Region', context.body_region && label(context.body_region)],
    ['Contrast', context.contrast && label(context.contrast)],
    ['Sequence Context', context.sequence_context || []],
  ],
  X_RAY: context => [
    ['Body Region / Study Anatomy', context.body_region && label(context.body_region)],
    ['Laterality', context.laterality && label(context.laterality)],
    ['View Context', xrayViewContext(context)],
    ['Source', context.source_type && label(context.source_type)],
  ],
  ULTRASOUND: context => [
    ['Body Region / Organ / Vascular Territory', context.body_region && label(context.body_region)],
    ['Study Context', context.vascular_context ? label(context.vascular_context) : context.study_extent && label(context.study_extent)],
    ['Technique', context.specialization && label(context.specialization)],
    ['Measurement-bearing Content', presence(context.measurement_bearing_present)],
  ],
  MAMMOGRAPHY: context => [
    ['Study Context', context.study_purpose && label(context.study_purpose)],
    ['Laterality', context.laterality && label(context.laterality)],
    ['Views / Tomosynthesis', context.acquisition_context || []],
    ['BI-RADS Assessment', presence(context.birads_assessment_present)],
  ],
  NUCLEAR_MEDICINE: context => [
    ['Study Family', context.study_family && label(context.study_family)],
    ['Body Region / Organ', context.body_region && label(context.body_region)],
    ['Radiopharmaceutical Context', presence(context.radiopharmaceutical_context_present)],
    ['Quantitative Uptake Context', presence(context.quantitative_uptake_context_present)],
  ],
  FLUOROSCOPY: context => [
    ['Study / Procedure Family', context.study_family && label(context.study_family)],
    ['Body System', context.body_system && label(context.body_system)],
    ['Contrast Study', presence(context.contrast_study_present)],
    ['Dynamic / Functional Context', presence(context.dynamic_functional_present)],
  ],
  OTHER: () => [],
};

function renderRadiologyContext(context) {
  const light = context.light_context || {};
  const family = light.family_context || null;
  if (light.domain_type !== 'RADIOLOGY' || !family || !RADIOLOGY_CONTEXT_RENDERERS[family.subdomain]) {
    $('semanticCard').hidden = true;
    return;
  }
  const other = family.subdomain === 'OTHER';
  $('contextTitle').textContent = other ? 'Radiology family requires review' : `${label(family.subdomain)} document context`;
  $('contextDescription').textContent = other
    ? 'MedNexus recognized this as a Radiology document, but the imaging family could not be classified safely.'
    : 'Bounded document-level context recognized for the current study.';
  renderRows($('semanticList'), [
    ['Subdomain', label(family.subdomain)],
    ...RADIOLOGY_CONTEXT_RENDERERS[family.subdomain](family),
  ]);
  $('semanticNote').hidden = !other;
  $('semanticNote').textContent = other
    ? `${OTHER_REASON_LABELS[family.review_reason] || 'Review is required to determine the imaging family.'} No modality has been guessed.`
    : '';
  $('semanticCard').hidden = false;
}

function renderIdentity(payload, context) {
  const identity = context.identity || {};
  const domain = identity.domain || identity.healthcare_domain || payload.domain;
  const unknown = domain === 'UNKNOWN' || identity.document_type === 'UNKNOWN';
  const subdomain = identity.subdomain_or_family;
  $('domainValue').textContent = unknown ? 'Document type not confidently identified' : label(domain);
  $('documentSummary').textContent = unknown
    ? 'Manual review recommended'
    : [label(identity.document_type || payload.document_type), subdomain && label(subdomain)].filter(Boolean).join(' · ');
  renderRows($('identityFacts'), [
    ['Document Type', unknown ? 'Not determined' : label(identity.document_type || payload.document_type)],
    ['Subdomain', unknown || !subdomain ? 'Not determined' : label(subdomain)],
    ['Document Nature', identity.document_nature && identity.document_nature !== 'UNKNOWN'
      ? label(identity.document_nature) : 'Not determined'],
    ['Primary Language', label(identity.language || context.document?.primary_language || payload.language)],
  ]);
  $('confidenceValue').textContent = `${Math.round(Number(identity.confidence ?? payload.confidence ?? 0) * 100)}%`;
  $('confidenceBand').textContent = `${label(identity.confidence_band || payload.confidence_band)} confidence`;
  $('confidenceNote').textContent = unknown
    ? 'MedNexus found some document features, but not enough evidence to identify the document reliably.'
    : 'Evidence supports this recognition.';
  $('recognitionSummary').classList.toggle('low', unknown || ['LOW', 'UNKNOWN'].includes(identity.confidence_band || payload.confidence_band));
}

function renderStructure(context) {
  const canonical = context.semantic_regions || [];
  const canonicalRegions = canonical.filter(region => region.role);
  const regions = canonicalRegions.length
    ? canonicalRegions.map(region => REGION_LABELS[region.role] || label(region.role))
    : (context.structure || []).map(region => region.semantic_role).filter(Boolean);
  renderList($('sectionList'), [...new Set(regions)], value => {
    const item = document.createElement('div');
    item.className = 'structure-item';
    item.textContent = value;
    return item;
  }, 'No semantic document regions were identified.');
}

function renderExplanations(payload) {
  const explanations = (payload.recognition_explanations || []).map(item => item.message).filter(Boolean);
  renderList($('recognitionReasons'), explanations, value => {
    const item = document.createElement('div');
    const icon = document.createElement('i');
    const message = document.createElement('span');
    item.className = 'simple-item';
    icon.textContent = '✓';
    message.textContent = value;
    item.append(icon, message);
    return item;
  }, 'Detailed recognition explanation is unavailable.');
}

function renderReadiness(payload, context) {
  const processing = context.processing_context || {};
  const review = processing.document_review_required ?? processing.manual_review_required ?? true;
  const states = review
    ? [['Review', 'Required before continuing', 'review']]
    : [
      ['PROTECT', processing.protect_ready ? 'Ready for stage' : 'Not ready', processing.protect_ready ? 'ready' : 'pending'],
      ['EXTRACT', processing.extract_ready ? 'Ready for stage' : 'Not ready', processing.extract_ready ? 'ready' : 'pending'],
    ];
  renderList($('readinessList'), states, ([stage, state, className]) => {
    const item = document.createElement('div');
    const name = document.createElement('b');
    const status = document.createElement('span');
    item.className = `readiness-item ${className}`;
    name.textContent = stage;
    status.textContent = state;
    item.append(name, status);
    return item;
  }, 'Readiness information is unavailable.');
  $('journeyTitle').textContent = review ? 'Review required before continuing.' : 'Document context established.';
  $('routeNote').textContent = review
    ? 'The document remains available for review; no downstream stage has been completed.'
    : 'This document is ready to enter supported next stages. Readiness does not mean those stages are complete.';
  $('continueBtn').hidden = review || !processing.protect_ready;
  $('continueBtn').onclick = () => {
    if (payload.journey?.continue_to_protect) location.href = payload.journey.continue_to_protect;
  };
}

function renderTechnicalDetails(payload, context) {
  $('machineDetails').textContent = JSON.stringify({
    document_context: context,
    legacy_compatibility: {
      domain: payload.domain, document_type: payload.document_type,
      document_subtype: payload.document_subtype, language: payload.language,
      confidence: payload.confidence, confidence_band: payload.confidence_band,
    },
    journey_id: payload.journey?.journey_id,
  }, null, 2);
  renderList($('technicalSections'), context.semantic_regions || [], region => {
    const item = document.createElement('div');
    item.className = 'technical-row';
    item.textContent = `${region.region_id} · ${region.role || 'UNRESOLVED'} · ${region.start}–${region.end}`;
    return item;
  }, 'No canonical region offsets.');
  renderList($('technicalEvidence'), payload.evidence || [], evidence => {
    const item = document.createElement('div');
    const heading = document.createElement('b');
    const detail = document.createElement('span');
    item.className = 'technical-row';
    heading.textContent = `${evidence.category} · weight ${evidence.weight}${evidence.concept_id ? ` · ${evidence.concept_id}` : ''}`;
    detail.textContent = `${evidence.signal}${evidence.reference ? ` · matched “${evidence.reference}”` : ''}${evidence.reference_systems?.length ? ` · ${evidence.reference_systems.join(', ')}` : ''}`;
    item.append(heading, detail);
    return item;
  }, 'No knowledge evidence.');
  $('technicalRouting').textContent = JSON.stringify({
    processing_context: context.processing_context || {}, legacy_routing: payload.routing || {},
  }, null, 2);
  document.querySelector('.technical-details').removeAttribute('open');
}

function render(payload) {
  const context = payload.document_context || {};
  renderIdentity(payload, context);
  renderRadiologyContext(context);
  renderStructure(context);
  renderExplanations(payload);
  renderReadiness(payload, context);
  renderTechnicalDetails(payload, context);
  const warnings = payload.warnings || [];
  $('warnings').classList.toggle('show', warnings.length > 0);
  $('warnings').textContent = warnings.length ? `Warnings: ${warnings.join(' · ')}` : '';
  $('results').classList.add('show');
  $('results').scrollIntoView({ behavior: 'smooth' });
}

async function analyze() {
  try {
    $('analyzeBtn').disabled = true;
    $('status').textContent = 'Establishing document context…';
    let response;
    if (mode === 'text') {
      const text = $('textInput').value.trim();
      if (!text) throw Error('Paste medical document text before analysis.');
      response = await fetch('/api/v1/understanding/analyze-text', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }),
      });
    } else {
      const file = $('fileInput').files[0];
      if (!file) throw Error('Choose a supported document before analysis.');
      const form = new FormData();
      form.append('file', file);
      response = await fetch('/api/v1/understanding/analyze-file', { method: 'POST', body: form });
    }
    const payload = await response.json();
    if (!response.ok) throw Error(payload.detail || 'MedNexus could not understand this document.');
    render(payload);
    $('status').textContent = '';
  } catch (error) {
    $('status').textContent = error.message || 'MedNexus could not understand this document.';
  } finally {
    $('analyzeBtn').disabled = false;
  }
}

$('textTab').onclick = () => setMode('text');
$('fileTab').onclick = () => setMode('file');
$('fileInput').onchange = () => {
  $('fileName').textContent = $('fileInput').files[0]?.name || 'No file selected';
};
$('analyzeBtn').onclick = analyze;
$('anotherBtn').onclick = () => {
  $('results').classList.remove('show');
  $('workspace').scrollIntoView({ behavior: 'smooth' });
};
